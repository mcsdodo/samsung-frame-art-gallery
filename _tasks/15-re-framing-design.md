# Re-framing Feature Design

## Overview

Add a "Re-framing" option that crops images to completely fill the TV's 16:9 frame, with user-adjustable positioning for single images.

## UI Controls

**CropSettings component** - new checkbox above existing controls:

```
[x] Re-framing
    Crop: [___]%  (disabled when re-framing)
    Matte: [___]% (disabled when re-framing)
    [Preview]
```

When "Re-framing" is checked:
- Both Crop and Matte inputs become disabled (grayed out)
- Their values are ignored during processing

## Preview Modal - Single Image

When re-framing is enabled and **one image** is selected:

**Visual layout:**
- Preview area shows the original image scaled to fit
- A 16:9 rectangle overlay indicates the "frame" (area that appears on TV)
- Areas **outside** the frame have a dark semi-transparent overlay (~50% opacity black)
- Frame area shows image at full brightness

**Interaction:**
- User clicks and drags the image to reposition which part fills the frame
- Image moves; frame stays fixed in center
- Dragging constrained so frame always stays fully covered

**Scaling:** Image automatically scaled so its smaller dimension matches the frame (ensuring full coverage). User controls position only, not scale.

## Preview Modal - Multiple Images

When re-framing is enabled and **multiple images** selected:

- Same layout as current preview (before/after side by side)
- "After" image shows center-cropped re-framing applied
- No drag interaction available
- Info message at top: "Re-framing uses center crop for multiple images. Select a single image for manual positioning."

## Backend Processing

**New parameters on PreviewRequest and UploadRequest:**
- `reframe_enabled: bool = False`
- `reframe_offsets: dict[str, dict] = {}` - map of path to `{x: 0.0-1.0, y: 0.0-1.0}`

**Processing logic:**
```python
if reframe_enabled:
    1. Calculate scale factor so smaller dimension fills 16:9 frame
    2. Scale image to cover frame
    3. Crop to exact 16:9 using reframe_offset for positioning
       - offset (0.5, 0.5) = center crop (default)
       - offset (0.0, 0.5) = crop from left edge
       - offset (1.0, 0.5) = crop from right edge
    4. Skip matte step entirely
else:
    # existing logic: crop then matte
```

**Edge cases:**
- Portrait images: Scale width to fill, crop top/bottom
- Landscape images: Scale height to fill, crop left/right
- Already 16:9: Pass through unchanged
- Panoramas: User positions left/center/right

## API Shape

```json
POST /api/tv/upload
{
  "paths": ["image1.jpg"],
  "crop_percent": 0,
  "matte_percent": 0,
  "reframe_enabled": true,
  "reframe_offsets": {
    "image1.jpg": {"x": 0.3, "y": 0.5}
  }
}
```

Map structure future-proofs for per-image offsets. Images not in map default to center (0.5, 0.5).

## Files to Modify

**Frontend:**
| File | Changes |
|------|---------|
| `CropSettings.vue` | Add reframe checkbox, disable crop/matte when checked |
| `LocalPanel.vue` | Track `reframeEnabled` and `reframeOffsets` state, pass to API |
| `PreviewModal.vue` | Add draggable image interaction, dark overlay, info message for batch |

**Backend:**
| File | Changes |
|------|---------|
| `src/api/tv.py` | Add `reframe_enabled` and `reframe_offsets` to request models |
| `src/services/image_processor.py` | Add `_reframe_image()` function, update `process_for_tv()` |

No new files needed.
