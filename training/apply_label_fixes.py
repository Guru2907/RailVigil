"""Delete wrong shapes from imported labels, from a reviewed fix list.

    python training/apply_label_fixes.py datasets/review/label_fixes.txt --labels-dir datasets/labels_staging --dry-run
    python training/apply_label_fixes.py datasets/review/label_fixes.txt --labels-dir datasets/labels_staging

Each line of the fix list:  <image id>: <shape numbers and/or class letters> | reason
  - numbers are the shape's position in the label file (0 = first line), as drawn
    on the review sheets;
  - a letter deletes every shape of that class: P permanent, T temporary,
    V vegetation, D debris, M material, C parked vehicle.
Lines starting with # are comments. The list is kept with the dataset as the
record of what was changed and why.
"""

import argparse
from pathlib import Path

import rvdata as rv

LETTER = {"P": "structure_permanent", "T": "structure_temporary", "V": "vegetation", "D": "debris_waste",
          "M": "material_dump", "C": "vehicle_parked"}


def parse(path: Path) -> dict[str, tuple[set[int], set[int], str]]:
    """image id -> (shape numbers, class indices, reason)."""
    fixes = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        head, _, reason = line.partition("|")
        image_id, _, spec = head.partition(":")
        numbers, classes = set(), set()
        for token in spec.split():
            if token.isdigit():
                numbers.add(int(token))
            elif token in LETTER:
                classes.add(rv.CLASSES.index(LETTER[token]))
            else:
                raise ValueError(f"{image_id.strip()}: cannot read {token!r}")
        fixes[image_id.strip()] = (numbers, classes, reason.strip())
    return fixes


def apply(labels, numbers: set[int], classes: set[int]):
    """(kept labels, deleted labels)."""
    kept, deleted = [], []
    for n, (c, pts) in enumerate(labels):
        (deleted if n in numbers or c in classes else kept).append((c, pts))
    return kept, deleted


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fixes", type=Path)
    p.add_argument("--labels-dir", type=Path, default=rv.LABELS)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    fixes = parse(args.fixes)
    deleted_by_class, photos, emptied, missing = {}, 0, [], []
    for image_id, (numbers, classes, _) in fixes.items():
        path = args.labels_dir / f"{image_id}.txt"
        if not path.is_file():
            missing.append(image_id)
            continue
        labels = rv.read_labels(path)
        out_of_range = [n for n in numbers if n >= len(labels)]
        if out_of_range:
            print(f"  {image_id}: no shape number {out_of_range} (it has {len(labels)}); those are skipped")
        kept, deleted = apply(labels, numbers, classes)
        for c, _ in deleted:
            deleted_by_class[rv.CLASSES[c]] = deleted_by_class.get(rv.CLASSES[c], 0) + 1
        photos += bool(deleted)
        if labels and not kept:
            emptied.append(image_id)
        if not args.dry_run:
            rv.write_labels(path, kept)
    verb = "Would delete" if args.dry_run else "Deleted"
    print(f"{verb} {sum(deleted_by_class.values())} shapes in {photos} photos: "
          + ", ".join(f"{c} {n}" for c, n in sorted(deleted_by_class.items(), key=lambda x: -x[1])))
    print(f"Photos left with no shapes (become clean examples): {len(emptied)}")
    if missing:
        print(f"Not found in {args.labels_dir}: {', '.join(missing)}")


if __name__ == "__main__":
    main()
