import hashlib
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

THUMBNAIL_SIZE = (200, 200)
CACHE_DIR = Path(os.environ.get("THUMBNAILS_DIR", "/thumbnails"))
IMAGES_DIR = Path(os.environ.get("IMAGES_DIR", "/images"))
ALLOWED_EXTENSIONS = {".jpg", ".jpeg"}
MAX_WORKERS = 4


def get_dimensions_cache_path(image_path: str) -> Path:
    """Generate cache path for image dimensions JSON."""
    hash_key = hashlib.md5(f"{image_path}|dims".encode()).hexdigest()
    return CACHE_DIR / f"{hash_key}.dims"


def get_image_dimensions(image_path: Path) -> tuple[int, int]:
    """Get image dimensions, using cache if available.

    Returns: (width, height) tuple
    """
    cache_path = get_dimensions_cache_path(str(image_path))

    # Check cache first
    if cache_path.exists():
        try:
            data = cache_path.read_text()
            w, h = data.split(',')
            return (int(w), int(h))
        except Exception:
            pass  # Cache corrupted, regenerate

    # Read dimensions from image
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with Image.open(image_path) as img:
            width, height = img.size
    except Exception as e:
        logger.warning(f"Failed to read dimensions for {image_path}: {e}")
        return (0, 0)  # Frontend will fall back to 16:9

    # Cache the result
    cache_path.write_text(f"{width},{height}")

    return (width, height)


def get_cache_path(image_path: str, size: int = 200) -> Path:
    """Generate cache path using MD5 hash of image path and size."""
    hash_key = hashlib.md5(f"{image_path}|size={size}".encode()).hexdigest()
    return CACHE_DIR / f"{hash_key}.jpg"


def generate_thumbnail(image_path: Path, size: int = 200) -> bytes:
    """Generate thumbnail for a single image, using cache if available.

    Args:
        image_path: Path to the source image
        size: Maximum dimension (width or height) for the thumbnail
    """
    cache_path = get_cache_path(str(image_path), size)

    if cache_path.exists():
        return cache_path.read_bytes()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as img:
        img.thumbnail((size, size), Image.Resampling.LANCZOS)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        thumbnail_data = buffer.getvalue()

    cache_path.write_bytes(thumbnail_data)
    return thumbnail_data


def _generate_single_thumbnail(image_path: Path, size: int = 200) -> tuple[Path, bool, str]:
    """Generate thumbnail for a single image. Returns (path, success, error)."""
    try:
        generate_thumbnail(image_path, size)
        return (image_path, True, "")
    except Exception as e:
        return (image_path, False, str(e))


def get_all_images() -> list[Path]:
    """Get all valid images from the images directory."""
    if not IMAGES_DIR.exists():
        return []

    images = []
    for path in IMAGES_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            images.append(path)
    return images


def get_valid_cache_keys() -> set[str]:
    """Get set of valid cache keys for current images."""
    images = get_all_images()
    return {hashlib.md5(str(p).encode()).hexdigest() for p in images}


def cleanup_orphaned_thumbnails() -> int:
    """Remove thumbnails that no longer have corresponding source images."""
    if not CACHE_DIR.exists():
        return 0

    valid_keys = get_valid_cache_keys()
    removed = 0

    for thumb_path in CACHE_DIR.glob("*.jpg"):
        key = thumb_path.stem
        if key not in valid_keys:
            thumb_path.unlink()
            removed += 1
            logger.debug(f"Removed orphaned thumbnail: {thumb_path.name}")

    if removed:
        logger.info(f"Cleaned up {removed} orphaned thumbnails")
    return removed


def generate_missing_thumbnails() -> tuple[int, int]:
    """Generate thumbnails for images that don't have cached thumbnails.

    Returns: (generated_count, error_count)
    """
    images = get_all_images()
    missing = []

    for image_path in images:
        cache_path = get_cache_path(str(image_path))
        if not cache_path.exists():
            missing.append(image_path)

    if not missing:
        logger.info("All thumbnails are up to date")
        return (0, 0)

    logger.info(f"Generating {len(missing)} missing thumbnails...")

    generated = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_generate_single_thumbnail, p): p for p in missing}

        for future in as_completed(futures):
            path, success, error = future.result()
            if success:
                generated += 1
            else:
                errors += 1
                logger.warning(f"Failed to generate thumbnail for {path}: {error}")

    logger.info(f"Generated {generated} thumbnails ({errors} errors)")
    return (generated, errors)


def initialize_thumbnails():
    """Initialize thumbnail cache: cleanup orphans and generate missing."""
    logger.info("Initializing thumbnail cache...")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cleanup_orphaned_thumbnails()
    generated, errors = generate_missing_thumbnails()

    total_images = len(get_all_images())
    logger.info(f"Thumbnail cache ready: {total_images} images")


def clear_cache():
    """Clear all cached thumbnails."""
    if CACHE_DIR.exists():
        for f in CACHE_DIR.glob("*.jpg"):
            f.unlink()
        logger.info("Thumbnail cache cleared")
