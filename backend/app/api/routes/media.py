from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.controllers import encroachment_controller as ctl
from app.db.database import get_db
from app.db.repositories import encroachment_repository as repo
from app.db.schemas.encroachment import MediaDetailOut, MediaOut, UploadResultOut
from app.services import image_service

router = APIRouter(prefix="/media", tags=["media"])


# Plain `def`: saving and checking uploads is blocking work, so FastAPI runs
# it in its thread pool instead of on the event loop.
@router.post("", response_model=list[UploadResultOut])
def upload_images(
    files: list[UploadFile] = File(..., description="One or more photos (jpg, jpeg, png, webp)"),
    zone_points: str | None = Form(None, description='Railway land in the photo, e.g. "[[0,0.6],[1,0.6],[1,1],[0,1]]"'),
    zone_format: str = Form("pixel", description="'pixel' or 'normalized' (0-1; same zone for photos of any size)"),
    zone_sidecar: str | None = Form(None, description="Zone as a JSON record instead of zone_points"),
    latitude: float | None = Form(None, description="Map pin, used when a photo has no GPS of its own"),
    longitude: float | None = Form(None),
    camera_label: str | None = Form(None),
    db: Session = Depends(get_db),
):
    results = image_service.ingest_images(
        db, files, zone_raw=zone_points, zone_format=zone_format, zone_sidecar=zone_sidecar,
        latitude=latitude, longitude=longitude, camera_label=camera_label,
    )
    return [ctl.media_out(r.media, duplicate=r.duplicate) for r in results]


@router.get("", response_model=list[MediaOut])
def list_images(
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return [ctl.media_out(m) for m in repo.list_media(db, status=status, limit=limit, offset=offset)]


@router.get("/{media_id}", response_model=MediaDetailOut)
def get_image(media_id: str, db: Session = Depends(get_db)):
    return ctl.media_detail_out(ctl.get_media_or_404(db, media_id))


@router.get("/{media_id}/original")
def get_original(media_id: str, db: Session = Depends(get_db)):
    return ctl.media_file(db, media_id, "original")


@router.get("/{media_id}/annotated")
def get_annotated(media_id: str, db: Session = Depends(get_db)):
    return ctl.media_file(db, media_id, "annotated")
