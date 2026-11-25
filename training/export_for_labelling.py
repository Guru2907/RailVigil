"""Export photos for labelling from scratch: no model guesses at all.

    python training/export_for_labelling.py                    # the test split -> datasets/upload/test_blind
    python training/export_for_labelling.py --split val --name val_blind

The test set's answer key must not start from the baseline's own guesses (that
made the baseline look better than it is), so test photos are labelled blind,
by two people separately, and compared with label_agreement.py.

Output: datasets/upload/<name>/
    images/<image id>.jpg     the photos; the id in the name lets import_labels.py match them
    classes.txt               the class names to create in the labelling tool, in this order
    <name>.zip                the same images, ready to upload
Each labeller draws every encroachment object (a box is enough) and ONE
`railway_zone` polygon around the railway land. See training/LABELLING_GUIDE.md.
"""

import argparse
import shutil
import zipfile

import rvdata as rv


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split", default="test", choices=rv.SPLITS)
    p.add_argument("--name", default="")
    args = p.parse_args()
    name = args.name or f"{args.split}_blind"

    rows = [r for r in rv.read_manifest() if r["split"] == args.split and r["role"] != rv.TRAIN_ONLY]
    if not rows:
        raise SystemExit(f"No photos in the {args.split} split.")
    out = rv.DATASETS / "upload" / name
    if out.exists():
        shutil.rmtree(out)
    (out / "images").mkdir(parents=True)
    for r in rows:
        src = rv.DATASETS / r["file"]
        shutil.copy2(src, out / "images" / f"{r['image_id']}{src.suffix.lower()}")
    # debris_waste is not used: waste is labelled material_dump (see LABELLING_GUIDE.md).
    used = [c for c in rv.CLASSES if c != "debris_waste"]
    (out / "classes.txt").write_text("\n".join([*used, rv.ZONE_CLASS]) + "\n", encoding="utf-8")
    with zipfile.ZipFile(out / f"{name}.zip", "w", zipfile.ZIP_STORED) as z:
        for img in sorted((out / "images").iterdir()):
            z.write(img, f"images/{img.name}")
    by_country = {}
    for r in rows:
        by_country[r["country"]] = by_country.get(r["country"], 0) + 1
    print(f"{len(rows)} {args.split} photos -> {out}")
    print("   " + ", ".join(f"{c} {n}" for c, n in sorted(by_country.items(), key=lambda x: -x[1])))
    print(f"Upload {out / (name + '.zip')} to a NEW Roboflow project per labeller (classes: {out / 'classes.txt'}).")


if __name__ == "__main__":
    main()
