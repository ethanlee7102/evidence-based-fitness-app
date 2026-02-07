from fastapi import APIRouter, Depends, HTTPException

from src.schema.profile import OnboardingRequest, ProfileResponse
from src.service.db_service import DBService
from src.utils.auth import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


def get_db_service() -> DBService:
    return DBService()


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    user_id: str = Depends(get_current_user),
    db: DBService = Depends(get_db_service),
) -> ProfileResponse:
    """Get the current user's profile."""
    profile = db.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse(**profile)


@router.post("/onboarding", response_model=ProfileResponse)
async def complete_onboarding(
    data: OnboardingRequest,
    user_id: str = Depends(get_current_user),
    db: DBService = Depends(get_db_service),
) -> ProfileResponse:
    """Complete onboarding for the current user."""
    profile = db.complete_onboarding(user_id, data)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse(**profile)
