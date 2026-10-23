"""Shared helpers for the RailVigil dataset and training tools.

Pure functions (no models, no GPU) so they are unit-tested in CI
(backend/tests/training). Class names come from the backend's taxonomy, so
the dataset, the trained model and the pipeline can never disagree on them.

Dataset layout (everything under datasets/ is git-ignored except the manifest):

    datasets/incoming/<batch>/      photos you drop in, any file names
    datasets/images/<id>.<ext>      managed copies, id = first 12 hex of SHA-256
    datasets/manifest.csv           one row per image: source, licence, GPS, split
    datasets/upload/<name>/         pre-labelled batch to upload to Roboflow / CVAT
    datasets/labels/<id>.txt        corrected labels imported back (YOLO segmentation)
    datasets/build/railvigil-seg/   train/val/test folders + data.yaml (generated)
"""

import csv
import hashlib
import math
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "backend"
# Overridable so a throwaway smoke test never touches the real dataset or runs.
DATASETS = Path(os.getenv("RAILVIGIL_DATASETS", REPO / "datasets"))
IMAGES = DATASETS / "images"
LABELS = DATASETS / "labels"
MANIFEST = DATASETS / "manifest.csv"
BUILD = DATASETS / "build" / "railvigil-seg"
RUNS = Path(os.getenv("RAILVIGIL_RUNS", REPO / "training" / "runs"))
WEIGHTS = REPO / "training" / "weights"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
from app.cv.encroachment.taxonomy import CLASSES  # noqa: E402  (pure constants, no app setup)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
# Written by prelabel.py into its output. Uncorrected pre-labels must never become
# ground truth: evaluating the baseline against its own guesses would be circular.
PRELABEL_MARKER = "RAILVIGIL_PRELABELS_NOT_GROUND_TRUTH.txt"
SPLITS = ("train", "val", "test")
DEFAULT_RATIOS = (0.70, 0.15, 0.15)
# Photos closer than this are treated as the same place and always share a split.
SAME_PLACE_M = 300.0

MANIFEST_FIELDS = [
    "image_id", "file", "original_name", "source", "source_url", "licence", "author",
    "lat", "lon", "captured_at", "location_source", "group", "split", "added_at",
]


# --- manifest ----------------------------------------------------------------

def read_manifest(path: Path = MANIFEST) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [{k: (row.get(k) or "") for k in MANIFEST_FIELDS} for row in csv.DictReader(f)]


def write_manifest(rows: list[dict], path: Path = MANIFEST) -> None:
    """Atomic write, so an interrupted run never leaves a half-written manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (r["added_at"], r["image_id"])):
            writer.writerow({k: row.get(k, "") for k in MANIFEST_FIELDS})
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_id_for(path: Path) -> str:
    return sha256_file(path)[:12]


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# --- EXIF --------------------------------------------------------------------

def _to_degrees(value, ref) -> float | None:
    try:
        d, m, s = (float(v) for v in value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    deg = d + m / 60 + s / 3600
    return -deg if ref in ("S", "W") else deg


def exif_info(path: Path) -> tuple[float | None, float | None, str]:
    """(lat, lon, captured_at) from a photo's EXIF; None / "" when absent."""
    from PIL import Image

    try:
        with Image.open(path) as img:
            exif = img.getexif()
            gps = exif.get_ifd(0x8825)
            sub = exif.get_ifd(0x8769)
    except Exception:  # noqa: BLE001  (unreadable EXIF is just "no EXIF")
        return None, None, ""
    lat = _to_degrees(gps.get(2), gps.get(1)) if gps else None
    lon = _to_degrees(gps.get(4), gps.get(3)) if gps else None
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        lat = lon = None
    taken = str(sub.get(0x9003) or exif.get(0x0132) or "")
    return lat, lon, taken


# --- location-aware splits ---------------------------------------------------

def distance_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def place_groups(rows: list[dict], same_place_m: float = SAME_PLACE_M) -> dict[str, str]:
    """image_id -> group key. Photos in one group always land in the same split:
    - a manual `group` value wins (e.g. several photos of one named site);
    - located photos within `same_place_m` of each other are chained together;
    - photos with neither are their own group."""
    parent = {r["image_id"]: r["image_id"] for r in rows}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    by_manual: dict[str, str] = {}
    for r in rows:
        if r["group"]:
            first = by_manual.setdefault(r["group"], r["image_id"])
            union(first, r["image_id"])

    located = [(r["image_id"], float(r["lat"]), float(r["lon"])) for r in rows if r["lat"] and r["lon"]]
    for i, (a, lat1, lon1) in enumerate(located):
        for b, lat2, lon2 in located[i + 1:]:
            if distance_m(lat1, lon1, lat2, lon2) <= same_place_m:
                union(a, b)
    return {r["image_id"]: find(r["image_id"]) for r in rows}


def _bucket(key: str, ratios=DEFAULT_RATIOS) -> str:
    x = int(hashlib.sha256(f"railvigil:{key}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    edge = 0.0
    for split, share in zip(SPLITS, ratios, strict=True):
        edge += share
        if x < edge:
            return split
    return SPLITS[-1]


def assign_splits(rows: list[dict], ratios=DEFAULT_RATIOS, same_place_m: float = SAME_PLACE_M) -> list[dict]:
    """Fill in `split` for rows that have none. Existing splits never change
    (the test set stays frozen), and a new photo of an already-split place
    joins that place's split so no place leaks between train and test."""
    groups = place_groups(rows, same_place_m)
    group_split: dict[str, str] = {}
    for r in rows:
        if r["split"]:
            group_split.setdefault(groups[r["image_id"]], r["split"])
    for r in rows:
        if not r["split"]:
            g = groups[r["image_id"]]
            r["split"] = group_split.setdefault(g, _bucket(g, ratios))
    return rows


def split_leaks(rows: list[dict], same_place_m: float = SAME_PLACE_M) -> list[str]:
    """Group keys whose photos ended up in more than one split (should be empty)."""
    groups = place_groups(rows, same_place_m)
    seen: dict[str, set] = {}
    for r in rows:
        if r["split"]:
            seen.setdefault(groups[r["image_id"]], set()).add(r["split"])
    return sorted(g for g, s in seen.items() if len(s) > 1)


# --- YOLO segmentation labels ------------------------------------------------

def read_labels(path: Path) -> list[tuple[int, list[tuple[float, float]]]]:
    """[(class index, [(x, y), ...] normalised 0-1)] from a YOLO-seg .txt file.
    A 4-number line (a plain box) is turned into its rectangle."""
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        cls, nums = int(float(parts[0])), [float(v) for v in parts[1:]]
        if len(nums) == 4:  # cx cy w h
            cx, cy, w, h = nums
            x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
            pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        elif len(nums) >= 6 and len(nums) % 2 == 0:
            pts = list(zip(nums[0::2], nums[1::2], strict=True))
        else:
            raise ValueError(f"{path}: malformed label line: {line!r}")
        out.append((cls, pts))
    return out


def write_labels(path: Path, labels) -> None:
    lines = [f"{cls} " + " ".join(f"{min(max(v, 0.0), 1.0):.6f}" for p in pts for v in p) for cls, pts in labels]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z]+", "_", name.lower()).strip("_")


CLASS_ALIASES = {
    "debris": "debris_waste", "waste": "debris_waste", "garbage": "debris_waste",
    "permanent_structure": "structure_permanent", "temporary_structure": "structure_temporary",
    "parked_vehicle": "vehicle_parked", "vehicle": "vehicle_parked", "material": "material_dump",
}


def class_remap(export_names: list[str]) -> dict[int, int]:
    """Export class index -> RailVigil class index, matched by name (labelling
    tools may reorder or rename classes). Unknown names are an error."""
    ours = {c: i for i, c in enumerate(CLASSES)}
    remap, unknown = {}, []
    for i, name in enumerate(export_names):
        key = _norm_name(name)
        key = CLASS_ALIASES.get(key, key)
        if key in ours:
            remap[i] = ours[key]
        else:
            unknown.append(name)
    if unknown:
        raise ValueError(f"Unknown class names in the export: {unknown}. Expected: {list(CLASSES)}")
    return remap


_ID = re.compile(r"^([0-9a-f]{12})")


def image_id_from_export_name(filename: str, known_ids: set[str]) -> str | None:
    """Roboflow renames 'ab12cd34ef56.jpg' to 'ab12cd34ef56_jpg.rf.<hash>.jpg';
    CVAT keeps the name. Either way the id is the first 12 hex characters."""
    m = _ID.match(Path(filename).name.lower())
    return m.group(1) if m and m.group(1) in known_ids else None


# --- box metrics (used to compare the pretrained baseline with the trained model) ---

def box_iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def polygon_box(pts, width: int, height: int):
    xs, ys = [p[0] * width for p in pts], [p[1] * height for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def average_precision(tp_by_conf: list[bool], n_gt: int) -> float:
    """All-point interpolated AP (as in COCO/VOC) from TP flags sorted by
    descending confidence."""
    if n_gt == 0:
        return float("nan")
    precisions, recalls, tp = [], [], 0
    for i, hit in enumerate(tp_by_conf, start=1):
        tp += hit
        precisions.append(tp / i)
        recalls.append(tp / n_gt)
    ap, prev_r = 0.0, 0.0
    for i, r in enumerate(recalls):
        if r > prev_r:
            ap += (r - prev_r) * max(precisions[i:])
            prev_r = r
    return ap


def evaluate_boxes(preds: dict, gts: dict, iou_threshold: float = 0.5) -> dict:
    """preds: image -> [(cls, conf, box)]; gts: image -> [(cls, box)].
    Returns per-class {n_gt, n_pred, tp, precision, recall, ap50}; a prediction
    matches the best unmatched ground truth of its class with IoU >= threshold."""
    results = {}
    for cls in sorted({c for v in gts.values() for c, _ in v} | {c for v in preds.values() for c, _, _ in v}):
        scored = []
        n_gt = 0
        for image in set(preds) | set(gts):
            gt_boxes = [b for c, b in gts.get(image, []) if c == cls]
            n_gt += len(gt_boxes)
            used = [False] * len(gt_boxes)
            for _, conf, pbox in sorted((p for p in preds.get(image, []) if p[0] == cls), key=lambda p: -p[1]):
                best, best_iou = -1, iou_threshold
                for j, g in enumerate(gt_boxes):
                    v = box_iou(pbox, g)
                    if not used[j] and v >= best_iou:
                        best, best_iou = j, v
                if best >= 0:
                    used[best] = True
                scored.append((conf, best >= 0))
        scored.sort(key=lambda s: -s[0])
        flags = [hit for _, hit in scored]
        tp = sum(flags)
        results[cls] = {
            "n_gt": n_gt,
            "n_pred": len(flags),
            "tp": tp,
            "precision": tp / len(flags) if flags else 0.0,
            "recall": tp / n_gt if n_gt else float("nan"),
            "ap50": average_precision(flags, n_gt),
        }
    return results
