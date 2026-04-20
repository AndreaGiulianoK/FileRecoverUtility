"""Lettura metadata EXIF via exiftool."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExifData:
    datetime_original: str  # "2023:08:15 14:32:07" o ""
    make: str
    model: str
    raw: dict


def read(path: Path) -> ExifData:
    try:
        out = subprocess.check_output(
            ["exiftool", "-j", "-DateTimeOriginal", "-Make", "-Model", str(path)],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        data = json.loads(out)[0]
    except (subprocess.CalledProcessError, FileNotFoundError, (json.JSONDecodeError, IndexError)):
        data = {}

    return ExifData(
        datetime_original=data.get("DateTimeOriginal", ""),
        make=data.get("Make", ""),
        model=data.get("Model", ""),
        raw=data,
    )


def build_filename(exif: ExifData, original_index: int, ext: str, fallback: str = "recovered") -> str:
    ext = ext.lstrip(".").lower()

    if exif.datetime_original:
        dt = exif.datetime_original.replace(":", "-").replace(" ", "_")
        parts = [dt]
        if exif.make:
            parts.append(_safe(exif.make))
        if exif.model:
            parts.append(_safe(exif.model))
        return "_".join(parts) + f".{ext}"

    return f"{fallback}_{original_index:05d}_no_meta.{ext}"


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s).strip("_")
