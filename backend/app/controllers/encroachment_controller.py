"""Turns encroachment rows into API responses, and the logic behind each
endpoint (routes stay thin; queries live in encroachment_repository)."""

import json

from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.encroachment import EncroachmentFinding, EncroachmentSite, Media, Report
from app.db.models.incident import Incident
from app.db.models.video import Video
from app.db.repositories import encroachment_repository as repo
from app.services import site_service, storage_service

API = "/api"


def _json(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except ValueError:
        return default


# --- converters ----------------------------------------------------------------------

def finding_out(f: EncroachmentFinding) -> dict:
    return {
        "id": f.id, "media_id": f.media_id, "site_id": f.site_id, "cls": f.cls, "label": f.label,
        "confidence": f.confidence, "bbox": [f.bbox_x1, f.bbox_y1, f.bbox_x2, f.bbox_y2],
        "zone_hit": f.zone_hit, "overlap_ratio": f.overlap_ratio, "overlap_area_px": f.overlap_area_px,
        "severity_score": f.severity_score, "severity": f.severity,
        "notes": _json(f.notes, []), "sources": _json(f.sources, []),
        "crop_url": f"{API}/encroachment/findings/{f.id}/crop" if f.crop_key else None,
        "created_at": f.created_at,
    }


def media_out(m: Media, duplicate: bool | None = None) -> dict:
    out = {
        "id": m.id, "kind": m.kind, "status": m.status, "error": m.error,
        "original_filename": m.original_filename, "width": m.width, "height": m.height,
        "captured_at": m.captured_at, "latitude": m.latitude, "longitude": m.longitude,
        "location_source": m.location_source, "camera_label": m.camera_label,
        "original_url": f"{API}/media/{m.id}/original",
        "annotated_url": f"{API}/media/{m.id}/annotated" if m.annotated_key else None,
        "created_at": m.created_at,
    }
    if duplicate is not None:
        out["duplicate"] = duplicate
    return out


def media_detail_out(m: Media) -> dict:
    return {
        **media_out(m),
        "zone": _json(m.zone_json, None),
        "model_versions": _json(m.model_versions, {}),
        "findings": [finding_out(f) for f in sorted(m.findings, key=lambda f: -f.severity_score)],
    }


def site_out(s: EncroachmentSite, latest_report_no: str | None) -> dict:
    return {
        "id": s.id, "cls": s.cls, "latitude": s.latitude, "longitude": s.longitude, "status": s.status,
        "finding_count": s.finding_count, "max_severity": s.max_severity,
        "first_reported_at": s.first_reported_at, "last_reported_at": s.last_reported_at,
        "latest_report_no": latest_report_no,
    }


def report_out(r: Report) -> dict:
    return {
        "report_no": r.report_no, "kind": r.kind, "reason": r.reason, "site_id": r.site_id,
        "media_id": r.media_id, "finding_id": r.finding_id, "created_at": r.created_at,
    }


# --- media ---------------------------------------------------------------------------

def get_media_or_404(db: Session, media_id: str) -> Media:
    media = repo.get_media(db, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return media


def media_file(db: Session, media_id: str, variant: str) -> FileResponse:
    media = get_media_or_404(db, media_id)
    key = media.original_key if variant == "original" else media.annotated_key
    if not storage_service.exists(key):
        raise HTTPException(status_code=404, detail=f"No {variant} image for this upload yet")
    return FileResponse(storage_service.path_for(key))


# --- findings -------------------------------------------------------------------------

def finding_crop(db: Session, finding_id: str) -> FileResponse:
    finding = repo.get_finding(db, finding_id)
    if finding is None or not storage_service.exists(finding.crop_key):
        raise HTTPException(status_code=404, detail="No evidence crop for this finding")
    return FileResponse(storage_service.path_for(finding.crop_key), media_type="image/jpeg")


# --- sites ------------------------------------------------------------------------------

def list_sites(db: Session, **filters) -> list[dict]:
    sites = repo.list_sites(db, **filters)
    latest = repo.latest_report_numbers(db, [s.id for s in sites])
    return [site_out(s, latest.get(s.id)) for s in sites]


def site_detail(db: Session, site_id: str) -> dict:
    site = repo.get_site(db, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    reports = repo.site_reports(db, site.id)
    return {
        **site_out(site, reports[0].report_no if reports else None),
        "findings": [finding_out(f) for f in repo.list_findings(db, site_id=site.id, limit=500)],
        "history": [
            {"from_status": h.from_status, "to_status": h.to_status, "note": h.note,
             "actor": h.actor, "created_at": h.created_at}
            for h in site.history
        ],
        "reports": [report_out(r) for r in reports],
    }


def update_site_status(db: Session, site_id: str, status: str, note: str | None, actor: str) -> dict:
    site = repo.get_site(db, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    actor = (actor or "officer").strip()[:100] or "officer"
    site_service.change_site_status(db, site, status, note=note, actor=actor)
    db.commit()
    db.refresh(site)
    return site_detail(db, site_id)


# --- reports -------------------------------------------------------------------------------

def report_detail(db: Session, report_no: str) -> dict:
    report = repo.get_report_by_no(db, report_no)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    site = repo.get_site(db, report.site_id) if report.site_id else None
    finding = repo.get_finding(db, report.finding_id) if report.finding_id else None
    media = repo.get_media(db, report.media_id) if report.media_id else None
    return {
        **report_out(report),
        "site": site_out(site, report.report_no) if site else None,
        "finding": finding_out(finding) if finding else None,
        "media": media_out(media) if media else None,
    }


# --- map ---------------------------------------------------------------------------------------

def map_features(db: Session, **filters) -> dict:
    """GeoJSON FeatureCollection of sites (coordinates are [longitude, latitude])."""
    sites = repo.list_sites(db, **filters)
    ids = [s.id for s in sites]
    latest_report = repo.latest_report_numbers(db, ids)
    latest_finding = repo.latest_findings(db, ids)
    features = []
    for s in sites:
        f = latest_finding.get(s.id)
        features.append({
            "type": "Feature",
            "id": s.id,
            "geometry": {"type": "Point", "coordinates": [s.longitude, s.latitude]},
            "properties": {
                "kind": "encroachment_site",
                "site_id": s.id, "cls": s.cls, "status": s.status, "max_severity": s.max_severity,
                "finding_count": s.finding_count,
                "first_reported_at": s.first_reported_at.isoformat(),
                "last_reported_at": s.last_reported_at.isoformat(),
                "latest_report_no": latest_report.get(s.id),
                "thumbnail_url": f"{API}/encroachment/findings/{f.id}/crop" if f and f.crop_key else None,
            },
        })
    return {"type": "FeatureCollection", "features": features}


def intrusion_features(db: Session, bbox=None, created_from=None, created_to=None, limit: int = 2000) -> list[dict]:
    """GeoJSON points for confirmed intrusion incidents of videos that have a camera location."""
    q = (select(Incident, Video).join(Video, Incident.video_id == Video.id)
         .where(Video.latitude.is_not(None), Video.longitude.is_not(None))
         .order_by(Incident.created_at.desc()).limit(limit))
    if bbox:
        min_lon, min_lat, max_lon, max_lat = bbox
        q = q.where(Video.longitude.between(min_lon, max_lon), Video.latitude.between(min_lat, max_lat))
    if created_from:
        q = q.where(Incident.created_at >= created_from)
    if created_to:
        q = q.where(Incident.created_at <= created_to)
    return [{
        "type": "Feature",
        "id": f"inc-{inc.id}",
        "geometry": {"type": "Point", "coordinates": [video.longitude, video.latitude]},
        "properties": {
            "kind": "intrusion_incident",
            "incident_id": inc.id, "video_id": video.id, "camera_label": video.camera_label,
            "object_class": inc.object_class, "event_type": inc.event_type, "severity": inc.severity,
            "risk_score": inc.risk_score, "created_at": inc.created_at.isoformat(),
        },
    } for inc, video in db.execute(q).all()]


def parse_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    if not raw:
        return None
    try:
        min_lon, min_lat, max_lon, max_lat = (float(v) for v in raw.split(","))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="bbox must be 'min_lon,min_lat,max_lon,max_lat'.") from exc
    if not (-180 <= min_lon <= max_lon <= 180 and -90 <= min_lat <= max_lat <= 90):
        raise HTTPException(status_code=422, detail="bbox is out of range or min > max.")
    return min_lon, min_lat, max_lon, max_lat


def split_csv(raw: str | None) -> list[str] | None:
    values = [v.strip() for v in (raw or "").split(",") if v.strip()]
    return values or None

