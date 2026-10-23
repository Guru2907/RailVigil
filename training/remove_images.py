"""Remove photos from the dataset (not relevant, not in India, duplicate scene...).

    python training/remove_images.py 0f47c8dc9867 2940a8d512f0 --reason "no track visible"

Deletes the image file and any label, and drops the manifest row. The ids
are the 12-character names of the files in datasets/images.
"""

import argparse

import rvdata as rv


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ids", nargs="+")
    p.add_argument("--reason", default="")
    args = p.parse_args()

    rows = rv.read_manifest()
    drop = set(args.ids)
    keep = []
    for r in rows:
        if r["image_id"] in drop:
            (rv.DATASETS / r["file"]).unlink(missing_ok=True)
            (rv.LABELS / f"{r['image_id']}.txt").unlink(missing_ok=True)
        else:
            keep.append(r)
    rv.write_manifest(keep)
    removed = len(rows) - len(keep)
    print(f"Removed {removed} photo(s){f' ({args.reason})' if args.reason else ''}. Manifest: {len(keep)} photos.")
    missing = drop - {r["image_id"] for r in rows}
    if missing:
        print(f"Not in the manifest: {', '.join(sorted(missing))}")


if __name__ == "__main__":
    main()
