"""
Central configuration. Every tunable value in the CV pipeline and API
lives here, read from environment variables with sane defaults — so
there are no magic numbers scattered across detector.py, zone_engine.py,
temporal_engine.py, risk_engine.py, etc. Change a threshold once, here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/

# --- storage locations -----------------------------------------------
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
MODELS_DIR = Path(os.getenv("MODELS_DIR", BASE_DIR / "models"))
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", BASE_DIR / "outputs"))

# --- database -----------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'railvigil.db'}")

# --- YOLO / detection -----------------------------------------------
MODEL_WEIGHTS = os.getenv("MODEL_WEIGHTS", str(MODELS_DIR / "yolov8n.pt"))
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.35"))

# Classes we care about for railway encroachment. Anything YOLO detects
# outside this set is ignored (e.g. "chair", "clock" from COCO).
RELEVANT_CLASSES = {"person", "car", "truck", "bus", "motorcycle", "bicycle"}

# --- frame sampling / confirmation -----------------------------------
# Only run YOLO on every Nth frame — keeps CPU-only inference usable at
# something close to real time. The frames in between are still drawn
# (zone + last known boxes) so the output video doesn't flicker; they
# just don't get fresh detections. Lower = smoother tracking, slower.
FRAME_SAMPLE_INTERVAL = int(os.getenv("FRAME_SAMPLE_INTERVAL", "3"))

# An object must stay inside the zone for at least this many SECONDS of
# video time before it's confirmed as a real event (anti-flicker: a
# one-off false detection never becomes an incident). Measured in
# seconds — NOT sampled frames — so behaviour is the same whatever the
# video's fps or FRAME_SAMPLE_INTERVAL happen to be.
CONFIRM_DWELL_SEC = float(os.getenv("CONFIRM_DWELL_SEC", "0.6"))

# When a tracked object stops being seen inside the zone we do NOT close
# its event immediately. A single missed detection (brief occlusion, a
# frame where YOLO simply didn't fire) must not split one real intrusion
# into several incidents. The event is closed only once the object has
# been missing for longer than this. Dwell time still only counts up to
# the last real sighting, so the grace window itself is never added.
MISS_GRACE_SEC = float(os.getenv("MISS_GRACE_SEC", "1.0"))

# --- temporal reasoning -------------------------------------------------
# Dwell time above this = "persistent" encroachment, not just passing
# through. Short for demo purposes — would be much longer in real
# deployment (documented in the paper's limitations section).
PERSISTENT_DWELL_THRESHOLD_SEC = float(os.getenv("PERSISTENT_DWELL_THRESHOLD_SEC", "8.0"))

# --- risk scoring ---------------------------------------------------
# Rule-based, not learned — documented honestly as a heuristic.
#
#   base  = w_penetration * max_penetration + w_dwell * min(dwell / RISK_DWELL_NORM_SEC, 1)
#   score = 100 * base * CLASS_RISK_FACTOR[object_class]
#
# `base` (0-1) is the spatiotemporal part: how deep into the zone and
# for how long. The class factor then SCALES it. That ordering matters:
#   - a truck that barely clips the zone edge for a moment is still
#     "low" (the object type alone can't produce a high score), and
#   - a person standing fully inside the zone for a long time can
#     still reach "critical" (person factor 0.8 -> max score 80).
# The earlier additive formula (+ w_class * class_weight) handed out
# 15-24 points just for existing, which made "low" unreachable for
# vehicles and pushed almost every incident to "medium" or above.
RISK_WEIGHTS = {
    "penetration": float(os.getenv("RISK_WEIGHT_PENETRATION", "0.6")),
    "dwell": float(os.getenv("RISK_WEIGHT_DWELL", "0.4")),
}
# Dwell time at which the dwell term saturates (= full weight).
RISK_DWELL_NORM_SEC = float(os.getenv("RISK_DWELL_NORM_SEC", "15.0"))

# Per-class multiplier on the spatiotemporal base (0-1). A truck on the
# track is a bigger hazard than a person, all else equal. Keep the top
# class at 1.0 so the 0-100 scale is actually reachable.
CLASS_RISK_FACTOR = {
    "person": 0.8,
    "bicycle": 0.75,
    "motorcycle": 0.85,
    "car": 0.9,
    "bus": 0.95,
    "truck": 1.0,
}

# Severity bands on the 0-100 score. Chosen so that, with the factors
# above, every band is reachable for every class (see tests/cv/test_risk_engine.py).
SEVERITY_THRESHOLDS = {"critical": 70, "high": 40, "medium": 20}

DEFAULT_CAMERA_LABEL = os.getenv("DEFAULT_CAMERA_LABEL", "Camera-1 (demo)")