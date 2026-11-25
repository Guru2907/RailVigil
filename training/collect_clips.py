"""Collect short, licensed video clips for the intrusion evaluation.

    python training/collect_clips.py --pixabay-preview          # thumbnail sheets, pick by eye
    python training/collect_clips.py --pixabay-ids 92376 3178 --intrusion yes
    python training/collect_clips.py --add-commons "File:Some_clip.webm" --intrusion no
    python training/collect_clips.py --commons 10

Clips go to datasets/intrusion/clips/ and are listed in datasets/intrusion/clips.csv
(source, licence, author, duration; tracked in git, the videos are not).
  - Pixabay (PIXABAY_API_KEY in training/.env, never printed). Its keyword search
    is loose (cows in fields, city crowds), so candidates are previewed as
    thumbnail sheets and only clips picked by eye are downloaded. Tier B.
  - Wikimedia Commons: free-licence railway videos (level crossings, trains
    passing). Tier A. Extra files can be named with --add-commons.
  - Mixkit: clip ids given with --mixkit (free licence, tier B).
Whether a clip really shows an intrusion is decided by watching it, when
datasets/intrusion/labels.csv is filled; `intrusion_hint` is only the search's guess.
"""

import argparse
import csv
import sys
import time
from pathlib import Path
from urllib.parse import quote

import collect_commons as cc
import requests
import rvdata as rv

CLIPS = rv.DATASETS / "intrusion" / "clips"
CLIPS_CSV = rv.DATASETS / "intrusion" / "clips.csv"
FIELDS = ["file", "tier", "source", "source_url", "licence", "author", "country", "duration_sec",
          "width", "height", "intrusion_hint", "query", "added_at"]
# Pixabay and Mixkit refuse requests without a browser-like User-Agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (RailVigil-dataset/0.2; academic project)"}
MIN_SEC, MAX_SEC = 8, 90
MAX_MB = 80

PIXABAY_QUERIES = [
    "railway track", "railroad crossing", "train track people", "railway crossing", "level crossing",
    "train tracks walking", "railway india", "train station platform", "railroad tracks", "rail track cow",
    "railway track dog", "people walking rails", "india train", "train passing", "railway line", "railway asia",
]
COMMONS_QUERIES = [
    ("level crossing pedestrians", "yes"), ("people crossing railway track", "yes"), ("cows on railway", "yes"),
    ("level crossing train", "no"), ("train passing level crossing", "no"), ("railway track India train", "no"),
]


def read_clips() -> list[dict]:
    if not CLIPS_CSV.is_file():
        return []
    with CLIPS_CSV.open(encoding="utf-8", newline="") as f:
        return [{k: r.get(k, "") for k in FIELDS} for r in csv.DictReader(f)]


def write_clips(rows: list[dict]) -> None:
    CLIPS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with CLIPS_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def save(url: str, name: str, headers: dict = HEADERS) -> Path | None:
    try:
        with requests.get(url, headers=headers, timeout=300, stream=True) as r:
            if not r.ok or not r.headers.get("content-type", "").startswith(("video/", "application/ogg")):
                return None
            CLIPS.mkdir(parents=True, exist_ok=True)
            path = CLIPS / name
            with path.open("wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
                    if f.tell() > MAX_MB * (1 << 20):
                        break
            if path.stat().st_size > MAX_MB * (1 << 20):
                path.unlink()
                return None
            return path
    except requests.RequestException:
        return None


def pixabay_get(key: str, **params) -> list[dict]:
    r = requests.get("https://pixabay.com/api/videos/", params={"key": key, "safesearch": "true", **params},
                     headers=HEADERS, timeout=60)
    if not r.ok:  # never print the URL: it carries the key
        print(f"  Pixabay {params.get('q') or params.get('id')}: HTTP {r.status_code}")
        return []
    return r.json().get("hits", [])


def pixabay_preview(key: str) -> int:
    """Thumbnail sheets of Pixabay candidates (nothing downloaded): keyword search is too
    loose to download blindly, so clips are picked by eye and added with --pixabay-ids."""
    import cv2
    import numpy as np

    seen, tiles = set(), []
    for query in PIXABAY_QUERIES:
        for hit in pixabay_get(key, q=query, per_page=50):
            if hit["id"] in seen or not MIN_SEC <= hit.get("duration", 0) <= MAX_SEC:
                continue
            seen.add(hit["id"])
            thumb = hit["videos"]["tiny"].get("thumbnail") or hit["videos"]["small"].get("thumbnail")
            tile = np.zeros((180, 320, 3), np.uint8)
            try:
                img = cv2.imdecode(np.frombuffer(requests.get(thumb, headers=HEADERS, timeout=30).content, np.uint8),
                                   cv2.IMREAD_COLOR)
            except requests.RequestException:
                img = None
            if img is not None:
                s = min(320 / img.shape[1], 158 / img.shape[0])
                small = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)))
                tile[22:22 + small.shape[0], :small.shape[1]] = small
            cv2.putText(tile, f"{hit['id']} {hit['duration']}s", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (80, 255, 160), 1)
            tiles.append(tile)
    out = rv.DATASETS / "intrusion" / "preview"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("pixabay_*.jpg"):
        old.unlink()
    tiles += [np.zeros((180, 320, 3), np.uint8)] * (-len(tiles) % 6)
    rows = [np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)]
    for n in range(0, len(rows), 7):
        cv2.imwrite(str(out / f"pixabay_{n // 7:02d}.jpg"), np.vstack(rows[n:n + 7]), [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(f"{len(seen)} candidates -> {out} (pixabay_*.jpg); add the good ones with --pixabay-ids")
    return len(seen)


def pixabay_ids(key: str, ids: list[str], hint: str, rows: list[dict], seen: set[str]) -> int:
    added = 0
    for clip_id in ids:
        name = f"pixabay_{clip_id}.mp4"
        hits = pixabay_get(key, id=clip_id)
        if name in seen or path_exists(name) or not hits:
            continue
        hit = hits[0]
        video = hit["videos"].get("medium") or hit["videos"].get("small")
        if not video or not video.get("url") or save(video["url"], name) is None:
            print(f"  pixabay {clip_id}: download failed")
            continue
        seen.add(name)
        rows.append({"file": name, "tier": "B", "source": "pixabay", "source_url": hit["pageURL"],
                     "licence": "Pixabay Content License", "author": hit.get("user", ""), "country": "unknown",
                     "duration_sec": hit.get("duration", ""), "width": video.get("width", ""),
                     "height": video.get("height", ""), "intrusion_hint": hint, "query": "picked by id",
                     "added_at": rv.now_iso()})
        added += 1
        print(f"+ {name}  {hit.get('duration')} s")
        time.sleep(0.5)
    return added


def path_exists(name: str) -> bool:
    return (CLIPS / name).is_file()


def commons_video(title: str, hint: str, query: str, rows: list[dict], seen: set[str]) -> bool:
    data = cc.api({"titles": title, "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime|mediatype",
                   "iiextmetadatafilter": "LicenseShortName|Artist"})
    pages = data.get("query", {}).get("pages", [])
    if not pages or "imageinfo" not in pages[0]:
        return False
    info = pages[0]["imageinfo"][0]
    meta = info.get("extmetadata", {})
    licence = meta.get("LicenseShortName", {}).get("value", "")
    duration = info.get("duration") or 0
    if info.get("mediatype") != "VIDEO" or not cc.is_free(licence) or not MIN_SEC <= duration <= MAX_SEC * 2:
        return False
    name = "commons_" + "".join(c if c.isascii() and c.isalnum() else "_" for c in title.removeprefix("File:"))[:80]
    name = name.rsplit("_", 1)[0] + "." + title.rsplit(".", 1)[-1].lower()
    # Wikimedia refuses browser-like User-Agents (HTTP 429); it wants the descriptive one.
    if name in seen or path_exists(name) or save(info["url"], name, cc.HEADERS) is None:
        return False
    seen.add(name)
    rows.append({"file": name, "tier": "A", "source": "wikimedia", "source_url": info.get("descriptionurl", ""),
                 "licence": licence, "author": cc.strip_html(meta.get("Artist", {}).get("value", ""))[:200],
                 "country": "", "duration_sec": round(duration, 1), "width": info.get("width", ""),
                 "height": info.get("height", ""), "intrusion_hint": hint, "query": query, "added_at": rv.now_iso()})
    print(f"+ {name}  {duration:.0f} s  [{licence}]")
    return True


def commons_search(limit: int, rows: list[dict], seen: set[str]) -> int:
    added = 0
    for query, hint in COMMONS_QUERIES:
        data = cc.api({"list": "search", "srsearch": f"{query} filetype:video", "srnamespace": 6, "srlimit": 20})
        for hit in data.get("query", {}).get("search", []):
            if added >= limit:
                return added
            added += commons_video(hit["title"], hint, query, rows, seen)
            time.sleep(1.0)
    return added


def mixkit(ids: list[str], rows: list[dict], seen: set[str]) -> int:
    added = 0
    for clip_id in ids:
        name = f"mixkit_{clip_id}.mp4"
        if name in seen or path_exists(name):
            continue
        if save(f"https://assets.mixkit.co/videos/{clip_id}/{clip_id}-720.mp4", name) is None:
            print(f"  mixkit {clip_id}: not found")
            continue
        seen.add(name)
        rows.append({"file": name, "tier": "B", "source": "mixkit",
                     "source_url": f"https://mixkit.co/free-stock-video/{quote(clip_id)}/",
                     "licence": "Mixkit Stock Video Free License", "author": "Mixkit", "country": "unknown",
                     "duration_sec": "", "width": "", "height": "", "intrusion_hint": "yes", "query": "mixkit id",
                     "added_at": rv.now_iso()})
        added += 1
        print(f"+ {name}")
    return added


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pixabay-preview", action="store_true", help="thumbnail sheets of Pixabay candidates")
    p.add_argument("--pixabay-ids", nargs="*", default=[], help="Pixabay video ids to download")
    p.add_argument("--commons", type=int, default=0, help="Commons clips to add from searches")
    p.add_argument("--add-commons", nargs="*", default=[], help="Commons file titles to add")
    p.add_argument("--intrusion", default="", help="hint for --add-commons / --pixabay-ids clips: yes / no")
    p.add_argument("--mixkit", nargs="*", default=[], help="Mixkit clip ids, e.g. 345")
    args = p.parse_args()

    rows = read_clips()
    seen = {r["file"] for r in rows}
    added = 0
    if args.pixabay_preview or args.pixabay_ids:
        key = rv.load_secret("PIXABAY_API_KEY")
        if not key:
            raise SystemExit("PIXABAY_API_KEY not found in training/.env")
        if args.pixabay_preview:
            pixabay_preview(key)
        added += pixabay_ids(key, args.pixabay_ids, args.intrusion, rows, seen)
        write_clips(rows)
    for title in args.add_commons:
        added += commons_video(title if title.startswith("File:") else f"File:{title}", args.intrusion,
                               "named", rows, seen)
        time.sleep(1.0)
    if args.commons:
        added += commons_search(args.commons, rows, seen)
    added += mixkit(args.mixkit, rows, seen)
    write_clips(rows)
    print(f"\nAdded {added} clips. {CLIPS_CSV}: {len(rows)} clips.")


if __name__ == "__main__":
    main()
