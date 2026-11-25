"""Event-level intrusion evaluation helpers (issue #3 part B).

Labels: clip, start_sec, end_sec, class, is_intrusion, notes
A predicted event matches a positive label when time intervals overlap
and the object class matches (or label class is '*').

is_intrusion = ``ignore`` marks a don't-care time range (a replay, another
camera angle the zone does not fit, a title card): alerts starting inside it
are dropped, and its length is not counted as video time.
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
    ignore: bool = False


@dataclass(frozen=True)
class PredEvent:
    clip: str
    start_sec: float
    end_sec: float
    object_class: str
    dwell_time_sec: float = 0.0
    event_type: str = ""
    alert_sec: float | None = None   # when the alert fired; None = unknown, use start_sec


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
            ignore = flag == "ignore"
            rows.append(
                LabelRow(
                    clip=raw["clip"].strip(),
                    start_sec=float(raw["start_sec"]),
                    end_sec=float(raw["end_sec"]),
                    object_class=(raw.get("class") or "*").strip(),
                    is_intrusion=is_intrusion,
                    notes=(raw.get("notes") or "").strip(),
                    ignore=ignore,
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
    processed_clips: set[str] | None = None,
) -> dict:
    """Greedy one-to-one matching of positive labels to predictions per clip.

    processed_clips: the clips the pipeline really ran on. When given, labels and
    predictions of other clips (no zone, unreadable video) are left out of every
    count, including the video hours, and listed under ``skipped_clips``.

    Unmatched predictions are split into ``fp_duplicate`` (it overlaps a labelled
    intrusion of the same class that was already matched: typically the tracker
    lost the object and alerted again) and ``fp_other`` (nothing labelled there).
    Both still count in ``fp`` and in precision.
    """
    skipped: list[str] = []
    if processed_clips is not None:
        keep = {_clip_key(c) for c in processed_clips}
        skipped = sorted({_clip_key(lab.clip) for lab in labels} - keep)
        labels = [lab for lab in labels if _clip_key(lab.clip) in keep]
        preds = [p for p in preds if _clip_key(p.clip) in keep]

    ignored_ranges: dict[str, list[tuple[float, float]]] = {}
    for lab in labels:
        if lab.ignore:
            ignored_ranges.setdefault(_clip_key(lab.clip), []).append((lab.start_sec, lab.end_sec))

    def in_ignored(pred: PredEvent) -> bool:
        return any(a <= pred.start_sec < b for a, b in ignored_ranges.get(_clip_key(pred.clip), []))

    n_ignored_preds = sum(1 for p in preds if in_ignored(p))
    preds = [p for p in preds if not in_ignored(p)]

    positives = [lab for lab in labels if lab.is_intrusion and not lab.ignore]
    negatives = [lab for lab in labels if not lab.is_intrusion and not lab.ignore]

    tp = 0
    matched_pred_ids: set[int] = set()
    confirmation_delays: list[float] = []
    first_seen_delays: list[float] = []

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
                # time to alert: from the moment the intrusion starts to the moment the alert fires
                fired = best.alert_sec if best.alert_sec is not None else best.start_sec
                confirmation_delays.append(max(0.0, fired - lab.start_sec))
                first_seen_delays.append(max(0.0, best.start_sec - lab.start_sec))
                available.pop(best_i)

    unmatched = [p for i, p in enumerate(preds) if i not in matched_pred_ids]
    fp = len(unmatched)
    fn = len(positives) - tp

    def on_real_intrusion(pred: PredEvent) -> bool:
        return any(
            class_matches(pred.object_class, lab.object_class)
            and intervals_overlap(pred.start_sec, pred.end_sec, lab.start_sec, lab.end_sec)
            for lab in labels_by_clip.get(_clip_key(pred.clip), [])
        )

    duplicates = [p for p in unmatched if on_real_intrusion(p)]

    per_clip: dict[str, dict] = {}
    for lab in labels:
        if lab.ignore:
            continue
        per_clip.setdefault(_clip_key(lab.clip), {"positives": 0, "tp": 0, "fn": 0, "fp": 0, "fp_duplicate": 0})
    for pred in preds:
        per_clip.setdefault(_clip_key(pred.clip), {"positives": 0, "tp": 0, "fn": 0, "fp": 0, "fp_duplicate": 0})
    for clip, clip_labels in labels_by_clip.items():
        per_clip[clip]["positives"] = len(clip_labels)
    for i, pred in enumerate(preds):
        if i in matched_pred_ids:
            per_clip[_clip_key(pred.clip)]["tp"] += 1
    for pred in unmatched:
        per_clip[_clip_key(pred.clip)]["fp"] += 1
    for pred in duplicates:
        per_clip[_clip_key(pred.clip)]["fp_duplicate"] += 1
    for row in per_clip.values():
        row["fn"] = row["positives"] - row["tp"]

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
        "fp_duplicate": len(duplicates),
        "fp_other": fp - len(duplicates),
        "n_positive_labels": len(positives),
        "n_negative_labels": len(negatives),
        "n_predictions": len(preds),
        "n_ignored_predictions": n_ignored_preds,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "false_alerts_per_hour": None if false_per_hour is None else round(false_per_hour, 4),
        "mean_confirmation_delay_sec": None if mean_delay is None else round(mean_delay, 4),
        "mean_first_seen_delay_sec": (
            round(sum(first_seen_delays) / len(first_seen_delays), 4) if first_seen_delays else None
        ),
        "alert_time_known": all(p.alert_sec is not None for p in preds) if preds else None,
        "video_hours_est": None if video_hours is None else round(video_hours, 4),
        "n_clips": len(per_clip),
        "skipped_clips": skipped,
        "per_clip": dict(sorted(per_clip.items())),
    }


def _merged_length(ranges: list[tuple[float, float]], limit: float) -> float:
    """Length of the union of time ranges, clipped to [0, limit]."""
    total, cur_a, cur_b = 0.0, None, None
    for a, b in sorted((max(0.0, a), min(limit, b)) for a, b in ranges):
        if b <= a:
            continue
        if cur_b is None or a > cur_b:
            total += 0.0 if cur_b is None else cur_b - cur_a
            cur_a, cur_b = a, b
        else:
            cur_b = max(cur_b, b)
    return total + (0.0 if cur_b is None else cur_b - cur_a)


def _estimate_hours(labels: list[LabelRow], preds: list[PredEvent]) -> float:
    """Duration estimate: max end_sec per clip, minus its don't-care ranges, summed.

    'foo.mp4' and 'foo' are one clip.
    """
    ends: dict[str, float] = {}
    for clip, end in [(lab.clip, lab.end_sec) for lab in labels] + [(p.clip, p.end_sec) for p in preds]:
        key = _clip_key(clip)
        ends[key] = max(ends.get(key, 0.0), end)
    ignored: dict[str, list[tuple[float, float]]] = {}
    for lab in labels:
        if lab.ignore:
            ignored.setdefault(_clip_key(lab.clip), []).append((lab.start_sec, lab.end_sec))
    total_sec = sum(end - _merged_length(ignored.get(clip, []), end) for clip, end in ends.items())
    return total_sec / 3600.0 if total_sec > 0 else 0.0
