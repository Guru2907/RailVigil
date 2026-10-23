"""
Converts raw spatial + temporal measurements into an interpretable
risk score and severity label. Deliberately RULE-BASED, not learned --
say so plainly in the paper. We're not claiming "AI learned the risk,"
we're saying "a documented weighted formula combines the factors that
matter." That's an honest, defensible scope.

    base  = w_penetration * max_penetration + w_dwell * dwell_norm     (0-1)
    score = 100 * base * class_factor                                  (0-100)

The class factor MULTIPLIES the spatiotemporal base rather than adding
to it, so the object type can only scale a real intrusion up or down --
it can't manufacture a score on its own. See config.py for the weights
and the reasoning behind the calibration.
"""

from app.core import config

# Which COCO classes count as "a person" vs "a vehicle" for event
# labelling. A bicycle is treated as a person because what's at risk is
# the rider, not the bike.
HUMAN_LIKE = {"person", "bicycle"}
VEHICLE_LIKE = {"car", "truck", "bus", "motorcycle"}
ANIMAL_LIKE = {"cow", "dog", "horse", "sheep", "elephant"}


def compute_risk_score(max_penetration: float, dwell_time_sec: float, object_class: str) -> float:
    """Returns a score from 0-100."""
    penetration = min(max(max_penetration, 0.0), 1.0)
    dwell_norm = min(max(dwell_time_sec, 0.0) / config.RISK_DWELL_NORM_SEC, 1.0)

    w = config.RISK_WEIGHTS
    base = w["penetration"] * penetration + w["dwell"] * dwell_norm
    base = min(base, 1.0)  # guards against someone setting weights that sum > 1

    # Unknown classes retain a conservative default rather than failing.
    class_factor = config.CLASS_RISK_FACTOR.get(object_class, config.CLASS_RISK_FACTOR["person"])

    return round(base * class_factor * 100, 1)


def severity_from_score(score: float) -> str:
    """Turns the 0-100 number into the label the UI expects
    (low / medium / high / critical)."""
    t = config.SEVERITY_THRESHOLDS
    if score >= t["critical"]:
        return "critical"
    if score >= t["high"]:
        return "high"
    if score >= t["medium"]:
        return "medium"
    return "low"


def is_persistent(dwell_time_sec: float) -> bool:
    """Dwell above this threshold = the object stuck around, not just
    passed through momentarily."""
    return dwell_time_sec >= config.PERSISTENT_DWELL_THRESHOLD_SEC


def classify_event_type(object_class: str, persistent: bool) -> str:
    if object_class in HUMAN_LIKE:
        return "persistent_human_presence" if persistent else "human_intrusion"
    if object_class in VEHICLE_LIKE:
        # Vehicles don't get a "persistent" variant: a car on the track is
        # an obstruction the moment it's there, however briefly.
        return "vehicle_intrusion"
    if object_class in ANIMAL_LIKE:
        return "persistent_animal_presence" if persistent else "animal_intrusion"
    return "other_intrusion"


def class_group(object_class: str) -> str:
    if object_class in HUMAN_LIKE:
        return "human"
    if object_class in VEHICLE_LIKE:
        return "vehicle"
    if object_class in ANIMAL_LIKE:
        return "animal"
    return "other"
