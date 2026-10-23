"""Add a folder of photos to the dataset: copy each into datasets/images/<id>,
read its GPS and capture time, and record its source and licence in the
manifest. Re-running on the same files is safe: duplicates are skipped.

    python training/add_images.py datasets/incoming/own_kalyan --source own --licence own --author "Gurpreet"
    python training/add_images.py datasets/incoming/commons --source wikimedia --credits credits.csv

--credits: optional CSV inside the folder with columns
    filename, source_url, author, licence[, group]
for per-file credit (Wikimedia Commons / Flickr / Mapillary downloads).
"""

import argparse
import csv
import shutil
from pathlib import Path

import rvdata as rv


def load_credits(folder: Path, name: str | None) -> dict[str, dict]:
    if not name:
        return {}
    path = folder / name
    with path.open(newline="", encoding="utf-8") as f:
        return {row["filename"].strip(): row for row in csv.DictReader(f)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("folder", type=Path)
    p.add_argument("--source", required=True, help="own | wikimedia | mapillary | flickr | taco | roboflow | other")
    p.add_argument("--licence", default="",
                   help='e.g. "own", "CC BY-SA 4.0" (required unless given per file in --credits)')
    p.add_argument("--author", default="")
    p.add_argument("--source-url", default="")
    p.add_argument("--group", default="", help="optional place name: photos with the same group always share a split")
    p.add_argument("--credits", help="CSV file inside the folder with per-file credits")
    args = p.parse_args()

    files = sorted(f for f in args.folder.rglob("*") if f.suffix.lower() in rv.IMAGE_EXTENSIONS)
    if not files:
        raise SystemExit(f"No images found in {args.folder}")
    credits = load_credits(args.folder, args.credits)

    rows = rv.read_manifest()
    known = {r["image_id"] for r in rows}
    rv.IMAGES.mkdir(parents=True, exist_ok=True)
    added = dupes = located = 0
    missing_licence = []

    for f in files:
        image_id = rv.image_id_for(f)
        if image_id in known:
            dupes += 1
            continue
        credit = credits.get(f.name, {})
        licence = (credit.get("licence") or args.licence).strip()
        if not licence:
            missing_licence.append(f.name)
            continue
        target = rv.IMAGES / f"{image_id}{f.suffix.lower()}"
        shutil.copy2(f, target)
        lat, lon, taken = rv.exif_info(f)
        located += lat is not None
        rows.append({
            "image_id": image_id,
            "file": f"images/{target.name}",
            "original_name": f.name,
            "source": args.source,
            "source_url": (credit.get("source_url") or args.source_url).strip(),
            "licence": licence,
            "author": (credit.get("author") or args.author).strip(),
            "lat": f"{lat:.6f}" if lat is not None else "",
            "lon": f"{lon:.6f}" if lon is not None else "",
            "captured_at": taken,
            "location_source": "exif" if lat is not None else "none",
            "group": (credit.get("group") or args.group).strip(),
            "split": "",
            "added_at": rv.now_iso(),
        })
        known.add(image_id)
        added += 1

    rv.write_manifest(rows)
    print(f"Added {added} photos ({located} with GPS), skipped {dupes} duplicates. Manifest: {len(rows)} photos.")
    if missing_licence:
        print(f"NOT added, no licence given ({len(missing_licence)}): {', '.join(missing_licence[:10])}"
              f"{' ...' if len(missing_licence) > 10 else ''}")
        print("Pass --licence, or add them to the --credits CSV.")


if __name__ == "__main__":
    main()
