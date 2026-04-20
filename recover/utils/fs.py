"""Utility per rilevamento dispositivi e mount."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BlockDevice:
    name: str        # es. sdb
    path: str        # es. /dev/sdb
    size: str        # es. 32G
    fstype: str      # es. vfat, exfat, ""
    label: str       # es. SANDISK
    mountpoint: str  # es. /media/user/SANDISK o ""
    removable: bool

    @property
    def is_mounted(self) -> bool:
        return bool(self.mountpoint)

    @property
    def display_name(self) -> str:
        return self.label or self.name


def list_removable() -> list[BlockDevice]:
    try:
        out = subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,PATH,SIZE,FSTYPE,LABEL,MOUNTPOINT,RM"],
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    data = json.loads(out)
    devices: list[BlockDevice] = []

    def _walk(nodes: list[dict]) -> None:
        for node in nodes:
            rm = str(node.get("rm", "0")) == "1"
            if rm:
                devices.append(BlockDevice(
                    name=node.get("name", ""),
                    path=node.get("path", f"/dev/{node.get('name', '')}"),
                    size=node.get("size", "?"),
                    fstype=node.get("fstype") or "",
                    label=node.get("label") or "",
                    mountpoint=node.get("mountpoint") or "",
                    removable=True,
                ))
            children = node.get("children") or []
            _walk(children)

    _walk(data.get("blockdevices", []))
    return devices


def session_dir(base: Path, device: BlockDevice, timestamp: str) -> Path:
    label = device.label or device.name
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
    return base / f"{safe}_{timestamp}"
