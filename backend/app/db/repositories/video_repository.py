"""Plain database access for Video rows. No business logic here --
that belongs in services/video_service.py. This file only knows how to
create/read/update Video records."""

from sqlalchemy.orm import Session

from app.db.models.video import Video


def create_video(db: Session, filename: str, original_filename: str,
                  zone_json: str, camera_label: str | None = None) -> Video:
    video = Video(
        filename=filename,
        original_filename=original_filename,
        zone_json=zone_json,
        camera_label=camera_label,
        status="uploaded",
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