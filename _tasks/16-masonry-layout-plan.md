# Masonry Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace uniform 16:9 grid with masonry layout showing images at their natural aspect ratios.

**Architecture:** Backend adds width/height to image list responses. Frontend uses `@yeger/vue-masonry-wall` library to render variable-height cards. Cards calculate aspect ratio from image dimensions with caps for extreme ratios.

**Tech Stack:** FastAPI + Pillow (backend), Vue 3 + @yeger/vue-masonry-wall (frontend)

---

## Task 1: Add dimension caching to thumbnail service

**Files:**
- Modify: `src/services/thumbnails.py`

**Step 1: Add get_image_dimensions function**

Add this function after the existing imports and constants (around line 15):

```python
def get_dimensions_cache_path(image_path: str) -> Path:
    """Generate cache path for image dimensions JSON."""
    hash_key = hashlib.md5(f"{image_path}|dims".encode()).hexdigest()
    return CACHE_DIR / f"{hash_key}.dims"


def get_image_dimensions(image_path: Path) -> tuple[int, int]:
    """Get image dimensions, using cache if available.

    Returns: (width, height) tuple
    """
    cache_path = get_dimensions_cache_path(str(image_path))

    # Check cache first
    if cache_path.exists():
        try:
            data = cache_path.read_text()
            w, h = data.split(',')
            return (int(w), int(h))
        except Exception:
            pass  # Cache corrupted, regenerate

    # Read dimensions from image
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as img:
        width, height = img.size

    # Cache the result
    cache_path.write_text(f"{width},{height}")

    return (width, height)
```

**Step 2: Verify the function works**

Run Python REPL test:
```bash
cd /app && python -c "
from pathlib import Path
from src.services.thumbnails import get_image_dimensions, IMAGES_DIR

# Find first image
for p in IMAGES_DIR.rglob('*.jpg'):
    dims = get_image_dimensions(p)
    print(f'{p.name}: {dims}')
    break
"
```

Expected: Prints image name and (width, height) tuple.

**Step 3: Commit**

```bash
git add src/services/thumbnails.py
git commit -m "feat: add image dimension caching to thumbnail service"
```

---

## Task 2: Add dimensions to image list API

**Files:**
- Modify: `src/api/images.py`

**Step 1: Import the dimension function**

At line 6 (after the thumbnail import), update to:

```python
from src.services.thumbnails import generate_thumbnail, get_image_dimensions
```

**Step 2: Add dimensions to list_images response**

In the `list_images` function, update both places where images are appended (lines 37-41 and 51-55):

For the recursive listing (around line 37), change:
```python
                images.append({
                    "path": str(rel_path),
                    "name": path.name,
                    "size": path.stat().st_size
                })
```

To:
```python
                width, height = get_image_dimensions(path)
                images.append({
                    "path": str(rel_path),
                    "name": path.name,
                    "size": path.stat().st_size,
                    "width": width,
                    "height": height
                })
```

For the folder listing (around line 51), change:
```python
                images.append({
                    "path": str(rel_path),
                    "name": path.name,
                    "size": path.stat().st_size
                })
```

To:
```python
                width, height = get_image_dimensions(path)
                images.append({
                    "path": str(rel_path),
                    "name": path.name,
                    "size": path.stat().st_size,
                    "width": width,
                    "height": height
                })
```

**Step 3: Test the API**

```bash
curl -s http://localhost:8080/api/images | python -m json.tool | head -30
```

Expected: Each image object includes `"width"` and `"height"` fields.

**Step 4: Commit**

```bash
git add src/api/images.py
git commit -m "feat: add width/height to image list API response"
```

---

## Task 3: Add dimensions to TV artwork API

**Files:**
- Modify: `src/api/tv.py`

**Step 1: Update list_artwork to include dimensions placeholder**

The TV API doesn't provide dimensions, so we'll add default 16:9 dimensions. Later, we could fetch from the thumbnail, but for now we'll use defaults.

In `list_artwork` function (around line 144), change:

```python
@router.get("/artwork")
async def list_artwork():
    client = require_tv_client()
    try:
        artwork = await asyncio.to_thread(client.get_artwork_list)
        return {"artwork": artwork, "count": len(artwork)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

To:

```python
@router.get("/artwork")
async def list_artwork():
    client = require_tv_client()
    try:
        artwork = await asyncio.to_thread(client.get_artwork_list)
        # Add default dimensions (TV API doesn't provide them)
        # Using 16:9 as default since TV displays in that ratio
        for item in artwork:
            if "width" not in item:
                item["width"] = 1920
            if "height" not in item:
                item["height"] = 1080
        return {"artwork": artwork, "count": len(artwork)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

**Step 2: Test the API**

```bash
curl -s http://localhost:8080/api/tv/artwork | python -m json.tool | head -30
```

Expected: Each artwork object includes `"width": 1920` and `"height": 1080`.

**Step 3: Commit**

```bash
git add src/api/tv.py
git commit -m "feat: add default dimensions to TV artwork API response"
```

---

## Task 4: Fetch Met image dimensions from headers

**Files:**
- Modify: `src/services/met_client.py`

**Context:** The Met API provides `primaryImageWidth`/`primaryImageHeight` for many objects, but not all. When missing, `batch_fetch_objects` returns 0. We need to fetch actual dimensions from the image header.

**Step 1: Add function to fetch image dimensions from URL**

Add this function after the `fetch_image` method (around line 259):

```python
def fetch_image_dimensions(self, image_url: str) -> tuple[int, int]:
    """Fetch image dimensions by reading just the header bytes.

    Returns: (width, height) tuple, or (0, 0) on failure.
    """
    try:
        from PIL import Image
        from io import BytesIO

        _LOGGER.debug(f"Fetching dimensions for: {image_url}")
        req = urllib.request.Request(
            image_url,
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
            return img.size
    except Exception as e:
        _LOGGER.warning(f"Failed to fetch dimensions for {image_url}: {e}")
        return (0, 0)
```

**Step 2: Update batch_fetch_objects to fetch missing dimensions**

In `batch_fetch_objects` (around line 83), after building the result dict and before appending, add dimension fetching:

Change this section (around lines 98-112):

```python
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
```

To:

```python
                is_low_res = not obj.get("primaryImage")
                width = obj.get("primaryImageWidth") or 0
                height = obj.get("primaryImageHeight") or 0

                # Fetch dimensions from image header if not provided by API
                if width == 0 or height == 0:
                    small_url = obj.get("primaryImageSmall", primary)
                    width, height = self.fetch_image_dimensions(small_url)

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
```

**Step 3: Test the change**

```bash
curl -s "http://localhost:8080/api/met/highlights?page=1" | python -m json.tool | grep -A2 '"width"'
```

Expected: Objects show actual dimensions instead of 0.

**Step 4: Commit**

```bash
git add src/services/met_client.py
git commit -m "feat: fetch Met image dimensions from headers when API doesn't provide them"
```

---

## Task 5: Install masonry library

**Files:**
- Modify: `src/frontend/package.json`

**Step 1: Install the dependency**

```bash
cd src/frontend && npm install @yeger/vue-masonry-wall
```

**Step 2: Verify installation**

```bash
cat src/frontend/package.json | grep masonry
```

Expected: `"@yeger/vue-masonry-wall": "^X.X.X"` appears in dependencies.

**Step 3: Commit**

```bash
git add src/frontend/package.json src/frontend/package-lock.json
git commit -m "feat: add @yeger/vue-masonry-wall dependency"
```

---

## Task 6: Update ImageCard for dynamic aspect ratio

**Files:**
- Modify: `src/frontend/src/components/ImageCard.vue`

**Step 1: Add computed aspect ratio**

In the `<script setup>` section, after the `displayName` computed (around line 137), add:

```javascript
const computedAspectRatio = computed(() => {
  const w = props.image.width
  const h = props.image.height

  if (!w || !h) {
    return 16 / 9  // Default fallback
  }

  let ratio = w / h

  // Cap extreme ratios to prevent layout issues
  // Min 1:2 (portrait), Max 3:1 (landscape)
  ratio = Math.max(ratio, 0.5)   // No taller than 1:2
  ratio = Math.min(ratio, 3)     // No wider than 3:1

  return ratio
})
```

**Step 2: Update template to use dynamic aspect ratio**

Change the root div (line 4) from:

```vue
    class="image-card"
```

To:

```vue
    class="image-card"
    :style="{ aspectRatio: computedAspectRatio }"
```

**Step 3: Remove fixed padding from CSS**

In the `<style scoped>` section, find `.image-card` (around line 141) and remove the `padding-bottom` line:

```css
.image-card {
  position: relative;
  width: 100%;
  padding-bottom: 56.25%; /* 16:9 landscape aspect ratio */  /* REMOVE THIS LINE */
  border-radius: 8px;
  ...
}
```

So it becomes:

```css
.image-card {
  position: relative;
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 3px solid transparent;
  transition: border-color 0.2s, transform 0.2s;
  background: #2a2a4e;
}
```

**Step 4: Verify change compiles**

```bash
cd src/frontend && npm run build
```

Expected: Build succeeds without errors.

**Step 5: Commit**

```bash
git add src/frontend/src/components/ImageCard.vue
git commit -m "feat: update ImageCard to use dynamic aspect ratio from image dimensions"
```

---

## Task 7: Update ImageGrid to use MasonryWall

**Files:**
- Modify: `src/frontend/src/components/ImageGrid.vue`

**Step 1: Import MasonryWall**

At the top of the `<script setup>` section (after line 52), add the import:

```javascript
import { computed, ref, watch, onMounted, onUnmounted, provide } from 'vue'
import MasonryWall from '@yeger/vue-masonry-wall'
import ImageCard from './ImageCard.vue'
```

**Step 2: Replace the grid div with MasonryWall**

Replace the entire grid section in the template (lines 30-47):

```vue
    <div v-else ref="gridRef" class="grid" @scroll="onScroll">
      <ImageCard
        v-for="image in visibleImages"
        :key="image.path || image.object_id || image.content_id"
        :image="image"
        :selected="selectedIds.has(image.path || image.object_id || image.content_id)"
        :is-current="currentId === (image.content_id)"
        :is-local="isLocal"
        @toggle="$emit('toggle', image)"
        @preview="$emit('preview', image)"
      />
      <div v-if="hasMore" ref="sentinelRef" class="load-more-sentinel">
        <div v-if="loadingMore" class="loading-spinner">
          <div class="spinner"></div>
          <span>Loading more...</span>
        </div>
      </div>
    </div>
```

With:

```vue
    <div v-else ref="gridRef" class="grid-container" @scroll="onScroll">
      <MasonryWall
        :items="visibleImages"
        :column-width="180"
        :gap="16"
        :ssr-columns="4"
        :scroll-container="gridRef"
      >
        <template #default="{ item }">
          <ImageCard
            :image="item"
            :selected="selectedIds.has(item.path || item.object_id || item.content_id)"
            :is-current="currentId === (item.content_id)"
            :is-local="isLocal"
            @toggle="$emit('toggle', item)"
            @preview="$emit('preview', item)"
          />
        </template>
      </MasonryWall>
      <div v-if="hasMore" ref="sentinelRef" class="load-more-sentinel">
        <div v-if="loadingMore" class="loading-spinner">
          <div class="spinner"></div>
          <span>Loading more...</span>
        </div>
      </div>
    </div>
```

**Step 3: Update CSS for masonry container**

Replace the `.grid` CSS rule (around line 198) with:

```css
.grid-container {
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}
```

Remove the old `.grid` rule entirely.

**Step 4: Verify build**

```bash
cd src/frontend && npm run build
```

Expected: Build succeeds.

**Step 5: Commit**

```bash
git add src/frontend/src/components/ImageGrid.vue
git commit -m "feat: replace CSS grid with MasonryWall component"
```

---

## Task 8: Test end-to-end

**Step 1: Rebuild Docker container**

```bash
docker-compose up --build -d
```

**Step 2: Manual verification checklist**

Open browser to http://localhost:8080 and verify:

- [ ] Local images panel shows masonry layout with varying heights
- [ ] Portrait images are taller than landscape images
- [ ] Square images appear square
- [ ] Clicking checkbox still toggles selection
- [ ] Double-clicking still opens preview
- [ ] Infinite scroll still loads more images
- [ ] TV panel shows artwork (with default 16:9 ratio)
- [ ] Met panel shows artwork with varying aspect ratios
- [ ] Select All / Deselect All still work
- [ ] Upload functionality still works

**Step 3: Fix any issues found**

If issues are found, fix them before proceeding.

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete masonry layout implementation

- Add image dimension caching to thumbnail service
- Add width/height to image list API
- Add default dimensions to TV artwork API
- Install @yeger/vue-masonry-wall library
- Update ImageCard for dynamic aspect ratio
- Update ImageGrid to use MasonryWall component"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add dimension caching | `src/services/thumbnails.py` |
| 2 | Add dimensions to image API | `src/api/images.py` |
| 3 | Add dimensions to TV API | `src/api/tv.py` |
| 4 | Fetch Met image dimensions | `src/services/met_client.py` |
| 5 | Install masonry library | `package.json` |
| 6 | Update ImageCard | `ImageCard.vue` |
| 7 | Update ImageGrid | `ImageGrid.vue` |
| 8 | End-to-end testing | N/A |

Total estimated tasks: 8 (with ~4 steps each = ~32 individual steps)
