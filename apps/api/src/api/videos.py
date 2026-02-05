from fastapi import APIRouter, Depends

from src.utils.auth import get_current_user
from src.service.db_service import DBService

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("/")
async def list_videos(user_id: str = Depends(get_current_user)):
    """List all videos for the current user."""
    db_service = DBService()
    videos = await db_service.get_user_videos(user_id)
    return {"videos": videos}
