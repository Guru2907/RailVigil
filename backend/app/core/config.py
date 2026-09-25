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

# How each object class weighs into the risk score (0-1). A truck
# encroaching is riskier than a person, all else equal.
CLASS_RISK_WEIGHT = {
    "person": 0.6,
    "bicycle": 0.5,
    "motorcycle": 0.75,
    "car": 0.85,
    "truck": 0.95,
    "bus": 0.9,
}

# --- frame sampling / confirmation -----------------------------------
# Only run YOLO on every Nth frame — keeps CPU-only inference usable at
# something close to real time.
FRAME_SAMPLE_INTERVAL = int(os.getenv("FRAME_SAMPLE_INTERVAL", "3"))

# An object must be seen inside the zone for this many CONSECUTIVE
# sampled frames before it's confirmed as a real event (anti-flicker).
CONSECUTIVE_FRAMES_THRESHOLD = int(os.getenv("CONSECUTIVE_FRAMES_THRESHOLD", "5"))

# --- temporal reasoning -------------------------------------------------
# Dwell time above this = "persistent" encroachment, not just passing
# through. Short for demo purposes — would be much longer in real
# deployment (documented in the paper's limitations section).
PERSISTENT_DWELL_THRESHOLD_SEC = float(os.getenv("PERSISTENT_DWELL_THRESHOLD_SEC", "8.0"))

# --- risk scoring ---------------------------------------------------
# R = w_penetration * penetration + w_dwell * dwell_norm + w_class * class_weight
# Rule-based, not learned — documented honestly as a heuristic.
RISK_WEIGHTS = {
    "penetration": float(os.getenv("RISK_WEIGHT_PENETRATION", "0.45")),
    "dwell": float(os.getenv("RISK_WEIGHT_DWELL", "0.30")),
    "class": float(os.getenv("RISK_WEIGHT_CLASS", "0.25")),
}
RISK_DWELL_NORM_SEC = float(os.getenv("RISK_DWELL_NORM_SEC", "15.0"))

DEFAULT_CAMERA_LABEL = os.getenv("DEFAULT_CAMERA_LABEL", "Camera-1 (demo)")