"""Shared test setup.

app.core.config reads environment variables ONCE, when it is first imported.
So the temporary database/folders below are set at the very top of this file,
before any test module can import `app`. That way tests never touch the real
railvigil.db or the real outputs/ folder.

(MODELS_DIR is left alone on purpose: the one end-to-end test that runs real
YOLO needs the real weights file.)

Database: a throwaway SQLite file by default. Set TEST_DATABASE_URL to run the
same suite against PostgreSQL (backend/scripts/test_postgres.ps1 does this
from backend/.env); that database's tables are emptied between tests.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

_TMP = Path(tempfile.mkdtemp(prefix="railvigil-tests-"))
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["DATA_DIR"] = str(_TMP / "data")
os.environ["OUTPUTS_DIR"] = str(_TMP / "outputs")
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import SessionLocal, init_db  # noqa: E402
from app.db.models.incident import Incident  # noqa: E402
from app.db.models.video import Video  # noqa: E402
from app.db.repositories import video_repository  # noqa: E402
from app.utils.file_utils import raw_dir, raw_video_path  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    """Create the schema once per test run, using the real migrations."""
    init_db()


@pytest.fixture(autouse=True)
def _clean_tables():
    """Every test starts with empty tables."""
    db = SessionLocal()
    try:
        db.query(Incident).delete()
        db.query(Video).delete()
        db.commit()
    finally:
        db.close()
    yield


# --- helpers ---------------------------------------------------------------

def write_synthetic_video(path, width=320, height=240, fps=10, seconds=2) -> str:
    """A small valid video: a white square sliding over black. Real YOLO
    won't detect anything in it; it only needs to be a readable video."""
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for i in range(fps * seconds):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        x = 10 + i * 3
        cv2.rectangle(frame, (x, 100), (x + 40, 140), (255, 255, 255), -1)
        writer.write(frame)
    writer.release()
    return str(path)


def make_video_row(filename="clip.mp4", status="queued", attempts=0, with_file=True) -> str:
    """Insert a Video row directly (and a dummy file for it) and return its id."""
    db = SessionLocal()
    try:
        video = video_repository.create_video(
            db, filename=filename, original_filename=filename,
            zone_json=json.dumps({"points": [[0, 0], [100, 0], [100, 100]]}), camera_label=None,
        )
        video.status = status
        video.attempts = attempts
        db.commit()
        video_id = video.id
    finally:
        db.close()
    if with_file:
        raw_dir().mkdir(parents=True, exist_ok=True)
        raw_video_path(filename).write_bytes(b"not a real video; the pipeline is faked in these tests")
    return video_id


def get_video(video_id: str) -> Video:
    db = SessionLocal()
    try:
        video = video_repository.get_video(db, video_id)
        db.expunge(video)
        return video
    finally:
        db.close()


def count_incidents(video_id: str) -> int:
    db = SessionLocal()
    try:
        return db.query(Incident).filter(Incident.video_id == video_id).count()
    finally:
        db.close()


@pytest.fixture
def synthetic_video(tmp_path):
    def _make(**kwargs):
        return write_synthetic_video(tmp_path / "upload.mp4", **kwargs)
    return _make
