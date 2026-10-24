from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.controllers import video_controller
from app.db.database import get_db
from app.db.repositories import video_repository
from app.db.schemas.video import VideoDetailOut, VideoOut, ZoneAssignIn

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("", response_model=VideoOut)
def upload_video(
    video: UploadFile = File(...),
    zone_points: str | None = Form(None),
    zone_sidecar: str | None = Form(None),
    camera_label: str | None = Form(None),
    latitude: float | None = Form(None, description="Camera location (optional); incidents are shown on the map"),
    longitude: float | None = Form(None),
    db: Session = Depends(get_db),
):
    return video_controller.upload_video(db, video, zone_points, camera_label, zone_sidecar, latitude, longitude)


@router.get("", response_model=list[VideoOut])
def list_videos(db: Session = Depends(get_db)):
    return video_controller.get_all_videos(db)


@router.get("/{video_id}", response_model=VideoDetailOut)
def get_video(video_id: str, db: Session = Depends(get_db)):
    return video_controller.get_video_status(db, video_id)


@router.put("/{video_id}/zone", response_model=VideoOut)
def put_zone(video_id: str, body: ZoneAssignIn, db: Session = Depends(get_db)):
    return video_controller.assign_zone(db, video_id, body.zone_points)


@router.get("/{video_id}/file")
def get_annotated_video(video_id: str, db: Session = Depends(get_db)):
    video = video_repository.get_video(db, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status != "done" or not video.output_video_path:
        raise HTTPException(status_code=409, detail=f"Video is '{video.status}', not ready yet")
    return FileResponse(video.output_video_path, media_type="video/mp4")
