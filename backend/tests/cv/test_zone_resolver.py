import json

import numpy as np
import pytest

from app.core.errors import ValidationFailed
from app.core.errors import ZoneUnavailable
from app.cv.common.zones import AutoZoneProvider, ResolvedZone, ZoneResolver, stored_zone_to_pixels

PIXEL_ZONE = [[10, 10], [200, 10], [200, 150], [10, 150]]
NORMALIZED_ZONE = [[0.03125, 1 / 24], [0.625, 1 / 24], [0.625, 0.625], [0.03125, 0.625]]


def test_manual_zone_precedes_sidecar_camera_and_auto(tmp_path):
    class UnreachableAuto:
        def resolve(self, width, height):
            raise AssertionError("lower-priority providers must not run")

    sidecar = tmp_path / "clip.zone.json"
    sidecar.write_text(json.dumps({"format": "normalized", "points": NORMALIZED_ZONE}))
    resolver = ZoneResolver(
        camera_zones={"Gate A": {"format": "normalized", "points": NORMALIZED_ZONE}},
        auto_provider=UnreachableAuto(),
    )

    zone = resolver.resolve(
        320, 240, manual_zone=PIXEL_ZONE, sidecar_path=tmp_path / "clip.mp4",
        camera_label="Gate A",
    )

    assert zone.source == "manual"
    np.testing.assert_allclose(zone.points, NORMALIZED_ZONE)


def test_sidecar_precedes_camera_zone(tmp_path):
    sidecar = tmp_path / "clip.zone.json"
    sidecar.write_text(json.dumps({"format": "normalized", "points": NORMALIZED_ZONE}))
    resolver = ZoneResolver(
        camera_zones={"Gate A": {"format": "normalized", "points": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8]]}}
    )

    zone = resolver.resolve(320, 240, sidecar_path=tmp_path / "clip.mp4", camera_label="Gate A")

    assert zone.source == "sidecar"
    np.testing.assert_allclose(zone.points, NORMALIZED_ZONE)


def test_camera_provider_resolves_configured_normalized_zone():
    zone = ZoneResolver(
        camera_zones={"Gate A": {"format": "normalized", "points": NORMALIZED_ZONE}}
    ).resolve(320, 240, camera_label="Gate A")

    assert zone.source == "camera"
    assert zone.to_pixels(320, 240) == PIXEL_ZONE


def test_camera_provider_precedes_auto_provider():
    class UnreachableAuto:
        def resolve(self, width, height):
            raise AssertionError("auto should not replace a configured camera zone")

    zone = ZoneResolver(
        camera_zones={"Gate A": NORMALIZED_ZONE},
        auto_provider=UnreachableAuto(),
    ).resolve(320, 240, camera_label="Gate A")

    assert zone.source == "camera"


def test_auto_provider_uses_only_a_validated_estimate():
    zone = ZoneResolver(
        camera_zones={},
        auto_provider=AutoZoneProvider(estimator=lambda width, height: NORMALIZED_ZONE),
    ).resolve(320, 240)

    assert zone.source == "auto"
    assert zone.to_pixels(320, 240) == PIXEL_ZONE


def test_pixel_coordinates_round_trip_through_normalized_storage():
    zone = ZoneResolver().resolve(320, 240, manual_zone=PIXEL_ZONE)

    np.testing.assert_allclose(zone.points, NORMALIZED_ZONE)
    assert zone.to_pixels(320, 240) == PIXEL_ZONE
    assert zone.as_record()["format"] == "normalized"


def test_legacy_pixel_record_remains_readable():
    points, source = stored_zone_to_pixels({"points": PIXEL_ZONE}, 320, 240)

    assert points == PIXEL_ZONE
    assert source == "legacy"


def test_normalized_record_preserves_source():
    record = {"format": "normalized", "points": NORMALIZED_ZONE, "source": "sidecar"}

    points, source = stored_zone_to_pixels(record, 320, 240)

    assert points == PIXEL_ZONE
    assert source == "sidecar"


def test_missing_zone_fails_instead_of_using_full_frame():
    with pytest.raises(ZoneUnavailable, match="No railway safety zone"):
        ZoneResolver(camera_zones={}).resolve(320, 240)


def test_invalid_lower_priority_sidecar_is_ignored_when_manual_zone_is_valid(tmp_path):
    sidecar = tmp_path / "clip.zone.json"
    sidecar.write_text("not-json")

    zone = ZoneResolver(camera_zones={}).resolve(
        320, 240, manual_zone=PIXEL_ZONE, sidecar_path=tmp_path / "clip.mp4"
    )

    assert zone.source == "manual"


def test_sidecar_accepts_legacy_pixel_point_lists(tmp_path):
    sidecar = tmp_path / "clip.zone.json"
    sidecar.write_text(json.dumps(PIXEL_ZONE))

    zone = ZoneResolver(camera_zones={}).resolve(320, 240, sidecar_path=tmp_path / "clip.mp4")

    assert zone == ResolvedZone(NORMALIZED_ZONE, "sidecar")
