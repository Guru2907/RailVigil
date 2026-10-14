import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core import config
from app.cv.risk_engine import (
    compute_risk_score, severity_from_score, is_persistent, classify_event_type
)


def test_risk_increases_with_penetration_and_dwell():
    low = compute_risk_score(max_penetration=0.1, dwell_time_sec=1.0, object_class="person")
    high = compute_risk_score(max_penetration=0.9, dwell_time_sec=20.0, object_class="person")
    assert high > low
    assert 0 <= low <= 100
    assert 0 <= high <= 100


def test_vehicle_riskier_than_person_all_else_equal():
    person = compute_risk_score(max_penetration=0.5, dwell_time_sec=5.0, object_class="person")
    truck = compute_risk_score(max_penetration=0.5, dwell_time_sec=5.0, object_class="truck")
    assert truck > person


def test_score_never_exceeds_100():
    assert compute_risk_score(max_penetration=1.0, dwell_time_sec=1e6, object_class="truck") == 100.0
    assert compute_risk_score(max_penetration=5.0, dwell_time_sec=-3.0, object_class="truck") <= 100.0


def test_low_is_reachable_for_every_class():
    """Regression for the old additive formula, where a vehicle got
    ~20 points just for being a vehicle and could never score 'low'."""
    for cls in config.CLASS_RISK_FACTOR:
        score = compute_risk_score(max_penetration=0.05, dwell_time_sec=0.5, object_class=cls)
        assert severity_from_score(score) == "low", (cls, score)


def test_critical_is_reachable_for_every_class():
    """A person fully inside the zone for a long time must still be
    'critical' even though the person factor is below 1."""
    for cls in config.CLASS_RISK_FACTOR:
        score = compute_risk_score(max_penetration=1.0, dwell_time_sec=60.0, object_class=cls)
        assert severity_from_score(score) == "critical", (cls, score)


def test_class_factor_cannot_create_risk_on_its_own():
    """Zero penetration and zero dwell -> zero score, whatever the class."""
    for cls in config.CLASS_RISK_FACTOR:
        assert compute_risk_score(0.0, 0.0, cls) == 0.0


def test_unknown_class_does_not_crash():
    assert compute_risk_score(0.5, 5.0, "cow") > 0


def test_severity_labels():
    t = config.SEVERITY_THRESHOLDS
    assert severity_from_score(t["medium"] - 1) == "low"
    assert severity_from_score(t["medium"]) == "medium"
    assert severity_from_score(t["high"]) == "high"
    assert severity_from_score(t["critical"]) == "critical"
    assert severity_from_score(100) == "critical"


def test_is_persistent():
    assert is_persistent(config.PERSISTENT_DWELL_THRESHOLD_SEC) is True
    assert is_persistent(config.PERSISTENT_DWELL_THRESHOLD_SEC - 0.1) is False


def test_event_type_classification():
    assert classify_event_type("person", persistent=False) == "human_intrusion"
    assert classify_event_type("person", persistent=True) == "persistent_human_presence"
    assert classify_event_type("bicycle", persistent=True) == "persistent_human_presence"
    assert classify_event_type("car", persistent=False) == "vehicle_intrusion"
    assert classify_event_type("car", persistent=True) == "vehicle_intrusion"  # vehicles stay vehicle_intrusion regardless
    assert classify_event_type("cow", persistent=False) == "obstruction"
    assert classify_event_type("cow", persistent=True) == "persistent_encroachment"
