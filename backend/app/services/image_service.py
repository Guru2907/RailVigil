"""Handles "someone uploaded photos" (POST /api/media).

All-or-nothing per request: every file is first streamed to a temporary file
and checked (type, size, really an image, zone fits, location valid). Only if
every file passes are media rows created, originals moved into storage and
jobs queued; otherwise every temporary file is deleted and nothing is kept.

The same photo uploaded again (same SHA-256) is not processed twice: the
existing media row is returned with duplicate=True.
"""

import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core import config
from app.core.errors import AppError, PayloadTooLarge, UnsupportedMedia, ValidationFailed
from app.cv.common.zones import ResolvedZone, ZoneResolver
from app.cv.encroachment.pipeline import load_image
from app.db.models.encroachment import Media
from app.db.repositories import encroachment_repository as repo
from app.services import geo_service, image_jobs, storage_service
from app.utils.file_utils import delete_quietly
from app.utils.zone_validation import parse_zone_points

logger = logging.getLogger(__name__)

CHUNK_BYTES = 1024 * 1024
ORIGINAL_STEM = "photo"   # stored as media/<id>/photo<ext>; evidence goes to media/<id>/photo/


@dataclass
class _Checked:
    upload_name: str
    temp_path: Path
    suffix: str
    sha256: str
    width: int
    height: int
    zone: ResolvedZone
    location: geo_service.Location | None
    captured_at: object = None
    duplicate_of: Media | None = None


@dataclass
class IngestResult:
    media: Media
    duplicate: bool = False


def _temp_dir() -> Path:
    d = storage_service.root() / "tmp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _check_extension(name: str | None) -> str:
    suffix = Path(name or "").suffix.lower()
    if suffix not in config.ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(config.ALLOWED_IMAGE_EXTENSIONS))
        raise UnsupportedMedia(f"'{name or 'file'}': unsupported file type '{suffix or 'none'}'. Allowed: {allowed}.")
    return suffix


def _stream_to_temp(upload: UploadFile, suffix: str) -> Path:
    path = _temp_dir() / f"{uuid.uuid4().hex}{suffix}"
    max_bytes = int(config.MAX_IMAGE_MB * 1024 * 1024)
    written = 0
    try:
        with path.open("wb") as f:
            while chunk := upload.file.read(CHUNK_BYTES):
                written += len(chunk)
                if written > max_bytes:
                    raise PayloadTooLarge(
                        f"'{upload.filename}' is too large (maximum {config.MAX_IMAGE_MB:g} MB)."
                    )
                f.write(chunk)
    except BaseException:
        delete_quietly(path)
        raise
    return path


def _parse_zone(zone_raw: str | None, zone_format: str):
    if not zone_raw or not zone_raw.strip():
        return None
    if zone_format == "pixel":
        return parse_zone_points(zone_raw)
    try:
        return json.loads(zone_raw)
    except ValueError as exc:
        raise ValidationFailed("zone_points must be valid JSON, for example [[0,0.6],[1,0.6],[1,1],[0,1]].") from exc


def ingest_images(db: Session, uploads: list[UploadFile], *, zone_raw: str | None = None,
                  zone_format: str = "pixel", zone_sidecar: str | None = None,
                  latitude=None, longitude=None, camera_label: str | None = None) -> list[IngestResult]:
    if not uploads:
        raise ValidationFailed("Upload at least one image.")
    if len(uploads) > config.MAX_IMAGES_PER_UPLOAD:
        raise ValidationFailed(f"At most {config.MAX_IMAGES_PER_UPLOAD} images per upload (got {len(uploads)}).")
    if zone_format not in ("pixel", "normalized"):
        raise ValidationFailed("zone_format must be 'pixel' or 'normalized'.")
    label = (camera_label or "").strip() or None
    if label and len(label) > config.MAX_CAMERA_LABEL_LEN:
        raise ValidationFailed(f"camera_label is too long (maximum {config.MAX_CAMERA_LABEL_LEN} characters).")
    manual_zone = _parse_zone(zone_raw, zone_format)
    if repo.count_unfinished_media(db) >= config.MAX_QUEUED_JOBS:
        raise AppError("The server has too many photos waiting to be processed. Please try again later.", 429)

    checked: list[_Checked] = []
    created: list[Media] = []
    try:
        # 1) check every file; nothing is stored yet
        for upload in uploads:
            suffix = _check_extension(upload.filename)
            temp = _stream_to_temp(upload, suffix)
            checked.append(_Checked(upload.filename or "", temp, suffix, "", 0, 0, None, None))
            item = checked[-1]
            try:
                image = load_image(temp)
            except ValidationFailed as exc:
                raise ValidationFailed(f"'{item.upload_name}': {exc.message}") from exc
            item.height, item.width = image.shape[:2]
            item.sha256 = storage_service.sha256_of(temp)
            try:
                item.zone = ZoneResolver().resolve(
                    item.width, item.height, manual_zone=manual_zone, manual_format=zone_format,
                    sidecar_data=zone_sidecar, camera_label=label,
                )
            except ValidationFailed as exc:
                raise ValidationFailed(f"'{item.upload_name}': {exc.message}") from exc
            item.location = geo_service.resolve_location(temp, latitude, longitude)
            item.captured_at = geo_service.exif_captured_at(temp)
            item.duplicate_of = repo.get_media_by_sha256(db, item.sha256)

        # 2) store: create rows, move originals into storage
        results: list[IngestResult] = []
        in_batch: dict[str, Media] = {}
        for item in checked:
            existing = item.duplicate_of or in_batch.get(item.sha256)
            if existing is not None:
                results.append(IngestResult(existing, duplicate=True))
                continue
            media = Media(
                id=uuid.uuid4().hex, kind="image", status="queued",
                original_filename=item.upload_name[:255], sha256=item.sha256,
                width=item.width, height=item.height, captured_at=item.captured_at,
                latitude=item.location.latitude if item.location else None,
                longitude=item.location.longitude if item.location else None,
                location_source=item.location.source if item.location else "none",
                zone_json=json.dumps(item.zone.as_record()), camera_label=label,
            )
            media.original_key = storage_service.media_key(media.id, f"{ORIGINAL_STEM}{item.suffix}")
            storage_service.put_file(media.original_key, item.temp_path)
            db.add(media)
            in_batch[item.sha256] = media
            created.append(media)
            results.append(IngestResult(media))
        db.commit()
    except BaseException:
        db.rollback()
        for media in created:
            storage_service.delete_prefix(storage_service.media_key(media.id))
        raise
    finally:
        for item in checked:
            delete_quietly(item.temp_path)

    queue = image_jobs.get_image_queue()
    for media in created:
        queue.submit(media.id)
        logger.info("media %s queued (%dx%d, location: %s)", media.id, media.width, media.height,
                    media.location_source)
    return results
