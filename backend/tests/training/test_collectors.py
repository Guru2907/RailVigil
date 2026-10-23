"""Collector rules (offline): India check, registering photos, train-only data,
Mapillary filters, Commons licence/India checks, TACO conversion."""

import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "training"))

import collect_commons as cc  # noqa: E402
import collect_mapillary as cm  # noqa: E402
import import_taco as taco  # noqa: E402
import rvdata as rv  # noqa: E402


@pytest.mark.parametrize("lat, lon", [
    (19.076, 72.877),   # Mumbai
    (18.94, 72.83),     # Mumbai CST, on the coast
    (28.61, 77.21),     # Delhi
    (22.57, 88.36),     # Kolkata
    (13.08, 80.27),     # Chennai, on the coast
    (12.97, 77.59),     # Bengaluru
    (17.38, 78.47),     # Hyderabad
    (31.63, 74.87),     # Amritsar, near the Pakistan border
    (23.83, 91.28),     # Agartala, near the Bangladesh border
    (26.76, 83.37),     # Gorakhpur, near the Nepal border
    (8.52, 76.94),      # Thiruvananthapuram
])
def test_indian_cities_are_in_india(lat, lon):
    assert rv.in_india(lat, lon)


@pytest.mark.parametrize("lat, lon", [
    (23.81, 90.41),     # Dhaka
    (22.36, 91.83),     # Chittagong
    (24.90, 91.87),     # Sylhet
    (27.71, 85.32),     # Kathmandu
    (31.52, 74.35),     # Lahore
    (24.86, 67.01),     # Karachi
    (6.93, 79.86),      # Colombo
    (9.66, 80.01),      # Jaffna
    (27.47, 89.64),     # Thimphu
    (16.87, 96.19),     # Yangon
])
def test_neighbouring_countries_are_not_india(lat, lon):
    assert not rv.in_india(lat, lon)


@pytest.fixture
def dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(rv, "IMAGES", tmp_path / "images")
    return tmp_path


def _photo(path, colour=(10, 20, 30)):
    Image.new("RGB", (32, 24), colour).save(path)
    return path


def test_register_image_dedupes_and_uses_source_location(dataset):
    rows = []
    meta = {"source": "mapillary", "licence": "CC BY-SA 4.0", "author": "someone", "lat": 19.0, "lon": 72.8,
            "location_source": "mapillary", "original_name": "mapillary_1.jpg"}
    image_id = rv.register_image(_photo(dataset / "a.jpg"), meta, rows)
    assert image_id and (dataset / "images" / f"{image_id}.jpg").is_file()
    assert rows[0]["lat"] == "19.000000" and rows[0]["location_source"] == "mapillary" and rows[0]["role"] == ""
    assert rv.register_image(_photo(dataset / "copy.jpg"), meta, rows) is None   # same pixels, same bytes
    assert len(rows) == 1


def test_register_image_requires_a_licence(dataset):
    with pytest.raises(ValueError):
        rv.register_image(_photo(dataset / "a.jpg"), {"source": "own", "licence": ""}, [])


def _row(image_id, **kw):
    return {**{k: "" for k in rv.MANIFEST_FIELDS}, "image_id": image_id, "added_at": "2026-10-23T00:00:00+00:00", **kw}


def test_train_only_rows_always_go_to_train():
    rows = [_row(f"{i:012x}", role=rv.TRAIN_ONLY) for i in range(200)] + [_row(f"{i + 1000:012x}") for i in range(200)]
    rv.assign_splits(rows)
    assert {r["split"] for r in rows if r["role"] == rv.TRAIN_ONLY} == {"train"}
    assert {r["split"] for r in rows if not r["role"]} == set(rv.SPLITS)
    assert rv.split_leaks(rows) == []


def test_train_only_row_in_test_is_reported_as_a_leak():
    rows = [_row("aaaaaaaaaaaa", role=rv.TRAIN_ONLY, split="test")]
    assert rv.split_leaks(rows) == ["train-only aaaaaaaaaaaa"]


# --- Mapillary filters -------------------------------------------------------

def test_camera_must_face_the_track_unless_on_it():
    assert cm.faces_track(3, None, 0)            # standing on the track: any direction
    assert cm.faces_track(25, 10, 350)           # 20 degrees off: facing it
    assert not cm.faces_track(25, 180, 0)        # looking away
    assert not cm.faces_track(25, None, 0)       # unknown direction, off the track


def test_bearing_and_angle_helpers():
    assert cm.bearing_deg(0, 0, 0, 10) == pytest.approx(0)
    assert cm.bearing_deg(0, 0, 10, 0) == pytest.approx(90)
    assert cm.angle_diff(350, 10) == pytest.approx(20)


def test_spacing_between_kept_photos():
    assert cm.far_enough(0, 0, [(150, 0)])
    assert not cm.far_enough(0, 0, [(60, 50)])


def test_sample_points_every_250_m():
    from shapely.geometry import LineString
    pts = cm.sample_points([LineString([(0, 0), (1000, 0)])])
    assert [p.x for p in pts] == [0, 250, 500, 750, 1000]


# --- Commons -------------------------------------------------------------------

def _commons_page(title="File:Slum by railway track, Mumbai.jpg", licence="CC BY-SA 4.0", cats=("Slums in Mumbai",),
                  coords=None, width=2000, mime="image/jpeg"):
    page = {
        "title": title,
        "categories": [{"title": f"Category:{c}"} for c in cats],
        "imageinfo": [{"mime": mime, "width": width, "thumburl": "https://upload/x.jpg",
                       "descriptionurl": "https://commons.wikimedia.org/wiki/" + title,
                       "extmetadata": {"LicenseShortName": {"value": licence},
                                       "Artist": {"value": '<a href="u">Jane Doe</a>'}}}],
    }
    if coords:
        page["coordinates"] = [{"lat": coords[0], "lon": coords[1]}]
    return page


def test_commons_accepts_free_indian_photo():
    meta = cc.candidate(_commons_page())
    assert meta["licence"] == "CC BY-SA 4.0" and meta["author"] == "Jane Doe" and meta["lat"] is None


@pytest.mark.parametrize("licence, ok", [
    ("CC BY-SA 4.0", True), ("CC BY 2.0", True), ("CC0", True), ("Public domain", True), ("FAL", True),
    ("CC BY-NC-SA 2.0", False), ("CC BY-ND 4.0", False), ("All rights reserved", False),
])
def test_commons_licences(licence, ok):
    assert cc.is_free(licence) is ok


def test_commons_rejects_foreign_or_unplaced_photos():
    assert cc.candidate(_commons_page(cats=("Slums in Dhaka", "Bangladesh"))) is None
    assert cc.candidate(_commons_page(title="File:Slum by tracks.jpg", cats=("Slums and rail tracks",))) is None
    assert cc.candidate(_commons_page(coords=(23.81, 90.41))) is None          # Dhaka coordinates win
    assert cc.candidate(_commons_page(cats=("Railways",), coords=(19.05, 72.84)))["lat"] == 19.05


def test_commons_rejects_maps_and_small_files():
    assert cc.candidate(_commons_page(title="File:Mumbai suburban railway map.jpg")) is None
    assert cc.candidate(_commons_page(width=400)) is None
    assert cc.candidate(_commons_page(mime="image/svg+xml")) is None


# --- TACO ------------------------------------------------------------------------

def test_taco_items_become_debris_and_tiny_items_are_dropped():
    data = {
        "images": [{"id": 1, "width": 100, "height": 50, "file_name": "batch_1/1.jpg"}],
        "annotations": [
            {"image_id": 1, "area": 500, "segmentation": [[10, 10, 40, 10, 40, 30]]},   # 10 % of the photo
            {"image_id": 1, "area": 5, "segmentation": [[1, 1, 2, 1, 2, 2]]},           # 0.1 %: dropped
        ],
    }
    [entry] = taco.taco_labels(data).values()
    [(cls, pts)] = entry["labels"]
    assert rv.CLASSES[cls] == "debris_waste"
    assert pts[1] == pytest.approx((0.4, 0.2))


def test_taco_rotated_downloads_are_detected():
    assert taco.same_frame(640, 480, 4000, 3000)
    assert not taco.same_frame(480, 640, 4000, 3000)
