"""Frame sheets for video clips: one image per clip, frames stamped with their time.

    python training/clip_frames.py                       # every clip in datasets/intrusion/clips
    python training/clip_frames.py --every 2 pixabay_3171.mp4

Writes datasets/intrusion/frames/<clip>.jpg. Use it to check that a clip shows a
track, and to fill datasets/intrusion/labels.csv (start_sec / end_sec of each
intrusion) without scrubbing through the video: read the times off the sheet,
then confirm the exact moments in a player.
"""

import argparse
from pathlib import Path

import cv2
import numpy as np
import rvdata as rv

CLIPS = rv.DATASETS / "intrusion" / "clips"
OUT = rv.DATASETS / "intrusion" / "frames"
TILE_W, TILE_H, COLS = 400, 225, 4


def sheet(path: Path, every: float | None, max_tiles: int) -> np.ndarray | None:
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frames / fps if frames > 0 else 0
    if duration <= 0:
        return None
    step = every or max(duration / max_tiles, 0.5)
    tiles, t = [], 0.0
    while t < duration and len(tiles) < max_tiles:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        scale = min(TILE_W / w, TILE_H / h)
        small = cv2.resize(frame, (int(w * scale), int(h * scale)))
        tile = np.zeros((TILE_H, TILE_W, 3), np.uint8)
        tile[:small.shape[0], :small.shape[1]] = small
        cv2.rectangle(tile, (0, 0), (92, 26), (0, 0, 0), -1)
        cv2.putText(tile, f"{t:6.1f} s", (4, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 255, 160), 2)
        tiles.append(tile)
        t += step
    cap.release()
    if not tiles:
        return None
    tiles += [np.zeros((TILE_H, TILE_W, 3), np.uint8)] * (-len(tiles) % COLS)
    grid = np.vstack([np.hstack(tiles[i:i + COLS]) for i in range(0, len(tiles), COLS)])
    title = np.zeros((34, grid.shape[1], 3), np.uint8)
    cv2.putText(title, f"{path.name}  ({duration:.1f} s)", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return np.vstack([title, grid])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("clips", nargs="*", help="clip file names (default: all)")
    p.add_argument("--every", type=float, help="seconds between frames (default: spread 16 frames)")
    p.add_argument("--max-tiles", type=int, default=16)
    args = p.parse_args()
    paths = [CLIPS / c for c in args.clips] if args.clips else sorted(x for x in CLIPS.iterdir() if x.is_file())
    OUT.mkdir(parents=True, exist_ok=True)
    for path in paths:
        img = sheet(path, args.every, args.max_tiles)
        if img is None:
            print(f"  {path.name}: could not read")
            continue
        cv2.imwrite(str(OUT / f"{path.stem}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(f"{len(paths)} clips -> {OUT}")


if __name__ == "__main__":
    main()
