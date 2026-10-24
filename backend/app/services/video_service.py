"""Upload + deferred zone assignment."""

import json
import logging
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core import config
from app.core.errors import AppError, ValidationFailed, ZoneUnavailable
from app.cv.common.zones import ZoneResolver
from app.db.models.video import Video
from app.db.repositories import video_repository
from app.services import geo_service, job_queue
from app.utils.file_utils import check_extension, delete_quietly, save_upload
from app.utils.video_utils import probe_video
from app.utils.zone_validation import parse_zone_points

logger = logging.getLogger(__name__)


def _clean_label(label: str | None) -> str | None:
    label = (label or "").strip()
    if len(label) > config.MAX_CAMERA_LABEL_LEN:
        raise ValidationFailed(
            f"camera_label is too long (maximum {config.MAX_CAMERA_LABEL_LEN} characters)."
        )
    return label or None


def ingest_upload(
    db: Session,
    upload: UploadFile,
    zone_raw: str | None,
    camera_label: str | None,
    zone_sidecar: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> Video:
    label = _clean_label(camera_label)
    location = geo_service.pin_location(latitude, longitude)  # validated before anything is stored
    where = {"latitude": location.latitude, "longitude": location.longitude} if location else {}
    zone_points = parse_zone_points(zone_raw) if zone_raw and zone_raw.strip() else None
    suffix = check_extension(upload.filename)

    # Queue limit only applies to work that will run; awaiting_zone does not count.
    if video_repository.count_unfinished(db) >= config.MAX_QUEUED_JOBS:
        # Still allow zone-less upload if we will park it as awaiting_zone.
        # We only know after resolve — check again below when queuing.
        pass

    path = save_upload(upload, suffix)
    try:
        meta = probe_video(path)
        try:
            zone = ZoneResolver().resolve(
                meta.width,
                meta.height,
                manual_zone=zone_points,
                sidecar_data=zone_sidecar,
                camera_label=label,
            )
        except ZoneUnavailable:
            video = video_repository.create_video(
                db,
                filename=Path(path).name,
                original_filename=(upload.filename or "")[:255],
                zone_json=None,
                camera_label=label,
                fps=meta.fps,
                width=meta.width,
                height=meta.height,
                duration_sec=meta.duration_sec,
                status="awaiting_zone",
                **where,
            )
            logger.info("video %s awaiting_zone", video.id)
            return video

        if video_repository.count_unfinished(db) >= config.MAX_QUEUED_JOBS:
            raise AppError(
                "The server has too many videos waiting to be processed. Please try again later.",
                429,
            )

        video = video_repository.create_video(
            db,
            filename=Path(path).name,
            original_filename=(upload.filename or "")[:255],
            zone_json=json.dumps(zone.as_record()),
            camera_label=label,
            fps=meta.fps,
            width=meta.width,
            height=meta.height,
            duration_sec=meta.duration_sec,
            status="queued",
            **where,
        )
    except BaseException:
        delete_quietly(path)
        raise

    job_queue.get_queue().submit(video.id)
    logger.info(
        "video %s queued (%dx%d, %s)",
        video.id,
        meta.width,
        meta.height,
        f"{meta.duration_sec:.1f}s" if meta.duration_sec else "length unknown",
    )
    return video


def assign_zone(db: Session, video_id: str, zone_points_raw) -> Video:
    video = video_repository.get_video(db, video_id)
    if video is None:
        raise AppError("Video not found", 404)
    if video.status != "awaiting_zone":
        raise AppError(f"Video is '{video.status}', not awaiting a zone.", 409)

    points = parse_zone_points(
        zone_points_raw if isinstance(zone_points_raw, str) else json.dumps(zone_points_raw)
    )
    if video.width is None or video.height is None:
        raise ValidationFailed("Video dimensions are unknown; cannot validate zone.")

    zone = ZoneResolver().resolve(video.width, video.height, manual_zone=points)

    if video_repository.count_unfinished(db) >= config.MAX_QUEUED_JOBS:
        raise AppError(
            "The server has too many videos waiting to be processed. Please try again later.",
            429,
        )

    if not video_repository.assign_zone_and_queue(db, video_id, json.dumps(zone.as_record())):
        raise AppError("Video is not awaiting a zone.", 409)

    job_queue.get_queue().submit(video_id)
    video = video_repository.get_video(db, video_id)
    logger.info("video %s zone assigned -> queued", video_id)
    return video
