from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers import encroachment_controller as ctl
from app.db.database import get_db
from app.db.repositories import encroachment_repository as repo
from app.db.schemas.encroachment import FindingOut, SiteDetailOut, SiteOut, SitePatch

router = APIRouter(prefix="/encroachment", tags=["encroachment"])


@router.get("/findings", response_model=list[FindingOut])
def list_findings(
    cls: str | None = None,
    severity: str | None = None,
    media_id: str | None = None,
    site_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    findings = repo.list_findings(db, cls=cls, severity=severity, media_id=media_id, site_id=site_id,
                                  limit=limit, offset=offset)
    return [ctl.finding_out(f) for f in findings]


@router.get("/findings/{finding_id}/crop")
def get_finding_crop(finding_id: str, db: Session = Depends(get_db)):
    return ctl.finding_crop(db, finding_id)


@router.get("/sites", response_model=list[SiteOut])
def list_sites(
    status: str | None = Query(None, description="Comma-separated, e.g. reported,under_review"),
    cls: str | None = None,
    severity: str | None = Query(None, description="Comma-separated worst severities, e.g. high,critical"),
    bbox: str | None = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    reported_from: datetime | None = None,
    reported_to: datetime | None = None,
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return ctl.list_sites(
        db, status=ctl.split_csv(status), cls=cls, severity=ctl.split_csv(severity), bbox=ctl.parse_bbox(bbox),
        reported_from=reported_from, reported_to=reported_to, limit=limit, offset=offset,
    )


@router.get("/sites/{site_id}", response_model=SiteDetailOut)
def get_site(site_id: str, db: Session = Depends(get_db)):
    return ctl.site_detail(db, site_id)


@router.patch("/sites/{site_id}", response_model=SiteDetailOut)
def update_site(site_id: str, body: SitePatch, db: Session = Depends(get_db)):
    """Review workflow: reported -> under_review -> verified -> action_taken ->
    resolved, or -> false_positive. Invalid moves return 409."""
    return ctl.update_site_status(db, site_id, body.status, body.note, body.actor)
