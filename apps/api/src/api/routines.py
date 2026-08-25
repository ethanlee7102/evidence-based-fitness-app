"""Routine (template) API — CRUD, duplicate, start workout, save from workout."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.api.workouts import _format_exercise, _format_workout_response
from src.schema.routine import (
    RoutineResponse,
    RoutineSummaryResponse,
    SaveAsRoutineRequest,
    SaveRoutineFullRequest,
)
from src.schema.workout import WorkoutResponse
from src.service.routine_service import RoutineService
from src.utils.auth import get_current_token, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/routines", tags=["routines"])

def _get_service(token: str) -> RoutineService:
    # Per-request, RLS-scoped to the caller (no singleton).
    return RoutineService(token)


def _format_routine_response(routine: dict) -> dict:
    """Format full routine data from DB join into RoutineResponse shape."""
    exercises = []
    for re in routine.get("routine_exercises", []):
        ex_data = re.get("exercises", {})
        exercise = _format_exercise(ex_data) if ex_data else {}

        sets = [
            {
                "id": s["id"],
                "routine_exercise_id": s["routine_exercise_id"],
                "set_number": s["set_number"],
                "target_reps": s.get("target_reps"),
                "set_type": s.get("set_type", "normal"),
            }
            for s in re.get("routine_sets", [])
        ]

        exercises.append({
            "id": re["id"],
            "routine_id": re["routine_id"],
            "exercise_id": re["exercise_id"],
            "exercise": exercise,
            "sort_order": re["sort_order"],
            "rest_timer_seconds": re.get("rest_timer_seconds"),
            "notes": re.get("notes"),
            "sets": sets,
        })

    return {
        "id": routine["id"],
        "user_id": routine["user_id"],
        "name": routine["name"],
        "last_used_at": routine.get("last_used_at"),
        "use_count": routine.get("use_count", 0),
        "created_at": routine["created_at"],
        "updated_at": routine["updated_at"],
        "exercises": exercises,
    }


# --- CRUD ---

@router.get("", response_model=list[RoutineSummaryResponse])
async def list_routines(user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token)):
    """List all user's routines (summaries)."""
    svc = _get_service(token)
    return svc.list_routines(user_id)


@router.post("", response_model=RoutineResponse)
async def create_routine(
    body: SaveRoutineFullRequest,
    user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token),
):
    """Create a routine with exercises and sets."""
    svc = _get_service(token)
    routine = svc.create_routine_full(
        user_id,
        name=body.name,
        exercises=[ex.model_dump() for ex in body.exercises],
    )
    return _format_routine_response(routine)


@router.get("/{routine_id}", response_model=RoutineResponse)
async def get_routine(routine_id: str, user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token)):
    """Get full routine detail."""
    svc = _get_service(token)
    routine = svc.get_routine(routine_id, user_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    return _format_routine_response(routine)


@router.put("/{routine_id}", response_model=RoutineResponse)
async def update_routine(
    routine_id: str,
    body: SaveRoutineFullRequest,
    user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token),
):
    """Update a routine (full replacement)."""
    svc = _get_service(token)
    routine = svc.update_routine_full(
        routine_id,
        user_id,
        name=body.name,
        exercises=[ex.model_dump() for ex in body.exercises],
    )
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    return _format_routine_response(routine)


@router.delete("/{routine_id}")
async def delete_routine(routine_id: str, user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token)):
    """Delete a routine."""
    svc = _get_service(token)
    deleted = svc.delete_routine(routine_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Routine not found")
    return {"detail": "Routine deleted"}


# --- Duplicate ---

@router.post("/{routine_id}/duplicate", response_model=RoutineResponse)
async def duplicate_routine(routine_id: str, user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token)):
    """Clone a routine."""
    svc = _get_service(token)
    routine = svc.duplicate_routine(routine_id, user_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    return _format_routine_response(routine)


# --- Start Workout from Routine ---

@router.post("/{routine_id}/start-workout", response_model=WorkoutResponse)
async def start_workout_from_routine(
    routine_id: str,
    user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token),
):
    """Create a workout pre-populated from a routine."""
    svc = _get_service(token)
    workout = svc.start_workout_from_routine(routine_id, user_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Routine not found")
    return _format_workout_response(workout)


# --- Save Workout as Routine ---

@router.post("/from-workout/{workout_id}", response_model=RoutineResponse)
async def save_workout_as_routine(
    workout_id: str,
    body: SaveAsRoutineRequest,
    user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token),
):
    """Save a completed workout as a routine template."""
    svc = _get_service(token)
    routine = svc.save_workout_as_routine(workout_id, user_id, body.name)
    if not routine:
        raise HTTPException(status_code=404, detail="Workout not found or has no completed sets")
    return _format_routine_response(routine)
