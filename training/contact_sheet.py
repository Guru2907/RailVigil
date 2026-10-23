"""Make numbered contact sheets for a quick look at many photos at once.

    python training/contact_sheet.py --source mapillary
    python training/contact_sheet.py --source wikimedia --per-sheet 12

Writes datasets/review/<source>_NN.jpg: grids of thumbnails, each labelled
with its image id, so irrelevant photos (no track visible, not India, blurry)
can be dropped with remove_images.py.
"""

import argparse

import cv2
import numpy as np
import rvdata as rv

TILE_W, TILE_H = 480, 320


def tile(path, label):
    img = cv2.imread(str(path))
    canvas = np.zeros((TILE_H, TILE_W, 3), np.uint8)
    if img is not None:
        h, w = img.shape[:2]
        scale = min(TILE_W / w, (TILE_H - 28) / h)
        small = cv2.resize(img, (int(w * scale), int(h * scale)))
        y0, x0 = 28 + (TILE_H - 28 - small.shape[0]) // 2, (TILE_W - small.shape[1]) // 2
        canvas[y0:y0 + small.shape[0], x0:x0 + small.shape[1]] = small
    cv2.putText(canvas, label, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 255, 160), 2)
    return canvas


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", required=True)
    p.add_argument("--per-sheet", type=int, default=12)
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--unlabelled", action="store_true", help="only photos without labels yet (new photos)")
    args = p.parse_args()

    rows = [r for r in rv.read_manifest() if r["source"] == args.source
            and not (args.unlabelled and (rv.LABELS / f"{r['image_id']}.txt").exists())]
    out = rv.DATASETS / "review"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob(f"{args.source}_*.jpg"):
        old.unlink()
    for n, i in enumerate(range(0, len(rows), args.per_sheet), start=1):
        batch = rows[i:i + args.per_sheet]
        tiles = [tile(rv.DATASETS / r["file"], r["image_id"]) for r in batch]
        tiles += [np.zeros((TILE_H, TILE_W, 3), np.uint8)] * (-len(tiles) % args.cols)
        grid = np.vstack([np.hstack(tiles[j:j + args.cols]) for j in range(0, len(tiles), args.cols)])
        cv2.imwrite(str(out / f"{args.source}_{n:02d}.jpg"), grid, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(f"{len(rows)} photos -> {out} ({args.source}_*.jpg)")


if __name__ == "__main__":
    main()
