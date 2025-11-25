from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os

from src.services.tv_client import get_tv_client

router = APIRouter()

IMAGES_DIR = Path(os.environ.get("IMAGES_DIR", "/images"))


def get_safe_path(relative_path: str) -> Path:
    full_path = (IMAGES_DIR / relative_path).resolve()
    if not str(full_path).startswith(str(IMAGES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    return full_path


class SetCurrentRequest(BaseModel):
    content_id: str


class UploadRequest(BaseModel):
    paths: list[str]
    matte_style: str = "none"
    matte_color: str = "neutral"
    display: bool = False


@router.get("/status")
async def get_status():
    client = get_tv_client()
    return client.get_status()


@router.get("/mattes")
async def get_mattes():
    client = get_tv_client()
    return client.get_matte_options()


@router.get("/artwork")
async def list_artwork():
    client = get_tv_client()
    try:
        artwork = client.get_artwork_list()
        return {"artwork": artwork, "count": len(artwork)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/artwork/current")
async def get_current_artwork():
    client = get_tv_client()
    try:
        return client.get_current_artwork()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/artwork/current")
async def set_current_artwork(request: SetCurrentRequest):
    client = get_tv_client()
    try:
        client.set_current_artwork(request.content_id)
        return {"success": True, "content_id": request.content_id}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.delete("/artwork/{content_id}")
async def delete_artwork(content_id: str):
    client = get_tv_client()
    try:
        client.delete_artwork(content_id)
        return {"success": True, "deleted": content_id}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/artwork/{content_id}/thumbnail")
async def get_artwork_thumbnail(content_id: str):
    client = get_tv_client()
    try:
        thumbnail_data = client.get_thumbnail(content_id)
        if not thumbnail_data:
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        return Response(content=thumbnail_data, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/upload")
async def upload_artwork(request: UploadRequest):
    client = get_tv_client()
    results = []

    for path in request.paths:
        try:
            image_path = get_safe_path(path)
            if not image_path.exists():
                results.append({"path": path, "success": False, "error": "File not found"})
                continue

            image_data = image_path.read_bytes()
            result = client.upload_artwork(
                image_data,
                matte=request.matte_style,
                matte_color=request.matte_color,
                display=request.display and len(request.paths) == 1
            )
            results.append({"path": path, "success": True, "result": result})
        except Exception as e:
            results.append({"path": path, "success": False, "error": str(e)})

    # If display requested and multiple images, display the last one
    if request.display and len(request.paths) > 1:
        last_success = next((r for r in reversed(results) if r["success"]), None)
        if last_success and "content_id" in last_success.get("result", {}):
            try:
                client.set_current_artwork(last_success["result"]["content_id"])
            except:
                pass

    return {"results": results}
