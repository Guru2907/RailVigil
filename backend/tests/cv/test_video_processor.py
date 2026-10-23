import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.errors import ZoneUnavailable
from app.cv.intrusion.video_processor import process_video


def _make_synthetic_video(path: str, width=320, height=240, fps=10, seconds=3):
    """Draws a plain video of a white square sliding across a black
    background -- won't be detected as 'person'/'car' by real YOLO
    (it's not a real object), but proves the PIPELINE runs end-to-end
    without crashing: video in, video out, no exceptions."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
    for i in range(fps * seconds):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        x = 10 + i * 3
        cv2.rectangle(frame, (x, 100), (x + 40, 140), (255, 255, 255), -1)
        writer.write(frame)
    writer.release()


def test_pipeline_runs_without_crashing(tmp_path):
    video_path = str(tmp_path / "synthetic.mp4")
    output_path = str(tmp_path / "annotated.mp4")
    _make_synthetic_video(video_path)

    zone_points = {"points": [[0, 0], [320, 0], [320, 240], [0, 240]]}

    class EmptyTracker:
        def reset(self):
            pass

        def track(self, frame):
            return []

    incidents = process_video(
        video_path=video_path,
        zone_points=zone_points,
        video_id="test123",
        output_video_path=output_path,
        tracker=EmptyTracker(),
    )

    assert isinstance(incidents, list)          # doesn't crash, returns a list
    assert Path(output_path).exists()            # annotated video got written


def test_pipeline_rejects_missing_zone_instead_of_using_full_frame(tmp_path):
    video_path = str(tmp_path / "missing-zone.mp4")
    _make_synthetic_video(video_path)

    try:
        process_video(
            video_path=video_path,
            zone_points=None,
            video_id="missing-zone",
            output_video_path=str(tmp_path / "annotated.mp4"),
        )
    except ZoneUnavailable as exc:
        assert "No railway safety zone" in exc.message
    else:
        raise AssertionError("missing zone must not silently become the full frame")
