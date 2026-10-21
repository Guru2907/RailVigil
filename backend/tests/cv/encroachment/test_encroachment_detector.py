"""Label mapping, merging across models, and the detector wrapper (with fake
models, so no weights are needed)."""

from types import SimpleNamespace

import numpy as np
import pytest

from app.core import config
from app.cv.common import model_registry
from app.cv.encroachment.detector import Detection, EncroachmentDetector, merge_detections
from app.cv.encroachment.taxonomy import (
    CLASSES,
    OIV7_LABELS,
    STRUCTURE_PERMANENT,
    STRUCTURE_TEMPORARY,
    VEGETATION,
    WORLD_PROMPTS,
    map_label,
)


def test_every_mapping_targets_a_known_class():
    assert set(OIV7_LABELS.values()) <= set(CLASSES)
    assert set(WORLD_PROMPTS.values()) <= set(CLASSES)


def test_trains_and_unknown_labels_are_never_encroachment():
    assert map_label("oiv7-v8s", "Train") is None
    assert map_label("oiv7-v8s", "Wall clock") is None
    assert map_label("no-such-model", "House") is None


def test_known_labels_map():
    assert map_label("oiv7-v8s", "House") == STRUCTURE_PERMANENT
    assert map_label("oiv7-v8s", "Tree") == VEGETATION
    assert map_label("world-v8s-railvigil", "tin shed") == STRUCTURE_TEMPORARY


def _d(cls, bbox, conf, source):
    return Detection(cls=cls, label="x", confidence=conf, bbox=bbox, sources=[source])


def test_same_class_overlapping_boxes_merge_keeping_the_more_confident():
    merged = merge_detections([
        _d(STRUCTURE_TEMPORARY, (0, 0, 100, 100), 0.6, "a@1"),
        _d(STRUCTURE_TEMPORARY, (5, 5, 100, 100), 0.8, "b@1"),
    ], iou_threshold=0.5)
    assert len(merged) == 1
    assert merged[0].confidence == 0.8
    assert merged[0].sources == ["b@1", "a@1"]


def test_different_classes_or_low_overlap_stay_separate():
    assert len(merge_detections([
        _d(STRUCTURE_TEMPORARY, (0, 0, 100, 100), 0.6, "a@1"),
        _d(VEGETATION, (0, 0, 100, 100), 0.8, "b@1"),
    ], 0.5)) == 2
    assert len(merge_detections([
        _d(STRUCTURE_TEMPORARY, (0, 0, 100, 100), 0.6, "a@1"),
        _d(STRUCTURE_TEMPORARY, (90, 90, 200, 200), 0.8, "b@1"),
    ], 0.5)) == 2


class _Arr:
    def __init__(self, values):
        self._v = np.array(values)

    def cpu(self):
        return self

    def numpy(self):
        return self._v


def _fake_model(names, boxes):
    """Mimics ultralytics.YOLO.predict(...)[0] for the attributes the detector reads."""
    result = SimpleNamespace(
        names=names,
        boxes=SimpleNamespace(
            xyxy=_Arr([b[0] for b in boxes]),
            cls=_Arr([b[1] for b in boxes]),
            conf=_Arr([b[2] for b in boxes]),
        ),
    )
    return SimpleNamespace(predict=lambda image, conf, verbose: [result])


def test_detector_maps_filters_and_merges_across_models():
    oiv7 = _fake_model({0: "House", 1: "Train", 2: "Tree"}, [
        ((10, 10, 110, 110), 0, 0.7),
        ((0, 0, 50, 50), 1, 0.9),          # Train: dropped
        ((200, 200, 260, 300), 2, 0.5),
    ])
    world = _fake_model({0: "concrete building"}, [((12, 12, 110, 110), 0, 0.8)])
    loaded = {
        "oiv7-v8s": SimpleNamespace(version="aaa", model=oiv7),
        "world-v8s-railvigil": SimpleNamespace(version="bbb", model=world),
    }
    detector = EncroachmentDetector(["oiv7-v8s", "world-v8s-railvigil"], min_confidence=0.25,
                                    merge_iou=0.5, loader=loaded.__getitem__)

    found = detector.detect(np.zeros((400, 400, 3), dtype=np.uint8))

    assert sorted(d.cls for d in found) == [STRUCTURE_PERMANENT, VEGETATION]
    building = next(d for d in found if d.cls == STRUCTURE_PERMANENT)
    assert building.confidence == pytest.approx(0.8)
    assert building.sources == ["world-v8s-railvigil@bbb", "oiv7-v8s@aaa"]
    assert detector.model_versions() == {"oiv7-v8s": "aaa", "world-v8s-railvigil": "bbb"}


def test_each_model_uses_its_own_confidence_cutoff(monkeypatch):
    used = {}

    def model(name):
        def predict(image, conf, verbose):
            used[name] = conf
            return [SimpleNamespace(names={}, boxes=None)]
        return SimpleNamespace(version="v", model=SimpleNamespace(predict=predict))

    monkeypatch.setattr(config, "ENC_MODEL_MIN_CONFIDENCE", {"oiv7-v8s": 0.25, "world-v8s-railvigil": 0.1})
    names = ["oiv7-v8s", "world-v8s-railvigil"]
    EncroachmentDetector(names, loader=model).detect(np.zeros((10, 10, 3), dtype=np.uint8))
    assert used == {"oiv7-v8s": 0.25, "world-v8s-railvigil": 0.1}

    used.clear()
    EncroachmentDetector(names, min_confidence=0.5, loader=model).detect(np.zeros((10, 10, 3), dtype=np.uint8))
    assert used == {"oiv7-v8s": 0.5, "world-v8s-railvigil": 0.5}


def test_missing_weights_raise_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(model_registry, "_cache", {})
    with pytest.raises(model_registry.ModelNotAvailable, match="build_world_model"):
        model_registry.get_model("world-v8s-railvigil")


def test_unknown_model_name_is_rejected():
    with pytest.raises(KeyError):
        model_registry.weights_path("nope")


def test_file_version_is_a_stable_short_hash(tmp_path):
    f = tmp_path / "w.pt"
    f.write_bytes(b"weights")
    assert model_registry.file_version(f) == model_registry.file_version(f)
    assert len(model_registry.file_version(f)) == 12
