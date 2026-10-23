"""The encroachment decision rule: when a detection becomes a finding, and how
severe it is. Zone = lower half of a 100x100 image."""

import pytest
from shapely.geometry import box

from app.cv.encroachment.detector import Detection
from app.cv.encroachment.geometry import zone_polygon
from app.cv.encroachment.rules import RuleConfig, classify_finding, severity_for
from app.cv.encroachment.taxonomy import (
    STRUCTURE_PERMANENT,
    STRUCTURE_TEMPORARY,
    VEGETATION,
    VEHICLE_PARKED,
)

ZONE = box(0, 50, 100, 100)
CFG = RuleConfig(
    min_confidence=0.25,
    min_overlap=0.2,
    category_weight={
        STRUCTURE_PERMANENT: 1.0, STRUCTURE_TEMPORARY: 0.9, VEGETATION: 0.6, VEHICLE_PARKED: 0.7,
    },
    severity_bands={"critical": 0.75, "high": 0.5, "medium": 0.25},
    vehicle_max_severity="medium",
)


def det(cls, bbox, conf=0.9):
    return Detection(cls=cls, label="test", confidence=conf, bbox=bbox, sources=["fake@0"])


def test_object_fully_inside_is_a_finding_with_full_overlap():
    f = classify_finding(det(STRUCTURE_PERMANENT, (10, 60, 40, 90)), ZONE, CFG)
    assert f is not None
    assert f.overlap_ratio == 1.0
    assert f.severity == "critical"
    assert f.zone_hit == "Z3"
    assert f.sources == ["fake@0"]


def test_object_outside_the_zone_is_not_a_finding():
    assert classify_finding(det(STRUCTURE_PERMANENT, (10, 0, 40, 40)), ZONE, CFG) is None


def test_half_inside_uses_category_weight_times_overlap():
    f = classify_finding(det(STRUCTURE_TEMPORARY, (10, 25, 40, 75)), ZONE, CFG)
    assert f.overlap_ratio == pytest.approx(0.5)
    assert f.severity_score == pytest.approx(0.45)
    assert f.severity == "medium"


def test_overlap_threshold_is_inclusive():
    at = classify_finding(det(STRUCTURE_PERMANENT, (0, 40, 10, 90)), ZONE, CFG)        # 40/50 = 0.8
    just_at = classify_finding(det(STRUCTURE_PERMANENT, (0, 10, 10, 60)), ZONE, CFG)   # 10/50 = 0.2
    below = classify_finding(det(STRUCTURE_PERMANENT, (0, 5, 10, 55)), ZONE, CFG)      # 5/50 = 0.1
    assert at is not None
    assert just_at is not None and just_at.overlap_ratio == pytest.approx(0.2)
    assert below is None


def test_low_confidence_is_ignored():
    assert classify_finding(det(STRUCTURE_PERMANENT, (10, 60, 40, 90), conf=0.2), ZONE, CFG) is None


def test_zero_area_box_is_ignored():
    assert classify_finding(det(STRUCTURE_PERMANENT, (10, 60, 10, 90)), ZONE, CFG) is None


def test_vehicle_severity_is_capped_and_noted():
    f = classify_finding(det(VEHICLE_PARKED, (10, 60, 40, 90)), ZONE, CFG)   # score 0.7 -> high
    assert f.severity == "medium"
    assert any("stationarity" in n for n in f.notes)


def test_low_confidence_keeps_severity_but_is_noted():
    cfg = RuleConfig(**{**CFG.__dict__, "low_confidence_note": 0.25})
    shaky = classify_finding(det(STRUCTURE_PERMANENT, (10, 60, 40, 90), conf=0.26 - 0.1), ZONE, cfg)
    sure = classify_finding(det(STRUCTURE_PERMANENT, (10, 60, 40, 90), conf=0.9), ZONE, cfg)
    assert shaky is None   # 0.16 is below the 0.25 floor of CFG
    cfg_low_floor = RuleConfig(**{**cfg.__dict__, "min_confidence": 0.1})
    shaky = classify_finding(det(STRUCTURE_PERMANENT, (10, 60, 40, 90), conf=0.16), ZONE, cfg_low_floor)
    assert shaky.severity == sure.severity == "critical"
    assert any("low detection confidence" in n for n in shaky.notes)
    assert sure.notes == []


def test_other_categories_have_no_notes():
    f = classify_finding(det(VEGETATION, (10, 60, 40, 90)), ZONE, CFG)
    assert f.notes == []


@pytest.mark.parametrize("score,expected", [
    (0.0, "low"), (0.249, "low"), (0.25, "medium"), (0.499, "medium"),
    (0.5, "high"), (0.749, "high"), (0.75, "critical"), (1.0, "critical"),
])
def test_severity_bands(score, expected):
    assert severity_for(score, CFG.severity_bands) == expected


@pytest.mark.parametrize("inside_px,expected", [
    (10, "low"),        # 10/50 = 0.2 inside -> score 0.2
    (15, "medium"),     # 0.3
    (30, "high"),       # 0.6
    (45, "critical"),   # 0.9
])
def test_every_band_is_reachable_for_a_structure(inside_px, expected):
    # A 10x50 box whose bottom `inside_px` pixels are inside the zone (y >= 50).
    f = classify_finding(det(STRUCTURE_PERMANENT, (0, inside_px, 10, 50 + inside_px)), ZONE, CFG)
    assert f.severity == expected


def test_self_intersecting_zone_still_works():
    # A "bow tie": two triangles touching at (50, 75). shapely repairs it into
    # its two lobes; a box inside the left lobe is fully on railway land.
    bowtie = zone_polygon([[0, 50], [100, 100], [100, 50], [0, 100]])
    assert bowtie.is_valid
    f = classify_finding(det(STRUCTURE_PERMANENT, (5, 65, 25, 85)), bowtie, CFG)
    assert f is not None and f.overlap_ratio == pytest.approx(1.0)
