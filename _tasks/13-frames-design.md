# Frame Cropping & Auto-Matte Design

## Problem

Museum artwork images often include decorative frames that look awkward on Samsung Frame TV. Users need to:
1. Crop frames from images before upload
2. Add consistent white matte padding to fit 16:9 aspect ratio

## Solution

Replace TV's native matte feature with server-side image processing that crops and adds white matte before upload.

---

## UI Changes

### Action Bar Controls

Replace `MatteSelector` with new `CropSettings` component in both `LocalPanel.vue` and `MetPanel.vue`:

```
┌─────────────────────────────────────────────────────────────────┐
│  Crop: [____0___] %    [Preview]    [Upload] [Upload & Display] │
└─────────────────────────────────────────────────────────────────┘
```

- **Crop input**: Number field, 0-50% range, default 0
- **Preview button**: Enabled when at least one image is selected
- **Upload buttons**: Unchanged, but now apply crop + auto-matte

### Removed
- `MatteSelector` component (style/color dropdowns)
- `/api/tv/mattes` endpoint
- `matte_style` and `matte_color` parameters

---

## Preview Modal

Side-by-side comparison for all selected images:

```
┌──────────────────────────────────────────────────────────────────┐
│  Preview (Crop: 10%)                                        [X]  │
├──────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                      │
│  │                 │    │   ┌─────────┐   │                      │
│  │    Original     │    │   │ Cropped │   │   image_001.jpg      │
│  │                 │    │   │ + Matte │   │                      │
│  │                 │    │   └─────────┘   │                      │
│  └─────────────────┘    └─────────────────┘                      │
│  ─────────────────────────────────────────────────────────────── │
│  ┌─────────────────┐    ┌─────────────────┐                      │
│  │                 │    │   ┌─────────┐   │                      │
│  │    Original     │    │   │ Cropped │   │   image_002.jpg      │
│  │                 │    │   │ + Matte │   │                      │
│  └─────────────────┘    └─────────────────┘                      │
│                              ...                                  │
├──────────────────────────────────────────────────────────────────┤
│                                          [Cancel]  [Upload All]  │
└──────────────────────────────────────────────────────────────────┘
```

- Both thumbnails same visual size for comparison
- Processed image shows 16:9 canvas with white matte
- Scrollable for multiple images
- Crop value adjustable in modal to re-preview

---

## Image Processing Logic

### New service: `src/services/image_processor.py`

```python
def process_for_tv(image_data: bytes, crop_percent: int) -> bytes:
    """
    1. Crop: Remove crop_percent from all 4 edges
    2. Matte: Add white padding for 16:9 output
    Returns: PNG bytes ready for TV upload
    """
```

### Crop Algorithm

```
Original 1000×800, crop 10%:
- Remove 100px from left, right (10% of width)
- Remove 80px from top, bottom (10% of height)
- Result: 800×640
```

### Matte Algorithm

```
After crop: 800×640

1. min_matte = 12% of max(W, H) = 12% of 800 = 96px
2. Add 96px padding all sides → 992×832
3. Current ratio = 992/832 = 1.19 (taller than 16:9 = 1.78)
4. Expand width for 16:9: 832 × 16/9 = 1479px
5. Final canvas: 1479×832 (16:9), image centered

Result:
- Left/right matte: (1479-800)/2 = 340px
- Top/bottom matte: 96px (minimum)
```

### Rules

- Minimum matte = 12% of image's longer side
- Final canvas is always 16:9 aspect ratio
- Image centered on white (#FFFFFF) canvas
- Output format: PNG (lossless)

---

## API Changes

### Modified: `POST /api/tv/upload`

```python
class UploadRequest(BaseModel):
    paths: list[str]           # Local paths or Met object IDs
    crop_percent: int = 0      # 0-50 range
    display: bool = False

# Removed: matte_style, matte_color
```

Flow:
1. Load image (disk or Met API)
2. `process_for_tv(image_data, crop_percent)`
3. Upload to TV with `matte="none"`

### New: `POST /api/preview`

```python
class PreviewRequest(BaseModel):
    paths: list[str]
    crop_percent: int = 0
    source: str = "local"      # "local" or "met"

# Response: List of base64-encoded processed images
```

---

## File Changes

### New Files
- `src/services/image_processor.py` - Crop and matte logic
- `src/frontend/src/components/CropSettings.vue` - Crop input + preview button
- `src/frontend/src/components/PreviewModal.vue` - Side-by-side modal

### Modified Files
- `src/api/tv.py` - Update UploadRequest, add /api/preview
- `src/services/tv_client.py` - Hardcode matte="none"
- `src/frontend/src/views/LocalPanel.vue` - Replace MatteSelector
- `src/frontend/src/views/MetPanel.vue` - Replace MatteSelector

### Removed Files
- `src/frontend/src/components/MatteSelector.vue`

### Removed Code
- `get_matte_options()` in tv_client.py
- `/api/tv/mattes` endpoint

---

## Dependencies

- Pillow (already in requirements.txt)
