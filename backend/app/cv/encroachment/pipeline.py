"""One image in, potential encroachment findings out.

    load image (EXIF orientation applied) -> resolve the railway zone
    -> detect objects -> classify_finding per detection -> optional evidence

The zone comes from the shared ZoneResolver (drawn points, a <image>.zone.json
sidecar, or a camera's saved zone). Without a zone the image is rejected; the
whole image is never treated as railway land.
"""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import ValidationFailed
from app.cv.common.zones import ZoneResolver
from app.cv.encroachment.detector import Detection
from app.cv.encroachment.evidence import write_evidence
from app.cv.encroachment.geometry import zone_polygon
from app.cv.encroachment.rules import Finding, RuleConfig, classify_finding

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@dataclass
class ImageResult:
    image_path: str
    width: int
    height: int
    zone_source: str
    zone_points: list[list[int]]
    detections: list[Detection]
    findings: list[Finding]
    evidence_dir: str | None = None


def load_image(path) -> np.ndarray:
    """BGR array with the photo's EXIF orientation applied, so coordinates
    match the picture as the user sees it (phone photos are often stored
    sideways with a rotation flag)."""
    try:
        with Image.open(path) as img:
            upright = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationFailed(f"'{Path(path).name}' could not be opened as an image.") from exc
    return cv2.cvtColor(np.asarray(upright), cv2.COLOR_RGB2BGR)


def analyze_image(image_path, detector, *, manual_zone=None, manual_format: str = "pixel",
                  camera_label: str | None = None, rule_config: RuleConfig | None = None,
                  out_dir=None, resolver: ZoneResolver | None = None) -> ImageResult:
    image = load_image(image_path)
    height, width = image.shape[:2]

    zone = (resolver or ZoneResolver()).resolve(
        width, height, manual_zone=manual_zone, manual_format=manual_format,
        sidecar_path=image_path, camera_label=camera_label,
    )
    zone_points = zone.to_pixels(width, height)
    zone_shape = zone_polygon(zone_points)

    cfg = rule_config or RuleConfig.from_settings()
    detections = detector.detect(image)
    findings = [f for d in detections if (f := classify_finding(d, zone_shape, cfg)) is not None]
    findings.sort(key=lambda f: f.severity_score, reverse=True)

    evidence_dir = None
    if out_dir is not None:
        models = detector.model_versions() if hasattr(detector, "model_versions") else {}
        evidence_dir = str(write_evidence(
            out_dir, image_path, image, zone_points, zone.source, findings, detections, models,
        ))

    return ImageResult(
        image_path=str(image_path), width=width, height=height,
        zone_source=zone.source, zone_points=zone_points,
        detections=detections, findings=findings, evidence_dir=evidence_dir,
    )
