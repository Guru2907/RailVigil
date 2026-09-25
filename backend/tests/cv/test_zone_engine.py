import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.cv.zone_engine import bbox_feet_point, point_in_zone, zone_mask, penetration_ratio


def test_bbox_feet_point_is_bottom_center():
    box = np.array([10, 20, 30, 60])  # x1, y1, x2, y2
    x, y = bbox_feet_point(box)
    assert x == 20
    assert y == 60


def test_point_in_zone_square():
    zone = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.int32)
    assert point_in_zone((50, 50), zone) is True
    assert point_in_zone((150, 50), zone) is False


def test_penetration_ratio_full_overlap():
    zone = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.int32)
    mask = zone_mask(zone, (100, 100))
    box = np.array([10, 10, 40, 40])  # fully inside the zone
    ratio = penetration_ratio(box, mask)
    assert 0.95 <= ratio <= 1.0


def test_penetration_ratio_no_overlap():
    zone = np.array([[0, 0], [50, 0], [50, 50], [0, 50]], dtype=np.int32)
    mask = zone_mask(zone, (100, 100))
    box = np.array([60, 60, 90, 90])  # entirely outside the zone
    ratio = penetration_ratio(box, mask)
    assert ratio == 0.0