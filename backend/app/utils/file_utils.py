"""Helpers for saving uploaded files to disk with a safe, unique name --
keeps this logic out of both the route and the service."""

import logging
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core import config
from app.core.errors import PayloadTooLarge, UnsupportedMedia

logger = logging.getLogger(__name__)

CHUNK_BYTES = 1024 * 1024  # copy the upload 1 MB at a time


def raw_dir() -> Path:
    return Path(config.DATA_DIR) / "raw"


def raw_video_path(filename: str) -> Path:
    """Where an uploaded video lives on disk. Only the bare filename is
    stored in the database, so this is the single place that knows the
    folder."""
    return raw_dir() / filename


def check_extension(original_name: str | None) -> str:
    """Returns the lower-cased extension, or raises UnsupportedMedia.
    Done BEFORE reading the body, so a wrong file type costs nothing."""
    suffix = Path(original_name or "").suffix.lower()
    if suffix not in config.ALLOWED_VIDEO_EXTENSIONS:
        allowed = ", ".join(sorted(config.ALLOWED_VIDEO_EXTENSIONS))
        raise UnsupportedMedia(f"Unsupported file type '{suffix or 'none'}'. Allowed: {allowed}.")
    return suffix


def save_upload(upload: UploadFile, suffix: str) -> str:
    """Streams an uploaded file into DATA_DIR/raw/ under a collision-proof
    name and returns the saved path.

    The file is copied in 1 MB chunks while counting bytes, so (a) memory use
    stays flat however big the upload is, and (b) an oversized upload is
    stopped as soon as it crosses the limit instead of after it has all
    arrived. A partly written file is deleted on any failure."""
    raw_dir().mkdir(parents=True, exist_ok=True)
    dest_path = raw_dir() / f"{uuid.uuid4().hex[:12]}{suffix}"
    max_bytes = int(config.MAX_UPLOAD_MB * 1024 * 1024)
    written = 0

    try:
        with dest_path.open("wb") as f:
            while chunk := upload.file.read(CHUNK_BYTES):
                written += len(chunk)
                if written > max_bytes:
                    raise PayloadTooLarge(f"File is too large (maximum {config.MAX_UPLOAD_MB:g} MB).")
                f.write(chunk)
    except BaseException:
        delete_quietly(dest_path)
        raise

    return str(dest_path)


def delete_quietly(path: str | Path) -> None:
    """Remove a file if it exists; never raise (used in cleanup paths where
    a second error would hide the first)."""
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        logger.warning("could not delete %s", path, exc_info=True)
