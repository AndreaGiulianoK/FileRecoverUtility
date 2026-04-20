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
            ["lsblk", "-J", "-o", "NAME,PATH,SIZE,FSTYPE,LABEL,MOUNTPOINT,RM,TRAN"],
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    data = json.loads(out)
    devices: list[BlockDevice] = []

    def _walk(nodes: list[dict], parent_tran: str = "") -> None:
        for node in nodes:
            rm = str(node.get("rm", "0")) == "1"
            tran = (node.get("tran") or parent_tran or "").lower()
            is_external = rm or tran == "usb"
            children = node.get("children") or []

            if is_external:
                if children:
                    # disco con partizioni: aggiungi solo le partizioni, non il disco padre
                    _walk(children, tran)
                else:
                    # foglia: partizione o disco non partizionato
                    size = node.get("size") or "0B"
                    if size.startswith("0"):
                        # slot lettore vuoto, nessun media inserito
                        continue
                    devices.append(BlockDevice(
                        name=node.get("name", ""),
                        path=node.get("path", f"/dev/{node.get('name', '')}"),
                        size=size,
                        fstype=node.get("fstype") or "",
                        label=node.get("label") or "",
                        mountpoint=node.get("mountpoint") or "",
                        removable=True,
                    ))
            else:
                _walk(children, tran)

    _walk(data.get("blockdevices", []))
    return devices


def unmount_device(dev: BlockDevice) -> tuple[bool, str]:
    """Smonta tutte le partizioni montate del dispositivo.

    Prova prima udisksctl (no sudo), poi umount con sudo.
    Ritorna (successo, messaggio_errore).
    """
    import shutil

    paths_to_unmount = [dev.path] if dev.mountpoint else []

    # Smonta anche le partizioni figlie montate (es. sdb1, sdb2)
    try:
        out = subprocess.check_output(
            ["lsblk", "-J", "-o", "PATH,MOUNTPOINT", dev.path],
            text=True, stderr=subprocess.DEVNULL,
        )
        import json as _json
        data = _json.loads(out)
        def _collect(nodes: list[dict]) -> None:
            for n in nodes:
                if n.get("mountpoint"):
                    paths_to_unmount.append(n["path"])
                _collect(n.get("children") or [])
        _collect(data.get("blockdevices", []))
    except Exception:
        pass

    # deduplica preservando l'ordine
    seen: set[str] = set()
    unique_paths = [p for p in paths_to_unmount if not (p in seen or seen.add(p))]  # type: ignore[func-returns-value]

    errors: list[str] = []
    for path in unique_paths:
        if shutil.which("udisksctl"):
            result = subprocess.run(
                ["udisksctl", "unmount", "-b", path],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                continue
        result = subprocess.run(
            ["sudo", "umount", path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            errors.append(result.stderr.strip() or f"umount {path} fallito")

    if errors:
        return False, "\n".join(errors)
    return True, ""


def session_dir(base: Path, device: BlockDevice, timestamp: str) -> Path:
    label = device.label or device.name
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
    return base / f"{safe}_{timestamp}"
