import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from src.services.thumbnails import generate_thumbnail, get_image_dimensions

router = APIRouter()

IMAGES_DIR = Path(os.environ.get("IMAGES_DIR", "/images"))
ALLOWED_EXTENSIONS = {".jpg", ".jpeg"}


def is_valid_image(path: Path) -> bool:
    return path.suffix.lower() in ALLOWED_EXTENSIONS and path.is_file()


def get_safe_path(relative_path: str) -> Path:
    """Prevent directory traversal attacks."""
    full_path = (IMAGES_DIR / relative_path).resolve()
    if not str(full_path).startswith(str(IMAGES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    return full_path


@router.get("")
async def list_images(folder: str = Query(None)):
    if not IMAGES_DIR.exists():
        return {"images": [], "folder": folder}

    if folder is None:
        # List ALL images recursively
        images = []
        for path in IMAGES_DIR.rglob("*"):
            if is_valid_image(path):
                rel_path = path.relative_to(IMAGES_DIR)
                width, height = get_image_dimensions(path)
                images.append({
                    "path": str(rel_path),
                    "name": path.name,
                    "size": path.stat().st_size,
                    "width": width,
                    "height": height
                })
    else:
        # List images in specific folder only
        search_dir = get_safe_path(folder)
        if not search_dir.exists() or not search_dir.is_dir():
            raise HTTPException(status_code=404, detail="Folder not found")

        images = []
        for path in search_dir.iterdir():
            if is_valid_image(path):
                rel_path = path.relative_to(IMAGES_DIR)
                width, height = get_image_dimensions(path)
                images.append({
                    "path": str(rel_path),
                    "name": path.name,
                    "size": path.stat().st_size,
                    "width": width,
                    "height": height
                })

    images.sort(key=lambda x: x["name"].lower())
    return {"images": images, "folder": folder, "count": len(images)}


@router.get("/folders")
async def list_folders():
    if not IMAGES_DIR.exists():
        return {"folders": []}

    folders = []
    for path in IMAGES_DIR.rglob("*"):
        if path.is_dir():
            rel_path = path.relative_to(IMAGES_DIR)
            folders.append(str(rel_path))

    folders.sort()
    return {"folders": folders}


@router.get("/{path:path}/thumbnail")
async def get_thumbnail(path: str, size: int = 200):
    """Get thumbnail for an image. Size parameter controls max dimension (default 200, max 1200)."""
    # Clamp size between 50 and 1200
    size = min(max(size, 50), 1200)

    image_path = get_safe_path(path)

    if not is_valid_image(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        thumbnail_data = generate_thumbnail(image_path, size)
        return Response(content=thumbnail_data, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{path:path}/full")
async def get_full_image(path: str):
    image_path = get_safe_path(path)

    if not is_valid_image(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return Response(content=image_path.read_bytes(), media_type="image/jpeg")
