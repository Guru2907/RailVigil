"""Train the RailVigil segmentation model on the built dataset.

    python training/train.py --name seg-v1                 # defaults suit an RTX 3050 (4 GB)
    python training/train.py --name seg-v1 --batch 4       # if you see "CUDA out of memory"
    python training/train.py --name smoke --epochs 3       # quick end-to-end check

Runs go to training/runs/<name>/ (git-ignored): weights/best.pt, curves,
confusion matrix, and railvigil_run.json recording exactly what was trained
(git commit, dataset fingerprint, settings), so every result can be traced.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import rvdata as rv


def dataset_fingerprint() -> tuple[str, dict]:
    """Hash of every image name and label file per split: changes whenever the data does."""
    digest = hashlib.sha256()
    counts = {}
    for split in rv.SPLITS:
        labels = sorted((rv.BUILD / "labels" / split).glob("*.txt"))
        counts[split] = len(labels)
        for f in labels:
            digest.update(f"{split}/{f.name}".encode())
            digest.update(f.read_bytes())
    return digest.hexdigest()[:16], counts


def git_state() -> dict:
    def run(*cmd):
        return subprocess.run(["git", *cmd], cwd=rv.REPO, capture_output=True, text=True).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain"))}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True)
    p.add_argument("--base", default="yolov8s-seg.pt", help="starting weights (COCO-pretrained YOLOv8s-seg)")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--patience", type=int, default=30, help="stop early after this many epochs without improvement")
    p.add_argument("--workers", type=int, default=2, help="data-loading processes (keep low on Windows)")
    p.add_argument("--device", default="0", help="0 = first GPU, cpu = CPU (very slow)")
    args = p.parse_args()

    data = rv.BUILD / "data.yaml"
    if not data.is_file():
        raise SystemExit("No dataset built yet. Run: python training/build_dataset.py")
    for split in ("train", "val"):
        if not any((rv.BUILD / "images" / split).glob("*")):
            raise SystemExit(f"The {split} split is empty. Add photos from more places, then rebuild the dataset.")

    import torch
    from ultralytics import YOLO

    if args.device != "cpu" and not torch.cuda.is_available():
        raise SystemExit("PyTorch cannot see the GPU. Run training/setup_training.ps1, or pass --device cpu.")

    fingerprint, counts = dataset_fingerprint()
    rv.WEIGHTS.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(rv.WEIGHTS / args.base))  # downloaded once on first use (~24 MB)
    model.train(
        data=str(data), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, patience=args.patience,
        workers=args.workers, device=args.device, project=str(rv.RUNS), name=args.name, exist_ok=False,
        seed=0, deterministic=True, plots=True,
    )

    # Ultralytics may add a suffix (seg-v1-2) if the name is taken: use the folder it really wrote.
    run_dir = Path(model.trainer.save_dir)
    meta = {
        "name": run_dir.name,
        "created_at": rv.now_iso(),
        "git": git_state(),
        "dataset": {"fingerprint": fingerprint, "labelled_photos": counts, "data_yaml": str(data)},
        "settings": vars(args),
        "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }
    (run_dir / "railvigil_run.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nDone: {run_dir / 'weights' / 'best.pt'}")
    print(f"Next: python training/evaluate.py --name {run_dir.name}")


if __name__ == "__main__":
    main()
