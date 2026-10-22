"""Counts for the dashboard (GET /api/stats/summary), for both modules."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.encroachment import EncroachmentFinding, EncroachmentSite, Media, Report
from app.db.models.incident import Incident
from app.db.models.video import Video
from app.services.site_service import CLOSED


def _counts(db: Session, column) -> dict[str, int]:
    return {key: n for key, n in db.execute(select(column, func.count()).group_by(column)).all()}


def summary(db: Session) -> dict:
    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def reports_since(since):
        return db.execute(select(func.count()).select_from(Report).where(Report.created_at >= since)).scalar_one()

    sites_by_status = _counts(db, EncroachmentSite.status)
    findings_by_severity = _counts(db, EncroachmentFinding.severity)
    encroachment = {
        "photos_by_status": _counts(db, Media.status),
        "findings_total": sum(findings_by_severity.values()),
        "findings_by_class": _counts(db, EncroachmentFinding.cls),
        "findings_by_severity": findings_by_severity,
        "findings_without_location": db.execute(
            select(func.count()).select_from(EncroachmentFinding).where(EncroachmentFinding.site_id.is_(None))
        ).scalar_one(),
        "sites_total": sum(sites_by_status.values()),
        "sites_open": sum(n for status, n in sites_by_status.items() if status not in CLOSED),
        "sites_by_status": sites_by_status,
        "critical_open_sites": db.execute(
            select(func.count()).select_from(EncroachmentSite)
            .where(EncroachmentSite.max_severity == "critical", EncroachmentSite.status.notin_(CLOSED))
        ).scalar_one(),
        "reports_total": db.execute(select(func.count()).select_from(Report)).scalar_one(),
        "reports_today": reports_since(today),
        "reports_last_7_days": reports_since(now - timedelta(days=7)),
    }

    incidents_by_severity = _counts(db, Incident.severity)
    intrusion = {
        "videos_by_status": _counts(db, Video.status),
        "incidents_total": sum(incidents_by_severity.values()),
        "incidents_by_severity": incidents_by_severity,
        "incidents_by_type": _counts(db, Incident.event_type),
    }
    return {"encroachment": encroachment, "intrusion": intrusion}
