from fastapi import APIRouter
from ..services.storage_service import StorageService

router = APIRouter()
storage = StorageService()

@router.get("/")
async def get_logs():
    """Fetch recent detection logs."""
    return {"logs": storage.get_logs()[::-1]} # Return newest first
