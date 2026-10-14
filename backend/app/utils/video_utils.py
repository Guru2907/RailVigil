"""Opens a saved upload with OpenCV just long enough to find out whether it
really is a video, and what size/length it is.

A file name or Content-Type says nothing reliable ("notes.txt" renamed to
"clip.mp4" passes both), so the only real test is: can the decoder read a
frame from it?
"""

import logging
from dataclasses import dataclass

import cv2

from app.core import config
from app.core.errors import ValidationFailed

logger = logging.getLogger(__name__)


@dataclass
class VideoMeta:
    width: int
    height: int
    fps: float
    duration_sec: float | None   # None when the container doesn't report a frame count


def probe_video(path: str) -> VideoMeta:
    cap = cv2.VideoCapture(path)
    try:
        if not cap.isOpened():
            raise ValidationFailed("This file could not be opened as a video.")

        ok, _frame = cap.read()
        if not ok:
            raise ValidationFailed("This file does not contain any readable video frames.")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    finally:
        cap.release()

    if width <= 0 or height <= 0:
        raise ValidationFailed("This video reports an invalid frame size.")

    duration = frames / fps if fps > 0 and frames > 0 else None
    if duration is None:
        # Some containers (e.g. browser-recorded .webm) don't store a frame
        # count. We accept them, but can't enforce MAX_VIDEO_SEC.
        logger.warning("video length unknown for %s; MAX_VIDEO_SEC not enforced", path)
    elif duration > config.MAX_VIDEO_SEC:
        raise ValidationFailed(
            f"Video is {duration:.0f}s long; the maximum is {config.MAX_VIDEO_SEC:.0f}s."
        )

    return VideoMeta(width=width, height=height, fps=fps, duration_sec=duration)
