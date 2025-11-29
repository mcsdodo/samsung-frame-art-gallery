# Samsung Frame Art Gallery - Development Guide

## Project Overview

Web application for managing artwork on Samsung Frame TVs. FastAPI backend + Vue 3 frontend, deployed via Docker.

## File Naming Convention

**IMPORTANT:** When creating new files in `_tasks/` directory, use `XX-[FILE_NAME].md` format (e.g. `01-TASK.md`) for easy sorting. Increment XX only for NEW tasks.

**When working on an existing task** (e.g., `15-task.md`), keep the same `XX-` number for all related content (plans, designs, updates). Do NOT increment the number - all task-related documentation stays under the same prefix.

Tasks, plans, and design documents are ALL stored in the `_tasks/` folder. Do NOT create `docs/`, `plans/`, or similar directories.

## Project Structure

```
/                           # Root directory
├── src/
│   ├── main.py             # FastAPI app entry point, lifespan management
│   ├── api/
│   │   ├── images.py       # /api/images/* endpoints
│   │   └── tv.py           # /api/tv/* endpoints
│   ├── services/
│   │   ├── tv_client.py    # Samsung TV WebSocket client (singleton)
│   │   ├── tv_discovery.py # SSDP-based TV discovery
│   │   ├── tv_settings.py  # Persistent TV selection (JSON in /app/data)
│   │   ├── tv_thumbnail_cache.py
│   │   └── thumbnails.py   # Local image thumbnail generation
│   └── frontend/           # Vue 3 SPA
│       ├── src/
│       │   ├── App.vue     # Root component
│       │   ├── components/ # Reusable UI components
│       │   └── views/      # Page-level components
│       └── package.json
├── docker/
│   └── Dockerfile          # Multi-stage build
├── docker-compose.yml
├── requirements.txt
└── _tasks/                 # Design docs, plans, tasks
```

## Tech Stack

- **Backend:** FastAPI 0.109+, Python 3.11, Pillow, uvicorn
- **Frontend:** Vue 3.4, Vite 5
- **TV API:** samsung-tv-ws-api (WebSocket-based)
- **Container:** Docker with multi-stage build

## Key APIs

| Endpoint | Purpose |
|----------|---------|
| `GET /api/images` | List local images |
| `GET /api/images/folders` | List folders |
| `GET /api/images/{path}/thumbnail` | Get thumbnail |
| `GET /api/tv/discover` | SSDP scan for TVs |
| `GET /api/tv/status` | TV connection status |
| `GET /api/tv/artwork` | List TV artwork |
| `POST /api/tv/upload` | Upload to TV |
| `POST /api/tv/artwork/current` | Display artwork |

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

## Important Implementation Details

1. **TVClient is a singleton** - Access via `get_tv_client()` in `tv_client.py`
2. **TV API calls use thread pool** - Wrapped in `asyncio.to_thread()` to avoid blocking
3. **Thumbnail caching** - MD5 hash-based filenames, parallel generation (4 workers)
4. **API version detection** - Auto-detects v3.x vs v4.x+ for thumbnail fetching
5. **Settings persistence** - JSON file in `/app/data/tv_settings.json`

## Common Tasks

### Adding a new API endpoint
1. Add route in `src/api/images.py` or `src/api/tv.py`
2. Router is already mounted in `main.py`

### Adding a new Vue component
1. Create in `src/frontend/src/components/`
2. Import and use in parent component

### Modifying TV communication
1. All TV logic in `src/services/tv_client.py`
2. Uses `samsung-tv-ws-api` library
3. Test with `src/verify_tv.py` utility

## Docker Volumes

- `/images` - Mount your image collection (read-only)
- `/thumbnails` - Thumbnail cache (named volume)
- `/app/data` - TV settings persistence (bind mount `./data`)

## Notes

- Network-local only, no authentication (trusted network assumption)
- TV must be powered on (not deep standby) for discovery
- Supports JPEG, PNG image formats
- Tested with Samsung Frame TVs (Art Mode required)


# Development environments
1. for development use docker-compose file
2. for deployment on a server use passwordless ssh ``ssh root@192.168.0.99`` and run the docker commands there
3. caddy proxy sits here ``ssh root@192.168.0.112``. DO NOT MAKE ANY CHANGES WITHOUT CONSULTING ME FIRST. You can check the logs if needed.
4. DO NOT make any changes on the caddy instance 192.168.0.22 without asking first.