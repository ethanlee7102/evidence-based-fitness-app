"""Routine (template) service.

Handles CRUD for routines, routine_exercises, routine_sets,
plus starting workouts from routines and saving workouts as routines.
Uses a per-request JWT-scoped client so Postgres RLS enforces access; still
filters by user_id in queries as defense in depth.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from src.db import get_user_supabase
from src.service.workout_service import WorkoutService, _single

logger = logging.getLogger(__name__)


class RoutineService:
    """Manages workout routine templates in Supabase."""

    def __init__(self, token: str):
        # RLS-scoped to the caller's JWT (see src/db.get_user_supabase).
        self.supabase = get_user_supabase(token)
        # Pass the same token so the inner service's writes/reads are RLS-scoped
        # to the caller (not an un-scoped/admin client).
        self.workout_service = WorkoutService(token)

    # --- List ---

    def list_routines(self, user_id: str) -> list[dict[str, Any]]:
        """List routines with summary info, ordered by recency."""
        response = (
            self.supabase.table("routines")
            .select("*, routine_exercises(id, routine_sets(id))")
            .eq("user_id", user_id)
            .order("last_used_at", desc=True, nullsfirst=False)
            .order("created_at", desc=True)
            .execute()
        )

        summaries = []
        for r in response.data:
            exercises = r.get("routine_exercises", [])
            total_sets = sum(
                len(re.get("routine_sets", []))
                for re in exercises
            )
            summaries.append({
                "id": r["id"],
                "name": r["name"],
                "exercise_count": len(exercises),
                "total_sets": total_sets,
                "last_used_at": r.get("last_used_at"),
                "use_count": r.get("use_count", 0),
            })

        return summaries

    # --- Get ---

    def get_routine(self, routine_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """Get full routine with exercises (+ exercise details) and sets."""
        routine = _single(
            self.supabase.table("routines")
            .select(
                "*, routine_exercises("
                "*, exercises(*, exercise_muscles(muscle_group_id, activation_level, muscle_groups(name, category))), "
                "routine_sets(*)"
                ")"
            )
            .eq("id", routine_id)
            .eq("user_id", user_id)
        )
        if not routine:
            return None

        # Sort exercises by sort_order, sets by set_number
        if routine.get("routine_exercises"):
            routine["routine_exercises"].sort(key=lambda re: re.get("sort_order", 0))
            for re in routine["routine_exercises"]:
                if re.get("routine_sets"):
                    re["routine_sets"].sort(key=lambda s: s.get("set_number", 0))

        return routine

    # --- Create ---

    def create_routine_full(
        self,
        user_id: str,
        name: str,
        exercises: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create a routine with all exercises and sets in one shot."""
        # Insert routine
        routine_resp = (
            self.supabase.table("routines")
            .insert({"user_id": user_id, "name": name})
            .execute()
        )
        routine = routine_resp.data[0]
        routine_id = routine["id"]

        self._insert_exercises_and_sets(routine_id, exercises)

        return self.get_routine(routine_id, user_id)

    # --- Update ---

    def update_routine_full(
        self,
        routine_id: str,
        user_id: str,
        name: str,
        exercises: list[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Full-replace routine content: update name, delete old exercises, insert new."""
        # Verify ownership
        existing = _single(
            self.supabase.table("routines")
            .select("id")
            .eq("id", routine_id)
            .eq("user_id", user_id)
        )
        if not existing:
            return None

        # Update routine metadata
        now = datetime.now(timezone.utc).isoformat()
        self.supabase.table("routines").update({
            "name": name,
            "updated_at": now,
        }).eq("id", routine_id).execute()

        # Delete old exercises (cascade deletes sets)
        self.supabase.table("routine_exercises").delete().eq(
            "routine_id", routine_id
        ).execute()

        # Insert new exercises and sets
        self._insert_exercises_and_sets(routine_id, exercises)

        return self.get_routine(routine_id, user_id)

    # --- Delete ---

    def delete_routine(self, routine_id: str, user_id: str) -> bool:
        """Delete a routine. Returns True if deleted."""
        response = (
            self.supabase.table("routines")
            .delete()
            .eq("id", routine_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(response.data) > 0

    # --- Duplicate ---

    def duplicate_routine(self, routine_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """Clone a routine with name '{name} (Copy)', reset stats."""
        original = self.get_routine(routine_id, user_id)
        if not original:
            return None

        # Build exercise inputs from original
        exercises = []
        for re in original.get("routine_exercises", []):
            sets = [
                {
                    "set_number": s["set_number"],
                    "target_reps": s.get("target_reps"),
                    "set_type": s.get("set_type", "normal"),
                }
                for s in re.get("routine_sets", [])
            ]
            exercises.append({
                "exercise_id": re["exercise_id"],
                "sort_order": re["sort_order"],
                "rest_timer_seconds": re.get("rest_timer_seconds"),
                "notes": re.get("notes"),
                "sets": sets,
            })

        new_name = f"{original['name']} (Copy)"
        if len(new_name) > 100:
            new_name = new_name[:100]

        return self.create_routine_full(user_id, new_name, exercises)

    # --- Start Workout from Routine ---

    def start_workout_from_routine(
        self, routine_id: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        """Create a workout pre-populated from a routine template."""
        routine = self.get_routine(routine_id, user_id)
        if not routine:
            return None

        # Create the workout
        workout = self.workout_service.start_workout(user_id)
        workout_id = workout["id"]

        # Populate exercises and sets
        for re in routine.get("routine_exercises", []):
            we_data = {
                "workout_id": workout_id,
                "exercise_id": re["exercise_id"],
                "sort_order": re["sort_order"],
                "rest_timer_seconds": re.get("rest_timer_seconds"),
                "notes": re.get("notes"),
            }
            we_resp = self.supabase.table("workout_exercises").insert(we_data).execute()
            we = we_resp.data[0]

            for rs in re.get("routine_sets", []):
                set_data = {
                    "workout_exercise_id": we["id"],
                    "set_number": rs["set_number"],
                    "set_type": rs.get("set_type", "normal"),
                    "weight_kg": None,
                    "reps": rs.get("target_reps"),
                    "completed": False,
                }
                self.supabase.table("workout_sets").insert(set_data).execute()

        # Update routine usage stats
        now = datetime.now(timezone.utc).isoformat()
        self.supabase.table("routines").update({
            "last_used_at": now,
            "use_count": routine.get("use_count", 0) + 1,
        }).eq("id", routine_id).execute()

        return self.workout_service.get_workout(workout_id, user_id)

    # --- Save Workout as Routine ---

    def save_workout_as_routine(
        self, workout_id: str, user_id: str, name: str
    ) -> Optional[dict[str, Any]]:
        """Convert a completed workout into a routine template."""
        workout = self.workout_service.get_workout(workout_id, user_id)
        if not workout:
            return None

        # Build exercise inputs from workout
        exercises = []
        for we in workout.get("workout_exercises", []):
            sets = []
            for s in we.get("workout_sets", []):
                if s.get("completed"):
                    sets.append({
                        "set_number": s["set_number"],
                        "target_reps": s.get("reps"),
                        "set_type": s.get("set_type", "normal"),
                    })

            # Only include exercises that had completed sets
            if sets:
                exercises.append({
                    "exercise_id": we["exercise_id"],
                    "sort_order": we["sort_order"],
                    "rest_timer_seconds": we.get("rest_timer_seconds"),
                    "notes": we.get("notes"),
                    "sets": sets,
                })

        if not exercises:
            return None

        return self.create_routine_full(user_id, name, exercises)

    # --- Helpers ---

    def _insert_exercises_and_sets(
        self, routine_id: str, exercises: list[dict[str, Any]]
    ) -> None:
        """Insert routine_exercises and routine_sets rows."""
        for ex in exercises:
            re_data = {
                "routine_id": routine_id,
                "exercise_id": ex["exercise_id"],
                "sort_order": ex["sort_order"],
                "rest_timer_seconds": ex.get("rest_timer_seconds"),
                "notes": ex.get("notes"),
            }
            re_resp = self.supabase.table("routine_exercises").insert(re_data).execute()
            re_row = re_resp.data[0]

            sets = ex.get("sets", [])
            if sets:
                set_rows = [
                    {
                        "routine_exercise_id": re_row["id"],
                        "set_number": s["set_number"],
                        "target_reps": s.get("target_reps"),
                        "set_type": s.get("set_type", "normal"),
                    }
                    for s in sets
                ]
                self.supabase.table("routine_sets").insert(set_rows).execute()
