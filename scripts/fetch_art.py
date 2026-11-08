#!/usr/bin/env python3
"""Download public-domain 4K artwork from Wikimedia Commons for the Frame gallery.

Searches the Google Art Project scans on Commons (or all of Commons with --all-commons),
keeps only public-domain images large enough to fill a 3840x2160 screen without upscaling,
and saves them to $IMAGES_DIR (default ./images), where the gallery's Local Images tab picks them up.

    python3 scripts/fetch_art.py monet
    python3 scripts/fetch_art.py "great wave" --limit 10
    python3 scripts/fetch_art.py hokusai --portrait --all
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
UA = "samsung-frame-art-gallery/1.0 (+https://github.com/mcsdodo/samsung-frame-art-gallery)"
TV_W, TV_H = 3840, 2160
DEFAULT_OUT = Path(os.environ.get("IMAGES_DIR", "images")).expanduser()
MAX_ORIGINAL_MB = 80  # only fetched for panoramas wider than 16:9


def get(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=120)


def search(query, all_commons, want, landscape):
    scope = "" if all_commons else 'intitle:"Google Art Project" '
    results, seen, offset = [], set(), 0
    while len(results) < want and offset is not None and offset < 500:
        data = json.load(get(API, {
            "action": "query", "format": "json", "generator": "search",
            "gsrnamespace": 6, "gsrlimit": 50, "gsroffset": offset,
            "gsrsearch": f"{scope}{query} filetype:bitmap filew:>{TV_W - 1} fileh:>{TV_H - 1}",
            "prop": "imageinfo", "iiprop": "size|url|extmetadata|mime",
            "iiurlwidth": TV_W, "iiextmetadatafilter": "LicenseShortName",
        }))
        offset = data.get("continue", {}).get("gsroffset")
        pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
        for p in pages:
            ii = p["imageinfo"][0]
            w, h = ii["width"], ii["height"]
            licence = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
            title = clean_title(p["title"])
            if w < TV_W or h < TV_H or ii.get("mime") != "image/jpeg":
                continue
            if not re.search(r"public domain|^PD|CC0", licence, re.I):
                continue
            if landscape and w < h:
                continue
            if title.lower() in seen:
                continue
            seen.add(title.lower())
            # A 3840-wide copy is 4K-tall enough unless the image is wider than 16:9.
            thumb_ok = ii.get("thumburl") and ii.get("thumbheight", 0) >= TV_H
            results.append({
                "title": title, "w": w, "h": h, "licence": licence,
                "page": ii["descriptionurl"],
                "url": ii["thumburl"] if thumb_ok else ii["url"],
                "mb": ii["size"] / 1e6 if not thumb_ok else None,
            })
            if len(results) >= want:
                break
    return results


def clean_title(file_title):
    name = re.sub(r"^File:", "", file_title)
    name = re.sub(r"\.jpe?g$", "", name, flags=re.I)
    return re.sub(r"\s*-\s*Google Art Project.*$", "", name).strip()


def safe_name(title):
    return re.sub(r'[\\/:*?"<>|]+', "", title)[:150].strip() + ".jpg"


def pick(results):
    raw = input("\nDownload which? (e.g. 1,3,5-8, 'all', or empty to quit): ").strip().lower()
    if not raw:
        return []
    if raw == "all":
        return results
    chosen = set()
    for part in raw.split(","):
        a, _, b = part.strip().partition("-")
        chosen.update(range(int(a), int(b or a) + 1))
    return [r for i, r in enumerate(results, 1) if i in chosen]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", help="artist, title or subject, e.g. monet, 'great wave', seascape")
    ap.add_argument("--limit", type=int, default=20, help="results to list (default 20)")
    ap.add_argument("--portrait", action="store_true", help="include portrait images (default: landscape only)")
    ap.add_argument("--all-commons", action="store_true", help="search all of Commons, not just Google Art Project scans")
    ap.add_argument("--all", action="store_true", help="download every result without asking")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output folder (default {DEFAULT_OUT})")
    args = ap.parse_args()

    results = search(args.query, args.all_commons, args.limit, landscape=not args.portrait)
    if not results:
        sys.exit("No public-domain 4K matches. Try another query, --portrait, or --all-commons.")
    for i, r in enumerate(results, 1):
        print(f"{i:3}. {r['title'][:90]}  ({r['w']}x{r['h']})")

    if args.all:
        chosen = results
    elif sys.stdin.isatty():
        chosen = pick(results)
    else:
        sys.exit("\nNot a terminal, so nothing downloaded. Re-run with --all to download these.")
    args.out.mkdir(parents=True, exist_ok=True)
    credits = args.out / "CREDITS.tsv"
    for r in chosen:
        dest = args.out / safe_name(r["title"])
        if dest.exists():
            print(f"  skip (already there): {dest.name}")
            continue
        if r["mb"] and r["mb"] > MAX_ORIGINAL_MB:
            print(f"  skip (original is {r['mb']:.0f} MB): {r['title']}")
            continue
        print(f"  downloading: {dest.name}")
        tmp = dest.with_suffix(".part")
        with get(r["url"]) as resp, open(tmp, "wb") as f:
            while chunk := resp.read(1 << 20):
                f.write(chunk)
        tmp.rename(dest)
        with open(credits, "a") as f:
            f.write(f"{dest.name}\t{r['licence']}\t{r['page']}\n")
    print(f"\nDone. Images are in {args.out}; open the gallery's Local Images tab to upload them.")


if __name__ == "__main__":
    main()
