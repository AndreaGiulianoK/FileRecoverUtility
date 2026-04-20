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
    pct_rescued: float = 0.0
    remaining: str = ""
    info_line: str = ""   # riga informativa da loggare (vuota se è solo status)


_SI = {"b": 1, "kb": 1_000, "mb": 1_000_000, "gb": 1_000_000_000, "tb": 1_000_000_000_000}

_ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|[\x08\r]")

# Parole chiave che identificano le righe di progresso ddrescue (non da loggare)
_STATUS_KEYS = (
    "ipos:", "opos:", "non-tried:", "rescued:", "bad areas:",
    "pct rescued:", "time since last", "non-trimmed:", "non-scraped:",
    "bad-sector:", "error rate:", "run time:", "remaining time:",
    "read errors:", "successful reads:",
)


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def is_status_line(line: str) -> bool:
    low = line.lower()
    return any(k in low for k in _STATUS_KEYS)


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


def _build_cmd(source: Path, image_path: Path, map_path: Path, extra_args: list[str]) -> list[str]:
    base = ["sudo", "ddrescue", "--force", str(source), str(image_path), str(map_path)]
    if extra_args:
        base.extend(extra_args)

    import shutil
    if shutil.which("stdbuf"):
        # stdbuf -eL forza line-buffering su stderr: l'output arriva subito invece di bloccarsi
        return ["stdbuf", "-eL"] + base
    return base


async def run(
    source: Path,
    image_path: Path,
    map_path: Path,
    extra_args: list[str] | None = None,
) -> AsyncIterator[ImagingProgress]:
    """Esegue ddrescue. Richiede che sudo sia già autenticato (via validate_sudo)."""
    image_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = _build_cmd(source, image_path, map_path, extra_args or [])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,   # cattura stdout oltre a stderr
        stderr=asyncio.subprocess.STDOUT, # unisci stderr su stdout
    )

    progress = ImagingProgress()
    buf = b""

    assert proc.stdout is not None
    while True:
        chunk = await proc.stdout.read(256)
        if not chunk:
            break
        buf += chunk
        # ddrescue usa \r per aggiornamenti in-place e \n per messaggi normali
        parts = re.split(rb"[\r\n]", buf)
        buf = parts[-1]
        for raw in parts[:-1]:
            line = strip_ansi(raw.decode("utf-8", errors="replace")).strip()
            if not line:
                continue
            # copia le stat precedenti, aggiorna solo i campi trovati
            progress = ImagingProgress(
                rescued_bytes=progress.rescued_bytes,
                error_bytes=progress.error_bytes,
                errors=progress.errors,
                rate=progress.rate,
                avg_rate=progress.avg_rate,
                elapsed=progress.elapsed,
                pct_rescued=progress.pct_rescued,
                remaining=progress.remaining,
                info_line="" if is_status_line(line) else line,
            )
            _parse_into(line, progress)
            yield progress

    await proc.wait()
    yield progress


def _parse_into(line: str, p: ImagingProgress) -> None:
    # lookbehind negativo: non matchare "pct rescued:" né "non-rescued:"
    m = re.search(r"(?<!\w)rescued:\s*([\d.,]+)\s*(B|kB|MB|GB|TB)\b", line, re.I)
    if m:
        p.rescued_bytes = _to_bytes(m.group(1).replace(",", "."), m.group(2))

    m = re.search(r"errsize:\s*([\d.]+)\s*(\w+)", line, re.I)
    if m:
        p.error_bytes = _to_bytes(m.group(1), m.group(2))

    m = re.search(r"\berrors:\s*(\d+)", line, re.I)
    if m:
        p.errors = int(m.group(1))

    m = re.search(r"read errors:\s*(\d+)", line, re.I)
    if m:
        p.errors = int(m.group(1))

    m = re.search(r"current rate:\s*([\d.,]+\s*\w+/s)", line, re.I)
    if m:
        p.rate = m.group(1).strip()

    m = re.search(r"average rate:\s*([\d.,]+\s*\w+/s)", line, re.I)
    if m:
        p.avg_rate = m.group(1).strip()

    m = re.search(r"run time:\s*([^\n,]+)", line, re.I)
    if m:
        p.elapsed = m.group(1).strip()

    m = re.search(r"pct rescued:\s*([\d.]+)%", line, re.I)
    if m:
        try:
            p.pct_rescued = float(m.group(1))
        except ValueError:
            pass

    m = re.search(r"remaining time:\s*([^\n,]+)", line, re.I)
    if m:
        p.remaining = m.group(1).strip()
