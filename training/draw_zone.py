"""Draw the track zone on a clip (or photo) and save it as <name>.zone.json beside it.

    python training/draw_zone.py datasets/intrusion/clips/pixabay_3178.mp4
    python training/draw_zone.py datasets/intrusion/clips --missing          # every clip without a zone yet
    python training/draw_zone.py datasets/intrusion/clips/pixabay_3178.mp4 --at 5   # frame at 5 s

A window shows one frame. Left-click around the area where a person, vehicle or
animal must not be (the track and its safety strip). Keys:
    Enter / s   save and go to the next clip      u   undo the last point
    y           redo a point you undid            b   back to the previous clip
    r           start again (y brings it back)    n   skip this clip
    q / Esc     quit
Leaving a clip with b, n, q or Esc while it has unsaved changes asks for the
same key a second time, so a zone is never thrown away by one stray key.
The zone is saved in normalised coordinates (0-1), the same sidecar format the
intrusion pipeline and evaluate_intrusion.py read, so it fits any resolution.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

VIDEO = {".mp4", ".webm", ".ogv", ".mov", ".avi", ".mkv"}
PHOTO = {".jpg", ".jpeg", ".png", ".webp"}
MAX_W, MAX_H = 1280, 760
LEAVE = {ord("b"): "back", ord("n"): "skipped", ord("q"): "quit", 27: "quit"}


def leave_or_warn(key: int, changed: bool, armed: int | None) -> tuple[str | None, int | None]:
    """For a leave key: (result, None) to leave now, or (None, key) to warn first.

    With unsaved changes the same key has to be pressed twice in a row.
    """
    if changed and armed != key:
        return None, key
    return LEAVE[key], None


def sidecar(path: Path) -> Path:
    return path.with_suffix(".zone.json")


def frame_of(path: Path, at_sec: float):
    if path.suffix.lower() in PHOTO:
        return cv2.imread(str(path))
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_MSEC, at_sec * 1000)
    ok, frame = cap.read()
    if not ok:                         # some files cannot seek: take the first frame
        cap.set(cv2.CAP_PROP_POS_MSEC, 0)
        ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def draw(path: Path, at_sec: float) -> str:
    """'saved', 'skipped', 'back' or 'quit'."""
    frame = frame_of(path, at_sec)
    if frame is None:
        print(f"  {path.name}: could not read a frame, skipped")
        return "skipped"
    h, w = frame.shape[:2]
    scale = min(MAX_W / w, MAX_H / h, 1.0)
    base = cv2.resize(frame, (int(w * scale), int(h * scale)))
    points: list[tuple[int, int]] = []
    existing = sidecar(path)
    if existing.is_file():
        old = json.loads(existing.read_text(encoding="utf-8"))["points"]
        points = [(int(x * base.shape[1]), int(y * base.shape[0])) for x, y in old]

    undone: list[tuple[int, int]] = []     # points taken off by undo/reset, newest last
    saved = list(points)                   # what is on disk, to spot unsaved changes
    armed: list[int | None] = [None]       # leave key pressed once with unsaved changes

    def on_click(event, x, y, *_):
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append((x, y))
            undone.clear()
            armed[0] = None

    title = f"{path.name}  |  Enter=save  u=undo  y=redo  r=reset  b=back  n=skip  q=quit"
    cv2.namedWindow(title)
    cv2.setMouseCallback(title, on_click)
    try:
        while True:
            view = base.copy()
            if len(points) >= 3:
                overlay = view.copy()
                cv2.fillPoly(overlay, [np.array(points, np.int32)], (0, 0, 255))
                view = cv2.addWeighted(overlay, 0.3, view, 0.7, 0)
            for i, p in enumerate(points):
                cv2.circle(view, p, 5, (0, 255, 255), -1)
                if i:
                    cv2.line(view, points[i - 1], p, (0, 255, 255), 2)
            if len(points) >= 3:
                cv2.line(view, points[-1], points[0], (0, 255, 255), 1)
            cv2.imshow(title, view)
            key = cv2.waitKey(30) & 0xFF
            if key == 0xFF:                    # no key pressed
                continue
            if key in LEAVE:
                result, armed[0] = leave_or_warn(key, points != saved, armed[0])
                if result:
                    return result
                name = "Esc" if key == 27 else chr(key)
                print(f"  unsaved changes: press {name} again to leave without saving, or Enter to save")
                continue
            armed[0] = None
            if key in (13, ord("s")):
                if len(points) < 3:
                    print("  need at least 3 points")
                    continue
                pts = [[round(x / base.shape[1], 4), round(y / base.shape[0], 4)] for x, y in points]
                existing.write_text(json.dumps({"format": "normalized", "points": pts}), encoding="utf-8")
                print(f"  saved {existing.name} ({len(pts)} points)")
                return "saved"
            if key == ord("u") and points:
                undone.append(points.pop())
            elif key == ord("y") and undone:
                points.append(undone.pop())
            elif key == ord("r"):
                undone.extend(reversed(points))
                points.clear()
    finally:
        cv2.destroyWindow(title)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("target", type=Path, help="a clip/photo, or a folder of them")
    p.add_argument("--missing", action="store_true", help="with a folder: only files without a .zone.json yet")
    p.add_argument("--at", type=float, default=1.0, help="seconds into the clip to show (default 1)")
    args = p.parse_args()
    if args.target.is_dir():
        files = sorted(f for f in args.target.iterdir() if f.suffix.lower() in VIDEO | PHOTO)
        if args.missing:
            files = [f for f in files if not sidecar(f).is_file()]
    else:
        files = [args.target]
    print(f"{len(files)} file(s) to draw")
    i = 0
    while 0 <= i < len(files):
        result = draw(files[i], args.at)
        if result == "quit":
            break
        i += -1 if result == "back" and i > 0 else (0 if result == "back" else 1)


if __name__ == "__main__":
    main()
