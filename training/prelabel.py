"""Pre-label photos so humans only correct instead of drawing from scratch.

The pretrained baseline (Open Images V7 + YOLO-World, the same models and
label mapping as the backend) finds candidate objects; MobileSAM turns each
box into a mask outline. The result is a folder you upload to Roboflow or
CVAT, fix by hand, export, and bring back with import_labels.py.

    python training/prelabel.py --name batch01                # all photos without labels yet
    python training/prelabel.py --name batch01 --limit 50 --no-sam

Output: datasets/upload/<name>/{images,labels}/ + data.yaml
  Roboflow: Upload > select the folder (format: YOLOv8 / YOLO segmentation)
  CVAT:     Import dataset > "Ultralytics YOLO Segmentation 1.0" (zip the folder)

Pre-labels are suggestions with the baseline's known mistakes. Every one must
be checked; missing objects (especially waste and bushes) must be drawn.
"""

import argparse
import shutil

import rvdata as rv

from app.cv.encroachment.taxonomy import CLASSES, map_label

BASELINE = {  # model name -> (weights file in backend/models, confidence cut-off)
    "oiv7-v8s": ("yolov8s-oiv7.pt", 0.25),
    "world-v8s-railvigil": ("yolov8s-world-railvigil.pt", 0.10),
}
MERGE_IOU = 0.5
MAX_BOX_SHARE = 0.8


def detect(models, image_path):
    """[(class index, conf, (x1, y1, x2, y2))] merged across models, plus image size."""
    found, size = [], None
    for name, (model, conf) in models.items():
        result = model.predict(str(image_path), conf=conf, verbose=False)[0]
        h, w = result.orig_shape
        size = (w, h)
        if result.boxes is None:
            continue
        for xyxy, cls_id, score in zip(result.boxes.xyxy.tolist(), result.boxes.cls.tolist(),
                                       result.boxes.conf.tolist(), strict=True):
            cls = map_label(name, result.names[int(cls_id)])
            if cls is None or (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1]) >= MAX_BOX_SHARE * w * h:
                continue
            found.append((CLASSES.index(cls), float(score), tuple(xyxy)))
    kept = []
    for det in sorted(found, key=lambda d: -d[1]):
        if not any(k[0] == det[0] and rv.box_iou(k[2], det[2]) >= MERGE_IOU for k in kept):
            kept.append(det)
    return kept, size


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True, help="batch name, e.g. batch01")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--include-labelled", action="store_true", help="also pre-label photos that already have labels")
    p.add_argument("--no-sam", action="store_true", help="rectangles only (faster, worse masks)")
    p.add_argument("--device", default=None, help="e.g. 0 for the GPU, cpu for the CPU (default: auto)")
    args = p.parse_args()

    from ultralytics import SAM, YOLO

    rows = rv.read_manifest()
    todo = [r for r in rows if args.include_labelled or not (rv.LABELS / f"{r['image_id']}.txt").exists()]
    if args.limit:
        todo = todo[: args.limit]
    if not todo:
        raise SystemExit("Nothing to pre-label (add photos with add_images.py first).")

    models = {}
    for name, (filename, conf) in BASELINE.items():
        path = rv.BACKEND / "models" / filename
        if not path.is_file():
            raise SystemExit(f"Missing {path}. See docs/ENCROACHMENT_SPEC.md for how to get the baseline weights.")
        models[name] = (YOLO(str(path)), conf)
    sam = None
    if not args.no_sam:
        rv.WEIGHTS.mkdir(parents=True, exist_ok=True)
        sam = SAM(str(rv.WEIGHTS / "mobile_sam.pt"))  # downloaded once (~40 MB) on first use

    out = rv.DATASETS / "upload" / args.name
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "labels").mkdir(parents=True, exist_ok=True)
    total = 0
    for i, row in enumerate(todo, start=1):
        image = rv.DATASETS / row["file"]
        dets, (w, h) = detect(models, image)
        labels = []
        if dets and sam is not None:
            res = sam(str(image), bboxes=[list(d[2]) for d in dets], verbose=False, device=args.device)[0]
            polys = res.masks.xyn if res.masks is not None else []
            for d, poly in zip(dets, polys, strict=False):
                pts = [(float(x), float(y)) for x, y in poly]
                labels.append((d[0], pts if len(pts) >= 3 else None, d[2]))
        else:
            labels = [(d[0], None, d[2]) for d in dets]
        final = []
        for cls, pts, (x1, y1, x2, y2) in labels:
            if pts is None:  # rectangle fallback
                pts = [(x1 / w, y1 / h), (x2 / w, y1 / h), (x2 / w, y2 / h), (x1 / w, y2 / h)]
            final.append((cls, pts))
        shutil.copy2(image, out / "images" / image.name)
        rv.write_labels(out / "labels" / f"{row['image_id']}.txt", final)
        total += len(final)
        print(f"[{i}/{len(todo)}] {image.name}: {len(final)} pre-labels")

    (out / rv.PRELABEL_MARKER).write_text(
        "Machine pre-labels from the pretrained baseline. Correct them in Roboflow/CVAT and import the EXPORT,\n"
        "not this folder. Labels imported from here would make the evaluation measure the baseline against itself.\n",
        encoding="utf-8",
    )
    names = "\n".join(f"  {i}: {c}" for i, c in enumerate(CLASSES))
    (out / "data.yaml").write_text(f"path: .\ntrain: images\nval: images\nnames:\n{names}\n", encoding="utf-8")
    print(f"\n{len(todo)} photos, {total} pre-labels -> {out}")
    print("Next: upload this folder to Roboflow/CVAT, correct every label, export as YOLO segmentation,")
    print("then run: python training/import_labels.py <export folder>")


if __name__ == "__main__":
    main()
