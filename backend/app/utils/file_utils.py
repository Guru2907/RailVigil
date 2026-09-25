"""Small helper for saving uploaded files to disk with a safe, unique
name -- keeps this logic out of both the route and the service."""

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core import config


def save_upload(upload: UploadFile, subdir: str = "raw") -> str:
    """Streams an uploaded file into DATA_DIR/<subdir>/ under a
    collision-proof name. Returns the saved path."""
    dest_dir = Path(config.DATA_DIR) / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(upload.filename or "").suffix
    dest_path = dest_dir / f"{uuid.uuid4().hex[:12]}{suffix}"

    with dest_path.open("wb") as f:
        f.write(upload.file.read())

    return str(dest_path)