"""Shared zone providers and pixel/normalized coordinate conversion."""

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

from app.core import config
from app.core.errors import ValidationFailed
from app.utils.zone_validation import parse_zone_points, validate_zone_in_frame


@dataclass(frozen=True)
class ResolvedZone:
    points: list[list[float]]
    source: str

    def to_pixels(self, width: int, height: int) -> list[list[int]]:
        pixels = [[x * width, y * height] for x, y in self.points]
        return validate_zone_in_frame(pixels, width, height)

    def as_record(self) -> dict:
        return {"format": "normalized", "points": self.points, "source": self.source}


def _normalized_points(points, coordinate_format: str, width: int, height: int):
    if width <= 0 or height <= 0:
        raise ValidationFailed("The video frame size is invalid; the zone cannot be resolved.")
    if coordinate_format == "pixel":
        points = parse_zone_points(json.dumps(points))
        pixels = validate_zone_in_frame(points, width, height)
        return [[x / width, y / height] for x, y in pixels]
    if coordinate_format != "normalized":
        raise ValidationFailed("Zone format must be 'pixel' or 'normalized'.")
    if not isinstance(points, list):
        raise ValidationFailed("zone_points must be a list of [x, y] points.")
    if len(points) < 3:
        raise ValidationFailed(f"A safety zone needs at least 3 points (got {len(points)}).")
    if len(points) > config.MAX_ZONE_POINTS:
        raise ValidationFailed(
            f"A safety zone can have at most {config.MAX_ZONE_POINTS} points (got {len(points)})."
        )
    for index, point in enumerate(points, start=1):
        if not (
            isinstance(point, (list, tuple))
            and len(point) == 2
            and all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                for value in point
            )
        ):
            raise ValidationFailed(f"Point {index} must be [x, y] with two numbers.")
        if any(value < 0 or value > 1 for value in point):
            raise ValidationFailed("Normalized zone coordinates must be between 0 and 1.")
    points = [[float(x), float(y)] for x, y in points]
    validate_zone_in_frame(
        parse_zone_points(json.dumps([[x * width, y * height] for x, y in points])),
        width, height,
    )
    return points


class ManualZoneProvider:
    def resolve(self, points, coordinate_format: str, width: int, height: int):
        if points is None:
            return None
        source = "manual"
        if isinstance(points, dict):
            coordinate_format = points.get("format", "pixel")
            source = points.get("source", source)
            points = points.get("points")
        normalized = _normalized_points(points, coordinate_format, width, height)
        return ResolvedZone(normalized, source)


class SidecarZoneProvider:
    def resolve(self, video_path, width: int, height: int, sidecar_data=None):
        if sidecar_data is not None:
            record = self._parse(sidecar_data)
        elif video_path is not None:
            path = Path(video_path)
            candidates = (path.with_suffix(".zone.json"), Path(f"{path}.zone.json"))
            sidecar = next((candidate for candidate in candidates if candidate.is_file()), None)
            if sidecar is None:
                return None
            try:
                record = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ValidationFailed(f"Could not read zone sidecar '{sidecar.name}'.") from exc
        else:
            return None

        zone = ManualZoneProvider().resolve(record, "pixel", width, height)
        return ResolvedZone(zone.points, "sidecar")

    @staticmethod
    def _parse(data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError as exc:
                raise ValidationFailed("Zone sidecar must contain valid JSON.") from exc
        if not isinstance(data, (dict, list)):
            raise ValidationFailed("Zone sidecar must contain a points list.")
        return data


class CameraZoneProvider:
    def __init__(self, zones: dict | None = None):
        self.zones = zones

    def resolve(self, camera_label: str | None, width: int, height: int):
        if not camera_label:
            return None
        zones = self.zones
        if zones is None:
            try:
                zones = json.loads(os.getenv("CAMERA_ZONES", "{}"))
            except ValueError as exc:
                raise ValidationFailed("CAMERA_ZONES must contain valid JSON.") from exc
        if not isinstance(zones, dict):
            raise ValidationFailed("CAMERA_ZONES must be a JSON object keyed by camera label.")
        if camera_label not in zones:
            return None
        record = zones[camera_label]
        if isinstance(record, dict):
            record = {"format": "normalized", **record}
        zone = ManualZoneProvider().resolve(record, "normalized", width, height)
        return ResolvedZone(zone.points, "camera")


class AutoZoneProvider:
    """Use an injected validated estimator; never guesses a frame."""

    def __init__(self, estimator=None):
        self.estimator = estimator

    def resolve(self, width: int, height: int):
        if self.estimator is None:
            return None
        candidate = self.estimator(width, height)
        if candidate is None:
            return None
        zone = ManualZoneProvider().resolve(candidate, "normalized", width, height)
        return ResolvedZone(zone.points, "auto")


class ZoneResolver:
    """Resolve zones in strict precedence order without whole-frame defaults."""

    def __init__(self, camera_zones: dict | None = None, auto_provider=None):
        self.manual = ManualZoneProvider()
        self.sidecar = SidecarZoneProvider()
        self.camera = CameraZoneProvider(camera_zones)
        self.auto = auto_provider or AutoZoneProvider()

    def resolve(
        self, width: int, height: int, *, manual_zone=None,
        manual_format: str = "pixel", sidecar_path=None, sidecar_data=None,
        camera_label: str | None = None,
    ) -> ResolvedZone:
        zone = self.manual.resolve(manual_zone, manual_format, width, height)
        if zone is not None:
            return zone
        zone = self.sidecar.resolve(sidecar_path, width, height, sidecar_data)
        if zone is not None:
            return zone
        zone = self.camera.resolve(camera_label, width, height)
        if zone is not None:
            return zone
        zone = self.auto.resolve(width, height)
        if zone is not None:
            return zone
        raise ValidationFailed(
            "No railway safety zone is available. Draw a zone, provide a .zone.json "
            "sidecar, or configure a zone for this camera."
        )


def stored_zone_to_pixels(record, width: int, height: int) -> tuple[list[list[int]], str]:
    """Read current normalized records and legacy pixel records."""
    if isinstance(record, str):
        try:
            record = json.loads(record)
        except ValueError as exc:
            raise ValidationFailed("The saved zone data is invalid.") from exc
    if isinstance(record, list):
        record = {"points": record}
    if not isinstance(record, dict):
        raise ValidationFailed("The saved zone data is invalid.")

    coordinate_format = record.get("format", "pixel")
    source = record.get("source", "legacy")
    zone = ManualZoneProvider().resolve(record.get("points"), coordinate_format, width, height)
    return zone.to_pixels(width, height), source
