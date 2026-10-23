"""Polygon helpers for the encroachment rule.

Objects and zones are shapely polygons in image pixels. An object's polygon
is its mask outline when the model is a segmentation model (the trained
RailVigil model), otherwise its bounding box (the pretrained baseline).
"""

from shapely.geometry import Polygon, box
from shapely.validation import make_valid


def box_polygon(bbox) -> Polygon:
    x1, y1, x2, y2 = bbox
    return box(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def object_polygon(bbox, outline=None):
    """The object's mask outline if the model gave a usable one, else its box."""
    if outline is not None and len(outline) >= 3:
        poly = Polygon(outline)
        if not poly.is_valid:
            poly = poly.buffer(0)  # repairs self-crossing mask outlines into (multi)polygons
        if poly.area > 0:
            return poly
    return box_polygon(bbox)


def zone_polygon(points) -> Polygon:
    """A usable polygon even if the drawn outline crosses itself."""
    poly = Polygon(points)
    if not poly.is_valid:
        poly = make_valid(poly)
    return poly


def overlap_ratio(obj: Polygon, zone: Polygon) -> tuple[float, float]:
    """(share of the object's area inside the zone, overlapping area in px²)."""
    if obj.area <= 0:
        return 0.0, 0.0
    inter = obj.intersection(zone).area
    return inter / obj.area, inter


def iou(a: Polygon, b: Polygon) -> float:
    union = a.union(b).area
    return a.intersection(b).area / union if union > 0 else 0.0
