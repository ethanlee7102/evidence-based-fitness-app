from datetime import datetime
from typing import Any, Optional

from src.db import get_supabase
from src.schema.profile import OnboardingRequest


class DBService:
    """Handles database operations."""

    def __init__(self):
        self.supabase = get_supabase()

    def get_profile(self, user_id: str) -> Optional[dict[str, Any]]:
        """Get a user's profile by ID."""
        response = (
            self.supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return response.data if response.data else None

    def complete_onboarding(
        self, user_id: str, data: OnboardingRequest
    ) -> Optional[dict[str, Any]]:
        """Complete onboarding by updating the user's profile."""
        update_data = {
            "display_name": data.display_name,
            "birthday": data.birthday.isoformat(),
            "gender": data.gender,
            "height_cm": data.height_cm,
            "weight_kg": data.weight_kg,
            "units_preference": data.units_preference,
            "experience_level": data.experience_level,
            "goal": data.goal,
            "workout_days_per_week": data.workout_days_per_week,
            "preferred_days": data.preferred_days,
            "injuries_limitations": data.injuries_limitations,
            "onboarding_completed": True,
            "onboarding_completed_at": datetime.utcnow().isoformat(),
        }

        response = (
            self.supabase.table("profiles")
            .update(update_data)
            .eq("id", user_id)
            .execute()
        )

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None

    # New workout methods will go here
