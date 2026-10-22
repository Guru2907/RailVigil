"""Where uploaded media and evidence files live (ADR-0002: files in storage,
only their keys in the database).

A key is a relative path such as "media/<id>/original.jpg". This module is
the only place that turns keys into real paths, so moving to object storage
(MinIO/S3) later means replacing this module, not its callers. Today files
live on local disk under STORAGE_DIR.
"""

import hashlib
import shutil
from pathlib import Path, PurePosixPath

from app.core import config

CHUNK_BYTES = 1024 * 1024


class InvalidKey(ValueError):
    """The key is absolute or tries to leave the storage folder."""


def root() -> Path:
    return Path(config.STORAGE_DIR)


def _clean(key: str) -> PurePosixPath:
    rel = PurePosixPath(key)
    if rel.is_absolute() or not rel.parts or ".." in rel.parts or ":" in rel.parts[0]:
        raise InvalidKey(f"invalid storage key: {key!r}")
    return rel


def path_for(key: str) -> Path:
    """Absolute local path of a key (the file may not exist yet)."""
    return root().joinpath(*_clean(key).parts)


def media_key(media_id: str, *parts: str) -> str:
    """Key inside one media item's folder, e.g. media_key(id, "crops", "01.jpg")."""
    return str(PurePosixPath("media", media_id, *parts))


def put_file(key: str, source: Path | str) -> str:
    """Copy a local file into storage under `key`; returns the key."""
    target = path_for(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return key


def put_bytes(key: str, data: bytes) -> str:
    target = path_for(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return key


def exists(key: str | None) -> bool:
    return bool(key) and path_for(key).is_file()


def delete_prefix(key: str) -> None:
    """Remove a folder of keys (e.g. all files of one media item); missing is fine."""
    shutil.rmtree(path_for(key), ignore_errors=True)


def sha256_of(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()
