"""Wrapper fsck + SHA-256 — fase VERIFY."""
from __future__ import annotations

import asyncio
import hashlib
import subprocess
from pathlib import Path


def detect_fstype(image_path: Path) -> str:
    try:
        out = subprocess.check_output(
            ["blkid", "-o", "value", "-s", "TYPE", str(image_path)],
            text=True, stderr=subprocess.DEVNULL,
        )
        return out.strip().lower()
    except Exception:
        return ""


def _fsck_cmd(image_path: Path) -> list[str]:
    fstype = detect_fstype(image_path)
    if fstype in ("vfat", "fat", "fat32", "fat16"):
        return ["fsck.fat", "-n", str(image_path)]
    if fstype in ("exfat",):
        return ["fsck.exfat", str(image_path)]
    return ["sudo", "fsck", "-n", str(image_path)]


class FsckProcess:
    """Wrapper asincrono per fsck, killabile."""

    def __init__(self) -> None:
        self._proc: asyncio.subprocess.Process | None = None

    async def run(self, image_path: Path) -> tuple[bool, str]:
        cmd = _fsck_cmd(image_path)
        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert self._proc.stdout is not None
        out_bytes = await self._proc.stdout.read()
        await self._proc.wait()
        output = out_bytes.decode("utf-8", errors="replace").strip()
        ok = self._proc.returncode in (0, 1)
        return ok, output

    def kill(self) -> None:
        if self._proc and self._proc.returncode is None:
            try:
                self._proc.kill()
            except ProcessLookupError:
                pass


async def compute_sha256_async(
    image_path: Path,
    sha_path: Path,
    abort: asyncio.Event | None = None,
    chunk: int = 1 << 20,
) -> str | None:
    """SHA-256 asincrono, interrompibile via abort event."""
    h = hashlib.sha256()
    loop = asyncio.get_event_loop()

    def _read_chunk(f, size: int) -> bytes:
        return f.read(size)

    with image_path.open("rb") as f:
        while True:
            if abort and abort.is_set():
                return None
            data = await loop.run_in_executor(None, _read_chunk, f, chunk)
            if not data:
                break
            h.update(data)

    digest = h.hexdigest()
    sha_path.write_text(f"{digest}  {image_path.name}\n", encoding="utf-8")
    return digest


def get_tool_version(tool: str) -> str:
    try:
        out = subprocess.check_output([tool, "--version"], text=True, stderr=subprocess.STDOUT)
        return out.splitlines()[0].strip()
    except Exception:
        return "?"
