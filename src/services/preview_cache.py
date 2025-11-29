"""Cache for processed image previews."""
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

_LOGGER = logging.getLogger(__name__)

CACHE_DIR = Path(os.environ.get("THUMBNAILS_DIR", "/thumbnails")) / "previews"


class PreviewCache:
    """Cache for processed image previews (original + processed thumbnails)."""

    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _cache_key(
        self,
        identifier: str,
        crop_percent: int,
        matte_percent: int,
        reframe_enabled: bool = False,
        reframe_offset_x: float = 0.5,
        reframe_offset_y: float = 0.5
    ) -> str:
        """Generate cache key from identifier and processing parameters."""
        key_string = f"{identifier}|crop={crop_percent}|matte={matte_percent}|reframe={reframe_enabled}|ox={reframe_offset_x:.2f}|oy={reframe_offset_y:.2f}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _original_path(self, cache_key: str) -> Path:
        return CACHE_DIR / f"{cache_key}_orig.jpg"

    def _processed_path(self, cache_key: str) -> Path:
        return CACHE_DIR / f"{cache_key}_proc.jpg"

    def get(
        self,
        identifier: str,
        crop_percent: int,
        matte_percent: int,
        reframe_enabled: bool = False,
        reframe_offset_x: float = 0.5,
        reframe_offset_y: float = 0.5
    ) -> Optional[tuple[bytes, bytes]]:
        """
        Get cached preview if available.

        Args:
            identifier: Unique identifier (file path or object ID)
            crop_percent: Crop percentage used
            matte_percent: Matte percentage used
            reframe_enabled: Whether reframe mode is enabled
            reframe_offset_x: Reframe horizontal offset (0.0-1.0)
            reframe_offset_y: Reframe vertical offset (0.0-1.0)

        Returns:
            Tuple of (original_bytes, processed_bytes) or None if not cached
        """
        cache_key = self._cache_key(
            identifier, crop_percent, matte_percent,
            reframe_enabled, reframe_offset_x, reframe_offset_y
        )
        orig_path = self._original_path(cache_key)
        proc_path = self._processed_path(cache_key)

        if orig_path.exists() and proc_path.exists():
            _LOGGER.debug(f"Preview cache hit: {identifier}")
            return orig_path.read_bytes(), proc_path.read_bytes()

        return None

    def set(
        self,
        identifier: str,
        crop_percent: int,
        matte_percent: int,
        original: bytes,
        processed: bytes,
        reframe_enabled: bool = False,
        reframe_offset_x: float = 0.5,
        reframe_offset_y: float = 0.5
    ) -> None:
        """
        Store preview in cache.

        Args:
            identifier: Unique identifier (file path or object ID)
            crop_percent: Crop percentage used
            matte_percent: Matte percentage used
            original: Original thumbnail bytes
            processed: Processed thumbnail bytes
            reframe_enabled: Whether reframe mode is enabled
            reframe_offset_x: Reframe horizontal offset (0.0-1.0)
            reframe_offset_y: Reframe vertical offset (0.0-1.0)
        """
        cache_key = self._cache_key(
            identifier, crop_percent, matte_percent,
            reframe_enabled, reframe_offset_x, reframe_offset_y
        )
        orig_path = self._original_path(cache_key)
        proc_path = self._processed_path(cache_key)

        orig_path.write_bytes(original)
        proc_path.write_bytes(processed)
        _LOGGER.debug(f"Cached preview: {identifier}")

    def invalidate(
        self,
        identifier: str,
        crop_percent: int = None,
        matte_percent: int = None,
        reframe_enabled: bool = False,
        reframe_offset_x: float = 0.5,
        reframe_offset_y: float = 0.5
    ) -> None:
        """
        Invalidate cached previews.

        If all parameters are provided, only that specific preview is removed.
        Otherwise, all previews for the identifier are removed (by pattern matching).
        """
        if crop_percent is not None and matte_percent is not None:
            cache_key = self._cache_key(
                identifier, crop_percent, matte_percent,
                reframe_enabled, reframe_offset_x, reframe_offset_y
            )
            for path in [self._original_path(cache_key), self._processed_path(cache_key)]:
                if path.exists():
                    path.unlink()
            _LOGGER.debug(f"Invalidated preview: {identifier}")
        else:
            # Can't efficiently invalidate all without tracking - just log
            _LOGGER.debug(f"Invalidate all previews for {identifier} not implemented")

    def clear(self) -> int:
        """Clear all cached previews. Returns count of files removed."""
        removed = 0
        if CACHE_DIR.exists():
            for path in CACHE_DIR.glob("*.jpg"):
                path.unlink()
                removed += 1
        _LOGGER.info(f"Cleared {removed} cached preview files")
        return removed

    def get_stats(self) -> dict:
        """Get cache statistics."""
        if not CACHE_DIR.exists():
            return {"count": 0, "size_bytes": 0}

        files = list(CACHE_DIR.glob("*.jpg"))
        total_size = sum(f.stat().st_size for f in files)

        return {
            "count": len(files) // 2,  # Pairs of orig/proc
            "size_bytes": total_size,
            "size_mb": round(total_size / (1024 * 1024), 2)
        }


# Singleton instance
_preview_cache: Optional[PreviewCache] = None


def get_preview_cache() -> PreviewCache:
    """Get the singleton preview cache instance."""
    global _preview_cache
    if _preview_cache is None:
        _preview_cache = PreviewCache()
    return _preview_cache
