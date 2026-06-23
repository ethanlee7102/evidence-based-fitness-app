"""Workout logging API — exercises, workouts, sets."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.schema.workout import (
    AddExerciseRequest,
    CreateExerciseRequest,
    CreateSetRequest,
    ExerciseResponse,
    ExerciseStatsResponse,
    FinishWorkoutRequest,
    MuscleGroupResponse,
    PreviousSetData,
    ReorderExercisesRequest,
    SetResponse,
    UpdateSetRequest,
    UpdateWorkoutExerciseRequest,
    WorkoutExerciseResponse,
    WorkoutResponse,
    WorkoutSummaryResponse,
)
from src.service.workout_service import WorkoutService
from src.utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workouts", tags=["workouts"])

_workout_service: WorkoutService | None = None


def _get_service() -> WorkoutService:
    global _workout_service
    if _workout_service is None:
        _workout_service = WorkoutService()
    return _workout_service


def _format_exercise(ex: dict) -> dict:
    """Format exercise data from DB join into ExerciseResponse shape."""
    muscles = []
    for em in ex.get("exercise_muscles", []):
        mg = em.get("muscle_groups", {})
        muscles.append({
            "muscle_group_id": em["muscle_group_id"],
            "muscle_group_name": mg.get("name", ""),
            "muscle_group_category": mg.get("category", ""),
            "activation_level": em["activation_level"],
        })
    return {
        "id": ex["id"],
        "name": ex["name"],
        "aliases": ex.get("aliases") or [],
        "equipment": ex.get("equipment"),
        "movement_pattern": ex.get("movement_pattern"),
        "force_type": ex.get("force_type"),
        "body_region": ex.get("body_region"),
        "laterality": ex.get("laterality", "bilateral"),
        "is_compound": ex.get("is_compound", True),
        "instructions": ex.get("instructions") or [],
        "video_url": ex.get("video_url"),
        "is_global": ex.get("is_global", False),
        "muscles": muscles,
    }


def _format_workout_response(workout: dict) -> dict:
    """Format full workout data from DB join into WorkoutResponse shape."""
    exercises = []
    for we in workout.get("workout_exercises", []):
        ex_data = we.get("exercises", {})
        exercise = _format_exercise(ex_data) if ex_data else {}

        sets = [
            {
                "id": s["id"],
                "workout_exercise_id": s["workout_exercise_id"],
                "set_number": s["set_number"],
                "weight_kg": s.get("weight_kg"),
                "reps": s.get("reps"),
                "rpe": s.get("rpe"),
                "set_type": s.get("set_type", "normal"),
                "duration_seconds": s.get("duration_seconds"),
                "rest_seconds": s.get("rest_seconds"),
                "is_to_failure": s.get("is_to_failure", False),
                "completed": s.get("completed", False),
                "completed_at": s.get("completed_at"),
                "created_at": s["created_at"],
            }
            for s in we.get("workout_sets", [])
        ]

        exercises.append({
            "id": we["id"],
            "workout_id": we["workout_id"],
            "exercise_id": we["exercise_id"],
            "exercise": exercise,
            "sort_order": we["sort_order"],
            "superset_group": we.get("superset_group"),
            "rest_timer_seconds": we.get("rest_timer_seconds"),
            "notes": we.get("notes"),
            "sets": sets,
        })

    return {
        "id": workout["id"],
        "user_id": workout["user_id"],
        "started_at": workout["started_at"],
        "completed_at": workout.get("completed_at"),
        "duration_seconds": workout.get("duration_seconds"),
        "body_weight_kg": workout.get("body_weight_kg"),
        "rating": workout.get("rating"),
        "notes": workout.get("notes"),
        "created_at": workout["created_at"],
        "exercises": exercises,
    }


# --- Muscle Groups ---

@router.get("/muscle-groups", response_model=list[MuscleGroupResponse])
async def get_muscle_groups(user_id: str = Depends(get_current_user)):
    """Get all muscle groups (for filters)."""
    svc = _get_service()
    return svc.get_muscle_groups()


# --- Exercises ---

@router.get("/exercises", response_model=list[ExerciseResponse])
async def search_exercises(
    q: Optional[str] = Query(None, min_length=1),
    equipment: Optional[str] = None,
    muscle_category: Optional[str] = None,
    user_id: str = Depends(get_current_user),
):
    """Search exercise library."""
    svc = _get_service()
    results = svc.search_exercises(user_id, q=q, equipment=equipment, muscle_category=muscle_category)
    return [_format_exercise(ex) for ex in results]


@router.get("/exercises/recent", response_model=list[ExerciseResponse])
async def get_recent_exercises(
    limit: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user),
):
    """Get recently used exercises from completed workouts."""
    svc = _get_service()
    results = svc.get_recent_exercises(user_id, limit=limit)
    return [_format_exercise(ex) for ex in results]


@router.get("/exercises/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise(exercise_id: str, user_id: str = Depends(get_current_user)):
    """Get exercise with muscle groups."""
    svc = _get_service()
    ex = svc.get_exercise(exercise_id, user_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return _format_exercise(ex)


@router.post("/exercises", response_model=ExerciseResponse)
async def create_exercise(
    body: CreateExerciseRequest,
    user_id: str = Depends(get_current_user),
):
    """Create a custom exercise."""
    svc = _get_service()
    ex = svc.create_exercise(
        user_id=user_id,
        name=body.name,
        equipment=body.equipment,
        movement_pattern=body.movement_pattern,
        force_type=body.force_type,
        body_region=body.body_region,
        laterality=body.laterality,
        is_compound=body.is_compound,
        instructions=body.instructions,
        muscle_group_ids=body.muscle_group_ids,
    )
    # Re-fetch with muscles for proper response
    full = svc.get_exercise(ex["id"], user_id)
    return _format_exercise(full) if full else ex


@router.get("/exercises/{exercise_id}/stats", response_model=ExerciseStatsResponse)
async def get_exercise_stats(
    exercise_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get user's stats for a specific exercise (recent sets + volume history)."""
    svc = _get_service()
    return svc.get_exercise_stats(user_id, exercise_id)


@router.get("/exercises/{exercise_id}/previous", response_model=list[PreviousSetData])
async def get_previous_sets(
    exercise_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get PREV column data — sets from last completed workout with this exercise."""
    svc = _get_service()
    return svc.get_previous_sets(user_id, exercise_id)


# --- Workouts ---

@router.post("", response_model=WorkoutResponse)
async def start_workout(user_id: str = Depends(get_current_user)):
    """Start a new workout."""
    svc = _get_service()
    workout = svc.start_workout(user_id)
    return {**workout, "exercises": []}


@router.get("", response_model=list[WorkoutSummaryResponse])
async def list_workouts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    exercise_id: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user),
):
    """List workout history (paginated, with optional filters)."""
    svc = _get_service()
    return svc.list_workouts(
        user_id,
        limit=limit,
        offset=offset,
        date_from=date_from,
        date_to=date_to,
        min_rating=min_rating,
        exercise_id=exercise_id,
    )


@router.get("/in-progress", response_model=Optional[WorkoutResponse])
async def get_in_progress_workout(user_id: str = Depends(get_current_user)):
    """Get current in-progress workout (if any)."""
    svc = _get_service()
    workout = svc.get_in_progress_workout(user_id)
    if not workout:
        return None
    # Fetch full details
    full = svc.get_workout(workout["id"], user_id)
    if not full:
        return None
    return _format_workout_response(full)


@router.get("/{workout_id}", response_model=WorkoutResponse)
async def get_workout(workout_id: str, user_id: str = Depends(get_current_user)):
    """Get full workout detail."""
    svc = _get_service()
    workout = svc.get_workout(workout_id, user_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    return _format_workout_response(workout)


@router.patch("/{workout_id}/finish", response_model=WorkoutResponse)
async def finish_workout(
    workout_id: str,
    body: FinishWorkoutRequest,
    user_id: str = Depends(get_current_user),
):
    """Finish a workout (set completed_at, duration, optional rating/body_weight)."""
    svc = _get_service()
    result = svc.finish_workout(
        workout_id, user_id,
        rating=body.rating,
        body_weight_kg=body.body_weight_kg,
        notes=body.notes,
        duration_seconds=body.duration_seconds,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Workout not found")
    # Return full workout
    full = svc.get_workout(workout_id, user_id)
    return _format_workout_response(full) if full else result


@router.delete("/{workout_id}")
async def delete_workout(workout_id: str, user_id: str = Depends(get_current_user)):
    """Delete a workout."""
    svc = _get_service()
    deleted = svc.delete_workout(workout_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workout not found")
    return {"detail": "Workout deleted"}


# --- Workout Exercises ---

@router.post("/{workout_id}/exercises", response_model=WorkoutExerciseResponse)
async def add_exercise_to_workout(
    workout_id: str,
    body: AddExerciseRequest,
    user_id: str = Depends(get_current_user),
):
    """Add an exercise to a workout."""
    svc = _get_service()
    result = svc.add_exercise_to_workout(
        workout_id, user_id, body.exercise_id, body.sort_order
    )
    if not result:
        raise HTTPException(status_code=404, detail="Workout not found")
    # Format into response shape
    ex_data = result.get("exercises", {})
    exercise = _format_exercise(ex_data) if ex_data else {}
    return {
        "id": result["id"],
        "workout_id": result["workout_id"],
        "exercise_id": result["exercise_id"],
        "exercise": exercise,
        "sort_order": result["sort_order"],
        "superset_group": result.get("superset_group"),
        "rest_timer_seconds": result.get("rest_timer_seconds"),
        "notes": result.get("notes"),
        "sets": [],
    }


@router.delete("/{workout_id}/exercises/{workout_exercise_id}")
async def remove_exercise_from_workout(
    workout_id: str,
    workout_exercise_id: str,
    user_id: str = Depends(get_current_user),
):
    """Remove an exercise from a workout."""
    svc = _get_service()
    deleted = svc.remove_exercise_from_workout(workout_id, workout_exercise_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Not found")
    return {"detail": "Exercise removed"}


@router.patch("/{workout_id}/exercises/reorder")
async def reorder_exercises(
    workout_id: str,
    body: ReorderExercisesRequest,
    user_id: str = Depends(get_current_user),
):
    """Reorder exercises in a workout."""
    svc = _get_service()
    success = svc.reorder_exercises(workout_id, user_id, [item.model_dump() for item in body.order])
    if not success:
        raise HTTPException(status_code=404, detail="Workout not found")
    return {"detail": "Exercises reordered"}


@router.patch("/{workout_id}/exercises/{workout_exercise_id}")
async def update_workout_exercise(
    workout_id: str,
    workout_exercise_id: str,
    body: UpdateWorkoutExerciseRequest,
    user_id: str = Depends(get_current_user),
):
    """Update a workout exercise (rest timer, notes)."""
    svc = _get_service()
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = svc.update_workout_exercise(workout_id, workout_exercise_id, user_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    return {"detail": "Updated"}


# --- Sets ---

@router.post("/{workout_id}/exercises/{workout_exercise_id}/sets", response_model=SetResponse)
async def add_set(
    workout_id: str,
    workout_exercise_id: str,
    body: CreateSetRequest,
    user_id: str = Depends(get_current_user),
):
    """Add a set to a workout exercise."""
    svc = _get_service()
    result = svc.add_set(
        workout_id, workout_exercise_id, user_id,
        set_number=body.set_number,
        weight_kg=body.weight_kg,
        reps=body.reps,
        set_type=body.set_type,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    return result


@router.patch("/{workout_id}/sets/{set_id}", response_model=SetResponse)
async def update_set(
    workout_id: str,
    set_id: str,
    body: UpdateSetRequest,
    user_id: str = Depends(get_current_user),
):
    """Update a set (weight, reps, checkmark, etc.)."""
    svc = _get_service()
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = svc.update_set(workout_id, set_id, user_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Set not found")
    return result


@router.delete("/{workout_id}/sets/{set_id}")
async def delete_set(
    workout_id: str,
    set_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete a set."""
    svc = _get_service()
    deleted = svc.delete_set(workout_id, set_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Set not found")
    return {"detail": "Set deleted"}
