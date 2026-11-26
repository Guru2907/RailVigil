"""Output files are still served after the project folder has moved, and a
file that is really gone is a 404, never a server error."""

import pytest
from conftest import make_video_row
from fastapi.testclient import TestClient
from test_api_hardening import add_incident

from app.core import config
from app.db.database import SessionLocal
from app.db.models.video import Video
from app.main import app
from app.services import job_queue
from app.services.job_queue import JobQueue
from app.utils.file_utils import find_output_file


def old_path(*parts: str) -> str:
    """A path as it was stored on the old Windows drive."""
    return chr(92).join(("E:", "Dev", "RailVigil", "backend", "outputs", *parts))


@pytest.fixture
def client():
    job_queue.set_queue(JobQueue(runner=lambda *a: None, recover=lambda: [], worker_count=1))
    with TestClient(app) as c:
        yield c
    job_queue.set_queue(None)


def finished_video(stored_path_under_old_home: str) -> str:
    """A done video whose stored output path points at a folder that no longer exists."""
    video_id = make_video_row()
    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        video.status = "done"
        video.output_video_path = old_path(video_id, stored_path_under_old_home)
        db.commit()
    finally:
        db.close()
    return video_id


def put_in_outputs(video_id: str, *below: str) -> None:
    target = config.OUTPUTS_DIR.joinpath(video_id, *below)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"file content")


def test_annotated_video_is_found_after_the_folder_moved(client):
    video_id = finished_video("annotated.mp4")
    put_in_outputs(video_id, "annotated.mp4")
    r = client.get(f"/api/videos/{video_id}/file")
    assert r.status_code == 200 and r.content == b"file content"


def test_missing_annotated_video_is_404_not_a_server_error(client):
    r = client.get(f"/api/videos/{finished_video('annotated.mp4')}/file")
    assert r.status_code == 404
    assert "E:" not in r.text


def test_snapshot_is_found_after_the_folder_moved(client):
    video_id = make_video_row()
    stored = old_path(video_id, "snapshots", "track1_2.0s.jpg")
    incident_id = add_incident(video_id, snapshot_path=stored)
    assert client.get(f"/api/incidents/{incident_id}/snapshot").status_code == 404
    put_in_outputs(video_id, "snapshots", "track1_2.0s.jpg")
    assert client.get(f"/api/incidents/{incident_id}/snapshot").status_code == 200


def test_lookup_stays_inside_the_videos_own_folder():
    put_in_outputs("other", "annotated.mp4")
    assert find_output_file(old_path("abc", "..", "other", "annotated.mp4"), "abc") is None
    assert find_output_file(old_path("other", "annotated.mp4"), "abc") is None
    assert find_output_file(old_path("abc"), "abc") is None
    assert find_output_file(None, "abc") is None
    # written on Linux, read anywhere
    put_in_outputs("abc", "snapshots", "a.jpg")
    assert find_output_file("/srv/railvigil/outputs/abc/snapshots/a.jpg", "abc") is not None
