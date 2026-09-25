"""
The orchestrator. Doesn't know HOW detection/tracking/zone/risk work
internally -- it just calls each piece in order, frame by frame, and
collects the final results. This is why splitting into separate files
is worth it: this file stays short and readable.

Video Upload -> video_service -> video_processor (THIS FILE) ->
    detector -> tracker -> zone_engine -> temporal_engine -> risk_engine
    -> snapshots -> incident_service -> database
"""

import subprocess
import time
from pathlib import Path

import imageio_ffmpeg

import cv2
import numpy as np

from app.core import config
from app.cv.tracker import Tracker
from app.cv.temporal_engine import TemporalEngine
from app.cv.frame_processor import FrameProcessor
from app.cv.risk_engine import compute_risk_score, is_persistent, classify_event_type, severity_from_score


def _build_zone_polygon(zone_points: list) -> np.ndarray:
    return np.array(zone_points, dtype=np.int32)


def _zone_mask(zone_poly: np.ndarray, frame_shape) -> np.ndarray:
    h, w = frame_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [zone_poly], 1)
    return mask


def _make_browser_playable(path: str) -> None:
    """Re-encode the OpenCV output to H.264 so browsers can play it.
    If ffmpeg fails, the original file is kept."""
    src = Path(path)
    tmp = src.with_name("annotated_h264.mp4")
    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-y", "-i", str(src), "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-preset", "veryfast", "-movflags", "+faststart", "-an", str(tmp)],
            check=True, capture_output=True,
        )
        tmp.replace(src)
    except Exception as exc:  # noqa: BLE001
        print(f"H.264 conversion skipped: {exc}")
        tmp.unlink(missing_ok=True)


def process_video(video_path: str, zone_points: list, video_id: str,
                   output_video_path: str, zone_label: str = "safety-zone",
                   progress_cb=None) -> list[dict]:
    """Runs the full pipeline on one video. Returns a list of plain
    dicts -- one per confirmed incident -- ready to be handed to
    incident_service for saving to the database."""

    zone_poly = _build_zone_polygon(zone_points)
    tracker = Tracker()
    temporal_engine = TemporalEngine()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    zmask = _zone_mask(zone_poly, (height, width))

    frame_processor = FrameProcessor(tracker, zone_poly, zmask, zone_label, temporal_engine, video_id)

    Path(output_video_path).parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    frame_idx = 0
    t0 = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        ts_sec = frame_idx / fps

        # Only run the (expensive) detection+tracking on every Nth frame.
        # Frames in between are written to the output unmodified -- fine
        # since a few unannotated frames aren't noticeable at video speed.
        if frame_idx % config.FRAME_SAMPLE_INTERVAL == 0:
            frame = frame_processor.process(frame, frame_idx, ts_sec)

        writer.write(frame)
        frame_idx += 1

        if progress_cb and frame_idx % 30 == 0:
            progress_cb(frame_idx, total_frames)

    # video ended -- close out anything still active
    temporal_engine.finalize_all()

    cap.release()
    writer.release()
    _make_browser_playable(output_video_path)

    elapsed = time.time() - t0
    print(f"Processed {frame_idx} frames in {elapsed:.1f}s")

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