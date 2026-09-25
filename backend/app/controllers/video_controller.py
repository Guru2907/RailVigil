import json

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.services import video_service
from app.db.repositories import video_repository
from app.utils.file_utils import save_upload


def upload_video(db: Session, video: UploadFile, zone_points: list, camera_label: str | None):
    video_path = save_upload(video, subdir="raw")
    zone_json = json.dumps({"points": zone_points})
    return video_service.start_video_processing(
        db, video_path=video_path, original_filename=video.filename,
        zone_points=zone_points, zone_json=zone_json, camera_label=camera_label,
    )


def get_video_status(db: Session, video_id: str):
    video = video_repository.get_video(db, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


def get_all_videos(db: Session):
    return video_repository.list_videos(db)