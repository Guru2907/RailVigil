from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.services import video_service
from app.db.repositories import video_repository


def upload_video(db: Session, video: UploadFile, zone_raw: str, camera_label: str | None):
    return video_service.ingest_upload(db, video, zone_raw, camera_label)


def get_video_status(db: Session, video_id: str):
    video = video_repository.get_video(db, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


def get_all_videos(db: Session):
    return video_repository.list_videos(db)
