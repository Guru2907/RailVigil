"""
Measure the PRETRAINED baseline (Open Images V7 + YOLO-World, exactly as the
pipeline runs them) on the same frozen test split as the trained model, so
the paper can show the improvement honestly.

    python scripts/evaluate_baseline.py                 # from backend/, backend venv

The baseline only gives boxes, so the comparison is box AP50 per class
(trained model: the "mAP50 (box)" column from training/evaluate.py).
Writes training/runs/baseline_eval_test.json.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "training"))

import rvdata as rv  # noqa: E402

from app.cv.encroachment.detector import EncroachmentDetector  # noqa: E402
from app.cv.encroachment.pipeline import load_image  # noqa: E402
from app.cv.encroachment.taxonomy import CLASSES  # noqa: E402

# Low cut-off so AP covers the whole precision/recall curve, like Ultralytics' val.
AP_CONFIDENCE = 0.01
# Precision / recall reported at the pipeline's operating confidence.
OPERATING_CONFIDENCE = 0.25


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split", default="test", choices=rv.SPLITS)
    args = p.parse_args()

    images = sorted((rv.BUILD / "images" / args.split).glob("*"))
    if not images:
        raise SystemExit(f"No images in the {args.split} split. Run training/build_dataset.py first.")

    detector = EncroachmentDetector(min_confidence=AP_CONFIDENCE)
    preds, gts = {}, {}
    for i, path in enumerate(images, start=1):
        image = load_image(str(path))
        h, w = image.shape[:2]
        preds[path.stem] = [(d.cls, d.confidence, d.bbox) for d in detector.detect(image)]
        label = rv.BUILD / "labels" / args.split / f"{path.stem}.txt"
        gts[path.stem] = [(CLASSES[c], rv.polygon_box(pts, w, h)) for c, pts in rv.read_labels(label)]
        print(f"[{i}/{len(images)}] {path.name}: {len(preds[path.stem])} detections, {len(gts[path.stem])} labelled")

    ap = rv.evaluate_boxes(preds, gts)
    operating = rv.evaluate_boxes({k: [p for p in v if p[1] >= OPERATING_CONFIDENCE] for k, v in preds.items()}, gts)
    per_class = {
        c: {"ap50": ap[c]["ap50"], "n_gt": ap[c]["n_gt"],
            "precision": operating.get(c, {}).get("precision", 0.0), "recall": operating.get(c, {}).get("recall", 0.0)}
        for c in CLASSES if c in ap
    }
    valid = [v["ap50"] for v in per_class.values() if v["n_gt"]]
    report = {
        "model": "baseline: " + ", ".join(f"{n}@{v}" for n, v in detector.model_versions().items()),
        "split": args.split,
        "evaluated_at": rv.now_iso(),
        "images": len(images),
        "per_class": per_class,
        "map50_box": sum(valid) / len(valid) if valid else None,
        "note": f"Box AP50 (conf >= {AP_CONFIDENCE}); precision/recall at conf >= {OPERATING_CONFIDENCE}.",
    }
    rv.RUNS.mkdir(parents=True, exist_ok=True)
    out = rv.RUNS / f"baseline_eval_{args.split}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n| Class | AP50 (box) | P | R | labelled objects |")
    print("|---|---|---|---|---|")
    for c, v in per_class.items():
        print(f"| {c} | {v['ap50']:.3f} | {v['precision']:.3f} | {v['recall']:.3f} | {v['n_gt']} |")
    if report["map50_box"] is not None:
        print(f"| **all** | {report['map50_box']:.3f} | | | |")
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
