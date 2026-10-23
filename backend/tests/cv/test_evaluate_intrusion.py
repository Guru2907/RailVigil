"""Unit tests for event-level matching (issue #3 part B) — no weights needed."""

from app.cv.intrusion.evaluation import LabelRow, PredEvent, intervals_overlap, match_events


def test_intervals_overlap():
    assert intervals_overlap(0, 5, 4, 10)
    assert not intervals_overlap(0, 3, 3, 5)  # touching endpoint only
    assert intervals_overlap(0, 3.1, 3, 5)


def test_match_precision_recall_basic():
    labels = [
        LabelRow("a", 0, 5, "person", True),
        LabelRow("a", 10, 15, "person", True),
        LabelRow("b", 0, 20, "*", False),
    ]
    preds = [
        PredEvent("a", 1, 4, "person", dwell_time_sec=3),
        PredEvent("a", 20, 25, "person", dwell_time_sec=2),  # unmatched → FP
    ]
    m = match_events(labels, preds)
    assert m["tp"] == 1
    assert m["fn"] == 1
    assert m["fp"] == 1
    assert m["precision"] == 0.5
    assert m["recall"] == 0.5
    assert m["mean_confirmation_delay_sec"] == 1.0


def test_clip_stem_normalization():
    labels = [LabelRow("clip_one", 0, 5, "person", True)]
    preds = [PredEvent("clip_one.mp4", 0.5, 4, "person")]
    m = match_events(labels, preds)
    assert m["tp"] == 1
    assert m["fp"] == 0
    assert m["fn"] == 0


def test_two_objects_need_two_labels():
    labels = [
        LabelRow("pair", 0, 8, "person", True),
        LabelRow("pair", 0, 8, "person", True),
    ]
    preds = [
        PredEvent("pair", 1, 7, "person"),
        PredEvent("pair", 1.5, 7.5, "person"),
    ]
    m = match_events(labels, preds)
    assert m["tp"] == 2
    assert m["fp"] == 0
    assert m["fn"] == 0
