import logging
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from src.api import images, tv
from src.services.thumbnails import initialize_thumbnails
from src.services.tv_client import TVClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize thumbnail cache on startup in background thread."""
    logger.info("Starting Samsung Frame Art Gallery...")
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(initialize_thumbnails)

    # Initialize TV client from saved settings
    try:
        tv_client = TVClient.initialize_from_settings()
        if tv_client:
            logger.info(f"TV client initialized for {tv_client.ip}")
        else:
            logger.info("No TV configured, user will need to connect via UI")
    except Exception as e:
        logger.warning(f"Failed to initialize TV client from settings: {e}")
        logger.info("TV will need to be configured via the connection modal")

    yield
    executor.shutdown(wait=False)


app = FastAPI(title="Samsung Frame Art Gallery", lifespan=lifespan)

# API routes
app.include_router(images.router, prefix="/api/images", tags=["images"])
app.include_router(tv.router, prefix="/api/tv", tags=["tv"])

# Serve static frontend (Vue build output)
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = static_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_path / "index.html")
