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
# Scripts import the taxonomy through this module (never `from app...` themselves),
# because the line above is what makes `app` importable.
from app.cv.encroachment.taxonomy import CLASSES, map_label  # noqa: E402, F401  (pure constants)

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
    "lat", "lon", "captured_at", "location_source", "group", "split", "added_at", "role",
]
# role "train_only": extra training data from outside India (e.g. TACO litter). It never
# enters val/test, so every reported number is measured on Indian photos only.
TRAIN_ONLY = "train_only"

# --- India check ---------------------------------------------------------------
# Coarse hand-traced outlines (lon, lat), accurate to roughly 10-30 km: enough to
# tell an Indian railway photo from one in Bangladesh, Nepal, Pakistan or Sri Lanka
# (a bounding box would wrongly include Bangladesh and Nepal).
INDIA_OUTLINE = [
    (68.2, 23.6), (68.9, 22.4), (69.9, 21.0), (71.0, 20.6), (72.6, 20.5), (72.7, 19.0), (72.95, 17.5),
    (73.4, 16.0), (74.0, 14.9), (74.6, 13.0), (75.5, 11.5), (76.2, 10.0), (76.6, 8.8), (77.5, 8.0),
    (78.2, 8.9), (79.3, 9.3), (79.9, 10.3), (79.9, 11.8), (80.45, 13.5), (80.3, 15.5), (81.3, 16.4),
    (82.3, 16.6), (83.4, 17.8), (85.0, 19.3), (86.4, 20.0), (87.0, 21.3), (88.2, 21.6), (89.0, 21.5),
    (92.3, 20.6), (92.7, 22.0), (93.2, 22.2), (93.4, 23.0), (94.2, 23.9), (94.6, 25.0), (95.2, 26.0),
    (95.9, 27.0), (97.2, 27.1), (97.4, 28.2), (96.6, 28.8), (95.4, 29.2), (94.2, 29.2), (93.0, 28.6),
    (92.0, 27.9), (91.6, 27.8), (92.0, 26.9), (90.0, 26.75), (89.0, 26.85), (88.9, 27.3), (88.8, 28.1),
    (88.1, 27.9), (81.0, 30.3), (79.0, 31.4), (78.7, 32.2), (79.4, 32.7), (79.4, 34.0), (78.3, 35.5),
    (77.0, 35.7), (75.5, 36.0), (74.3, 35.4), (73.6, 34.5), (73.8, 33.6), (74.3, 33.0), (74.7, 32.5),
    (74.6, 31.6), (74.55, 31.0), (73.9, 30.3), (73.4, 29.9), (72.5, 28.9), (71.9, 28.0), (70.6, 27.8),
    (69.6, 27.2), (70.1, 25.9), (70.7, 25.6), (71.1, 24.4), (70.0, 24.2), (68.8, 24.3),
]
# Countries inside or next to the outline above, cut out of it.
EXCLUDED_OUTLINES = {
    "Bangladesh": [
        (88.95, 21.55), (88.88, 22.9), (88.75, 23.6), (88.45, 24.25), (88.05, 24.75), (88.4, 25.3), (88.1, 25.9),
        (88.35, 26.45), (88.95, 26.25), (89.85, 25.95), (89.85, 25.3), (90.6, 25.15), (92.05, 25.15), (92.2, 24.95),
        (91.95, 24.35), (91.75, 24.15), (91.25, 23.95), (91.2, 23.75), (91.3, 23.45), (91.45, 23.1), (92.1, 22.6),
        (92.35, 21.9), (92.65, 21.25), (92.3, 20.65), (91.9, 21.4), (90.5, 21.8), (89.9, 21.8),
    ],
    "Nepal": [
        (80.06, 28.95), (80.5, 29.8), (81.2, 30.2), (82.5, 29.9), (83.5, 29.3), (84.5, 28.7), (86.0, 28.1),
        (87.0, 28.0), (88.2, 27.8), (88.15, 26.4), (87.0, 26.4), (86.0, 26.6), (85.0, 26.9), (84.0, 27.4),
        (83.0, 27.4), (82.0, 27.7), (81.0, 28.3),
    ],
}


def _inside(lon: float, lat: float, poly) -> bool:
    """Ray casting point-in-polygon."""
    inside = False
    j = len(poly) - 1
    for i, (xi, yi) in enumerate(poly):
        xj, yj = poly[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def in_india(lat: float, lon: float) -> bool:
    return _inside(lon, lat, INDIA_OUTLINE) and not any(_inside(lon, lat, p) for p in EXCLUDED_OUTLINES.values())


def load_secret(name: str) -> str | None:
    """A value from the environment or training/.env (git-ignored). Never print it."""
    if os.getenv(name):
        return os.environ[name]
    env = REPO / "training" / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == name:
                return value.strip().strip('"').strip("'") or None
    return None


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
    joins that place's split so no place leaks between train and test.
    Train-only rows (outside data such as TACO) always go to train."""
    for r in rows:
        if r.get("role") == TRAIN_ONLY:
            r["split"] = "train"
    regular = [r for r in rows if r.get("role") != TRAIN_ONLY]
    groups = place_groups(regular, same_place_m)
    group_split: dict[str, str] = {}
    for r in regular:
        if r["split"]:
            group_split.setdefault(groups[r["image_id"]], r["split"])
    for r in regular:
        if not r["split"]:
            g = groups[r["image_id"]]
            r["split"] = group_split.setdefault(g, _bucket(g, ratios))
    return rows


def split_leaks(rows: list[dict], same_place_m: float = SAME_PLACE_M) -> list[str]:
    """Group keys whose photos ended up in more than one split (should be empty)."""
    regular = [r for r in rows if r.get("role") != TRAIN_ONLY]
    groups = place_groups(regular, same_place_m)
    seen: dict[str, set] = {}
    for r in regular:
        if r["split"]:
            seen.setdefault(groups[r["image_id"]], set()).add(r["split"])
    leaks = sorted(g for g, s in seen.items() if len(s) > 1)
    leaks += [f"train-only {r['image_id']}" for r in rows
              if r.get("role") == TRAIN_ONLY and r["split"] not in ("", "train")]
    return leaks


# --- adding images ---------------------------------------------------------------

def register_image(src: Path, meta: dict, rows: list[dict], known: set[str] | None = None) -> str | None:
    """Copy one photo into datasets/images and append its manifest row to `rows`.
    `meta` holds source, licence, author, source_url and optionally lat/lon,
    captured_at, group, role, original_name. Location from `meta` wins over EXIF.
    Returns the new image id, or None for a duplicate (same SHA-256)."""
    import shutil

    if not meta.get("licence"):
        raise ValueError(f"{src}: no licence")
    known = known if known is not None else {r["image_id"] for r in rows}
    image_id = image_id_for(src)
    if image_id in known:
        return None
    IMAGES.mkdir(parents=True, exist_ok=True)
    target = IMAGES / f"{image_id}{Path(src).suffix.lower() or '.jpg'}"
    shutil.copy2(src, target)
    lat, lon = meta.get("lat"), meta.get("lon")
    location_source = meta.get("location_source", "source") if lat is not None and lon is not None else "none"
    exif_lat, exif_lon, taken = exif_info(src)
    if lat is None and exif_lat is not None:
        lat, lon, location_source = exif_lat, exif_lon, "exif"
    rows.append({
        "image_id": image_id,
        "file": f"images/{target.name}",
        "original_name": meta.get("original_name", Path(src).name),
        "source": meta["source"],
        "source_url": meta.get("source_url", ""),
        "licence": meta["licence"],
        "author": meta.get("author", ""),
        "lat": f"{float(lat):.6f}" if lat is not None else "",
        "lon": f"{float(lon):.6f}" if lon is not None else "",
        "captured_at": meta.get("captured_at") or taken,
        "location_source": location_source,
        "group": meta.get("group", ""),
        "split": "",
        "added_at": now_iso(),
        "role": meta.get("role", ""),
    })
    known.add(image_id)
    return image_id


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
