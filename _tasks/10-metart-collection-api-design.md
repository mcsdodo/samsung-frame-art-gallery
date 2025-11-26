# Met Museum Collection API Integration - Design

## Overview

Add the Metropolitan Museum of Art's collection as a browsable image source, allowing users to discover and upload public domain artwork to their Samsung Frame TV.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UI structure | Tabs in left panel | Extensible for future sources, minimal layout changes |
| Browsing approach | Highlights first, then department filter | High-quality initial experience, ~4k curated works |
| Backend architecture | Proxy through backend | Cleaner upload flow, caching, consistent API patterns |
| Loading strategy | Batch fetch with pagination (24/page) | Balances responsiveness with simplicity, fits existing infinite scroll |
| Thumbnail display | Image only | Consistent with Local tab, details in preview modal |
| Image resolution | Smart default (full-res with fallback) | Best quality for 4K display, handles edge cases |
| Resolution warning | Show popup for sub-4K images | User transparency before upload |

---

## Architecture

### Data Flow

```
User opens Met tab
    → Frontend: GET /api/met/highlights?page=1
    → Backend: Fetch object IDs from Met API
    → Backend: Batch fetch details for 24 objects
    → Backend: Return [{object_id, title, artist, image_url, width, height}, ...]
    → Frontend: Display in ImageGrid
    → User scrolls → Load more pages

User selects images → clicks Upload
    → Frontend: POST /api/met/upload {object_ids, matte_style, matte_color, display}
    → Backend: For each object_id:
        → Fetch object details → get primaryImage URL
        → Download image bytes
        → Upload to TV via tv_client
    → Return results array
```

---

## Frontend Components

### New Components

**`SourcePanel.vue`**
- Wrapper with tab bar: "Local" | "Met Museum"
- Renders active panel based on selected tab
- Passes through `@uploaded` and `@preview` events

**`MetPanel.vue`**
- Header with department filter dropdown
- Default view: Highlights (no department filter)
- Uses existing `ImageGrid` component
- Uses existing `ActionBar` with `MatteSelector`
- Tracks selection via `selectedIds` (Set of object IDs)

**`ResolutionWarning.vue`**
- Modal shown before upload if any selected image < 3840x2160
- Lists affected images with their resolutions
- "Upload Anyway" / "Cancel" buttons

### Modified Components

**`ImagePreview.vue`**
- Extend to show Met metadata: Title, Artist, Date, Medium, Dimensions
- Resolution indicator (e.g., "3840 x 2160")
- "View on Met website" link

---

## Backend Implementation

### New Files

**`src/services/met_client.py`**

```python
class MetClient:
    MET_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"

    def get_departments() -> list[dict]
        # GET /departments
        # Cached 24h

    def get_highlights(page: int, page_size: int = 24) -> dict
        # GET /search?isHighlight=true&hasImages=true
        # Returns {objects: [...], total: int, page: int}

    def get_objects_by_department(dept_id: int, page: int, page_size: int = 24) -> dict
        # GET /objects?departmentIds={dept_id}
        # Filter for hasImages, paginate

    def get_object(object_id: int) -> dict
        # GET /objects/{object_id}
        # Cached 1h

    def fetch_image(image_url: str) -> bytes
        # Download image bytes for TV upload
```

**`src/api/met.py`**

```python
router = APIRouter()

@router.get("/departments")
@router.get("/highlights")
@router.get("/objects")
@router.get("/object/{object_id}")
@router.post("/upload")
    # Request: {object_ids: [], matte_style, matte_color, display}
    # Response: {results: [{object_id, success, error?}, ...]}
```

### Caching Strategy

- In-memory dict with TTL
- Departments: 24h TTL (rarely change)
- Object details: 1h TTL (stable data)
- No persistence (rebuilds on restart)

---

## Error Handling

### Met API Errors

| Error | Handling |
|-------|----------|
| Network failure | Toast "Failed to load artwork, please retry" |
| Rate limited | Exponential backoff, auto-retry |
| Object not found | Skip in batch, show error in single fetch |

### Image Availability

| Scenario | Handling |
|----------|----------|
| No `primaryImage` | Filter out, don't return to frontend |
| Only `primaryImageSmall` | Use it, flag `is_low_res: true` |
| Image download fails | Return error for item, continue others |
| URL expired | Retry with fresh object fetch, then fail |

### Resolution Warning

- Frame TV resolution: 3840x2160 (4K)
- Show warning if either image dimension < corresponding TV dimension
- Display: "Image: 2048x1536 | Recommended: 3840x2160"

---

## Files Summary

### Create

| File | Purpose |
|------|---------|
| `src/services/met_client.py` | Met API client with caching |
| `src/api/met.py` | FastAPI router for Met endpoints |
| `src/frontend/src/views/MetPanel.vue` | Met browsing panel |
| `src/frontend/src/components/SourcePanel.vue` | Tab wrapper component |
| `src/frontend/src/components/ResolutionWarning.vue` | Upload warning modal |

### Modify

| File | Changes |
|------|---------|
| `src/main.py` | Mount Met router at `/api/met` |
| `src/frontend/src/App.vue` | Replace LocalPanel with SourcePanel |
| `src/frontend/src/components/ImagePreview.vue` | Add Met metadata display |

---

## Out of Scope

Reserved for future iterations:
- Search functionality (keyword search)
- Saved collections / favorites
- Additional museum APIs (Rijksmuseum, Art Institute of Chicago)
