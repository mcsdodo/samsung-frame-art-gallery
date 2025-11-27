import logging
from pathlib import Path
from typing import Optional

_LOGGER = logging.getLogger(__name__)

CACHE_DIR = Path("/tmp/tv_thumbnails")


class TVThumbnailCache:
    def __init__(self):
        CACHE_DIR.mkdir(exist_ok=True)

    def _cache_path(self, content_id: str) -> Path:
        # Sanitize content_id for safe filename
        safe_id = content_id.replace("/", "_").replace("\\", "_")
        return CACHE_DIR / f"{safe_id}.jpg"

    def get(self, content_id: str) -> Optional[bytes]:
        path = self._cache_path(content_id)
        if path.exists():
            _LOGGER.debug(f"Cache hit for thumbnail: {content_id}")
            return path.read_bytes()
        return None

    def set(self, content_id: str, data: bytes) -> None:
        path = self._cache_path(content_id)
        path.write_bytes(data)
        _LOGGER.debug(f"Cached thumbnail: {content_id}")

    def invalidate(self, content_id: str) -> None:
        path = self._cache_path(content_id)
        if path.exists():
            path.unlink()
            _LOGGER.debug(f"Invalidated cache for: {content_id}")

    def clear(self) -> None:
        """Clear all cached thumbnails."""
        for path in CACHE_DIR.glob("*.jpg"):
            path.unlink()
        _LOGGER.info("Cleared all thumbnail cache")

    def cleanup_orphaned(self, valid_content_ids: set[str]) -> int:
        """Remove cached thumbnails that are no longer on the TV.
        
        Args:
            valid_content_ids: Set of content_ids currently on the TV
            
        Returns:
            Number of orphaned thumbnails removed
        """
        removed = 0
        for path in CACHE_DIR.glob("*.jpg"):
            # Extract content_id from filename (reverse of _cache_path sanitization)
            cached_id = path.stem.replace("_", "/")
            # Also try without replacement in case content_id had no slashes
            if cached_id not in valid_content_ids and path.stem not in valid_content_ids:
                path.unlink()
                removed += 1
                _LOGGER.debug(f"Removed orphaned thumbnail: {path.stem}")
        
        if removed:
            _LOGGER.info(f"Cleaned up {removed} orphaned TV thumbnail(s)")
        return removed
