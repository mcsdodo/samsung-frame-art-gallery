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
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SamsungFrameArtGallery/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
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
        """Fetch multiple objects, filtering those without images and deduplicating by image URL."""
        results = []
        seen_images = set()
        for obj_id in object_ids:
            obj = self.get_object(obj_id)
            if obj and (obj.get("primaryImage") or obj.get("primaryImageSmall")):
                # Normalize to simpler format for frontend
                primary = obj.get("primaryImage") or obj.get("primaryImageSmall")

                # Skip duplicate images (different objects can share same photo)
                if primary in seen_images:
                    continue
                seen_images.add(primary)

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

    def _get_object_ids(self, endpoint: str, cache_key: str) -> list[int]:
        """Fetch and cache object IDs from search/objects endpoint."""
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        data = self._fetch_json(endpoint)
        object_ids = data.get("objectIDs") or []
        # Cache for 1 hour
        self._set_cached(cache_key, object_ids, self._objects_ttl)
        return object_ids

    def get_highlights(self, page: int = 1, page_size: int = 24) -> dict:
        """Get highlighted artworks with images, paginated."""
        cache_key = "highlights:ids"
        url = f"{MET_API_BASE}/search?isHighlight=true&hasImages=true&q=*"
        all_ids = self._get_object_ids(url, cache_key)

        total = len(all_ids)
        start = (page - 1) * page_size
        end = start + page_size
        page_ids = all_ids[start:end]

        objects = self.batch_fetch_objects(page_ids)

        return {
            "objects": objects,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total
        }

    def get_by_department(self, department_id: int, page: int = 1, page_size: int = 24) -> dict:
        """Get artworks by department with images, paginated."""
        cache_key = f"department:{department_id}:ids"
        url = f"{MET_API_BASE}/search?departmentId={department_id}&hasImages=true&q=*"
        all_ids = self._get_object_ids(url, cache_key)

        total = len(all_ids)
        start = (page - 1) * page_size
        end = start + page_size
        page_ids = all_ids[start:end]

        objects = self.batch_fetch_objects(page_ids)

        return {
            "objects": objects,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total
        }

    def fetch_image(self, image_url: str) -> bytes:
        """Download image bytes from Met servers."""
        _LOGGER.info(f"Downloading image: {image_url}")
        req = urllib.request.Request(
            image_url,
            headers={"User-Agent": "SamsungFrameArtGallery/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read()


# Singleton instance
_client: Optional[MetClient] = None


def get_met_client() -> MetClient:
    """Get or create Met client singleton."""
    global _client
    if _client is None:
        _client = MetClient()
    return _client
