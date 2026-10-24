"""Camera location on video upload, and intrusion incidents on the GIS map."""

import json

import pytest
from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.db.models.incident import Incident
from app.db.models.video import Video
from app.main import app
from app.services import job_queue
from app.services.job_queue import JobQueue

SQUARE = [[10, 10], [150, 10], [150, 110], [10, 110]]


@pytest.fixture
def client():
    job_queue.set_queue(JobQueue(runner=lambda *a: None, recover=lambda: [], worker_count=1))
    with TestClient(app) as c:
        yield c
    job_queue.set_queue(None)


def upload(client, path, **form):
    with open(path, "rb") as f:
        return client.post("/api/videos", files={"video": ("clip.mp4", f, "video/mp4")},
                           data={"zone_points": json.dumps(SQUARE), **form})


def add_incident(video_id, severity="high"):
    db = SessionLocal()
    try:
        inc = Incident(video_id=video_id, track_id=1, object_class="person", event_type="human_intrusion",
                       severity=severity, risk_score=55.0, start_frame=0, end_frame=10, start_ts=0.0, end_ts=1.0,
                       dwell_time_sec=1.0, max_penetration=0.8, avg_penetration=0.6, is_persistent=False)
        db.add(inc)
        db.commit()
        return inc.id
    finally:
        db.close()


def test_upload_stores_camera_location(client, synthetic_video):
    r = upload(client, synthetic_video(), latitude="26.85", longitude="80.95")
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["latitude"], body["longitude"]) == (26.85, 80.95)


def test_upload_without_location_is_fine(client, synthetic_video):
    r = upload(client, synthetic_video())
    assert r.status_code == 200 and r.json()["latitude"] is None


@pytest.mark.parametrize("form", [{"latitude": "26.85"}, {"latitude": "95", "longitude": "80"}])
def test_bad_camera_location_is_422(client, synthetic_video, form):
    r = upload(client, synthetic_video(), **form)
    assert r.status_code == 422 and "latitude and longitude" in r.json()["detail"]


def test_map_shows_incidents_of_located_videos_only(client, synthetic_video):
    located = upload(client, synthetic_video(), latitude="26.85", longitude="80.95").json()["id"]
    unlocated = upload(client, synthetic_video()).json()["id"]
    inc = add_incident(located)
    add_incident(unlocated)

    feats = client.get("/api/map/features", params={"layers": "sites,intrusions"}).json()["features"]
    intrusions = [f for f in feats if f["properties"]["kind"] == "intrusion_incident"]
    assert [f["properties"]["incident_id"] for f in intrusions] == [inc]
    assert intrusions[0]["geometry"]["coordinates"] == [80.95, 26.85]
    assert intrusions[0]["id"] == f"inc-{inc}"

    # Default layer is sites only; bbox filters intrusions too.
    assert all(f["properties"]["kind"] == "encroachment_site"
               for f in client.get("/api/map/features").json()["features"])
    far = client.get("/api/map/features", params={"layers": "intrusions", "bbox": "70,10,71,11"}).json()
    assert far["features"] == []


def test_unknown_layer_is_422(client):
    assert client.get("/api/map/features", params={"layers": "sites,trains"}).status_code == 422


def test_video_location_columns_exist():
    assert {"latitude", "longitude"} <= set(Video.__table__.columns.keys())
