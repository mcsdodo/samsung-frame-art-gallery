# Met Museum Collection API - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Metropolitan Museum of Art collection browsing and upload capability to the Samsung Frame Art Gallery.

**Architecture:** Backend proxies Met API with caching, frontend adds tabbed interface with Met browsing panel. Batch fetching with pagination, resolution warnings before upload.

**Tech Stack:** Python/FastAPI (backend), Vue 3 Composition API (frontend), Met Collection API (external)

---

## Track A: Backend (Tasks 1-6)

### Task A1: Met Client - Core Structure

**Files:**
- Create: `src/services/met_client.py`

**Step 1: Create Met client with basic structure**

```python
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
```

**Step 2: Verify syntax**

Run: `python -m py_compile src/services/met_client.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add src/services/met_client.py
git commit -m "feat(met): add Met client core structure with caching"
```

---

### Task A2: Met Client - Departments Endpoint

**Files:**
- Modify: `src/services/met_client.py`

**Step 1: Add get_departments method to MetClient class**

Add after `_fetch_json` method:

```python
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
```

**Step 2: Verify syntax**

Run: `python -m py_compile src/services/met_client.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add src/services/met_client.py
git commit -m "feat(met): add departments endpoint"
```

---

### Task A3: Met Client - Object Details & Batch Fetch

**Files:**
- Modify: `src/services/met_client.py`

**Step 1: Add get_object and batch_fetch_objects methods**

Add after `get_departments` method:

```python
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
```

**Step 2: Verify syntax**

Run: `python -m py_compile src/services/met_client.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add src/services/met_client.py
git commit -m "feat(met): add object details and batch fetch"
```

---

### Task A4: Met Client - Highlights & Browse

**Files:**
- Modify: `src/services/met_client.py`

**Step 1: Add get_highlights and get_by_department methods**

Add after `batch_fetch_objects` method:

```python
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
```

**Step 2: Verify syntax**

Run: `python -m py_compile src/services/met_client.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add src/services/met_client.py
git commit -m "feat(met): add highlights and department browsing"
```

---

### Task A5: Met Client - Image Download

**Files:**
- Modify: `src/services/met_client.py`

**Step 1: Add fetch_image method**

Add after `get_by_department` method:

```python
    def fetch_image(self, image_url: str) -> bytes:
        """Download image bytes from Met servers."""
        _LOGGER.info(f"Downloading image: {image_url}")
        req = urllib.request.Request(
            image_url,
            headers={"User-Agent": "SamsungFrameArtGallery/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read()
```

**Step 2: Verify syntax**

Run: `python -m py_compile src/services/met_client.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add src/services/met_client.py
git commit -m "feat(met): add image download"
```

---

### Task A6: Met API Router

**Files:**
- Create: `src/api/met.py`
- Modify: `src/main.py`

**Step 1: Create Met API router**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio

from src.services.met_client import get_met_client
from src.services.tv_client import get_tv_client, TVClient

router = APIRouter()


def require_tv_client() -> TVClient:
    """Get TV client or raise 503 if not configured."""
    client = get_tv_client()
    if client is None:
        raise HTTPException(status_code=503, detail="No TV configured")
    return client


@router.get("/departments")
async def get_departments():
    """Get list of museum departments."""
    client = get_met_client()
    departments = await asyncio.to_thread(client.get_departments)
    return {"departments": departments}


@router.get("/highlights")
async def get_highlights(page: int = 1, page_size: int = 24):
    """Get highlighted artworks, paginated."""
    client = get_met_client()
    return await asyncio.to_thread(client.get_highlights, page, page_size)


@router.get("/objects")
async def get_objects(department_id: int, page: int = 1, page_size: int = 24):
    """Get artworks by department, paginated."""
    client = get_met_client()
    return await asyncio.to_thread(client.get_by_department, department_id, page, page_size)


@router.get("/object/{object_id}")
async def get_object(object_id: int):
    """Get single object details."""
    client = get_met_client()
    obj = await asyncio.to_thread(client.get_object, object_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj


class MetUploadRequest(BaseModel):
    object_ids: list[int]
    matte_style: str = "none"
    matte_color: str = "neutral"
    display: bool = False


@router.post("/upload")
async def upload_met_artwork(request: MetUploadRequest):
    """Download Met artwork and upload to TV."""
    met_client = get_met_client()
    tv_client = require_tv_client()

    results = []
    for object_id in request.object_ids:
        try:
            # Get object details
            obj = await asyncio.to_thread(met_client.get_object, object_id)
            if not obj:
                results.append({"object_id": object_id, "success": False, "error": "Object not found"})
                continue

            # Get best available image URL
            image_url = obj.get("primaryImage") or obj.get("primaryImageSmall")
            if not image_url:
                results.append({"object_id": object_id, "success": False, "error": "No image available"})
                continue

            # Download image
            image_data = await asyncio.to_thread(met_client.fetch_image, image_url)

            # Upload to TV
            display_this = request.display and object_id == request.object_ids[-1]
            result = await asyncio.to_thread(
                tv_client.upload_artwork,
                image_data,
                request.matte_style,
                request.matte_color,
                display_this
            )

            results.append({
                "object_id": object_id,
                "success": True,
                "content_id": result.get("content_id"),
                "title": obj.get("title", "Untitled")
            })
        except Exception as e:
            results.append({"object_id": object_id, "success": False, "error": str(e)})

    return {"results": results}
```

**Step 2: Mount router in main.py**

In `src/main.py`, add import and mount:

After line `from src.api import images, tv`:
```python
from src.api import images, tv, met
```

After line `app.include_router(tv.router, prefix="/api/tv", tags=["tv"])`:
```python
app.include_router(met.router, prefix="/api/met", tags=["met"])
```

**Step 3: Verify syntax**

Run: `python -m py_compile src/api/met.py && python -m py_compile src/main.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add src/api/met.py src/main.py
git commit -m "feat(met): add Met API router with all endpoints"
```

---

## Track B: Frontend (Tasks 1-6)

### Task B1: SourcePanel Component

**Files:**
- Create: `src/frontend/src/components/SourcePanel.vue`

**Step 1: Create tab wrapper component**

```vue
<template>
  <div class="source-panel">
    <div class="source-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <LocalPanel
      v-show="activeTab === 'local'"
      @uploaded="$emit('uploaded')"
      @preview="(img) => $emit('preview', img, true)"
    />

    <MetPanel
      v-show="activeTab === 'met'"
      @uploaded="$emit('uploaded')"
      @preview="(img) => $emit('preview', img, false)"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import LocalPanel from '../views/LocalPanel.vue'
import MetPanel from '../views/MetPanel.vue'

defineEmits(['uploaded', 'preview'])

const tabs = [
  { id: 'local', label: 'Local' },
  { id: 'met', label: 'Met Museum' }
]

const activeTab = ref('local')
</script>

<style scoped>
.source-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.source-tabs {
  display: flex;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a4e;
  flex-shrink: 0;
}

.source-tabs button {
  flex: 1;
  padding: 0.75rem;
  border: none;
  background: transparent;
  color: #888;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.source-tabs button:hover {
  color: #aaa;
}

.source-tabs button.active {
  color: white;
  border-bottom: 2px solid #4a90d9;
}
</style>
```

**Step 2: Commit**

```bash
git add src/frontend/src/components/SourcePanel.vue
git commit -m "feat(frontend): add SourcePanel with tabs"
```

---

### Task B2: MetPanel Component - Basic Structure

**Files:**
- Create: `src/frontend/src/views/MetPanel.vue`

**Step 1: Create Met browsing panel**

```vue
<template>
  <div class="met-panel">
    <div class="panel-header">
      <h2>Metropolitan Museum of Art</h2>
      <div class="department-select">
        <select v-model="selectedDepartment" @change="loadArtwork">
          <option :value="null">Highlights</option>
          <option
            v-for="dept in departments"
            :key="dept.departmentId"
            :value="dept.departmentId"
          >
            {{ dept.displayName }}
          </option>
        </select>
      </div>
    </div>

    <ImageGrid
      :images="artwork"
      :selected-ids="selectedIds"
      :loading="loading"
      :is-local="false"
      @toggle="toggleSelection"
      @select-all="selectAll"
      @preview="(img) => $emit('preview', img)"
    />

    <ActionBar>
      <template #left>
        <MatteSelector @change="matte = $event" />
      </template>
      <button
        class="secondary"
        :disabled="selectedIds.size === 0 || uploading"
        @click="upload(false)"
      >
        Upload ({{ selectedIds.size }})
      </button>
      <button
        class="primary"
        :disabled="selectedIds.size === 0 || uploading"
        @click="upload(true)"
      >
        Upload & Display
      </button>
    </ActionBar>

    <ResolutionWarning
      v-if="showResolutionWarning"
      :images="lowResImages"
      @confirm="confirmUpload"
      @cancel="showResolutionWarning = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import MatteSelector from '../components/MatteSelector.vue'
import ResolutionWarning from '../components/ResolutionWarning.vue'

const emit = defineEmits(['uploaded', 'preview'])

const departments = ref([])
const selectedDepartment = ref(null)
const artwork = ref([])
const selectedIds = ref(new Set())
const loading = ref(false)
const uploading = ref(false)
const matte = ref({ style: 'none', color: 'neutral' })
const currentPage = ref(1)
const hasMore = ref(false)

const showResolutionWarning = ref(false)
const pendingUpload = ref({ display: false })

// TV resolution threshold
const TV_WIDTH = 3840
const TV_HEIGHT = 2160

const lowResImages = computed(() => {
  return artwork.value.filter(img =>
    selectedIds.value.has(img.object_id) &&
    (img.width < TV_WIDTH || img.height < TV_HEIGHT)
  )
})

const loadDepartments = async () => {
  try {
    const res = await fetch('/api/met/departments')
    const data = await res.json()
    departments.value = data.departments || []
  } catch (e) {
    console.error('Failed to load departments:', e)
  }
}

const loadArtwork = async (append = false) => {
  if (!append) {
    currentPage.value = 1
    artwork.value = []
  }

  loading.value = true
  try {
    const endpoint = selectedDepartment.value
      ? `/api/met/objects?department_id=${selectedDepartment.value}&page=${currentPage.value}`
      : `/api/met/highlights?page=${currentPage.value}`

    const res = await fetch(endpoint)
    const data = await res.json()

    // Transform for ImageGrid compatibility
    const newArtwork = (data.objects || []).map(obj => ({
      ...obj,
      content_id: `met_${obj.object_id}`,
      thumbnail: obj.image_url_small || obj.image_url,
      path: null
    }))

    if (append) {
      artwork.value = [...artwork.value, ...newArtwork]
    } else {
      artwork.value = newArtwork
      selectedIds.value = new Set()
    }

    hasMore.value = data.has_more
  } catch (e) {
    console.error('Failed to load artwork:', e)
  } finally {
    loading.value = false
  }
}

const loadMore = async () => {
  if (hasMore.value && !loading.value) {
    currentPage.value++
    await loadArtwork(true)
  }
}

const toggleSelection = (image) => {
  const newSet = new Set(selectedIds.value)
  const id = image.object_id
  if (newSet.has(id)) {
    newSet.delete(id)
  } else {
    newSet.add(id)
  }
  selectedIds.value = newSet
}

const selectAll = (checked) => {
  if (checked) {
    selectedIds.value = new Set(artwork.value.map(a => a.object_id))
  } else {
    selectedIds.value = new Set()
  }
}

const upload = async (display) => {
  if (selectedIds.value.size === 0) return

  // Check for low resolution images
  if (lowResImages.value.length > 0) {
    pendingUpload.value = { display }
    showResolutionWarning.value = true
    return
  }

  await doUpload(display)
}

const confirmUpload = async () => {
  showResolutionWarning.value = false
  await doUpload(pendingUpload.value.display)
}

const doUpload = async (display) => {
  uploading.value = true
  try {
    const res = await fetch('/api/met/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        object_ids: Array.from(selectedIds.value),
        matte_style: matte.value.style,
        matte_color: matte.value.color,
        display
      })
    })
    const data = await res.json()
    console.log('Upload results:', data)
    selectedIds.value = new Set()
    emit('uploaded')
  } catch (e) {
    console.error('Upload failed:', e)
  } finally {
    uploading.value = false
  }
}

onMounted(() => {
  loadDepartments()
  loadArtwork()
})

defineExpose({ loadMore, hasMore })
</script>

<style scoped>
.met-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: #12121f;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #2a2a4e;
}

.panel-header h2 {
  font-size: 1.1rem;
  margin: 0;
}

.department-select select {
  padding: 0.4rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
}
</style>
```

**Step 2: Commit**

```bash
git add src/frontend/src/views/MetPanel.vue
git commit -m "feat(frontend): add MetPanel component"
```

---

### Task B3: ResolutionWarning Component

**Files:**
- Create: `src/frontend/src/components/ResolutionWarning.vue`

**Step 1: Create resolution warning modal**

```vue
<template>
  <div class="modal-overlay" @click.self="$emit('cancel')">
    <div class="modal">
      <h3>Low Resolution Warning</h3>
      <p>
        The following images are smaller than your TV's 4K resolution (3840 × 2160)
        and may appear pixelated:
      </p>

      <ul class="image-list">
        <li v-for="img in images" :key="img.object_id">
          <strong>{{ img.title }}</strong>
          <span class="resolution">{{ img.width }} × {{ img.height }}</span>
        </li>
      </ul>

      <div class="actions">
        <button class="secondary" @click="$emit('cancel')">Cancel</button>
        <button class="primary" @click="$emit('confirm')">Upload Anyway</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  images: { type: Array, required: true }
})

defineEmits(['confirm', 'cancel'])
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1.5rem;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal h3 {
  margin: 0 0 1rem;
  color: #ffaa00;
}

.modal p {
  color: #aaa;
  margin-bottom: 1rem;
}

.image-list {
  list-style: none;
  padding: 0;
  margin: 0 0 1.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.image-list li {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  border-bottom: 1px solid #2a2a4e;
}

.image-list li strong {
  color: white;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 1rem;
}

.resolution {
  color: #ff6666;
  font-family: monospace;
  white-space: nowrap;
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.actions button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
}

.actions .secondary {
  background: #3a3a5e;
  color: white;
}

.actions .primary {
  background: #4a90d9;
  color: white;
}
</style>
```

**Step 2: Commit**

```bash
git add src/frontend/src/components/ResolutionWarning.vue
git commit -m "feat(frontend): add ResolutionWarning modal"
```

---

### Task B4: Update ImageGrid for Met Images

**Files:**
- Modify: `src/frontend/src/components/ImageGrid.vue`

**Step 1: Update key binding for Met compatibility**

In `ImageGrid.vue`, line 33, change the `:key` binding:

```vue
:key="image.path || image.object_id || image.content_id"
```

**Step 2: Update selected check**

In line 35, update the `:selected` binding:

```vue
:selected="selectedIds.has(image.path || image.object_id || image.content_id)"
```

**Step 3: Commit**

```bash
git add src/frontend/src/components/ImageGrid.vue
git commit -m "fix(frontend): support Met object_id in ImageGrid"
```

---

### Task B5: Update ImageCard for Met Thumbnails

**Files:**
- Modify: `src/frontend/src/components/ImageCard.vue`

**Step 1: Read current ImageCard**

First examine the current thumbnail logic in ImageCard.vue to understand how to add Met image support.

**Step 2: Update thumbnail URL computation**

Find the thumbnail URL logic and update to handle Met images. Add computed property:

```javascript
const thumbnailUrl = computed(() => {
  if (props.image.thumbnail) {
    // Met images have direct thumbnail URL
    return props.image.thumbnail
  }
  if (props.isLocal) {
    return `/api/images/thumbnail/${encodeURIComponent(props.image.path)}`
  }
  return `/api/tv/artwork/${props.image.content_id}/thumbnail`
})
```

Replace direct URL references with `thumbnailUrl.value`.

**Step 3: Commit**

```bash
git add src/frontend/src/components/ImageCard.vue
git commit -m "fix(frontend): support Met thumbnail URLs in ImageCard"
```

---

### Task B6: Integrate SourcePanel into App.vue

**Files:**
- Modify: `src/frontend/src/App.vue`

**Step 1: Replace LocalPanel import with SourcePanel**

Change import from:
```javascript
import LocalPanel from './views/LocalPanel.vue'
```
To:
```javascript
import SourcePanel from './components/SourcePanel.vue'
```

**Step 2: Update template**

Replace `<LocalPanel>` with `<SourcePanel>` in both desktop and mobile templates:

Desktop (around line 28):
```vue
<SourcePanel class="panel" @uploaded="refreshTV" @preview="showPreview" />
```

Mobile (around line 35):
```vue
<SourcePanel v-show="activeTab === 'local'" class="panel" @uploaded="refreshTV" @preview="showPreview" />
```

**Step 3: Update mobile tab label**

Change the mobile tab button text from "Local" to "Images" (line 18):
```vue
@click="activeTab = 'local'"
>Images</button>
```

**Step 4: Commit**

```bash
git add src/frontend/src/App.vue
git commit -m "feat(frontend): integrate SourcePanel with tabs into App"
```

---

## Track C: Integration (Task 1)

### Task C1: Build and Test

**Step 1: Build frontend**

```bash
cd src/frontend && npm run build && cd ../..
```

**Step 2: Build Docker image**

```bash
docker-compose build
```

**Step 3: Run locally and test**

```bash
docker-compose up -d
```

Test endpoints:
- http://localhost:8080/api/met/departments
- http://localhost:8080/api/met/highlights
- http://localhost:8080 (UI with tabs)

**Step 4: Deploy to test host**

```bash
docker save samsung-frame-art-gallery-app | gzip > /tmp/art-gallery.tar.gz
scp /tmp/art-gallery.tar.gz root@192.168.0.99:/tmp/
ssh root@192.168.0.99 "docker load < /tmp/art-gallery.tar.gz && cd /opt/samsung-frame-art-gallery && docker compose down && docker compose up -d"
```

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete Met Museum collection integration"
```

---

## Parallel Execution Notes

**Track A (Backend)** and **Track B (Frontend)** can run simultaneously:
- Track A: Tasks A1-A6 (Met client + API)
- Track B: Tasks B1-B6 (Vue components)
- Track C: After both complete (integration testing)

Frontend can use mock data or real API (once backend is deployed) during development.
