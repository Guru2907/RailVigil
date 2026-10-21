"""
One-time build of backend/models/yolov8s-world-railvigil.pt: YOLOv8s-WorldV2
with RailVigil's text prompts (taxonomy.WORLD_PROMPTS) built in.

    python scripts/build_world_model.py

Why a build step: turning text prompts into the model's class embeddings
needs OpenAI CLIP. Ultralytics installs it from GitHub and downloads its
weights (a few hundred MB) the first time prompts are set. Doing that once
here means the app itself never needs CLIP or a network connection: the saved
model carries the embeddings. Re-run this script whenever WORLD_PROMPTS changes.

Needs backend/models/yolov8s-worldv2.pt (Ultralytics release asset).
CLIP weights are cached in backend/models/clip/ (git-ignored).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `app` importable

from app.core import config  # noqa: E402
from app.cv.common.model_registry import file_version, weights_path  # noqa: E402
from app.cv.encroachment.taxonomy import WORLD_PROMPTS  # noqa: E402

BASE_WEIGHTS = "yolov8s-worldv2.pt"


def main() -> int:
    base = Path(config.MODELS_DIR) / BASE_WEIGHTS
    if not base.is_file():
        print(f"error: {base} not found (Ultralytics release asset {BASE_WEIGHTS}).")
        return 2

    # Keep CLIP's download inside the project instead of Ultralytics' global
    # weights folder, for this process only.
    from ultralytics.nn import text_model

    text_model.WEIGHTS_DIR = Path(config.MODELS_DIR)
    from ultralytics import YOLOWorld

    prompts = list(WORLD_PROMPTS)
    model = YOLOWorld(str(base))
    model.set_classes(prompts)
    # set_classes caches the whole CLIP text encoder on the model (~300 MB).
    # Prediction only uses the computed text features (txt_feats), so drop it.
    model.model.clip_model = None

    out = weights_path("world-v8s-railvigil")
    model.save(str(out))
    print(f"saved {out} ({len(prompts)} prompts, version {file_version(out)})")
    for i, p in enumerate(prompts):
        print(f"  {i:2d} {p!r} -> {WORLD_PROMPTS[p]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
