"""train.py ablation options: --exclude drops photos from the train split only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "training"))

import rvdata as rv  # noqa: E402
import train  # noqa: E402

ROWS = [
    {"image_id": "in1", "source": "wikimedia", "country": "India"},
    {"image_id": "fr1", "source": "flickr", "country": "France"},
    {"image_id": "tc1", "source": "taco", "country": ""},
]


def _build(tmp_path, monkeypatch):
    for split in rv.SPLITS:
        (tmp_path / "images" / split).mkdir(parents=True)
        (tmp_path / "labels" / split).mkdir(parents=True)
    for r in ROWS:
        (tmp_path / "images" / "train" / f"{r['image_id']}.jpg").write_bytes(b"x")
        (tmp_path / "labels" / "train" / f"{r['image_id']}.txt").write_text("", encoding="utf-8")
    (tmp_path / "images" / "val" / "in2.jpg").write_bytes(b"x")
    (tmp_path / "labels" / "val" / "in2.txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(rv, "BUILD", tmp_path)
    monkeypatch.setattr(rv, "read_manifest", lambda: ROWS)


def test_exclude_foreign_keeps_india_and_taco(tmp_path, monkeypatch):
    _build(tmp_path, monkeypatch)
    kept, dropped = train.train_subset(["foreign"])
    assert sorted(p.stem for p in kept) == ["in1", "tc1"]
    assert dropped == {"foreign": 1}


def test_exclude_taco(tmp_path, monkeypatch):
    _build(tmp_path, monkeypatch)
    kept, dropped = train.train_subset(["taco"])
    assert sorted(p.stem for p in kept) == ["fr1", "in1"]
    assert dropped == {"taco": 1}


def test_fingerprint_follows_the_train_subset_and_keeps_val(tmp_path, monkeypatch):
    _build(tmp_path, monkeypatch)
    full, full_counts = train.dataset_fingerprint()
    kept, _ = train.train_subset(["taco"])
    sub, sub_counts = train.dataset_fingerprint(kept)
    assert full != sub
    assert (full_counts["train"], sub_counts["train"]) == (3, 2)
    assert full_counts["val"] == sub_counts["val"] == 1
