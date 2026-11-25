"""Train the RailVigil segmentation model on the built dataset.

    python training/train.py --name railvigil-s                 # defaults suit an RTX 3050 (4 GB)
    python training/train.py --name railvigil-s --batch 4       # if you see "CUDA out of memory"
    python training/train.py --name smoke --epochs 3       # quick end-to-end check
    python training/train.py --name s-seed1 --seed 1             # same run, another random start
    python training/train.py --name s-india --exclude foreign    # ablation: train without foreign railway photos
    python training/train.py --name s-notaco --exclude taco      # ablation: train without the TACO litter photos

--exclude only removes photos from the train split; val and test stay the same,
so runs remain comparable.

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

EXCLUDE = {
    # foreign railway photos; TACO (litter, no country) is kept so only one thing changes
    "foreign": lambda r: r.get("source") != "taco" and r.get("country") != "India",
    "taco": lambda r: r.get("source") == "taco",
}


def train_subset(exclude: list[str]) -> tuple[list[Path], dict]:
    """Train images left after dropping the excluded groups, and how many each group removed."""
    rows = {r["image_id"]: r for r in rv.read_manifest()}
    kept, dropped = [], {e: 0 for e in exclude}
    for img in sorted((rv.BUILD / "images" / "train").glob("*")):
        row = rows.get(img.stem, {})
        hit = [e for e in exclude if EXCLUDE[e](row)]
        for e in hit:
            dropped[e] += 1
        if not hit:
            kept.append(img)
    return kept, dropped


def dataset_fingerprint(train_images: list[Path] | None = None) -> tuple[str, dict]:
    """Hash of every image name and label file per split: changes whenever the data does."""
    digest = hashlib.sha256()
    counts = {}
    for split in rv.SPLITS:
        labels = sorted((rv.BUILD / "labels" / split).glob("*.txt"))
        if split == "train" and train_images is not None:
            labels = [rv.BUILD / "labels" / "train" / f"{img.stem}.txt" for img in train_images]
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
    p.add_argument("--freeze", type=int, default=0,
                   help="freeze the first N layers (e.g. 10 = backbone) to keep pretrained features on small data")
    p.add_argument("--seed", type=int, default=0, help="random seed; repeat a run with other seeds to measure noise")
    p.add_argument("--exclude", nargs="+", choices=sorted(EXCLUDE), default=[],
                   help="drop these photos from the train split only (ablations)")
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

    dropped = {}
    train_images = None
    if args.exclude:
        train_images, dropped = train_subset(args.exclude)
        lists = rv.BUILD.parent / "lists" / args.name
        lists.mkdir(parents=True, exist_ok=True)
        (lists / "train.txt").write_text("\n".join(str(i) for i in train_images), encoding="utf-8")
        train_list = (lists / "train.txt").as_posix()
        text = data.read_text(encoding="utf-8").replace("train: images/train", f"train: {train_list}")
        data = lists / "data.yaml"
        data.write_text(text, encoding="utf-8")
        print(f"Excluded from train: {dropped}; {len(train_images)} train photos left")

    fingerprint, counts = dataset_fingerprint(train_images)
    rv.WEIGHTS.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(rv.WEIGHTS / args.base))  # downloaded once on first use (~24 MB)
    model.train(
        data=str(data), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, patience=args.patience,
        workers=args.workers, device=args.device, project=str(rv.RUNS), name=args.name, exist_ok=False,
        seed=args.seed, deterministic=True, plots=True, freeze=args.freeze or None,
    )

    # Ultralytics may add a suffix (railvigil-s-2) if the name is taken: use the folder it really wrote.
    run_dir = Path(model.trainer.save_dir)
    meta = {
        "name": run_dir.name,
        "created_at": rv.now_iso(),
        "git": git_state(),
        "dataset": {"fingerprint": fingerprint, "labelled_photos": counts, "data_yaml": str(data),
                    "excluded_from_train": dropped},
        "settings": vars(args),
        "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }
    (run_dir / "railvigil_run.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nDone: {run_dir / 'weights' / 'best.pt'}")
    print(f"Next: python training/evaluate.py --name {run_dir.name}")


if __name__ == "__main__":
    main()
