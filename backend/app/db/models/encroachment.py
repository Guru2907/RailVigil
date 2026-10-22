"""Tables for the encroachment module (docs/DATA_MODEL.md).

media                  one uploaded photo and its processing state
encroachment_findings  potential encroachments found in a photo
encroachment_sites     the same place reported again and again (needs a location)
site_history           every status change of a site
reports                numbered reports (RV-ENC-YYYY-NNNNNN)
report_counters        the last number issued per kind and year

Locations are plain latitude/longitude columns so the schema works on SQLite
and PostgreSQL alike; on PostgreSQL the migration adds a spatial index and
site_service uses PostGIS for distance searches. List-like values (notes,
sources, model versions, zones) are stored as JSON text for the same reason.
Ids are full UUID hex strings.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class Media(Base):
    """One uploaded photo. Lifecycle: queued -> processing -> done | failed."""

    __tablename__ = "media"

    id = Column(String(32), primary_key=True, default=_uuid)
    kind = Column(String, nullable=False, default="image")
    status = Column(String, nullable=False, default="queued", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)

    original_filename = Column(String, nullable=True)
    sha256 = Column(String(64), nullable=False, unique=True)   # the same file uploaded twice is one media row
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    captured_at = Column(DateTime(timezone=True), nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_source = Column(String, nullable=False, default="none")   # exif | pin | none

    zone_json = Column(Text, nullable=True)        # ResolvedZone.as_record()
    camera_label = Column(String, nullable=True)
    original_key = Column(String, nullable=True)   # storage keys (services/storage_service.py)
    annotated_key = Column(String, nullable=True)
    model_versions = Column(Text, nullable=True)   # JSON: {"model-name": "version"}

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    findings = relationship("EncroachmentFinding", back_populates="media", cascade="all, delete-orphan")


class EncroachmentSite(Base):
    """A place where potential encroachment has been reported. Only findings
    from located photos belong to a site."""

    __tablename__ = "encroachment_sites"

    id = Column(String(32), primary_key=True, default=_uuid)
    cls = Column(String, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    # reported -> under_review -> verified -> action_taken -> resolved | false_positive
    status = Column(String, nullable=False, default="reported", index=True)
    finding_count = Column(Integer, nullable=False, default=0)
    max_severity = Column(String, nullable=False, default="low")
    first_reported_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    last_reported_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    findings = relationship("EncroachmentFinding", back_populates="site")
    history = relationship(
        "SiteHistory", back_populates="site", cascade="all, delete-orphan", order_by="SiteHistory.created_at"
    )


class EncroachmentFinding(Base):
    """One potential encroachment in one photo (rules.Finding, stored)."""

    __tablename__ = "encroachment_findings"

    id = Column(String(32), primary_key=True, default=_uuid)
    media_id = Column(String(32), ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id = Column(String(32), ForeignKey("encroachment_sites.id", ondelete="SET NULL"), nullable=True, index=True)

    cls = Column(String, nullable=False, index=True)
    label = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    bbox_x1 = Column(Float, nullable=False)
    bbox_y1 = Column(Float, nullable=False)
    bbox_x2 = Column(Float, nullable=False)
    bbox_y2 = Column(Float, nullable=False)
    zone_hit = Column(String, nullable=False)
    overlap_ratio = Column(Float, nullable=False)
    overlap_area_px = Column(Float, nullable=False)
    severity_score = Column(Float, nullable=False)
    severity = Column(String, nullable=False, index=True)
    notes = Column(Text, nullable=True)     # JSON list of strings
    sources = Column(Text, nullable=True)   # JSON list of "model@version"
    crop_key = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    media = relationship("Media", back_populates="findings")
    site = relationship("EncroachmentSite", back_populates="findings")


class SiteHistory(Base):
    """Audit trail: every status change of a site, including automatic ones."""

    __tablename__ = "site_history"

    id = Column(String(32), primary_key=True, default=_uuid)
    site_id = Column(String(32), ForeignKey("encroachment_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String, nullable=True)   # None when the site is created
    to_status = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    actor = Column(String, nullable=False, default="system")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    site = relationship("EncroachmentSite", back_populates="history")


class Report(Base):
    """A numbered report, issued automatically for a new site, a critical
    finding or a site found again after it was closed."""

    __tablename__ = "reports"

    id = Column(String(32), primary_key=True, default=_uuid)
    report_no = Column(String, nullable=False, unique=True)
    kind = Column(String, nullable=False, default="encroachment")
    reason = Column(String, nullable=False)   # new_site | critical_finding | re_encroached
    site_id = Column(String(32), ForeignKey("encroachment_sites.id", ondelete="SET NULL"), nullable=True, index=True)
    media_id = Column(String(32), ForeignKey("media.id", ondelete="SET NULL"), nullable=True, index=True)
    finding_id = Column(
        String(32), ForeignKey("encroachment_findings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)


class ReportCounter(Base):
    """Last report number issued per kind and year; incremented atomically."""

    __tablename__ = "report_counters"
    __table_args__ = (UniqueConstraint("kind", "year", name="uq_report_counters_kind_year"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    kind = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    last_value = Column(Integer, nullable=False, default=0)
