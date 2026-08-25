"""Workout logging service.

Handles CRUD for workouts, workout_exercises, workout_sets, exercises,
and muscle_groups. Uses a per-request JWT-scoped client so Postgres RLS
enforces access; still filters by user_id in queries as defense in depth.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from src.db import get_user_supabase

logger = logging.getLogger(__name__)


def _single(query) -> Optional[dict[str, Any]]:
    """Execute a query expecting 0 or 1 rows. Returns the row dict or None.

    Supabase's maybe_single() raises/returns None on 406 (0 rows).
    This helper uses limit(1) instead, which always succeeds.
    """
    response = query.limit(1).execute()
    return response.data[0] if response.data else None


def _sanitize_filter(value: str) -> str:
    """Strip PostgREST operator characters to prevent filter injection."""
    return re.sub(r'[,.()\[\]{}]', '', value)


class WorkoutService:
    """Manages workout logging data in Supabase."""

    def __init__(self, token: str):
        # RLS-scoped to the caller's JWT (see src/db.get_user_supabase).
        self.supabase = get_user_supabase(token)

    # --- Muscle Groups ---

    def get_muscle_groups(self) -> list[dict[str, Any]]:
        """Get all muscle groups ordered by display_order."""
        response = (
            self.supabase.table("muscle_groups")
            .select("*")
            .order("display_order")
            .execute()
        )
        return response.data

    # --- Exercises ---

    def search_exercises(
        self,
        user_id: str,
        q: Optional[str] = None,
        equipment: Optional[str] = None,
        muscle_category: Optional[str] = None,
        limit: int = 400,
    ) -> list[dict[str, Any]]:
        """Search exercises visible to user (global + own custom)."""
        query = (
            self.supabase.table("exercises")
            .select("*, exercise_muscles(muscle_group_id, activation_level, muscle_groups(name, category))")
            .or_(f"is_global.eq.true,created_by.eq.{user_id}")
        )

        if q:
            safe_q = _sanitize_filter(q)
            if safe_q:
                query = query.or_(f"name.ilike.%{safe_q}%,aliases.cs.{{{safe_q}}}")

        if equipment:
            query = query.eq("equipment", equipment)

        query = query.order("name").limit(limit)
        response = query.execute()
        results = response.data

        if muscle_category:
            filtered = []
            for ex in results:
                muscles = ex.get("exercise_muscles", [])
                has_category = any(
                    m.get("muscle_groups", {}).get("category") == muscle_category
                    for m in muscles
                )
                if has_category:
                    filtered.append(ex)
            results = filtered

        return results

    def get_exercise(self, exercise_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """Get a single exercise with muscle groups."""
        return _single(
            self.supabase.table("exercises")
            .select("*, exercise_muscles(muscle_group_id, activation_level, muscle_groups(name, category))")
            .eq("id", exercise_id)
            .or_(f"is_global.eq.true,created_by.eq.{user_id}")
        )

    def create_exercise(
        self,
        user_id: str,
        name: str,
        equipment: Optional[str] = None,
        movement_pattern: Optional[str] = None,
        force_type: Optional[str] = None,
        body_region: Optional[str] = None,
        laterality: str = "bilateral",
        is_compound: bool = True,
        instructions: list[str] | None = None,
        muscle_group_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a custom exercise for the user. Atomic: cleans up on muscle insert failure."""
        data = {
            "name": name,
            "equipment": equipment,
            "movement_pattern": movement_pattern,
            "force_type": force_type,
            "body_region": body_region,
            "laterality": laterality,
            "is_compound": is_compound,
            "instructions": instructions or [],
            "is_global": False,
            "created_by": user_id,
        }
        response = self.supabase.table("exercises").insert(data).execute()
        exercise = response.data[0]

        if muscle_group_ids:
            muscle_rows = [
                {
                    "exercise_id": exercise["id"],
                    "muscle_group_id": mg_id,
                    "activation_level": "high",
                }
                for mg_id in muscle_group_ids
            ]
            try:
                self.supabase.table("exercise_muscles").insert(muscle_rows).execute()
            except Exception as e:
                # Rollback: delete the orphaned exercise
                logger.error(f"Failed to insert muscle mappings, rolling back exercise: {e}")
                self.supabase.table("exercises").delete().eq("id", exercise["id"]).execute()
                raise

        return exercise

    # --- Workouts ---

    def start_workout(self, user_id: str) -> dict[str, Any]:
        """Create a new workout (in-progress)."""
        data = {"user_id": user_id}
        response = self.supabase.table("workouts").insert(data).execute()
        return response.data[0]

    def get_workout(self, workout_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """Get full workout with exercises and sets."""
        workout = _single(
            self.supabase.table("workouts")
            .select(
                "*, workout_exercises("
                "*, exercises(*, exercise_muscles(muscle_group_id, activation_level, muscle_groups(name, category))), "
                "workout_sets(*)"
                ")"
            )
            .eq("id", workout_id)
            # No user_id filter: RLS scopes to own rows + demo workouts for guests
            # (migration 017). Registered users still see only their own.
        )
        if not workout:
            return None

        # Sort exercises by sort_order, sets by set_number
        if workout.get("workout_exercises"):
            workout["workout_exercises"].sort(key=lambda we: we.get("sort_order", 0))
            for we in workout["workout_exercises"]:
                if we.get("workout_sets"):
                    we["workout_sets"].sort(key=lambda s: s.get("set_number", 0))
        return workout

    def get_in_progress_workout(self, user_id: str) -> Optional[dict[str, Any]]:
        """Get the user's current in-progress workout (if any)."""
        return _single(
            self.supabase.table("workouts")
            .select("*")
            .eq("user_id", user_id)
            .is_("completed_at", "null")
            .order("started_at", desc=True)
        )

    def list_workouts(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_rating: Optional[int] = None,
        exercise_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List workouts with summary info (exercise count, set count, volume)."""
        # Exercise filter: two-step lookup for workout IDs containing this exercise
        workout_id_filter: list[str] | None = None
        if exercise_id:
            we_resp = (
                self.supabase.table("workout_exercises")
                .select("workout_id")
                .eq("exercise_id", exercise_id)
                .execute()
            )
            workout_id_filter = list({r["workout_id"] for r in we_resp.data})
            if not workout_id_filter:
                return []

        query = (
            self.supabase.table("workouts")
            .select(
                "*, workout_exercises(id, exercises(name), workout_sets(weight_kg, reps, completed))"
            )
            # No user_id filter: RLS scopes to own + demo (guest). See migration 017.
        )

        if date_from:
            query = query.gte("started_at", date_from)
        if date_to:
            # Make end date inclusive of the full day
            end = datetime.fromisoformat(date_to) + timedelta(days=1)
            query = query.lt("started_at", end.isoformat())
        if min_rating:
            query = query.gte("rating", min_rating)
        if workout_id_filter is not None:
            query = query.in_("id", workout_id_filter)

        response = (
            query
            .order("started_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        summaries = []
        for w in response.data:
            exercises = w.get("workout_exercises", [])
            exercise_count = len(exercises)
            set_count = 0
            total_volume = 0.0

            for we in exercises:
                sets = we.get("workout_sets", [])
                for s in sets:
                    if s.get("completed"):
                        set_count += 1
                        weight = s.get("weight_kg") or 0
                        reps = s.get("reps") or 0
                        total_volume += weight * reps

            summaries.append({
                "id": w["id"],
                "user_id": w["user_id"],
                "started_at": w["started_at"],
                "completed_at": w.get("completed_at"),
                "duration_seconds": w.get("duration_seconds"),
                "rating": w.get("rating"),
                "notes": w.get("notes"),
                "exercise_count": exercise_count,
                "set_count": set_count,
                "total_volume_kg": round(total_volume, 1),
            })

        return summaries

    def finish_workout(
        self,
        workout_id: str,
        user_id: str,
        rating: Optional[int] = None,
        body_weight_kg: Optional[float] = None,
        notes: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        """Mark workout as completed. Returns None if not found or already completed."""
        workout = _single(
            self.supabase.table("workouts")
            .select("started_at, completed_at")
            .eq("id", workout_id)
            .eq("user_id", user_id)
        )
        if not workout:
            return None

        # Guard: don't allow finishing an already-completed workout
        if workout.get("completed_at"):
            return None

        now = datetime.now(timezone.utc)

        # Use client-provided duration (accounts for pause/resume) or fall back to wall-clock
        if duration_seconds is not None:
            duration = duration_seconds
        else:
            started = datetime.fromisoformat(workout["started_at"].replace("Z", "+00:00"))
            duration = int((now - started).total_seconds())

        update_data: dict[str, Any] = {
            "completed_at": now.isoformat(),
            "duration_seconds": duration,
        }
        if rating is not None:
            update_data["rating"] = rating
        if body_weight_kg is not None:
            update_data["body_weight_kg"] = body_weight_kg
        if notes is not None:
            update_data["notes"] = notes

        response = (
            self.supabase.table("workouts")
            .update(update_data)
            .eq("id", workout_id)
            .eq("user_id", user_id)
            .execute()
        )
        return response.data[0] if response.data else None

    def delete_workout(self, workout_id: str, user_id: str) -> bool:
        """Delete a workout. Returns True if deleted."""
        response = (
            self.supabase.table("workouts")
            .delete()
            .eq("id", workout_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(response.data) > 0

    # --- Workout Exercises ---

    def add_exercise_to_workout(
        self,
        workout_id: str,
        user_id: str,
        exercise_id: str,
        sort_order: int,
    ) -> Optional[dict[str, Any]]:
        """Add an exercise to a workout."""
        workout = _single(
            self.supabase.table("workouts")
            .select("id")
            .eq("id", workout_id)
            .eq("user_id", user_id)
        )
        if not workout:
            return None

        data = {
            "workout_id": workout_id,
            "exercise_id": exercise_id,
            "sort_order": sort_order,
        }
        response = self.supabase.table("workout_exercises").insert(data).execute()
        we = response.data[0]

        exercise = self.get_exercise(exercise_id, user_id)
        we["exercises"] = exercise
        we["workout_sets"] = []
        return we

    def remove_exercise_from_workout(
        self,
        workout_id: str,
        workout_exercise_id: str,
        user_id: str,
    ) -> bool:
        """Remove an exercise from a workout. Returns True if deleted."""
        workout = _single(
            self.supabase.table("workouts")
            .select("id")
            .eq("id", workout_id)
            .eq("user_id", user_id)
        )
        if not workout:
            return False

        response = (
            self.supabase.table("workout_exercises")
            .delete()
            .eq("id", workout_exercise_id)
            .eq("workout_id", workout_id)
            .execute()
        )
        return len(response.data) > 0

    def reorder_exercises(
        self,
        workout_id: str,
        user_id: str,
        order: list[dict],
    ) -> bool:
        """Reorder exercises in a workout.

        Note: makes N sequential DB calls. Acceptable for now since exercise
        counts per workout are small (<20). Consider an RPC if this becomes slow.
        """
        workout = _single(
            self.supabase.table("workouts")
            .select("id")
            .eq("id", workout_id)
            .eq("user_id", user_id)
        )
        if not workout:
            return False

        for item in order:
            self.supabase.table("workout_exercises").update(
                {"sort_order": item["sort_order"]}
            ).eq("id", item["workout_exercise_id"]).eq(
                "workout_id", workout_id
            ).execute()

        return True

    # --- Sets ---

    def add_set(
        self,
        workout_id: str,
        workout_exercise_id: str,
        user_id: str,
        set_number: int,
        weight_kg: Optional[float] = None,
        reps: Optional[int] = None,
        set_type: str = "normal",
    ) -> Optional[dict[str, Any]]:
        """Add a set to a workout exercise."""
        if not self._verify_workout_exercise_ownership(
            workout_id, workout_exercise_id, user_id
        ):
            return None

        data = {
            "workout_exercise_id": workout_exercise_id,
            "set_number": set_number,
            "weight_kg": weight_kg,
            "reps": reps,
            "set_type": set_type,
        }
        response = self.supabase.table("workout_sets").insert(data).execute()
        return response.data[0]

    def update_set(
        self,
        workout_id: str,
        set_id: str,
        user_id: str,
        updates: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Update a set (weight, reps, completed, etc.)."""
        set_row = _single(
            self.supabase.table("workout_sets")
            .select("*, workout_exercises!inner(workout_id, workouts!inner(user_id))")
            .eq("id", set_id)
        )
        if not set_row:
            return None

        we = set_row.get("workout_exercises", {})
        w = we.get("workouts", {})
        if we.get("workout_id") != workout_id or w.get("user_id") != user_id:
            return None

        if "completed" in updates:
            if updates["completed"]:
                updates["completed_at"] = datetime.now(timezone.utc).isoformat()
            else:
                updates["completed_at"] = None

        # Pass all updates through — Pydantic already validated via exclude_unset
        response = (
            self.supabase.table("workout_sets")
            .update(updates)
            .eq("id", set_id)
            .execute()
        )
        return response.data[0] if response.data else None

    def delete_set(
        self,
        workout_id: str,
        set_id: str,
        user_id: str,
    ) -> bool:
        """Delete a set. Returns True if deleted."""
        set_row = _single(
            self.supabase.table("workout_sets")
            .select("*, workout_exercises!inner(workout_id, workouts!inner(user_id))")
            .eq("id", set_id)
        )
        if not set_row:
            return False

        we = set_row.get("workout_exercises", {})
        w = we.get("workouts", {})
        if we.get("workout_id") != workout_id or w.get("user_id") != user_id:
            return False

        self.supabase.table("workout_sets").delete().eq("id", set_id).execute()
        return True

    # --- PREV Column ---

    def get_previous_sets(
        self,
        user_id: str,
        exercise_id: str,
    ) -> list[dict[str, Any]]:
        """Get sets from user's most recent completed workout containing this exercise."""
        response = (
            self.supabase.table("workout_exercises")
            .select(
                "id, workout_id, "
                "workouts!inner(user_id, completed_at, started_at), "
                "workout_sets(set_number, weight_kg, reps)"
            )
            .eq("exercise_id", exercise_id)
            # No workouts.user_id filter: RLS scopes to own + demo (guest, mig 017).
            .not_.is_("workouts.completed_at", "null")
            .order("workouts(started_at)", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            return []

        we = response.data[0]
        sets = we.get("workout_sets", [])
        sets.sort(key=lambda s: s.get("set_number", 0))

        return [
            {
                "set_number": s["set_number"],
                "weight_kg": s.get("weight_kg"),
                "reps": s.get("reps"),
            }
            for s in sets
        ]

    def update_workout_exercise(
        self,
        workout_id: str,
        workout_exercise_id: str,
        user_id: str,
        updates: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Update a workout exercise (rest_timer_seconds, notes)."""
        if not self._verify_workout_exercise_ownership(
            workout_id, workout_exercise_id, user_id
        ):
            return None

        response = (
            self.supabase.table("workout_exercises")
            .update(updates)
            .eq("id", workout_exercise_id)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_recent_exercises(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get exercises from user's most recent completed workouts, deduplicated."""
        response = (
            self.supabase.table("workout_exercises")
            .select(
                "exercise_id, "
                "workouts!inner(started_at, completed_at, user_id), "
                "exercises(*, exercise_muscles(muscle_group_id, activation_level, muscle_groups(name, category)))"
            )
            # No workouts.user_id filter: RLS scopes to own + demo (guest, mig 017).
            .not_.is_("workouts.completed_at", "null")
            .order("workouts(started_at)", desc=True)
            .limit(limit * 5)
            .execute()
        )

        seen: set[str] = set()
        results: list[dict[str, Any]] = []
        for row in response.data:
            eid = row["exercise_id"]
            if eid in seen:
                continue
            seen.add(eid)
            ex = row.get("exercises", {})
            if ex:
                results.append(ex)
            if len(results) >= limit:
                break

        return results

    # --- Exercise Stats ---

    def get_exercise_stats(
        self,
        user_id: str,
        exercise_id: str,
        recent_limit: int = 5,
    ) -> dict[str, Any]:
        """Get exercise stats: recent sets and per-session volume history."""
        # Fetch all completed sets for this exercise by this user
        response = (
            self.supabase.table("workout_exercises")
            .select(
                "exercise_id, "
                "workouts!inner(user_id, completed_at, started_at), "
                "workout_sets(weight_kg, reps, rpe, set_type, completed, completed_at)"
            )
            .eq("exercise_id", exercise_id)
            # No workouts.user_id filter: RLS scopes to own + demo (guest, mig 017).
            .not_.is_("workouts.completed_at", "null")
            .order("workouts(started_at)", desc=True)
            .execute()
        )

        # Build recent sets (flat list, newest first) and volume history (per session)
        recent_sets: list[dict[str, Any]] = []
        volume_history: list[dict[str, Any]] = []

        for we in response.data:
            workout = we.get("workouts", {})
            date = (workout.get("completed_at") or workout.get("started_at", ""))[:10]
            sets = we.get("workout_sets", [])

            session_volume = 0.0
            session_set_count = 0

            for s in sets:
                if not s.get("completed"):
                    continue
                weight = s.get("weight_kg") or 0
                reps = s.get("reps") or 0
                volume = weight * reps
                session_volume += volume
                session_set_count += 1

                recent_sets.append({
                    "date": date,
                    "weight_kg": s.get("weight_kg"),
                    "reps": s.get("reps"),
                    "rpe": s.get("rpe"),
                    "set_type": s.get("set_type", "normal"),
                    "volume": round(volume, 1),
                })

            if session_set_count > 0:
                volume_history.append({
                    "date": date,
                    "volume": round(session_volume, 1),
                    "sets": session_set_count,
                })

        # Volume history should be chronological (oldest first) for charting
        volume_history.reverse()

        return {
            "exercise_id": exercise_id,
            "recent_sets": recent_sets[:recent_limit],
            "volume_history": volume_history,
        }

    # --- Helpers ---

    def _verify_workout_exercise_ownership(
        self,
        workout_id: str,
        workout_exercise_id: str,
        user_id: str,
    ) -> bool:
        """Verify that workout_exercise belongs to the user's workout."""
        row = _single(
            self.supabase.table("workout_exercises")
            .select("id, workouts!inner(user_id)")
            .eq("id", workout_exercise_id)
            .eq("workout_id", workout_id)
            .eq("workouts.user_id", user_id)
        )
        return row is not None
