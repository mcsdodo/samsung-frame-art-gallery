from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os
import asyncio
import time
import base64

from src.services.tv_client import get_tv_client, TVClient
from src.services.tv_settings import load_settings, save_settings, TVSettings
from src.services.tv_discovery import discover_tvs
from src.services.image_processor import process_for_tv, generate_preview

router = APIRouter()


def require_tv_client() -> TVClient:
    """Get TV client or raise 503 if not configured."""
    client = get_tv_client()
    if client is None:
        raise HTTPException(status_code=503, detail="No TV configured")
    return client

IMAGES_DIR = Path(os.environ.get("IMAGES_DIR", "/images"))


def get_safe_path(relative_path: str) -> Path:
    full_path = (IMAGES_DIR / relative_path).resolve()
    if not str(full_path).startswith(str(IMAGES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    return full_path


class SetCurrentRequest(BaseModel):
    content_id: str


class PreviewRequest(BaseModel):
    paths: list[str]
    crop_percent: int = 0


class UploadRequest(BaseModel):
    paths: list[str]
    crop_percent: int = 0
    display: bool = False


class TVSettingsRequest(BaseModel):
    ip: str
    name: str = "Samsung TV"
    manual_entry: bool = False


@router.get("/settings")
async def get_tv_settings():
    """Get current TV settings."""
    settings = load_settings()
    return {
        "selected_tv_ip": settings.selected_tv_ip,
        "selected_tv_name": settings.selected_tv_name,
        "manual_entry": settings.manual_entry,
        "configured": settings.configured
    }


@router.post("/settings")
async def set_tv_settings(request: TVSettingsRequest):
    """Save TV settings and reconfigure client."""
    # Try to connect to verify TV is reachable
    try:
        client = TVClient.configure(request.ip)
        status = await asyncio.to_thread(client.get_status)
        if not status.get("connected"):
            raise HTTPException(
                status_code=400,
                detail=f"Could not connect to TV at {request.ip}: {status.get('error', 'Unknown error')}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not connect to TV: {e}")

    # Save settings
    settings = TVSettings(
        selected_tv_ip=request.ip,
        selected_tv_name=request.name,
        manual_entry=request.manual_entry
    )
    save_settings(settings)

    return {
        "success": True,
        "selected_tv_ip": settings.selected_tv_ip,
        "selected_tv_name": settings.selected_tv_name
    }


@router.get("/discover")
async def discover_samsung_tvs():
    """Discover Samsung TVs on the network."""
    start = time.time()

    tvs = await asyncio.to_thread(discover_tvs)

    return {
        "tvs": [{"ip": tv.ip, "name": tv.name, "model": tv.model} for tv in tvs],
        "scan_duration_ms": int((time.time() - start) * 1000)
    }


@router.get("/status")
async def get_status():
    client = get_tv_client()
    if client is None:
        return {"connected": False, "configured": False, "error": "No TV configured"}
    status = await asyncio.to_thread(client.get_status)
    status["configured"] = True
    return status


@router.get("/artwork")
async def list_artwork():
    client = require_tv_client()
    try:
        artwork = await asyncio.to_thread(client.get_artwork_list)
        return {"artwork": artwork, "count": len(artwork)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/artwork/current")
async def get_current_artwork():
    client = require_tv_client()
    try:
        return await asyncio.to_thread(client.get_current_artwork)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/artwork/current")
async def set_current_artwork(request: SetCurrentRequest):
    client = require_tv_client()
    try:
        await asyncio.to_thread(client.set_current_artwork, request.content_id)
        return {"success": True, "content_id": request.content_id}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.delete("/artwork/{content_id}")
async def delete_artwork(content_id: str):
    client = require_tv_client()
    try:
        await asyncio.to_thread(client.delete_artwork, content_id)
        return {"success": True, "deleted": content_id}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/artwork/{content_id}/thumbnail")
async def get_artwork_thumbnail(content_id: str):
    """Get thumbnail for TV artwork. May timeout for built-in Samsung content."""
    client = require_tv_client()
    try:
        # Run blocking TV call in thread pool to not block event loop
        thumbnail_data = await asyncio.to_thread(client.get_thumbnail, content_id)
        if not thumbnail_data:
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        return Response(content=thumbnail_data, media_type="image/jpeg")
    except Exception as e:
        # Thumbnail retrieval often times out for built-in Samsung content
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/preview")
async def preview_processed(request: PreviewRequest):
    """Generate preview of processed images (cropped + matted)."""
    previews = []

    for path in request.paths:
        try:
            image_path = get_safe_path(path)
            if not image_path.exists():
                continue

            image_data = image_path.read_bytes()
            original, processed = await asyncio.to_thread(
                generate_preview, image_data, request.crop_percent
            )

            previews.append({
                "id": path,
                "name": image_path.name,
                "original": base64.b64encode(original).decode('utf-8'),
                "processed": base64.b64encode(processed).decode('utf-8')
            })
        except Exception as e:
            pass  # Skip failed previews silently

    return {"previews": previews}


@router.post("/upload")
async def upload_artwork(request: UploadRequest):
    client = require_tv_client()
    results = []

    for path in request.paths:
        try:
            image_path = get_safe_path(path)
            if not image_path.exists():
                results.append({"path": path, "success": False, "error": "File not found"})
                continue

            image_data = image_path.read_bytes()

            # Process image (crop + matte)
            processed_data = await asyncio.to_thread(
                process_for_tv, image_data, request.crop_percent
            )

            # Run blocking TV upload in thread pool
            result = await asyncio.to_thread(
                client.upload_artwork,
                processed_data,
                request.display and len(request.paths) == 1
            )
            results.append({"path": path, "success": True, "result": result})
        except Exception as e:
            results.append({"path": path, "success": False, "error": str(e)})

    # If display requested and multiple images, display the last one
    if request.display and len(request.paths) > 1:
        last_success = next((r for r in reversed(results) if r["success"]), None)
        if last_success and "content_id" in last_success.get("result", {}):
            try:
                await asyncio.to_thread(
                    client.set_current_artwork,
                    last_success["result"]["content_id"]
                )
            except:
                pass

    return {"results": results}
