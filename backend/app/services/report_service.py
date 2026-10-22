"""Numbered reports: RV-ENC-2026-000001, RV-INT-2026-000001, ...

Numbers come from one counter row per kind and year, incremented with a
single UPDATE ... RETURNING inside the caller's transaction. PostgreSQL locks
that row until the transaction ends and SQLite allows one writer at a time,
so two jobs finishing together can never get the same number. A rolled-back
transaction gives its number back, so numbers have no gaps from failures.
"""

from datetime import UTC, datetime

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.encroachment import Report, ReportCounter

PREFIXES = {"encroachment": "RV-ENC", "intrusion": "RV-INT"}
REASONS = {"new_site", "critical_finding", "re_encroached"}


def format_report_no(kind: str, year: int, number: int) -> str:
    return f"{PREFIXES[kind]}-{year}-{number:06d}"


def next_report_no(db: Session, kind: str = "encroachment", year: int | None = None) -> str:
    if kind not in PREFIXES:
        raise ValueError(f"unknown report kind {kind!r}")
    year = year or datetime.now(UTC).year

    exists = db.execute(
        select(ReportCounter.id).where(ReportCounter.kind == kind, ReportCounter.year == year)
    ).first()
    if exists is None:
        # First report of this kind this year. Another transaction may create
        # the row at the same moment; the savepoint lets us ignore that.
        try:
            with db.begin_nested():
                db.execute(insert(ReportCounter).values(kind=kind, year=year, last_value=0))
        except IntegrityError:
            pass

    number = db.execute(
        update(ReportCounter)
        .where(ReportCounter.kind == kind, ReportCounter.year == year)
        .values(last_value=ReportCounter.last_value + 1)
        .returning(ReportCounter.last_value)
    ).scalar_one()
    return format_report_no(kind, year, number)


def issue_report(db: Session, reason: str, *, site=None, media=None, finding=None,
                 kind: str = "encroachment") -> Report:
    """Create a report row in the caller's transaction (not committed here)."""
    if reason not in REASONS:
        raise ValueError(f"unknown report reason {reason!r}")
    report = Report(
        report_no=next_report_no(db, kind),
        kind=kind,
        reason=reason,
        site_id=getattr(site, "id", None),
        media_id=getattr(media, "id", None),
        finding_id=getattr(finding, "id", None),
    )
    db.add(report)
    db.flush()
    return report
