from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers import encroachment_controller as ctl
from app.db.database import get_db
from app.db.repositories import encroachment_repository as repo
from app.db.schemas.encroachment import ReportDetailOut, ReportOut

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def list_reports(
    reason: str | None = None,
    site_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    reports = repo.list_reports(db, reason=reason, site_id=site_id, created_from=created_from,
                                created_to=created_to, limit=limit, offset=offset)
    return [ctl.report_out(r) for r in reports]


@router.get("/{report_no}", response_model=ReportDetailOut)
def get_report(report_no: str, db: Session = Depends(get_db)):
    return ctl.report_detail(db, report_no)
