"""Event-level intrusion evaluation helpers (issue #3 part B).

Labels: clip, start_sec, end_sec, class, is_intrusion, notes
A predicted event matches a positive label when time intervals overlap
and the object class matches (or label class is '*').
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LabelRow:
    clip: str
    start_sec: float
    end_sec: float
    object_class: str
    is_intrusion: bool
    notes: str = ""


@dataclass(frozen=True)
class PredEvent:
    clip: str
    start_sec: float
    end_sec: float
    object_class: str
    dwell_time_sec: float = 0.0
    event_type: str = ""


def intervals_overlap(a0: float, a1: float, b0: float, b1: float) -> bool:
    return a0 < b1 and b0 < a1


def class_matches(pred_class: str, label_class: str) -> bool:
    if label_class in {"*", "", "any"}:
        return True
    return pred_class.lower() == label_class.lower()


def load_labels(path: Path | str) -> list[LabelRow]:
    rows: list[LabelRow] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            if not raw.get("clip"):
                continue
            flag = str(raw.get("is_intrusion", "1")).strip().lower()
            is_intrusion = flag in {"1", "true", "yes", "y"}
            rows.append(
                LabelRow(
                    clip=raw["clip"].strip(),
                    start_sec=float(raw["start_sec"]),
                    end_sec=float(raw["end_sec"]),
                    object_class=(raw.get("class") or "*").strip(),
                    is_intrusion=is_intrusion,
                    notes=(raw.get("notes") or "").strip(),
                )
            )
    return rows


def _clip_key(name: str) -> str:
    """Normalize clip ids so 'foo.mp4' and 'foo' match."""
    path = Path(name)
    return path.stem if path.suffix else name


def match_events(
    labels: list[LabelRow],
    preds: list[PredEvent],
) -> dict:
    """Greedy one-to-one matching of positive labels to predictions per clip."""
    positives = [lab for lab in labels if lab.is_intrusion]
    negatives = [lab for lab in labels if not lab.is_intrusion]

    tp = 0
    matched_pred_ids: set[int] = set()
    confirmation_delays: list[float] = []

    # group by clip
    labels_by_clip: dict[str, list[LabelRow]] = {}
    for lab in positives:
        labels_by_clip.setdefault(_clip_key(lab.clip), []).append(lab)
    preds_by_clip: dict[str, list[tuple[int, PredEvent]]] = {}
    for idx, pred in enumerate(preds):
        preds_by_clip.setdefault(_clip_key(pred.clip), []).append((idx, pred))

    for clip, clip_labels in labels_by_clip.items():
        available = list(preds_by_clip.get(clip, []))
        for lab in clip_labels:
            best = None
            best_i = None
            for i, (pid, pred) in enumerate(available):
                if pid in matched_pred_ids:
                    continue
                if not class_matches(pred.object_class, lab.object_class):
                    continue
                if not intervals_overlap(pred.start_sec, pred.end_sec, lab.start_sec, lab.end_sec):
                    continue
                # prefer earliest prediction that overlaps
                if best is None or pred.start_sec < best.start_sec:
                    best = pred
                    best_i = i
            if best is not None:
                tp += 1
                pid = available[best_i][0]
                matched_pred_ids.add(pid)
                # confirmation delay ≈ how long after label start the event starts
                confirmation_delays.append(max(0.0, best.start_sec - lab.start_sec))
                available.pop(best_i)

    fp = sum(1 for i, _ in enumerate(preds) if i not in matched_pred_ids)
    fn = len(positives) - tp

    # Negative labels that still got an overlapping prediction of matching class
    # count toward false alerts (already in fp via unmatched preds; also track rate).
    video_hours = _estimate_hours(labels, preds)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    mean_delay = (
        sum(confirmation_delays) / len(confirmation_delays) if confirmation_delays else None
    )
    false_per_hour = (fp / video_hours) if video_hours > 0 else None

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "n_positive_labels": len(positives),
        "n_negative_labels": len(negatives),
        "n_predictions": len(preds),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "false_alerts_per_hour": None if false_per_hour is None else round(false_per_hour, 4),
        "mean_confirmation_delay_sec": None if mean_delay is None else round(mean_delay, 4),
        "video_hours_est": None if video_hours is None else round(video_hours, 4),
    }


def _estimate_hours(labels: list[LabelRow], preds: list[PredEvent]) -> float:
    """Rough duration estimate: max end_sec per clip, summed."""
    ends: dict[str, float] = {}
    for lab in labels:
        ends[lab.clip] = max(ends.get(lab.clip, 0.0), lab.end_sec)
    for pred in preds:
        ends[pred.clip] = max(ends.get(pred.clip, 0.0), pred.end_sec)
    total_sec = sum(ends.values())
    return total_sec / 3600.0 if total_sec > 0 else 0.0
