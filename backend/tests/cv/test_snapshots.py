import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.cv.snapshots import save_snapshot


def test_snapshot_is_written_to_disk():
    fake_frame = np.zeros((100, 100, 3), dtype="uint8")  # a plain black image
    path = save_snapshot(fake_frame, video_id="testvid123", track_id=7, ts_sec=4.2)

    assert Path(path).exists()
    assert "track7_4.2s.jpg" in path

    # cleanup after the test
    Path(path).unlink()