"""
Orchestrates the whole "someone uploaded a video" workflow:

1. Create a Video row (status="uploaded")
2. Run process_video() in a BACKGROUND THREAD -- so the upload request
   returns immediately with a video id, instead of the browser hanging
   for however long YOLO takes to chew through the whole video
3. On success: bulk-save the incidents, mark the video "done"
4. On failure: mark it "failed" with the error message, so the
   frontend can show that instead of hanging forever
"""

import threading
import traceback
from pathlib import Path

from app.core import config
from app.cv.video_processor import process_video
from app.db.repositories import video_repository, incident_repository
from app.db.database import SessionLocal


def _output_video_path(video_id: str) -> str:
    return str(Path(config.OUTPUTS_DIR) / video_id / "annotated.mp4")


def _run_processing(video_id: str, video_path: str, zone_points: list):
    """This function runs INSIDE the background thread. It makes its
    OWN database session -- SQLAlchemy sessions aren't safe to share
    across threads, so we can't reuse the session from the route that
    kicked this off."""
    db = SessionLocal()
    try:
        video_repository.update_video_status(db, video_id, "processing")

        output_path = _output_video_path(video_id)
        incidents = process_video(
            video_path=video_path,
            zone_points=zone_points,
            video_id=video_id,
            output_video_path=output_path,
        )

        if incidents:
            incident_repository.bulk_create(db, video_id, incidents)

        video_repository.update_video_status(db, video_id, "done", output_video_path=output_path)

    except Exception as exc:  # noqa: BLE001 -- any pipeline failure gets recorded, not swallowed
        video_repository.update_video_status(
            db, video_id, "failed", error=f"{exc}\n{traceback.format_exc()}"
        )
    finally:
        db.close()


def start_video_processing(db, video_path: str, original_filename: str,
                            zone_points: list, zone_json: str, camera_label: str | None = None):
    """Called by the API route. Creates the Video row SYNCHRONOUSLY (so
    the route can return a real video id right away), then hands off
    the slow part to a background thread."""
    filename = Path(video_path).name
    video = video_repository.create_video(
        db, filename=filename, original_filename=original_filename,
        zone_json=zone_json, camera_label=camera_label,
    )

    thread = threading.Thread(
        target=_run_processing,
        args=(video.id, video_path, zone_points),
        daemon=True,
    )
    thread.start()

    return video