from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Gender = Literal["male", "female", "other", "prefer_not_to_say"]
ExperienceLevel = Literal["beginner", "intermediate", "advanced"]
FitnessGoal = Literal["strength", "build_muscle", "lose_weight", "general_fitness", "cardio_endurance"]
UnitsPreference = Literal["metric", "imperial"]
DayOfWeek = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class OnboardingRequest(BaseModel):
    """Request body for completing onboarding."""

    display_name: str = Field(..., min_length=1, max_length=100)
    birthday: date
    gender: Gender
    height_cm: float = Field(..., gt=0, le=300)
    weight_kg: float = Field(..., gt=0, le=500)
    units_preference: UnitsPreference = "metric"
    experience_level: ExperienceLevel
    goal: FitnessGoal
    workout_days_per_week: int = Field(..., ge=1, le=7)
    preferred_days: Optional[list[DayOfWeek]] = None
    injuries_limitations: Optional[str] = Field(None, max_length=1000)


class ProfileResponse(BaseModel):
    """Response for profile endpoints."""

    id: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    birthday: Optional[date] = None
    gender: Optional[Gender] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    units_preference: UnitsPreference = "metric"
    experience_level: Optional[ExperienceLevel] = None
    goal: Optional[FitnessGoal] = None
    workout_days_per_week: Optional[int] = None
    preferred_days: Optional[list[DayOfWeek]] = None
    injuries_limitations: Optional[str] = None
    onboarding_completed: bool = False
    onboarding_completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
