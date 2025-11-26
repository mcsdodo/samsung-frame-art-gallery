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


# Singleton instance
_client: Optional[MetClient] = None


def get_met_client() -> MetClient:
    """Get or create Met client singleton."""
    global _client
    if _client is None:
        _client = MetClient()
    return _client
