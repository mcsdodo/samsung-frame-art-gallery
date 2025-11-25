from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.services.tv_client import get_tv_client

router = APIRouter()


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
