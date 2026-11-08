#!/usr/bin/env python3
"""Make full-bleed 4K Frame images from the public "popular art" list on art.framecrop.app.

The list page links public-domain originals on Wikimedia Commons. This downloads each one from
Commons, crops it to fill 3840x2160 (no borders), and saves it as "Artist - Title.jpg".
Skipped, and listed at the end: portrait works (a 16:9 crop would cut most of them away),
anything not marked public domain, and anything too small to fill 4K without upscaling.

    python3 scripts/fetch_framecrop_popular.py            # into $IMAGES_DIR/FrameCrop Popular
    python3 scripts/fetch_framecrop_popular.py --dry-run  # list what it would do

Needs Pillow (pip install Pillow).
"""
import argparse
import html
import io
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

LIST_URL = "https://art.framecrop.app/popular"
API = "https://commons.wikimedia.org/w/api.php"
UA = "samsung-frame-art-gallery/1.0 (+https://github.com/mcsdodo/samsung-frame-art-gallery)"
TV_W, TV_H = 3840, 2160
MAX_ORIGINAL_MB = 150
DEFAULT_OUT = Path(os.environ.get("IMAGES_DIR", "images")).expanduser() / "FrameCrop Popular"

Image.MAX_IMAGE_PIXELS = None  # Google Art Project scans are legitimately huge

# The list's own titles are inconsistent; these give "Artist - Title (Year)". Others fall back to the list title.
NAMES = {
    "Vincent_van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg": "Vincent van Gogh - Starry Night Over the Rhône (1888)",
    "Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg": "Vincent van Gogh - The Starry Night (1889)",
    "Bruno_Moras_-_Winterlandschaft_im_Gebirge.jpg": "Bruno Moras - Winter Landscape in the Mountains",
    "Nighthawks_by_Edward_Hopper_1942.jpg": "Edward Hopper - Nighthawks (1942)",
    "The_Great_Wave_off_Kanagawa.jpg": "Katsushika Hokusai - The Great Wave off Kanagawa (c. 1831)",
    "Albert_Bierstadt_-_Among_the_Sierra_Nevada,_California_-_Google_Art_Project.jpg": "Albert Bierstadt - Among the Sierra Nevada, California (1868)",
    "Amandelbloesem_-_s0176V1962_-_Van_Gogh_Museum.jpg": "Vincent van Gogh - Almond Blossom (1890)",
    "Claude_Monet_-_The_Magpie_-_Google_Art_Project.jpg": "Claude Monet - The Magpie (1868-69)",
    "Vincent_van_Gogh_-_Landscape_from_Saint-Rémy_-_Google_Art_Project.jpg": "Vincent van Gogh - Landscape from Saint-Rémy (1889)",
    "Monet_-_Impression,_Sunrise.jpg": "Claude Monet - Impression, Sunrise (1872)",
    "Kandinsky_-_Composition_8,_July_1923.jpg": "Wassily Kandinsky - Composition VIII (1923)",
    "Claude_Monet_-_Jardin_à_Sainte-Adresse.jpg": "Claude Monet - Garden at Sainte-Adresse (1867)",
    "Monet_Snow_at_Argenteuil_1875.jpg": "Claude Monet - Snow at Argenteuil (1875)",
}
# Matched on the list title when the Commons file name is long or unusual.
TITLE_NAMES = {
    'Detail of the painting "View of Bazincourt, Sunset" by Camille Pissarro': "Camille Pissarro - View of Bazincourt, Sunset (1892, detail)",
    "Vincent van Gogh - Wheat Field with Cypresses (National Gallery version)": "Vincent van Gogh - Wheat Field with Cypresses (1889)",
    "Leonardo da Vinci (1452-1519) - The Last Supper (1495-1498)": "Leonardo da Vinci - The Last Supper (1495-98)",
    "Farmhouse in Provence, 1888, Vincent van Gogh, NGA": "Vincent van Gogh - Farmhouse in Provence (1888)",
    "Camille Pissarro, The Boulevard Montmartre at Night, 1897": "Camille Pissarro - The Boulevard Montmartre at Night (1897)",
    "Low Tide at Pourville, by Claude Monet, Cleveland Museum of Art, 1947.196": "Claude Monet - Low Tide at Pourville (1882)",
    "Claude Monet, The Water-Lily Pond (National Gallery, London)": "Claude Monet - The Water-Lily Pond (1899)",
    "Washington Crossing the Delaware by Emanuel Leutze, MMA-NYC, 1851": "Emanuel Leutze - Washington Crossing the Delaware (1851)",
    "H. A. Brendekilde - A wooded path in autumn (1902)": "H. A. Brendekilde - A Wooded Path in Autumn (1902)",
    "Harald Sohlberg - Street in Røros in Winter": "Harald Sohlberg - Street in Røros in Winter (1903)",
}


def get(url, tries=4):
    for attempt in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=300)
        except urllib.error.HTTPError as e:  # Wikimedia rate-limits bursts; wait as long as it asks
            if e.code != 429 or attempt == tries - 1:
                raise
            time.sleep(int(e.headers.get("Retry-After") or 0) or 10 * (attempt + 1))


def list_artworks():
    """(commons file name, display title) pairs from the public list page, in page order."""
    page = get(LIST_URL).read().decode()
    found = {}
    for tag in re.findall(r"<img[^>]+image-proxy[^>]+>", page):
        src = re.search(r'image-proxy\?url=([^"&]+)', tag).group(1)
        alt = (re.search(r'alt="([^"]*)"', tag) or [None, ""])[1]
        url = urllib.parse.unquote(html.unescape(src)).split("?")[0]
        parts = url.split("/")
        name = parts[parts.index("thumb") + 3] if "/commons/thumb/" in url else parts[-1]
        found.setdefault(urllib.parse.unquote(name), html.unescape(alt))
    return list(found.items())


def commons_info(files):
    info = {}
    for i in range(0, len(files), 50):
        data = json.load(get(API + "?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "prop": "imageinfo",
            "titles": "|".join("File:" + f for f in files[i:i + 50]),
            "iiprop": "size|url|mime|extmetadata", "iiextmetadatafilter": "LicenseShortName",
        })))
        for p in data["query"]["pages"].values():
            if "imageinfo" in p:
                info[p["title"][5:]] = p["imageinfo"][0]  # normalised: spaces, not underscores
    return info


def scaled_url(file_name, width):
    data = json.load(get(API + "?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "prop": "imageinfo",
        "titles": "File:" + file_name, "iiprop": "url", "iiurlwidth": width,
    })))
    return next(iter(data["query"]["pages"].values()))["imageinfo"][0].get("thumburl")


def nice_name(title):
    title = re.sub(r"\s*-\s*(Google Art Project|Van Gogh Museum|Detroit Institute of Arts)\b.*$", "", title)
    title = re.sub(r"\s*-\s*s\d{4}V\d{4}\s*", " ", title)  # museum inventory codes
    title = re.sub(r'[\\/:*?"<>|]+', "", title).strip(" -.")
    return title[:140] + ".jpg"


def fill_crop(img):
    scale = max(TV_W / img.width, TV_H / img.height)
    img = img.resize((math.ceil(img.width * scale), math.ceil(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - TV_W) // 2, (img.height - TV_H) // 2
    return img.crop((left, top, left + TV_W, top + TV_H))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    artworks = list_artworks()
    info = commons_info([f for f, _ in artworks])
    print(f"{len(artworks)} artworks on the list\n")
    args.out.mkdir(parents=True, exist_ok=True)
    skipped, made, seen = [], 0, set()

    for file_name, alt in artworks:
        ii = info.get(file_name.replace("_", " "))
        title = alt or file_name.rsplit(".", 1)[0].replace("_", " ")
        if not ii:
            skipped.append((title, "not found on Commons")); continue
        w, h = ii["width"], ii["height"]
        licence = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
        if not re.search(r"public domain|^PD|CC0", licence, re.I):
            skipped.append((title, f"licence is {licence or 'unknown'}")); continue
        if h > w:
            skipped.append((title, f"portrait {w}x{h}")); continue
        if w < TV_W or h < TV_H or (w / h > TV_W / TV_H and h < TV_H):
            skipped.append((title, f"too small for 4K ({w}x{h})")); continue
        fixed = NAMES.get(file_name) or TITLE_NAMES.get(title)
        name = fixed + ".jpg" if fixed else nice_name(title)
        if name.lower() in seen:
            skipped.append((title, "duplicate of another file")); continue
        seen.add(name.lower())
        dest = args.out / name
        if dest.exists():
            print(f"  exists   {name}"); continue
        if args.dry_run:
            print(f"  would make {name}  (from {w}x{h})"); continue

        need_w = math.ceil(max(TV_W, TV_H * w / h))
        url = scaled_url(file_name, need_w) if need_w < w else None
        if not url:
            if ii.get("size", 0) / 1e6 > MAX_ORIGINAL_MB:
                skipped.append((title, f"original is {ii['size'] / 1e6:.0f} MB")); continue
            url = ii["url"]
        try:
            img = Image.open(io.BytesIO(get(url).read()))
            img.load()
        except Exception as e:  # a non-standard thumbnail width can be refused; fall back to the original
            if url == ii["url"]:
                skipped.append((title, f"download failed: {e}")); continue
            img = Image.open(io.BytesIO(get(ii["url"]).read()))
        if img.width < TV_W or img.height < TV_H:
            img = Image.open(io.BytesIO(get(ii["url"]).read()))
        icc = img.info.get("icc_profile")
        fill_crop(img.convert("RGB")).save(dest, "JPEG", quality=92, optimize=True, icc_profile=icc)
        with open(args.out / "CREDITS.tsv", "a") as f:
            f.write(f"{name}\t{licence}\t{ii['descriptionurl']}\n")
        made += 1
        print(f"  made     {name}")
        time.sleep(2)  # stay well under Wikimedia's rate limit

    print(f"\n{made} new 3840x2160 images in {args.out}")
    if skipped:
        print(f"\nSkipped {len(skipped)}:")
        for t, why in skipped:
            print(f"  - {t}: {why}")


if __name__ == "__main__":
    main()
