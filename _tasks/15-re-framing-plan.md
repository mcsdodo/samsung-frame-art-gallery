# Re-framing Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "Re-framing" option that crops images to fill 16:9 frame with user-adjustable positioning.

**Architecture:** Checkbox in CropSettings enables reframe mode, which disables crop/matte. PreviewModal gets draggable image positioning for single images. Backend adds `_reframe_image()` function that scales and crops to fill 16:9.

**Tech Stack:** Vue 3, FastAPI, Pillow, CSS transforms for drag interaction.

---

## Task 1: Backend - Add Reframe Processing Function

**Files:**
- Modify: `src/services/image_processor.py`

**Step 1: Add the `_reframe_image` function after `_crop_image`**

In `src/services/image_processor.py`, add after line 65 (after `_crop_image` function):

```python
def _reframe_image(img: Image.Image, offset_x: float = 0.5, offset_y: float = 0.5) -> Image.Image:
    """
    Scale and crop image to fill 16:9 frame exactly.

    Args:
        img: Source image
        offset_x: Horizontal position 0.0 (left) to 1.0 (right), 0.5 = center
        offset_y: Vertical position 0.0 (top) to 1.0 (bottom), 0.5 = center

    Returns:
        Image cropped to exact 16:9 aspect ratio
    """
    w, h = img.size
    current_ratio = w / h

    if current_ratio > TARGET_RATIO:
        # Image is wider than 16:9 - crop sides
        new_w = int(h * TARGET_RATIO)
        new_h = h
        max_offset = w - new_w
        left = int(max_offset * offset_x)
        top = 0
    else:
        # Image is taller than 16:9 - crop top/bottom
        new_w = w
        new_h = int(w / TARGET_RATIO)
        max_offset = h - new_h
        left = 0
        top = int(max_offset * offset_y)

    return img.crop((left, top, left + new_w, top + new_h))
```

**Step 2: Update `process_for_tv` signature and logic**

Replace the `process_for_tv` function (lines 10-51) with:

```python
def process_for_tv(
    image_data: bytes,
    crop_percent: int = 0,
    matte_percent: int = None,
    reframe_enabled: bool = False,
    reframe_offset_x: float = 0.5,
    reframe_offset_y: float = 0.5
) -> bytes:
    """
    Process image for TV display:
    - If reframe_enabled: Scale/crop to fill 16:9 exactly
    - Otherwise: Crop edges, then add matte for 16:9

    Args:
        image_data: Raw image bytes (JPEG/PNG)
        crop_percent: Percentage to crop from each edge (0-50)
        matte_percent: Minimum matte as % of longer side (default from env)
        reframe_enabled: If True, fill frame completely (no matte)
        reframe_offset_x: Horizontal crop position (0.0-1.0)
        reframe_offset_y: Vertical crop position (0.0-1.0)

    Returns:
        PNG bytes ready for TV upload
    """
    if matte_percent is None:
        matte_percent = DEFAULT_MATTE_PERCENT

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

    if reframe_enabled:
        # Reframe mode: fill 16:9 completely
        img = _reframe_image(img, reframe_offset_x, reframe_offset_y)
    else:
        # Standard mode: crop then matte
        if crop_percent > 0:
            img = _crop_image(img, crop_percent)
        img = _add_matte(img, matte_percent)

    # Output as PNG
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    return output.getvalue()
```

**Step 3: Update `generate_preview` signature**

Replace the `generate_preview` function (lines 104-128) with:

```python
def generate_preview(
    image_data: bytes,
    crop_percent: int = 0,
    matte_percent: int = None,
    reframe_enabled: bool = False,
    reframe_offset_x: float = 0.5,
    reframe_offset_y: float = 0.5
) -> tuple[bytes, bytes]:
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
    processed_full = process_for_tv(
        image_data, crop_percent, matte_percent,
        reframe_enabled, reframe_offset_x, reframe_offset_y
    )
    processed = Image.open(io.BytesIO(processed_full))
    processed.thumbnail((400, 400), Image.Resampling.LANCZOS)

    proc_output = io.BytesIO()
    processed.save(proc_output, format='JPEG', quality=85)

    return orig_output.getvalue(), proc_output.getvalue()
```

**Step 4: Verify changes compile**

Run: `cd C:\_dev\samsung-frame-art-gallery && python -c "from src.services.image_processor import process_for_tv, generate_preview; print('OK')"`

Expected: `OK`

**Step 5: Commit**

```bash
git add src/services/image_processor.py
git commit -m "feat: add reframe image processing for 16:9 fill"
```

---

## Task 2: Backend - Update API Models and Endpoints

**Files:**
- Modify: `src/api/tv.py`

**Step 1: Update PreviewRequest model**

Replace lines 42-45:

```python
class PreviewRequest(BaseModel):
    paths: list[str]
    crop_percent: int = 0
    matte_percent: int = 10
    reframe_enabled: bool = False
    reframe_offsets: dict[str, dict] = {}  # path -> {"x": 0.5, "y": 0.5}
```

**Step 2: Update UploadRequest model**

Replace lines 48-52:

```python
class UploadRequest(BaseModel):
    paths: list[str]
    crop_percent: int = 0
    matte_percent: int = 10
    display: bool = False
    reframe_enabled: bool = False
    reframe_offsets: dict[str, dict] = {}  # path -> {"x": 0.5, "y": 0.5}
```

**Step 3: Update preview endpoint to use reframe params**

Replace the `process_single_preview` inner function in the `/preview` endpoint (lines 199-224) with:

```python
    async def process_single_preview(path: str):
        try:
            image_path = get_safe_path(path)
            if not image_path.exists():
                return None

            # Get reframe offset for this path (default center)
            offset = request.reframe_offsets.get(path, {"x": 0.5, "y": 0.5})
            offset_x = offset.get("x", 0.5)
            offset_y = offset.get("y", 0.5)

            # Check cache first (only for non-reframe or center-positioned reframe)
            cache_key_valid = not request.reframe_enabled or (offset_x == 0.5 and offset_y == 0.5)
            if cache_key_valid:
                cached = cache.get(path, request.crop_percent, request.matte_percent)
                if cached:
                    original, processed = cached
                    return {
                        "id": path,
                        "name": image_path.name,
                        "original_url": f"data:image/jpeg;base64,{base64.b64encode(original).decode('utf-8')}",
                        "processed_url": f"data:image/jpeg;base64,{base64.b64encode(processed).decode('utf-8')}"
                    }

            image_data = image_path.read_bytes()
            original, processed = await asyncio.to_thread(
                generate_preview,
                image_data,
                request.crop_percent,
                request.matte_percent,
                request.reframe_enabled,
                offset_x,
                offset_y
            )

            # Cache only stable results
            if cache_key_valid:
                cache.set(path, request.crop_percent, request.matte_percent, original, processed)

            return {
                "id": path,
                "name": image_path.name,
                "original_url": f"data:image/jpeg;base64,{base64.b64encode(original).decode('utf-8')}",
                "processed_url": f"data:image/jpeg;base64,{base64.b64encode(processed).decode('utf-8')}"
            }
        except Exception:
            return None  # Skip failed previews silently
```

**Step 4: Update upload endpoint to use reframe params**

Replace the `read_and_process` inner function in the `/upload` endpoint (lines 237-251) with:

```python
    async def read_and_process(path: str):
        """Read and process image in parallel, return processed data and metadata."""
        try:
            image_path = get_safe_path(path)
            if not image_path.exists():
                return {"path": path, "success": False, "error": "File not found"}

            # Get reframe offset for this path (default center)
            offset = request.reframe_offsets.get(path, {"x": 0.5, "y": 0.5})
            offset_x = offset.get("x", 0.5)
            offset_y = offset.get("y", 0.5)

            image_data = image_path.read_bytes()
            processed_data = await asyncio.to_thread(
                process_for_tv,
                image_data,
                request.crop_percent,
                request.matte_percent,
                request.reframe_enabled,
                offset_x,
                offset_y
            )

            return {"path": path, "processed_data": processed_data}
        except Exception as e:
            return {"path": path, "success": False, "error": str(e)}
```

**Step 5: Verify server starts**

Run: `cd C:\_dev\samsung-frame-art-gallery && python -c "from src.api.tv import router; print('OK')"`

Expected: `OK`

**Step 6: Commit**

```bash
git add src/api/tv.py
git commit -m "feat: add reframe parameters to preview and upload endpoints"
```

---

## Task 3: Frontend - Add Reframe Checkbox to CropSettings

**Files:**
- Modify: `src/frontend/src/components/CropSettings.vue`

**Step 1: Update template with reframe checkbox**

Replace the entire `<template>` section (lines 1-35) with:

```vue
<template>
  <div class="crop-settings">
    <div class="reframe-field">
      <label class="checkbox-label">
        <input
          type="checkbox"
          v-model="reframeValue"
          @change="emitChange"
        />
        Re-framing
      </label>
    </div>
    <div class="crop-field" :class="{ disabled: reframeValue }">
      <label>Crop:</label>
      <input
        type="number"
        v-model.number="cropValue"
        min="0"
        max="50"
        step="1"
        :disabled="reframeValue"
        @input="emitChange"
      />
      <span class="unit">%</span>
    </div>
    <div class="crop-field" :class="{ disabled: reframeValue }">
      <label>Matte:</label>
      <input
        type="number"
        v-model.number="matteValue"
        min="0"
        max="50"
        step="1"
        :disabled="reframeValue"
        @input="emitChange"
      />
      <span class="unit">%</span>
    </div>
    <button
      class="preview-btn"
      @click="$emit('preview')"
      :disabled="!hasSelection"
    >
      Preview
    </button>
  </div>
</template>
```

**Step 2: Update script to include reframeValue**

Replace the entire `<script setup>` section (lines 37-71) with:

```vue
<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['change', 'preview'])
const props = defineProps({
  hasSelection: {
    type: Boolean,
    default: false
  }
})

const reframeValue = ref(false)
const cropValue = ref(0)
const matteValue = ref(10)

const emitChange = () => {
  emit('change', {
    crop: cropValue.value,
    matte: matteValue.value,
    reframe: reframeValue.value
  })
}

onMounted(async () => {
  try {
    const res = await fetch('/api/tv/config')
    const data = await res.json()
    if (data.default_crop_percent !== undefined) {
      cropValue.value = data.default_crop_percent
    }
    if (data.default_matte_percent !== undefined) {
      matteValue.value = data.default_matte_percent
    }
    emitChange()
  } catch (e) {
    // Use defaults if config fetch fails
    emitChange()
  }
})
</script>
```

**Step 3: Update styles for reframe checkbox and disabled state**

Replace the entire `<style scoped>` section (lines 73-129) with:

```vue
<style scoped>
.crop-settings {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.reframe-field {
  display: flex;
  align-items: center;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  color: #ccc;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.crop-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: opacity 0.2s;
}

.crop-field.disabled {
  opacity: 0.4;
  pointer-events: none;
}

.crop-field label {
  font-size: 0.9rem;
  color: #aaa;
}

.crop-field input[type="number"] {
  width: 70px;
  padding: 0.4rem 0.6rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
}

.crop-field input[type="number"]:focus {
  outline: none;
  border-color: #4a90d9;
}

.crop-field input[type="number"]:disabled {
  background: #1a1a2e;
  color: #666;
}

.crop-field .unit {
  font-size: 0.9rem;
  color: #aaa;
}

.preview-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #3a3a5e;
  color: white;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.preview-btn:hover:not(:disabled) {
  background: #4a4a6e;
}

.preview-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
```

**Step 4: Verify frontend compiles**

Run: `cd C:\_dev\samsung-frame-art-gallery\src\frontend && npm run build 2>&1 | head -20`

Expected: Build succeeds (may have warnings, no errors)

**Step 5: Commit**

```bash
git add src/frontend/src/components/CropSettings.vue
git commit -m "feat: add re-framing checkbox to CropSettings"
```

---

## Task 4: Frontend - Wire Reframe State in LocalPanel

**Files:**
- Modify: `src/frontend/src/views/LocalPanel.vue`

**Step 1: Add reframe state refs**

After line 81 (`const previews = ref([])`), add:

```javascript
const reframeEnabled = ref(false)
const reframeOffsets = ref({})  // path -> {x, y}
```

**Step 2: Update setSettings to handle reframe**

Replace the `setSettings` function (lines 128-131) with:

```javascript
const setSettings = (settings) => {
  cropPercent.value = settings.crop
  mattePercent.value = settings.matte
  reframeEnabled.value = settings.reframe || false
}
```

**Step 3: Update loadPreviews to pass reframe params**

Replace the `loadPreviews` function (lines 133-157) with:

```javascript
const loadPreviews = async () => {
  if (selectedIds.value.size === 0) return

  showPreview.value = true
  previewLoading.value = false  // Don't show loading initially for reframe
  previews.value = []

  // Reset offsets when opening preview
  reframeOffsets.value = {}

  // For reframe mode with single image, we don't fetch preview immediately
  // The PreviewModal handles initial display and offset updates
  if (reframeEnabled.value && selectedIds.value.size === 1) {
    previewLoading.value = false
    return
  }

  previewLoading.value = true

  try {
    const res = await fetch('/api/tv/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        paths: Array.from(selectedIds.value),
        crop_percent: cropPercent.value,
        matte_percent: mattePercent.value,
        reframe_enabled: reframeEnabled.value,
        reframe_offsets: reframeOffsets.value
      })
    })
    const data = await res.json()
    previews.value = data.previews || []
  } catch (e) {
    console.error('Preview failed:', e)
  } finally {
    previewLoading.value = false
  }
}
```

**Step 4: Add function to fetch preview with offset**

After `loadPreviews`, add:

```javascript
const fetchPreviewWithOffset = async (path, offsetX, offsetY) => {
  // Update stored offset
  reframeOffsets.value = {
    ...reframeOffsets.value,
    [path]: { x: offsetX, y: offsetY }
  }

  try {
    const res = await fetch('/api/tv/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        paths: [path],
        crop_percent: cropPercent.value,
        matte_percent: mattePercent.value,
        reframe_enabled: true,
        reframe_offsets: { [path]: { x: offsetX, y: offsetY } }
      })
    })
    const data = await res.json()
    if (data.previews && data.previews.length > 0) {
      previews.value = data.previews
    }
  } catch (e) {
    console.error('Preview update failed:', e)
  }
}
```

**Step 5: Update upload to include reframe params**

Replace the `upload` function (lines 164-188) with:

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
        matte_percent: mattePercent.value,
        display,
        reframe_enabled: reframeEnabled.value,
        reframe_offsets: reframeOffsets.value
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

**Step 6: Update PreviewModal props in template**

Replace lines 50-58 (the PreviewModal component) with:

```vue
    <PreviewModal
      v-if="showPreview"
      :previews="previews"
      :crop-percent="cropPercent"
      :matte-percent="mattePercent"
      :loading="previewLoading"
      :reframe-enabled="reframeEnabled"
      :selected-paths="Array.from(selectedIds)"
      @close="showPreview = false"
      @upload="uploadFromPreview"
      @offset-change="fetchPreviewWithOffset"
    />
```

**Step 7: Verify frontend compiles**

Run: `cd C:\_dev\samsung-frame-art-gallery\src\frontend && npm run build 2>&1 | head -20`

Expected: Build succeeds

**Step 8: Commit**

```bash
git add src/frontend/src/views/LocalPanel.vue
git commit -m "feat: wire reframe state and API calls in LocalPanel"
```

---

## Task 5: Frontend - Add Draggable Reframe UI to PreviewModal

**Files:**
- Modify: `src/frontend/src/components/PreviewModal.vue`

**Step 1: Update template for reframe mode**

Replace the entire `<template>` section (lines 1-46) with:

```vue
<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2 v-if="reframeEnabled">Re-framing Preview</h2>
        <h2 v-else>Preview (Crop: {{ cropPercent }}%, Matte: {{ mattePercent }}%)</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <!-- Reframe info message for multiple images -->
      <div v-if="reframeEnabled && selectedPaths.length > 1" class="info-banner">
        Re-framing uses center crop for multiple images. Select a single image for manual positioning.
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Generating previews...</p>
      </div>

      <!-- Single image reframe mode with drag -->
      <div v-else-if="reframeEnabled && selectedPaths.length === 1" class="reframe-container">
        <div class="reframe-instructions">
          Drag the image to position the crop area
        </div>
        <div
          class="reframe-viewport"
          ref="viewportRef"
          @mousedown="startDrag"
          @touchstart="startDrag"
        >
          <img
            v-if="originalImageUrl"
            :src="originalImageUrl"
            class="reframe-image"
            :style="imageStyle"
            draggable="false"
            @load="onImageLoad"
          />
          <div class="frame-overlay">
            <div class="frame-outside top"></div>
            <div class="frame-outside bottom"></div>
            <div class="frame-outside left"></div>
            <div class="frame-outside right"></div>
          </div>
        </div>
      </div>

      <!-- Standard preview mode -->
      <div v-else-if="previews.length === 0" class="empty-state">
        <p>No previews available</p>
      </div>

      <div v-else class="previews-container">
        <div v-for="preview in previews" :key="preview.name" class="preview-item">
          <h3>{{ preview.name }}</h3>
          <div class="comparison">
            <div class="image-box">
              <h4>Original</h4>
              <img :src="preview.original_url" :alt="`Original ${preview.name}`" />
            </div>
            <div class="image-box">
              <h4>Processed</h4>
              <img :src="preview.processed_url" :alt="`Processed ${preview.name}`" />
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="secondary" @click="$emit('close')">Cancel</button>
        <button
          class="primary"
          @click="$emit('upload')"
          :disabled="loading || (previews.length === 0 && !reframeEnabled)"
        >
          Upload All
        </button>
      </div>
    </div>
  </div>
</template>
```

**Step 2: Update script with drag logic**

Replace the entire `<script setup>` section (lines 48-68) with:

```vue
<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

const emit = defineEmits(['close', 'upload', 'offset-change'])
const props = defineProps({
  previews: {
    type: Array,
    default: () => []
  },
  cropPercent: {
    type: Number,
    default: 0
  },
  mattePercent: {
    type: Number,
    default: 10
  },
  loading: {
    type: Boolean,
    default: false
  },
  reframeEnabled: {
    type: Boolean,
    default: false
  },
  selectedPaths: {
    type: Array,
    default: () => []
  }
})

// Reframe drag state
const viewportRef = ref(null)
const originalImageUrl = ref(null)
const imageNaturalWidth = ref(0)
const imageNaturalHeight = ref(0)
const offsetX = ref(0.5)
const offsetY = ref(0.5)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const dragStartOffsetX = ref(0)
const dragStartOffsetY = ref(0)

const TARGET_RATIO = 16 / 9

// Calculate image dimensions and position
const imageStyle = computed(() => {
  if (!imageNaturalWidth.value || !imageNaturalHeight.value) return {}

  const imgRatio = imageNaturalWidth.value / imageNaturalHeight.value
  const viewportWidth = 800  // Fixed viewport width
  const viewportHeight = viewportWidth / TARGET_RATIO

  let imgDisplayWidth, imgDisplayHeight

  if (imgRatio > TARGET_RATIO) {
    // Image wider than viewport - fit height, overflow width
    imgDisplayHeight = viewportHeight
    imgDisplayWidth = viewportHeight * imgRatio
  } else {
    // Image taller than viewport - fit width, overflow height
    imgDisplayWidth = viewportWidth
    imgDisplayHeight = viewportWidth / imgRatio
  }

  // Calculate max offset in pixels
  const maxOffsetX = imgDisplayWidth - viewportWidth
  const maxOffsetY = imgDisplayHeight - viewportHeight

  // Apply offset
  const translateX = -maxOffsetX * offsetX.value
  const translateY = -maxOffsetY * offsetY.value

  return {
    width: `${imgDisplayWidth}px`,
    height: `${imgDisplayHeight}px`,
    transform: `translate(${translateX}px, ${translateY}px)`
  }
})

const onImageLoad = (e) => {
  imageNaturalWidth.value = e.target.naturalWidth
  imageNaturalHeight.value = e.target.naturalHeight
}

const startDrag = (e) => {
  e.preventDefault()
  isDragging.value = true

  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY

  dragStartX.value = clientX
  dragStartY.value = clientY
  dragStartOffsetX.value = offsetX.value
  dragStartOffsetY.value = offsetY.value

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', onDrag)
  document.addEventListener('touchend', stopDrag)
}

const onDrag = (e) => {
  if (!isDragging.value) return

  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY

  const deltaX = clientX - dragStartX.value
  const deltaY = clientY - dragStartY.value

  // Convert pixel delta to offset delta (inverted because we're moving the image)
  const viewportWidth = 800
  const viewportHeight = viewportWidth / TARGET_RATIO

  const imgRatio = imageNaturalWidth.value / imageNaturalHeight.value
  let maxOffsetX, maxOffsetY

  if (imgRatio > TARGET_RATIO) {
    const imgDisplayHeight = viewportHeight
    const imgDisplayWidth = viewportHeight * imgRatio
    maxOffsetX = imgDisplayWidth - viewportWidth
    maxOffsetY = 0
  } else {
    const imgDisplayWidth = viewportWidth
    const imgDisplayHeight = viewportWidth / imgRatio
    maxOffsetX = 0
    maxOffsetY = imgDisplayHeight - viewportHeight
  }

  // Calculate new offset (inverted drag direction)
  if (maxOffsetX > 0) {
    offsetX.value = Math.max(0, Math.min(1, dragStartOffsetX.value - deltaX / maxOffsetX))
  }
  if (maxOffsetY > 0) {
    offsetY.value = Math.max(0, Math.min(1, dragStartOffsetY.value - deltaY / maxOffsetY))
  }
}

const stopDrag = () => {
  if (!isDragging.value) return
  isDragging.value = false

  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)

  // Emit offset change to parent
  if (props.selectedPaths.length === 1) {
    emit('offset-change', props.selectedPaths[0], offsetX.value, offsetY.value)
  }
}

// Load original image for reframe mode
const loadOriginalImage = async () => {
  if (!props.reframeEnabled || props.selectedPaths.length !== 1) return

  const path = props.selectedPaths[0]
  originalImageUrl.value = `/api/images/${encodeURIComponent(path)}/thumbnail?size=1200`

  // Reset offset to center
  offsetX.value = 0.5
  offsetY.value = 0.5
}

watch(() => [props.reframeEnabled, props.selectedPaths], loadOriginalImage, { immediate: true })

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
})
</script>
```

**Step 3: Update styles for reframe UI**

Add the following CSS at the end of the `<style scoped>` section (before the closing `</style>` tag, after line 241):

```css
/* Reframe mode styles */
.info-banner {
  background: #2a3a5e;
  color: #8ab4f8;
  padding: 0.75rem 1.5rem;
  font-size: 0.9rem;
  border-bottom: 1px solid #3a4a6e;
}

.reframe-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem;
  overflow: hidden;
}

.reframe-instructions {
  color: #aaa;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.reframe-viewport {
  position: relative;
  width: 800px;
  max-width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  cursor: grab;
  border-radius: 4px;
  background: #000;
}

.reframe-viewport:active {
  cursor: grabbing;
}

.reframe-image {
  position: absolute;
  top: 0;
  left: 0;
  user-select: none;
  pointer-events: none;
}

.frame-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.frame-outside {
  position: absolute;
  background: rgba(0, 0, 0, 0.5);
}

.frame-outside.top {
  top: -100%;
  left: 0;
  right: 0;
  height: 100%;
}

.frame-outside.bottom {
  bottom: -100%;
  left: 0;
  right: 0;
  height: 100%;
}

.frame-outside.left {
  left: -100%;
  top: -100%;
  bottom: -100%;
  width: 100%;
}

.frame-outside.right {
  right: -100%;
  top: -100%;
  bottom: -100%;
  width: 100%;
}
```

**Step 4: Verify frontend compiles**

Run: `cd C:\_dev\samsung-frame-art-gallery\src\frontend && npm run build`

Expected: Build succeeds

**Step 5: Commit**

```bash
git add src/frontend/src/components/PreviewModal.vue
git commit -m "feat: add draggable reframe UI to PreviewModal"
```

---

## Task 6: Backend - Add Large Thumbnail Endpoint

The reframe preview needs a larger thumbnail for the drag UI.

**Files:**
- Modify: `src/api/images.py`

**Step 1: Find and update the thumbnail endpoint**

First, read the images.py file to find where to add the size parameter:

Run: Read `src/api/images.py` to see current thumbnail endpoint.

Add `size` query parameter to the existing thumbnail endpoint. The endpoint should accept an optional `size` parameter (default 200, max 1200) and generate a thumbnail of that size.

Update the thumbnail endpoint (look for `@router.get("/{path:path}/thumbnail")`):

```python
@router.get("/{path:path}/thumbnail")
async def get_thumbnail(path: str, size: int = 200):
    """Get thumbnail for an image. Size parameter controls max dimension (default 200, max 1200)."""
    size = min(max(size, 50), 1200)  # Clamp between 50 and 1200
    # ... rest of implementation uses 'size' instead of hardcoded 200
```

**Step 2: Verify server starts**

Run: `cd C:\_dev\samsung-frame-art-gallery && python -c "from src.api.images import router; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add src/api/images.py
git commit -m "feat: add size parameter to thumbnail endpoint for reframe preview"
```

---

## Task 7: Integration Test

**Step 1: Start the development environment**

Run: `cd C:\_dev\samsung-frame-art-gallery && docker-compose up --build -d`

**Step 2: Open browser and test**

1. Navigate to `http://localhost:8080`
2. Select a single image
3. Check "Re-framing" checkbox - verify Crop and Matte become disabled
4. Click "Preview" - verify drag interface appears
5. Drag the image - verify the visible area changes
6. Release drag - verify preview updates to show new crop position
7. Click "Upload All" - verify image uploads with chosen position

**Step 3: Test multiple images**

1. Select 3+ images
2. Check "Re-framing"
3. Click "Preview"
4. Verify info message appears: "Re-framing uses center crop..."
5. Verify no drag interface, standard preview shown

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete re-framing feature implementation"
```

---

## Summary

| Task | Files | Purpose |
|------|-------|---------|
| 1 | `image_processor.py` | Add `_reframe_image()` function |
| 2 | `tv.py` | Add reframe params to API models |
| 3 | `CropSettings.vue` | Add reframe checkbox UI |
| 4 | `LocalPanel.vue` | Wire reframe state and API calls |
| 5 | `PreviewModal.vue` | Add draggable reframe UI |
| 6 | `images.py` | Add size param for large thumbnails |
| 7 | - | Integration testing |
