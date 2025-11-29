# Samsung Frame Art Gallery

A self-hosted web application for managing artwork on Samsung Frame TVs. Browse your local image collection or discover public domain masterpieces from the Metropolitan Museum of Art, then upload them to your TV with customizable framing options.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Vue](https://img.shields.io/badge/vue-3.4+-green.svg)

## Features

### Image Sources
- **Local Images** - Browse your personal image collection with folder navigation and smart thumbnails
- **Met Museum Collection** - Discover and upload public domain artwork from The Metropolitan Museum of Art's open collection (400,000+ works)

### TV Integration
- **Auto TV Discovery** - Automatically finds Samsung Frame TVs on your network via SSDP
- **Batch Upload** - Upload multiple images to your TV at once
- **Art Management** - View, display, and delete artwork on your TV
- **Live Preview** - See exactly how your images will look before uploading

### Image Processing
- **Smart Cropping** - Remove unwanted edges from images (0-50%)
- **Auto Matte** - Automatically add museum-style matting to fit the 16:9 frame
- **Re-framing Mode** - Fill the entire frame with adjustable positioning for single images

### User Experience
- **Responsive Design** - Split-panel desktop layout, tabbed mobile interface
- **Infinite Scroll** - Seamless browsing through large collections
- **Masonry Layout** - Beautiful variable-height image grid
- **Docker-Ready** - Simple one-command deployment

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Samsung Frame TV (or any Samsung TV with Art Mode) on the same network
- A folder of images (optional - you can also use the Met Museum collection)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/samsung-frame-art-gallery.git
   cd samsung-frame-art-gallery
   ```

2. **Configure your images path** (optional)

   Create a `.env` file or edit `docker-compose.yml`:
   ```bash
   # Option A: Using .env file
   echo "IMAGES_DIR=/path/to/your/images" > .env

   # Option B: Edit docker-compose.yml volumes directly
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Open the web UI**

   Navigate to `http://localhost:8080`

5. **Connect to your TV**

   Click the TV status indicator in the header to discover and select your Samsung TV.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IMAGES_DIR` | `./images` | Path to your local image collection |
| `TV_IP` | - | Pre-configure TV IP (skips auto-discovery) |
| `DEFAULT_CROP_PERCENT` | `5` | Default edge crop percentage |
| `DEFAULT_MATTE_PERCENT` | `10` | Default matte size percentage |

### Docker Compose

```yaml
services:
  app:
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "8080:8080"
    volumes:
      - /path/to/your/images:/images:ro    # Your image collection
      - ./data/thumbnails:/thumbnails      # Thumbnail cache
      - ./data:/app/data                   # TV settings persistence
    environment:
      - TV_IP=${TV_IP:-}
      - DEFAULT_CROP_PERCENT=${DEFAULT_CROP_PERCENT:-5}
      - DEFAULT_MATTE_PERCENT=${DEFAULT_MATTE_PERCENT:-10}
    restart: unless-stopped
```

## Usage

### Local Images Tab

1. Browse your image collection using folder navigation
2. Select one or more images by clicking on them
3. Adjust crop and matte percentages, or enable "Re-framing" mode
4. Click "Preview" to see how images will look on the TV
5. Click "Upload" or "Upload & Display"

### Met Museum Tab

1. Browse highlighted works or filter by medium (Paintings, Drawings, etc.)
2. Use search to find specific artworks
3. Select works and preview/upload just like local images
4. All Met Museum images are public domain - free to use

### TV Panel

1. View all artwork currently stored on your TV
2. Click any artwork to display it
3. Delete artwork you no longer want

## Development

### Local Setup

**Backend:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run with hot reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

**Frontend:**
```bash
cd src/frontend
npm install
npm run dev
```

### Project Structure

```
samsung-frame-art-gallery/
├── src/
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── images.py           # Local image endpoints
│   │   ├── tv.py               # TV control & upload endpoints
│   │   └── met.py              # Met Museum API endpoints
│   ├── services/
│   │   ├── tv_client.py        # Samsung TV WebSocket client
│   │   ├── tv_discovery.py     # SSDP-based TV discovery
│   │   ├── tv_settings.py      # Persistent TV selection
│   │   ├── met_client.py       # Met Museum API client
│   │   ├── image_processor.py  # Crop, matte, reframe processing
│   │   ├── thumbnails.py       # Local image thumbnails
│   │   └── preview_cache.py    # Preview generation cache
│   └── frontend/               # Vue 3 + Vite SPA
│       ├── src/
│       │   ├── views/
│       │   │   ├── LocalPanel.vue
│       │   │   ├── MetPanel.vue
│       │   │   └── TVPanel.vue
│       │   └── components/
│       └── package.json
├── docker/
│   └── Dockerfile              # Multi-stage build
├── docker-compose.yml
└── requirements.txt
```

### Tech Stack

- **Backend:** FastAPI, Python 3.11+, Pillow, httpx
- **Frontend:** Vue 3.4, Vite 5
- **TV Communication:** [samsung-tv-ws-api](https://github.com/NickWaterton/samsung-tv-ws-api)
- **External APIs:** [Met Museum Collection API](https://metmuseum.github.io/)
- **Infrastructure:** Docker, Docker Compose

## API Reference

### Local Images

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/images` | List images (optional `?folder=` filter) |
| GET | `/api/images/folders` | List available folders |
| GET | `/api/images/{path}/thumbnail` | Get image thumbnail |
| GET | `/api/images/{path}/full` | Get full image |

### Met Museum

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/met/departments` | List museum departments |
| GET | `/api/met/highlights` | Get highlighted artworks |
| GET | `/api/met/medium/{medium}` | Get artworks by medium |
| GET | `/api/met/search?q=` | Search artworks |
| GET | `/api/met/object/{id}` | Get artwork details |
| POST | `/api/met/preview` | Generate processed preview |
| POST | `/api/met/upload` | Upload artwork to TV |

### TV Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tv/discover` | Scan for Samsung TVs |
| GET | `/api/tv/status` | Get TV connection status |
| GET | `/api/tv/settings` | Get saved TV selection |
| POST | `/api/tv/settings` | Save TV selection |
| GET | `/api/tv/artwork` | List artwork on TV |
| GET | `/api/tv/artwork/current` | Get currently displayed artwork |
| POST | `/api/tv/artwork/current` | Display specific artwork |
| DELETE | `/api/tv/artwork/{id}` | Delete artwork from TV |
| POST | `/api/tv/preview` | Generate upload preview |
| POST | `/api/tv/upload` | Upload local images to TV |

## TV Compatibility

Tested with Samsung Frame TVs. Should work with any Samsung TV that supports Art Mode via WebSocket API.

**Supported TV API versions:**
- v3.x (older Frame models)
- v4.x+ (newer models with SSL)

## Troubleshooting

### TV not discovered

- Ensure your TV is on the same network/subnet as the host
- TV must be powered on (not in deep standby)
- Try manually entering the TV IP address in settings
- Check if your network blocks SSDP multicast (UDP 1900)

### Upload fails

- Verify the TV is in Art Mode (not regular TV mode)
- Check that image format is supported (JPEG, PNG)
- Ensure sufficient storage space on TV
- Large images may timeout - try with smaller files first

### Thumbnails not loading

- First load generates thumbnails - allow time for processing
- Check that images volume is mounted correctly
- Verify read permissions on the images directory

### Met Museum images not loading

- The Met API may be slow for large searches
- Some artworks don't have high-resolution images available
- Network connectivity to `collectionapi.metmuseum.org` required

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [samsung-tv-ws-api](https://github.com/NickWaterton/samsung-tv-ws-api) - Samsung TV WebSocket API library
- [The Metropolitan Museum of Art Collection API](https://metmuseum.github.io/) - Public domain artwork access
- Samsung for creating the Frame TV with Art Mode
