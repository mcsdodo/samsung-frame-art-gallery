from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_status():
    return {"connected": False, "message": "Not implemented"}
