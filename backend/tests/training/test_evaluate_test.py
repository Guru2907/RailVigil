"""evaluate_test.py scoring: one AP definition for every model, paired bootstrap, groups."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "training"))

import evaluate_test as et  # noqa: E402

BOX = (10.0, 10.0, 50.0, 50.0)
ROWS = [{"image_id": f"in{i}", "country": "India"} for i in range(4)] + \
       [{"image_id": f"fr{i}", "country": "France"} for i in range(4)]
GTS = {r["image_id"]: [("vegetation", BOX)] for r in ROWS}


def test_perfect_model_scores_one_and_beats_an_empty_one():
    preds = {"perfect": {k: [("vegetation", 0.9, BOX)] for k in GTS}, "empty": {k: [] for k in GTS}}
    rep = et.score(["empty", "perfect"], ROWS, GTS, preds, resamples=50, min_objects=1, seed=0)
    allg = rep["groups"]["all"]
    assert allg["mean_ap50"]["perfect"]["value"] == 1.0
    assert allg["mean_ap50"]["empty"]["value"] == 0.0
    pair = allg["paired_differences"]["perfect - empty"]
    assert pair["difference"] == 1.0 and pair["share_above_zero"] == 1.0


def test_groups_split_india_from_other_countries():
    preds = {"india_only": {k: ([("vegetation", 0.9, BOX)] if k.startswith("in") else []) for k in GTS}}
    rep = et.score(["india_only"], ROWS, GTS, preds, resamples=20, min_objects=1, seed=0)
    assert rep["groups"]["India"]["photos"] == 4
    assert rep["groups"]["India"]["mean_ap50"]["india_only"]["value"] == 1.0
    assert rep["groups"]["other countries"]["mean_ap50"]["india_only"]["value"] == 0.0


def test_rare_classes_are_left_out_of_the_mean():
    gts = dict(GTS, in0=[("vegetation", BOX), ("material_dump", BOX)])
    preds = {"m": {k: [("vegetation", 0.9, BOX)] for k in gts}}
    rep = et.score(["m"], ROWS, gts, preds, resamples=10, min_objects=2, seed=0)
    assert rep["classes"] == ["vegetation"]
    assert rep["excluded_classes"] == {"material_dump": 1}
