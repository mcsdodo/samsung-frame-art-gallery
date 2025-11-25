from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def list_images():
    return {"images": [], "message": "Not implemented"}
