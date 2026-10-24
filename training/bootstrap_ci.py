"""95 % bootstrap confidence intervals for box AP50 on the test split.

    python training/bootstrap_ci.py --name railvigil-s        # after evaluate_baseline.py

The test set is small, so a single AP number can move a lot by chance. This
resamples the test photos with replacement (default 1000 times), recomputes
per-class box AP50 and the class mean for both the fine-tuned model and the
pretrained baseline on each resample, and reports the 2.5th-97.5th
percentiles. It also reports the paired difference (model - baseline), whose
interval tells whether the gap is larger than chance.

AP here uses rvdata.evaluate_boxes (IoU >= 0.5, all-point interpolation) for
BOTH models, so the comparison uses one definition. Baseline predictions come
from backend/scripts/evaluate_baseline.py (baseline_preds_test.json).
Classes with fewer than --min-objects test objects are left out of the mean.
"""

import argparse
import json
import math
import random

import rvdata as rv


def mean_ap(preds, gts, images, classes):
    sub_p = {}
    sub_g = {}
    for n, img in enumerate(images):         # duplicates get distinct keys
        key = f"{img}#{n}"
        sub_p[key] = preds.get(img, [])
        sub_g[key] = gts.get(img, [])
    res = rv.evaluate_boxes(sub_p, sub_g)
    per = {c: res[c]["ap50"] for c in classes if c in res and res[c]["n_gt"] > 0}
    vals = [v for v in per.values() if not math.isnan(v)]
    return (sum(vals) / len(vals) if vals else float("nan")), per


def percentile(values, q):
    values = sorted(v for v in values if not math.isnan(v))
    if not values:
        return float("nan")
    k = (len(values) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True, help="training run whose best.pt is evaluated")
    p.add_argument("--resamples", type=int, default=1000)
    p.add_argument("--min-objects", type=int, default=5)
    p.add_argument("--device", default="0")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    from ultralytics import YOLO

    base = json.loads((rv.RUNS / "baseline_preds_test.json").read_text(encoding="utf-8"))
    gts = {k: [(c, tuple(b)) for c, b in v] for k, v in base["gts"].items()}
    base_preds = {k: [(c, s, tuple(b)) for c, s, b in v] for k, v in base["preds"].items()}

    model = YOLO(str(rv.RUNS / args.name / "weights" / "best.pt"))
    preds = {}
    for img in sorted((rv.BUILD / "images" / "test").glob("*")):
        r = model.predict(str(img), conf=0.01, verbose=False, device=args.device)[0]
        names = r.names
        preds[img.stem] = [(names[int(c)], float(s), tuple(map(float, b)))
                           for b, c, s in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist(),
                                              strict=True)]

    images = sorted(gts)
    counts = {}
    for v in gts.values():
        for c, _ in v:
            counts[c] = counts.get(c, 0) + 1
    classes = [c for c in rv.CLASSES if counts.get(c, 0) >= args.min_objects]

    point_model, per_model = mean_ap(preds, gts, images, classes)
    point_base, per_base = mean_ap(base_preds, gts, images, classes)
    rng = random.Random(args.seed)
    boots = {"model": [], "baseline": [], "diff": []}
    per_boot = {c: {"model": [], "baseline": []} for c in classes}
    for _ in range(args.resamples):
        sample = [rng.choice(images) for _ in images]
        m, pm = mean_ap(preds, gts, sample, classes)
        b, pb = mean_ap(base_preds, gts, sample, classes)
        boots["model"].append(m)
        boots["baseline"].append(b)
        boots["diff"].append(m - b)
        for c in classes:
            per_boot[c]["model"].append(pm.get(c, float("nan")))
            per_boot[c]["baseline"].append(pb.get(c, float("nan")))

    def ci(values):
        return [percentile(values, 0.025), percentile(values, 0.975)]

    report = {
        "run": args.name, "resamples": args.resamples, "seed": args.seed, "test_photos": len(images),
        "classes": classes, "excluded_classes": {c: n for c, n in counts.items() if c not in classes},
        "mean_ap50": {"model": point_model, "model_ci95": ci(boots["model"]),
                      "baseline": point_base, "baseline_ci95": ci(boots["baseline"]),
                      "difference": point_model - point_base, "difference_ci95": ci(boots["diff"])},
        "per_class": {c: {"model": per_model.get(c), "model_ci95": ci(per_boot[c]["model"]),
                          "baseline": per_base.get(c), "baseline_ci95": ci(per_boot[c]["baseline"]),
                          "test_objects": counts[c]} for c in classes},
        "note": "Box AP50 by rvdata.evaluate_boxes for both models; test photos resampled with replacement.",
    }
    out = rv.RUNS / args.name / "bootstrap_ci_test.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    f = lambda x: f"{x:.3f}"  # noqa: E731
    print(f"\nBox AP50, 95 % bootstrap CI ({args.resamples} resamples of {len(images)} test photos)")
    print("| Class | Baseline | Fine-tuned | Test objects |")
    print("|---|---|---|---|")
    for c, v in report["per_class"].items():
        print(f"| {c} | {f(v['baseline'])} [{f(v['baseline_ci95'][0])}, {f(v['baseline_ci95'][1])}] | "
              f"{f(v['model'])} [{f(v['model_ci95'][0])}, {f(v['model_ci95'][1])}] | {v['test_objects']} |")
    m = report["mean_ap50"]
    print(f"| **Mean** | {f(m['baseline'])} [{f(m['baseline_ci95'][0])}, {f(m['baseline_ci95'][1])}] | "
          f"{f(m['model'])} [{f(m['model_ci95'][0])}, {f(m['model_ci95'][1])}] | |")
    print(f"\nDifference (fine-tuned - baseline): {f(m['difference'])} "
          f"[{f(m['difference_ci95'][0])}, {f(m['difference_ci95'][1])}]")
    print(f"Excluded (< {args.min_objects} test objects): {report['excluded_classes']}")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
