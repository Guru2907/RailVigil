"""Dataset and metric helpers used by training/ (pure functions)."""

import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "training"))

import rvdata as rv  # noqa: E402

from app.cv.encroachment.taxonomy import CLASSES  # noqa: E402


def _row(image_id, lat="", lon="", group="", split=""):
    return {**{k: "" for k in rv.MANIFEST_FIELDS}, "image_id": image_id, "lat": lat, "lon": lon,
            "group": group, "split": split, "added_at": "2026-10-23T00:00:00+00:00"}


# --- manifest -----------------------------------------------------------------

def test_manifest_round_trip(tmp_path):
    path = tmp_path / "manifest.csv"
    rows = [_row("bbbbbbbbbbbb", "19.1", "72.9"), _row("aaaaaaaaaaaa")]
    rv.write_manifest(rows, path)
    back = rv.read_manifest(path)
    assert [r["image_id"] for r in back] == ["aaaaaaaaaaaa", "bbbbbbbbbbbb"]
    assert back[1]["lat"] == "19.1"
    assert not (tmp_path / "manifest.csv.tmp").exists()


def test_missing_manifest_is_empty(tmp_path):
    assert rv.read_manifest(tmp_path / "none.csv") == []


# --- EXIF --------------------------------------------------------------------

def test_exif_gps_and_time(tmp_path):
    img = Image.new("RGB", (8, 8))
    exif = img.getexif()
    exif[0x8825] = {1: "N", 2: (19.0, 4.0, 12.0), 3: "E", 4: (72.0, 50.0, 24.0)}
    exif[0x0132] = "2026:10:01 09:30:00"
    path = tmp_path / "gps.jpg"
    img.save(path, exif=exif)
    lat, lon, taken = rv.exif_info(path)
    assert lat == pytest.approx(19.07) and lon == pytest.approx(72.84)
    assert taken == "2026:10:01 09:30:00"


def test_no_exif(tmp_path):
    path = tmp_path / "plain.png"
    Image.new("RGB", (8, 8)).save(path)
    assert rv.exif_info(path) == (None, None, "")


# --- splits --------------------------------------------------------------------

def test_nearby_photos_and_manual_groups_share_a_place():
    rows = [
        _row("a00000000001", "19.07000", "72.84000"),
        _row("a00000000002", "19.07100", "72.84000"),   # ~111 m away -> same place
        _row("a00000000003", "19.08000", "72.84000"),   # ~1.1 km -> different place
        _row("a00000000004", group="kalyan-km42"),
        _row("a00000000005", group="kalyan-km42"),
        _row("a00000000006"),
    ]
    g = rv.place_groups(rows)
    assert g["a00000000001"] == g["a00000000002"] != g["a00000000003"]
    assert g["a00000000004"] == g["a00000000005"]
    assert len(set(g.values())) == 4


def test_chained_photos_join_one_place():
    # 1-2 and 2-3 are each 250 m apart (1-3 is 500 m): all one place.
    rows = [_row(f"b0000000000{i}", f"{19 + i * 0.00225:.5f}", "72.84") for i in range(3)]
    assert len(set(rv.place_groups(rows).values())) == 1


def test_splits_are_assigned_deterministically_and_cover_all():
    rows = [_row(f"{i:012x}") for i in range(300)]
    rv.assign_splits(rows)
    splits = [r["split"] for r in rows]
    assert set(splits) == set(rv.SPLITS)
    assert 0.6 < splits.count("train") / 300 < 0.8
    again = rv.assign_splits([_row(f"{i:012x}") for i in range(300)])
    assert [r["split"] for r in again] == splits


def test_existing_splits_are_frozen_and_new_photos_join_their_place():
    rows = [_row("c00000000001", "19.07", "72.84", split="test"), _row("c00000000002", "19.07001", "72.84")]
    rv.assign_splits(rows)
    assert [r["split"] for r in rows] == ["test", "test"]
    assert rv.split_leaks(rows) == []


def test_split_leak_is_detected():
    rows = [_row("d00000000001", group="x", split="train"), _row("d00000000002", group="x", split="test")]
    assert rv.split_leaks(rows) != []


# --- labels ----------------------------------------------------------------------

def test_labels_round_trip_and_box_lines(tmp_path):
    path = tmp_path / "l.txt"
    rv.write_labels(path, [(2, [(0.1, 0.1), (0.5, 0.1), (0.5, 0.4)])])
    [(cls, pts)] = rv.read_labels(path)
    assert cls == 2 and pts[1] == pytest.approx((0.5, 0.1))
    path.write_text("1 0.5 0.5 0.2 0.4\n")
    [(cls, pts)] = rv.read_labels(path)
    assert cls == 1 and pts[0] == pytest.approx((0.4, 0.3)) and pts[2] == pytest.approx((0.6, 0.7))


def test_empty_label_file_is_a_negative(tmp_path):
    path = tmp_path / "neg.txt"
    rv.write_labels(path, [])
    assert rv.read_labels(path) == []


def test_malformed_label_line_raises(tmp_path):
    path = tmp_path / "bad.txt"
    path.write_text("0 0.1 0.2 0.3\n")
    with pytest.raises(ValueError):
        rv.read_labels(path)


def test_class_remap_by_name_with_reordering_and_aliases():
    export = ["Vegetation", "debris", "structure_permanent", "Temporary Structure", "material_dump", "parked vehicle"]
    remap = rv.class_remap(export)
    assert [CLASSES[remap[i]] for i in range(len(export))] == [
        "vegetation", "debris_waste", "structure_permanent", "structure_temporary", "material_dump", "vehicle_parked"]
    with pytest.raises(ValueError, match="Unknown class"):
        rv.class_remap(["vegetation", "train"])


def test_image_id_from_tool_export_names():
    known = {"ab12cd34ef56"}
    assert rv.image_id_from_export_name("ab12cd34ef56_jpg.rf.0f9a8b.jpg", known) == "ab12cd34ef56"
    assert rv.image_id_from_export_name("AB12CD34EF56.JPG", known) == "ab12cd34ef56"
    assert rv.image_id_from_export_name("ffffffffffff.jpg", known) is None
    assert rv.image_id_from_export_name("IMG_1234.jpg", known) is None


# --- metrics -----------------------------------------------------------------------

def test_box_iou():
    assert rv.box_iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1
    assert rv.box_iou((0, 0, 10, 10), (5, 0, 15, 10)) == pytest.approx(1 / 3)
    assert rv.box_iou((0, 0, 1, 1), (2, 2, 3, 3)) == 0


def test_average_precision():
    assert rv.average_precision([True, True], 2) == pytest.approx(1.0)
    assert rv.average_precision([True, False, True], 2) == pytest.approx(0.5 * 1 + 0.5 * (2 / 3))
    assert rv.average_precision([False], 1) == 0


def test_evaluate_boxes_matches_each_ground_truth_once():
    gts = {"img": [("vegetation", (0, 0, 10, 10)), ("vegetation", (20, 20, 30, 30))]}
    preds = {"img": [
        ("vegetation", 0.9, (0, 0, 10, 10)),
        ("vegetation", 0.8, (1, 1, 10, 10)),       # duplicate of the first: false positive
        ("vegetation", 0.7, (20, 20, 30, 30)),
        ("debris_waste", 0.6, (50, 50, 60, 60)),   # no debris labelled: false positive
    ]}
    r = rv.evaluate_boxes(preds, gts)
    assert r["vegetation"]["tp"] == 2 and r["vegetation"]["n_pred"] == 3
    assert r["vegetation"]["recall"] == 1 and r["vegetation"]["precision"] == pytest.approx(2 / 3)
    assert r["debris_waste"]["tp"] == 0 and r["debris_waste"]["n_gt"] == 0


def test_polygon_box():
    assert rv.polygon_box([(0.1, 0.2), (0.5, 0.2), (0.3, 0.6)], 100, 50) == pytest.approx((10, 10, 50, 30))
