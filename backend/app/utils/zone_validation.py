"""Validation for the safety-zone polygon that arrives with an upload.

It is checked in two steps because we only know the frame size AFTER the
video has been saved and opened:
  1. parse_zone_points      -- shape and numbers only (cheap, runs BEFORE the
                               file is written, so a bad request costs nothing)
  2. validate_zone_in_frame -- every point must lie inside the real frame

Messages are written for the person who drew the zone, not for developers.
"""

import json
import math

from app.core import config
from app.core.errors import ValidationFailed

MIN_ZONE_AREA_PX2 = 1.0


def _polygon_area(points: list[list[float]]) -> float:
    """Shoelace formula. Zero means the points are in a straight line or
    all the same spot, so there is no zone to monitor."""
    total = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def _is_number(v) -> bool:
    # bool is a subclass of int in Python; `true` is not a coordinate.
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def parse_zone_points(raw: str) -> list[list[float]]:
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        raise ValidationFailed("zone_points must be valid JSON, for example [[10,10],[200,10],[200,150]].")

    if not isinstance(data, list):
        raise ValidationFailed("zone_points must be a list of [x, y] points.")
    if len(data) < 3:
        raise ValidationFailed(f"A safety zone needs at least 3 points (got {len(data)}).")
    if len(data) > config.MAX_ZONE_POINTS:
        raise ValidationFailed(f"A safety zone can have at most {config.MAX_ZONE_POINTS} points (got {len(data)}).")

    points = []
    for i, p in enumerate(data, start=1):
        if not (isinstance(p, (list, tuple)) and len(p) == 2 and all(_is_number(v) for v in p)):
            raise ValidationFailed(f"Point {i} must be [x, y] with two numbers.")
        points.append([float(p[0]), float(p[1])])

    if _polygon_area(points) < MIN_ZONE_AREA_PX2:
        raise ValidationFailed("The safety zone has no area. Its points are on one line or in the same spot.")

    return points


def validate_zone_in_frame(points: list[list[float]], width: int, height: int) -> list[list[int]]:
    """Returns the points as whole pixels (what the pipeline uses)."""
    for i, (x, y) in enumerate(points, start=1):
        if not (0 <= x <= width and 0 <= y <= height):
            raise ValidationFailed(
                f"Point {i} ({x:.0f}, {y:.0f}) is outside the {width}x{height} video frame."
            )
    return [[round(x), round(y)] for x, y in points]
