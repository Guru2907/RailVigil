"""POST /api/videos: every way an upload can be rejected, and the happy path.

The queue is replaced with one whose runner does nothing, so a successful
upload stays `queued` and these tests are deterministic.
"""

import json

import pytest
from conftest import get_video
from fastapi.testclient import TestClient

from app.core import config
from app.main import app
from app.services import job_queue
from app.services.job_queue import JobQueue
from app.utils.file_utils import raw_dir

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
    data = dict(form)
    if zone is not None:
        data["zone_points"] = zone if isinstance(zone, str) else json.dumps(zone)
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
    zone = json.loads(video.zone_json)
    assert zone["format"] == "normalized"
    assert zone["source"] == "manual"
    assert zone["points"][0] == [10 / 320, 10 / 240]
    assert (raw_dir() / video.filename).exists()


def test_upload_accepts_sidecar_zone_when_manual_zone_is_absent(client, synthetic_video):
    sidecar = {"format": "normalized", "points": [[0.1, 0.1], [0.8, 0.1], [0.8, 0.8], [0.1, 0.8]]}

    response = upload(client, synthetic_video(), zone=None, zone_sidecar=json.dumps(sidecar))

    assert response.status_code == 200
    stored = json.loads(get_video(response.json()["id"]).zone_json)
    assert stored["source"] == "sidecar"
    assert stored["format"] == "normalized"


def test_upload_uses_camera_zone_when_manual_and_sidecar_are_absent(
    client, synthetic_video, monkeypatch
):
    monkeypatch.setenv(
        "CAMERA_ZONES",
        json.dumps({"Platform 2": {"format": "normalized", "points": [[0.1, 0.1], [0.8, 0.1], [0.8, 0.8]]}}),
    )

    response = upload(client, synthetic_video(), zone=None, camera_label="Platform 2")

    assert response.status_code == 200
    stored = json.loads(get_video(response.json()["id"]).zone_json)
    assert stored["source"] == "camera"


def test_upload_without_any_zone_source_awaits_zone(client, synthetic_video, monkeypatch):
    monkeypatch.delenv("CAMERA_ZONES", raising=False)

    response = upload(client, synthetic_video(), zone=None)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "awaiting_zone"
    assert body["has_output"] is False
    assert "output_video_path" not in body
    video = get_video(body["id"])
    assert video.zone_json is None


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


def test_upload_without_zone_is_awaiting_zone(client, synthetic_video):
    """Zone is optional at upload time; video parks as awaiting_zone."""
    with open(synthetic_video(), "rb") as f:
        r = client.post("/api/videos", files={"video": ("clip.mp4", f, "video/mp4")})
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_zone"


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


def test_put_zone_queues_awaiting_video(client, synthetic_video, monkeypatch):
    monkeypatch.delenv("CAMERA_ZONES", raising=False)
    created = upload(client, synthetic_video(), zone=None).json()
    assert created["status"] == "awaiting_zone"

    r = client.put(f"/api/videos/{created['id']}/zone", json={"zone_points": SQUARE})
    assert r.status_code == 200
    assert r.json()["status"] == "queued"
    assert get_video(created["id"]).zone_json is not None


def test_put_zone_404_409_422(client, synthetic_video, monkeypatch):
    monkeypatch.delenv("CAMERA_ZONES", raising=False)
    assert client.put("/api/videos/nope/zone", json={"zone_points": SQUARE}).status_code == 404

    queued = upload(client, synthetic_video(), zone=SQUARE).json()
    assert client.put(f"/api/videos/{queued['id']}/zone", json={"zone_points": SQUARE}).status_code == 409

    waiting = upload(client, synthetic_video(), zone=None).json()
    bad = client.put(f"/api/videos/{waiting['id']}/zone", json={"zone_points": [[0, 0], [1, 1]]})
    assert bad.status_code == 422


def test_video_out_exposes_has_output_not_path(client, synthetic_video):
    body = upload(client, synthetic_video(), zone=SQUARE).json()
    assert "output_video_path" not in body
    assert body["has_output"] is False
