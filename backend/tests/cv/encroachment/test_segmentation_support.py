"""The trained RailVigil model is a segmentation model: its mask outlines,
not its boxes, decide how much of an object lies on railway land."""

from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import box

from app.cv.encroachment.detector import Detection, EncroachmentDetector, merge_detections
from app.cv.encroachment.evidence import annotate
from app.cv.encroachment.geometry import object_polygon
from app.cv.encroachment.rules import RuleConfig, classify_finding
from app.cv.encroachment.taxonomy import CLASSES, STRUCTURE_TEMPORARY, map_label

CFG = RuleConfig(
    min_confidence=0.1, min_overlap=0.2,
    category_weight={c: 1.0 for c in CLASSES},
    severity_bands={"critical": 0.75, "high": 0.5, "medium": 0.25},
    vehicle_max_severity="medium",
)
ZONE = box(0, 0, 100, 100)

# An L-shaped object: a 100x100 block inside the zone plus a thin arm reaching
# out to x=200. Its box is half outside; its mask is ~91 % inside.
L_SHAPE = [(0, 0), (100, 0), (100, 90), (200, 90), (200, 100), (0, 100)]
L_BOX = (0, 0, 200, 100)


def test_object_polygon_prefers_the_mask_outline():
    assert object_polygon(L_BOX, L_SHAPE).area == pytest.approx(100 * 100 + 100 * 10)
    assert object_polygon(L_BOX, None).area == 200 * 100


def test_object_polygon_falls_back_to_the_box_for_unusable_outlines():
    assert object_polygon(L_BOX, [(0, 0), (10, 10)]).area == 200 * 100        # fewer than 3 points
    assert object_polygon(L_BOX, [(0, 0), (5, 0), (10, 0)]).area == 200 * 100  # zero area


def test_self_crossing_outline_is_repaired():
    bow_tie = [(0, 0), (10, 10), (10, 0), (0, 10)]
    assert object_polygon((0, 0, 10, 10), bow_tie).area > 0


def test_overlap_uses_the_mask_not_the_box():
    with_mask = classify_finding(Detection(STRUCTURE_TEMPORARY, "hut", 0.8, L_BOX, ["seg@1"], L_SHAPE), ZONE, CFG)
    box_only = classify_finding(Detection(STRUCTURE_TEMPORARY, "hut", 0.8, L_BOX, ["seg@1"]), ZONE, CFG)

    assert with_mask.overlap_ratio == pytest.approx(10000 / 11000, abs=1e-3)
    assert with_mask.severity == "critical"
    assert with_mask.outline == L_SHAPE
    assert box_only.overlap_ratio == pytest.approx(0.5)
    assert box_only.severity == "high"
    assert box_only.outline is None


def test_merge_keeps_the_outline_of_the_kept_detection():
    square = [(0, 0), (100, 0), (100, 100), (0, 100)]
    a = Detection(STRUCTURE_TEMPORARY, "hut", 0.9, (0, 0, 100, 100), ["seg@1"], square)
    b = Detection(STRUCTURE_TEMPORARY, "hut", 0.5, (2, 2, 100, 100), ["other@1"])
    [merged] = merge_detections([a, b], 0.5)
    assert merged.outline == a.outline
    assert merged.sources == ["seg@1", "other@1"]


class _Arr:
    def __init__(self, values):
        self._v = np.array(values)

    def cpu(self):
        return self

    def numpy(self):
        return self._v


def test_detector_reads_mask_outlines_from_a_segmentation_model():
    result = SimpleNamespace(
        names={0: STRUCTURE_TEMPORARY},
        boxes=SimpleNamespace(xyxy=_Arr([L_BOX]), cls=_Arr([0]), conf=_Arr([0.8])),
        masks=SimpleNamespace(xy=[np.array(L_SHAPE, dtype=np.float32)]),
    )
    model = SimpleNamespace(predict=lambda image, conf, verbose: [result])
    detector = EncroachmentDetector(["railvigil-seg"], min_confidence=0.25, merge_iou=0.5,
                                    loader={"railvigil-seg": SimpleNamespace(version="s1", model=model)}.__getitem__)

    [det] = detector.detect(np.zeros((400, 400, 3), dtype=np.uint8))

    assert det.cls == STRUCTURE_TEMPORARY
    assert det.outline == [tuple(map(float, p)) for p in L_SHAPE]
    assert det.sources == ["railvigil-seg@s1"]


def test_trained_model_labels_are_railvigil_classes():
    for cls in CLASSES:
        assert map_label("railvigil-seg", cls) == cls
    assert map_label("railvigil-seg", "train") is None


def test_annotation_draws_outlines():
    image = np.zeros((120, 220, 3), dtype=np.uint8)
    finding = classify_finding(Detection(STRUCTURE_TEMPORARY, "hut", 0.8, L_BOX, ["seg@1"], L_SHAPE), ZONE, CFG)
    out = annotate(image, [(0, 0), (100, 0), (100, 100), (0, 100)], [finding], [])
    assert out.shape == image.shape
    assert out[90, 150].any()  # the top edge of the L's arm is drawn, outside the zone
