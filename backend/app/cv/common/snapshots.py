"""
Saves a JPEG of the frame at the moment an incident gets confirmed --
gives your faculty something concrete to look at ("here's the exact
frame where the intrusion was confirmed") instead of just a number in a
table.
"""

from pathlib import Path

import cv2

from app.core import config


def save_snapshot(frame, video_id: str, track_id: int, ts_sec: float) -> str:
    """Writes the given frame to disk under OUTPUTS_DIR/<video_id>/snapshots/
    and returns the saved file's path as a string, for storing on the
    Incident row."""
    snap_dir = Path(config.OUTPUTS_DIR) / video_id / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)

    filename = f"track{track_id}_{ts_sec:.1f}s.jpg"
    snap_path = snap_dir / filename

    cv2.imwrite(str(snap_path), frame)
    return str(snap_path)