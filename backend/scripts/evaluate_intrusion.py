"""
Evaluate intrusion predictions against datasets/intrusion/labels.csv.

Examples (from backend/):

  # Match precomputed prediction JSON against labels
  python scripts/evaluate_intrusion.py --preds path/to/preds.json

  # Run the live pipeline on every labelled clip under --clips-dir
  python scripts/evaluate_intrusion.py --clips-dir D:/railvigil-clips --run-pipeline

  # Sweep CONFIRM_DWELL_SEC (pipeline mode only)
  python scripts/evaluate_intrusion.py --clips-dir D:/clips --run-pipeline \\
      --sweep confirm_dwell 0.3,0.6,1.0,2.0,3.0

Prediction JSON schema: list of
  {clip, start_sec, end_sec, class|object_class, dwell_time_sec?, event_type?}
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import config  # noqa: E402
from app.cv.intrusion.evaluation import PredEvent, load_labels, match_events  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LABELS = REPO_ROOT / "datasets" / "intrusion" / "labels.csv"


def _load_preds(path: Path) -> list[PredEvent]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("--preds must be a JSON list")
    out: list[PredEvent] = []
    for row in data:
        out.append(
            PredEvent(
                clip=str(row["clip"]),
                start_sec=float(row["start_sec"]),
                end_sec=float(row["end_sec"]),
                object_class=str(row.get("object_class") or row.get("class") or "person"),
                dwell_time_sec=float(row.get("dwell_time_sec") or 0.0),
                event_type=str(row.get("event_type") or ""),
            )
        )
    return out


def _find_video(clips_dir: Path, clip: str) -> Path | None:
    direct = clips_dir / clip
    if direct.is_file():
        return direct
    stem = Path(clip).stem
    for ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
        candidate = clips_dir / f"{stem}{ext}"
        if candidate.is_file():
            return candidate
    return None


def _run_pipeline(clips_dir: Path, clip_names: list[str], out_root: Path) -> list[PredEvent]:
    from app.cv.intrusion.video_processor import process_video

    preds: list[PredEvent] = []
    config.OUTPUTS_DIR = out_root
    for clip in clip_names:
        video = _find_video(clips_dir, clip)
        if video is None:
            logging.warning("skip missing clip: %s", clip)
            continue
        out_video = out_root / video.stem / "annotated.mp4"
        out_video.parent.mkdir(parents=True, exist_ok=True)
        try:
            incidents = process_video(
                video_path=str(video),
                zone_points=None,
                video_id=video.stem,
                output_video_path=str(out_video),
            )
        except Exception as exc:  # noqa: BLE001
            logging.error("pipeline failed for %s: %s", clip, exc)
            continue
        for inc in incidents:
            preds.append(
                PredEvent(
                    clip=video.stem,
                    start_sec=float(inc["start_ts"]),
                    end_sec=float(inc["end_ts"]),
                    object_class=str(inc["object_class"]),
                    dwell_time_sec=float(inc["dwell_time_sec"]),
                    event_type=str(inc["event_type"]),
                )
            )
    return preds


def _print_metrics(title: str, metrics: dict) -> None:
    print(f"\n=== {title} ===")
    for key in (
        "tp", "fp", "fn", "precision", "recall",
        "false_alerts_per_hour", "mean_confirmation_delay_sec",
        "n_positive_labels", "n_predictions", "video_hours_est",
    ):
        print(f"  {key}: {metrics.get(key)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--preds", type=Path, help="JSON predictions (skip live pipeline)")
    parser.add_argument("--clips-dir", type=Path, help="directory of labelled clips + .zone.json")
    parser.add_argument("--run-pipeline", action="store_true", help="run process_video on labelled clips")
    parser.add_argument("--out", type=Path, default=Path(config.OUTPUTS_DIR) / "_eval")
    parser.add_argument(
        "--sweep",
        nargs=2,
        metavar=("PARAM", "VALUES"),
        help="sweep config float, e.g. confirm_dwell 0.3,0.6,1.0,3.0",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not args.labels.is_file():
        raise SystemExit(f"labels not found: {args.labels}")
    labels = load_labels(args.labels)
    clip_names = sorted({lab.clip for lab in labels})

    if args.sweep and not args.run_pipeline:
        raise SystemExit("--sweep requires --run-pipeline")

    if args.preds:
        preds = _load_preds(args.preds)
        # normalize clip stems so labels without extension still match
        normalized = []
        for p in preds:
            normalized.append(p)
            stem = Path(p.clip).stem
            if stem != p.clip:
                normalized.append(
                    PredEvent(stem, p.start_sec, p.end_sec, p.object_class, p.dwell_time_sec, p.event_type)
                )
        metrics = match_events(labels, normalized)
        _print_metrics("baseline", metrics)
        print(json.dumps(metrics, indent=2))
        return

    if not args.run_pipeline:
        raise SystemExit("pass --preds JSON or --run-pipeline --clips-dir")

    if not args.clips_dir or not args.clips_dir.is_dir():
        raise SystemExit("--clips-dir must be an existing directory")

    param_map = {
        "confirm_dwell": "CONFIRM_DWELL_SEC",
        "miss_grace": "MISS_GRACE_SEC",
        "frame_sample": "FRAME_SAMPLE_INTERVAL",
        "persistent_dwell": "PERSISTENT_DWELL_THRESHOLD_SEC",
    }

    if args.sweep:
        key, values_csv = args.sweep
        attr = param_map.get(key)
        if not attr:
            raise SystemExit(f"unknown sweep param {key}; choose from {list(param_map)}")
        results = []
        for raw in values_csv.split(","):
            value = float(raw.strip())
            if attr == "FRAME_SAMPLE_INTERVAL":
                value = int(value)
            setattr(config, attr, value)
            preds = _run_pipeline(args.clips_dir, clip_names, args.out / f"sweep_{key}_{value}")
            metrics = match_events(labels, preds)
            metrics["param"] = key
            metrics["value"] = value
            results.append(metrics)
            _print_metrics(f"{key}={value}", metrics)
        print(json.dumps(results, indent=2))
        return

    preds = _run_pipeline(args.clips_dir, clip_names, args.out)
    metrics = match_events(labels, preds)
    _print_metrics("baseline", metrics)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
