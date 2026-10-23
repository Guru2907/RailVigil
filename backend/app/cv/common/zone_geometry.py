"""
Defines the railway safety zone and answers two questions for any
detected object's bounding box:

1. Is it inside the zone at all? (point_in_zone)
2. HOW MUCH of it is inside the zone? (penetration_ratio)

Question 2 matters because two objects can both be "inside" but
very differently -- one just barely clipping the zone's edge (15%
overlap) vs. one mostly inside it (70%). That distinction feeds
risk_engine.py later.
"""

import cv2
import numpy as np


def bbox_feet_point(xyxy) -> tuple:
    """Returns the bottom-center point of a bounding box -- i.e. roughly
    where the object's feet/base touch the ground. This is a better
    proxy for "is this object standing on the track" than the box's
    center point, which could be up near a person's head."""
    x1, y1, x2, y2 = xyxy
    return (int((x1 + x2) / 2), int(y2))


def point_in_zone(point, zone_poly: np.ndarray, margin_px: int = 0) -> bool:
    """Is this single point inside the zone polygon?"""
    dist = cv2.pointPolygonTest(zone_poly, point, True)
    return dist >= -margin_px


def zone_mask(zone_poly: np.ndarray, frame_shape) -> np.ndarray:
    """Rasterizes the zone polygon into a 0/1 grid the same size as the
    video frame. Computed ONCE per video (not per frame) and reused --
    the zone doesn't move, no reason to redraw it every frame."""
    h, w = frame_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [zone_poly], 1)
    return mask


def penetration_ratio(xyxy, zmask: np.ndarray) -> float:
    """What fraction of this bounding box's area overlaps the zone?
    0.0 = fully outside, 1.0 = fully inside."""
    h, w = zmask.shape
    x1, y1, x2, y2 = [int(v) for v in xyxy]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return 0.0

    box_area = (x2 - x1) * (y2 - y1)
    if box_area <= 0:
        return 0.0

    overlap = int(zmask[y1:y2, x1:x2].sum())
    return min(1.0, overlap / box_area)


def box_iou(a, b) -> float:
    """Intersection-over-union of two axis-aligned boxes in xyxy form.
    Returns 0.0 when there is no overlap or either box has zero area."""
    ax1, ay1, ax2, ay2 = (float(v) for v in a)
    bx1, by1, bx2, by2 = (float(v) for v in b)

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter <= 0.0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0.0:
        return 0.0
    return inter / union
