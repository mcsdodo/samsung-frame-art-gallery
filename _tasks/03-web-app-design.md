# Samsung Frame Art Gallery - Web Application Design

**Date:** 2025-11-25
**Status:** Approved
**Prerequisite:** TV verification completed (all tests passed)

## Overview

Web application to browse local images and manage Samsung Frame TV art mode. Runs in Docker, accessible via browser on local network.

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend | Vue 3 + Vite | Reactive UI, good for image galleries |
| Backend | FastAPI | Async support for TV WebSocket, auto API docs |
| Container | Docker multi-stage | Single container, Vue builds to static |
| Image format | JPEG only | Samsung TV art mode optimized for JPEG |
| Auth | None | Local network only |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
│  ┌─────────────┐     ┌─────────────┐                    │
│  │   Vue SPA   │────▶│   FastAPI   │────▶ Samsung TV    │
│  │  (Frontend) │     │  (Backend)  │      192.168.0.105 │
│  └─────────────┘     └─────────────┘                    │
│         │                   │                           │
│         │            ┌──────┴──────┐                    │
│         │            │ /images vol │                    │
│         │            └─────────────┘                    │
│         │              Mounted folder                   │
└─────────────────────────────────────────────────────────┘
```

## API Design

### Local Images
```
GET  /api/images                    - List all images (flat)
GET  /api/images?folder=landscapes  - List images in folder
GET  /api/folders                   - List available folders
GET  /api/images/{path}/thumbnail   - Get image thumbnail
GET  /api/images/{path}/full        - Get full image
```

### TV Artwork
```
GET  /api/tv/artwork                - List artwork on TV
GET  /api/tv/artwork/current        - Get current artwork info
POST /api/tv/artwork/current        - Set artwork as current
DEL  /api/tv/artwork/{content_id}   - Delete artwork from TV
```

### Upload
```
POST /api/tv/upload                 - Upload image(s) to TV
     Body: { paths: [...], matte: { style, color }, display: bool }
```

### TV Status
```
GET  /api/tv/status                 - Connection status, art mode supported
GET  /api/tv/mattes                 - Available matte styles/colors
```

## UI Design

### Desktop Layout (Split View)
```
┌──────────────────────────────────────────────────────────┐
│  Samsung Frame Art Gallery                    [TV: ●]    │
├────────────────────────┬─────────────────────────────────┤
│  LOCAL IMAGES          │  TV ARTWORK                     │
│  [All] [Folders ▼]     │  [Refresh]                      │
│  ☑ Select All          │  ☑ Select All                   │
├────────────────────────┼─────────────────────────────────┤
│ ┌─────┐ ┌─────┐ ┌─────┐│ ┌─────┐ ┌─────┐ ┌─────┐        │
│ │ ☑  │ │ ☐  │ │ ☐  ││ │ ☑  │ │ ☐  │ │ NOW │        │
│ │     │ │     │ │     ││ │     │ │     │ │ ▶   │        │
│ └─────┘ └─────┘ └─────┘│ └─────┘ └─────┘ └─────┘        │
│                        │                                 │
├────────────────────────┼─────────────────────────────────┤
│ [Upload] [Upload+Show] │ [Display] [Delete]              │
│ Matte: [Style▼][Color▼]│ 2 selected                      │
└────────────────────────┴─────────────────────────────────┘
```

### Mobile Layout (Tabs)
```
┌─────────────────────────┐
│ [Local] [TV]    [●]     │
├─────────────────────────┤
│ [All] [Folders ▼]       │
│ ☑ Select All            │
├─────────────────────────┤
│ ┌─────┐ ┌─────┐         │
│ │ ☑  │ │ ☐  │         │
│ └─────┘ └─────┘         │
├─────────────────────────┤
│ Matte: [Style▼][Color▼] │
│ [Upload] [Upload+Show]  │
└─────────────────────────┘
```

### Key Interactions
- Checkbox on each image for multi-select
- "NOW ▶" badge shows currently displayed artwork
- TV status indicator (green dot = connected)
- Action buttons disabled when nothing selected

## Project Structure

```
samsung-frame-art-gallery/
├── docker/
│   └── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── src/
│   ├── main.py              # FastAPI app entry
│   ├── api/
│   │   ├── images.py        # Local image endpoints
│   │   └── tv.py            # TV artwork endpoints
│   ├── services/
│   │   ├── tv_client.py     # Samsung TV wrapper
│   │   └── thumbnails.py    # Thumbnail generation/cache
│   └── frontend/            # Vue app
│       ├── package.json
│       ├── vite.config.js
│       └── src/
│           ├── App.vue
│           ├── components/
│           │   ├── ImageGrid.vue
│           │   ├── ImageCard.vue
│           │   ├── MatteSelector.vue
│           │   └── ActionBar.vue
│           └── views/
│               └── Gallery.vue
├── static/                  # Vue build output
└── _tasks/
```

## Docker Configuration

### docker-compose.yml
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

### Dockerfile (multi-stage)
```dockerfile
# Stage 1: Build Vue
FROM node:20-slim AS frontend
WORKDIR /app
COPY src/frontend/package*.json ./
RUN npm ci
COPY src/frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY --from=frontend /app/dist ./static/
EXPOSE 8080
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## Features Summary

- Browse local JPEG images (flat or by folder)
- Multi-select for bulk upload/delete
- Upload to TV with matte style/color options
- Upload only OR upload + display immediately
- View/manage TV artwork library
- Delete artwork from TV
- Set any artwork as current display
- Responsive layout (split-view desktop, tabs mobile)
- TV connection status indicator

## Usage

```bash
# Place JPEGs in ./images folder
docker-compose up --build

# Access at http://localhost:8080
```
