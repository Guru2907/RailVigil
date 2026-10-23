"""Evidence for one analysed image: an annotated copy, one crop per finding,
and findings.json. Written to <out_dir>/<image stem>/."""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

# BGR colours by severity; detections that did not become findings are grey.
SEVERITY_COLOURS = {
    "critical": (0, 0, 255),
    "high": (0, 140, 255),
    "medium": (0, 215, 255),
    "low": (0, 180, 0),
}
DETECTION_COLOUR = (160, 160, 160)
ZONE_COLOUR = (255, 255, 0)
CROP_MARGIN = 0.1  # extra context around each crop, as a share of the box size


def _clip_box(bbox, width, height, margin=0.0):
    x1, y1, x2, y2 = bbox
    mx, my = (x2 - x1) * margin, (y2 - y1) * margin
    return (
        max(0, int(x1 - mx)), max(0, int(y1 - my)),
        min(width, int(x2 + mx)), min(height, int(y2 + my)),
    )


def annotate(image_bgr, zone_points, findings, detections):
    out = image_bgr.copy()
    h, w = out.shape[:2]
    zone = np.array(zone_points, dtype=np.int32)
    overlay = out.copy()
    cv2.fillPoly(overlay, [zone], ZONE_COLOUR)
    out = cv2.addWeighted(overlay, 0.15, out, 0.85, 0)
    cv2.polylines(out, [zone], isClosed=True, color=ZONE_COLOUR, thickness=2)

    finding_boxes = {tuple(f.bbox) for f in findings}
    for det in detections:
        if tuple(det.bbox) not in finding_boxes:
            x1, y1, x2, y2 = _clip_box(det.bbox, w, h)
            cv2.rectangle(out, (x1, y1), (x2, y2), DETECTION_COLOUR, 1)

    for i, f in enumerate(findings, start=1):
        colour = SEVERITY_COLOURS[f.severity]
        x1, y1, x2, y2 = _clip_box(f.bbox, w, h)
        if f.outline:
            # Segmentation model: draw the real object outline, box kept thin for reference
            cv2.polylines(out, [np.array(f.outline, dtype=np.int32)], isClosed=True, color=colour, thickness=2)
            cv2.rectangle(out, (x1, y1), (x2, y2), colour, 1)
        else:
            cv2.rectangle(out, (x1, y1), (x2, y2), colour, 2)
        text = f"#{i} {f.cls} {f.severity} {f.confidence:.2f}"
        cv2.putText(out, text, (x1, max(12, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 2)
    return out


def write_evidence(out_dir, image_path, image_bgr, zone_points, zone_source, findings, detections,
                   models: dict) -> Path:
    target = Path(out_dir) / Path(image_path).stem
    crops = target / "crops"
    crops.mkdir(parents=True, exist_ok=True)
    h, w = image_bgr.shape[:2]

    cv2.imwrite(str(target / "annotated.jpg"), annotate(image_bgr, zone_points, findings, detections))
    crop_files = []
    for i, f in enumerate(findings, start=1):
        x1, y1, x2, y2 = _clip_box(f.bbox, w, h, CROP_MARGIN)
        name = f"finding_{i:02d}_{f.cls}.jpg"
        if x2 > x1 and y2 > y1:
            cv2.imwrite(str(crops / name), image_bgr[y1:y2, x1:x2])
            crop_files.append(name)
        else:
            crop_files.append(None)

    report = {
        "image": str(image_path),
        "width": w,
        "height": h,
        "generated_at": datetime.now(UTC).isoformat(),
        "note": ("Potential encroachments for officer review. Pretrained baseline: accuracy not measured; "
                 "trained models: see docs/EVALUATION.md."),
        "models": models,
        "zone": {"source": zone_source, "points_px": zone_points},
        "detections_total": len(detections),
        "findings": [{**asdict(f), "crop": c} for f, c in zip(findings, crop_files, strict=True)],
    }
    (target / "findings.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return target
