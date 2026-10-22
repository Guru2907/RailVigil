"""Response and request shapes for the encroachment API. Files are exposed
only as API URLs (never storage paths); JSON text columns come back as real
lists and objects."""

from datetime import datetime

from pydantic import BaseModel


class FindingOut(BaseModel):
    id: str
    media_id: str
    site_id: str | None
    cls: str
    label: str
    confidence: float
    bbox: list[float]                 # [x1, y1, x2, y2] in image pixels
    zone_hit: str
    overlap_ratio: float
    overlap_area_px: float
    severity_score: float
    severity: str
    notes: list[str]
    sources: list[str]
    crop_url: str | None
    created_at: datetime


class MediaOut(BaseModel):
    id: str
    kind: str
    status: str                       # queued | processing | done | failed
    error: str | None
    original_filename: str | None
    width: int | None
    height: int | None
    captured_at: datetime | None
    latitude: float | None
    longitude: float | None
    location_source: str              # exif | pin | none
    camera_label: str | None
    original_url: str
    annotated_url: str | None         # only once processing is done
    created_at: datetime


class UploadResultOut(MediaOut):
    duplicate: bool                   # True: this exact file was uploaded before; nothing new queued


class MediaDetailOut(MediaOut):
    zone: dict | None
    model_versions: dict
    findings: list[FindingOut]


class SiteOut(BaseModel):
    id: str
    cls: str
    latitude: float
    longitude: float
    status: str
    finding_count: int
    max_severity: str
    first_reported_at: datetime
    last_reported_at: datetime
    latest_report_no: str | None


class SiteHistoryOut(BaseModel):
    from_status: str | None
    to_status: str
    note: str | None
    actor: str
    created_at: datetime


class ReportOut(BaseModel):
    report_no: str
    kind: str
    reason: str                       # new_site | critical_finding | re_encroached
    site_id: str | None
    media_id: str | None
    finding_id: str | None
    created_at: datetime


class SiteDetailOut(SiteOut):
    findings: list[FindingOut]
    history: list[SiteHistoryOut]
    reports: list[ReportOut]


class SitePatch(BaseModel):
    status: str
    note: str | None = None
    actor: str = "officer"


class ReportDetailOut(ReportOut):
    site: SiteOut | None
    finding: FindingOut | None
    media: MediaOut | None


class StatsOut(BaseModel):
    encroachment: dict
    intrusion: dict
