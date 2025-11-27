from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio
import base64

from src.services.met_client import get_met_client
from src.services.tv_client import get_tv_client, TVClient
from src.services.image_processor import generate_preview, process_for_tv

router = APIRouter()


def require_tv_client() -> TVClient:
    """Get TV client or raise 503 if not configured."""
    client = get_tv_client()
    if client is None:
        raise HTTPException(status_code=503, detail="No TV configured")
    return client


@router.get("/departments")
async def get_departments():
    """Get list of museum departments."""
    client = get_met_client()
    departments = await asyncio.to_thread(client.get_departments)
    return {"departments": departments}


@router.get("/highlights")
async def get_highlights(page: int = 1, page_size: int = 48, medium: str = None):
    """Get highlighted artworks, paginated."""
    client = get_met_client()
    return await asyncio.to_thread(client.get_highlights, page, page_size, medium)


@router.get("/medium/{medium}")
async def get_by_medium(medium: str, page: int = 1, page_size: int = 48, highlights: bool = False):
    """Get artworks by medium (e.g., Paintings, Sculpture), paginated."""
    client = get_met_client()
    return await asyncio.to_thread(client.get_by_medium, medium, page, page_size, highlights)


@router.get("/objects")
async def get_objects(department_id: int, page: int = 1, page_size: int = 48, highlights: bool = False):
    """Get artworks by department, paginated."""
    client = get_met_client()
    return await asyncio.to_thread(client.get_by_department, department_id, page, page_size, highlights)


@router.get("/search")
async def search_objects(q: str, department_id: int = None, medium: str = None, highlights: bool = False, page: int = 1, page_size: int = 48):
    """Search artworks by keyword, optionally filtered by department, medium, or highlights."""
    client = get_met_client()
    return await asyncio.to_thread(client.search, q, department_id, medium, highlights, page, page_size)


@router.get("/object/{object_id}")
async def get_object(object_id: int):
    """Get single object details."""
    client = get_met_client()
    obj = await asyncio.to_thread(client.get_object, object_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj


class MetPreviewRequest(BaseModel):
    object_ids: list[int]
    crop_percent: int = 0
    matte_percent: int = 10


class MetUploadRequest(BaseModel):
    object_ids: list[int]
    crop_percent: int = 0
    matte_percent: int = 10
    display: bool = False


@router.post("/preview")
async def preview_met_artwork(request: MetPreviewRequest):
    """Generate preview of processed Met artwork (cropped + matted)."""
    met_client = get_met_client()
    previews = []

    for object_id in request.object_ids:
        try:
            obj = await asyncio.to_thread(met_client.get_object, object_id)
            if not obj:
                continue

            image_url = obj.get("primaryImage") or obj.get("primaryImageSmall")
            if not image_url:
                continue

            image_data = await asyncio.to_thread(met_client.fetch_image, image_url)
            original, processed = await asyncio.to_thread(
                generate_preview, image_data, request.crop_percent, request.matte_percent
            )

            previews.append({
                "id": object_id,
                "name": obj.get("title", "Untitled"),
                "original_url": f"data:image/jpeg;base64,{base64.b64encode(original).decode('utf-8')}",
                "processed_url": f"data:image/jpeg;base64,{base64.b64encode(processed).decode('utf-8')}"
            })
        except Exception as e:
            pass  # Skip failed previews silently

    return {"previews": previews}


@router.post("/upload")
async def upload_met_artwork(request: MetUploadRequest):
    """Download Met artwork, process, and upload to TV."""
    met_client = get_met_client()
    tv_client = require_tv_client()

    results = []
    for object_id in request.object_ids:
        try:
            # Get object details
            obj = await asyncio.to_thread(met_client.get_object, object_id)
            if not obj:
                results.append({"object_id": object_id, "success": False, "error": "Object not found"})
                continue

            # Get best available image URL
            image_url = obj.get("primaryImage") or obj.get("primaryImageSmall")
            if not image_url:
                results.append({"object_id": object_id, "success": False, "error": "No image available"})
                continue

            # Download image
            image_data = await asyncio.to_thread(met_client.fetch_image, image_url)

            # Process image (crop + matte)
            processed_data = await asyncio.to_thread(
                process_for_tv, image_data, request.crop_percent, request.matte_percent
            )

            # Upload to TV
            display_this = request.display and object_id == request.object_ids[-1]
            result = await asyncio.to_thread(
                tv_client.upload_artwork,
                processed_data,
                display_this
            )

            results.append({
                "object_id": object_id,
                "success": True,
                "content_id": result.get("content_id"),
                "title": obj.get("title", "Untitled")
            })
        except Exception as e:
            results.append({"object_id": object_id, "success": False, "error": str(e)})

    return {"results": results}
