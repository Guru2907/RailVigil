"""job_runner: what happens to one video, and recovery after a crash.

The real pipeline (YOLO) is replaced by a fake `process_video`, so these
tests need no model weights and run in milliseconds.
"""

from pathlib import Path

import pytest
from conftest import count_incidents, get_video, make_video_row
from sqlalchemy import update

from app.core import config
from app.core.errors import ValidationFailed
from app.cv.intrusion.video_processor import ProcessingAborted
from app.db.database import SessionLocal
from app.db.models.video import Video
from app.db.repositories import video_repository
from app.services import job_runner


def _incident(track_id=1):
    return {
        "track_id": track_id, "object_class": "person", "event_type": "human_intrusion",
        "severity": "high", "is_persistent": False, "start_frame": 0, "end_frame": 30,
        "start_ts": 0.0, "end_ts": 2.0, "dwell_time_sec": 2.0, "max_penetration": 0.5,
        "avg_penetration": 0.4, "risk_score": 50.0, "zone_label": "z", "snapshot_path": None,
    }


@pytest.fixture
def fake_pipeline(monkeypatch):
    """Replace process_video; tests set `.behaviour` to control it."""
    class Fake:
        calls = []
        behaviour = staticmethod(lambda **kw: [])

        def __call__(self, **kwargs):
            Fake.calls.append(kwargs)
            return Fake.behaviour(**kwargs)

    Fake.calls = []
    monkeypatch.setattr(job_runner, "process_video", Fake())
    return Fake


def run(video_id, tracker=object(), should_abort=lambda: False):
    job_runner.run_job(video_id, lambda: tracker, should_abort)


# --- happy path ----------------------------------------------------------------

def test_successful_job_saves_incidents_and_marks_done(fake_pipeline):
    fake_pipeline.behaviour = staticmethod(lambda **kw: [_incident(1), _incident(2)])
    vid = make_video_row()

    run(vid)

    video = get_video(vid)
    assert video.status == "done"
    assert video.progress == 100.0
    assert video.error is None
    assert video.attempts == 1
    assert video.output_video_path.endswith("annotated.mp4")
    assert count_incidents(vid) == 2


def test_rerunning_a_video_does_not_duplicate_incidents(fake_pipeline):
    """Crash-recovery can run the same video twice. Incidents must be
    replaced, not added on top."""
    fake_pipeline.behaviour = staticmethod(lambda **kw: [_incident(1), _incident(2)])
    vid = make_video_row()
    run(vid)

    # simulate crash recovery putting it back in the queue
    db = SessionLocal()
    db.execute(update(Video).where(Video.id == vid).values(status="queued"))
    db.commit()
    db.close()
    run(vid)

    assert count_incidents(vid) == 2


def test_progress_callback_and_tracker_are_passed_to_pipeline(fake_pipeline):
    sentinel = object()
    vid = make_video_row()
    run(vid, tracker=sentinel)

    kwargs = fake_pipeline.calls[0]
    assert kwargs["tracker"] is sentinel
    assert callable(kwargs["progress_cb"])
    assert callable(kwargs["abort_cb"])
    assert kwargs["zone_points"] == {"points": [[0, 0], [100, 0], [100, 100]]}


# --- claiming -------------------------------------------------------------------

def test_claim_succeeds_once_only():
    vid = make_video_row()
    db = SessionLocal()
    try:
        assert video_repository.claim_video(db, vid) is True
        assert video_repository.claim_video(db, vid) is False   # already processing
    finally:
        db.close()


def test_job_that_is_not_queued_is_skipped(fake_pipeline):
    for status in ("processing", "done", "failed"):
        vid = make_video_row(filename=f"{status}.mp4", status=status)
        run(vid)
    assert fake_pipeline.calls == []


def test_mark_done_does_not_transition_a_queued_video():
    vid = make_video_row()
    db = SessionLocal()
    try:
        assert video_repository.mark_done(db, vid, "output.mp4") is False
    finally:
        db.close()

    assert get_video(vid).status == "queued"


def test_unknown_video_id_is_skipped(fake_pipeline):
    run("does-not-exist")
    assert fake_pipeline.calls == []


# --- failure --------------------------------------------------------------------

def test_failure_is_recorded_with_a_safe_short_message(fake_pipeline):
    def boom(**kw):
        raise RuntimeError(r"secret internals: C:\Users\someone\models\weights.pt")
    fake_pipeline.behaviour = staticmethod(boom)
    vid = make_video_row()

    run(vid)

    video = get_video(vid)
    assert video.status == "failed"
    assert video.error == job_runner.GENERIC_FAILURE
    assert "secret" not in video.error and "Users" not in video.error
    assert "\n" not in video.error                    # no traceback


def test_failure_cleans_up_partial_output(fake_pipeline):
    def write_then_fail(**kw):
        out = Path(kw["output_video_path"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"partial")
        raise RuntimeError("died halfway")
    fake_pipeline.behaviour = staticmethod(write_then_fail)
    vid = make_video_row()

    run(vid)

    assert not job_runner.output_dir(vid).exists()


def test_tracker_load_failure_fails_the_job(fake_pipeline):
    def bad_tracker():
        raise OSError("weights file corrupt")
    vid = make_video_row()

    job_runner.run_job(vid, bad_tracker, lambda: False)

    video = get_video(vid)
    assert video.status == "failed"
    assert "weights" not in video.error


def test_describe_failure_messages():
    assert job_runner.describe_failure(ValidationFailed("zone is bad")) == "zone is bad"
    assert "could not be opened" in job_runner.describe_failure(FileNotFoundError("/x/y.mp4"))
    assert "memory" in job_runner.describe_failure(MemoryError())
    assert job_runner.describe_failure(KeyError("x")) == job_runner.GENERIC_FAILURE


# --- graceful shutdown ----------------------------------------------------------------

def test_abort_requeues_the_video_and_refunds_the_attempt(fake_pipeline):
    def aborted(**kw):
        raise ProcessingAborted(kw["video_id"])
    fake_pipeline.behaviour = staticmethod(aborted)
    vid = make_video_row()

    run(vid)

    video = get_video(vid)
    assert video.status == "queued"
    assert video.attempts == 0           # shutdown is not the video's fault
    assert video.error is None


# --- progress reporting ---------------------------------------------------------------

def _processing_row():
    vid = make_video_row(status="queued")
    db = SessionLocal()
    video_repository.claim_video(db, vid)
    db.close()
    return vid


def test_progress_is_throttled_and_capped():
    vid = _processing_row()
    db = SessionLocal()
    try:
        reporter = job_runner.ProgressReporter(db, vid, interval_sec=3600)
        reporter(30, 100)
        assert get_video(vid).progress == 30.0
        reporter(60, 100)                                  # inside the interval: not written
        assert get_video(vid).progress == 30.0

        fast = job_runner.ProgressReporter(db, vid, interval_sec=0)
        fast(100, 100)
        assert get_video(vid).progress == 99.0             # only "done" reaches 100
    finally:
        db.close()


def test_progress_ignores_unknown_total():
    vid = _processing_row()
    db = SessionLocal()
    try:
        job_runner.ProgressReporter(db, vid, interval_sec=0)(10, 0)
        assert get_video(vid).progress == 0.0
    finally:
        db.close()


def test_late_progress_write_cannot_change_a_finished_video(fake_pipeline):
    vid = make_video_row()
    run(vid)                                               # done, progress 100
    db = SessionLocal()
    try:
        video_repository.update_progress(db, vid, 42.0)
    finally:
        db.close()
    assert get_video(vid).progress == 100.0


# --- crash recovery -------------------------------------------------------------------

def test_recovery_requeues_orphans_and_gives_up_on_repeat_crashers():
    orphan = make_video_row("a.mp4", status="processing", attempts=1)
    crasher = make_video_row("b.mp4", status="processing", attempts=config.MAX_JOB_ATTEMPTS)
    waiting = make_video_row("c.mp4", status="queued")
    missing = make_video_row("d.mp4", status="queued", with_file=False)
    finished = make_video_row("e.mp4", status="done")

    ids = job_runner.recover_unfinished_jobs()

    assert ids == [orphan, waiting]                        # oldest first; nothing else
    assert get_video(orphan).status == "queued"
    assert get_video(orphan).attempts == 1                 # recovery itself doesn't use up an attempt
    assert get_video(crasher).status == "failed"
    assert "interrupted" in get_video(crasher).error
    assert get_video(missing).status == "failed"
    assert "missing" in get_video(missing).error
    assert get_video(finished).status == "done"
