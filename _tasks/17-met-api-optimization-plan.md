# Met API Performance Optimization Plan

**Goal:** Speed up Met Museum API calls from ~4-6s to ~1-2s per page load.

**Files to modify:**
- `src/services/met_client.py` - Core optimizations
- `src/api/met.py` - Use small images for previews

---

## Task 1: Remove sleep, add exponential backoff on 429

**File:** `src/services/met_client.py`

Remove `time.sleep(0.1)` from `get_object()`. Add retry logic with exponential backoff only when we receive HTTP 429.

```python
def get_object(self, object_id: int, retries: int = 3) -> dict | None:
    """Fetch single object metadata with exponential backoff on rate limit."""
    cache_key = f"object_{object_id}"
    if cache_key in self._cache:
        return self._cache[cache_key]

    url = f"{MET_API_BASE}/objects/{object_id}"

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": MET_USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as response:
                obj = json.loads(response.read().decode())
                self._cache[cache_key] = obj
                return obj
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                _LOGGER.warning(f"Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            _LOGGER.warning(f"Failed to fetch object {object_id}: {e}")
            return None
    return None
```

**Savings:** ~2.4s per 24-item page

---

## Task 2: Parallel object fetching with semaphore

**File:** `src/services/met_client.py`

Replace sequential `batch_fetch_objects()` with async parallel fetching using semaphore to limit concurrent requests.

Add async method:
```python
async def batch_fetch_objects_async(self, object_ids: list[int], max_concurrent: int = 5) -> list[dict]:
    """Fetch objects in parallel with concurrency limit."""
    import asyncio

    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(obj_id: int) -> dict | None:
        async with semaphore:
            return await asyncio.to_thread(self.get_object, obj_id)

    tasks = [fetch_one(obj_id) for obj_id in object_ids]
    results = await asyncio.gather(*tasks)

    # Process results (add dimensions, normalize)
    processed = []
    for obj in results:
        if obj and obj.get("primaryImage"):
            # ... existing normalization logic
            processed.append(normalized)
    return processed
```

Update API endpoints to use async version.

**Savings:** ~1-2s (round-trip overhead reduction)

---

## Task 3: Use primaryImageSmall for previews

**File:** `src/api/met.py`

In `generate_preview()` endpoint, use the smaller image URL for preview generation instead of full resolution.

Change:
```python
image_url = obj.get("primaryImage") or obj.get("primaryImageSmall")
```

To:
```python
# Use small image for preview (faster download), full image only for upload
image_url = obj.get("primaryImageSmall") or obj.get("primaryImage")
```

Keep full image for `/upload` endpoint where quality matters.

**Savings:** ~1-3s per preview (smaller downloads)

---

## Task 4: Persist dimension cache

**File:** `src/services/met_client.py`

Cache fetched dimensions to disk so they persist across restarts.

```python
DIMENSIONS_CACHE_DIR = Path(os.environ.get("THUMBNAILS_DIR", "/thumbnails")) / "met_dims"

def _get_cached_dimensions(self, image_url: str) -> tuple[int, int] | None:
    cache_file = DIMENSIONS_CACHE_DIR / f"{hashlib.md5(image_url.encode()).hexdigest()}.dims"
    if cache_file.exists():
        try:
            w, h = cache_file.read_text().split(',')
            return (int(w), int(h))
        except:
            pass
    return None

def _cache_dimensions(self, image_url: str, width: int, height: int) -> None:
    DIMENSIONS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = DIMENSIONS_CACHE_DIR / f"{hashlib.md5(image_url.encode()).hexdigest()}.dims"
    cache_file.write_text(f"{width},{height}")
```

Update `fetch_image_dimensions()` to check/write cache.

**Savings:** ~0.5-1s per image on subsequent requests

---

## Summary

| Task | Change | Savings |
|------|--------|---------|
| 1 | Remove sleep, add 429 backoff | ~2.4s/page |
| 2 | Parallel fetching with semaphore | ~1-2s/page |
| 3 | Use small images for previews | ~1-3s/preview |
| 4 | Persist dimension cache | ~0.5-1s/image |

**Total improvement:** 60-75% faster (4-6s → 1-2s per page)
