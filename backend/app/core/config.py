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
# Stored media and evidence for the encroachment module (services/storage_service.py).
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage"))

# --- database -----------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'railvigil.db'}")

# --- YOLO / detection -----------------------------------------------
MODEL_WEIGHTS = os.getenv("MODEL_WEIGHTS", str(MODELS_DIR / "yolov8n.pt"))
# Provisional confidence threshold; validate against labeled railway footage.
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.35"))

# Classes included in railway intrusion detection. Anything YOLO detects
# outside this set is ignored (e.g. "chair", "clock" from COCO).
INTRUSION_CLASSES = {
    "person", "bicycle", "car", "motorcycle", "bus", "truck",
    "cow", "dog", "horse", "sheep", "elephant",
}

# Provisional IoU for continuing an event after a ByteTrack ID switch.
ID_MERGE_MIN_IOU = float(os.getenv("ID_MERGE_MIN_IOU", "0.3"))

# --- frame sampling / confirmation -----------------------------------
# Provisional sampling threshold: only run YOLO on every Nth frame; this keeps CPU-only inference usable at
# something close to real time. The frames in between are still drawn
# (zone + last known boxes) so the output video doesn't flicker; they
# just don't get fresh detections. Lower = smoother tracking, slower.
FRAME_SAMPLE_INTERVAL = int(os.getenv("FRAME_SAMPLE_INTERVAL", "3"))

# Provisional threshold: an object must stay inside the zone for at least this many SECONDS
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
# Provisional threshold; tune against labeled footage before deployment.
MISS_GRACE_SEC = float(os.getenv("MISS_GRACE_SEC", "1.0"))

# --- temporal reasoning -------------------------------------------------
# Provisional threshold; dwell above this is labeled persistent presence.
# Short for demo purposes; this value would be much longer in real
# deployment (documented in the paper's limitations section).
PERSISTENT_DWELL_THRESHOLD_SEC = float(os.getenv("PERSISTENT_DWELL_THRESHOLD_SEC", "8.0"))

# Optional camera-label to normalized-zone map, supplied as JSON in the environment.
# Example: {"Platform 2":{"format":"normalized","points":[[0.2,0.5],[0.8,0.5],[0.8,1],[0.2,1]]}}

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
# Provisional risk weights and thresholds; calibrate on labeled footage.
RISK_WEIGHTS = {
    "penetration": float(os.getenv("RISK_WEIGHT_PENETRATION", "0.6")),
    "dwell": float(os.getenv("RISK_WEIGHT_DWELL", "0.4")),
}
# Provisional dwell time at which the dwell term saturates (= full weight).
RISK_DWELL_NORM_SEC = float(os.getenv("RISK_DWELL_NORM_SEC", "15.0"))

# Provisional per-class multiplier on the spatiotemporal base (0-1). A truck on the
# track is a bigger hazard than a person, all else equal. Keep the top
# class at 1.0 so the 0-100 scale is actually reachable.
CLASS_RISK_FACTOR = {
    "person": 0.8,
    "bicycle": 0.75,
    "motorcycle": 0.85,
    "car": 0.9,
    "bus": 0.95,
    "truck": 1.0,
    "elephant": 1.0,  # provisional: large wildlife on track
    "cow": 0.9,       # provisional: cattle strikes common
    "horse": 0.85,
    "sheep": 0.75,
    "dog": 0.7,  # >= 0.7 so max score can still reach "critical"
}

# Provisional severity bands on the 0-100 score. Chosen so that, with the factors
# above, every band is reachable for every class (see tests/cv/test_risk_engine.py).
SEVERITY_THRESHOLDS = {"critical": 70, "high": 40, "medium": 20}

DEFAULT_CAMERA_LABEL = os.getenv("DEFAULT_CAMERA_LABEL", "Camera-1 (demo)")

# --- logging -------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- upload validation ---------------------------------------------------
# Checked while the file is being streamed to disk, so an oversized upload
# is rejected without ever holding the whole file in memory.
MAX_UPLOAD_MB = float(os.getenv("MAX_UPLOAD_MB", "500"))
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
# Reject very long videos up front: CPU inference runs at roughly real
# time or slower, so a 3-hour upload would block the queue for hours.
MAX_VIDEO_SEC = float(os.getenv("MAX_VIDEO_SEC", "600"))
MAX_ZONE_POINTS = int(os.getenv("MAX_ZONE_POINTS", "50"))
MAX_CAMERA_LABEL_LEN = 100

# --- background processing ----------------------------------------------
# Number of videos processed at the same time. Each worker loads its OWN
# copy of the YOLO model (tracker state lives on the model, so sharing one
# between concurrent workers would mix up track ids). Keep at 1 unless the
# machine has the RAM/GPU for more.
WORKER_COUNT = int(os.getenv("WORKER_COUNT", "1"))

# Uploads are refused (HTTP 429) while this many videos are already waiting
# or being processed, so a burst of uploads can't fill the disk with videos
# that will take hours to get through.
MAX_QUEUED_JOBS = int(os.getenv("MAX_QUEUED_JOBS", "20"))

# How many times a video may START processing before we give up on it.
# Protects against a video that crashes the whole server (e.g. out of
# memory) being retried forever after every restart.
MAX_JOB_ATTEMPTS = int(os.getenv("MAX_JOB_ATTEMPTS", "3"))

# Progress is written to the database at most this often, so a fast
# video doesn't turn into hundreds of tiny DB writes.
PROGRESS_UPDATE_SEC = float(os.getenv("PROGRESS_UPDATE_SEC", "2.0"))

# --- encroachment (Phase 1 baseline) -----------------------------------------
# Every value below is PROVISIONAL: chosen by hand for the pretrained baseline
# models and to be replaced by values measured on the labelled test set
# (docs/EVALUATION.md). See docs/ENCROACHMENT_SPEC.md for the rule itself.

# Which registered models the image pipeline runs (cv/common/model_registry.py).
ENC_MODELS = [m.strip() for m in os.getenv("ENC_MODELS", "oiv7-v8s,world-v8s-railvigil").split(",") if m.strip()]
# Per-model confidence cut-off when detecting. Open-vocabulary YOLO-World gives
# systematically lower scores than a closed-set model (on a test frame a real
# tarpaulin shelter scored 0.20), so one shared threshold does not fit both.
ENC_MODEL_MIN_CONFIDENCE = {
    "oiv7-v8s": float(os.getenv("ENC_MIN_CONFIDENCE_OIV7", "0.25")),
    "world-v8s-railvigil": float(os.getenv("ENC_MIN_CONFIDENCE_WORLD", "0.10")),
    # Provisional until chosen from the evaluation run (docs/EVALUATION.md).
    "railvigil-seg": float(os.getenv("ENC_MIN_CONFIDENCE_SEG", "0.25")),
}
# Rule-level floor: no finding below this confidence, whichever model produced it.
ENC_MIN_CONFIDENCE = float(os.getenv("ENC_MIN_CONFIDENCE", "0.10"))
# Findings below this confidence keep their severity (how serious the object
# would be) but carry a "low detection confidence" note for the reviewer.
ENC_LOW_CONFIDENCE_NOTE = float(os.getenv("ENC_LOW_CONFIDENCE_NOTE", "0.25"))
# Minimum share of an object's area that must lie inside the railway zone.
ENC_MIN_OVERLAP = float(os.getenv("ENC_MIN_OVERLAP", "0.2"))
# A box covering at least this share of the whole image is not an object (on a
# close-up of track, Open Images returned "Building" for the entire photo).
ENC_MAX_BOX_SHARE = float(os.getenv("ENC_MAX_BOX_SHARE", "0.8"))
# Two models reporting the same class with at least this box IoU count as one object.
ENC_MERGE_IOU = float(os.getenv("ENC_MERGE_IOU", "0.5"))
# How serious each category is, 0-1. severity_score = weight * overlap.
ENC_CATEGORY_WEIGHT = {
    "structure_permanent": 1.0,
    "structure_temporary": 0.9,
    "material_dump": 0.8,
    "debris_waste": 0.7,
    "vehicle_parked": 0.7,
    "vegetation": 0.6,
}
# Lower bounds of the severity bands on severity_score; below "medium" is "low".
ENC_SEVERITY_BANDS = {"critical": 0.75, "high": 0.5, "medium": 0.25}
# One photo cannot show that a vehicle is parked, so its severity is capped.
ENC_VEHICLE_MAX_SEVERITY = "medium"

# --- encroachment sites, reports and photo uploads (Phase 2) -----------------
# Findings of the same class within this many metres of an open site are the
# same site. PROVISIONAL: GPS on phones is often off by 5-20 m.
ENC_SITE_RADIUS_M = float(os.getenv("ENC_SITE_RADIUS_M", "25"))
MAX_IMAGE_MB = float(os.getenv("MAX_IMAGE_MB", "25"))
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
# Photos accepted in one POST /api/media request.
MAX_IMAGES_PER_UPLOAD = int(os.getenv("MAX_IMAGES_PER_UPLOAD", "20"))
# Photos analysed at the same time. Each worker holds the encroachment models
# (~50 MB of weights plus working memory); keep at 1 on a laptop.
IMAGE_WORKER_COUNT = int(os.getenv("IMAGE_WORKER_COUNT", "1"))
