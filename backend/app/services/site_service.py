"""Encroachment sites: the same place reported again and again.

A finding from a located photo joins the nearest site of the same class
within ENC_SITE_RADIUS_M; otherwise it starts a new site. A resolved site
that is found again is reopened as re-encroached -- repeat reports are the
evidence of persistence. A site an officer marked false_positive keeps that
status (the finding is still attached, so the record stays complete), so the
same harmless object does not reopen it on every photo.

Distance search: PostGIS (ST_DWithin on geography, backed by the spatial
index from migration 9944f93555d3) on PostgreSQL; a bounding box plus the
haversine formula on SQLite.

Review workflow (changes are written to site_history):

    reported -> under_review -> verified -> action_taken -> resolved
         \\------------\\-> false_positive
    resolved / false_positive -> reported   (reopen)
"""

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core import config
from app.core.errors import ValidationFailed
from app.cv.encroachment.rules import SEVERITY_ORDER
from app.db.models.encroachment import EncroachmentFinding, EncroachmentSite, SiteHistory
from app.services.geo_service import Location, distance_m

STATUSES = ("reported", "under_review", "verified", "action_taken", "resolved", "false_positive")
CLOSED = frozenset({"resolved", "false_positive"})
TRANSITIONS = {
    "reported": {"under_review", "false_positive"},
    "under_review": {"verified", "false_positive", "reported"},
    "verified": {"action_taken", "resolved"},
    "action_taken": {"resolved", "verified"},
    "resolved": {"reported"},
    "false_positive": {"reported"},
}
METRES_PER_DEGREE_LAT = 111_320.0

# Same expression as the spatial index, so PostgreSQL can use it.
_NEAREST_SITE_PG = text("""
    SELECT id FROM encroachment_sites
    WHERE cls = :cls
      AND ST_DWithin(geography(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)),
                     geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)), :radius)
    ORDER BY ST_Distance(geography(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)),
                         geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)))
    LIMIT 1
""")


class InvalidTransition(ValidationFailed):
    status_code = 409


@dataclass
class SiteAssignment:
    site: EncroachmentSite
    created: bool
    reopened: bool


def _worse(a: str, b: str) -> str:
    return a if SEVERITY_ORDER.index(a) >= SEVERITY_ORDER.index(b) else b


def find_nearby_site(db: Session, cls: str, lat: float, lon: float,
                     radius_m: float | None = None) -> EncroachmentSite | None:
    """Nearest site of this class within the radius, open or closed."""
    radius = config.ENC_SITE_RADIUS_M if radius_m is None else radius_m
    if db.get_bind().dialect.name == "postgresql":
        site_id = db.execute(_NEAREST_SITE_PG, {"cls": cls, "lat": lat, "lon": lon, "radius": radius}).scalar()
        return db.get(EncroachmentSite, site_id) if site_id else None

    dlat = radius / METRES_PER_DEGREE_LAT
    dlon = radius / (METRES_PER_DEGREE_LAT * max(math.cos(math.radians(lat)), 1e-6))
    candidates = db.execute(
        select(EncroachmentSite).where(
            EncroachmentSite.cls == cls,
            EncroachmentSite.latitude.between(lat - dlat, lat + dlat),
            EncroachmentSite.longitude.between(lon - dlon, lon + dlon),
        )
    ).scalars().all()
    best, best_d = None, None
    for site in candidates:
        d = distance_m(lat, lon, site.latitude, site.longitude)
        if d <= radius and (best_d is None or d < best_d):
            best, best_d = site, d
    return best


def change_site_status(db: Session, site: EncroachmentSite, to_status: str,
                       note: str | None = None, actor: str = "system") -> SiteHistory:
    """Move a site along the review workflow; invalid moves raise InvalidTransition (409)."""
    if to_status not in STATUSES:
        raise ValidationFailed(f"Unknown status '{to_status}'. Allowed: {', '.join(STATUSES)}.")
    if to_status not in TRANSITIONS[site.status]:
        allowed = ", ".join(sorted(TRANSITIONS[site.status])) or "none"
        raise InvalidTransition(f"A '{site.status}' site cannot move to '{to_status}'. Allowed: {allowed}.")
    entry = SiteHistory(site_id=site.id, from_status=site.status, to_status=to_status, note=note, actor=actor)
    site.status = to_status
    db.add(entry)
    return entry


def assign_site(db: Session, finding: EncroachmentFinding, location: Location | None) -> SiteAssignment | None:
    """Attach a stored finding to a site (in the caller's transaction).
    Returns None for photos without a location."""
    if location is None:
        return None
    now = datetime.now(UTC)
    site = find_nearby_site(db, finding.cls, location.latitude, location.longitude)

    if site is None:
        site = EncroachmentSite(
            cls=finding.cls, latitude=location.latitude, longitude=location.longitude,
            status="reported", finding_count=1, max_severity=finding.severity,
            first_reported_at=now, last_reported_at=now,
        )
        db.add(site)
        db.flush()
        db.add(SiteHistory(site_id=site.id, from_status=None, to_status="reported",
                           note="site created from a new finding", actor="system"))
        finding.site_id = site.id
        return SiteAssignment(site, created=True, reopened=False)

    reopened = site.status == "resolved"
    if reopened:
        change_site_status(db, site, "reported", note="found again after being closed (re-encroached)")
    site.finding_count += 1
    site.max_severity = _worse(site.max_severity, finding.severity)
    site.last_reported_at = now
    finding.site_id = site.id
    return SiteAssignment(site, created=False, reopened=reopened)
