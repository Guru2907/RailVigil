"""What happens to ONE video once a worker picks it up -- and what happens
to videos left unfinished by a crash.

    queued --claim--> processing --success--> done
                          |------ failure --> failed   (short message; traceback only in the log)
                          |------ shutdown -> queued   (will be re-run after restart)

The database row is the source of truth for that state. The in-memory
queue in job_queue.py is only a to-do list rebuilt from the database at
startup, which is why a crash or restart can never lose a job.

This file knows nothing about threads or queues: `run_job` is a plain
function, which makes it easy to test with a fake `process_video`.
"""

import json
import logging
import shutil
import time
from pathlib import Path

from app.core import config
from app.core.errors import AppError
from app.cv.intrusion.video_processor import ProcessingAborted, process_video
from app.db.database import SessionLocal
from app.db.repositories import incident_repository, video_repository
from app.utils.file_utils import raw_video_path

logger = logging.getLogger(__name__)

# Shown to the user (and stored in Video.error). Deliberately vague: the
# real cause is in the server log, tagged with the video id.
GENERIC_FAILURE = (
    "Processing failed unexpectedly. Please try again; if it keeps failing, contact an administrator."
)


def output_dir(video_id: str) -> Path:
    return Path(config.OUTPUTS_DIR) / video_id


def output_video_path(video_id: str) -> str:
    return str(output_dir(video_id) / "annotated.mp4")


def _discard_output(video_id: str) -> None:
    """Remove the annotated video and snapshots. Used before a (re)run so a
    retry never mixes with leftovers, and after a failed/aborted run so no
    half-written video is left behind."""
    shutil.rmtree(output_dir(video_id), ignore_errors=True)


def describe_failure(exc: BaseException) -> str:
    """Turn an exception into a message that is safe to show to a user."""
    if isinstance(exc, AppError):
        return exc.message
    if isinstance(exc, FileNotFoundError):
        return "The uploaded video file could not be opened."
    if isinstance(exc, MemoryError):
        return "The server ran out of memory while processing this video."
    return GENERIC_FAILURE


class ProgressReporter:
    """Callable passed to process_video as `progress_cb(done, total)`.

    process_video reports every ~30 frames; writing each of those to the
    database would be a lot of tiny writes, so this only writes when
    PROGRESS_UPDATE_SEC has passed. Capped at 99: the bar only reaches 100
    when the video is actually marked done (the frame count a container
    reports can be a little off)."""

    def __init__(self, db, video_id: str, interval_sec: float | None = None):
        self._db = db
        self._video_id = video_id
        self._interval = config.PROGRESS_UPDATE_SEC if interval_sec is None else interval_sec
        self._last_write = 0.0  # monotonic clock; 0 means "never written"

    def __call__(self, done: int, total: int) -> None:
        if total <= 0:
            return
        now = time.monotonic()
        if self._last_write and now - self._last_write < self._interval:
            return
        self._last_write = now
        percent = min(99.0, round(100.0 * done / total, 1))
        video_repository.update_progress(self._db, self._video_id, percent)


def complete_video(db, video_id: str, incidents: list[dict], output_path: str) -> None:
    """Save incidents AND mark the video done in ONE transaction.

    Done separately, a crash between the two steps would leave a video that
    is still `processing` but already has incidents; recovery would re-run
    it and insert them a second time. In one transaction it's all-or-nothing,
    and replace_for_video clears any earlier attempt's incidents anyway."""
    incident_repository.replace_for_video(db, video_id, incidents, commit=False)
    if not video_repository.mark_done(db, video_id, output_path, commit=False):
        raise RuntimeError(f"video {video_id} was not processing at completion time")
    db.commit()


def run_job(video_id: str, get_tracker, should_abort) -> None:
    """Process one video start to finish.

    get_tracker:  callable returning the worker's long-lived Tracker (loaded on
                  first use, so a missing model file becomes a failed job, not
                  a dead worker).
    should_abort: callable; True when the server is shutting down.
    """
    db = SessionLocal()
    try:
        # Atomic queued -> processing. If the video was already taken (or
        # finished, or deleted) this returns False and we just move on.
        if not video_repository.claim_video(db, video_id):
            logger.info("video %s is no longer queued; skipping", video_id)
            return

        video = video_repository.get_video(db, video_id)
        logger.info("video %s: processing started (attempt %d)", video_id, video.attempts)
        try:
            zone_record = json.loads(video.zone_json) if video.zone_json else None
            _discard_output(video_id)
            out_path = output_video_path(video_id)

            incidents = process_video(
                video_path=str(raw_video_path(video.filename)),
                zone_points=zone_record,
                video_id=video_id,
                output_video_path=out_path,
                zone_label=video.camera_label or "safety-zone",
                camera_label=video.camera_label,
                progress_cb=ProgressReporter(db, video_id),
                tracker=get_tracker(),
                abort_cb=should_abort,
            )
            complete_video(db, video_id, incidents, out_path)
            logger.info("video %s: done, %d incident(s)", video_id, len(incidents))

        except ProcessingAborted:
            # Server is stopping. Not the video's fault: put it back and
            # don't count the attempt.
            db.rollback()
            _discard_output(video_id)
            video_repository.requeue_video(db, video_id, refund_attempt=True)
            logger.info("video %s: interrupted by shutdown, requeued", video_id)

        except Exception as exc:  # noqa: BLE001 -- every pipeline failure must be recorded, never lost
            # The full traceback goes to the log only.
            logger.exception("video %s: processing failed", video_id)
            db.rollback()  # the session may be mid-transaction if the failure was a DB error
            _discard_output(video_id)
            video_repository.mark_failed(db, video_id, describe_failure(exc))
    finally:
        db.close()


def recover_unfinished_jobs() -> list[str]:
    """Run once at startup, before workers start. Returns the ids to enqueue
    (oldest first).

    * `queued`      -> just enqueue again (the in-memory queue was lost).
    * `processing`  -> the server died mid-job. Put it back to `queued` --
                       unless it has already started MAX_JOB_ATTEMPTS times,
                       which suggests this very video is what keeps crashing
                       the server; then fail it instead of looping forever.
    * Any of them whose uploaded file has gone missing is failed.
    """
    db = SessionLocal()
    ids: list[str] = []
    try:
        for video in video_repository.list_unfinished(db):
            if not raw_video_path(video.filename).exists():
                logger.error("video %s: uploaded file is missing, failing it", video.id)
                video_repository.mark_failed(db, video.id, "The uploaded video file is missing from the server.")
                continue

            if video.status == "processing":
                if video.attempts >= config.MAX_JOB_ATTEMPTS:
                    logger.error("video %s: interrupted %d times, giving up", video.id, video.attempts)
                    video_repository.mark_failed(
                        db, video.id,
                        "Processing was interrupted too many times and has been stopped.",
                    )
                    continue
                logger.warning("video %s: was interrupted mid-processing, requeueing", video.id)
                video_repository.requeue_video(db, video.id)

            ids.append(video.id)
    finally:
        db.close()
    return ids
