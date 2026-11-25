"""Final test: every model on the blind-labelled test photos, with bootstrap intervals.

Stage 1, predictions (one file per model, in --out):

    python training/evaluate_test.py predict --model v2-s-f10 --labels datasets/labels_test/A
    python training/evaluate_test.py predict --model railvigil-s --labels datasets/labels_test/A
    # the pretrained ensemble exactly as the app runs it; needs the backend venv:
    backend/.venv/Scripts/python training/evaluate_test.py predict --model baseline --labels datasets/labels_test/A

Stage 2, scores:

    python training/evaluate_test.py score --labels datasets/labels_test/A --models baseline railvigil-s v2-s-f10

Scoring uses ONE definition for every model: box AP50 from rvdata.evaluate_boxes
(IoU >= 0.5, all-point interpolation; predictions kept down to confidence 0.01),
averaged over the classes with at least --min-objects test objects. The test
photos are resampled with replacement (--resamples times, the same resamples for
every model), giving 95 % intervals for each model and for the paired difference
between two models. Results are reported for all photos, Indian photos and photos
from other countries.

For fine-tuned models, stage 1 also records Ultralytics' own mask and box mAP on
the same labels, comparable with the validation tables.

Per-class hybrid (each class taken from the model that is best at it ON
VALIDATION, then scored on test once):

    python training/evaluate_test.py predict --split val --model baseline --labels datasets/labels \\
        --out training/runs/val_eval
    python training/evaluate_test.py score --split val --labels datasets/labels --models baseline v2-m-f10 \\
        --out training/runs/val_eval --report training/runs/val_eval/report
    python training/evaluate_test.py hybrid --labels datasets/labels_test/A --models baseline v2-m-f10 \\
        --val-report training/runs/val_eval/report.json --name hybrid
"""

import argparse
import json
import math
import os
import random
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rvdata as rv  # noqa: E402

OUT = rv.RUNS / "test_eval"
AP_CONFIDENCE = 0.01
GROUPS = ("all", "India", "other countries")


def test_photos(labels_dir: Path, split: str = "test") -> list[dict]:
    """Manifest rows of the split's photos that have a label file in labels_dir."""
    return [r for r in rv.read_manifest()
            if r["split"] == split and (labels_dir / f"{r['image_id']}.txt").is_file()]


def route_by_validation(val_report: dict, models: list[str]) -> dict[str, str]:
    """For each class, the candidate with the highest validation AP50 (ties: the first listed)."""
    per = val_report["groups"]["all"]["per_class_ap50"]
    routing = {}
    for c in val_report["classes"]:
        scores = [(per[m][c]["value"], -i, m) for i, m in enumerate(models)
                  if m in per and not math.isnan(per[m][c]["value"])]
        if scores:
            routing[c] = max(scores)[2]
    return routing


def combine(preds_by_model: dict[str, dict], routing: dict[str, str], fallback: str) -> dict:
    """Hybrid predictions: class c comes only from routing[c] (others from the fallback model)."""
    images = set().union(*(p.keys() for p in preds_by_model.values()))
    out = {}
    for img in images:
        out[img] = [d for m, preds in preds_by_model.items() for d in preds.get(img, [])
                    if routing.get(d[0], fallback) == m]
    return out


def group_of(row: dict) -> str:
    return "India" if row.get("country") == "India" else "other countries"


def ground_truth(rows: list[dict], labels_dir: Path) -> dict:
    from PIL import Image

    gts = {}
    for r in rows:
        with Image.open(rv.DATASETS / r["file"]) as im:
            w, h = im.size
        gts[r["image_id"]] = [(rv.CLASSES[c], rv.polygon_box(pts, w, h))
                              for c, pts in rv.read_labels(labels_dir / f"{r['image_id']}.txt")]
    return gts


# --- stage 1 ----------------------------------------------------------------------

def predict_finetuned(name: str, rows: list[dict], labels_dir: Path, imgsz: int) -> dict:
    from ultralytics import YOLO

    model = YOLO(str(rv.RUNS / name / "weights" / "best.pt"))
    preds = {}
    for r in rows:
        res = model.predict(str(rv.DATASETS / r["file"]), conf=AP_CONFIDENCE, imgsz=imgsz, verbose=False)[0]
        preds[r["image_id"]] = [
            (res.names[int(c)], float(s), tuple(map(float, b)))
            for b, c, s in zip(res.boxes.xyxy.tolist(), res.boxes.cls.tolist(), res.boxes.conf.tolist(), strict=True)
        ]
    return {"preds": preds, "ultralytics": ultralytics_val(model, rows, labels_dir, imgsz)}


def ultralytics_val(model, rows: list[dict], labels_dir: Path, imgsz: int) -> dict:
    """Ultralytics mask/box mAP on these labels, per group (a temporary YOLO folder)."""
    tmp = Path(tempfile.mkdtemp())
    try:
        out = {}
        for group in GROUPS:
            chosen = [r for r in rows if group == "all" or group_of(r) == group]
            root = tmp / group.replace(" ", "_")
            (root / "images" / "val").mkdir(parents=True)
            (root / "labels" / "val").mkdir(parents=True)
            for r in chosen:
                src = rv.DATASETS / r["file"]
                dst = root / "images" / "val" / f"{r['image_id']}{src.suffix.lower()}"
                try:
                    os.link(src, dst)
                except OSError:
                    shutil.copy2(src, dst)
                shutil.copy2(labels_dir / f"{r['image_id']}.txt", root / "labels" / "val" / f"{r['image_id']}.txt")
            names = "\n".join(f"  {i}: {c}" for i, c in enumerate(rv.CLASSES))
            (root / "data.yaml").write_text(f"path: {root.as_posix()}\ntrain: images/val\nval: images/val\n"
                                            f"names:\n{names}\n", encoding="utf-8")
            m = model.val(data=str(root / "data.yaml"), split="val", imgsz=imgsz, batch=4, workers=0,
                          verbose=False, plots=False, project=str(tmp / "runs"), name="v", exist_ok=True)
            out[group] = {"photos": len(chosen), "mask_map50": float(m.seg.map50), "mask_map50_95": float(m.seg.map),
                          "box_map50": float(m.box.map50), "box_map50_95": float(m.box.map)}
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def predict_baseline(rows: list[dict]) -> dict:
    """The pretrained ensemble (Open Images V7 + YOLO-World), as the app runs it."""
    sys.path.insert(0, str(rv.REPO / "backend"))
    from app.cv.encroachment.detector import EncroachmentDetector
    from app.cv.encroachment.pipeline import load_image

    detector = EncroachmentDetector(min_confidence=AP_CONFIDENCE)
    preds = {}
    for r in rows:
        image = load_image(str(rv.DATASETS / r["file"]))
        preds[r["image_id"]] = [(d.cls, d.confidence, tuple(map(float, d.bbox))) for d in detector.detect(image)]
    return {"preds": preds, "models": list(detector.model_names)}


# --- stage 2 ----------------------------------------------------------------------

def mean_ap(preds: dict, gts: dict, images: list[str], classes: list[str]) -> tuple[float, dict]:
    sub_p, sub_g = {}, {}
    for n, img in enumerate(images):          # a resample can repeat a photo: distinct keys
        sub_p[f"{img}#{n}"] = preds.get(img, [])
        sub_g[f"{img}#{n}"] = gts.get(img, [])
    res = rv.evaluate_boxes(sub_p, sub_g)
    per = {c: res[c]["ap50"] for c in classes if c in res and res[c]["n_gt"] > 0}
    vals = [v for v in per.values() if not math.isnan(v)]
    return (sum(vals) / len(vals) if vals else float("nan")), per


def percentile(values: list[float], q: float) -> float:
    values = sorted(v for v in values if not math.isnan(v))
    if not values:
        return float("nan")
    k = (len(values) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def ci(values: list[float]) -> list[float]:
    return [percentile(values, 0.025), percentile(values, 0.975)]


def score(models: list[str], rows: list[dict], gts: dict, preds: dict, resamples: int, min_objects: int,
          seed: int) -> dict:
    counts: dict[str, int] = {}
    for v in gts.values():
        for c, _ in v:
            counts[c] = counts.get(c, 0) + 1
    classes = [c for c in rv.CLASSES if counts.get(c, 0) >= min_objects]
    report = {"classes": classes, "excluded_classes": {c: n for c, n in counts.items() if c not in classes},
              "test_objects": counts, "resamples": resamples, "seed": seed, "groups": {}}
    rng = random.Random(seed)
    for group in GROUPS:
        images = sorted(r["image_id"] for r in rows if group == "all" or group_of(r) == group)
        point = {m: mean_ap(preds[m], gts, images, classes) for m in models}
        boots: dict[str, list[float]] = {m: [] for m in models}
        per_boot: dict[str, dict[str, list[float]]] = {m: {c: [] for c in classes} for m in models}
        for _ in range(resamples):
            sample = [rng.choice(images) for _ in images]
            for m in models:
                v, per = mean_ap(preds[m], gts, sample, classes)
                boots[m].append(v)
                for c in classes:
                    per_boot[m][c].append(per.get(c, float("nan")))
        pairs = {}
        for i, a in enumerate(models):
            for b in models[i + 1:]:
                diff = [x - y for x, y in zip(boots[b], boots[a], strict=True)]
                pairs[f"{b} - {a}"] = {"difference": point[b][0] - point[a][0], "ci95": ci(diff),
                                       "share_above_zero": sum(d > 0 for d in diff) / len(diff)}
        report["groups"][group] = {
            "photos": len(images),
            "objects": {c: sum(1 for i in images for k, _ in gts[i] if k == c) for c in classes},
            "mean_ap50": {m: {"value": point[m][0], "ci95": ci(boots[m])} for m in models},
            "per_class_ap50": {m: {c: {"value": point[m][1].get(c, float("nan")), "ci95": ci(per_boot[m][c])}
                                   for c in classes} for m in models},
            "paired_differences": pairs,
        }
    return report


def markdown(report: dict, models: list[str], extra: dict) -> str:
    def f(x):
        return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.3f}"

    def iv(d):
        return f"{f(d['value'])} [{f(d['ci95'][0])}, {f(d['ci95'][1])}]"

    lines = [f"Box AP50 (IoU 0.5), mean over {', '.join(report['classes'])}; "
             f"95 % bootstrap intervals from {report['resamples']} paired resamples of the test photos.", ""]
    head = "| Model | " + " | ".join(f"{g} ({report['groups'][g]['photos']})" for g in GROUPS) + " |"
    lines += [head, "|---|" + "---|" * len(GROUPS)]
    for m in models:
        lines.append(f"| {m} | " + " | ".join(iv(report["groups"][g]["mean_ap50"][m]) for g in GROUPS) + " |")
    lines += ["", "Paired differences (row model minus column model), all photos:", "",
              "| Difference | Value | 95 % interval | Resamples above 0 |", "|---|---|---|---|"]
    for k, v in report["groups"]["all"]["paired_differences"].items():
        lines.append(f"| {k} | {f(v['difference'])} | [{f(v['ci95'][0])}, {f(v['ci95'][1])}] | "
                     f"{v['share_above_zero']:.0%} |")
    lines += ["", "Per class, all photos (objects in brackets):", "",
              "| Model | " + " | ".join(f"{c} ({report['groups']['all']['objects'][c]})" for c in report["classes"])
              + " |", "|---|" + "---|" * len(report["classes"])]
    for m in models:
        per = report["groups"]["all"]["per_class_ap50"][m]
        lines.append(f"| {m} | " + " | ".join(iv(per[c]) for c in report["classes"]) + " |")
    if report["excluded_classes"]:
        lines += ["", "Left out of the mean (fewer than the minimum objects): "
                  + ", ".join(f"{c} ({n})" for c, n in report["excluded_classes"].items())]
    ult = {m: e["ultralytics"] for m, e in extra.items() if e.get("ultralytics")}
    if ult:
        lines += ["", "Ultralytics metrics of the fine-tuned models on the same labels (mask mAP50 / mask mAP50-95 "
                  "/ box mAP50):", "", "| Model | " + " | ".join(GROUPS) + " |", "|---|" + "---|" * len(GROUPS)]
        for m, u in ult.items():
            lines.append(f"| {m} | " + " | ".join(
                f"{u[g]['mask_map50']:.3f} / {u[g]['mask_map50_95']:.3f} / {u[g]['box_map50']:.3f}" for g in GROUPS)
                + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("stage", choices=["predict", "score", "hybrid"])
    p.add_argument("--labels", type=Path, required=True, help="the test answer key, e.g. datasets/labels_test/A")
    p.add_argument("--split", default="test", choices=rv.SPLITS, help="which manifest split to use")
    p.add_argument("--val-report", type=Path, help="hybrid: JSON from 'score --split val' that sets the routing")
    p.add_argument("--name", default="hybrid", help="hybrid: name of the combined model")
    p.add_argument("--model", help="predict: a training run name, or 'baseline'")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--models", nargs="+", help="score: models in reporting order")
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--resamples", type=int, default=1000)
    p.add_argument("--min-objects", type=int, default=5)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--report", type=Path, help="score: also write the JSON and markdown here (without suffix)")
    args = p.parse_args()

    rows = test_photos(args.labels, args.split)
    if not rows:
        raise SystemExit(f"No {args.split} photos with labels in {args.labels}")
    args.out.mkdir(parents=True, exist_ok=True)

    if args.stage == "hybrid":
        if not (args.models and args.val_report):
            raise SystemExit("hybrid needs --models and --val-report")
        routing = route_by_validation(json.loads(args.val_report.read_text(encoding="utf-8")), args.models)
        loaded = {m: json.loads((args.out / f"preds_{m}.json").read_text(encoding="utf-8")) for m in args.models}
        preds = {m: e["preds"] for m, e in loaded.items()}
        result = {"model": args.name, "routing": routing, "fallback": args.models[0], "candidates": args.models,
                  "chosen_on": str(args.val_report), "preds": combine(preds, routing, args.models[0]),
                  "labels": str(args.labels), "photos": len(rows)}
        (args.out / f"preds_{args.name}.json").write_text(json.dumps(result), encoding="utf-8")
        print(f"{args.name}: routing chosen on validation: {routing}")
        return

    if args.stage == "predict":
        if not args.model:
            raise SystemExit("predict needs --model")
        result = predict_baseline(rows) if args.model == "baseline" else \
            predict_finetuned(args.model, rows, args.labels, args.imgsz)
        result.update({"model": args.model, "labels": str(args.labels), "photos": len(rows), "imgsz": args.imgsz})
        (args.out / f"preds_{args.model}.json").write_text(json.dumps(result), encoding="utf-8")
        print(f"{args.model}: predictions for {len(rows)} photos -> {args.out / f'preds_{args.model}.json'}")
        return

    if not args.models:
        raise SystemExit("score needs --models")
    extra = {m: json.loads((args.out / f"preds_{m}.json").read_text(encoding="utf-8")) for m in args.models}
    preds = {m: {k: [(c, s, tuple(b)) for c, s, b in v] for k, v in e["preds"].items()} for m, e in extra.items()}
    gts = ground_truth(rows, args.labels)
    report = score(args.models, rows, gts, preds, args.resamples, args.min_objects, args.seed)
    report.update({"labels": str(args.labels), "photos": len(rows),
                   "ultralytics": {m: e["ultralytics"] for m, e in extra.items() if e.get("ultralytics")},
                   "baseline_models": extra.get("baseline", {}).get("models")})
    md = markdown(report, args.models, extra)
    print(md)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        args.report.with_suffix(".md").write_text(md, encoding="utf-8")
        print(f"written: {args.report.with_suffix('.json')} and .md")


if __name__ == "__main__":
    main()
