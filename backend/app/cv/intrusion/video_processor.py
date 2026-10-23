"""
The orchestrator. Doesn't know HOW detection/tracking/zone/risk work
internally -- it just calls each piece in order, frame by frame, and
collects the final results. This is why splitting into separate files
is worth it: this file stays short and readable.

Video Upload -> video_service -> video_processor (THIS FILE) ->
    detector -> tracker -> zone_engine -> temporal_engine -> risk_engine
    -> snapshots -> incident_service -> database
"""

import logging
import subprocess
import time
from pathlib import Path

import imageio_ffmpeg

import cv2
import numpy as np

from app.core import config
from app.cv.common.tracker import Tracker
from app.cv.common.zone_geometry import zone_mask
from app.cv.common.zones import ZoneResolver
from app.cv.intrusion.temporal_engine import TemporalEngine
from app.cv.intrusion.frame_processor import FrameProcessor
from app.cv.intrusion.risk_engine import compute_risk_score, is_persistent, classify_event_type, severity_from_score

logger = logging.getLogger(__name__)


class ProcessingAborted(Exception):
    """Raised inside process_video when `abort_cb()` says to stop (e.g. the
    server is shutting down). It is not an error: the caller puts the video
    back in the queue so it is processed again after the restart."""


def _make_browser_playable(path: str) -> None:
    """Re-encode the OpenCV output to H.264 so browsers can play it.
    If ffmpeg fails, the original (mp4v) file is kept."""
    src = Path(path)
    tmp = src.with_name("annotated_h264.mp4")  # lives in this video's own folder, so no clashes
    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-y", "-i", str(src), "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-preset", "veryfast", "-movflags", "+faststart", "-an", str(tmp)],
            check=True, capture_output=True,
        )
        tmp.replace(src)
    except Exception as exc:  # noqa: BLE001
        logger.warning("H.264 conversion skipped: %s", exc)
        tmp.unlink(missing_ok=True)


def process_video(video_path: str, zone_points: list | dict | None, video_id: str,
                   output_video_path: str, zone_label: str = "safety-zone",
                   progress_cb=None, tracker: Tracker | None = None,
                   abort_cb=None, zone_format: str = "pixel",
                   camera_label: str | None = None) -> list[dict]:
    """Runs the full pipeline on one video. Returns a list of plain
    dicts -- one per confirmed incident -- ready to be handed to
    incident_service for saving to the database.

    tracker:   pass a long-lived Tracker (one per worker) to avoid reloading
               the YOLO weights for every video. Its state is reset here, so
               it is always safe to reuse. If omitted, a new one is created.
    abort_cb:  optional callable checked once per frame; when it returns True
               we stop and raise ProcessingAborted.
    """

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    try:
        zone = ZoneResolver().resolve(
            width, height, manual_zone=zone_points, manual_format=zone_format,
            sidecar_path=video_path, camera_label=camera_label,
        )
        zone_poly = np.array(zone.to_pixels(width, height), dtype=np.int32)
    except BaseException:
        cap.release()
        raise

    tracker = tracker or Tracker(class_filter=config.INTRUSION_CLASSES)
    tracker.reset()  # never inherit ids from a previous video
    temporal_engine = TemporalEngine()
    zmask = zone_mask(zone_poly, (height, width))  # rasterized once, reused every frame

    frame_processor = FrameProcessor(tracker, zone_poly, zmask, zone_label, temporal_engine, video_id)

    Path(output_video_path).parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    frame_idx = 0
    t0 = time.time()

    # try/finally so the video file and the writer are always released, even
    # if detection throws halfway through. Before this, a crash left both
    # open (on Windows that also keeps the files locked).
    try:
        while True:
            if abort_cb is not None and abort_cb():
                raise ProcessingAborted(video_id)

            ok, frame = cap.read()
            if not ok:
                break

            ts_sec = frame_idx / fps

            # Expensive detection+tracking only on every Nth frame; the frames
            # in between still get the overlay (zone + last boxes) so the
            # output video doesn't flicker.
            run_detection = frame_idx % config.FRAME_SAMPLE_INTERVAL == 0
            frame = frame_processor.process(frame, frame_idx, ts_sec, run_detection)

            writer.write(frame)
            frame_idx += 1

            if progress_cb and frame_idx % 30 == 0:
                progress_cb(frame_idx, total_frames)
    finally:
        cap.release()
        writer.release()

    # video ended -- close out anything still active
    temporal_engine.finalize_all()

    _make_browser_playable(output_video_path)

    elapsed = time.time() - t0
    logger.info("video %s: processed %d frames in %.1fs", video_id, frame_idx, elapsed)

    # Turn each closed TrackState into a plain dict ready for the database
    incidents = []
    for state in temporal_engine.get_closed_events():
        dwell = state.dwell_time()
        persistent = is_persistent(dwell)
        risk_score = compute_risk_score(state.max_penetration(), dwell, state.object_class)

        incidents.append({
            "track_id": state.track_id,
            "object_class": state.object_class,
            "event_type": classify_event_type(state.object_class, persistent),
            "severity": severity_from_score(risk_score),
            "is_persistent": persistent,
            "start_frame": state.start_frame,
            "end_frame": state.last_frame,
            "start_ts": round(state.start_ts, 2),
            "end_ts": round(state.last_ts, 2),
            "dwell_time_sec": round(dwell, 2),
            "max_penetration": round(state.max_penetration(), 3),
            "avg_penetration": round(state.avg_penetration(), 3),
            "risk_score": risk_score,
            "zone_label": zone_label,
            "snapshot_path": state.snapshot_path,
        })

    return incidents
