# Samsung Frame Art Gallery

A self-hosted web application for managing artwork on Samsung Frame TVs. Browse your local image collection, upload artwork to your TV, and control what's displayed - all from a clean, responsive interface.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- **Browse Local Images** - View your image collection with folder filtering and smart thumbnails
- **Auto TV Discovery** - Automatically finds Samsung TVs on your network via SSDP
- **Upload Artwork** - Batch upload images to your TV's art collection
- **Matte Customization** - Configure matte styles (modern, thin, flexible) and colors
- **TV Art Management** - View, display, and delete artwork on your TV
- **Responsive Design** - Works on desktop (split-panel) and mobile (tabbed)
- **Docker-Ready** - Simple deployment with Docker Compose

## Screenshots

*Coming soon*

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Samsung Frame TV (or Samsung TV with Art Mode) on the same network
- A folder of images you want to display

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/samsung-frame-art-gallery.git
   cd samsung-frame-art-gallery
   ```

2. **Configure your images path**

   Edit `docker-compose.yml` and update the images volume mount:
   ```yaml
   volumes:
     - /path/to/your/images:/images:ro
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Open the web UI**

   Navigate to `http://localhost:8080`

5. **Connect to your TV**

   Click the TV status indicator to discover and select your Samsung TV.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TV_IP` | - | Pre-configure TV IP (optional, can use auto-discovery) |
| `IMAGES_DIR` | `/images` | Container path for mounted images |
| `THUMBNAILS_DIR` | `/thumbnails` | Container path for thumbnail cache |

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
      - thumbnails:/thumbnails              # Thumbnail cache
      - ./data:/app/data                    # TV settings persistence
    environment:
      - TV_IP=${TV_IP:-}                    # Optional: default TV IP
    restart: unless-stopped

volumes:
  thumbnails:
```

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
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   ├── images.py           # Image listing & thumbnails
│   │   └── tv.py               # TV control endpoints
│   ├── services/
│   │   ├── tv_client.py        # Samsung TV WebSocket client
│   │   ├── tv_discovery.py     # SSDP TV discovery
│   │   ├── tv_settings.py      # Persistent settings
│   │   ├── tv_thumbnail_cache.py
│   │   └── thumbnails.py       # Local image thumbnails
│   └── frontend/               # Vue 3 + Vite SPA
├── docker/
│   └── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── _tasks/                     # Design docs & plans
```

### Tech Stack

- **Backend:** FastAPI, Python 3.11, Pillow
- **Frontend:** Vue 3, Vite
- **TV Communication:** [samsung-tv-ws-api](https://github.com/NickWaterton/samsung-tv-ws-api)
- **Infrastructure:** Docker, Docker Compose

## API Reference

### Images

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/images` | List images (optional `?folder=` filter) |
| GET | `/api/images/folders` | List available folders |
| GET | `/api/images/{path}/thumbnail` | Get image thumbnail |
| GET | `/api/images/{path}/full` | Get full image |

### TV Discovery

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tv/discover` | Scan for Samsung TVs |
| GET | `/api/tv/settings` | Get saved TV selection |
| POST | `/api/tv/settings` | Save TV selection |

### TV Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tv/status` | Get TV connection status |
| GET | `/api/tv/mattes` | Get available matte options |
| GET | `/api/tv/artwork` | List artwork on TV |
| GET | `/api/tv/artwork/current` | Get currently displayed artwork |
| POST | `/api/tv/artwork/current` | Display specific artwork |
| DELETE | `/api/tv/artwork/{id}` | Delete artwork from TV |
| POST | `/api/tv/upload` | Upload images to TV |

## TV Compatibility

Tested with Samsung Frame TVs. Should work with any Samsung TV that supports Art Mode via WebSocket API.

**Supported API versions:**
- v3.x (older models)
- v4.x+ (newer models with SSL)

## Troubleshooting

### TV not discovered

- Ensure your TV is on the same network as the host
- Try manually entering the TV IP address
- Check that the TV is powered on (not in standby)

### Upload fails

- Verify the TV is in Art Mode
- Check that the image format is supported (JPEG, PNG)
- Ensure sufficient storage on the TV

### Thumbnails not loading

- The first load generates thumbnails - give it time
- Check that the images volume is mounted correctly
- Verify read permissions on the images directory

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
- Samsung for creating the Frame TV with Art Mode
