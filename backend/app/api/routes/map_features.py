from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers import encroachment_controller as ctl
from app.db.database import get_db

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/features")
def map_features(
    bbox: str | None = Query(None, description="min_lon,min_lat,max_lon,max_lat (the visible map area)"),
    cls: str | None = None,
    severity: str | None = Query(None, description="Comma-separated, e.g. high,critical"),
    status: str | None = Query(None, description="Comma-separated, e.g. reported,under_review"),
    reported_from: datetime | None = None,
    reported_to: datetime | None = None,
    limit: int = Query(2000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """GeoJSON FeatureCollection of encroachment sites. Photos without a
    location have no site and therefore never appear here."""
    return ctl.map_features(
        db, status=ctl.split_csv(status), cls=cls, severity=ctl.split_csv(severity), bbox=ctl.parse_bbox(bbox),
        reported_from=reported_from, reported_to=reported_to, limit=limit,
    )
