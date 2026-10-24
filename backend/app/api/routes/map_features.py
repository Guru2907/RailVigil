from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
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
    layers: str = Query("sites", description="Comma-separated: sites, intrusions"),
    db: Session = Depends(get_db),
):
    """GeoJSON FeatureCollection of encroachment sites and, with
    layers=sites,intrusions, intrusion incidents. Photos without a location
    have no site, and videos without a camera location have no map point;
    neither ever appears here. Site filters (class, severity, status) apply to
    sites only; bbox and the date range apply to both."""
    wanted = set(ctl.split_csv(layers) or ["sites"])
    unknown = wanted - {"sites", "intrusions"}
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown layers: {', '.join(sorted(unknown))}")
    box = ctl.parse_bbox(bbox)
    features = []
    if "sites" in wanted:
        features += ctl.map_features(
            db, status=ctl.split_csv(status), cls=cls, severity=ctl.split_csv(severity), bbox=box,
            reported_from=reported_from, reported_to=reported_to, limit=limit,
        )["features"]
    if "intrusions" in wanted:
        features += ctl.intrusion_features(db, bbox=box, created_from=reported_from, created_to=reported_to,
                                           limit=limit)
    return {"type": "FeatureCollection", "features": features}
