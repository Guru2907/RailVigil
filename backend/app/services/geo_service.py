"""Where a photo was taken: GPS from its EXIF data, or a pin the user dropped.

Priority: EXIF GPS -> map pin -> none. A photo without a location is still
analysed and its findings stored, but it gets no site and no map point.
"""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

from app.core.errors import ValidationFailed

GPS_IFD = 0x8825
EXIF_IFD = 0x8769
DATETIME_ORIGINAL = 0x9003
EARTH_RADIUS_M = 6_371_008.8
IST = timezone(timedelta(hours=5, minutes=30), "IST")


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    source: str   # "exif" | "pin"


def valid_coordinates(lat, lon) -> bool:
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180


def _to_degrees(dms, ref) -> float | None:
    try:
        degrees, minutes, seconds = (float(v) for v in dms)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    value = degrees + minutes / 60 + seconds / 3600
    return -value if str(ref).upper() in ("S", "W") else value


def exif_location(path: Path | str) -> Location | None:
    """GPS position stored in the photo, or None if absent or unusable."""
    try:
        with Image.open(path) as img:
            gps = img.getexif().get_ifd(GPS_IFD)
    except (OSError, ValueError):
        return None
    if not gps or 2 not in gps or 4 not in gps:
        return None
    lat = _to_degrees(gps[2], gps.get(1, "N"))
    lon = _to_degrees(gps[4], gps.get(3, "E"))
    if lat is None or lon is None or not valid_coordinates(lat, lon) or (lat == 0 and lon == 0):
        return None   # (0, 0) is what many cameras write when they had no fix
    return Location(round(lat, 7), round(lon, 7), "exif")


def exif_captured_at(path: Path | str) -> datetime | None:
    """DateTimeOriginal from the photo. EXIF has no time zone; it is read as
    Indian Standard Time, where these photos are taken, and stored as UTC."""
    try:
        with Image.open(path) as img:
            raw = img.getexif().get_ifd(EXIF_IFD).get(DATETIME_ORIGINAL)
        local = datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
    except (OSError, ValueError, TypeError):
        return None
    return local.replace(tzinfo=IST).astimezone(UTC)


def resolve_location(path: Path | str, pin_lat=None, pin_lon=None) -> Location | None:
    """EXIF GPS first, then the user's pin, otherwise None. A pin given with
    only one coordinate, or out of range, is rejected."""
    exif = exif_location(path)
    if exif is not None:
        return exif
    if pin_lat is None and pin_lon is None:
        return None
    if pin_lat is None or pin_lon is None or not valid_coordinates(pin_lat, pin_lon):
        raise ValidationFailed("latitude and longitude must both be given, within -90..90 and -180..180.")
    return Location(round(float(pin_lat), 7), round(float(pin_lon), 7), "pin")


def distance_m(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in metres (haversine); used where PostGIS is not available."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))
