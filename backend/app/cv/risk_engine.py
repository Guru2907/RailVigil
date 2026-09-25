"""
Converts raw spatial + temporal measurements into an interpretable
risk score and severity label. Deliberately RULE-BASED, not learned --
say so plainly in the paper. We're not claiming "AI learned the risk,"
we're saying "a documented weighted formula combines the factors that
matter." That's an honest, defensible scope for a mini project.

R = w_penetration * penetration + w_dwell * dwell_norm + w_class * class_weight
"""

from app.core import config


def compute_risk_score(max_penetration: float, dwell_time_sec: float, object_class: str) -> float:
    """Returns a score from 0-100."""
    dwell_norm = min(dwell_time_sec / config.RISK_DWELL_NORM_SEC, 1.0)
    class_weight = config.CLASS_RISK_WEIGHT.get(object_class, 0.5)

    w = config.RISK_WEIGHTS
    score = (
        w["penetration"] * max_penetration
        + w["dwell"] * dwell_norm
        + w["class"] * class_weight
    )
    return round(min(1.0, score) * 100, 1)


def severity_from_score(score: float) -> str:
    """Turns the 0-100 number into the label your scaffold's UI expects
    (Incident #RV-0042, Severity: High, etc.)."""
    if score >= 70:
        return "critical"
    if score >= 40:
        return "high"
    if score >= 20:
        return "medium"
    return "low"


def is_persistent(dwell_time_sec: float) -> bool:
    """Dwell above this threshold = the object stuck around, not just
    passed through momentarily."""
    return dwell_time_sec >= config.PERSISTENT_DWELL_THRESHOLD_SEC


def classify_event_type(object_class: str, persistent: bool) -> str:
    vehicle_like = {"car", "truck", "bus", "motorcycle"}
    if object_class == "person":
        return "persistent_human_presence" if persistent else "human_intrusion"
    if object_class in vehicle_like:
        return "vehicle_intrusion"
    if object_class == "bicycle":
        return "human_intrusion"
    return "persistent_encroachment" if persistent else "obstruction"