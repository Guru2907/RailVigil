"""Add photos listed in datasets/incoming/incoming.csv (from a collection agent or by hand).

    python training/ingest_incoming.py
    python training/ingest_incoming.py --csv datasets/incoming/other.csv --dry-run

CSV columns (extra columns are ignored):
    file_name, media_type, tier, source, source_url, direct_download_url, licence,
    author_or_credit, country, region_or_city, lat, lon, captured_or_uploaded_date
Rules:
  - only `media_type=photo` rows; clips are handled by collect_clips.py;
  - a row needs a source_url, a licence and a tier (A, B or C), else it is rejected;
  - Wikimedia Commons rows are re-checked on Commons (the licence must still be
    free) and downloaded at 2048 px, like collect_commons.py;
  - tier C rows (research use only) are never downloaded here: save the photo by
    hand as datasets/incoming/files/<file_name>. They become training-only;
  - other rows are downloaded from direct_download_url, or taken from
    datasets/incoming/files/<file_name> when that file exists.
"""

import argparse
import csv
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import collect_commons as cc
import rvdata as rv

INCOMING = rv.DATASETS / "incoming"


def commons_title(url: str) -> str | None:
    path = unquote(urlparse(url).path)
    return path.split("/wiki/", 1)[1] if "/wiki/File:" in path else None


def commons_meta(title: str) -> dict | None:
    data = cc.api({"titles": title, **cc.FILE_PROPS})
    pages = data.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        return None
    info = (pages[0].get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata", {})
    licence = meta.get("LicenseShortName", {}).get("value", "")
    if not cc.is_free(licence):
        return None
    return {"licence": licence, "_download": info.get("thumburl") or info.get("url"), "_original": info.get("url"),
            "author": cc.strip_html(meta.get("Artist", {}).get("value", ""))[:200]}


def row_meta(row: dict) -> dict:
    lat, lon = row.get("lat", "").strip(), row.get("lon", "").strip()
    return {
        "source": row["source"].strip().lower(),
        "source_url": row["source_url"].strip(),
        "licence": row["licence"].strip(),
        "author": row.get("author_or_credit", "").strip() or "unknown (see source page)",
        "lat": float(lat) if lat else None,
        "lon": float(lon) if lon else None,
        "location_source": "source",
        "captured_at": row.get("captured_or_uploaded_date", "").strip(),
        "original_name": row["file_name"].strip(),
        "country": row.get("country", "").strip(),
        "region": row.get("region_or_city", "").strip(),
        "tier": row["tier"].strip().upper(),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", type=Path, default=INCOMING / "incoming.csv")
    p.add_argument("--dry-run", action="store_true", help="check rows, download nothing")
    args = p.parse_args()

    rows = rv.read_manifest()
    known = {r["image_id"] for r in rows}
    seen = {r["original_name"] for r in rows}
    tmp = Path(tempfile.mkdtemp(prefix="rv_incoming_"))
    added = dup = 0
    problems = []
    with args.csv.open(encoding="utf-8-sig", newline="") as f:
        incoming = [r for r in csv.DictReader(f) if r.get("media_type", "photo").strip() == "photo"]

    for row in incoming:
        name = row.get("file_name", "").strip()
        if not row.get("source_url", "").strip() or row.get("tier", "").strip().upper() not in rv.TIERS:
            problems.append(f"{name}: no source_url or tier")
            continue
        meta = row_meta(row)
        if meta["original_name"] in seen:
            dup += 1
            continue
        local = INCOMING / "files" / name
        url = original = None
        if meta["source"] == "wikimedia" and (title := commons_title(meta["source_url"])):
            checked = commons_meta(title)
            if checked is None:
                problems.append(f"{name}: not on Commons any more, or licence not free")
                continue
            meta["licence"], url, original = checked["licence"], checked["_download"], checked["_original"]
            meta["author"] = meta["author"] if meta["author"] != "unknown (see source page)" else checked["author"]
        elif meta["tier"] == "C" or local.is_file():
            if not local.is_file():
                problems.append(f"{name}: tier C, save it by hand as {local}")
                continue
        else:
            url = row.get("direct_download_url", "").strip()
        if not meta["licence"]:
            problems.append(f"{name}: no licence")
            continue
        if args.dry_run:
            print(f"ok  {name}  [{meta['tier']} {meta['licence']}]")
            continue
        if url:
            target = tmp / (Path(name).stem + (Path(urlparse(url).path).suffix.lower() or ".jpg"))
            local = cc.download_photo(url, original, target)
            if local is None:
                problems.append(f"{name}: download failed")
                continue
            time.sleep(1.0)
        image_id = rv.register_image(local, meta, rows, known)
        seen.add(meta["original_name"])
        if image_id:
            added += 1
            print(f"+ {image_id}  {name}  [{meta['tier']} {meta['licence']}]")
        else:
            dup += 1

    if not args.dry_run:
        rv.assign_splits(rows)
        rv.write_manifest(rows)
    print(f"\n{len(incoming)} photo rows: {added} added, {dup} already present, {len(problems)} not added.")
    for msg in problems:
        print(f"  - {msg}")


if __name__ == "__main__":
    main()
