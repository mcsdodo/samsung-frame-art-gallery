# Samsung Frame Art Gallery - Development Guide

## Project Overview

Web application for managing artwork on Samsung Frame TVs. Features local image browsing, Met Museum public domain artwork integration, and image processing (crop, matte, re-framing). FastAPI backend + Vue 3 frontend, deployed via Docker.

## File Naming Convention

**IMPORTANT:** When creating new files in `_tasks/` directory, use `XX-[FILE_NAME].md` format (e.g. `01-TASK.md`) for easy sorting. Increment XX only for NEW tasks.

**When working on an existing task** (e.g., `15-task.md`), keep the same `XX-` number for all related content (plans, designs, updates). Do NOT increment the number - all task-related documentation stays under the same prefix.

Tasks, plans, and design documents are ALL stored in the `_tasks/` folder. Do NOT create `docs/`, `plans/`, or similar directories.

## Project Structure

```
/
├── src/
│   ├── main.py                 # FastAPI app entry point, lifespan management
│   ├── api/
│   │   ├── images.py           # /api/images/* endpoints
│   │   ├── tv.py               # /api/tv/* endpoints
│   │   └── met.py              # /api/met/* endpoints (Met Museum)
│   ├── services/
│   │   ├── tv_client.py        # Samsung TV WebSocket client (singleton)
│   │   ├── tv_discovery.py     # SSDP-based TV discovery
│   │   ├── tv_settings.py      # Persistent TV selection (JSON in /app/data)
│   │   ├── tv_thumbnail_cache.py
│   │   ├── met_client.py       # Met Museum Collection API client
│   │   ├── image_processor.py  # Crop, matte, reframe processing
│   │   ├── preview_cache.py    # Preview generation caching
│   │   └── thumbnails.py       # Local image thumbnail generation
│   └── frontend/               # Vue 3 SPA
│       ├── src/
│       │   ├── App.vue         # Root component
│       │   ├── components/     # Reusable UI components
│       │   └── views/          # Page-level components (LocalPanel, MetPanel, TVPanel)
│       └── package.json
├── docker/
│   └── Dockerfile              # Multi-stage build
├── docker-compose.yml
├── requirements.txt
└── _tasks/                     # Design docs, plans, implementation notes
```

## Tech Stack

- **Backend:** FastAPI 0.109+, Python 3.11, Pillow, httpx, uvicorn
- **Frontend:** Vue 3.4, Vite 5
- **TV API:** samsung-tv-ws-api (WebSocket-based)
- **External API:** Met Museum Collection API
- **Container:** Docker with multi-stage build

## Key APIs

| Endpoint | Purpose |
|----------|---------|
| `GET /api/images` | List local images |
| `GET /api/images/folders` | List folders |
| `GET /api/images/{path}/thumbnail` | Get thumbnail (supports `?size=` param) |
| `GET /api/tv/discover` | SSDP scan for TVs |
| `GET /api/tv/status` | TV connection status |
| `GET /api/tv/artwork` | List TV artwork |
| `POST /api/tv/upload` | Upload to TV (with crop/matte/reframe) |
| `POST /api/tv/preview` | Generate preview images |
| `GET /api/met/highlights` | Get Met Museum highlights |
| `GET /api/met/search` | Search Met collection |
| `POST /api/met/upload` | Download from Met and upload to TV |

## Development Commands

```bash
# Docker (production-like)
docker-compose up --build

# Backend only (with hot reload)
pip install -r requirements.txt
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080

# Frontend only (dev server with HMR)
cd src/frontend
npm install
npm run dev

# Frontend build (production)
cd src/frontend
npm run build
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TV_IP` | - | Pre-configured TV IP address |
| `IMAGES_DIR` | `/images` | Path to mounted images |
| `THUMBNAILS_DIR` | `/thumbnails` | Thumbnail cache directory |
| `DEFAULT_CROP_PERCENT` | `5` | Default edge crop percentage |
| `DEFAULT_MATTE_PERCENT` | `10` | Default matte size percentage |

## Important Implementation Details

1. **TVClient is a singleton** - Access via `get_tv_client()` in `tv_client.py`
2. **MetClient is a singleton** - Access via `get_met_client()` in `met_client.py`
3. **TV API calls use thread pool** - Wrapped in `asyncio.to_thread()` to avoid blocking
4. **Thumbnail caching** - MD5 hash-based filenames, supports variable sizes
5. **Preview caching** - Cache key includes crop/matte/reframe params
6. **API version detection** - Auto-detects TV v3.x vs v4.x+ for thumbnail fetching
7. **Settings persistence** - JSON file in `/app/data/tv_settings.json`

## Common Tasks

### Adding a new API endpoint
1. Add route in appropriate file under `src/api/`
2. Router is already mounted in `main.py`

### Adding a new Vue component
1. Create in `src/frontend/src/components/`
2. Import and use in parent component

### Modifying TV communication
1. All TV logic in `src/services/tv_client.py`
2. Uses `samsung-tv-ws-api` library

### Modifying image processing
1. Core logic in `src/services/image_processor.py`
2. Functions: `process_for_tv()`, `generate_preview()`, `_crop_image()`, `_add_matte()`, `_reframe_image()`

## Docker Volumes

- `/images` - Mount your image collection (read-only)
- `/thumbnails` - Thumbnail cache
- `/app/data` - TV settings persistence

## Notes

- Network-local only, no authentication (trusted network assumption)
- TV must be powered on (not deep standby) for discovery
- Supports JPEG, PNG image formats
- Met Museum images are public domain (CC0)
- Tested with Samsung Frame TVs (Art Mode required)
