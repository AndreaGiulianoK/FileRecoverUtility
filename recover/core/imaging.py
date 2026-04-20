"""Wrapper ddrescue — fase IMAGE."""
from __future__ import annotations

import asyncio
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator


@dataclass
class ImagingProgress:
    rescued_bytes: int = 0
    error_bytes: int = 0
    errors: int = 0
    rate: str = ""
    avg_rate: str = ""
    elapsed: str = ""
    line: str = ""


_SI = {"b": 1, "kb": 1_000, "mb": 1_000_000, "gb": 1_000_000_000, "tb": 1_000_000_000_000}


def _to_bytes(value: str, unit: str) -> int:
    try:
        return int(float(value) * _SI.get(unit.lower().rstrip("s"), 1))
    except ValueError:
        return 0


def device_size_bytes(dev_path: str) -> int:
    """Dimensione in byte via lsblk (non richiede sudo)."""
    try:
        out = subprocess.check_output(
            ["lsblk", "-b", "-dn", "-o", "SIZE", dev_path],
            text=True, stderr=subprocess.DEVNULL,
        )
        return int(out.strip())
    except Exception:
        return 0


async def validate_sudo(password: str) -> bool:
    """Valida la password sudo e mette in cache le credenziali.

    Usa 'sudo -S -v': non esegue comandi, aggiorna solo il timestamp sudo.
    Dopo questa chiamata, sudo non richiederà password per qualche minuto.
    """
    proc = await asyncio.create_subprocess_exec(
        "sudo", "-S", "-v",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    assert proc.stdin is not None
    proc.stdin.write((password + "\n").encode())
    await proc.stdin.drain()
    proc.stdin.close()
    await proc.wait()
    return proc.returncode == 0


async def run(
    source: Path,
    image_path: Path,
    map_path: Path,
    extra_args: list[str] | None = None,
) -> AsyncIterator[ImagingProgress]:
    """Esegue ddrescue. Richiede che sudo sia già autenticato (via validate_sudo)."""
    image_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "sudo", "ddrescue",
        "--force",
        str(source), str(image_path), str(map_path),
    ]
    if extra_args:
        cmd.extend(extra_args)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    progress = ImagingProgress()
    buf = b""

    assert proc.stderr is not None
    while True:
        chunk = await proc.stderr.read(512)
        if not chunk:
            break
        buf += chunk
        # split on \r and \n, keeping incomplete tail
        parts = re.split(rb"[\r\n]", buf)
        buf = parts[-1]
        for raw in parts[:-1]:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            progress.line = line
            _parse_into(line, progress)
            yield progress

    await proc.wait()
    # yield final state
    yield progress


def _parse_into(line: str, p: ImagingProgress) -> None:
    m = re.search(r"rescued:\s*([\d.]+)\s*(\w+)", line, re.I)
    if m:
        p.rescued_bytes = _to_bytes(m.group(1), m.group(2))

    m = re.search(r"errsize:\s*([\d.]+)\s*(\w+)", line, re.I)
    if m:
        p.error_bytes = _to_bytes(m.group(1), m.group(2))

    m = re.search(r"errors:\s*(\d+)", line, re.I)
    if m:
        p.errors = int(m.group(1))

    m = re.search(r"current rate:\s*([\d.]+\s*\w+/s)", line, re.I)
    if m:
        p.rate = m.group(1).strip()

    m = re.search(r"average rate:\s*([\d.]+\s*\w+/s)", line, re.I)
    if m:
        p.avg_rate = m.group(1).strip()

    m = re.search(r"run time:\s*([^\n,]+)", line, re.I)
    if m:
        p.elapsed = m.group(1).strip()
