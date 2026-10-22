"""Processing uploaded photos in the background, and recovering after a crash.

    queued --claim--> processing --success--> done
                          |------ failure --> failed   (short message; traceback only in the log)
                          |------ shutdown -> queued   (re-run after restart)

Photos get their own JobQueue instance (services/job_queue.py is reused
unchanged): its worker loads the encroachment models once and keeps them.

A finished photo is saved in ONE transaction -- findings, site assignment,
reports and status=done together -- so a crash can never leave half-saved
results, and a retry starts clean.

Reports are issued automatically (services/report_service.py), at most one
per site per photo -- a photo of five huts at one spot is one event, not five:
  * new_site          -- a located finding started a new site
  * re_encroached     -- a resolved site was found again
  * critical_finding  -- an existing site's worst severity just became critical;
                         or, for a photo without a location (no site), once per
                         photo that has a critical finding
"""

import json
import logging

from sqlalchemy.orm import Session

from app.core import config
from app.core.errors import AppError
from app.cv.common.model_registry import ModelNotAvailable
from app.cv.encroachment.detector import EncroachmentDetector
from app.cv.encroachment.pipeline import analyze_image
from app.db.database import SessionLocal
from app.db.models.encroachment import EncroachmentFinding, Media
from app.db.repositories import encroachment_repository as repo
from app.services import report_service, site_service, storage_service
from app.services.geo_service import Location
from app.services.job_queue import JobQueue

logger = logging.getLogger(__name__)

GENERIC_FAILURE = "Processing failed unexpectedly. Please try again; if it keeps failing, contact an administrator."
EVIDENCE_FOLDER = "photo"   # analyze_image writes evidence to <out_dir>/<original stem>/


class ProcessingAborted(Exception):
    """The server is shutting down; the photo goes back to the queue."""


def describe_failure(exc: BaseException) -> str:
    if isinstance(exc, AppError):
        return exc.message
    if isinstance(exc, ModelNotAvailable):
        return "The encroachment models are not installed on the server."
    if isinstance(exc, FileNotFoundError):
        return "The uploaded image file could not be found."
    if isinstance(exc, MemoryError):
        return "The server ran out of memory while processing this image."
    return GENERIC_FAILURE


def _location_of(media: Media) -> Location | None:
    if media.latitude is None or media.longitude is None:
        return None
    return Location(media.latitude, media.longitude, media.location_source)


def _site_report_reason(assignment) -> str | None:
    if assignment.created:
        return "new_site"
    if assignment.reopened:
        return "re_encroached"
    if assignment.escalated_to_critical:
        return "critical_finding"
    return None


def save_results(db: Session, media: Media, result, model_versions: dict) -> list[EncroachmentFinding]:
    """Store findings, assign sites, issue reports and mark the photo done
    (not committed here: the caller commits once)."""
    evidence_key = storage_service.media_key(media.id, EVIDENCE_FOLDER)
    report = json.loads((storage_service.path_for(evidence_key) / "findings.json").read_text(encoding="utf-8"))
    crops = [f.get("crop") for f in report["findings"]]
    location = _location_of(media)

    stored = []
    reported_sites: set[str] = set()     # one report per site per photo
    unlocated_critical_reported = False
    # result.findings is sorted most severe first, so a site's report points
    # at its worst finding in this photo.
    for finding, crop in zip(result.findings, crops, strict=True):
        row = EncroachmentFinding(
            media_id=media.id, cls=finding.cls, label=finding.label, confidence=finding.confidence,
            bbox_x1=finding.bbox[0], bbox_y1=finding.bbox[1], bbox_x2=finding.bbox[2], bbox_y2=finding.bbox[3],
            zone_hit=finding.zone_hit, overlap_ratio=finding.overlap_ratio,
            overlap_area_px=finding.overlap_area_px, severity_score=finding.severity_score,
            severity=finding.severity, notes=json.dumps(finding.notes), sources=json.dumps(finding.sources),
            crop_key=f"{evidence_key}/crops/{crop}" if crop else None,
        )
        db.add(row)
        db.flush()

        assignment = site_service.assign_site(db, row, location)
        if assignment is not None:
            reason = _site_report_reason(assignment)
            if reason and assignment.site.id not in reported_sites:
                report_service.issue_report(db, reason, site=assignment.site, media=media, finding=row)
                reported_sites.add(assignment.site.id)
        elif row.severity == "critical" and not unlocated_critical_reported:
            report_service.issue_report(db, "critical_finding", media=media, finding=row)
            unlocated_critical_reported = True
        stored.append(row)

    media.annotated_key = f"{evidence_key}/annotated.jpg"
    media.model_versions = json.dumps(model_versions)
    media.status = "done"
    media.error = None
    return stored


def run_image_job(media_id: str, get_detector, should_abort) -> None:
    db = SessionLocal()
    try:
        if not repo.claim_media(db, media_id):
            logger.info("media %s is no longer queued; skipping", media_id)
            return
        media = repo.get_media(db, media_id)
        logger.info("media %s: processing started (attempt %d)", media_id, media.attempts)
        evidence_key = storage_service.media_key(media_id, EVIDENCE_FOLDER)
        try:
            if should_abort():
                raise ProcessingAborted(media_id)
            storage_service.delete_prefix(evidence_key)   # a retry never mixes with leftovers
            detector = get_detector()
            result = analyze_image(
                storage_service.path_for(media.original_key), detector,
                manual_zone=json.loads(media.zone_json) if media.zone_json else None,
                out_dir=storage_service.path_for(storage_service.media_key(media_id)),
            )
            versions = detector.model_versions() if hasattr(detector, "model_versions") else {}
            stored = save_results(db, media, result, versions)
            db.commit()
            logger.info("media %s: done, %d finding(s)", media_id, len(stored))

        except ProcessingAborted:
            db.rollback()
            storage_service.delete_prefix(evidence_key)
            repo.requeue_media(db, media_id, refund_attempt=True)
            logger.info("media %s: interrupted by shutdown, requeued", media_id)

        except Exception as exc:  # noqa: BLE001 -- every failure must be recorded, never lost
            logger.exception("media %s: processing failed", media_id)
            db.rollback()
            storage_service.delete_prefix(evidence_key)
            repo.mark_media_failed(db, media_id, describe_failure(exc))
    finally:
        db.close()


def recover_unfinished_images() -> list[str]:
    """At startup: re-queue photos a previous run left queued or processing;
    give up on one that keeps crashing the server, or whose file is gone."""
    db = SessionLocal()
    ids: list[str] = []
    try:
        for media in repo.list_unfinished_media(db):
            if not storage_service.exists(media.original_key):
                repo.mark_media_failed(db, media.id, "The uploaded image file is missing from the server.")
                continue
            if media.status == "processing":
                if media.attempts >= config.MAX_JOB_ATTEMPTS:
                    repo.mark_media_failed(db, media.id,
                                           "Processing was interrupted too many times and has been stopped.")
                    continue
                repo.requeue_media(db, media.id)
            ids.append(media.id)
    finally:
        db.close()
    return ids


# One photo queue per process, created on first use. Tests swap it with set_image_queue().
_queue: JobQueue | None = None


def get_image_queue() -> JobQueue:
    global _queue
    if _queue is None:
        _queue = JobQueue(
            runner=run_image_job,
            tracker_factory=EncroachmentDetector,    # loaded once per worker, on its first photo
            recover=recover_unfinished_images,
            worker_count=config.IMAGE_WORKER_COUNT,
        )
    return _queue


def set_image_queue(q: JobQueue | None) -> None:
    global _queue
    _queue = q
