"""Evaluate a trained run on the frozen TEST split (never seen in training).

    python training/evaluate.py --name seg-v1

Writes training/runs/<name>/eval_test.json and prints a Markdown table of
per-class precision, recall, mAP50 and mAP50-95 for masks and boxes. Only
numbers produced here (on the frozen test split) may be quoted in the
README, the UI or the paper (docs/EVALUATION.md).
"""

import argparse
import json

import rvdata as rv


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--device", default="0")
    args = p.parse_args()

    from ultralytics import YOLO

    run_dir = rv.RUNS / args.name
    weights = run_dir / "weights" / "best.pt"
    if not weights.is_file():
        raise SystemExit(f"No trained weights at {weights}")
    if not any((rv.BUILD / "images" / "test").glob("*")):
        raise SystemExit("The test split is empty. Add more labelled photos and rebuild the dataset.")

    m = YOLO(str(weights)).val(
        data=str(rv.BUILD / "data.yaml"), split="test", imgsz=args.imgsz, batch=args.batch,
        device=args.device, project=str(run_dir), name="test_eval", exist_ok=True, plots=True,
    )
    names = m.names
    per_class = {}
    for i, c in enumerate(m.ap_class_index):
        bp, br, b50, b5095 = m.box.class_result(i)
        sp, sr, s50, s5095 = m.seg.class_result(i)
        per_class[names[int(c)]] = {
            "box": {"precision": bp, "recall": br, "map50": b50, "map50_95": b5095},
            "mask": {"precision": sp, "recall": sr, "map50": s50, "map50_95": s5095},
        }
    overall = {
        "box": {"precision": m.box.mp, "recall": m.box.mr, "map50": m.box.map50, "map50_95": m.box.map},
        "mask": {"precision": m.seg.mp, "recall": m.seg.mr, "map50": m.seg.map50, "map50_95": m.seg.map},
    }
    meta_file = run_dir / "railvigil_run.json"
    report = {
        "run": args.name,
        "evaluated_at": rv.now_iso(),
        "split": "test",
        "weights": str(weights),
        "weights_sha12": rv.sha256_file(weights)[:12],
        "dataset_fingerprint": (json.loads(meta_file.read_text())["dataset"]["fingerprint"]
                                if meta_file.is_file() else None),
        "per_class": per_class,
        "overall": overall,
        "note": "Precision/recall at Ultralytics' best-F1 confidence; mAP over all confidences.",
    }
    (run_dir / "eval_test.json").write_text(json.dumps(report, indent=2, default=float), encoding="utf-8")

    def fmt(v):
        return f"{float(v):.3f}"

    print("\n| Class | P (mask) | R (mask) | mAP50 (mask) | mAP50-95 (mask) | mAP50 (box) |")
    print("|---|---|---|---|---|---|")
    for cls, r in per_class.items():
        k = r["mask"]
        print(f"| {cls} | {fmt(k['precision'])} | {fmt(k['recall'])} | {fmt(k['map50'])} | {fmt(k['map50_95'])} "
              f"| {fmt(r['box']['map50'])} |")
    o = overall["mask"]
    print(f"| **all** | {fmt(o['precision'])} | {fmt(o['recall'])} | {fmt(o['map50'])} | {fmt(o['map50_95'])} "
          f"| {fmt(overall['box']['map50'])} |")
    print(f"\nSaved {run_dir / 'eval_test.json'}")
    print("Compare with the pretrained baseline: backend/scripts/evaluate_baseline.py (box mAP50).")


if __name__ == "__main__":
    main()
