import json

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.schemas.video import VideoOut, VideoDetailOut
from app.controllers import video_controller

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("", response_model=VideoOut)
async def upload_video(
    video: UploadFile = File(...),
    zone_points: str = Form(...),          # JSON string: "[[10,10],[200,10],[200,150],[10,150]]"
    camera_label: str | None = Form(None),
    db: Session = Depends(get_db),
):
    points = json.loads(zone_points)
    return video_controller.upload_video(db, video, points, camera_label)


@router.get("", response_model=list[VideoOut])
def list_videos(db: Session = Depends(get_db)):
    return video_controller.get_all_videos(db)


@router.get("/{video_id}", response_model=VideoDetailOut)
def get_video(video_id: str, db: Session = Depends(get_db)):
    return video_controller.get_video_status(db, video_id)


@router.get("/{video_id}/file")
def get_annotated_video(video_id: str, db: Session = Depends(get_db)):
    video = video_controller.get_video_status(db, video_id)
    if video.status != "done" or not video.output_video_path:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=f"Video is '{video.status}', not ready yet")
    return FileResponse(video.output_video_path, media_type="video/mp4")