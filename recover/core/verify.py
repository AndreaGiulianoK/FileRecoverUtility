"""Wrapper fsck + SHA-256 — fase VERIFY."""
from __future__ import annotations

import subprocess
from pathlib import Path

from recover.utils.hash import sha256


def detect_fstype(image_path: Path) -> str:
    try:
        out = subprocess.check_output(
            ["blkid", "-o", "value", "-s", "TYPE", str(image_path)],
            text=True, stderr=subprocess.DEVNULL,
        )
        return out.strip().lower()
    except Exception:
        return ""


def run_fsck(image_path: Path, fstype: str = "") -> tuple[bool, str]:
    """Esegue fsck in modalità read-only (-n). Ritorna (ok, output)."""
    if not fstype:
        fstype = detect_fstype(image_path)

    if fstype in ("vfat", "fat", "fat32", "fat16"):
        cmd = ["fsck.fat", "-n", str(image_path)]
    elif fstype in ("exfat",):
        cmd = ["fsck.exfat", str(image_path)]
    else:
        # tentativo generico
        cmd = ["sudo", "fsck", "-n", str(image_path)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        output = (result.stdout + result.stderr).strip()
        # fsck.fat returns 0 for clean, 1 for errors fixable, 2+ for severe
        ok = result.returncode in (0, 1)
        return ok, output
    except FileNotFoundError as e:
        return False, f"Comando non trovato: {e}"
    except subprocess.TimeoutExpired:
        return False, "fsck timeout (>5 min)"


def compute_sha256(image_path: Path, sha_path: Path) -> str:
    digest = sha256(image_path)
    sha_path.write_text(f"{digest}  {image_path.name}\n", encoding="utf-8")
    return digest


def get_tool_version(tool: str) -> str:
    try:
        out = subprocess.check_output([tool, "--version"], text=True, stderr=subprocess.STDOUT)
        return out.splitlines()[0].strip()
    except Exception:
        return "?"
