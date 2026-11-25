"""Labelling tools: the railway-zone class, blind test export, labeller agreement."""

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "training"))

import export_for_labelling as efl  # noqa: E402
import import_labels as il  # noqa: E402
import label_agreement as la  # noqa: E402
import rvdata as rv  # noqa: E402

STRUCT = rv.CLASSES.index("structure_permanent")
VEG = rv.CLASSES.index("vegetation")


def _box(x1, y1, x2, y2):
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


# --- railway zone ----------------------------------------------------------------

def test_railway_zone_maps_to_the_zone_index_not_a_class():
    remap = rv.class_remap(["vegetation", "railway_zone", "Railway Zone"])
    assert remap == {0: VEG, 1: rv.ZONE_INDEX, 2: rv.ZONE_INDEX}
    with pytest.raises(ValueError):
        rv.class_remap(["railway_track"])


def test_zone_is_split_off_and_a_stray_click_is_dropped():
    labels = [(STRUCT, _box(0.1, 0.1, 0.2, 0.2)),
              (rv.ZONE_INDEX, _box(0.0, 0.5, 1.0, 1.0)),       # the real zone
              (rv.ZONE_INDEX, _box(0.4, 0.4, 0.41, 0.41))]     # a stray click
    objects, pieces = il.split_zone(labels)
    assert objects == [(STRUCT, _box(0.1, 0.1, 0.2, 0.2))]
    assert pieces == [[[0.0, 0.5], [1.0, 0.5], [1.0, 1.0], [0.0, 1.0]]]
    assert il.split_zone([(STRUCT, _box(0, 0, 1, 1))])[1] is None


def test_zone_drawn_in_several_pieces_keeps_every_piece_largest_first():
    labels = [(rv.ZONE_INDEX, _box(0.0, 0.5, 0.3, 1.0)),       # one track
              (rv.ZONE_INDEX, _box(0.4, 0.5, 1.0, 1.0))]       # the other, larger
    _, pieces = il.split_zone(labels)
    assert [len(pieces), pieces[0][0], pieces[1][0]] == [2, [0.4, 0.5], [0.0, 0.5]]


def test_zone_iou_uses_the_union_of_pieces(tmp_path):
    whole = tmp_path / "whole.json"
    whole.write_text(json.dumps({"format": "normalized", "points": _box(0, 0.5, 1, 1)}))
    split = tmp_path / "split.json"
    halves = [_box(0, 0.5, 0.5, 1), _box(0.5, 0.5, 1, 1)]
    split.write_text(json.dumps({"format": "normalized", "points": halves[0], "pieces": halves}))
    assert la.zone_iou(whole, split) == pytest.approx(1.0)


def test_coco_export_with_a_zone_category():
    data = {
        "images": [{"id": 1, "file_name": "abcdef123456.jpg", "width": 100, "height": 100}],
        "categories": [{"id": 1, "name": "vegetation"}, {"id": 2, "name": "railway_zone"}],
        "annotations": [
            {"image_id": 1, "category_id": 1, "bbox": [10, 10, 20, 20], "segmentation": []},
            {"image_id": 1, "category_id": 2, "bbox": [0, 50, 100, 50],
             "segmentation": [[0, 50, 100, 50, 100, 100, 0, 100]]},
        ],
    }
    [labels] = rv.coco_labels(data).values()
    assert sorted(c for c, _ in labels) == [rv.ZONE_INDEX, VEG]


# --- blind export ------------------------------------------------------------------

def test_blind_export_has_only_images_of_the_split(tmp_path, monkeypatch):
    monkeypatch.setattr(rv, "DATASETS", tmp_path)
    (tmp_path / "images").mkdir()
    rows = []
    for i, (split, role) in enumerate([("test", ""), ("test", ""), ("train", ""), ("test", rv.TRAIN_ONLY)]):
        image_id = f"{i:012x}"
        Image.new("RGB", (8, 8)).save(tmp_path / "images" / f"{image_id}.jpg")
        rows.append({**{k: "" for k in rv.MANIFEST_FIELDS}, "image_id": image_id,
                     "file": f"images/{image_id}.jpg", "split": split, "role": role, "country": "India"})
    monkeypatch.setattr(rv, "read_manifest", lambda: rows)
    monkeypatch.setattr(sys, "argv", ["export_for_labelling.py"])
    efl.main()
    out = tmp_path / "upload" / "test_blind"
    assert sorted(p.name for p in (out / "images").iterdir()) == ["000000000000.jpg", "000000000001.jpg"]
    assert not (out / "labels").exists()                                 # no model guesses
    used = [c for c in rv.CLASSES if c != "debris_waste"]                 # waste is labelled material_dump
    assert (out / "classes.txt").read_text().split() == [*used, "railway_zone"]
    assert (out / "test_blind.zip").is_file()


# --- agreement ---------------------------------------------------------------------

def test_cohen_kappa():
    assert la.cohen_kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert la.cohen_kappa([True, True, False, False], [False, False, True, True]) == pytest.approx(-1.0)
    assert la.cohen_kappa([True] * 4, [True] * 4) == 1.0


def test_agreement_between_two_labellers(tmp_path):
    a, b = tmp_path / "A", tmp_path / "B"
    rv.write_labels(a / "p1.txt", [(STRUCT, _box(0.1, 0.1, 0.3, 0.3)), (VEG, _box(0.5, 0.5, 0.9, 0.9))])
    rv.write_labels(b / "p1.txt", [(STRUCT, _box(0.11, 0.1, 0.3, 0.31))])          # same hut, missed the bush
    rv.write_labels(a / "p2.txt", [])
    rv.write_labels(b / "p2.txt", [(VEG, _box(0.0, 0.0, 0.2, 0.2))])               # B saw a bush A did not
    for d, pts in ((a, _box(0, 0.5, 1, 1)), (b, _box(0, 0.6, 1, 1))):
        z = tmp_path / f"{d.name}_zones"
        z.mkdir()
        (z / "p1.json").write_text(json.dumps({"format": "normalized", "points": pts}))
    res = la.agreement(a, b)
    s, v = res["per_class"]["structure_permanent"], res["per_class"]["vegetation"]
    assert (s["matched"], s["box_agreement"]) == (1, 1.0)
    assert (v["boxes_a"], v["boxes_b"], v["matched"], v["box_agreement"]) == (1, 1, 0, 0.0)
    assert res["zone_mean_iou"] == pytest.approx(0.8)
    assert "| structure_permanent | 1 | 1 | 1 | 1.00 |" in la.table(res)


# --- reviewed label fixes ----------------------------------------------------------

import apply_label_fixes as alf  # noqa: E402


def test_fix_list_deletes_by_number_and_by_class(tmp_path):
    fixes = tmp_path / "fixes.txt"
    fixes.write_text("# comment\nabcdef123456: 0 C | wrong shapes\n", encoding="utf-8")
    [(image_id, (numbers, classes, reason))] = alf.parse(fixes).items()
    assert (image_id, numbers, reason) == ("abcdef123456", {0}, "wrong shapes")
    car = rv.CLASSES.index("vehicle_parked")
    labels = [(STRUCT, _box(0, 0, 1, 1)), (VEG, _box(0, 0, 1, 1)), (car, _box(0, 0, 1, 1))]
    kept, deleted = alf.apply(labels, numbers, classes)
    assert [c for c, _ in kept] == [VEG] and len(deleted) == 2


def test_fix_list_refuses_unknown_tokens(tmp_path):
    fixes = tmp_path / "fixes.txt"
    fixes.write_text("abcdef123456: X | ?\n", encoding="utf-8")
    with pytest.raises(ValueError):
        alf.parse(fixes)
