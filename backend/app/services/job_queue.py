"""Background workers that process uploaded videos one after another.

How it fits together
--------------------
* The upload request saves the video, creates a `queued` row, and calls
  `submit(video_id)`. It returns immediately; it never waits for YOLO.
* A small pool of worker threads (WORKER_COUNT, default 1) takes ids off an
  in-memory queue and calls job_runner.run_job().
* The in-memory queue is only a convenience. The database says which videos
  are unfinished, and `start()` rebuilds the queue from it, so nothing is
  lost on a restart.

Why each worker has its OWN tracker/model
-----------------------------------------
Ultralytics keeps tracking state (which box is which id) on the model.
Two workers sharing one model would corrupt each other's tracks. So each
worker loads the model once, on its first job, and reuses it for every
later video (Tracker.reset() clears the state between videos).

Limits (documented on purpose)
------------------------------
This is an in-process queue: it assumes ONE server process. Running
uvicorn with several `--workers` would create several independent queues
that don't know about each other. For a single machine with SQLite that is
the right trade-off; to scale out, replace this module with RQ/Celery --
the rest of the code only calls `submit()`.
"""

import logging
import queue
import threading
import time

from app.core import config
from app.cv.common.tracker import Tracker
from app.services import job_runner

logger = logging.getLogger(__name__)


class _LazyTracker:
    """Creates the worker's Tracker on first use, then keeps it. If creating
    it fails (e.g. the model file can't be loaded), nothing is cached so the
    next job tries again, and THIS job fails with a clear log entry."""

    def __init__(self, factory):
        self._factory = factory
        self._tracker = None

    def __call__(self):
        if self._tracker is None:
            logger.info("loading detection model for this worker")
            self._tracker = self._factory()
        return self._tracker


class JobQueue:
    def __init__(self, runner=None, tracker_factory=None, recover=None, worker_count: int | None = None):
        # Injected so tests can run the real queue with a fake runner and no model.
        self._runner = runner or job_runner.run_job
        self._tracker_factory = tracker_factory or (lambda: Tracker(class_filter=config.INTRUSION_CLASSES))
        self._recover = recover or job_runner.recover_unfinished_jobs
        self._worker_count = worker_count

        self._queue: queue.Queue[str] = queue.Queue()
        self._pending: set[str] = set()      # ids currently queued or running (prevents double-submit)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    # --- public API --------------------------------------------------------
    def submit(self, video_id: str) -> None:
        """Add a video to the queue. Safe to call before start(); workers
        pick it up once they are running."""
        with self._lock:
            if video_id in self._pending:
                return
            self._pending.add(video_id)
        self._queue.put(video_id)

    def start(self) -> None:
        if self._threads:
            return
        self._stop.clear()

        for video_id in self._recover():
            self.submit(video_id)

        count = self._worker_count or config.WORKER_COUNT
        for i in range(count):
            t = threading.Thread(target=self._worker_loop, name=f"video-worker-{i + 1}", daemon=True)
            t.start()
            self._threads.append(t)
        logger.info("job queue started with %d worker(s)", count)

    def stop(self, timeout: float = 30.0) -> None:
        """Ask workers to stop. A job in progress notices on its next frame,
        puts its video back to `queued`, and exits. Threads are daemons, so
        even if one is stuck past `timeout` the process can still exit; the
        startup recovery handles whatever was left `processing`."""
        self._stop.set()
        deadline = time.monotonic() + timeout
        for t in self._threads:
            t.join(max(0.0, deadline - time.monotonic()))
        self._threads.clear()
        logger.info("job queue stopped")

    def wait_idle(self, timeout: float = 30.0) -> bool:
        """Block until nothing is queued or running. For tests and scripts."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if not self._pending:
                    return True
            time.sleep(0.02)
        return False

    # --- worker -----------------------------------------------------------------
    def _worker_loop(self) -> None:
        get_tracker = _LazyTracker(self._tracker_factory)
        while not self._stop.is_set():
            try:
                video_id = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._runner(video_id, get_tracker, self._stop.is_set)
            except Exception:  # noqa: BLE001 -- a bug in one job must not kill the worker
                logger.exception("worker crashed while running video %s", video_id)
            finally:
                with self._lock:
                    self._pending.discard(video_id)
                self._queue.task_done()


# One queue per process, created on first use. Tests swap it with set_queue().
_queue: JobQueue | None = None


def get_queue() -> JobQueue:
    global _queue
    if _queue is None:
        _queue = JobQueue()
    return _queue


def set_queue(q: JobQueue | None) -> None:
    global _queue
    _queue = q
