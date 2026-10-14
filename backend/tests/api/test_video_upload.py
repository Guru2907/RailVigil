"""POST /api/videos: every way an upload can be rejected, and the happy path.

The queue is replaced with one whose runner does nothing, so a successful
upload stays `queued` and these tests are deterministic.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.main import app
from app.services import job_queue
from app.services.job_queue import JobQueue
from app.utils.file_utils import raw_dir
from conftest import get_video

SQUARE = [[10, 10], [200, 10], [200, 150], [10, 150]]   # fits the 320x240 synthetic video


@pytest.fixture
def client():
    job_queue.set_queue(JobQueue(runner=lambda *a: None, recover=lambda: [], worker_count=1))
    with TestClient(app) as c:                           # `with` runs startup/shutdown (lifespan)
        yield c
    job_queue.set_queue(None)


def files_on_disk() -> set[str]:
    return {p.name for p in raw_dir().glob("*")} if raw_dir().exists() else set()


def upload(client, path, zone=SQUARE, name="clip.mp4", **form):
    data = {"zone_points": zone if isinstance(zone, str) else json.dumps(zone), **form}
    with open(path, "rb") as f:
        return client.post("/api/videos", files={"video": (name, f, "video/mp4")}, data=data)


# --- success ----------------------------------------------------------------------

def test_valid_upload_is_accepted_and_queued(client, synthetic_video):
    r = upload(client, synthetic_video(), camera_label="  Platform 2  ")

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued"
    assert body["progress"] == 0.0
    assert body["camera_label"] == "Platform 2"           # trimmed

    video = get_video(body["id"])
    assert (video.width, video.height) == (320, 240)      # read from the real file
    assert video.fps == pytest.approx(10, abs=0.5)
    assert video.duration_sec == pytest.approx(2, abs=0.3)
    assert json.loads(video.zone_json)["points"] == SQUARE
    assert (raw_dir() / video.filename).exists()


def test_status_endpoint_reports_progress_field(client, synthetic_video):
    vid = upload(client, synthetic_video()).json()["id"]
    r = client.get(f"/api/videos/{vid}")
    assert r.status_code == 200
    assert {"status", "progress", "error"} <= set(r.json())


# --- rejected: file ---------------------------------------------------------------

def test_wrong_extension_is_415_and_nothing_is_saved(client, synthetic_video):
    before = files_on_disk()
    r = upload(client, synthetic_video(), name="clip.exe")
    assert r.status_code == 415
    assert ".exe" in r.json()["detail"]
    assert files_on_disk() == before


def test_text_file_renamed_to_mp4_is_422_and_deleted(client, tmp_path):
    fake = tmp_path / "notes.mp4"
    fake.write_text("this is not a video")
    before = files_on_disk()
    r = upload(client, fake)
    assert r.status_code == 422
    assert "video" in r.json()["detail"].lower()
    assert files_on_disk() == before


def test_oversized_upload_is_413_and_deleted(client, synthetic_video, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 0.001)  # about 1 KB
    before = files_on_disk()
    r = upload(client, synthetic_video())
    assert r.status_code == 413
    assert "too large" in r.json()["detail"].lower()
    assert files_on_disk() == before


def test_too_long_video_is_422_and_deleted(client, synthetic_video, monkeypatch):
    monkeypatch.setattr(config, "MAX_VIDEO_SEC", 1)
    before = files_on_disk()
    r = upload(client, synthetic_video(seconds=3))
    assert r.status_code == 422
    assert "maximum" in r.json()["detail"]
    assert files_on_disk() == before


# --- rejected: zone ----------------------------------------------------------------

@pytest.mark.parametrize("zone, expected", [
    ("not json at all", "valid JSON"),
    ('{"a": 1}', "list"),
    ([[0, 0], [10, 10]], "at least 3"),
    ([[0, 0], [10, 0], ["x", 5]], "Point 3"),
    ([[0, 0], [10, 0], [5]], "Point 3"),
    ([[0, 0], [10, 0], [5, True]], "Point 3"),
    ('[[0,0],[10,0],[NaN,5]]', "Point 3"),
    ([[0, 0], [10, 10], [20, 20]], "no area"),            # all on one line
    ([[5, 5], [5, 5], [5, 5]], "no area"),
])
def test_bad_zone_shape_is_422_and_file_never_saved(client, synthetic_video, zone, expected):
    before = files_on_disk()
    r = upload(client, synthetic_video(), zone=zone)
    assert r.status_code == 422
    assert expected in r.json()["detail"]
    assert files_on_disk() == before


def test_too_many_zone_points_is_422(client, synthetic_video, monkeypatch):
    monkeypatch.setattr(config, "MAX_ZONE_POINTS", 4)
    zone = [[0, 0], [100, 0], [100, 50], [50, 100], [0, 50]]
    r = upload(client, synthetic_video(), zone=zone)
    assert r.status_code == 422
    assert "at most 4" in r.json()["detail"]


def test_zone_outside_frame_is_422_and_file_deleted(client, synthetic_video):
    before = files_on_disk()
    r = upload(client, synthetic_video(), zone=[[0, 0], [1280, 0], [1280, 720]])
    assert r.status_code == 422
    assert "320x240" in r.json()["detail"]                # tells the user the real frame size
    assert files_on_disk() == before


def test_camera_label_too_long_is_422(client, synthetic_video):
    r = upload(client, synthetic_video(), camera_label="x" * (config.MAX_CAMERA_LABEL_LEN + 1))
    assert r.status_code == 422


def test_missing_fields_are_422(client, synthetic_video):
    with open(synthetic_video(), "rb") as f:
        r = client.post("/api/videos", files={"video": ("clip.mp4", f, "video/mp4")})
    assert r.status_code == 422


# --- back-pressure -----------------------------------------------------------------

def test_upload_refused_when_too_many_videos_are_waiting(client, synthetic_video, monkeypatch):
    monkeypatch.setattr(config, "MAX_QUEUED_JOBS", 1)
    assert upload(client, synthetic_video()).status_code == 200
    before = files_on_disk()
    r = upload(client, synthetic_video())
    assert r.status_code == 429
    assert files_on_disk() == before


# --- other endpoints ----------------------------------------------------------------

def test_unknown_video_is_404(client):
    assert client.get("/api/videos/nope").status_code == 404


def test_annotated_file_is_409_until_done(client, synthetic_video):
    vid = upload(client, synthetic_video()).json()["id"]
    r = client.get(f"/api/videos/{vid}/file")
    assert r.status_code == 409
    assert "queued" in r.json()["detail"]
