"""
Run the full CV pipeline on one video file from the command line and
print the incidents it produces -- no server, no database, no browser.
Handy for checking a change to the temporal/risk logic on real footage.

    python scripts/run_clip.py path/to/clip.mp4
    python scripts/run_clip.py path/to/clip.mp4 --zone "[[420,720],[990,720],[650,230],[590,230]]"
    python scripts/run_clip.py path/to/clip.mp4 --out outputs/_manual

Zone points are in PIXELS of the video frame, same as the API expects.
If --zone is omitted a preset is used when the file name matches one
below, otherwise the whole frame becomes the zone.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `app` importable

from app.core import config  # noqa: E402
from app.cv.video_processor import process_video  # noqa: E402

# Rough zones for the practice clips in Desktop/railvigil-clips, drawn
# from sampled frames. 1280x720 pixel coordinates.
ZONE_PRESETS = {
    # track runs from the bottom of the frame up to a vanishing point
    "person_walking_tracks_1": [[420, 720], [990, 720], [650, 230], [590, 230]],
    # low-angle shot, people walk along the rails in the lower band
    "couple_walking_tracks": [[0, 720], [1280, 720], [1280, 480], [0, 480]],
    # fixed camera, track across the lower half; a train passes mid-clip
    "train_tracks_empty": [[0, 720], [1280, 720], [1280, 330], [0, 330]],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", help="path to an .mp4 file")
    parser.add_argument("--zone", help="JSON list of [x, y] pixel points (>= 3)")
    parser.add_argument("--out", default=str(Path(config.OUTPUTS_DIR) / "_manual"),
                        help="folder for annotated.mp4 and snapshots/")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    video_path = Path(args.video)
    if not video_path.exists():
        sys.exit(f"no such file: {video_path}")

    if args.zone:
        zone = json.loads(args.zone)
    elif video_path.stem in ZONE_PRESETS:
        zone = ZONE_PRESETS[video_path.stem]
        print(f"using zone preset for '{video_path.stem}': {zone}")
    else:
        import cv2
        cap = cv2.VideoCapture(str(video_path))
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        zone = [[0, 0], [w, 0], [w, h], [0, h]]
        print(f"no preset for '{video_path.stem}', using the whole {w}x{h} frame as the zone")

    video_id = video_path.stem
    out_dir = Path(args.out) / video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    output_video = out_dir / "annotated.mp4"

    # Snapshots are written under OUTPUTS_DIR/<video_id>/snapshots by the
    # pipeline; point OUTPUTS_DIR at --out so everything lands together.
    config.OUTPUTS_DIR = Path(args.out)

    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  {done}/{total} frames ({pct:.0f}%)", end="", flush=True)

    incidents = process_video(
        video_path=str(video_path), zone_points=zone, video_id=video_id,
        output_video_path=str(output_video), progress_cb=progress,
    )
    print()

    if not incidents:
        print("no incidents")
    else:
        cols = ["track_id", "object_class", "severity", "risk_score", "start_ts", "end_ts",
                "dwell_time_sec", "max_penetration", "event_type"]
        print("  ".join(f"{c:>14}" for c in cols))
        for inc in incidents:
            print("  ".join(f"{str(inc[c]):>14}" for c in cols))
        print(f"\n{len(incidents)} incident(s)")

    print(f"annotated video: {output_video}")
    print(f"snapshots:       {out_dir / 'snapshots'}")


if __name__ == "__main__":
    main()
