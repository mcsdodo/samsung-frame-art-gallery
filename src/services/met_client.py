import logging
import time
from typing import Optional
from dataclasses import dataclass
import urllib.request
import json

_LOGGER = logging.getLogger(__name__)

MET_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"


@dataclass
class CacheEntry:
    data: any
    expires_at: float


class MetClient:
    """Client for Metropolitan Museum of Art Collection API."""

    def __init__(self):
        self._cache: dict[str, CacheEntry] = {}
        self._departments_ttl = 86400  # 24 hours
        self._objects_ttl = 3600  # 1 hour

    def _get_cached(self, key: str) -> Optional[any]:
        """Get cached value if not expired."""
        entry = self._cache.get(key)
        if entry and entry.expires_at > time.time():
            return entry.data
        return None

    def _set_cached(self, key: str, data: any, ttl: int) -> None:
        """Cache value with TTL."""
        self._cache[key] = CacheEntry(data=data, expires_at=time.time() + ttl)

    def _fetch_json(self, url: str) -> dict:
        """Fetch JSON from URL."""
        _LOGGER.debug(f"Fetching: {url}")
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode())

    def get_departments(self) -> list[dict]:
        """Get list of museum departments. Cached for 24h."""
        cache_key = "departments"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        data = self._fetch_json(f"{MET_API_BASE}/departments")
        departments = data.get("departments", [])
        self._set_cached(cache_key, departments, self._departments_ttl)
        return departments

    def get_object(self, object_id: int) -> Optional[dict]:
        """Get single object details. Cached for 1h."""
        cache_key = f"object:{object_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            data = self._fetch_json(f"{MET_API_BASE}/objects/{object_id}")
            # Only cache if has image
            if data.get("primaryImage") or data.get("primaryImageSmall"):
                self._set_cached(cache_key, data, self._objects_ttl)
            return data
        except Exception as e:
            _LOGGER.warning(f"Failed to fetch object {object_id}: {e}")
            return None

    def batch_fetch_objects(self, object_ids: list[int]) -> list[dict]:
        """Fetch multiple objects, filtering those without images."""
        results = []
        for obj_id in object_ids:
            obj = self.get_object(obj_id)
            if obj and (obj.get("primaryImage") or obj.get("primaryImageSmall")):
                # Normalize to simpler format for frontend
                primary = obj.get("primaryImage") or obj.get("primaryImageSmall")
                is_low_res = not obj.get("primaryImage")
                results.append({
                    "object_id": obj.get("objectID"),
                    "title": obj.get("title", "Untitled"),
                    "artist": obj.get("artistDisplayName", "Unknown"),
                    "date": obj.get("objectDate", ""),
                    "medium": obj.get("medium", ""),
                    "department": obj.get("department", ""),
                    "image_url": primary,
                    "image_url_small": obj.get("primaryImageSmall", primary),
                    "width": obj.get("primaryImageWidth") or 0,
                    "height": obj.get("primaryImageHeight") or 0,
                    "is_low_res": is_low_res,
                    "met_url": obj.get("objectURL", "")
                })
        return results


# Singleton instance
_client: Optional[MetClient] = None


def get_met_client() -> MetClient:
    """Get or create Met client singleton."""
    global _client
    if _client is None:
        _client = MetClient()
    return _client
