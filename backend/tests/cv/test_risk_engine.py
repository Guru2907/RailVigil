import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

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


def test_severity_labels():
    assert severity_from_score(10) == "low"
    assert severity_from_score(25) == "medium"
    assert severity_from_score(50) == "high"
    assert severity_from_score(90) == "critical"


def test_event_type_classification():
    assert classify_event_type("person", persistent=False) == "human_intrusion"
    assert classify_event_type("person", persistent=True) == "persistent_human_presence"
    assert classify_event_type("car", persistent=False) == "vehicle_intrusion"
    assert classify_event_type("car", persistent=True) == "vehicle_intrusion"  # vehicles stay vehicle_intrusion regardless