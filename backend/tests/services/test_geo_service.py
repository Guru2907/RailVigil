"""Photo locations: EXIF GPS first, then a map pin, otherwise none."""

from datetime import UTC, datetime

import pytest
from PIL import Image

from app.core.errors import ValidationFailed
from app.services import geo_service


def _jpeg(path, gps=None, taken=None):
    exif = Image.Exif()
    if gps is not None:
        exif[geo_service.GPS_IFD] = gps
    if taken is not None:
        exif[geo_service.EXIF_IFD] = {geo_service.DATETIME_ORIGINAL: taken}
    Image.new("RGB", (32, 24), (90, 90, 90)).save(path, exif=exif)
    return path


# Bengaluru City railway station, roughly: 12°58'40.8"N 77°34'12.0"E
BLR_GPS = {1: "N", 2: (12.0, 58.0, 40.8), 3: "E", 4: (77.0, 34.0, 12.0)}


def test_exif_gps_is_read_as_decimal_degrees(tmp_path):
    loc = geo_service.exif_location(_jpeg(tmp_path / "a.jpg", BLR_GPS))
    assert loc.source == "exif"
    assert loc.latitude == pytest.approx(12.978, abs=1e-3)
    assert loc.longitude == pytest.approx(77.570, abs=1e-3)


def test_southern_and_western_references_are_negative(tmp_path):
    gps = {1: "S", 2: (33.0, 52.0, 0.0), 3: "W", 4: (151.0, 12.0, 0.0)}
    loc = geo_service.exif_location(_jpeg(tmp_path / "b.jpg", gps))
    assert loc.latitude < 0 and loc.longitude < 0


def test_missing_or_null_island_gps_is_no_location(tmp_path):
    assert geo_service.exif_location(_jpeg(tmp_path / "none.jpg")) is None
    zero = {1: "N", 2: (0.0, 0.0, 0.0), 3: "E", 4: (0.0, 0.0, 0.0)}
    assert geo_service.exif_location(_jpeg(tmp_path / "zero.jpg", zero)) is None
    (tmp_path / "not-image.jpg").write_text("x", encoding="utf-8")
    assert geo_service.exif_location(tmp_path / "not-image.jpg") is None


def test_exif_capture_time_is_read_as_ist_and_stored_as_utc(tmp_path):
    taken = geo_service.exif_captured_at(_jpeg(tmp_path / "t.jpg", taken="2026:10:20 14:30:00"))
    assert taken == datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
    assert geo_service.exif_captured_at(_jpeg(tmp_path / "n.jpg")) is None


def test_exif_wins_over_pin_and_pin_is_used_otherwise(tmp_path):
    with_gps = _jpeg(tmp_path / "gps.jpg", BLR_GPS)
    without = _jpeg(tmp_path / "plain.jpg")
    assert geo_service.resolve_location(with_gps, 28.6, 77.2).source == "exif"
    pin = geo_service.resolve_location(without, 28.6139, 77.2090)
    assert (pin.source, pin.latitude, pin.longitude) == ("pin", 28.6139, 77.209)
    assert geo_service.resolve_location(without) is None


@pytest.mark.parametrize("lat,lon", [(28.6, None), (None, 77.2), (91, 77), (28, 181), ("abc", 77), (float("nan"), 1)])
def test_bad_pins_are_rejected(tmp_path, lat, lon):
    with pytest.raises(ValidationFailed):
        geo_service.resolve_location(_jpeg(tmp_path / "p.jpg"), lat, lon)


def test_distance_formula():
    # one degree of latitude is about 111.2 km
    assert geo_service.distance_m(12.0, 77.0, 13.0, 77.0) == pytest.approx(111_195, rel=1e-3)
    assert geo_service.distance_m(12.0, 77.0, 12.0, 77.0) == 0
