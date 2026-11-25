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


def test_skipped_clips_do_not_count_as_video_time():
    labels = [
        LabelRow("ran", 0, 3600, "*", False),
        LabelRow("no_zone", 0, 3600, "*", False),
    ]
    preds = [PredEvent("ran", 10, 12, "person")]
    m = match_events(labels, preds, processed_clips={"ran.mp4"})
    assert m["video_hours_est"] == 1.0
    assert m["false_alerts_per_hour"] == 1.0
    assert m["skipped_clips"] == ["no_zone"]
    assert m["n_clips"] == 1


def test_skipped_clip_positives_are_not_misses():
    labels = [LabelRow("no_zone", 2, 5, "person", True)]
    m = match_events(labels, [], processed_clips=set())
    assert m["fn"] == 0
    assert m["n_positive_labels"] == 0


def test_duplicate_alerts_are_split_from_other_false_alerts():
    labels = [LabelRow("a", 0, 10, "person", True)]
    preds = [
        PredEvent("a", 1, 4, "person"),    # matched
        PredEvent("a", 6, 9, "person"),    # same person, new track id: duplicate
        PredEvent("a", 20, 25, "person"),  # nothing labelled there
        PredEvent("a", 2, 5, "car"),       # wrong class: not a duplicate
    ]
    m = match_events(labels, preds)
    assert (m["tp"], m["fp"], m["fp_duplicate"], m["fp_other"]) == (1, 3, 1, 2)
    assert m["per_clip"]["a"] == {"positives": 1, "tp": 1, "fn": 0, "fp": 3, "fp_duplicate": 1}


def test_extension_and_stem_are_one_clip_for_hours():
    labels = [LabelRow("c", 0, 1800, "*", False)]
    preds = [PredEvent("c.mp4", 100, 200, "person")]
    assert match_events(labels, preds)["video_hours_est"] == 0.5
