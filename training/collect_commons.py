"""Collect freely licensed Indian railway-corridor photos from Wikimedia Commons.

    python training/collect_commons.py --limit 100

Sources: the category "Slums and rail tracks" (and its subcategories) plus
searches such as "railway track slum Mumbai". A photo is kept only if:
  - its licence is free (CC0, public domain, CC BY, CC BY-SA, FAL, GFDL; never NC or ND);
  - it is in India: coordinates inside India (rvdata.in_india) or, without
    coordinates, Indian place names in its title/categories and no foreign ones;
  - it is a photo of reasonable size, not a map, diagram or logo.
Title, author, licence and the file page are recorded in the manifest. No account needed.
"""

import argparse
import html
import re
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import rvdata as rv

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "RailVigil-dataset/0.1 (academic project; https://github.com/Guru2907/RailVigil)"}

CATEGORIES = ["Slums and rail tracks"]
QUERIES = [
    "railway track slum India", "railway track slum Mumbai", "railway line slum Delhi",
    "railway track Kolkata slum", "railway encroachment India", "garbage railway track India",
    "railway track Mumbai", "railway track Delhi", "railway track Kolkata", "railway track Chennai",
    "railway track Hyderabad", "railway track Bangalore", "level crossing India", "railway line huts India",
    "jhuggi railway", "railway track India houses",
    # Uttar Pradesh and Bihar, plus more trackside scenes
    "railway track Lucknow", "railway track Kanpur", "railway track Varanasi", "railway track Prayagraj",
    "railway track Allahabad", "railway track Gorakhpur", "railway track Agra", "railway track Mathura",
    "railway track Ghaziabad", "railway track Meerut", "railway track Bareilly", "railway track Jhansi",
    "railway track Patna", "railway track Gaya", "railway track Muzaffarpur", "railway track Darbhanga",
    "railway track Bhagalpur", "railway track Samastipur", "railway line Uttar Pradesh", "railway line Bihar",
    "railway station Uttar Pradesh track", "railway station Bihar track", "slum railway Lucknow",
    "slum railway Patna", "garbage railway line", "railway crossing village India", "railway track village India",
    "railway track market India", "railway track shops India", "railway line houses Kolkata",
    "railway track Mumbai suburban slum", "railway colony India", "railway track vegetation India",
]

INDIA_WORDS = [
    "india", "indian", "uttar pradesh", "varanasi", "prayagraj", "allahabad", "gorakhpur",
    "mathura", "ghaziabad", "meerut", "bareilly", "jhansi", "gaya", "muzaffarpur", "darbhanga", "bhagalpur",
    "samastipur", "bihar", "mumbai", "bombay", "delhi", "kolkata", "calcutta", "chennai", "madras", "bengaluru",
    "bangalore", "hyderabad", "secunderabad", "pune", "ahmedabad", "surat", "jaipur", "lucknow", "kanpur", "patna",
    "nagpur", "thane", "howrah", "dharavi", "bandra", "kerala", "kochi", "cochin", "goa", "assam", "guwahati",
    "odisha", "bhubaneswar", "maharashtra", "gujarat", "rajasthan", "punjab", "haryana", "uttar pradesh", "bihar",
    "west bengal", "tamil nadu", "karnataka", "telangana", "andhra", "madhya pradesh", "bhopal", "indore",
    "jharkhand", "ranchi", "chhattisgarh", "uttarakhand", "himachal", "varanasi", "agra", "amritsar", "chandigarh",
    "visakhapatnam", "vijayawada", "coimbatore", "madurai", "mysore", "mysuru", "mangalore", "ghatkopar", "kurla",
    "dadar", "andheri", "sion",
]
FOREIGN_WORDS = [
    "bangladesh", "dhaka", "chittagong", "pakistan", "karachi", "lahore", "nepal", "kathmandu", "sri lanka",
    "colombo", "bhutan", "myanmar", "burma", "china", "indonesia", "jakarta", "philippines", "manila", "thailand",
    "bangkok", "vietnam", "cambodia", "kenya", "nairobi", "nigeria", "brazil", "mexico", "peru", "egypt", "cairo",
]
NOT_PHOTOS = re.compile(r"\b(map|diagram|logo|chart|plan|route|schematic|sign|stamp|svg)\b", re.I)
FREE_LICENCE = re.compile(r"^(cc0|cc[ -]by(-sa)?( [\d.]+)?( [a-z]+)?|public domain|pd[- ].*|pd|fal|gfdl.*)$", re.I)
MIN_WIDTH = 800


def api(params):
    error = None
    for attempt in range(4):
        try:
            r = requests.get(API, params={"action": "query", "format": "json", "formatversion": 2, **params},
                             headers=HEADERS, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            error = exc
            time.sleep(3 * (attempt + 1))
    raise SystemExit(f"Wikimedia Commons request failed: {error}")


FILE_PROPS = {
    "prop": "imageinfo|coordinates|categories", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 2048,
    "cllimit": "max", "clshow": "!hidden", "iiextmetadatafilter": "LicenseShortName|Artist|DateTimeOriginal",
}


def strip_html(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def is_free(licence: str) -> bool:
    lic = licence.strip()
    return bool(FREE_LICENCE.match(lic)) and not re.search(r"\b(nc|nd)\b", lic, re.I)


def india_evidence(title: str, categories: list[str], coords) -> bool:
    """Coordinates decide when present; otherwise Indian place names without foreign ones."""
    if coords:
        return rv.in_india(coords[0]["lat"], coords[0]["lon"])
    text = " ".join([title, *categories]).lower()
    if any(re.search(rf"\b{w}\b", text) for w in FOREIGN_WORDS):
        return False
    return any(re.search(rf"\b{w}\b", text) for w in INDIA_WORDS)


def candidate(page) -> dict | None:
    """Manifest metadata for a usable Commons file page, or None."""
    info = (page.get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata", {})
    title = page.get("title", "")
    cats = [c["title"].removeprefix("Category:") for c in page.get("categories", [])]
    licence = meta.get("LicenseShortName", {}).get("value", "")
    if info.get("mime") not in ("image/jpeg", "image/png") or (info.get("width") or 0) < MIN_WIDTH:
        return None
    if NOT_PHOTOS.search(title) or not is_free(licence) or not india_evidence(title, cats, page.get("coordinates")):
        return None
    coords = page.get("coordinates")
    return {
        "source": "wikimedia",
        "source_url": info.get("descriptionurl", ""),
        "licence": licence,
        "author": strip_html(meta.get("Artist", {}).get("value", ""))[:200] or "unknown (see source page)",
        "lat": coords[0]["lat"] if coords else None,
        "lon": coords[0]["lon"] if coords else None,
        "location_source": "wikimedia",
        "captured_at": strip_html(meta.get("DateTimeOriginal", {}).get("value", ""))[:40],
        "original_name": title.removeprefix("File:"),
        "_download": info.get("thumburl") or info.get("url"),
    }


def category_pages(category, depth=1):
    cont = {}
    while True:
        data = api({"generator": "categorymembers", "gcmtitle": f"Category:{category}", "gcmtype": "file",
                    "gcmlimit": 50, **FILE_PROPS, **cont})
        yield from data.get("query", {}).get("pages", [])
        if "continue" not in data:
            break
        cont = data["continue"]
    if depth > 0:
        subs = api({"list": "categorymembers", "cmtitle": f"Category:{category}", "cmtype": "subcat", "cmlimit": 50})
        for sub in subs.get("query", {}).get("categorymembers", []):
            yield from category_pages(sub["title"].removeprefix("Category:"), depth - 1)


def search_pages(query, max_results=150):
    offset = 0
    while offset < max_results:
        data = api({"generator": "search", "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": 6,
                    "gsrlimit": 50, "gsroffset": offset, **FILE_PROPS})
        pages = data.get("query", {}).get("pages", [])
        yield from pages
        if "continue" not in data or not pages:
            break
        offset = data["continue"].get("gsroffset", offset + 50)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # photo titles in any language
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--limit", type=int, default=100, help="new photos to add")
    args = p.parse_args()

    rows = rv.read_manifest()
    known = {r["image_id"] for r in rows}
    seen = {r["original_name"] for r in rows if r["source"] == "wikimedia"}
    tmp = Path(tempfile.mkdtemp(prefix="rv_commons_"))
    added = checked = 0

    def pages():
        for cat in CATEGORIES:
            yield from category_pages(cat)
        for q in QUERIES:
            yield from search_pages(q)

    for page in pages():
        if added >= args.limit:
            break
        checked += 1
        meta = candidate(page)
        if meta is None or meta["original_name"] in seen:
            continue
        seen.add(meta["original_name"])
        url = meta.pop("_download")
        resp = requests.get(url, headers=HEADERS, timeout=120)
        if not resp.ok:
            continue
        # Thumbnail URLs carry tracking parameters (?utm_source=...): take the suffix from the path only.
        path = tmp / f"commons_{len(seen)}{Path(urlparse(url).path).suffix.lower() or '.jpg'}"
        path.write_bytes(resp.content)
        if rv.register_image(path, meta, rows, known):
            added += 1
            print(f"+ {meta['original_name'][:80]}  [{meta['licence']}]")
        time.sleep(0.2)
        if added % 20 == 0:
            rv.write_manifest(rows)

    rv.write_manifest(rows)
    print(f"\nChecked {checked} files, added {added} photos. Manifest: {len(rows)} photos.")


if __name__ == "__main__":
    main()
