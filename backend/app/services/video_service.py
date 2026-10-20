"""Handles "someone uploaded a video":

1. Validate everything cheap BEFORE touching the disk (label, zone shape,
   file type), then stream the file to disk with a size cap.
2. Open it to check it is really a video and that the zone fits its frame.
3. Create the Video row as `queued` and hand its id to the job queue.

The request returns as soon as that is done. The slow part (YOLO) runs
later in a worker -- see job_queue.py (threads) and job_runner.py (the job).
Any failure after the file was saved deletes the file again, so rejected
uploads never pile up on disk.
"""

import json
import logging
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core import config
from app.core.errors import AppError, ValidationFailed
from app.cv.common.zones import ZoneResolver
from app.db.models.video import Video
from app.db.repositories import video_repository
from app.services import job_queue
from app.utils.file_utils import check_extension, delete_quietly, save_upload
from app.utils.video_utils import probe_video
from app.utils.zone_validation import parse_zone_points

logger = logging.getLogger(__name__)


def _clean_label(label: str | None) -> str | None:
    label = (label or "").strip()
    if len(label) > config.MAX_CAMERA_LABEL_LEN:
        raise ValidationFailed(f"camera_label is too long (maximum {config.MAX_CAMERA_LABEL_LEN} characters).")
    return label or None


def ingest_upload(db: Session, upload: UploadFile, zone_raw: str | None,
                  camera_label: str | None, zone_sidecar: str | None = None) -> Video:
    label = _clean_label(camera_label)
    zone_points = parse_zone_points(zone_raw) if zone_raw and zone_raw.strip() else None
    suffix = check_extension(upload.filename)

    if video_repository.count_unfinished(db) >= config.MAX_QUEUED_JOBS:
        raise AppError("The server has too many videos waiting to be processed. Please try again later.", 429)

    path = save_upload(upload, suffix)
    try:
        meta = probe_video(path)
        zone = ZoneResolver().resolve(
            meta.width, meta.height, manual_zone=zone_points,
            sidecar_data=zone_sidecar, camera_label=label,
        )
        video = video_repository.create_video(
            db,
            filename=Path(path).name,
            original_filename=(upload.filename or "")[:255],
            zone_json=json.dumps(zone.as_record()),
            camera_label=label,
            fps=meta.fps, width=meta.width, height=meta.height, duration_sec=meta.duration_sec,
        )
    except BaseException:
        delete_quietly(path)   # a rejected upload must not leave its file behind
        raise

    job_queue.get_queue().submit(video.id)
    logger.info("video %s queued (%dx%d, %s)", video.id, meta.width, meta.height,
                f"{meta.duration_sec:.1f}s" if meta.duration_sec else "length unknown")
    return video
