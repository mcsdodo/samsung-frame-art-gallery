# TV Thumbnails - Robust Implementation Plan

## Problem Summary

The Samsung TV thumbnail API has two versions:
- **Old API** (pre-2022 TVs, API < 4.0): `get_thumbnail()` - no SSL required
- **New API** (2022+ TVs, API >= 4.0): `get_thumbnail_list()` - requires SSL

Current quick fix uses `get_thumbnail_list()` always, which works for new TVs but:
1. May not work for older TVs
2. Concurrent requests overwhelm the TV connection
3. No caching of TV thumbnails

## Implementation Tasks

### Task 1: Add API Version Detection
**File:** `src/services/tv_client.py`

```python
class TVClient:
    def __init__(self):
        self._tv: Optional[SamsungTVWS] = None
        self._api_version: Optional[str] = None

    def get_api_version(self) -> str:
        """Get and cache TV API version."""
        if self._api_version is None:
            tv = self._get_tv()
            self._api_version = tv.art().get_api_version()
        return self._api_version

    def _is_new_api(self) -> bool:
        """Check if TV uses new API (4.0+)."""
        version = self.get_api_version()
        # Version format: "4.3.4.0" or "2.03"
        major = int(version.split('.')[0])
        return major >= 4
```

### Task 2: Smart Thumbnail Method Selection
**File:** `src/services/tv_client.py`

```python
def get_thumbnail(self, content_id: str) -> bytes:
    """Get thumbnail using appropriate API based on TV version."""
    tv = self._get_tv()

    if self._is_new_api():
        # New API requires get_thumbnail_list with SSL
        thumbnails = tv.art().get_thumbnail_list([content_id])
        if thumbnails:
            data = list(thumbnails.values())[0]
            return bytes(data) if isinstance(data, bytearray) else data
    else:
        # Old API uses get_thumbnail without SSL
        data = tv.art().get_thumbnail(content_id)
        return bytes(data) if isinstance(data, bytearray) else data

    return None
```

### Task 3: Add Request Serialization (Prevent Concurrent TV Calls)
**File:** `src/services/tv_client.py`

The TV WebSocket can't handle concurrent requests. Add a lock:

```python
import threading

class TVClient:
    def __init__(self):
        self._tv: Optional[SamsungTVWS] = None
        self._api_version: Optional[str] = None
        self._lock = threading.Lock()

    def get_thumbnail(self, content_id: str) -> bytes:
        with self._lock:
            # ... existing implementation
```

### Task 4: Add TV Thumbnail Caching
**File:** `src/services/tv_thumbnail_cache.py` (new file)

Cache TV thumbnails to avoid repeated slow TV requests:

```python
import hashlib
from pathlib import Path
from typing import Optional

CACHE_DIR = Path("/tmp/tv_thumbnails")

class TVThumbnailCache:
    def __init__(self):
        CACHE_DIR.mkdir(exist_ok=True)

    def _cache_path(self, content_id: str) -> Path:
        return CACHE_DIR / f"{content_id}.jpg"

    def get(self, content_id: str) -> Optional[bytes]:
        path = self._cache_path(content_id)
        if path.exists():
            return path.read_bytes()
        return None

    def set(self, content_id: str, data: bytes) -> None:
        self._cache_path(content_id).write_bytes(data)

    def invalidate(self, content_id: str) -> None:
        path = self._cache_path(content_id)
        if path.exists():
            path.unlink()
```

### Task 5: Integrate Caching into TV Client
**File:** `src/services/tv_client.py`

```python
from src.services.tv_thumbnail_cache import TVThumbnailCache

class TVClient:
    def __init__(self):
        # ... existing
        self._thumbnail_cache = TVThumbnailCache()

    def get_thumbnail(self, content_id: str) -> bytes:
        # Check cache first
        cached = self._thumbnail_cache.get(content_id)
        if cached:
            return cached

        # Fetch from TV
        with self._lock:
            data = self._fetch_thumbnail_from_tv(content_id)

        # Cache result
        if data:
            self._thumbnail_cache.set(content_id, data)

        return data
```

### Task 6: Add Retry Logic for Transient Failures
**File:** `src/services/tv_client.py`

```python
import time

def get_thumbnail(self, content_id: str, retries: int = 2) -> bytes:
    for attempt in range(retries + 1):
        try:
            return self._fetch_thumbnail_from_tv(content_id)
        except Exception as e:
            if attempt < retries:
                time.sleep(0.5)
                self._tv = None  # Reset connection
            else:
                raise
```

## Testing Checklist

- [ ] Thumbnails load for user-uploaded content (MY_F* IDs)
- [ ] Thumbnails load for Samsung built-in content (SAM-* IDs)
- [ ] Thumbnails load for numbered content (320* IDs)
- [ ] Multiple concurrent requests don't cause failures
- [ ] Thumbnails are cached and subsequent loads are fast
- [ ] Works after TV restart/reconnection

## Migration Notes

- The quick fix (always use `get_thumbnail_list`) should remain as fallback
- API version detection should happen once at startup and be cached
- Consider exposing API version in `/api/tv/status` for debugging
