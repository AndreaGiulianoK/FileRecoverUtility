"""Rinomina, dedup, sorting — fase ORGANIZE."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable, Iterator

import magic

from recover.core.session import RecoveredFile
from recover.utils import exif as exif_mod
from recover.utils.hash import sha256

_IMAGE_MIMES = {"image/jpeg", "image/png", "image/tiff", "image/heic", "image/x-canon-cr2",
                "image/x-canon-cr3", "image/x-nikon-nef", "image/x-sony-arw", "image/webp"}
_VIDEO_MIMES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska",
                "video/mp2t", "video/mpeg"}


def _mimetype(path: Path) -> str:
    try:
        return magic.from_file(str(path), mime=True)
    except Exception:
        return "application/octet-stream"


def _subdir(mime: str, cfg: dict[str, Any]) -> str:
    out = cfg.get("output", {})
    if mime in _IMAGE_MIMES:
        return out.get("subdir_images", "images")
    if mime in _VIDEO_MIMES:
        return out.get("subdir_videos", "videos")
    return out.get("subdir_others", "others")


def _make_thumb(src: Path, thumb_path: Path, size: tuple[int, int]) -> str:
    try:
        from PIL import Image
        with Image.open(src) as img:
            img.thumbnail(size)
            img.save(thumb_path, "JPEG", quality=75)
        return thumb_path.name
    except Exception:
        return ""


def run(
    raw_dir: Path,
    session_dir: Path,
    cfg: dict[str, Any],
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> Iterator[RecoveredFile]:
    rec_cfg = cfg.get("recovery", {})
    do_dedup = rec_cfg.get("deduplication", True)
    do_rename = rec_cfg.get("rename_with_exif", True)
    do_thumb = rec_cfg.get("create_thumbnail", True)
    fallback = rec_cfg.get("fallback_name", "recovered")
    thumb_size: tuple[int, int] = tuple(rec_cfg.get("thumbnail_size", [256, 256]))  # type: ignore[assignment]
    out_cfg = cfg.get("output", {})

    thumb_dir = session_dir / ".thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    for sub in [
        out_cfg.get("subdir_images", "images"),
        out_cfg.get("subdir_videos", "videos"),
        out_cfg.get("subdir_others", "others"),
        out_cfg.get("subdir_duplicates", "duplicates"),
    ]:
        (session_dir / sub).mkdir(parents=True, exist_ok=True)

    all_files = [p for p in raw_dir.rglob("*") if p.is_file()]
    seen_hashes: dict[str, Path] = {}
    name_counters: dict[str, int] = {}
    index = 0

    for index, src in enumerate(all_files):
        if progress_cb:
            progress_cb(index, len(all_files), src.name)

        mime = _mimetype(src)
        subdir_name = _subdir(mime, cfg)

        # dedup
        is_dup = False
        file_hash = ""
        if do_dedup:
            file_hash = sha256(src)
            if file_hash in seen_hashes:
                is_dup = True
                subdir_name = out_cfg.get("subdir_duplicates", "duplicates")
            else:
                seen_hashes[file_hash] = src

        # nome file
        ext = src.suffix
        if do_rename and not is_dup:
            exif = exif_mod.read(src)
            base_name = exif_mod.build_filename(exif, index, ext, fallback)
        else:
            base_name = src.name

        # collisione nome
        dest_dir = session_dir / subdir_name
        stem, suf = Path(base_name).stem, Path(base_name).suffix
        final_name = base_name
        count = name_counters.get(base_name, 0)
        if count > 0:
            final_name = f"{stem}_{count:03d}{suf}"
        name_counters[base_name] = count + 1

        dest = dest_dir / final_name
        try:
            shutil.copy2(src, dest)
        except OSError:
            continue

        # thumbnail
        thumb_str = ""
        if do_thumb and mime in _IMAGE_MIMES:
            thumb_path = thumb_dir / (dest.stem + "_thumb.jpg")
            thumb_name = _make_thumb(dest, thumb_path, thumb_size)
            if thumb_name:
                import base64
                data = (thumb_dir / thumb_name).read_bytes()
                thumb_str = "data:image/jpeg;base64," + base64.b64encode(data).decode()

        # stato
        size = dest.stat().st_size
        status = "DUPLICATO" if is_dup else "OK"
        exif_date = ""
        if not is_dup and do_rename:
            try:
                exif_date = exif_mod.read(dest).datetime_original
            except Exception:
                pass

        yield RecoveredFile(
            path=dest,
            name=final_name,
            mimetype=mime,
            size=size,
            date_original=exif_date,
            status=status,
            thumbnail=thumb_str,
        )
