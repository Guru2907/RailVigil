"""Bring corrected labels back from Roboflow or CVAT.

Export the project as "COCO Segmentation" (Roboflow: the YOLO entries in its
list sit under "Convert To Object Detection" and would turn outlines into
boxes), "YOLOv8" segmentation, or "Ultralytics YOLO Segmentation 1.0" (CVAT),
unzip it, then:

    python training/import_labels.py path/to/export
    python training/import_labels.py path/to/export --labels-dir datasets/labels_test/A   # one labeller's test labels

Labels are matched to manifest photos by their image id (the first 12 hex
characters of the file name, which both tools keep), class names are mapped
by name (so the tool's class order does not matter), and written to
datasets/labels/<id>.txt. A photo exported with no objects gets an empty
label file: a "clean corridor" negative example, which is useful.

A polygon labelled `railway_zone` is not an object: it is the photo's railway
land, saved as <zones-dir>/<id>.json (normalised points), the same format as a
zone sidecar. It is used to evaluate the app's real decision rule. If the
railway land was drawn as several pieces (one per track, say), every piece is
kept under "pieces" and "points" holds the largest; tiny pieces under 2 % of the
zone's area are stray clicks and are dropped.
"""

import argparse
import json
from pathlib import Path

import rvdata as rv


def export_class_names(export: Path) -> list[str]:
    import yaml

    candidates = list(export.rglob("data.yaml")) + list(export.rglob("*.yaml"))
    if not candidates:
        raise SystemExit(f"No data.yaml found in {export}")
    data = yaml.safe_load(candidates[0].read_text(encoding="utf-8"))
    names = data.get("names")
    if isinstance(names, dict):
        return [names[k] for k in sorted(names, key=int)]
    return list(names)


def load_export(export: Path) -> dict[str, list]:
    """Exported image file name -> [(RailVigil class index, normalised outline)],
    from a COCO JSON export if there is one, otherwise from YOLO label files."""
    import json

    for path in export.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "images" in data and "annotations" in data:
            labels = {}
            for json_file in export.rglob("*.json"):  # Roboflow writes one per split folder
                part = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(part, dict) and "annotations" in part:
                    labels.update(rv.coco_labels(part))
            return labels
    remap = rv.class_remap(export_class_names(export))
    return {
        f.name: [(remap[c], pts) for c, pts in rv.read_labels(label)]
        for f in export.rglob("*") if f.suffix.lower() in rv.IMAGE_EXTENSIONS
        for label in [f.parent.parent / "labels" / f"{f.stem}.txt"]
        if label.is_file()
    }


STRAY_PIECE = 0.02   # a zone piece smaller than this share of the zone's area is a stray click


def polygon_area(pts) -> float:
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1], strict=True))) / 2


def split_zone(labels):
    """(object labels, railway-zone pieces or None). Pieces are sorted largest first;
    pieces under STRAY_PIECE of the total area (a stray click) are dropped."""
    objects = [(c, pts) for c, pts in labels if c != rv.ZONE_INDEX]
    zones = sorted((pts for c, pts in labels if c == rv.ZONE_INDEX), key=polygon_area, reverse=True)
    if not zones:
        return objects, None
    total = sum(polygon_area(z) for z in zones) or 1.0
    kept = [z for i, z in enumerate(zones) if i == 0 or polygon_area(z) / total >= STRAY_PIECE]
    return objects, [[[round(x, 6), round(y, 6)] for x, y in z] for z in kept]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("export", type=Path)
    p.add_argument("--overwrite", action="store_true", help="replace labels that were already imported")
    p.add_argument("--labels-dir", type=Path, default=rv.LABELS,
                   help="where to write the labels (default datasets/labels); use a separate folder per labeller")
    p.add_argument("--zones-dir", type=Path, default=None,
                   help="where to write railway_zone polygons (default: a 'zones' folder next to --labels-dir)")
    p.add_argument("--allow-prelabels", action="store_true",
                   help="smoke tests only: accept an uncorrected prelabel.py folder as labels")
    args = p.parse_args()

    if any(args.export.rglob(rv.PRELABEL_MARKER)) and not args.allow_prelabels:
        raise SystemExit(
            "This is a prelabel.py output folder: machine guesses, not ground truth. Upload it to Roboflow/CVAT,\n"
            "correct every label, export, and import the export instead. (--allow-prelabels exists for smoke tests.)")

    known = {r["image_id"] for r in rv.read_manifest()}
    labels_dir = args.labels_dir
    default_zones = "zones" if labels_dir == rv.LABELS else f"{labels_dir.name}_zones"
    zones_dir = args.zones_dir or labels_dir.parent / default_zones
    labels_dir.mkdir(parents=True, exist_ok=True)
    labels_by_name = load_export(args.export)
    images = [f for f in args.export.rglob("*") if f.suffix.lower() in rv.IMAGE_EXTENSIONS]
    written = skipped = negatives = objects = zones = 0
    multi_piece = []
    unmatched = []
    for img in images:
        image_id = rv.image_id_from_export_name(img.name, known)
        if image_id is None:
            unmatched.append(img.name)
            continue
        target = labels_dir / f"{image_id}.txt"
        if target.exists() and not args.overwrite:
            skipped += 1
            continue
        labels, pieces = split_zone(labels_by_name.get(img.name, []))
        rv.write_labels(target, labels)
        if pieces:
            zones_dir.mkdir(parents=True, exist_ok=True)
            zone = {"format": "normalized", "points": pieces[0]}
            if len(pieces) > 1:
                zone["pieces"] = pieces
                multi_piece.append(image_id)
            (zones_dir / f"{image_id}.json").write_text(json.dumps(zone), encoding="utf-8")
            zones += 1
        written += 1
        objects += len(labels)
        negatives += not labels

    print(f"Imported {written} label files into {labels_dir} ({objects} objects, {negatives} clean negatives, "
          f"{zones} railway zones); skipped {skipped} already imported (use --overwrite to replace).")
    if multi_piece:
        print(f"{len(multi_piece)} zones were drawn in several pieces; all pieces kept: {', '.join(multi_piece[:8])}")
    if written - zones:
        print(f"WARNING: {written - zones} photos have no railway_zone")
    if unmatched:
        print(f"WARNING: {len(unmatched)} exported images are not in the manifest "
              f"(renamed, or never added with add_images.py): {', '.join(unmatched[:8])}")


if __name__ == "__main__":
    main()
