"""Named YOLO models, loaded once and shared.

Each model has a stable name used in config and stored on every result, plus
a version: the first 12 hex characters of the weights file's SHA-256, so a
result can always be traced to the exact file that produced it.

Weights live in MODELS_DIR (git-ignored). A missing file raises
ModelNotAvailable with a hint instead of letting Ultralytics download
something at runtime.
"""

import hashlib
import threading
from dataclasses import dataclass
from pathlib import Path

from app.core import config


class ModelNotAvailable(RuntimeError):
    """The weights file for a registered model is not on disk."""


@dataclass(frozen=True)
class ModelSpec:
    name: str
    filename: str
    description: str
    how_to_get: str


MODELS: dict[str, ModelSpec] = {
    spec.name: spec
    for spec in (
        ModelSpec(
            "coco-v8n", "yolov8n.pt",
            "YOLOv8n, COCO (80 classes); intrusion pipeline",
            "Ultralytics release asset yolov8n.pt",
        ),
        ModelSpec(
            "oiv7-v8s", "yolov8s-oiv7.pt",
            "YOLOv8s, Open Images V7 (601 classes); encroachment baseline",
            "Ultralytics release asset yolov8s-oiv7.pt",
        ),
        ModelSpec(
            "world-v8s-railvigil", "yolov8s-world-railvigil.pt",
            "YOLOv8s-WorldV2 with RailVigil's text prompts built in; encroachment baseline",
            "run backend/scripts/build_world_model.py",
        ),
        ModelSpec(
            "railvigil-seg", "railvigil-seg.pt",
            "YOLOv8s-seg trained on the RailVigil corridor dataset (6 classes, masks); encroachment",
            "train with training/train.py, then training/promote.py copies the chosen run here",
        ),
    )
}


@dataclass(frozen=True)
class LoadedModel:
    name: str
    version: str
    model: object  # ultralytics.YOLO


_cache: dict[str, LoadedModel] = {}
_lock = threading.Lock()


def weights_path(name: str) -> Path:
    if name not in MODELS:
        raise KeyError(f"Unknown model '{name}'. Registered: {', '.join(sorted(MODELS))}")
    return Path(config.MODELS_DIR) / MODELS[name].filename


def file_version(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:12]


def get_model(name: str) -> LoadedModel:
    """Load a registered model on first use, then return the cached one.
    Ultralytics models keep per-call state only for tracking, which the
    encroachment pipeline does not use, so sharing is safe for predict()."""
    with _lock:
        if name in _cache:
            return _cache[name]
        path = weights_path(name)
        if not path.is_file():
            raise ModelNotAvailable(
                f"Weights for '{name}' not found at {path}. Get them via: {MODELS[name].how_to_get}."
            )
        from ultralytics import YOLO  # heavy import, only when a model is actually needed

        loaded = LoadedModel(name=name, version=file_version(path), model=YOLO(str(path)))
        _cache[name] = loaded
        return loaded
