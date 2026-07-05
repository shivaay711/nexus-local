"""Upload/import safety: extension + size limits, path-traversal rejection,
and zip-bomb-aware archive extraction."""
from __future__ import annotations

import zipfile
from pathlib import Path

from ..config import settings

MAX_ARCHIVE_MEMBERS = 2000
MAX_ARCHIVE_TOTAL_UNCOMPRESSED = 500 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200  # per member


class FileValidationError(ValueError):
    pass


def validate_import_path(path: Path) -> Path:
    p = Path(path).resolve()
    if not p.exists() or not p.is_file():
        raise FileValidationError(f"Not a file: {path}")
    if p.suffix.lower() not in settings.allowed_extensions and p.suffix.lower() != ".zip":
        raise FileValidationError(f"Unsupported file type: {p.suffix}")
    if p.stat().st_size > settings.max_file_size_bytes:
        raise FileValidationError("File exceeds size limit")
    if p.stat().st_size == 0:
        raise FileValidationError("Empty file")
    return p


def safe_extract_zip(archive: Path, dest: Path) -> list[Path]:
    """Extract a ZIP defensively. Rejects traversal names, absolute paths,
    symlinks, oversized totals, and suspicious compression ratios."""
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    total = 0
    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
        if len(infos) > MAX_ARCHIVE_MEMBERS:
            raise FileValidationError("Archive has too many members")
        for info in infos:
            name = info.filename
            if name.endswith("/"):
                continue
            target = (dest / name).resolve()
            if not str(target).startswith(str(dest)):
                raise FileValidationError(f"Path traversal attempt: {name}")
            if (info.external_attr >> 16) & 0o120000 == 0o120000:
                raise FileValidationError(f"Symlink in archive: {name}")
            if info.compress_size > 0 and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                raise FileValidationError(f"Suspicious compression ratio: {name}")
            total += info.file_size
            if total > MAX_ARCHIVE_TOTAL_UNCOMPRESSED:
                raise FileValidationError("Archive expands beyond safety limit")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                out.write(src.read())
            extracted.append(target)
    return extracted
