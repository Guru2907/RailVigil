"""Regression on three fixed reference clips (issue #3 part A).

Requires GOLDEN_CLIPS_DIR (clips + .zone.json sidecars outside the repo)
and YOLO weights. Skipped in CI / when either is missing — never fails
the default suite for that reason.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.core import config
from app.cv.intrusion.video_processor import process_video

EXPECTED_DIR = Path(__file__).resolve().parent / "expected"

CLIP_KEYS = ("person_crossing", "two_people", "empty_or_train")


def _golden_dir() -> Path | None:
    raw = os.getenv("GOLDEN_CLIPS_DIR", "").strip()
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_dir() else None


def _weights_available() -> bool:
    return Path(config.MODEL_WEIGHTS).is_file()


def _requires_golden_env():
    if _golden_dir() is None:
        pytest.skip("GOLDEN_CLIPS_DIR not set or missing")
    if not _weights_available():
        pytest.skip(f"YOLO weights not found at {config.MODEL_WEIGHTS}")


@pytest.fixture(scope="module")
def golden_dir():
    _requires_golden_env()
    return _golden_dir()


@pytest.mark.requires_weights
@pytest.mark.parametrize("clip_key", CLIP_KEYS)
def test_golden_clip_matches_expected(clip_key: str, golden_dir: Path, tmp_path_factory):
    expected = json.loads((EXPECTED_DIR / f"{clip_key}.json").read_text(encoding="utf-8"))
    video = golden_dir / expected["clip"]
    if not video.is_file():
        # also allow stem without forcing .mp4 in filename field mismatches
        candidates = list(golden_dir.glob(f"{clip_key}.*"))
        video = next((p for p in candidates if p.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}), None)
        if video is None:
            pytest.skip(f"clip not found for {clip_key} under {golden_dir}")

    sidecar = video.with_suffix(".zone.json")
    if not sidecar.is_file():
        sidecar = Path(f"{video}.zone.json")
    if not sidecar.is_file():
        pytest.fail(f"missing zone sidecar for {video.name}")

    out_root = tmp_path_factory.mktemp(f"golden_{clip_key}")
    config.OUTPUTS_DIR = out_root
    out_video = out_root / "annotated.mp4"

    incidents = process_video(
        video_path=str(video),
        zone_points=None,
        video_id=clip_key,
        output_video_path=str(out_video),
    )

    count = len(incidents)
    lo = expected["incident_count"]["min"]
    hi = expected["incident_count"]["max"]
    assert lo <= count <= hi, f"{clip_key}: expected {lo}-{hi} incidents, got {count}: {incidents}"

    allowed_classes = set(expected.get("object_classes") or [])
    allowed_types = set(expected.get("event_types") or [])
    min_dwell = float(expected.get("min_dwell_sec") or 0.0)

    for inc in incidents:
        if allowed_classes:
            assert inc["object_class"] in allowed_classes, inc
        if allowed_types:
            assert inc["event_type"] in allowed_types, inc
        assert float(inc["dwell_time_sec"]) >= min_dwell, inc
