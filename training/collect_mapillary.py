"""Collect Mapillary street-level photos that look at Indian railway tracks.

    python training/collect_mapillary.py --per-city 35
    python training/collect_mapillary.py --cities mumbai,kolkata --per-city 60

For each city: railway lines come from OpenStreetMap (Overpass API). Points
every ~250 m along them are searched on Mapillary, and a photo is kept only if:
  - it is not a panorama;
  - it was taken within 40 m of a track and the camera faces the track
    (or it stands on the track);
  - it lies inside India (rvdata.in_india);
  - it is at least 100 m from photos already kept (spread, not 30 frames of one spot).

Mapillary images are CC BY-SA 4.0; the photographer's username and the image
link are recorded in the manifest. Needs MAPILLARY_TOKEN in training/.env
(a READ-only client token); it is never printed.
"""

import argparse
import json
import math
import random
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import requests
import rvdata as rv

# (south, west, north, east)
CITIES = {
    "mumbai": (18.88, 72.78, 19.45, 73.20),
    "delhi": (28.45, 76.95, 28.85, 77.40),
    "kolkata": (22.40, 88.20, 22.80, 88.55),
    "chennai": (12.85, 80.05, 13.25, 80.32),
    "bengaluru": (12.85, 77.45, 13.10, 77.75),
    "hyderabad": (17.30, 78.30, 17.55, 78.60),
}
# Public Overpass servers, tried in order (they are often overloaded).
OVERPASS_SERVERS = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
GRAPH = "https://graph.mapillary.com/images"
FIELDS = "id,thumb_2048_url,computed_geometry,geometry,captured_at,creator,is_pano,compass_angle,computed_compass_angle"
USER_AGENT = "RailVigil-dataset/0.1 (academic project; https://github.com/Guru2907/RailVigil)"

SAMPLE_EVERY_M = 250
SEARCH_RADIUS_DEG = 0.0004   # ~45 m box around each sample point
MAX_TRACK_DIST_M = 40
ON_TRACK_M = 8               # closer than this: any camera direction is fine
MAX_ANGLE_DEG = 70           # camera direction vs direction to the nearest track point
MIN_SPACING_M = 100
BRIDGE_CLEARANCE_M = 15      # photos this close to a road / foot bridge are skipped


class Local:
    """Equirectangular metres around a city centre: accurate enough within a city."""

    def __init__(self, lat0, lon0):
        self.lat0, self.lon0 = lat0, lon0
        self.kx = 111320.0 * math.cos(math.radians(lat0))
        self.ky = 110540.0

    def xy(self, lon, lat):
        return ((lon - self.lon0) * self.kx, (lat - self.lat0) * self.ky)

    def lonlat(self, x, y):
        return (self.lon0 + x / self.kx, self.lat0 + y / self.ky)


def bearing_deg(x1, y1, x2, y2) -> float:
    """Compass bearing (0 = north, clockwise) from point 1 to point 2, local metres."""
    return math.degrees(math.atan2(x2 - x1, y2 - y1)) % 360


def angle_diff(a, b) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def faces_track(dist_m: float, camera_deg, to_track_deg: float) -> bool:
    if dist_m <= ON_TRACK_M:
        return True
    if camera_deg is None:
        return False
    return angle_diff(camera_deg, to_track_deg) <= MAX_ANGLE_DEG


def far_enough(x, y, kept, min_m=MIN_SPACING_M) -> bool:
    return all((x - kx) ** 2 + (y - ky) ** 2 >= min_m ** 2 for kx, ky in kept)


TILE_DEG = 0.06   # ~6.5 km squares: small enough for busy Overpass servers to answer


def city_tiles(bbox):
    """Tiles covering a city, centre first (dense track and the most street photos)."""
    s, w, n, e = bbox
    cy, cx = (s + n) / 2, (w + e) / 2
    tiles = []
    lat = s
    while lat < n:
        lon = w
        while lon < e:
            top, right = min(lat + TILE_DEG, n), min(lon + TILE_DEG, e)
            tiles.append((round(lat, 4), round(lon, 4), round(top, 4), round(right, 4)))
            lon += TILE_DEG
        lat += TILE_DEG
    return sorted(tiles, key=lambda t: ((t[0] + t[2]) / 2 - cy) ** 2 + ((t[1] + t[3]) / 2 - cx) ** 2)


def city_lines(bbox, local, want_points):
    """Railway lines and road/foot bridges for as many tiles as needed to give
    `want_points` sample points. Bridges are optional (a failed lookup only
    disables that filter for the tile); a tile whose railways cannot be fetched is skipped."""
    rails, bridges = [], []
    for tile in city_tiles(bbox):
        if len(sample_points(rails)) >= want_points:
            break
        s, w, n, e = tile
        tile_rails = _overpass_lines(
            f'way["railway"="rail"]["service"!~"yard|siding|spur|crossover"]({s},{w},{n},{e});', local,
            cache=f"rail_{s}_{w}_{n}_{e}")
        if tile_rails is None:
            print(f"  skipped tile {tile}: OpenStreetMap did not answer")
            continue
        rails += tile_rails
        # Road bridges and foot-over-bridges: photos taken on them look at the road, not the track below.
        bridges += _overpass_lines(f'way["bridge"]["highway"]({s},{w},{n},{e});', local,
                                   cache=f"bridges_{s}_{w}_{n}_{e}") or []
    return rails, bridges


def _overpass_lines(selector, local, cache):
    """OpenStreetMap ways as local-metre lines, or None if no server answered.
    Responses are cached under datasets/external/osm/, so reruns never ask again."""
    from shapely.geometry import LineString

    cache_file = rv.DATASETS / "external" / "osm" / f"{cache}.json"
    data = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.is_file() else None
    query = f"[out:json][timeout:90];{selector}out geom;"
    for url in OVERPASS_SERVERS if data is None else []:
        try:
            r = requests.post(url, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=120)
            r.raise_for_status()
            data = r.json()
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(data), encoding="utf-8")
            break
        except (requests.RequestException, ValueError) as exc:
            print(f"  Overpass {url.split('/')[2]} failed ({exc.__class__.__name__})")
            time.sleep(3)
    if data is None:
        return None
    lines = []
    for el in data.get("elements", []):
        pts = [local.xy(p["lon"], p["lat"]) for p in el.get("geometry", [])]
        if len(pts) >= 2:
            lines.append(LineString(pts))
    return lines


def sample_points(lines, every_m=SAMPLE_EVERY_M):
    pts = []
    for line in lines:
        n = max(1, int(line.length // every_m))
        pts.extend(line.interpolate(i * every_m) for i in range(n + 1) if i * every_m <= line.length)
    return pts


def search(token, lon, lat):
    d = SEARCH_RADIUS_DEG
    r = SESSION.get(GRAPH, params={
        "bbox": f"{lon - d},{lat - d},{lon + d},{lat + d}",
        "fields": FIELDS, "limit": 50,
    }, headers={"Authorization": f"OAuth {token}"}, timeout=60)
    if r.status_code == 429:
        time.sleep(30)
        return []
    r.raise_for_status()
    return r.json().get("data", [])


SESSION = requests.Session()


def search_many(token, lonlats, in_flight=8):
    """Search results per point, in order, with a few searches in flight at once."""
    with ThreadPoolExecutor(max_workers=in_flight) as pool:
        for i in range(0, len(lonlats), in_flight):
            yield from pool.map(lambda ll: search(token, *ll), lonlats[i:i + in_flight])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cities", default=",".join(CITIES))
    p.add_argument("--per-city", type=int, default=35)
    p.add_argument("--max-searches", type=int, default=600, help="Mapillary searches per city at most")
    args = p.parse_args()

    from shapely.geometry import Point
    from shapely.strtree import STRtree

    token = rv.load_secret("MAPILLARY_TOKEN")
    if not token:
        raise SystemExit("MAPILLARY_TOKEN not found in training/.env")

    rows = rv.read_manifest()
    known = {r["image_id"] for r in rows}
    seen_names = {r["original_name"] for r in rows if r["source"] == "mapillary"}
    tmp = Path(tempfile.mkdtemp(prefix="rv_mly_"))

    for city in args.cities.split(","):
        bbox = CITIES[city]
        local = Local((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
        lines, bridges = city_lines(bbox, local, args.max_searches)
        if not lines:
            print(f"{city}: no railway data from OpenStreetMap, skipped")
            continue
        tree = STRtree(lines)
        bridge_tree = STRtree(bridges) if bridges else None
        points = sample_points(lines)
        random.Random(f"railvigil-{city}").shuffle(points)
        s, w, n, e = bbox
        kept_xy = [local.xy(float(r["lon"]), float(r["lat"])) for r in rows
                   if r["source"] == "mapillary" and r["lon"]
                   and s <= float(r["lat"]) <= n and w <= float(r["lon"]) <= e]
        added = searches = 0
        print(f"{city}: {len(lines)} railway lines, {len(bridges)} bridges, {len(points)} sample points")
        for found in search_many(token, [local.lonlat(pt.x, pt.y) for pt in points[: args.max_searches]]):
            if len(kept_xy) >= args.per_city:
                break
            searches += 1
            for img in found:
                name = f"mapillary_{img['id']}.jpg"
                geom = img.get("computed_geometry") or img.get("geometry")
                if img.get("is_pano") or name in seen_names or not geom or not img.get("thumb_2048_url"):
                    continue
                ilon, ilat = geom["coordinates"]
                if not rv.in_india(ilat, ilon):
                    continue
                x, y = local.xy(ilon, ilat)
                here = Point(x, y)
                nearest = lines[int(tree.nearest(here))]
                dist = nearest.distance(here)
                if dist > MAX_TRACK_DIST_M:
                    continue
                if bridge_tree is not None:
                    bridge = bridges[int(bridge_tree.nearest(here))]
                    if bridge.distance(here) < BRIDGE_CLEARANCE_M:
                        continue
                target = nearest.interpolate(nearest.project(here))
                camera = img.get("computed_compass_angle", img.get("compass_angle"))
                if not faces_track(dist, camera, bearing_deg(x, y, target.x, target.y)):
                    continue
                if not far_enough(x, y, kept_xy):
                    continue
                path = tmp / name
                resp = SESSION.get(img["thumb_2048_url"], timeout=60)
                if not resp.ok:
                    continue
                path.write_bytes(resp.content)
                taken = img.get("captured_at")
                image_id = rv.register_image(path, {
                    "source": "mapillary",
                    "source_url": f"https://www.mapillary.com/app/?pKey={img['id']}",
                    "licence": "CC BY-SA 4.0",
                    "author": (img.get("creator") or {}).get("username", ""),
                    "lat": ilat, "lon": ilon, "location_source": "mapillary",
                    "captured_at": datetime.fromtimestamp(taken / 1000, UTC).isoformat() if taken else "",
                    "original_name": name,
                }, rows, known)
                seen_names.add(name)
                if image_id:
                    kept_xy.append((x, y))
                    added += 1
                    print(f"  + {name}  {dist:.0f} m from track")
                break  # one photo per sample point keeps the set spread out

        rv.write_manifest(rows)  # save after every city, so a crash loses little
        print(f"{city}: added {added} photos after {searches} searches")

    total = sum(1 for r in rows if r["source"] == "mapillary")
    print(f"\nMapillary photos in the manifest: {total}")


if __name__ == "__main__":
    main()
