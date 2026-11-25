"""How closely two people labelled the same photos.

    python training/label_agreement.py datasets/labels_test/A datasets/labels_test/B

Both folders hold YOLO label files (<image id>.txt) for the same photos,
imported with `import_labels.py --labels-dir`. Reported per class:
  - box agreement: boxes of the same class matched one-to-one at IoU >= 0.5;
    agreement = 2 x matched / (boxes by A + boxes by B)  (an F1 between labellers);
  - Cohen's kappa on "does this photo contain the class at all" (chance-corrected).
Zones (the *_zones folders next to each) are compared by their mean IoU.
Writes a markdown table to stdout and to <A>/../agreement.md.
"""

import argparse
import json
from pathlib import Path

import rvdata as rv


def boxes(path: Path) -> list[tuple[int, tuple[float, float, float, float]]]:
    if not path.is_file():
        return []
    out = []
    for cls, pts in rv.read_labels(path):
        xs, ys = [x for x, _ in pts], [y for _, y in pts]
        out.append((cls, (min(xs), min(ys), max(xs), max(ys))))
    return out


def match_count(a: list, b: list, iou: float = 0.5) -> int:
    """Greedy one-to-one matching, best IoU first."""
    pairs = sorted(((rv.box_iou(x, y), i, j) for i, x in enumerate(a) for j, y in enumerate(b)), reverse=True)
    used_a, used_b, n = set(), set(), 0
    for v, i, j in pairs:
        if v < iou:
            break
        if i not in used_a and j not in used_b:
            used_a.add(i)
            used_b.add(j)
            n += 1
    return n


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def polygon_iou(p: list, q: list) -> float:
    from shapely.geometry import Polygon

    a, b = Polygon(p).buffer(0), Polygon(q).buffer(0)
    union = a.union(b).area
    return a.intersection(b).area / union if union else 0.0


def agreement(dir_a: Path, dir_b: Path) -> dict:
    ids = sorted({f.stem for f in dir_a.glob("*.txt")} & {f.stem for f in dir_b.glob("*.txt")})
    per = {}
    for ci, cname in enumerate(rv.CLASSES):
        n_a = n_b = matched = 0
        has_a, has_b = [], []
        for i in ids:
            a = [bx for c, bx in boxes(dir_a / f"{i}.txt") if c == ci]
            b = [bx for c, bx in boxes(dir_b / f"{i}.txt") if c == ci]
            n_a, n_b = n_a + len(a), n_b + len(b)
            matched += match_count(a, b)
            has_a.append(bool(a))
            has_b.append(bool(b))
        per[cname] = {"boxes_a": n_a, "boxes_b": n_b, "matched": matched,
                      "box_agreement": 2 * matched / (n_a + n_b) if n_a + n_b else float("nan"),
                      "kappa": cohen_kappa(has_a, has_b)}
    zones = []
    za, zb = dir_a.parent / f"{dir_a.name}_zones", dir_b.parent / f"{dir_b.name}_zones"
    for i in ids:
        fa, fb = za / f"{i}.json", zb / f"{i}.json"
        if fa.is_file() and fb.is_file():
            zones.append(polygon_iou(json.loads(fa.read_text())["points"], json.loads(fb.read_text())["points"]))
    return {"photos": len(ids), "per_class": per,
            "zone_mean_iou": sum(zones) / len(zones) if zones else float("nan"), "zones_compared": len(zones)}


def table(res: dict) -> str:
    f = lambda x: "–" if x != x else f"{x:.2f}"  # noqa: E731  (NaN check)
    lines = [f"Labeller agreement on {res['photos']} photos", "",
             "| Class | Boxes A | Boxes B | Matched (IoU ≥ 0.5) | Box agreement | Kappa (present / absent) |",
             "|---|---|---|---|---|---|"]
    for c, v in res["per_class"].items():
        lines.append(f"| {c} | {v['boxes_a']} | {v['boxes_b']} | {v['matched']} | {f(v['box_agreement'])} "
                     f"| {f(v['kappa'])} |")
    lines += ["", f"Railway zone: mean IoU {f(res['zone_mean_iou'])} over {res['zones_compared']} photos."]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("labels_a", type=Path)
    p.add_argument("labels_b", type=Path)
    args = p.parse_args()
    md = table(agreement(args.labels_a, args.labels_b))
    print(md)
    (args.labels_a.parent / "agreement.md").write_text(md + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
