"""Import TACO (Trash Annotations in Context) as extra `debris_waste` examples.

    python training/import_taco.py --limit 400

TACO (tacodataset.org, Proenca & Simoes 2020) has ~1500 photos of litter
with every item outlined by people. Our baseline never detects garbage, so
these outlines teach the model what waste looks like without anyone in the
team drawing them.

Rules:
  - every TACO outline becomes `debris_waste`; tiny items (< 0.3 % of the
    photo, e.g. cigarette butts) are dropped, since trackside waste is heaps;
  - only photos where litter covers at least 1 % are used, largest first;
  - photos are `role=train_only`: TACO is not Indian, so it never enters
    val/test and every reported number stays India-only;
  - a photo whose downloaded size does not match its annotation frame
    (rotated by EXIF) is skipped rather than given misplaced outlines.
"""

import argparse
import json
import tempfile
import time
from pathlib import Path

import requests
import rvdata as rv

ANNOTATIONS_URL = "https://raw.githubusercontent.com/pedropro/TACO/master/data/annotations.json"
MIN_ITEM_SHARE = 0.003
MIN_IMAGE_SHARE = 0.01
DEBRIS = rv.CLASSES.index("debris_waste")


def taco_labels(annotations: dict) -> dict[int, dict]:
    """image id -> {"image": image record, "labels": [(class, [(x, y) normalised])], "share": litter area share}."""
    images = {im["id"]: im for im in annotations["images"]}
    out: dict[int, dict] = {}
    for ann in annotations["annotations"]:
        im = images[ann["image_id"]]
        w, h = im["width"], im["height"]
        if not ann.get("segmentation") or ann["area"] / (w * h) < MIN_ITEM_SHARE:
            continue
        entry = out.setdefault(im["id"], {"image": im, "labels": [], "share": 0.0})
        entry["share"] += ann["area"] / (w * h)
        for poly in ann["segmentation"]:
            if isinstance(poly, list) and len(poly) >= 6:
                entry["labels"].append((DEBRIS, [(x / w, y / h) for x, y in zip(poly[0::2], poly[1::2], strict=True)]))
    return {k: v for k, v in out.items() if v["labels"] and v["share"] >= MIN_IMAGE_SHARE}


def same_frame(width, height, ann_w, ann_h, tolerance=0.02) -> bool:
    """True if a downloaded image has the annotation frame's aspect ratio (not rotated)."""
    return abs(width / height - ann_w / ann_h) <= tolerance * (ann_w / ann_h)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--limit", type=int, default=400)
    args = p.parse_args()

    from PIL import Image

    cache = rv.DATASETS / "external" / "taco" / "annotations.json"
    if not cache.is_file():
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(requests.get(ANNOTATIONS_URL, timeout=120).content)
    candidates = sorted(taco_labels(json.loads(cache.read_text(encoding="utf-8"))).values(),
                        key=lambda e: -e["share"])

    rows = rv.read_manifest()
    known = {r["image_id"] for r in rows}
    done = {r["original_name"] for r in rows if r["source"] == "taco"}
    tmp = Path(tempfile.mkdtemp(prefix="rv_taco_"))
    added = skipped = 0
    for entry in candidates:
        if added >= args.limit:
            break
        im = entry["image"]
        name = f"taco_{im['file_name'].replace('/', '_')}"
        if name in done:
            continue
        url = im.get("flickr_640_url") or im.get("flickr_url")
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
        except requests.RequestException:
            skipped += 1
            continue
        path = tmp / name
        path.write_bytes(resp.content)
        with Image.open(path) as img:
            if not same_frame(img.width, img.height, im["width"], im["height"]):
                skipped += 1
                continue
        image_id = rv.register_image(path, {
            "source": "taco",
            "source_url": "http://tacodataset.org",
            "licence": "CC BY 4.0 (TACO dataset)",
            "author": "TACO dataset (Proenca & Simoes, 2020)",
            "role": rv.TRAIN_ONLY,
            "original_name": name,
        }, rows, known)
        if image_id:
            rv.write_labels(rv.LABELS / f"{image_id}.txt", entry["labels"])
            added += 1
            if added % 50 == 0:
                rv.write_manifest(rows)
                print(f"  {added} TACO photos imported")
        time.sleep(0.05)

    rv.write_manifest(rows)
    print(f"Imported {added} TACO photos as train-only debris_waste examples; skipped {skipped} "
          f"(unavailable or rotated). Manifest: {len(rows)} photos.")


if __name__ == "__main__":
    main()
