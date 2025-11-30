import asyncio
import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import urllib.request
import json

_LOGGER = logging.getLogger(__name__)

MET_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
MET_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DIMENSIONS_CACHE_DIR = Path(os.environ.get("THUMBNAILS_DIR", "/thumbnails")) / "met_dims"


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
            headers={
                "User-Agent": MET_USER_AGENT,
                "Accept": "application/json",
            }
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

    def get_object(self, object_id: int, retries: int = 3) -> Optional[dict]:
        """Get single object details. Cached for 1h. Retries with backoff on 429."""
        cache_key = f"object:{object_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        url = f"{MET_API_BASE}/objects/{object_id}"

        for attempt in range(retries):
            try:
                data = self._fetch_json(url)
                # Only cache if has image
                if data.get("primaryImage") or data.get("primaryImageSmall"):
                    self._set_cached(cache_key, data, self._objects_ttl)
                return data
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < retries - 1:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    _LOGGER.warning(f"Rate limited on object {object_id}, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                _LOGGER.warning(f"HTTP error fetching object {object_id}: {e}")
                return None
            except Exception as e:
                _LOGGER.warning(f"Failed to fetch object {object_id}: {e}")
                return None
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
                width = obj.get("primaryImageWidth") or 0
                height = obj.get("primaryImageHeight") or 0

                # Skip dimension fetching during list - frontend uses 16:9 fallback
                results.append({
                    "object_id": obj.get("objectID"),
                    "title": obj.get("title", "Untitled"),
                    "artist": obj.get("artistDisplayName", "Unknown"),
                    "date": obj.get("objectDate", ""),
                    "medium": obj.get("medium", ""),
                    "department": obj.get("department", ""),
                    "image_url": primary,
                    "image_url_small": obj.get("primaryImageSmall", primary),
                    "width": width,
                    "height": height,
                    "is_low_res": is_low_res,
                    "met_url": obj.get("objectURL", "")
                })
        return results

    def _normalize_object(self, obj: dict, fetch_missing_dims: bool = False) -> Optional[dict]:
        """Normalize raw API object to frontend format. Returns None if no image.

        Args:
            obj: Raw object from Met API
            fetch_missing_dims: If True, fetch dimensions for objects without them (slow).
                              If False, return 0,0 and let frontend use fallback ratio.
        """
        if not obj or not (obj.get("primaryImage") or obj.get("primaryImageSmall")):
            return None

        primary = obj.get("primaryImage") or obj.get("primaryImageSmall")
        is_low_res = not obj.get("primaryImage")
        width = obj.get("primaryImageWidth") or 0
        height = obj.get("primaryImageHeight") or 0

        # Optionally fetch dimensions from image header if not provided by API
        if fetch_missing_dims and (width == 0 or height == 0):
            small_url = obj.get("primaryImageSmall", primary)
            width, height = self.fetch_image_dimensions(small_url)

        return {
            "object_id": obj.get("objectID"),
            "title": obj.get("title", "Untitled"),
            "artist": obj.get("artistDisplayName", "Unknown"),
            "date": obj.get("objectDate", ""),
            "medium": obj.get("medium", ""),
            "department": obj.get("department", ""),
            "image_url": primary,
            "image_url_small": obj.get("primaryImageSmall", primary),
            "width": width,
            "height": height,
            "is_low_res": is_low_res,
            "met_url": obj.get("objectURL", "")
        }

    async def batch_fetch_objects_async(self, object_ids: list[int], max_concurrent: int = 5) -> list[dict]:
        """Fetch objects in parallel with concurrency limit."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_one(obj_id: int) -> Optional[dict]:
            async with semaphore:
                return await asyncio.to_thread(self.get_object, obj_id)

        # Fetch all objects in parallel
        tasks = [fetch_one(obj_id) for obj_id in object_ids]
        raw_objects = await asyncio.gather(*tasks)

        # Normalize and deduplicate
        results = []
        seen_images = set()
        for obj in raw_objects:
            normalized = self._normalize_object(obj)
            if normalized:
                img_url = normalized["image_url"]
                if img_url not in seen_images:
                    seen_images.add(img_url)
                    results.append(normalized)

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

    def get_highlights(self, page: int = 1, page_size: int = 24, medium: Optional[str] = None) -> dict:
        """Get highlighted artworks with images, paginated."""
        if medium:
            cache_key = f"highlights:{medium}:ids"
            url = f"{MET_API_BASE}/search?isHighlight=true&hasImages=true&medium={medium}&q=*"
        else:
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

    def get_by_medium(self, medium: str, page: int = 1, page_size: int = 24, highlights_only: bool = False) -> dict:
        """Get artworks by medium (e.g., Paintings, Sculpture), paginated."""
        import urllib.parse
        encoded_medium = urllib.parse.quote(medium)

        highlight_suffix = ":highlights" if highlights_only else ""
        cache_key = f"medium:{medium}{highlight_suffix}:ids"

        highlight_param = "&isHighlight=true" if highlights_only else ""
        url = f"{MET_API_BASE}/search?hasImages=true&medium={encoded_medium}{highlight_param}&q=*"
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

    def get_by_department(self, department_id: int, page: int = 1, page_size: int = 24, highlights_only: bool = False) -> dict:
        """Get artworks by department with images, paginated."""
        highlight_suffix = ":highlights" if highlights_only else ""
        cache_key = f"department:{department_id}{highlight_suffix}:ids"

        highlight_param = "&isHighlight=true" if highlights_only else ""
        url = f"{MET_API_BASE}/search?departmentId={department_id}&hasImages=true{highlight_param}&q=*"
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

    def search(self, query: str, department_id: Optional[int] = None, medium: Optional[str] = None, highlights_only: bool = False, page: int = 1, page_size: int = 24) -> dict:
        """Search artworks by keyword, optionally filtered by department, medium, or highlights."""
        import urllib.parse
        encoded_query = urllib.parse.quote(query)

        # Build cache key and URL
        # IMPORTANT: q parameter must come LAST for Met API to work correctly
        params = ["hasImages=true"]
        cache_parts = [f"search:{query}"]

        if department_id:
            params.append(f"departmentId={department_id}")
            cache_parts.append(f"dept:{department_id}")
        if medium:
            encoded_medium = urllib.parse.quote(medium)
            params.append(f"medium={encoded_medium}")
            cache_parts.append(f"medium:{medium}")
        if highlights_only:
            params.append("isHighlight=true")
            cache_parts.append("highlights")

        # q must be last
        params.append(f"q={encoded_query}")

        cache_key = ":".join(cache_parts) + ":ids"
        url = f"{MET_API_BASE}/search?" + "&".join(params)

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
            "has_more": end < total,
            "query": query
        }

    # Async versions for parallel fetching
    async def get_highlights_async(self, page: int = 1, page_size: int = 24, medium: Optional[str] = None) -> dict:
        """Get highlighted artworks with images, paginated (async parallel fetch)."""
        if medium:
            cache_key = f"highlights:{medium}:ids"
            url = f"{MET_API_BASE}/search?isHighlight=true&hasImages=true&medium={medium}&q=*"
        else:
            cache_key = "highlights:ids"
            url = f"{MET_API_BASE}/search?isHighlight=true&hasImages=true&q=*"

        all_ids = await asyncio.to_thread(self._get_object_ids, url, cache_key)
        total = len(all_ids)
        start = (page - 1) * page_size
        end = start + page_size
        page_ids = all_ids[start:end]

        objects = await self.batch_fetch_objects_async(page_ids)

        return {
            "objects": objects,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total
        }

    async def get_by_medium_async(self, medium: str, page: int = 1, page_size: int = 24, highlights_only: bool = False) -> dict:
        """Get artworks by medium, paginated (async parallel fetch)."""
        import urllib.parse
        encoded_medium = urllib.parse.quote(medium)

        highlight_suffix = ":highlights" if highlights_only else ""
        cache_key = f"medium:{medium}{highlight_suffix}:ids"

        highlight_param = "&isHighlight=true" if highlights_only else ""
        url = f"{MET_API_BASE}/search?hasImages=true&medium={encoded_medium}{highlight_param}&q=*"

        all_ids = await asyncio.to_thread(self._get_object_ids, url, cache_key)
        total = len(all_ids)
        start = (page - 1) * page_size
        end = start + page_size
        page_ids = all_ids[start:end]

        objects = await self.batch_fetch_objects_async(page_ids)

        return {
            "objects": objects,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total
        }

    async def get_by_department_async(self, department_id: int, page: int = 1, page_size: int = 24, highlights_only: bool = False) -> dict:
        """Get artworks by department, paginated (async parallel fetch)."""
        highlight_suffix = ":highlights" if highlights_only else ""
        cache_key = f"department:{department_id}{highlight_suffix}:ids"

        highlight_param = "&isHighlight=true" if highlights_only else ""
        url = f"{MET_API_BASE}/search?departmentId={department_id}&hasImages=true{highlight_param}&q=*"

        all_ids = await asyncio.to_thread(self._get_object_ids, url, cache_key)
        total = len(all_ids)
        start = (page - 1) * page_size
        end = start + page_size
        page_ids = all_ids[start:end]

        objects = await self.batch_fetch_objects_async(page_ids)

        return {
            "objects": objects,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total
        }

    async def search_async(self, query: str, department_id: Optional[int] = None, medium: Optional[str] = None, highlights_only: bool = False, page: int = 1, page_size: int = 24) -> dict:
        """Search artworks by keyword (async parallel fetch)."""
        import urllib.parse
        encoded_query = urllib.parse.quote(query)

        params = ["hasImages=true"]
        cache_parts = [f"search:{query}"]

        if department_id:
            params.append(f"departmentId={department_id}")
            cache_parts.append(f"dept:{department_id}")
        if medium:
            encoded_medium = urllib.parse.quote(medium)
            params.append(f"medium={encoded_medium}")
            cache_parts.append(f"medium:{medium}")
        if highlights_only:
            params.append("isHighlight=true")
            cache_parts.append("highlights")

        params.append(f"q={encoded_query}")
        cache_key = ":".join(cache_parts) + ":ids"
        url = f"{MET_API_BASE}/search?" + "&".join(params)

        all_ids = await asyncio.to_thread(self._get_object_ids, url, cache_key)
        total = len(all_ids)
        start = (page - 1) * page_size
        end = start + page_size
        page_ids = all_ids[start:end]

        objects = await self.batch_fetch_objects_async(page_ids)

        return {
            "objects": objects,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total,
            "query": query
        }

    def fetch_image(self, image_url: str) -> bytes:
        """Download image bytes from Met servers."""
        import urllib.parse

        # URL-encode path to handle spaces and special chars
        parsed = urllib.parse.urlparse(image_url)
        encoded_path = urllib.parse.quote(parsed.path)
        encoded_url = urllib.parse.urlunparse(parsed._replace(path=encoded_path))

        _LOGGER.info(f"Downloading image: {encoded_url}")
        req = urllib.request.Request(
            encoded_url,
            headers={
                "User-Agent": MET_USER_AGENT,
                "Accept": "image/*",
            }
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read()

    def _get_cached_dimensions(self, image_url: str) -> Optional[tuple[int, int]]:
        """Get cached dimensions from disk."""
        cache_file = DIMENSIONS_CACHE_DIR / f"{hashlib.md5(image_url.encode()).hexdigest()}.dims"
        if cache_file.exists():
            try:
                w, h = cache_file.read_text().split(',')
                return (int(w), int(h))
            except Exception:
                pass
        return None

    def _cache_dimensions(self, image_url: str, width: int, height: int) -> None:
        """Cache dimensions to disk."""
        DIMENSIONS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = DIMENSIONS_CACHE_DIR / f"{hashlib.md5(image_url.encode()).hexdigest()}.dims"
        cache_file.write_text(f"{width},{height}")

    def fetch_image_dimensions(self, image_url: str) -> tuple[int, int]:
        """Fetch image dimensions by reading just the header bytes.

        Returns: (width, height) tuple, or (0, 0) on failure.
        Uses persistent disk cache to avoid re-fetching.
        """
        # Check disk cache first
        cached = self._get_cached_dimensions(image_url)
        if cached:
            return cached

        try:
            from PIL import Image
            from io import BytesIO
            import urllib.parse

            # URL-encode path to handle spaces and special chars
            parsed = urllib.parse.urlparse(image_url)
            encoded_path = urllib.parse.quote(parsed.path)
            encoded_url = urllib.parse.urlunparse(parsed._replace(path=encoded_path))

            _LOGGER.debug(f"Fetching dimensions for: {encoded_url}")
            req = urllib.request.Request(
                encoded_url,
                headers={
                    "User-Agent": MET_USER_AGENT,
                    "Accept": "image/*",
                    "Range": "bytes=0-65535",  # First 64KB usually contains header
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                header_bytes = response.read()

            # PIL can read dimensions from partial data
            with Image.open(BytesIO(header_bytes)) as img:
                width, height = img.size

            # Cache to disk for future use
            self._cache_dimensions(image_url, width, height)
            return (width, height)
        except Exception as e:
            _LOGGER.warning(f"Failed to fetch dimensions for {image_url}: {e}")
            return (0, 0)


# Singleton instance
_client: Optional[MetClient] = None


def get_met_client() -> MetClient:
    """Get or create Met client singleton."""
    global _client
    if _client is None:
        _client = MetClient()
    return _client
