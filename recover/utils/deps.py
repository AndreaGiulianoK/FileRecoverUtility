"""Verifica dipendenze di sistema all'avvio."""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field

REQUIRED_TOOLS: dict[str, str] = {
    "ddrescue": "sudo apt install gddrescue",
    "photorec": "sudo apt install testdisk",
    "testdisk": "sudo apt install testdisk",
    "exiftool": "sudo apt install libimage-exiftool-perl",
    "fsck": "sudo apt install e2fsprogs",
    "file": "sudo apt install file",
}


@dataclass
class DepsResult:
    ok: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return len(self.missing) == 0

    def install_hint(self) -> str:
        cmds = {REQUIRED_TOOLS[t] for t in self.missing if t in REQUIRED_TOOLS}
        return "\n".join(sorted(cmds))


def check() -> DepsResult:
    result = DepsResult()
    for tool in REQUIRED_TOOLS:
        if shutil.which(tool):
            result.ok.append(tool)
        else:
            result.missing.append(tool)
    return result
