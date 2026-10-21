"""Image pipeline end to end with a fake detector: zones, EXIF orientation,
findings and evidence files. No model weights needed."""

import json

import cv2
import numpy as np
import pytest
from PIL import Image

from app.core.errors import ValidationFailed
from app.cv.encroachment.detector import Detection
from app.cv.encroachment.pipeline import analyze_image, load_image
from app.cv.encroachment.taxonomy import STRUCTURE_TEMPORARY, VEGETATION

# 200x100 image; railway zone = bottom half.
ZONE_PX = [[0, 50], [200, 50], [200, 100], [0, 100]]


class FakeDetector:
    def __init__(self, detections):
        self.detections = detections

    def detect(self, image):
        self.seen_shape = image.shape
        return list(self.detections)

    def model_versions(self):
        return {"fake": "000000000000"}


HUT = Detection(STRUCTURE_TEMPORARY, "hut", 0.9, (20, 60, 80, 95), ["fake@0"])      # inside
TREE = Detection(VEGETATION, "Tree", 0.8, (120, 0, 180, 40), ["fake@0"])            # outside


@pytest.fixture
def photo(tmp_path):
    path = tmp_path / "corridor.jpg"
    cv2.imwrite(str(path), np.full((100, 200, 3), 120, dtype=np.uint8))
    return path


def test_findings_only_for_objects_on_railway_land(photo):
    result = analyze_image(photo, FakeDetector([HUT, TREE]), manual_zone=ZONE_PX)
    assert (result.width, result.height) == (200, 100)
    assert result.zone_source == "manual"
    assert len(result.detections) == 2
    assert [f.cls for f in result.findings] == [STRUCTURE_TEMPORARY]


def test_evidence_files_are_written(photo, tmp_path):
    out = tmp_path / "evidence"
    result = analyze_image(photo, FakeDetector([HUT, TREE]), manual_zone=ZONE_PX, out_dir=out)
    folder = out / "corridor"
    assert result.evidence_dir == str(folder)
    assert (folder / "annotated.jpg").is_file()
    report = json.loads((folder / "findings.json").read_text(encoding="utf-8"))
    assert report["models"] == {"fake": "000000000000"}
    assert report["zone"]["source"] == "manual"
    assert report["detections_total"] == 2
    assert len(report["findings"]) == 1
    finding = report["findings"][0]
    assert finding["cls"] == STRUCTURE_TEMPORARY and finding["severity"] in {"low", "medium", "high", "critical"}
    assert (folder / "crops" / finding["crop"]).is_file()
    assert "accuracy not measured" in report["note"]


def test_normalized_zone_is_accepted(photo):
    zone = [[0, 0.5], [1, 0.5], [1, 1], [0, 1]]
    result = analyze_image(photo, FakeDetector([HUT]), manual_zone=zone, manual_format="normalized")
    assert result.zone_points == ZONE_PX
    assert len(result.findings) == 1


def test_sidecar_zone_is_used_when_no_zone_is_given(photo):
    photo.with_suffix(".zone.json").write_text(
        json.dumps({"format": "normalized", "points": [[0, 0.5], [1, 0.5], [1, 1], [0, 1]]}), encoding="utf-8"
    )
    result = analyze_image(photo, FakeDetector([HUT]))
    assert result.zone_source == "sidecar"
    assert len(result.findings) == 1


def test_no_zone_is_rejected_never_whole_image(photo):
    detector = FakeDetector([HUT])
    with pytest.raises(ValidationFailed, match="No railway safety zone"):
        analyze_image(photo, detector)
    assert not hasattr(detector, "seen_shape")   # detection never ran


def test_exif_rotation_is_applied(tmp_path):
    path = tmp_path / "phone.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6   # "rotate 90° clockwise to display"
    Image.new("RGB", (200, 100), (10, 20, 30)).save(path, exif=exif)
    assert load_image(path).shape[:2] == (200, 100)   # displayed upright: 100 wide, 200 tall

    detector = FakeDetector([])
    result = analyze_image(path, detector, manual_zone=[[0, 100], [100, 100], [100, 200], [0, 200]])
    assert (result.width, result.height) == (100, 200)
    assert detector.seen_shape[:2] == (200, 100)


def test_non_image_file_is_rejected(tmp_path):
    bad = tmp_path / "notes.jpg"
    bad.write_text("not an image", encoding="utf-8")
    with pytest.raises(ValidationFailed, match="could not be opened as an image"):
        analyze_image(bad, FakeDetector([]), manual_zone=ZONE_PX)


def test_findings_are_sorted_most_severe_first(photo):
    partly = Detection(STRUCTURE_TEMPORARY, "shed", 0.9, (100, 30, 160, 70), ["fake@0"])   # half inside
    result = analyze_image(photo, FakeDetector([partly, HUT]), manual_zone=ZONE_PX)
    scores = [f.severity_score for f in result.findings]
    assert scores == sorted(scores, reverse=True) and len(scores) == 2
