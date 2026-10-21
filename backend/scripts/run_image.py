"""
Run the encroachment pipeline on one image or a folder of images and print
the potential encroachments found -- no server, no database.

    python scripts/run_image.py photo.jpg --zone "[[0,400],[1280,400],[1280,720],[0,720]]"
    python scripts/run_image.py photos/            # each image needs <name>.zone.json
    python scripts/run_image.py photo.jpg --zone "[[0,0.6],[1,0.6],[1,1],[0,1]]" --zone-format normalized

The zone is the railway land (right-of-way) in the image. Without --zone, a
sidecar <image>.zone.json or a CAMERA_ZONES entry (--camera-label) is
required; the whole image is never used as the zone.
Evidence (annotated image, crops, findings.json) goes to --out.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `app` importable

from app.core import config  # noqa: E402
from app.core.errors import AppError  # noqa: E402
from app.cv.common.model_registry import ModelNotAvailable  # noqa: E402
from app.cv.encroachment.detector import EncroachmentDetector  # noqa: E402
from app.cv.encroachment.pipeline import IMAGE_EXTENSIONS, analyze_image  # noqa: E402


def _images(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(p for p in target.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)
    return [target]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help="an image file or a folder of images")
    parser.add_argument("--zone", help="JSON list of zone points (>= 3); applies to every image")
    parser.add_argument("--zone-format", choices=("pixel", "normalized"), default="pixel")
    parser.add_argument("--camera-label", help="camera label for a CAMERA_ZONES lookup")
    parser.add_argument("--models", default=",".join(config.ENC_MODELS),
                        help="comma-separated registered model names")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    parser.add_argument("--out", default=str(Path(config.OUTPUTS_DIR) / "encroachment" / stamp),
                        help="folder for evidence")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    target = Path(args.target)
    if not target.exists():
        parser.error(f"no such file or folder: {target}")
    try:
        zone = json.loads(args.zone) if args.zone else None
    except ValueError:
        parser.error("--zone must be valid JSON")

    detector = EncroachmentDetector(model_names=[m.strip() for m in args.models.split(",") if m.strip()])
    try:
        print("models:", ", ".join(f"{n}@{v}" for n, v in detector.model_versions().items()))
    except ModelNotAvailable as exc:
        print(f"error: {exc}")
        return 2

    images = _images(target)
    if not images:
        print("no images found")
        return 1

    total = 0
    for image in images:
        try:
            result = analyze_image(
                image, detector, manual_zone=zone, manual_format=args.zone_format,
                camera_label=args.camera_label, out_dir=args.out,
            )
        except AppError as exc:
            print(f"\n{image.name}: skipped - {exc.message}")
            continue
        total += len(result.findings)
        print(f"\n{image.name}  ({result.width}x{result.height}, zone: {result.zone_source}, "
              f"{len(result.detections)} relevant detections, {len(result.findings)} findings)")
        for i, f in enumerate(result.findings, start=1):
            note = f"  [{'; '.join(f.notes)}]" if f.notes else ""
            print(f"  #{i} {f.cls:<20} {f.severity:<8} score {f.severity_score:.2f}  "
                  f"inside {f.overlap_ratio:.0%}  conf {f.confidence:.2f}  ({f.label}){note}")
    print(f"\n{total} potential encroachment(s) in {len(images)} image(s). Evidence: {args.out}")
    print("Baseline pretrained models; accuracy not measured. Findings need officer review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
