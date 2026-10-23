"""Assign location-safe train/val/test splits and build the folder YOLO trains on.

    python training/build_dataset.py

1. Every labelled photo without a split gets one (70/15/15). Photos of the
   same place (same `group`, or GPS within 300 m) always share a split, and
   existing splits never change: the test set stays frozen.
2. datasets/build/railvigil-seg/{images,labels}/{train,val,test} is rebuilt
   (hard links, so no extra disk space) with a data.yaml.
3. Prints object counts per class and split, so you can see which classes
   still need more examples.
"""

import argparse
import os
import shutil

import rvdata as rv

from app.cv.encroachment.taxonomy import CLASSES


def link(src, dst):
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--same-place-m", type=float, default=rv.SAME_PLACE_M)
    args = p.parse_args()

    rows = rv.read_manifest()
    labelled = [r for r in rows if (rv.LABELS / f"{r['image_id']}.txt").exists()]
    if not labelled:
        raise SystemExit("No labelled photos yet. Run prelabel.py, correct, then import_labels.py.")

    rv.assign_splits(labelled, same_place_m=args.same_place_m)
    leaks = rv.split_leaks(labelled, args.same_place_m)
    if leaks:
        raise SystemExit(f"Place groups split across train/test: {leaks[:5]}. Fix the `split` column in the manifest.")
    by_id = {r["image_id"]: r for r in labelled}
    for r in rows:
        if r["image_id"] in by_id:
            r["split"] = by_id[r["image_id"]]["split"]
    rv.write_manifest(rows)

    if rv.BUILD.exists():
        shutil.rmtree(rv.BUILD)
    for split in rv.SPLITS:
        (rv.BUILD / "images" / split).mkdir(parents=True)
        (rv.BUILD / "labels" / split).mkdir(parents=True)
    counts = {s: [0] * len(CLASSES) for s in rv.SPLITS}
    photos = {s: 0 for s in rv.SPLITS}
    negatives = {s: 0 for s in rv.SPLITS}
    for r in labelled:
        split = r["split"]
        image = rv.DATASETS / r["file"]
        label = rv.LABELS / f"{r['image_id']}.txt"
        link(image, rv.BUILD / "images" / split / image.name)
        shutil.copy2(label, rv.BUILD / "labels" / split / f"{image.stem}.txt")
        objs = rv.read_labels(label)
        photos[split] += 1
        negatives[split] += not objs
        for cls, _ in objs:
            counts[split][cls] += 1

    names = "\n".join(f"  {i}: {c}" for i, c in enumerate(CLASSES))
    (rv.BUILD / "data.yaml").write_text(
        f"path: {rv.BUILD.as_posix()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n{names}\n",
        encoding="utf-8",
    )

    width = max(len(c) for c in CLASSES)
    print(f"{'class':<{width}}  " + "  ".join(f"{s:>6}" for s in rv.SPLITS))
    for i, c in enumerate(CLASSES):
        print(f"{c:<{width}}  " + "  ".join(f"{counts[s][i]:>6}" for s in rv.SPLITS))
    print(f"{'photos':<{width}}  " + "  ".join(f"{photos[s]:>6}" for s in rv.SPLITS))
    print(f"{'(no objects)':<{width}}  " + "  ".join(f"{negatives[s]:>6}" for s in rv.SPLITS))
    print(f"\nDataset ready: {rv.BUILD / 'data.yaml'}")
    empty = [s for s in rv.SPLITS if not photos[s]]
    if empty:
        print(f"WARNING: no photos in {', '.join(empty)}. Splits are by place, so add photos from more places "
              "(or set `split` by hand in the manifest for a small test).")
    weak = [c for i, c in enumerate(CLASSES) if counts["train"][i] < 300]
    if weak:
        print(f"Below the ~300-object target in train: {', '.join(weak)}")


if __name__ == "__main__":
    main()
