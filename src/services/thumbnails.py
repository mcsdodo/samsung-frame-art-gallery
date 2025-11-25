import hashlib
from io import BytesIO
from pathlib import Path
from PIL import Image

THUMBNAIL_SIZE = (300, 300)
CACHE_DIR = Path("/tmp/thumbnails")


def get_cache_path(image_path: str) -> Path:
    hash_key = hashlib.md5(image_path.encode()).hexdigest()
    return CACHE_DIR / f"{hash_key}.jpg"


def generate_thumbnail(image_path: Path) -> bytes:
    cache_path = get_cache_path(str(image_path))

    # Check cache
    if cache_path.exists():
        return cache_path.read_bytes()

    # Generate thumbnail
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as img:
        img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        # Convert to RGB if needed (for JPEG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        thumbnail_data = buffer.getvalue()

    # Cache it
    cache_path.write_bytes(thumbnail_data)

    return thumbnail_data


def clear_cache():
    if CACHE_DIR.exists():
        for f in CACHE_DIR.glob("*.jpg"):
            f.unlink()
