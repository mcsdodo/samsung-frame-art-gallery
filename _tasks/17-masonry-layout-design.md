# Masonry Layout for Variable Aspect Ratio Previews

## Overview

Replace the uniform 16:9 grid with a masonry layout that displays images at their natural aspect ratios. This makes better use of screen space and shows each image's true proportions.

## Backend Changes

### Add dimensions to image API responses

**`/api/images` endpoint:**

Add `width` and `height` fields to each image in the response:

```python
{
  "name": "sunset.jpg",
  "path": "vacation/sunset.jpg",
  "width": 4032,
  "height": 3024
}
```

**Implementation:**
- Use Pillow to read dimensions when listing images
- Cache dimensions in the thumbnail service (store metadata alongside thumbnails)
- For images without cached dimensions, read on-demand and cache

**TV artwork (`/api/tv/artwork`):**
- Include dimensions if available from TV API
- Fall back to 16:9 default if not available

**Met images:**
- Fetch dimensions from `primaryImageSmall` on first request and cache

## Frontend Changes

### Install masonry library

```bash
npm install @yeger/vue-masonry-wall
```

Chosen for: Vue 3 native, ~4KB, handles resize/dynamic content.

### Update ImageGrid.vue

Replace CSS Grid with MasonryWall component:

```vue
<template>
  <MasonryWall :items="visibleImages" :column-width="180" :gap="16">
    <template #default="{ item }">
      <ImageCard
        :image="item"
        :selected="selectedIds.has(item.path || item.object_id || item.content_id)"
        ...
      />
    </template>
  </MasonryWall>
</template>
```

### Update ImageCard.vue

Remove fixed 16:9 padding hack. Use dynamic aspect ratio:

```vue
<div class="image-card" :style="{ aspectRatio: computedAspectRatio }">
```

Where `computedAspectRatio` is calculated from `image.width / image.height`.

## Edge Cases

| Case | Handling |
|------|----------|
| Missing dimensions | Default to 16:9 (aspectRatio: 1.78) |
| Very tall images (e.g., 1:5) | Cap aspect ratio at 1:2 to prevent excessive height |
| Very wide images (e.g., 5:1) | Cap aspect ratio at 3:1 to prevent tiny slivers |
| Infinite scroll | Masonry library handles dynamic item addition |
| Window resize | Library handles responsive reflow |

## Files to Change

### Backend
| File | Change |
|------|--------|
| `src/api/images.py` | Add `width`, `height` to image list response |
| `src/services/thumbnails.py` | Cache dimensions when generating thumbnails |
| `src/api/tv.py` | Add dimensions to TV artwork response |

### Frontend
| File | Change |
|------|--------|
| `package.json` | Add `@yeger/vue-masonry-wall` dependency |
| `src/components/ImageGrid.vue` | Replace CSS grid with MasonryWall component |
| `src/components/ImageCard.vue` | Remove fixed 16:9 padding, use dynamic `aspectRatio` style |

## Testing

- Verify local images show with correct aspect ratios
- Verify TV artwork panel works
- Verify Met panel works
- Test infinite scroll still works
- Test selection (checkbox, select all) still works
- Test with portrait, landscape, and square images mixed together

## Scope

Masonry layout applies to all panels: Local, TV, and Met.
