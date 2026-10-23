"""Smoke test with the real baseline weights. Skipped in CI and wherever the
weights are not in backend/models (see docs/ENCROACHMENT_SPEC.md)."""

import cv2
import numpy as np
import pytest

from app.core import config
from app.cv.common.model_registry import weights_path
from app.cv.encroachment.detector import EncroachmentDetector
from app.cv.encroachment.pipeline import analyze_image

pytestmark = pytest.mark.requires_weights


@pytest.fixture
def detector():
    missing = [n for n in config.ENC_MODELS if not weights_path(n).is_file()]
    if missing:
        pytest.skip(f"weights not available: {', '.join(missing)}")
    return EncroachmentDetector()


def test_real_models_run_end_to_end(tmp_path, detector):
    image = tmp_path / "blank.jpg"
    cv2.imwrite(str(image), np.full((360, 640, 3), 127, dtype=np.uint8))
    result = analyze_image(
        image, detector, manual_zone=[[0, 0.5], [1, 0.5], [1, 1], [0, 1]],
        manual_format="normalized", out_dir=tmp_path / "evidence",
    )
    assert isinstance(result.findings, list)
    assert set(detector.model_versions()) == set(config.ENC_MODELS)
    assert (tmp_path / "evidence" / "blank" / "findings.json").is_file()
