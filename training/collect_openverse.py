"""Collect CC-licensed railway-corridor photos through Openverse (mostly Flickr).

    python training/collect_openverse.py --country Bangladesh --limit 20
    python training/collect_openverse.py --country all --limit 10

Openverse indexes openly licensed images. Only CC0, public domain, CC BY and
CC BY-SA are requested (never NC or ND). Wikimedia results are skipped:
collect_commons.py covers them with better metadata. A photo is kept only if
its title or tags name the country (same place-name rules as the Commons
collector), it is at least 800 px wide, and it is not a map or diagram. The
creator, licence and the photo's own page are recorded. Every photo is tier A.
"""

import argparse
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import collect_commons as cc
import requests
import rvdata as rv

API = "https://api.openverse.org/v1/images/"
HEADERS = {"User-Agent": "RailVigil-dataset/0.2 (academic project; https://github.com/Guru2907/RailVigil)"}
LICENCES = "by,by-sa,cc0,pdm"
PAGE_SIZE = 20          # the most an anonymous client may ask for
MAX_PAGES = 5
INDIA_QUERIES = ["railway slum India", "railway track Mumbai slum", "railway track India garbage",
                 "railway line huts India", "railway track Kolkata", "railway track Delhi slum",
                 "level crossing India", "railway track village India"]


def licence_name(item: dict) -> str:
    code, version = item.get("license", ""), item.get("license_version", "")
    if code == "cc0":
        return "CC0"
    if code == "pdm":
        return "Public domain"
    return f"CC {code.upper()} {version}".strip()


def placed(item: dict, country: str) -> bool:
    title = item.get("title") or ""
    tags = [t.get("name", "") for t in item.get("tags") or []]
    if country == "India":
        return cc.india_evidence(title, tags, None)
    return cc.country_evidence(country, title, tags, None)


def candidate(item: dict, country: str) -> dict | None:
    if (item.get("source") or "").startswith("wikimedia") or (item.get("width") or 0) < cc.MIN_WIDTH:
        return None
    licence = licence_name(item)
    title = item.get("title") or ""
    if not cc.is_free(licence) or cc.NOT_PHOTOS.search(title) or cc.OFF_TOPIC.search(title):
        return None
    if not placed(item, country):
        return None
    return {
        "source": item.get("source") or item.get("provider") or "openverse",
        "source_url": item.get("foreign_landing_url") or "",
        "licence": licence,
        "author": (item.get("creator") or "unknown (see source page)")[:200],
        "original_name": f"openverse_{item['id']}",
        "country": country,
        "tier": "A",
        "_download": item.get("url"),
    }


def search(query: str):
    for page in range(1, MAX_PAGES + 1):
        for attempt in range(4):
            try:
                r = requests.get(API, params={"q": query, "license": LICENCES, "page_size": PAGE_SIZE, "page": page},
                                 headers=HEADERS, timeout=60)
                if r.status_code in (429, 502, 503, 504):
                    time.sleep(10 * (attempt + 1))
                    continue
                break
            except requests.RequestException:
                time.sleep(10 * (attempt + 1))
        else:
            return
        if not r.ok:
            return
        data = r.json()
        yield from data.get("results", [])
        if page >= (data.get("page_count") or 0):
            return
        time.sleep(1.0)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--country", default="all", help="India, one of the collect_commons countries, or 'all'")
    p.add_argument("--limit", type=int, default=15, help="new photos per country")
    args = p.parse_args()
    countries = list(cc.COUNTRIES) if args.country == "all" else [args.country]

    rows = rv.read_manifest()
    known = {r["image_id"] for r in rows}
    seen = {r["original_name"] for r in rows}
    tmp = Path(tempfile.mkdtemp(prefix="rv_openverse_"))
    total = 0
    for country in countries:
        queries = INDIA_QUERIES if country == "India" else [q.format(c=country) for q in cc.COUNTRY_QUERIES]
        added = 0
        for q in queries:
            if added >= args.limit:
                break
            for item in search(q):
                if added >= args.limit:
                    break
                meta = candidate(item, country)
                if meta is None or meta["original_name"] in seen:
                    continue
                seen.add(meta["original_name"])
                url = meta.pop("_download")
                try:
                    resp = requests.get(url, headers=HEADERS, timeout=120)
                except requests.RequestException:
                    continue
                if not resp.ok or not resp.headers.get("content-type", "").startswith("image/"):
                    continue
                path = tmp / f"{meta['original_name']}{Path(urlparse(url).path).suffix.lower() or '.jpg'}"
                path.write_bytes(resp.content)
                if rv.register_image(path, meta, rows, known):
                    added += 1
                    print(f"+ {country}: {(item.get('title') or '')[:70]}  [{meta['licence']}, {meta['source']}]")
                time.sleep(0.5)
        rv.write_manifest(rows)
        total += added
        print(f"{country}: added {added}")
    print(f"\nAdded {total} photos. Manifest: {len(rows)} photos.")


if __name__ == "__main__":
    main()
