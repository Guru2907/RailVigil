"""Phase 2b end to end through the API: upload photos -> background job ->
findings, sites, reports, map and stats. The real photo queue and job runner
run; only the YOLO models are replaced by a fake detector, so no weights are
needed (works in CI)."""

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core import config
from app.cv.common.model_registry import ModelNotAvailable
from app.cv.encroachment.detector import Detection
from app.cv.encroachment.taxonomy import STRUCTURE_TEMPORARY, VEGETATION
from app.db.database import SessionLocal
from app.db.models.encroachment import Media
from app.main import app
from app.services import image_jobs, job_queue, storage_service
from app.services.job_queue import JobQueue

# 200x100 photos; railway land = bottom half (normalized zone).
ZONE = json.dumps([[0, 0.5], [1, 0.5], [1, 1], [0, 1]])
HUT = Detection(STRUCTURE_TEMPORARY, "hut", 0.8, (20, 60, 80, 95), ["fake@1"])       # fully inside -> critical
BUSH = Detection(VEGETATION, "bush", 0.7, (120, 30, 180, 70), ["fake@1"])            # half inside  -> low
SHACK = Detection(STRUCTURE_TEMPORARY, "shack", 0.75, (100, 55, 150, 95), ["fake@1"])  # fully inside -> critical
HUT_EDGE = Detection(STRUCTURE_TEMPORARY, "hut", 0.8, (20, 20, 80, 60), ["fake@1"])    # 25 % inside  -> low
BLR = (12.9784, 77.5702)
METRES_PER_DEG_LAT = 111_320.0


class FakeDetector:
    detections = [HUT]
    error = None

    def detect(self, image):
        if FakeDetector.error:
            raise FakeDetector.error
        return list(FakeDetector.detections)

    def model_versions(self):
        return {"fake": "1"}


@pytest.fixture
def api():
    FakeDetector.detections, FakeDetector.error = [HUT], None
    job_queue.set_queue(JobQueue(runner=lambda *a: None, recover=lambda: [], worker_count=1))
    queue = JobQueue(runner=image_jobs.run_image_job, tracker_factory=FakeDetector,
                     recover=lambda: [], worker_count=1)
    image_jobs.set_image_queue(queue)
    with TestClient(app) as client:
        yield client, queue
    image_jobs.set_image_queue(None)
    job_queue.set_queue(None)


_counter = iter(range(1, 10_000))


def photo(tmp_path, shade=None, gps=None) -> str:
    """A small JPEG; every call gets a different shade so files differ."""
    shade = shade if shade is not None else next(_counter) % 250
    path = tmp_path / f"p{shade}_{next(_counter)}.jpg"
    if gps is None:
        cv2.imwrite(str(path), np.full((100, 200, 3), shade, dtype=np.uint8))
    else:
        exif = Image.Exif()
        exif[0x8825] = gps
        Image.new("RGB", (200, 100), (shade, shade, shade)).save(path, exif=exif)
    return str(path)


def upload(client, *paths, zone=ZONE, zone_format="normalized", **form):
    data = {**form, "zone_format": zone_format}
    if zone is not None:
        data["zone_points"] = zone
    handles = [open(p, "rb") for p in paths]
    try:
        files = [("files", (Path(p).name, h, "image/jpeg")) for p, h in zip(paths, handles, strict=True)]
        return client.post("/api/media", files=files, data=data)
    finally:
        for h in handles:
            h.close()


def at(metres_north: float) -> dict:
    return {"latitude": BLR[0] + metres_north / METRES_PER_DEG_LAT, "longitude": BLR[1]}


def processed(client, queue, response) -> list[dict]:
    assert response.status_code == 200, response.text
    assert queue.wait_idle(timeout=30)
    return [client.get(f"/api/media/{m['id']}").json() for m in response.json()]


# --- photos without a location ---------------------------------------------------

def test_photo_without_location_is_analysed_but_gets_no_site(api, tmp_path):
    client, queue = api
    (media,) = processed(client, queue, upload(client, photo(tmp_path)))

    assert media["status"] == "done" and media["location_source"] == "none"
    assert media["model_versions"] == {"fake": "1"}
    assert media["zone"]["source"] == "manual"
    (finding,) = media["findings"]
    assert (finding["cls"], finding["severity"], finding["site_id"]) == (STRUCTURE_TEMPORARY, "critical", None)

    assert client.get(media["original_url"]).status_code == 200
    annotated = client.get(media["annotated_url"])
    assert annotated.status_code == 200 and annotated.content[:2] == b"\xff\xd8"   # a JPEG
    assert client.get(finding["crop_url"]).headers["content-type"] == "image/jpeg"

    assert client.get("/api/map/features").json() == {"type": "FeatureCollection", "features": []}
    reports = client.get("/api/reports").json()
    assert [(r["reason"], r["site_id"]) for r in reports] == [("critical_finding", None)]


# --- located photos, sites and reports --------------------------------------------

def test_located_photo_creates_a_site_a_report_and_a_map_point(api, tmp_path):
    client, queue = api
    (media,) = processed(client, queue, upload(client, photo(tmp_path), **at(0)))
    assert media["location_source"] == "pin"
    site_id = media["findings"][0]["site_id"]
    assert site_id

    (report,) = client.get("/api/reports").json()
    assert report["reason"] == "new_site" and report["report_no"].startswith("RV-ENC-")

    features = client.get("/api/map/features").json()["features"]
    assert len(features) == 1
    assert features[0]["geometry"]["coordinates"] == pytest.approx([BLR[1], BLR[0]])
    props = features[0]["properties"]
    assert (props["site_id"], props["latest_report_no"]) == (site_id, report["report_no"])
    assert props["thumbnail_url"].endswith("/crop")


def test_second_photo_10m_away_joins_the_site_60m_starts_a_new_one(api, tmp_path):
    client, queue = api
    FakeDetector.detections = [BUSH]                                # low severity: no critical reports
    first = processed(client, queue, upload(client, photo(tmp_path), **at(0)))[0]["findings"][0]["site_id"]
    near = processed(client, queue, upload(client, photo(tmp_path), **at(10)))[0]["findings"][0]["site_id"]
    far = processed(client, queue, upload(client, photo(tmp_path), **at(60)))[0]["findings"][0]["site_id"]

    assert near == first and far != first
    site = client.get(f"/api/encroachment/sites/{first}").json()
    assert site["finding_count"] == 2 and len(site["findings"]) == 2
    assert [r["reason"] for r in client.get("/api/reports").json()] == ["new_site", "new_site"]


def test_exif_gps_is_used_when_there_is_no_pin(api, tmp_path):
    client, queue = api
    gps = {1: "N", 2: (12.0, 58.0, 40.8), 3: "E", 4: (77.0, 34.0, 12.0)}
    (media,) = processed(client, queue, upload(client, photo(tmp_path, gps=gps), latitude=28.6, longitude=77.2))
    assert media["location_source"] == "exif"
    assert media["latitude"] == pytest.approx(12.978, abs=1e-3)


def test_same_file_uploaded_twice_is_one_photo(api, tmp_path):
    client, queue = api
    path = photo(tmp_path)
    first = upload(client, path).json()[0]
    queue.wait_idle(timeout=30)
    second = upload(client, path, path).json()
    assert [m["id"] for m in second] == [first["id"], first["id"]]
    assert all(m["duplicate"] for m in second) and first["duplicate"] is False
    assert len(client.get("/api/media").json()) == 1


# --- report rules: one event, one report -------------------------------------------

def reasons(client) -> list[str]:
    return sorted(r["reason"] for r in client.get("/api/reports").json())


def test_several_huts_at_one_spot_in_one_photo_are_one_report(api, tmp_path):
    client, queue = api
    FakeDetector.detections = [HUT, SHACK]                       # two critical huts, same class, same pin
    (media,) = processed(client, queue, upload(client, photo(tmp_path), **at(0)))
    assert len({f["site_id"] for f in media["findings"]}) == 1
    assert reasons(client) == ["new_site"]

    processed(client, queue, upload(client, photo(tmp_path), **at(5)))   # site already critical
    assert reasons(client) == ["new_site"]


def test_site_escalating_to_critical_gets_a_report(api, tmp_path):
    client, queue = api
    FakeDetector.detections = [HUT_EDGE]                          # low severity first
    processed(client, queue, upload(client, photo(tmp_path), **at(0)))
    FakeDetector.detections = [HUT]                               # same place, now critical
    processed(client, queue, upload(client, photo(tmp_path), **at(3)))
    assert reasons(client) == ["critical_finding", "new_site"]
    site = client.get("/api/encroachment/sites").json()[0]
    assert site["max_severity"] == "critical" and site["finding_count"] == 2


def test_unlocated_photo_with_several_critical_findings_is_one_report(api, tmp_path):
    client, queue = api
    FakeDetector.detections = [HUT, SHACK]
    processed(client, queue, upload(client, photo(tmp_path)))
    assert reasons(client) == ["critical_finding"]


# --- review workflow -----------------------------------------------------------------

def test_site_review_workflow_and_reopening(api, tmp_path):
    client, queue = api
    (media,) = processed(client, queue, upload(client, photo(tmp_path), **at(0)))
    site_id = media["findings"][0]["site_id"]
    url = f"/api/encroachment/sites/{site_id}"

    r = client.patch(url, json={"status": "resolved"})
    assert r.status_code == 409 and "cannot move" in r.json()["detail"]
    assert client.patch(url, json={"status": "deleted"}).status_code == 422
    assert client.patch("/api/encroachment/sites/nope", json={"status": "verified"}).status_code == 404

    for status in ("under_review", "verified", "action_taken", "resolved"):
        r = client.patch(url, json={"status": status, "note": f"moved to {status}", "actor": "SSE Bengaluru"})
        assert r.status_code == 200, r.text
    site = r.json()
    assert site["status"] == "resolved"
    assert [h["to_status"] for h in site["history"]] == [
        "reported", "under_review", "verified", "action_taken", "resolved"]
    assert site["history"][-1]["actor"] == "SSE Bengaluru"

    processed(client, queue, upload(client, photo(tmp_path), **at(5)))     # found again
    site = client.get(url).json()
    assert site["status"] == "reported"
    assert [r["reason"] for r in site["reports"]][0] == "re_encroached"


def test_site_and_map_filters(api, tmp_path):
    client, queue = api
    processed(client, queue, upload(client, photo(tmp_path), **at(0)))
    FakeDetector.detections = [BUSH]
    processed(client, queue, upload(client, photo(tmp_path), latitude=28.6139, longitude=77.2090))   # Delhi

    around_blr = f"{BLR[1] - 0.01},{BLR[0] - 0.01},{BLR[1] + 0.01},{BLR[0] + 0.01}"
    assert len(client.get("/api/map/features", params={"bbox": around_blr}).json()["features"]) == 1
    assert len(client.get("/api/map/features", params={"severity": "critical"}).json()["features"]) == 1
    assert len(client.get("/api/encroachment/sites", params={"cls": VEGETATION}).json()) == 1
    assert len(client.get("/api/encroachment/sites", params={"status": "reported,under_review"}).json()) == 2
    assert client.get("/api/map/features", params={"bbox": "1,2,3"}).status_code == 422
    assert client.get("/api/map/features", params={"bbox": "10,10,5,5"}).status_code == 422


def test_report_detail_and_findings_list(api, tmp_path):
    client, queue = api
    processed(client, queue, upload(client, photo(tmp_path), **at(0)))
    (report,) = client.get("/api/reports").json()
    detail = client.get(f"/api/reports/{report['report_no']}").json()
    assert detail["site"]["id"] == detail["finding"]["site_id"]
    assert detail["media"]["status"] == "done"
    assert client.get("/api/reports/RV-ENC-1999-000001").status_code == 404
    assert len(client.get("/api/encroachment/findings", params={"severity": "critical"}).json()) == 1
    assert client.get("/api/encroachment/findings", params={"severity": "low"}).json() == []


def test_stats_summary(api, tmp_path):
    client, queue = api
    processed(client, queue, upload(client, photo(tmp_path), **at(0)))
    processed(client, queue, upload(client, photo(tmp_path)))
    stats = client.get("/api/stats/summary").json()
    enc = stats["encroachment"]
    assert enc["photos_by_status"] == {"done": 2}
    assert enc["findings_total"] == 2 and enc["findings_without_location"] == 1
    assert (enc["sites_total"], enc["sites_open"], enc["critical_open_sites"]) == (1, 1, 1)
    assert enc["reports_total"] == 2 and enc["reports_today"] == 2
    assert "incidents_total" in stats["intrusion"]


# --- rejected uploads -------------------------------------------------------------------

def stored_media_folders() -> set[str]:
    folder = storage_service.root() / "media"
    return {p.name for p in folder.iterdir()} if folder.exists() else set()


def test_one_bad_file_rejects_the_whole_batch_and_keeps_nothing(api, tmp_path):
    client, _ = api
    bad = tmp_path / "notes.jpg"
    bad.write_text("not an image", encoding="utf-8")
    r = upload(client, photo(tmp_path), str(bad))
    assert r.status_code == 422 and "notes.jpg" in r.json()["detail"]
    assert client.get("/api/media").json() == []
    assert stored_media_folders() == set()


@pytest.mark.parametrize("name,status", [("plan.pdf", 415), ("photo.gif", 415)])
def test_wrong_file_type(api, tmp_path, name, status):
    client, _ = api
    path = tmp_path / name
    path.write_bytes(b"x")
    assert upload(client, str(path)).status_code == status


def test_limits(api, tmp_path, monkeypatch):
    client, _ = api
    monkeypatch.setattr(config, "MAX_IMAGE_MB", 0.0001)
    assert upload(client, photo(tmp_path)).status_code == 413
    monkeypatch.setattr(config, "MAX_IMAGE_MB", 25)
    monkeypatch.setattr(config, "MAX_IMAGES_PER_UPLOAD", 1)
    assert upload(client, photo(tmp_path), photo(tmp_path)).status_code == 422


@pytest.mark.parametrize("form,needle", [
    ({"zone": None}, "No railway safety zone"),
    ({"latitude": 12.9}, "latitude and longitude"),
    ({"latitude": 95, "longitude": 77}, "latitude and longitude"),
    ({"zone_format": "metres"}, "zone_format"),
    ({"zone": "[[0,0],[1,0]]"}, "at least 3 points"),
])
def test_bad_zone_or_location_is_422(api, tmp_path, form, needle):
    client, _ = api
    r = upload(client, photo(tmp_path), **form)
    assert r.status_code == 422 and needle in r.json()["detail"]
    assert stored_media_folders() == set()


def test_unknown_media_and_missing_files_are_404(api):
    client, _ = api
    assert client.get("/api/media/nope").status_code == 404
    assert client.get("/api/encroachment/findings/nope/crop").status_code == 404
    db = SessionLocal()
    try:
        db.add(Media(id="a" * 32, sha256="b" * 64, status="queued", original_key="media/aaa/photo.jpg"))
        db.commit()
    finally:
        db.close()
    assert client.get(f"/api/media/{'a' * 32}/annotated").status_code == 404


# --- failures and recovery ----------------------------------------------------------------

@pytest.mark.parametrize("error,message", [
    (RuntimeError("boom"), "Processing failed unexpectedly"),
    (ModelNotAvailable("missing"), "models are not installed"),
])
def test_failed_job_is_recorded_with_a_safe_message(api, tmp_path, error, message):
    client, queue = api
    FakeDetector.error = error
    (media,) = processed(client, queue, upload(client, photo(tmp_path)))
    assert media["status"] == "failed" and message in media["error"]
    assert media["findings"] == [] and media["annotated_url"] is None
    assert "boom" not in media["error"]


def test_recovery_requeues_and_gives_up(tmp_path, monkeypatch):
    db = SessionLocal()
    try:
        ok = Media(id="1" * 32, sha256="1" * 64, status="processing", attempts=1,
                   original_key=storage_service.put_bytes("media/1/photo.jpg", b"x"))
        crashy = Media(id="2" * 32, sha256="2" * 64, status="processing", attempts=config.MAX_JOB_ATTEMPTS,
                       original_key=storage_service.put_bytes("media/2/photo.jpg", b"x"))
        gone = Media(id="3" * 32, sha256="3" * 64, status="queued", original_key="media/3/photo.jpg")
        db.add_all([ok, crashy, gone])
        db.commit()
    finally:
        db.close()

    assert image_jobs.recover_unfinished_images() == ["1" * 32]
    db = SessionLocal()
    try:
        status = {m.id[0]: (m.status, m.error) for m in db.query(Media).all()}
    finally:
        db.close()
    assert status["1"] == ("queued", None)
    assert status["2"][0] == "failed" and "too many times" in status["2"][1]
    assert status["3"][0] == "failed" and "missing" in status["3"][1]
