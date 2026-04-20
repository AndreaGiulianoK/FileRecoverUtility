"""Generazione report HTML — fase REPORT."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from recover.core.session import RecoveredFile, Session

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_VERSION = "0.1"


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n //= 1024
    return f"{n:.0f} TB"


def generate(session: Session) -> Path:
    assert session.session_dir is not None

    files = session.recovered_files
    images = [f for f in files if f.mimetype.startswith("image/")]
    videos = [f for f in files if f.mimetype.startswith("video/")]
    others = [f for f in files if not f.mimetype.startswith(("image/", "video/"))]
    dups   = [f for f in files if f.status == "DUPLICATO"]
    no_meta = [f for f in files if "_no_meta" in f.name]
    corrupted = [f for f in files if f.status in ("PARZIALE", "CORROTTO")]

    stats = {
        "total": len(files),
        "images": len(images),
        "videos": len(videos),
        "others": len(others),
        "duplicates": len(dups),
        "no_meta": len(no_meta),
        "corrupted": len(corrupted),
    }

    file_rows = [
        {
            "name": f.name,
            "mimetype": f.mimetype,
            "size": _human(f.size),
            "date_original": f.date_original,
            "status": f.status,
            "status_class": f.status_class,
            "thumbnail": f.thumbnail,
        }
        for f in files
    ]

    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)
    tmpl = env.get_template("report.html.j2")

    html = tmpl.render(
        session={
            "device": f"{session.device.path} ({session.device.label or session.device.name})",
            "date": session.timestamp,
            "mode": {"A": "Recupero file cancellati (testdisk)",
                     "B": "Recupero filesystem corrotto (photorec)",
                     "C": "Solo imaging (ddrescue)"}.get(session.mode, session.mode),
            "image_sha256": session.image_sha256 or "—",
        },
        stats=stats,
        files=file_rows,
        version=_VERSION,
        tool_versions=session.tool_versions,
    )

    report_path = session.session_dir / "report.html"
    report_path.write_text(html, encoding="utf-8")
    return report_path
