# Samsung Frame Art Gallery - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a web application to browse local images and manage Samsung Frame TV art mode.

**Architecture:** Vue 3 SPA frontend with FastAPI backend, running in a single Docker container. Frontend builds to static files served by FastAPI. TV communication via samsungtvws WebSocket library.

**Tech Stack:** Python 3.11, FastAPI, Vue 3, Vite, Pillow (thumbnails), samsungtvws

---

## Phase 1: Backend Foundation (Can run in parallel with Phase 2)

### Task 1.1: Project Structure Setup

**Files:**
- Create: `src/main.py`
- Create: `src/api/__init__.py`
- Create: `src/api/images.py`
- Create: `src/api/tv.py`
- Create: `src/services/__init__.py`
- Create: `src/services/tv_client.py`
- Create: `src/services/thumbnails.py`
- Modify: `requirements.txt`

**Step 1: Update requirements.txt**

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6
Pillow>=10.2.0
git+https://github.com/NickWaterton/samsung-tv-ws-api.git
```

**Step 2: Create main FastAPI app**

Create `src/main.py`:
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from src.api import images, tv

app = FastAPI(title="Samsung Frame Art Gallery")

# API routes
app.include_router(images.router, prefix="/api/images", tags=["images"])
app.include_router(tv.router, prefix="/api/tv", tags=["tv"])

# Serve static frontend (Vue build output)
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = static_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_path / "index.html")
```

**Step 3: Create API module init files**

Create `src/api/__init__.py`:
```python
# API routers
```

Create `src/services/__init__.py`:
```python
# Services
```

**Step 4: Create placeholder routers**

Create `src/api/images.py`:
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def list_images():
    return {"images": [], "message": "Not implemented"}
```

Create `src/api/tv.py`:
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_status():
    return {"connected": False, "message": "Not implemented"}
```

**Step 5: Create placeholder services**

Create `src/services/tv_client.py`:
```python
# Samsung TV client wrapper
```

Create `src/services/thumbnails.py`:
```python
# Thumbnail generation service
```

**Step 6: Test the server starts**

Run: `cd src && python -m uvicorn main:app --reload --port 8080`
Expected: Server starts, visit http://localhost:8080/api/tv/status returns JSON

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: add FastAPI project structure with placeholder routes"
```

---

### Task 1.2: TV Client Service

**Files:**
- Modify: `src/services/tv_client.py`

**Step 1: Implement TV client wrapper**

```python
import os
from typing import Optional
from samsungtvws import SamsungTVWS

TV_IP = os.environ.get("TV_IP", "192.168.0.105")
TV_TIMEOUT = 10

class TVClient:
    _instance: Optional["TVClient"] = None

    def __init__(self):
        self._tv: Optional[SamsungTVWS] = None

    @classmethod
    def get_instance(cls) -> "TVClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_tv(self) -> SamsungTVWS:
        if self._tv is None:
            self._tv = SamsungTVWS(TV_IP, timeout=TV_TIMEOUT)
        return self._tv

    def get_status(self) -> dict:
        try:
            tv = self._get_tv()
            supported = tv.art().supported()
            return {"connected": True, "art_mode_supported": supported, "tv_ip": TV_IP}
        except Exception as e:
            self._tv = None
            return {"connected": False, "error": str(e), "tv_ip": TV_IP}

    def get_artwork_list(self) -> list:
        tv = self._get_tv()
        return tv.art().available() or []

    def get_current_artwork(self) -> dict:
        tv = self._get_tv()
        return tv.art().get_current() or {}

    def set_current_artwork(self, content_id: str) -> bool:
        tv = self._get_tv()
        tv.art().select_image(content_id)
        return True

    def delete_artwork(self, content_id: str) -> bool:
        tv = self._get_tv()
        tv.art().delete(content_id)
        return True

    def upload_artwork(self, image_data: bytes, matte: str = "none",
                       matte_color: str = "neutral", display: bool = False) -> dict:
        tv = self._get_tv()
        result = tv.art().upload(image_data, matte=matte, portrait_matte=matte)
        if display and result:
            content_id = result.get("content_id")
            if content_id:
                tv.art().select_image(content_id)
        return result or {}

    def get_matte_options(self) -> dict:
        return {
            "styles": ["none", "modernthin", "modern", "flexible"],
            "colors": ["neutral", "antique", "warm", "cold"]
        }


def get_tv_client() -> TVClient:
    return TVClient.get_instance()
```

**Step 2: Commit**

```bash
git add src/services/tv_client.py
git commit -m "feat: add Samsung TV client wrapper service"
```

---

### Task 1.3: TV API Endpoints

**Files:**
- Modify: `src/api/tv.py`

**Step 1: Implement TV endpoints**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.services.tv_client import get_tv_client

router = APIRouter()


class SetCurrentRequest(BaseModel):
    content_id: str


class UploadRequest(BaseModel):
    paths: list[str]
    matte_style: str = "none"
    matte_color: str = "neutral"
    display: bool = False


@router.get("/status")
async def get_status():
    client = get_tv_client()
    return client.get_status()


@router.get("/mattes")
async def get_mattes():
    client = get_tv_client()
    return client.get_matte_options()


@router.get("/artwork")
async def list_artwork():
    client = get_tv_client()
    try:
        artwork = client.get_artwork_list()
        return {"artwork": artwork, "count": len(artwork)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/artwork/current")
async def get_current_artwork():
    client = get_tv_client()
    try:
        return client.get_current_artwork()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/artwork/current")
async def set_current_artwork(request: SetCurrentRequest):
    client = get_tv_client()
    try:
        client.set_current_artwork(request.content_id)
        return {"success": True, "content_id": request.content_id}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.delete("/artwork/{content_id}")
async def delete_artwork(content_id: str):
    client = get_tv_client()
    try:
        client.delete_artwork(content_id)
        return {"success": True, "deleted": content_id}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

**Step 2: Test endpoints**

Run server, then test:
```bash
curl http://localhost:8080/api/tv/status
curl http://localhost:8080/api/tv/mattes
curl http://localhost:8080/api/tv/artwork
```

**Step 3: Commit**

```bash
git add src/api/tv.py
git commit -m "feat: add TV artwork API endpoints"
```

---

### Task 1.4: Thumbnail Service

**Files:**
- Modify: `src/services/thumbnails.py`

**Step 1: Implement thumbnail generation**

```python
import hashlib
from io import BytesIO
from pathlib import Path
from PIL import Image

THUMBNAIL_SIZE = (300, 300)
CACHE_DIR = Path("/tmp/thumbnails")


def get_cache_path(image_path: str) -> Path:
    hash_key = hashlib.md5(image_path.encode()).hexdigest()
    return CACHE_DIR / f"{hash_key}.jpg"


def generate_thumbnail(image_path: Path) -> bytes:
    cache_path = get_cache_path(str(image_path))

    # Check cache
    if cache_path.exists():
        return cache_path.read_bytes()

    # Generate thumbnail
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as img:
        img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        # Convert to RGB if needed (for JPEG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        thumbnail_data = buffer.getvalue()

    # Cache it
    cache_path.write_bytes(thumbnail_data)

    return thumbnail_data


def clear_cache():
    if CACHE_DIR.exists():
        for f in CACHE_DIR.glob("*.jpg"):
            f.unlink()
```

**Step 2: Commit**

```bash
git add src/services/thumbnails.py
git commit -m "feat: add thumbnail generation with caching"
```

---

### Task 1.5: Images API Endpoints

**Files:**
- Modify: `src/api/images.py`

**Step 1: Implement local images endpoints**

```python
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from src.services.thumbnails import generate_thumbnail

router = APIRouter()

IMAGES_DIR = Path(os.environ.get("IMAGES_DIR", "/images"))
ALLOWED_EXTENSIONS = {".jpg", ".jpeg"}


def is_valid_image(path: Path) -> bool:
    return path.suffix.lower() in ALLOWED_EXTENSIONS and path.is_file()


def get_safe_path(relative_path: str) -> Path:
    """Prevent directory traversal attacks."""
    full_path = (IMAGES_DIR / relative_path).resolve()
    if not str(full_path).startswith(str(IMAGES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    return full_path


@router.get("")
async def list_images(folder: str = Query(None)):
    if not IMAGES_DIR.exists():
        return {"images": [], "folder": folder}

    search_dir = IMAGES_DIR if folder is None else get_safe_path(folder)

    if not search_dir.exists() or not search_dir.is_dir():
        raise HTTPException(status_code=404, detail="Folder not found")

    images = []
    for path in search_dir.iterdir():
        if is_valid_image(path):
            rel_path = path.relative_to(IMAGES_DIR)
            images.append({
                "path": str(rel_path),
                "name": path.name,
                "size": path.stat().st_size
            })

    images.sort(key=lambda x: x["name"].lower())
    return {"images": images, "folder": folder, "count": len(images)}


@router.get("/folders")
async def list_folders():
    if not IMAGES_DIR.exists():
        return {"folders": []}

    folders = []
    for path in IMAGES_DIR.rglob("*"):
        if path.is_dir():
            rel_path = path.relative_to(IMAGES_DIR)
            folders.append(str(rel_path))

    folders.sort()
    return {"folders": folders}


@router.get("/{path:path}/thumbnail")
async def get_thumbnail(path: str):
    image_path = get_safe_path(path)

    if not is_valid_image(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        thumbnail_data = generate_thumbnail(image_path)
        return Response(content=thumbnail_data, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{path:path}/full")
async def get_full_image(path: str):
    image_path = get_safe_path(path)

    if not is_valid_image(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return Response(content=image_path.read_bytes(), media_type="image/jpeg")
```

**Step 2: Test with local images folder**

Create test images folder and test:
```bash
mkdir -p images
# Add some JPEG files to images/
curl http://localhost:8080/api/images
curl http://localhost:8080/api/images/folders
```

**Step 3: Commit**

```bash
git add src/api/images.py
git commit -m "feat: add local images API with thumbnails"
```

---

### Task 1.6: Upload Endpoint

**Files:**
- Modify: `src/api/tv.py`

**Step 1: Add upload endpoint to tv.py**

Add this import at top:
```python
from pathlib import Path
import os
```

Add constant:
```python
IMAGES_DIR = Path(os.environ.get("IMAGES_DIR", "/images"))
```

Add helper function:
```python
def get_safe_path(relative_path: str) -> Path:
    full_path = (IMAGES_DIR / relative_path).resolve()
    if not str(full_path).startswith(str(IMAGES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    return full_path
```

Add endpoint:
```python
@router.post("/upload")
async def upload_artwork(request: UploadRequest):
    client = get_tv_client()
    results = []

    for path in request.paths:
        try:
            image_path = get_safe_path(path)
            if not image_path.exists():
                results.append({"path": path, "success": False, "error": "File not found"})
                continue

            image_data = image_path.read_bytes()
            result = client.upload_artwork(
                image_data,
                matte=request.matte_style,
                matte_color=request.matte_color,
                display=request.display and len(request.paths) == 1
            )
            results.append({"path": path, "success": True, "result": result})
        except Exception as e:
            results.append({"path": path, "success": False, "error": str(e)})

    # If display requested and multiple images, display the last one
    if request.display and len(request.paths) > 1:
        last_success = next((r for r in reversed(results) if r["success"]), None)
        if last_success and "content_id" in last_success.get("result", {}):
            try:
                client.set_current_artwork(last_success["result"]["content_id"])
            except:
                pass

    return {"results": results}
```

**Step 2: Commit**

```bash
git add src/api/tv.py
git commit -m "feat: add artwork upload endpoint with matte support"
```

---

## Phase 2: Frontend Foundation (Can run in parallel with Phase 1)

### Task 2.1: Vue Project Setup

**Files:**
- Create: `src/frontend/package.json`
- Create: `src/frontend/vite.config.js`
- Create: `src/frontend/index.html`
- Create: `src/frontend/src/main.js`
- Create: `src/frontend/src/App.vue`
- Create: `src/frontend/src/style.css`

**Step 1: Create package.json**

```json
{
  "name": "samsung-frame-gallery",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

**Step 2: Create vite.config.js**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://localhost:8080'
    }
  },
  build: {
    outDir: '../../static',
    emptyOutDir: true
  }
})
```

**Step 3: Create index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Samsung Frame Art Gallery</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

**Step 4: Create src/main.js**

```javascript
import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

createApp(App).mount('#app')
```

**Step 5: Create src/App.vue**

```vue
<template>
  <div class="app">
    <header class="header">
      <h1>Samsung Frame Art Gallery</h1>
      <div class="status" :class="{ connected: tvStatus.connected }">
        <span class="status-dot"></span>
        {{ tvStatus.connected ? 'TV Connected' : 'TV Disconnected' }}
      </div>
    </header>
    <main class="main">
      <p>Loading...</p>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const tvStatus = ref({ connected: false })

onMounted(async () => {
  try {
    const res = await fetch('/api/tv/status')
    tvStatus.value = await res.json()
  } catch (e) {
    console.error('Failed to get TV status:', e)
  }
})
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #1a1a2e;
  color: white;
}

.header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ff4444;
}

.status.connected .status-dot {
  background: #44ff44;
}

.main {
  padding: 1rem;
}
</style>
```

**Step 6: Create src/style.css**

```css
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0f0f1a;
  color: #e0e0e0;
  min-height: 100vh;
}

.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
```

**Step 7: Install dependencies and test**

```bash
cd src/frontend
npm install
npm run dev
```

Visit http://localhost:5173 - should show header with TV status

**Step 8: Commit**

```bash
git add src/frontend/
git commit -m "feat: add Vue 3 project with basic layout"
```

---

### Task 2.2: ImageCard Component

**Files:**
- Create: `src/frontend/src/components/ImageCard.vue`

**Step 1: Create ImageCard component**

```vue
<template>
  <div
    class="image-card"
    :class="{ selected, current: isCurrent }"
    @click="$emit('toggle')"
  >
    <div class="checkbox" @click.stop="$emit('toggle')">
      <input type="checkbox" :checked="selected" />
    </div>
    <img
      :src="thumbnailUrl"
      :alt="image.name"
      loading="lazy"
    />
    <div class="overlay">
      <span class="name">{{ image.name }}</span>
      <span v-if="isCurrent" class="current-badge">NOW</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  image: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  isCurrent: { type: Boolean, default: false },
  isLocal: { type: Boolean, default: true }
})

defineEmits(['toggle'])

const thumbnailUrl = computed(() => {
  if (props.isLocal) {
    return `/api/images/${encodeURIComponent(props.image.path)}/thumbnail`
  }
  // TV artwork - use content_id for identification
  return `/api/tv/artwork/${props.image.content_id}/thumbnail`
})
</script>

<style scoped>
.image-card {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 3px solid transparent;
  transition: border-color 0.2s, transform 0.2s;
}

.image-card:hover {
  transform: scale(1.02);
}

.image-card.selected {
  border-color: #4a90d9;
}

.image-card.current {
  border-color: #44ff44;
}

.checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
}

.checkbox input {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px;
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.name {
  font-size: 0.8rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%;
}

.current-badge {
  background: #44ff44;
  color: black;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: bold;
}
</style>
```

**Step 2: Commit**

```bash
git add src/frontend/src/components/ImageCard.vue
git commit -m "feat: add ImageCard component with selection support"
```

---

### Task 2.3: ImageGrid Component

**Files:**
- Create: `src/frontend/src/components/ImageGrid.vue`

**Step 1: Create ImageGrid component**

```vue
<template>
  <div class="image-grid-container">
    <div class="grid-header">
      <label class="select-all">
        <input
          type="checkbox"
          :checked="allSelected"
          @change="$emit('select-all', $event.target.checked)"
        />
        Select All ({{ selectedCount }}/{{ images.length }})
      </label>
      <slot name="header-actions"></slot>
    </div>

    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="images.length === 0" class="empty">
      No images found
    </div>

    <div v-else class="grid">
      <ImageCard
        v-for="image in images"
        :key="image.path || image.content_id"
        :image="image"
        :selected="selectedIds.has(image.path || image.content_id)"
        :is-current="currentId === (image.content_id)"
        :is-local="isLocal"
        @toggle="$emit('toggle', image)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ImageCard from './ImageCard.vue'

const props = defineProps({
  images: { type: Array, default: () => [] },
  selectedIds: { type: Set, default: () => new Set() },
  currentId: { type: String, default: null },
  loading: { type: Boolean, default: false },
  isLocal: { type: Boolean, default: true }
})

defineEmits(['toggle', 'select-all'])

const selectedCount = computed(() => props.selectedIds.size)
const allSelected = computed(() =>
  props.images.length > 0 && props.selectedIds.size === props.images.length
)
</script>

<style scoped>
.image-grid-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.grid-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a4e;
}

.select-all {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.select-all input {
  width: 18px;
  height: 18px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
}

.loading, .empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #888;
}
</style>
```

**Step 2: Commit**

```bash
git add src/frontend/src/components/ImageGrid.vue
git commit -m "feat: add ImageGrid component with multi-select"
```

---

### Task 2.4: MatteSelector Component

**Files:**
- Create: `src/frontend/src/components/MatteSelector.vue`

**Step 1: Create MatteSelector component**

```vue
<template>
  <div class="matte-selector">
    <div class="matte-field">
      <label>Style:</label>
      <select v-model="style" @change="emitChange">
        <option v-for="s in styles" :key="s" :value="s">{{ formatLabel(s) }}</option>
      </select>
    </div>
    <div class="matte-field">
      <label>Color:</label>
      <select v-model="color" @change="emitChange">
        <option v-for="c in colors" :key="c" :value="c">{{ formatLabel(c) }}</option>
      </select>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['change'])

const styles = ref(['none'])
const colors = ref(['neutral'])
const style = ref('none')
const color = ref('neutral')

const formatLabel = (s) => s.charAt(0).toUpperCase() + s.slice(1)

const emitChange = () => {
  emit('change', { style: style.value, color: color.value })
}

onMounted(async () => {
  try {
    const res = await fetch('/api/tv/mattes')
    const data = await res.json()
    styles.value = data.styles || ['none']
    colors.value = data.colors || ['neutral']
  } catch (e) {
    console.error('Failed to load matte options:', e)
  }
})
</script>

<style scoped>
.matte-selector {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.matte-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.matte-field label {
  font-size: 0.9rem;
  color: #aaa;
}

.matte-field select {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
  cursor: pointer;
}
</style>
```

**Step 2: Commit**

```bash
git add src/frontend/src/components/MatteSelector.vue
git commit -m "feat: add MatteSelector component"
```

---

### Task 2.5: ActionBar Component

**Files:**
- Create: `src/frontend/src/components/ActionBar.vue`

**Step 1: Create ActionBar component**

```vue
<template>
  <div class="action-bar">
    <slot name="left"></slot>
    <div class="actions">
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #1a1a2e;
  border-top: 1px solid #2a2a4e;
  gap: 1rem;
  flex-wrap: wrap;
}

.actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

:deep(button) {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-weight: 500;
  transition: opacity 0.2s;
}

:deep(button:disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}

:deep(button.primary) {
  background: #4a90d9;
  color: white;
}

:deep(button.secondary) {
  background: #3a3a5e;
  color: white;
}

:deep(button.danger) {
  background: #d94a4a;
  color: white;
}
</style>
```

**Step 2: Commit**

```bash
git add src/frontend/src/components/ActionBar.vue
git commit -m "feat: add ActionBar component"
```

---

## Phase 3: Integration (After Phases 1 & 2)

### Task 3.1: Gallery View - Local Images Panel

**Files:**
- Create: `src/frontend/src/views/LocalPanel.vue`

**Step 1: Create LocalPanel component**

```vue
<template>
  <div class="local-panel">
    <div class="panel-header">
      <h2>Local Images</h2>
      <div class="folder-select">
        <button
          :class="{ active: !currentFolder }"
          @click="currentFolder = null"
        >All</button>
        <select v-if="folders.length" v-model="currentFolder">
          <option :value="null">All Folders</option>
          <option v-for="f in folders" :key="f" :value="f">{{ f }}</option>
        </select>
      </div>
    </div>

    <ImageGrid
      :images="images"
      :selected-ids="selectedIds"
      :loading="loading"
      :is-local="true"
      @toggle="toggleSelection"
      @select-all="selectAll"
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
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import MatteSelector from '../components/MatteSelector.vue'

const emit = defineEmits(['uploaded'])

const images = ref([])
const folders = ref([])
const currentFolder = ref(null)
const selectedIds = ref(new Set())
const loading = ref(false)
const uploading = ref(false)
const matte = ref({ style: 'none', color: 'neutral' })

const loadImages = async () => {
  loading.value = true
  try {
    const url = currentFolder.value
      ? `/api/images?folder=${encodeURIComponent(currentFolder.value)}`
      : '/api/images'
    const res = await fetch(url)
    const data = await res.json()
    images.value = data.images || []
    selectedIds.value = new Set()
  } catch (e) {
    console.error('Failed to load images:', e)
  } finally {
    loading.value = false
  }
}

const loadFolders = async () => {
  try {
    const res = await fetch('/api/images/folders')
    const data = await res.json()
    folders.value = data.folders || []
  } catch (e) {
    console.error('Failed to load folders:', e)
  }
}

const toggleSelection = (image) => {
  const newSet = new Set(selectedIds.value)
  if (newSet.has(image.path)) {
    newSet.delete(image.path)
  } else {
    newSet.add(image.path)
  }
  selectedIds.value = newSet
}

const selectAll = (checked) => {
  if (checked) {
    selectedIds.value = new Set(images.value.map(i => i.path))
  } else {
    selectedIds.value = new Set()
  }
}

const upload = async (display) => {
  if (selectedIds.value.size === 0) return

  uploading.value = true
  try {
    const res = await fetch('/api/tv/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        paths: Array.from(selectedIds.value),
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

watch(currentFolder, loadImages)

onMounted(() => {
  loadImages()
  loadFolders()
})
</script>

<style scoped>
.local-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
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

.folder-select {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.folder-select button {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: transparent;
  color: #aaa;
  cursor: pointer;
}

.folder-select button.active {
  background: #4a90d9;
  color: white;
  border-color: #4a90d9;
}

.folder-select select {
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
git add src/frontend/src/views/LocalPanel.vue
git commit -m "feat: add LocalPanel with folder navigation and upload"
```

---

### Task 3.2: Gallery View - TV Panel

**Files:**
- Create: `src/frontend/src/views/TVPanel.vue`

**Step 1: Create TVPanel component**

```vue
<template>
  <div class="tv-panel">
    <div class="panel-header">
      <h2>TV Artwork</h2>
      <button class="refresh-btn" @click="loadArtwork" :disabled="loading">
        Refresh
      </button>
    </div>

    <ImageGrid
      :images="artwork"
      :selected-ids="selectedIds"
      :current-id="currentId"
      :loading="loading"
      :is-local="false"
      @toggle="toggleSelection"
      @select-all="selectAll"
    />

    <ActionBar>
      <template #left>
        <span class="selected-count">{{ selectedIds.size }} selected</span>
      </template>
      <button
        class="secondary"
        :disabled="selectedIds.size !== 1"
        @click="setAsCurrent"
      >
        Display
      </button>
      <button
        class="danger"
        :disabled="selectedIds.size === 0 || deleting"
        @click="deleteSelected"
      >
        Delete ({{ selectedIds.size }})
      </button>
    </ActionBar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'

const artwork = ref([])
const currentId = ref(null)
const selectedIds = ref(new Set())
const loading = ref(false)
const deleting = ref(false)

const loadArtwork = async () => {
  loading.value = true
  try {
    const [artRes, currentRes] = await Promise.all([
      fetch('/api/tv/artwork'),
      fetch('/api/tv/artwork/current')
    ])
    const artData = await artRes.json()
    const currentData = await currentRes.json()

    artwork.value = artData.artwork || []
    currentId.value = currentData.content_id || null
    selectedIds.value = new Set()
  } catch (e) {
    console.error('Failed to load TV artwork:', e)
  } finally {
    loading.value = false
  }
}

const toggleSelection = (image) => {
  const newSet = new Set(selectedIds.value)
  if (newSet.has(image.content_id)) {
    newSet.delete(image.content_id)
  } else {
    newSet.add(image.content_id)
  }
  selectedIds.value = newSet
}

const selectAll = (checked) => {
  if (checked) {
    selectedIds.value = new Set(artwork.value.map(a => a.content_id))
  } else {
    selectedIds.value = new Set()
  }
}

const setAsCurrent = async () => {
  const contentId = Array.from(selectedIds.value)[0]
  if (!contentId) return

  try {
    await fetch('/api/tv/artwork/current', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_id: contentId })
    })
    currentId.value = contentId
    selectedIds.value = new Set()
  } catch (e) {
    console.error('Failed to set current artwork:', e)
  }
}

const deleteSelected = async () => {
  if (selectedIds.value.size === 0) return

  deleting.value = true
  try {
    for (const contentId of selectedIds.value) {
      await fetch(`/api/tv/artwork/${contentId}`, { method: 'DELETE' })
    }
    await loadArtwork()
  } catch (e) {
    console.error('Failed to delete artwork:', e)
  } finally {
    deleting.value = false
  }
}

onMounted(loadArtwork)

defineExpose({ loadArtwork })
</script>

<style scoped>
.tv-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
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

.refresh-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: transparent;
  color: #aaa;
  cursor: pointer;
}

.refresh-btn:hover:not(:disabled) {
  background: #2a2a4e;
}

.selected-count {
  color: #888;
  font-size: 0.9rem;
}
</style>
```

**Step 2: Commit**

```bash
git add src/frontend/src/views/TVPanel.vue
git commit -m "feat: add TVPanel with artwork management"
```

---

### Task 3.3: Main App Integration

**Files:**
- Modify: `src/frontend/src/App.vue`

**Step 1: Update App.vue with responsive layout**

```vue
<template>
  <div class="app">
    <header class="header">
      <h1>Samsung Frame Art Gallery</h1>
      <div class="status" :class="{ connected: tvStatus.connected }">
        <span class="status-dot"></span>
        {{ tvStatus.connected ? 'Connected' : 'Disconnected' }}
      </div>
    </header>

    <!-- Mobile: Tabs -->
    <div class="mobile-tabs" v-if="isMobile">
      <button
        :class="{ active: activeTab === 'local' }"
        @click="activeTab = 'local'"
      >Local</button>
      <button
        :class="{ active: activeTab === 'tv' }"
        @click="activeTab = 'tv'"
      >TV</button>
    </div>

    <main class="main" :class="{ mobile: isMobile }">
      <!-- Desktop: Split view -->
      <template v-if="!isMobile">
        <LocalPanel class="panel" @uploaded="refreshTV" />
        <div class="divider"></div>
        <TVPanel ref="tvPanel" class="panel" />
      </template>

      <!-- Mobile: Tab content -->
      <template v-else>
        <LocalPanel v-show="activeTab === 'local'" class="panel" @uploaded="refreshTV" />
        <TVPanel v-show="activeTab === 'tv'" ref="tvPanel" class="panel" />
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import LocalPanel from './views/LocalPanel.vue'
import TVPanel from './views/TVPanel.vue'

const tvStatus = ref({ connected: false })
const isMobile = ref(false)
const activeTab = ref('local')
const tvPanel = ref(null)

const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
}

const refreshTV = () => {
  tvPanel.value?.loadArtwork()
}

onMounted(async () => {
  checkMobile()
  window.addEventListener('resize', checkMobile)

  try {
    const res = await fetch('/api/tv/status')
    tvStatus.value = await res.json()
  } catch (e) {
    console.error('Failed to get TV status:', e)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #1a1a2e;
  color: white;
}

.header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ff4444;
}

.status.connected .status-dot {
  background: #44ff44;
}

.mobile-tabs {
  display: flex;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a4e;
}

.mobile-tabs button {
  flex: 1;
  padding: 0.75rem;
  border: none;
  background: transparent;
  color: #888;
  cursor: pointer;
  font-size: 1rem;
}

.mobile-tabs button.active {
  color: white;
  border-bottom: 2px solid #4a90d9;
}

.main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.main.mobile {
  flex-direction: column;
}

.panel {
  flex: 1;
  overflow: hidden;
}

.divider {
  width: 1px;
  background: #2a2a4e;
}
</style>
```

**Step 2: Build and test**

```bash
cd src/frontend
npm run build
```

Start backend and test at http://localhost:8080

**Step 3: Commit**

```bash
git add src/frontend/src/App.vue
git commit -m "feat: integrate panels with responsive layout"
```

---

### Task 3.4: Update Docker Configuration

**Files:**
- Modify: `docker/Dockerfile`
- Modify: `docker-compose.yml`

**Step 1: Update Dockerfile for multi-stage build**

```dockerfile
# Stage 1: Build Vue frontend
FROM node:20-slim AS frontend
WORKDIR /app
COPY src/frontend/package*.json ./
RUN npm ci
COPY src/frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim

WORKDIR /app

# Install git for pip
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY --from=frontend /app/dist ./static/

EXPOSE 8080

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Step 2: Update docker-compose.yml**

```yaml
services:
  app:
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "8080:8080"
    volumes:
      - ./images:/images:ro
    environment:
      - TV_IP=192.168.0.105
    restart: unless-stopped
```

**Step 3: Test full build**

```bash
docker-compose up --build
```

Visit http://localhost:8080

**Step 4: Commit**

```bash
git add docker/Dockerfile docker-compose.yml
git commit -m "feat: update Docker for production build"
```

---

### Task 3.5: Fix ImageCard for TV Artwork (No Thumbnails)

**Files:**
- Modify: `src/frontend/src/components/ImageCard.vue`

**Step 1: Update ImageCard to handle TV artwork without thumbnails**

TV artwork from Samsung doesn't have a direct thumbnail endpoint. Update the component to show a placeholder or fetch differently:

```vue
<template>
  <div
    class="image-card"
    :class="{ selected, current: isCurrent }"
    @click="$emit('toggle')"
  >
    <div class="checkbox" @click.stop="$emit('toggle')">
      <input type="checkbox" :checked="selected" />
    </div>
    <img
      v-if="thumbnailUrl"
      :src="thumbnailUrl"
      :alt="displayName"
      loading="lazy"
      @error="imgError = true"
    />
    <div v-else class="placeholder">
      <span>{{ displayName.slice(0, 2).toUpperCase() }}</span>
    </div>
    <div class="overlay">
      <span class="name">{{ displayName }}</span>
      <span v-if="isCurrent" class="current-badge">NOW</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  image: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  isCurrent: { type: Boolean, default: false },
  isLocal: { type: Boolean, default: true }
})

defineEmits(['toggle'])

const imgError = ref(false)

const thumbnailUrl = computed(() => {
  if (imgError.value) return null
  if (props.isLocal) {
    return `/api/images/${encodeURIComponent(props.image.path)}/thumbnail`
  }
  // TV artwork doesn't have thumbnails from our API
  return null
})

const displayName = computed(() => {
  if (props.isLocal) {
    return props.image.name
  }
  return props.image.content_id || 'Unknown'
})
</script>

<style scoped>
.image-card {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 3px solid transparent;
  transition: border-color 0.2s, transform 0.2s;
  background: #2a2a4e;
}

.image-card:hover {
  transform: scale(1.02);
}

.image-card.selected {
  border-color: #4a90d9;
}

.image-card.current {
  border-color: #44ff44;
}

.checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
}

.checkbox input {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  font-weight: bold;
  color: #666;
  background: linear-gradient(135deg, #2a2a4e, #1a1a2e);
}

.overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px;
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.name {
  font-size: 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%;
}

.current-badge {
  background: #44ff44;
  color: black;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: bold;
}
</style>
```

**Step 2: Commit**

```bash
git add src/frontend/src/components/ImageCard.vue
git commit -m "fix: handle TV artwork display without thumbnails"
```

---

## Summary

**Phase 1 (Backend):** Tasks 1.1-1.6 - Can run independently
**Phase 2 (Frontend):** Tasks 2.1-2.5 - Can run independently
**Phase 3 (Integration):** Tasks 3.1-3.5 - Requires Phases 1 & 2 complete

**Parallel execution strategy:**
- Agent A: Phase 1 (Backend)
- Agent B: Phase 2 (Frontend)
- After both complete: Phase 3 (Integration)

**Total tasks:** 14
**Estimated parallelizable:** 11 tasks across 2 agents
