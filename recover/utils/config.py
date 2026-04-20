"""Carica e salva config.toml."""
from __future__ import annotations

import shutil
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

_DEFAULT = Path(__file__).parent.parent.parent / "config.toml.default"
_USER = Path(__file__).parent.parent.parent / "config.toml"


def load() -> dict[str, Any]:
    if not _USER.exists():
        shutil.copy(_DEFAULT, _USER)
    with _USER.open("rb") as f:
        return tomllib.load(f)


def save(cfg: dict[str, Any]) -> None:
    with _USER.open("wb") as f:
        tomli_w.dump(cfg, f)


def output_dir(cfg: dict[str, Any]) -> Path:
    return Path(cfg["general"]["output_dir"]).expanduser()


def image_dir(cfg: dict[str, Any]) -> Path:
    return Path(cfg["imaging"]["image_dir"]).expanduser()
