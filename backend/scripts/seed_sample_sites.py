"""
Fill the app with SAMPLE data: upload the dataset photos that have a real
location (datasets/manifest.csv) through the normal API, so the GIS map,
dashboard, sites and reports show real Indian locations.

    python scripts/seed_sample_sites.py                    # backend must be running (uvicorn)
    python scripts/seed_sample_sites.py --limit 40
    python scripts/seed_sample_sites.py --remove           # delete all sample data again

Every photo is analysed by the current pipeline exactly like a user upload,
with these sample settings:
  - location = the photo's GPS from the manifest (sent as the map pin);
  - zone = the lower 45 % of the photo (a stand-in for the real right-of-way,
    which is not known for these photos);
  - camera_label = "dataset-sample", so the data can be told apart and removed.
It is sample data for demonstration, not field reports.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "training"))

import rvdata as rv  # noqa: E402

SAMPLE_LABEL = "dataset-sample"
LOWER_PART = [[0, 0.55], [1, 0.55], [1, 1], [0, 1]]


def seed(api: str, limit: int) -> None:
    rows = [r for r in rv.read_manifest() if r["role"] != rv.TRAIN_ONLY and r["lat"] and r["lon"]]
    rows = rows[:limit] if limit else rows
    print(f"Uploading {len(rows)} located photos to {api} as '{SAMPLE_LABEL}'")
    done = dup = 0
    for i, r in enumerate(rows, start=1):
        path = rv.DATASETS / r["file"]
        for _ in range(120):  # the server refuses new work (429) while its queue is full: wait and retry
            with path.open("rb") as f:
                resp = requests.post(f"{api}/media", files={"files": (path.name, f)}, data={
                    "zone_points": json.dumps(LOWER_PART), "zone_format": "normalized",
                    "latitude": r["lat"], "longitude": r["lon"], "camera_label": SAMPLE_LABEL,
                }, timeout=120)
            if resp.status_code != 429:
                break
            time.sleep(5)
        if resp.status_code != 200:
            print(f"  [{i}] {path.name}: {resp.status_code} {resp.text[:120]}")
            continue
        item = resp.json()[0]
        dup += item["duplicate"]
        done += 1
        if i % 20 == 0:
            print(f"  {i}/{len(rows)} uploaded")
    print(f"Uploaded {done} ({dup} were already there). The backend analyses them in the background;")
    print("open the GIS map in a minute or two.")


def remove() -> None:
    from sqlalchemy import select

    from app.db.database import SessionLocal
    from app.db.models.encroachment import EncroachmentFinding, EncroachmentSite, Media, Report
    from app.services import storage_service

    db = SessionLocal()
    try:
        media = list(db.execute(select(Media).where(Media.camera_label == SAMPLE_LABEL)).scalars())
        media_ids = {m.id for m in media}
        site_ids = {f.site_id for f in db.execute(
            select(EncroachmentFinding).where(EncroachmentFinding.media_id.in_(media_ids))).scalars() if f.site_id}
        # Only sites that contain nothing but sample findings are deleted.
        other = {f.site_id for f in db.execute(
            select(EncroachmentFinding).where(EncroachmentFinding.site_id.in_(site_ids),
                                              EncroachmentFinding.media_id.notin_(media_ids))).scalars()}
        sample_sites = site_ids - other
        for rep in db.execute(select(Report).where(
                Report.media_id.in_(media_ids) | Report.site_id.in_(sample_sites))).scalars():
            db.delete(rep)
        for m in media:
            db.delete(m)                      # findings cascade
        db.flush()
        for s in db.execute(select(EncroachmentSite).where(EncroachmentSite.id.in_(sample_sites))).scalars():
            db.delete(s)                      # history cascades
        db.commit()
    finally:
        db.close()
    for media_id in media_ids:
        storage_service.delete_prefix(storage_service.media_key(media_id))
    print(f"Removed {len(media_ids)} sample photos and {len(sample_sites)} sample-only sites.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api", default="http://127.0.0.1:8000/api")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--remove", action="store_true")
    args = p.parse_args()
    if args.remove:
        remove()
        return
    try:
        requests.get(f"{args.api}/health", timeout=5).raise_for_status()
    except requests.RequestException:
        raise SystemExit(f"Backend not reachable at {args.api}. Start it first: uvicorn app.main:app") from None
    start = time.time()
    seed(args.api, args.limit)
    print(f"({time.time() - start:.0f} s)")


if __name__ == "__main__":
    main()
