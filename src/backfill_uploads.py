"""One-off: match artwork already on the TV to local files by thumbnail similarity, and record it.

Uploads made before the upload record existed have no link back to their file. Run inside the
container:  python -m src.backfill_uploads [--apply]
Without --apply it only prints the proposed matches.
"""
import io
import os
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

from src.services import upload_registry
from src.services.tv_client import TVClient

IMAGES_DIR = Path(os.environ.get("IMAGES_DIR", "/images"))
SIZE = (48, 27)
MAX_DIFF = 18  # mean absolute grey-level difference, 0-255
MIN_MARGIN = 4  # best match must beat the runner-up by this much


def trim_white(img):
    """Old uploads were padded with a white matte; compare the picture, not the matte."""
    grey = img.convert("L")
    bbox = ImageChops.difference(grey, Image.new("L", grey.size, 255)).point(lambda v: 255 if v > 12 else 0).getbbox()
    return img.crop(bbox) if bbox else img


def signature(img):
    return list(img.convert("L").resize(SIZE, Image.LANCZOS).get_flattened_data())


def variants(img):
    """What an upload of this file can look like: filled to 16:9, or edge-cropped then matted."""
    yield list(ImageOps.fit(img.convert("L"), SIZE, Image.LANCZOS).get_flattened_data())
    w, h = img.size
    for pct in (0, 5, 10):
        dx, dy = int(w * pct / 100), int(h * pct / 100)
        yield signature(img.crop((dx, dy, w - dx, h - dy)))


def diff(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def local_signatures():
    sigs = {}
    for path in sorted(IMAGES_DIR.rglob("*")):
        if path.suffix.lower() not in (".jpg", ".jpeg") or not path.is_file():
            continue
        img = Image.open(path)
        img.draft("RGB", (400, 400))
        img = ImageOps.exif_transpose(img).convert("RGB")
        sigs[str(path.relative_to(IMAGES_DIR))] = list(variants(img))
    return sigs


def main():
    apply = "--apply" in sys.argv
    client = TVClient.initialize_from_settings()
    if client is None:
        sys.exit("No TV configured")
    known = upload_registry.load()
    artwork = [a for a in client.get_artwork_list()
               if a["content_id"].startswith("MY_") and a["content_id"] not in known]
    print(f"{len(artwork)} uploaded artworks with no recorded source")
    locals_ = local_signatures()

    matched = 0
    for art in sorted(artwork, key=lambda a: a.get("image_date", "")):
        cid = art["content_id"]
        try:
            thumb = Image.open(io.BytesIO(client.get_thumbnail(cid))).convert("RGB")
        except Exception as e:
            print(f"  {cid}: no thumbnail ({e})")
            continue
        sig = signature(trim_white(thumb))
        ranked = sorted((min(diff(sig, v) for v in vs), p) for p, vs in locals_.items())
        (best, path), runner_up = ranked[0], ranked[1][0] if len(ranked) > 1 else 255
        ok = best <= MAX_DIFF and runner_up - best >= MIN_MARGIN
        print(f"  {cid}  {'MATCH' if ok else 'skip '}  {best:5.1f} (next {runner_up:5.1f})  {path}")
        if ok:
            matched += 1
            if apply:
                upload_registry.record(cid, path)
    print(f"\n{matched} matched" + ("" if apply else "; re-run with --apply to save them"))


if __name__ == "__main__":
    main()
