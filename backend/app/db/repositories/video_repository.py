"""Plain database access for Video rows. No business logic here --
that belongs in services/video_service.py. This file only knows how to
create/read/update Video records.

The job-state helpers (claim, progress, requeue, fail) are written as
single UPDATE statements with a status guard (`WHERE status = ...`) rather
than "load the row, change it, save it". That makes each transition atomic:
if two threads race for the same video, the database lets exactly one of
them win, with no locking code on our side.
"""

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models.video import Video


def create_video(db: Session, filename: str, original_filename: str,
                  zone_json: str, camera_label: str | None = None,
                  fps: float | None = None, width: int | None = None,
                  height: int | None = None, duration_sec: float | None = None) -> Video:
    video = Video(
        filename=filename,
        original_filename=original_filename,
        zone_json=zone_json,
        camera_label=camera_label,
        fps=fps, width=width, height=height, duration_sec=duration_sec,
        status="queued",
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def get_video(db: Session, video_id: str) -> Video | None:
    return db.query(Video).filter(Video.id == video_id).first()


def list_videos(db: Session) -> list[Video]:
    return db.query(Video).order_by(Video.created_at.desc()).all()


def update_video_status(db: Session, video_id: str, status: str, **fields) -> Video | None:
    video = get_video(db, video_id)
    if video is None:
        return None
    video.status = status
    for key, value in fields.items():
        setattr(video, key, value)
    db.commit()
    db.refresh(video)
    return video


# --- job-state transitions ---------------------------------------------------

def claim_video(db: Session, video_id: str) -> bool:
    """queued -> processing, and count this as one attempt. Returns True
    only for the caller that actually made the change, so a video that was
    submitted twice (or picked up by two workers) is processed once."""
    result = db.execute(
        update(Video)
        .where(Video.id == video_id, Video.status == "queued")
        .values(status="processing", attempts=Video.attempts + 1, progress=0.0, error=None)
    )
    db.commit()
    return result.rowcount == 1


def update_progress(db: Session, video_id: str, percent: float) -> None:
    """Only moves the bar while the video is still `processing`, so a late
    progress write can't overwrite a finished/failed row."""
    db.execute(
        update(Video)
        .where(Video.id == video_id, Video.status == "processing")
        .values(progress=percent)
    )
    db.commit()


def requeue_video(db: Session, video_id: str, refund_attempt: bool = False) -> None:
    """processing -> queued. `refund_attempt` is used when the job was
    interrupted by a clean shutdown, which isn't the video's fault and so
    shouldn't count towards MAX_JOB_ATTEMPTS."""
    values = {"status": "queued", "progress": 0.0}
    if refund_attempt:
        values["attempts"] = Video.attempts - 1
    db.execute(
        update(Video)
        .where(Video.id == video_id, Video.status == "processing")
        .values(**values)
    )
    db.commit()


def mark_failed(db: Session, video_id: str, message: str) -> None:
    db.execute(
        update(Video)
        .where(Video.id == video_id, Video.status.in_(["queued", "processing"]))
        .values(status="failed", error=message)
    )
    db.commit()


def mark_done(db: Session, video_id: str, output_video_path: str, commit: bool = True) -> None:
    db.execute(
        update(Video)
        .where(Video.id == video_id)
        .values(status="done", progress=100.0, error=None, output_video_path=output_video_path)
    )
    if commit:
        db.commit()


def count_unfinished(db: Session) -> int:
    return db.query(Video).filter(Video.status.in_(["queued", "processing"])).count()


def list_unfinished(db: Session) -> list[Video]:
    """Videos that still need work, oldest first. Used at startup to rebuild
    the in-memory queue from the database (the DB is the source of truth;
    the queue is just a convenience)."""
    return (
        db.query(Video)
        .filter(Video.status.in_(["queued", "processing"]))
        .order_by(Video.created_at.asc())
        .all()
    )
