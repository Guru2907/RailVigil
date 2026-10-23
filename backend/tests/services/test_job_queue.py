"""job_queue: the worker threads. Uses the REAL queue and the REAL job
runner, with only the YOLO pipeline faked."""

import threading
import time

import pytest
from conftest import get_video, make_video_row

from app.cv.intrusion.video_processor import ProcessingAborted
from app.services import job_runner
from app.services.job_queue import JobQueue


@pytest.fixture
def queues():
    """Hand out queues and always stop them, even when a test fails."""
    created = []

    def make(**kwargs):
        kwargs.setdefault("recover", lambda: [])
        kwargs.setdefault("tracker_factory", lambda: object())
        kwargs.setdefault("worker_count", 1)
        q = JobQueue(**kwargs)
        created.append(q)
        return q

    yield make
    for q in created:
        q.stop(timeout=5)


def test_videos_are_processed_one_at_a_time_in_order(monkeypatch, queues):
    order = []
    running = []
    overlap = []

    def fake(**kw):
        running.append(kw["video_id"])
        if len(running) > 1:
            overlap.append(list(running))
        time.sleep(0.05)
        order.append(kw["video_id"])
        running.remove(kw["video_id"])
        return []

    monkeypatch.setattr(job_runner, "process_video", fake)
    ids = [make_video_row(f"v{i}.mp4") for i in range(3)]

    q = queues()
    for vid in ids:
        q.submit(vid)
    q.start()

    assert q.wait_idle(10)
    assert order == ids
    assert overlap == []                                    # never two at once with 1 worker
    assert all(get_video(v).status == "done" for v in ids)


def test_submitting_the_same_video_twice_runs_it_once(monkeypatch, queues):
    calls = []
    monkeypatch.setattr(job_runner, "process_video", lambda **kw: calls.append(kw["video_id"]) or [])
    vid = make_video_row()

    q = queues()
    q.submit(vid)
    q.submit(vid)
    q.start()

    assert q.wait_idle(10)
    assert calls == [vid]


def test_model_is_loaded_once_per_worker_and_reused(monkeypatch, queues):
    seen = []
    monkeypatch.setattr(job_runner, "process_video", lambda **kw: seen.append(kw["tracker"]) or [])
    loads = []

    def factory():
        loads.append(1)
        return object()

    ids = [make_video_row(f"v{i}.mp4") for i in range(3)]
    q = queues(tracker_factory=factory)
    for vid in ids:
        q.submit(vid)
    q.start()

    assert q.wait_idle(10)
    assert len(loads) == 1                                  # not once per video
    assert len(seen) == 3 and all(t is seen[0] for t in seen)


def test_model_load_failure_fails_that_job_but_worker_survives(monkeypatch, queues):
    monkeypatch.setattr(job_runner, "process_video", lambda **kw: [])
    attempts = []

    def flaky_factory():
        attempts.append(1)
        if len(attempts) == 1:
            raise OSError("cannot load weights")
        return object()

    first = make_video_row("first.mp4")
    second = make_video_row("second.mp4")
    q = queues(tracker_factory=flaky_factory)
    q.submit(first)
    q.submit(second)
    q.start()

    assert q.wait_idle(10)
    assert get_video(first).status == "failed"
    assert get_video(second).status == "done"               # worker is alive; load was retried


def test_a_crashing_runner_does_not_kill_the_worker(queues):
    handled = []

    def runner(video_id, get_tracker, should_abort):
        if video_id == "bad":
            raise RuntimeError("bug in the runner itself")
        handled.append(video_id)

    q = queues(runner=runner)
    q.submit("bad")
    q.submit("good")
    q.start()

    assert q.wait_idle(10)
    assert handled == ["good"]


def test_start_rebuilds_the_queue_from_recovery(monkeypatch, queues):
    monkeypatch.setattr(job_runner, "process_video", lambda **kw: [])
    left_over = make_video_row("leftover.mp4", status="processing", attempts=1)

    q = queues(recover=job_runner.recover_unfinished_jobs)
    q.start()

    assert q.wait_idle(10)
    assert get_video(left_over).status == "done"


def test_shutdown_interrupts_a_running_job_and_requeues_it(monkeypatch, queues):
    started = threading.Event()

    def long_job(**kw):
        started.set()
        while not kw["abort_cb"]():                         # a real run checks this every frame
            time.sleep(0.01)
        raise ProcessingAborted(kw["video_id"])

    monkeypatch.setattr(job_runner, "process_video", long_job)
    vid = make_video_row()
    q = queues()
    q.submit(vid)
    q.start()
    assert started.wait(5)

    q.stop(timeout=5)

    video = get_video(vid)
    assert video.status == "queued"                         # will be picked up after restart
    assert video.attempts == 0


def test_two_workers_run_two_videos_at_once(monkeypatch, queues):
    both_running = threading.Barrier(2, timeout=5)

    def needs_a_partner(**kw):
        both_running.wait()                                 # only passes if two jobs run together
        return []

    monkeypatch.setattr(job_runner, "process_video", needs_a_partner)
    ids = [make_video_row(f"w{i}.mp4") for i in range(2)]
    q = queues(worker_count=2)
    for vid in ids:
        q.submit(vid)
    q.start()

    assert q.wait_idle(10)
    assert all(get_video(v).status == "done" for v in ids)
