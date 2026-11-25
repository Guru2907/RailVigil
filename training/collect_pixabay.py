"""Collect free-stock railway photos from Pixabay (tier B: training only).

    python training/collect_pixabay.py --limit 40

Pixabay photos are under the Pixabay Content License: free to use, credit
recorded, but the files may not be redistributed as they are, and they carry no
place information. So they are tier B: training data only, never in val/test,
figures or a shared dataset. Mostly useful as clean-track negatives and extra
trackside scenes; every photo still goes through the visual review.
Needs PIXABAY_API_KEY in training/.env; it is never printed.
"""

import argparse
import sys
import tempfile
import time
from pathlib import Path

import requests
import rvdata as rv

API = "https://pixabay.com/api/"
# Pixabay refuses requests without a browser-like User-Agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (RailVigil-dataset/0.2; academic project)"}
LICENCE = "Pixabay Content License"
QUERIES = [
    "railway slum", "railway tracks garbage", "railway tracks houses", "train tracks trash",
    "railway track india", "railway line village", "level crossing", "railroad tracks weeds",
    "railway station track", "railway track shacks", "train tracks market", "abandoned railway",
]


def search(key: str, query: str, pages: int = 2):
    for page in range(1, pages + 1):
        try:
            r = requests.get(API, params={"key": key, "q": query, "image_type": "photo", "per_page": 50,
                                          "page": page, "safesearch": "true", "min_width": 1024},
                             headers=HEADERS, timeout=60)
        except requests.RequestException:
            return
        if not r.ok:  # never print the URL: it carries the key
            print(f"  Pixabay search '{query}' failed: HTTP {r.status_code}")
            return
        hits = r.json().get("hits", [])
        yield from hits
        if len(hits) < 50:
            return
        time.sleep(1.0)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--limit", type=int, default=40, help="new photos to add")
    p.add_argument("--per-query", type=int, default=6, help="photos to keep per search at most")
    args = p.parse_args()
    key = rv.load_secret("PIXABAY_API_KEY")
    if not key:
        raise SystemExit("PIXABAY_API_KEY not found in training/.env")

    rows = rv.read_manifest()
    known = {r["image_id"] for r in rows}
    seen = {r["original_name"] for r in rows}
    tmp = Path(tempfile.mkdtemp(prefix="rv_pixabay_"))
    added = 0
    for q in QUERIES:
        kept = 0
        for hit in search(key, q):
            if added >= args.limit or kept >= args.per_query:
                break
            name = f"pixabay_{hit['id']}"
            if name in seen:
                continue
            seen.add(name)
            resp = requests.get(hit["largeImageURL"], headers=HEADERS, timeout=120)
            if not resp.ok:
                continue
            path = tmp / f"{name}.jpg"
            path.write_bytes(resp.content)
            if rv.register_image(path, {
                "source": "pixabay", "source_url": hit["pageURL"], "licence": LICENCE,
                "author": hit.get("user", ""), "original_name": name, "country": "unknown",
                "tier": "B",
            }, rows, known):
                added += 1
                kept += 1
                print(f"+ {name}  ({hit.get('tags', '')[:60]})")
            time.sleep(0.5)
        if added >= args.limit:
            break
    rv.write_manifest(rows)
    print(f"\nAdded {added} photos (tier B, training only). Manifest: {len(rows)} photos.")


if __name__ == "__main__":
    main()
