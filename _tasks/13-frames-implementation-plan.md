# Frame Cropping & Auto-Matte Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add server-side image processing to crop museum frames and add white matte for 16:9 aspect ratio before uploading to Samsung Frame TV.

**Architecture:** New `image_processor.py` service handles Pillow-based cropping and matte generation. Frontend replaces MatteSelector with CropSettings component + PreviewModal. Both LocalPanel and MetPanel use the new workflow. TV's native matte is bypassed (hardcoded to "none").

**Tech Stack:** Python/Pillow (backend image processing), Vue 3 (frontend components), FastAPI (preview endpoint)

---

## Task 1: Create Image Processor Service

**Files:**
- Create: `src/services/image_processor.py`

**Step 1: Create the image processor module**

```python
"""Image processing for TV upload: cropping and auto-matte."""
import io
from PIL import Image

TARGET_RATIO = 16 / 9  # Samsung Frame TV aspect ratio
MIN_MATTE_PERCENT = 0.12  # 12% of longer side


def process_for_tv(image_data: bytes, crop_percent: int = 0) -> bytes:
    """
    Process image for TV display:
    1. Crop: Remove crop_percent from all 4 edges
    2. Matte: Add white padding for 16:9 output

    Args:
        image_data: Raw image bytes (JPEG/PNG)
        crop_percent: Percentage to crop from each edge (0-50)

    Returns:
        PNG bytes ready for TV upload
    """
    # Load image
    img = Image.open(io.BytesIO(image_data))

    # Convert to RGB if necessary (handle RGBA, palette, etc.)
    if img.mode in ('RGBA', 'P', 'LA'):
        # Create white background for transparency
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Step 1: Crop
    if crop_percent > 0:
        img = _crop_image(img, crop_percent)

    # Step 2: Add matte for 16:9
    img = _add_matte(img)

    # Output as PNG
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    return output.getvalue()


def _crop_image(img: Image.Image, crop_percent: int) -> Image.Image:
    """Crop percentage from all 4 edges."""
    w, h = img.size
    crop_x = int(w * crop_percent / 100)
    crop_y = int(h * crop_percent / 100)

    left = crop_x
    top = crop_y
    right = w - crop_x
    bottom = h - crop_y

    return img.crop((left, top, right, bottom))


def _add_matte(img: Image.Image) -> Image.Image:
    """
    Add white matte padding to achieve 16:9 aspect ratio.

    Rules:
    - Minimum matte = 12% of image's longer side (on all sides)
    - Expand as needed to reach 16:9
    - Image centered on white canvas
    """
    w, h = img.size
    longer_side = max(w, h)
    min_matte = int(longer_side * MIN_MATTE_PERCENT)

    # Start with minimum matte on all sides
    canvas_w = w + (min_matte * 2)
    canvas_h = h + (min_matte * 2)

    # Adjust to 16:9
    current_ratio = canvas_w / canvas_h

    if current_ratio < TARGET_RATIO:
        # Too tall - expand width
        canvas_w = int(canvas_h * TARGET_RATIO)
    elif current_ratio > TARGET_RATIO:
        # Too wide - expand height
        canvas_h = int(canvas_w / TARGET_RATIO)

    # Create white canvas and paste image centered
    canvas = Image.new('RGB', (canvas_w, canvas_h), (255, 255, 255))
    paste_x = (canvas_w - w) // 2
    paste_y = (canvas_h - h) // 2
    canvas.paste(img, (paste_x, paste_y))

    return canvas


def generate_preview(image_data: bytes, crop_percent: int = 0) -> tuple[bytes, bytes]:
    """
    Generate preview images for comparison.

    Returns:
        Tuple of (original_thumbnail, processed_thumbnail) as JPEG bytes
    """
    # Original thumbnail
    original = Image.open(io.BytesIO(image_data))
    if original.mode not in ('RGB', 'L'):
        original = original.convert('RGB')
    original.thumbnail((400, 400), Image.Resampling.LANCZOS)

    orig_output = io.BytesIO()
    original.save(orig_output, format='JPEG', quality=85)

    # Processed thumbnail
    processed_full = process_for_tv(image_data, crop_percent)
    processed = Image.open(io.BytesIO(processed_full))
    processed.thumbnail((400, 400), Image.Resampling.LANCZOS)

    proc_output = io.BytesIO()
    processed.save(proc_output, format='JPEG', quality=85)

    return orig_output.getvalue(), proc_output.getvalue()
```

**Step 2: Verify module loads without errors**

Run: `cd C:\_dev\samsung-frame-art-gallery && python -c "from src.services.image_processor import process_for_tv, generate_preview; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add src/services/image_processor.py
git commit -m "feat: add image processor service for crop and matte"
```

---

## Task 2: Add Preview API Endpoint

**Files:**
- Modify: `src/api/tv.py`
- Modify: `src/api/met.py`

**Step 1: Add preview endpoint to tv.py**

Add imports at top of `src/api/tv.py`:

```python
import base64
from src.services.image_processor import process_for_tv, generate_preview
```

Add new request model after `UploadRequest`:

```python
class PreviewRequest(BaseModel):
    paths: list[str]
    crop_percent: int = 0
```

Add new endpoint before the `/upload` endpoint:

```python
@router.post("/preview")
async def preview_processed(request: PreviewRequest):
    """Generate preview of processed images (cropped + matted)."""
    results = []

    for path in request.paths:
        try:
            image_path = get_safe_path(path)
            if not image_path.exists():
                results.append({"path": path, "success": False, "error": "File not found"})
                continue

            image_data = image_path.read_bytes()
            original, processed = await asyncio.to_thread(
                generate_preview, image_data, request.crop_percent
            )

            results.append({
                "path": path,
                "success": True,
                "original": base64.b64encode(original).decode('utf-8'),
                "processed": base64.b64encode(processed).decode('utf-8')
            })
        except Exception as e:
            results.append({"path": path, "success": False, "error": str(e)})

    return {"results": results}
```

**Step 2: Add preview endpoint to met.py**

Add imports at top of `src/api/met.py`:

```python
import base64
from src.services.image_processor import generate_preview
```

Add new request model after `MetUploadRequest`:

```python
class MetPreviewRequest(BaseModel):
    object_ids: list[int]
    crop_percent: int = 0
```

Add new endpoint before the `/upload` endpoint:

```python
@router.post("/preview")
async def preview_met_artwork(request: MetPreviewRequest):
    """Generate preview of processed Met artwork (cropped + matted)."""
    met_client = get_met_client()
    results = []

    for object_id in request.object_ids:
        try:
            obj = await asyncio.to_thread(met_client.get_object, object_id)
            if not obj:
                results.append({"object_id": object_id, "success": False, "error": "Object not found"})
                continue

            image_url = obj.get("primaryImage") or obj.get("primaryImageSmall")
            if not image_url:
                results.append({"object_id": object_id, "success": False, "error": "No image available"})
                continue

            image_data = await asyncio.to_thread(met_client.fetch_image, image_url)
            original, processed = await asyncio.to_thread(
                generate_preview, image_data, request.crop_percent
            )

            results.append({
                "object_id": object_id,
                "success": True,
                "title": obj.get("title", "Untitled"),
                "original": base64.b64encode(original).decode('utf-8'),
                "processed": base64.b64encode(processed).decode('utf-8')
            })
        except Exception as e:
            results.append({"object_id": object_id, "success": False, "error": str(e)})

    return {"results": results}
```

**Step 3: Verify server starts**

Run: `cd C:\_dev\samsung-frame-art-gallery && python -c "from src.api.tv import router; from src.api.met import router; print('OK')"`

Expected: `OK`

**Step 4: Commit**

```bash
git add src/api/tv.py src/api/met.py
git commit -m "feat: add preview endpoints for crop/matte preview"
```

---

## Task 3: Update Upload Endpoints to Use Image Processor

**Files:**
- Modify: `src/api/tv.py`
- Modify: `src/api/met.py`
- Modify: `src/services/tv_client.py`

**Step 1: Update UploadRequest in tv.py**

Replace the existing `UploadRequest` class:

```python
class UploadRequest(BaseModel):
    paths: list[str]
    crop_percent: int = 0
    display: bool = False
```

**Step 2: Update upload endpoint in tv.py**

Replace the `/upload` endpoint implementation:

```python
@router.post("/upload")
async def upload_artwork(request: UploadRequest):
    client = require_tv_client()
    results = []

    for path in request.paths:
        try:
            image_path = get_safe_path(path)
            if not image_path.exists():
                results.append({"path": path, "success": False, "error": "File not found"})
                continue

            image_data = image_path.read_bytes()

            # Process image (crop + matte)
            processed_data = await asyncio.to_thread(
                process_for_tv, image_data, request.crop_percent
            )

            # Run blocking TV upload in thread pool
            result = await asyncio.to_thread(
                client.upload_artwork,
                processed_data,
                request.display and len(request.paths) == 1
            )
            results.append({"path": path, "success": True, "result": result})
        except Exception as e:
            results.append({"path": path, "success": False, "error": str(e)})

    # If display requested and multiple images, display the last one
    if request.display and len(request.paths) > 1:
        last_success = next((r for r in reversed(results) if r["success"]), None)
        if last_success and "content_id" in last_success.get("result", {}):
            try:
                await asyncio.to_thread(
                    client.set_current_artwork,
                    last_success["result"]["content_id"]
                )
            except:
                pass

    return {"results": results}
```

**Step 3: Update MetUploadRequest in met.py**

Replace the existing `MetUploadRequest` class:

```python
class MetUploadRequest(BaseModel):
    object_ids: list[int]
    crop_percent: int = 0
    display: bool = False
```

**Step 4: Update upload endpoint in met.py**

Add import at top:

```python
from src.services.image_processor import process_for_tv
```

Replace the `/upload` endpoint implementation:

```python
@router.post("/upload")
async def upload_met_artwork(request: MetUploadRequest):
    """Download Met artwork, process, and upload to TV."""
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

            # Process image (crop + matte)
            processed_data = await asyncio.to_thread(
                process_for_tv, image_data, request.crop_percent
            )

            # Upload to TV
            display_this = request.display and object_id == request.object_ids[-1]
            result = await asyncio.to_thread(
                tv_client.upload_artwork,
                processed_data,
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

**Step 5: Simplify tv_client.upload_artwork**

Replace the `upload_artwork` method in `src/services/tv_client.py`:

```python
def upload_artwork(self, image_data: bytes, display: bool = False) -> dict:
    tv = self._get_tv()
    # Always use no matte - we add our own white matte server-side
    result = tv.art().upload(image_data, matte="none", portrait_matte="none")
    if display and result:
        content_id = result.get("content_id")
        if content_id:
            tv.art().select_image(content_id)
    return result or {}
```

**Step 6: Remove unused matte methods from tv_client.py**

Delete the `get_matte_options` method (lines 199-245 approximately).

**Step 7: Remove /mattes endpoint from tv.py**

Delete this endpoint:

```python
@router.get("/mattes")
async def get_mattes():
    client = require_tv_client()
    return client.get_matte_options()
```

**Step 8: Verify server starts**

Run: `cd C:\_dev\samsung-frame-art-gallery && python -c "from src.main import app; print('OK')"`

Expected: `OK`

**Step 9: Commit**

```bash
git add src/api/tv.py src/api/met.py src/services/tv_client.py
git commit -m "feat: integrate image processor into upload flow, remove TV matte"
```

---

## Task 4: Create CropSettings Component

**Files:**
- Create: `src/frontend/src/components/CropSettings.vue`

**Step 1: Create the CropSettings component**

```vue
<template>
  <div class="crop-settings">
    <div class="crop-field">
      <label>Crop:</label>
      <input
        type="number"
        v-model.number="cropPercent"
        min="0"
        max="50"
        @input="emitChange"
      />
      <span class="unit">%</span>
    </div>
    <button
      class="preview-btn"
      :disabled="!canPreview"
      @click="$emit('preview')"
    >
      Preview
    </button>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  canPreview: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['change', 'preview'])

const cropPercent = ref(0)

const emitChange = () => {
  // Clamp value to valid range
  if (cropPercent.value < 0) cropPercent.value = 0
  if (cropPercent.value > 50) cropPercent.value = 50
  emit('change', cropPercent.value)
}

// Emit initial value
emitChange()
</script>

<style scoped>
.crop-settings {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.crop-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.crop-field label {
  font-size: 0.9rem;
  color: #aaa;
}

.crop-field input {
  width: 60px;
  padding: 0.4rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
  text-align: right;
}

.crop-field input::-webkit-inner-spin-button,
.crop-field input::-webkit-outer-spin-button {
  opacity: 1;
}

.unit {
  font-size: 0.9rem;
  color: #aaa;
}

.preview-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
  cursor: pointer;
  font-size: 0.9rem;
}

.preview-btn:hover:not(:disabled) {
  background: #3a3a5e;
}

.preview-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
```

**Step 2: Commit**

```bash
git add src/frontend/src/components/CropSettings.vue
git commit -m "feat: add CropSettings component"
```

---

## Task 5: Create PreviewModal Component

**Files:**
- Create: `src/frontend/src/components/PreviewModal.vue`

**Step 1: Create the PreviewModal component**

```vue
<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Preview (Crop: {{ cropPercent }}%)</h3>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">
        <div v-if="loading" class="loading">
          Loading previews...
        </div>

        <div v-else class="preview-list">
          <div v-for="item in previews" :key="item.id" class="preview-item">
            <div class="preview-images">
              <div class="preview-image">
                <img :src="'data:image/jpeg;base64,' + item.original" alt="Original" />
                <span class="label">Original</span>
              </div>
              <div class="preview-image">
                <img :src="'data:image/jpeg;base64,' + item.processed" alt="Processed" />
                <span class="label">Cropped + Matte</span>
              </div>
            </div>
            <div class="preview-name">{{ item.name }}</div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="secondary" @click="$emit('close')">Cancel</button>
        <button class="primary" @click="$emit('upload')" :disabled="loading">
          Upload All
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  previews: {
    type: Array,
    required: true
  },
  cropPercent: {
    type: Number,
    default: 0
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['close', 'upload'])
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: #1a1a2e;
  border-radius: 8px;
  max-width: 900px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  border: 1px solid #2a2a4e;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #2a2a4e;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.close-btn {
  background: transparent;
  border: none;
  color: #888;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: white;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #888;
}

.preview-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.preview-item {
  border-bottom: 1px solid #2a2a4e;
  padding-bottom: 1.5rem;
}

.preview-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.preview-images {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.preview-image {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.preview-image img {
  max-width: 350px;
  max-height: 250px;
  object-fit: contain;
  border-radius: 4px;
  background: #2a2a4e;
}

.preview-image .label {
  font-size: 0.85rem;
  color: #888;
}

.preview-name {
  text-align: center;
  margin-top: 0.5rem;
  font-size: 0.9rem;
  color: #ccc;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid #2a2a4e;
}

.modal-footer button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-weight: 500;
}

.modal-footer button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-footer button.primary {
  background: #4a90d9;
  color: white;
}

.modal-footer button.secondary {
  background: #3a3a5e;
  color: white;
}

@media (max-width: 700px) {
  .preview-images {
    flex-direction: column;
    align-items: center;
  }

  .preview-image img {
    max-width: 100%;
  }
}
</style>
```

**Step 2: Commit**

```bash
git add src/frontend/src/components/PreviewModal.vue
git commit -m "feat: add PreviewModal component for side-by-side comparison"
```

---

## Task 6: Update LocalPanel to Use New Components

**Files:**
- Modify: `src/frontend/src/views/LocalPanel.vue`

**Step 1: Replace imports**

Replace the MatteSelector import with new components:

```javascript
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import CropSettings from '../components/CropSettings.vue'
import PreviewModal from '../components/PreviewModal.vue'
```

**Step 2: Update reactive state**

Replace `const matte = ref({ style: 'none', color: 'neutral' })` with:

```javascript
const cropPercent = ref(0)
const showPreview = ref(false)
const previewLoading = ref(false)
const previews = ref([])
```

**Step 3: Add preview function**

Add after the `selectAll` function:

```javascript
const loadPreviews = async () => {
  if (selectedIds.value.size === 0) return

  previewLoading.value = true
  showPreview.value = true
  previews.value = []

  try {
    const res = await fetch('/api/tv/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        paths: Array.from(selectedIds.value),
        crop_percent: cropPercent.value
      })
    })
    const data = await res.json()

    previews.value = data.results
      .filter(r => r.success)
      .map(r => ({
        id: r.path,
        name: r.path.split('/').pop(),
        original: r.original,
        processed: r.processed
      }))
  } catch (e) {
    console.error('Failed to load previews:', e)
  } finally {
    previewLoading.value = false
  }
}

const uploadFromPreview = async () => {
  showPreview.value = false
  await upload(true)
}
```

**Step 4: Update upload function**

Replace the upload function body:

```javascript
const upload = async (display) => {
  if (selectedIds.value.size === 0) return

  uploading.value = true
  try {
    const res = await fetch('/api/tv/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        paths: Array.from(selectedIds.value),
        crop_percent: cropPercent.value,
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
```

**Step 5: Update template ActionBar section**

Replace the ActionBar section in template:

```vue
<ActionBar>
  <template #left>
    <CropSettings
      :can-preview="selectedIds.size > 0"
      @change="cropPercent = $event"
      @preview="loadPreviews"
    />
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

<PreviewModal
  v-if="showPreview"
  :previews="previews"
  :crop-percent="cropPercent"
  :loading="previewLoading"
  @close="showPreview = false"
  @upload="uploadFromPreview"
/>
```

**Step 6: Verify no syntax errors**

Run: `cd C:\_dev\samsung-frame-art-gallery\src\frontend && npm run build 2>&1 | head -20`

Expected: Build succeeds or only shows unrelated warnings

**Step 7: Commit**

```bash
git add src/frontend/src/views/LocalPanel.vue
git commit -m "feat: update LocalPanel with crop settings and preview modal"
```

---

## Task 7: Update MetPanel to Use New Components

**Files:**
- Modify: `src/frontend/src/views/MetPanel.vue`

**Step 1: Replace imports**

Replace the MatteSelector import with new components:

```javascript
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import CropSettings from '../components/CropSettings.vue'
import PreviewModal from '../components/PreviewModal.vue'
import ResolutionWarning from '../components/ResolutionWarning.vue'
```

**Step 2: Update reactive state**

Replace `const matte = ref({ style: 'none', color: 'neutral' })` with:

```javascript
const cropPercent = ref(0)
const showPreview = ref(false)
const previewLoading = ref(false)
const previews = ref([])
```

**Step 3: Add preview function**

Add after the `selectAll` function:

```javascript
const loadPreviews = async () => {
  if (selectedIds.value.size === 0) return

  previewLoading.value = true
  showPreview.value = true
  previews.value = []

  try {
    const res = await fetch('/api/met/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        object_ids: Array.from(selectedIds.value),
        crop_percent: cropPercent.value
      })
    })
    const data = await res.json()

    previews.value = data.results
      .filter(r => r.success)
      .map(r => ({
        id: r.object_id,
        name: r.title || `Object ${r.object_id}`,
        original: r.original,
        processed: r.processed
      }))
  } catch (e) {
    console.error('Failed to load previews:', e)
  } finally {
    previewLoading.value = false
  }
}

const uploadFromPreview = async () => {
  showPreview.value = false
  await doUpload(true)
}
```

**Step 4: Update doUpload function**

Replace the doUpload function body:

```javascript
const doUpload = async (display) => {
  uploading.value = true
  try {
    const res = await fetch('/api/met/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        object_ids: Array.from(selectedIds.value),
        crop_percent: cropPercent.value,
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
```

**Step 5: Update template ActionBar section**

Replace the ActionBar section in template:

```vue
<ActionBar>
  <template #left>
    <CropSettings
      :can-preview="selectedIds.size > 0"
      @change="cropPercent = $event"
      @preview="loadPreviews"
    />
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

<PreviewModal
  v-if="showPreview"
  :previews="previews"
  :crop-percent="cropPercent"
  :loading="previewLoading"
  @close="showPreview = false"
  @upload="uploadFromPreview"
/>
```

**Step 6: Verify no syntax errors**

Run: `cd C:\_dev\samsung-frame-art-gallery\src\frontend && npm run build 2>&1 | head -20`

Expected: Build succeeds or only shows unrelated warnings

**Step 7: Commit**

```bash
git add src/frontend/src/views/MetPanel.vue
git commit -m "feat: update MetPanel with crop settings and preview modal"
```

---

## Task 8: Delete MatteSelector Component

**Files:**
- Delete: `src/frontend/src/components/MatteSelector.vue`

**Step 1: Delete the file**

```bash
rm src/frontend/src/components/MatteSelector.vue
```

**Step 2: Verify build still works**

Run: `cd C:\_dev\samsung-frame-art-gallery\src\frontend && npm run build`

Expected: Build succeeds

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove unused MatteSelector component"
```

---

## Task 9: Final Integration Test

**Step 1: Rebuild and start Docker**

```bash
cd C:\_dev\samsung-frame-art-gallery
docker-compose down
docker-compose up --build -d
```

**Step 2: Test local panel workflow**

1. Open http://localhost:8080
2. Go to Local tab
3. Select an image
4. Set crop to 5%
5. Click Preview - verify side-by-side modal appears
6. Click Upload All - verify upload succeeds

**Step 3: Test Met panel workflow**

1. Go to Met tab
2. Select an artwork
3. Set crop to 10%
4. Click Preview - verify side-by-side modal appears
5. Click Upload All - verify upload succeeds

**Step 4: Commit final state**

```bash
git add -A
git commit -m "feat: complete frame cropping and auto-matte implementation"
```

---

## Summary of Changes

**New Files:**
- `src/services/image_processor.py` - Crop and matte logic
- `src/frontend/src/components/CropSettings.vue` - Crop input + preview button
- `src/frontend/src/components/PreviewModal.vue` - Side-by-side comparison modal

**Modified Files:**
- `src/api/tv.py` - Updated UploadRequest, added /preview endpoint, removed /mattes
- `src/api/met.py` - Updated MetUploadRequest, added /preview endpoint
- `src/services/tv_client.py` - Simplified upload_artwork, removed get_matte_options
- `src/frontend/src/views/LocalPanel.vue` - Use CropSettings + PreviewModal
- `src/frontend/src/views/MetPanel.vue` - Use CropSettings + PreviewModal

**Deleted Files:**
- `src/frontend/src/components/MatteSelector.vue`
