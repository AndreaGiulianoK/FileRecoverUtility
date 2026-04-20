"""Stato condiviso di una sessione di recupero."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from recover.utils.fs import BlockDevice


@dataclass
class RecoveredFile:
    path: Path
    name: str
    mimetype: str
    size: int
    date_original: str
    status: str          # OK | PARZIALE | CORROTTO | DUPLICATO
    thumbnail: str       # data-URI base64 o ""

    @property
    def status_class(self) -> str:
        return {"OK": "ok", "PARZIALE": "warn", "CORROTTO": "error", "DUPLICATO": "warn"}.get(
            self.status, "ok"
        )


@dataclass
class Session:
    device: BlockDevice
    mode: str            # A | B | C
    timestamp: str       # YYYY-MM-DD_HHMMSS

    image_path: Path | None = None
    map_path: Path | None = None
    image_sha256: str | None = None
    session_dir: Path | None = None
    raw_dir: Path | None = None          # output grezzo photorec/testdisk
    recovered_files: list[RecoveredFile] = field(default_factory=list)
    fsck_ok: bool | None = None
    fsck_output: str = ""
    tool_versions: dict[str, str] = field(default_factory=dict)
