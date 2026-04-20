"""Wrapper TSK (fls + icat) per recupero automatico file."""
from __future__ import annotations

import asyncio
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator


@dataclass
class FileEntry:
    inode: str
    path: str
    deleted: bool


@dataclass
class AnalyzeProgress:
    total: int = 0
    done: int = 0
    current_file: str = ""
    failed: int = 0
    finished: bool = False


_FLS_LINE = re.compile(r'^([a-z-])/([a-z-])\s+(\*\s+)?([^:]+):')


def check_tools() -> list[str]:
    return [t for t in ("fls", "icat") if not shutil.which(t)]


async def list_files(image_path: Path, include_all: bool = True) -> list[FileEntry]:
    proc = await asyncio.create_subprocess_exec(
        "fls", "-r", "-p", str(image_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate()

    entries: list[FileEntry] = []
    for raw in stdout.decode("utf-8", errors="replace").splitlines():
        if "\t" not in raw:
            continue
        meta_part, path = raw.split("\t", 1)
        path = path.strip()

        m = _FLS_LINE.match(meta_part.strip())
        if not m:
            continue
        type1, type2, star, inode = m.groups()

        # skip directories and virtual entries
        if type1 == "d" or type2 == "d":
            continue
        if path.split("/")[-1].startswith("$"):
            continue

        deleted = bool(star) or type1 == "-"
        if include_all or deleted:
            entries.append(FileEntry(inode=inode.strip(), path=path, deleted=deleted))

    return entries


async def run(
    image_path: Path,
    raw_dir: Path,
    include_all: bool = True,
    abort: asyncio.Event | None = None,
) -> AsyncIterator[AnalyzeProgress]:
    entries = await list_files(image_path, include_all=include_all)
    prog = AnalyzeProgress(total=len(entries))
    yield prog

    for entry in entries:
        if abort and abort.is_set():
            break

        prog.current_file = entry.path
        dest = raw_dir / entry.path
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            proc = await asyncio.create_subprocess_exec(
                "icat", str(image_path), entry.inode,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            assert proc.stdout is not None
            with open(dest, "wb") as f:
                while True:
                    chunk = await proc.stdout.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            await proc.wait()
            if proc.returncode != 0:
                prog.failed += 1
                dest.unlink(missing_ok=True)
        except Exception:
            prog.failed += 1

        prog.done += 1
        yield prog

    prog.finished = True
    yield prog
