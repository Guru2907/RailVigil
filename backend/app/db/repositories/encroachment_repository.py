"""Database access for the encroachment tables. No business rules here (those
live in services/); job-state changes are single guarded UPDATEs, like
video_repository, so two workers can never both claim the same photo."""

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.models.encroachment import EncroachmentFinding, EncroachmentSite, Media, Report

UNFINISHED = ("queued", "processing")


# --- media (photos) and their job state ----------------------------------------

def get_media(db: Session, media_id: str) -> Media | None:
    return db.get(Media, media_id)


def get_media_by_sha256(db: Session, sha256: str) -> Media | None:
    return db.execute(select(Media).where(Media.sha256 == sha256)).scalar_one_or_none()


def list_media(db: Session, status: str | None = None, limit: int = 100, offset: int = 0) -> list[Media]:
    q = select(Media).order_by(Media.created_at.desc()).limit(limit).offset(offset)
    if status:
        q = q.where(Media.status == status)
    return list(db.execute(q).scalars())


def count_unfinished_media(db: Session) -> int:
    return db.execute(select(func.count()).select_from(Media).where(Media.status.in_(UNFINISHED))).scalar_one()


def list_unfinished_media(db: Session) -> list[Media]:
    return list(db.execute(
        select(Media).where(Media.status.in_(UNFINISHED)).order_by(Media.created_at.asc())
    ).scalars())


def claim_media(db: Session, media_id: str) -> bool:
    """queued -> processing (counting one attempt); True only for the claimer."""
    result = db.execute(
        update(Media).where(Media.id == media_id, Media.status == "queued")
        .values(status="processing", attempts=Media.attempts + 1, error=None)
    )
    db.commit()
    return result.rowcount == 1


def requeue_media(db: Session, media_id: str, refund_attempt: bool = False) -> None:
    values = {"status": "queued"}
    if refund_attempt:
        values["attempts"] = Media.attempts - 1
    db.execute(update(Media).where(Media.id == media_id, Media.status == "processing").values(**values))
    db.commit()


def mark_media_failed(db: Session, media_id: str, message: str) -> None:
    db.execute(
        update(Media).where(Media.id == media_id, Media.status.in_(UNFINISHED))
        .values(status="failed", error=message)
    )
    db.commit()


# --- findings ---------------------------------------------------------------------

def get_finding(db: Session, finding_id: str) -> EncroachmentFinding | None:
    return db.get(EncroachmentFinding, finding_id)


def list_findings(db: Session, cls: str | None = None, severity: str | None = None,
                  media_id: str | None = None, site_id: str | None = None,
                  limit: int = 100, offset: int = 0) -> list[EncroachmentFinding]:
    q = select(EncroachmentFinding).order_by(EncroachmentFinding.created_at.desc()).limit(limit).offset(offset)
    if cls:
        q = q.where(EncroachmentFinding.cls == cls)
    if severity:
        q = q.where(EncroachmentFinding.severity == severity)
    if media_id:
        q = q.where(EncroachmentFinding.media_id == media_id)
    if site_id:
        q = q.where(EncroachmentFinding.site_id == site_id)
    return list(db.execute(q).scalars())


# --- sites --------------------------------------------------------------------------

def get_site(db: Session, site_id: str) -> EncroachmentSite | None:
    return db.get(EncroachmentSite, site_id)


def list_sites(db: Session, status: list[str] | None = None, cls: str | None = None,
               severity: list[str] | None = None, bbox: tuple[float, float, float, float] | None = None,
               reported_from: datetime | None = None, reported_to: datetime | None = None,
               limit: int = 500, offset: int = 0) -> list[EncroachmentSite]:
    """bbox = (min_lon, min_lat, max_lon, max_lat), as in GeoJSON."""
    q = select(EncroachmentSite).order_by(EncroachmentSite.last_reported_at.desc()).limit(limit).offset(offset)
    if status:
        q = q.where(EncroachmentSite.status.in_(status))
    if cls:
        q = q.where(EncroachmentSite.cls == cls)
    if severity:
        q = q.where(EncroachmentSite.max_severity.in_(severity))
    if bbox:
        min_lon, min_lat, max_lon, max_lat = bbox
        q = q.where(EncroachmentSite.longitude.between(min_lon, max_lon),
                    EncroachmentSite.latitude.between(min_lat, max_lat))
    if reported_from:
        q = q.where(EncroachmentSite.last_reported_at >= reported_from)
    if reported_to:
        q = q.where(EncroachmentSite.last_reported_at <= reported_to)
    return list(db.execute(q).scalars())


def site_reports(db: Session, site_id: str) -> list[Report]:
    return list(db.execute(
        select(Report).where(Report.site_id == site_id).order_by(Report.created_at.desc())
    ).scalars())


def latest_report_numbers(db: Session, site_ids: list[str]) -> dict[str, str]:
    """site id -> newest report number, for many sites in one query."""
    if not site_ids:
        return {}
    rows = db.execute(
        select(Report.site_id, Report.report_no, Report.created_at)
        .where(Report.site_id.in_(site_ids)).order_by(Report.created_at.asc())
    ).all()
    return {site_id: report_no for site_id, report_no, _ in rows}   # last one wins = newest


def latest_findings(db: Session, site_ids: list[str]) -> dict[str, EncroachmentFinding]:
    """site id -> its most recent finding (for map thumbnails)."""
    if not site_ids:
        return {}
    rows = db.execute(
        select(EncroachmentFinding).where(EncroachmentFinding.site_id.in_(site_ids))
        .order_by(EncroachmentFinding.created_at.asc())
    ).scalars()
    return {f.site_id: f for f in rows}


# --- reports --------------------------------------------------------------------------

def get_report_by_no(db: Session, report_no: str) -> Report | None:
    return db.execute(select(Report).where(Report.report_no == report_no)).scalar_one_or_none()


def list_reports(db: Session, reason: str | None = None, site_id: str | None = None,
                 created_from: datetime | None = None, created_to: datetime | None = None,
                 limit: int = 100, offset: int = 0) -> list[Report]:
    q = select(Report).order_by(Report.created_at.desc()).limit(limit).offset(offset)
    if reason:
        q = q.where(Report.reason == reason)
    if site_id:
        q = q.where(Report.site_id == site_id)
    if created_from:
        q = q.where(Report.created_at >= created_from)
    if created_to:
        q = q.where(Report.created_at <= created_to)
    return list(db.execute(q).scalars())
