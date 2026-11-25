"""Security hardening: no static file mount, no server paths in API responses,
and CORS origins come from configuration."""

import cv2
import numpy as np
import pytest
from conftest import make_video_row
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import config
from app.db.database import SessionLocal
from app.db.models.incident import Incident
from app.main import app
from app.middleware.cors import add_cors
from app.services import job_queue
from app.services.job_queue import JobQueue


@pytest.fixture
def client():
    job_queue.set_queue(JobQueue(runner=lambda *a: None, recover=lambda: [], worker_count=1))
    with TestClient(app) as c:
        yield c
    job_queue.set_queue(None)


def add_incident(video_id, snapshot_path=None):
    db = SessionLocal()
    try:
        inc = Incident(video_id=video_id, track_id=1, object_class="person", event_type="human_intrusion",
                       severity="high", risk_score=55.0, start_frame=0, end_frame=10, start_ts=0.0, end_ts=1.0,
                       dwell_time_sec=1.0, max_penetration=0.8, avg_penetration=0.6, is_persistent=False,
                       zone_label="track zone",
                       snapshot_path=snapshot_path)
        db.add(inc)
        db.commit()
        return inc.id
    finally:
        db.close()


# --- 1. no static mount of the outputs folder ------------------------------------

def test_output_files_are_not_served_by_path(client):
    secret = config.OUTPUTS_DIR / "some-video" / "snapshots" / "track1.jpg"
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_bytes(b"not for direct download")
    assert client.get("/static/outputs/some-video/snapshots/track1.jpg").status_code == 404


# --- 2. no server paths in incident responses --------------------------------------

def test_incident_json_has_no_disk_path_only_a_flag(client, tmp_path):
    snap = tmp_path / "snap.jpg"
    cv2.imwrite(str(snap), np.zeros((8, 8, 3), np.uint8))
    video_id = make_video_row()
    with_snap = add_incident(video_id, snapshot_path=str(snap))
    without = add_incident(video_id)

    body = client.get(f"/api/incidents/{with_snap}").json()
    assert "snapshot_path" not in body and body["has_snapshot"] is True
    assert str(tmp_path) not in str(body)
    listed = {i["id"]: i for i in client.get("/api/incidents").json()}
    assert listed[without]["has_snapshot"] is False and "snapshot_path" not in listed[without]


def test_snapshot_is_still_served_by_its_endpoint(client, tmp_path):
    snap = tmp_path / "snap.jpg"
    cv2.imwrite(str(snap), np.zeros((8, 8, 3), np.uint8))
    incident_id = add_incident(make_video_row(), snapshot_path=str(snap))
    r = client.get(f"/api/incidents/{incident_id}/snapshot")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert client.get(f"/api/incidents/{add_incident(make_video_row())}/snapshot").status_code == 404


# --- 3. CORS origins from configuration ---------------------------------------------

def test_default_cors_origins_are_the_vite_dev_server():
    assert "http://localhost:5173" in config.CORS_ORIGINS


def test_only_configured_origins_are_allowed():
    tiny = FastAPI()
    add_cors(tiny, origins=["https://railvigil.example.org"])

    @tiny.get("/ping")
    def ping():
        return {"ok": True}

    c = TestClient(tiny)
    allowed = c.get("/ping", headers={"Origin": "https://railvigil.example.org"})
    refused = c.get("/ping", headers={"Origin": "http://localhost:5173"})
    assert allowed.headers.get("access-control-allow-origin") == "https://railvigil.example.org"
    assert "access-control-allow-origin" not in refused.headers
