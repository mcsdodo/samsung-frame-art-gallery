from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio

from src.services.met_client import get_met_client
from src.services.tv_client import get_tv_client, TVClient

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
async def get_highlights(page: int = 1, page_size: int = 24):
    """Get highlighted artworks, paginated."""
    client = get_met_client()
    return await asyncio.to_thread(client.get_highlights, page, page_size)


@router.get("/objects")
async def get_objects(department_id: int, page: int = 1, page_size: int = 24):
    """Get artworks by department, paginated."""
    client = get_met_client()
    return await asyncio.to_thread(client.get_by_department, department_id, page, page_size)


@router.get("/object/{object_id}")
async def get_object(object_id: int):
    """Get single object details."""
    client = get_met_client()
    obj = await asyncio.to_thread(client.get_object, object_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj


class MetUploadRequest(BaseModel):
    object_ids: list[int]
    matte_style: str = "none"
    matte_color: str = "neutral"
    display: bool = False


@router.post("/upload")
async def upload_met_artwork(request: MetUploadRequest):
    """Download Met artwork and upload to TV."""
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

            # Upload to TV
            display_this = request.display and object_id == request.object_ids[-1]
            result = await asyncio.to_thread(
                tv_client.upload_artwork,
                image_data,
                request.matte_style,
                request.matte_color,
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
