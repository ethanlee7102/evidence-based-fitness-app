"""Pydantic models for workout routine (template) endpoints."""

from typing import Optional

from pydantic import BaseModel, Field

from src.schema.workout import ExerciseResponse, SetType

# --- Response Models ---

class RoutineSetResponse(BaseModel):
    id: str
    routine_exercise_id: str
    set_number: int
    target_reps: Optional[int] = None
    set_type: SetType = "normal"


class RoutineExerciseResponse(BaseModel):
    id: str
    routine_id: str
    exercise_id: str
    exercise: ExerciseResponse
    sort_order: int
    rest_timer_seconds: Optional[int] = None
    notes: Optional[str] = None
    sets: list[RoutineSetResponse] = []


class RoutineResponse(BaseModel):
    id: str
    user_id: str
    name: str
    last_used_at: Optional[str] = None
    use_count: int = 0
    created_at: str
    updated_at: str
    exercises: list[RoutineExerciseResponse] = []


class RoutineSummaryResponse(BaseModel):
    """Lightweight routine for list view."""
    id: str
    name: str
    exercise_count: int = 0
    total_sets: int = 0
    last_used_at: Optional[str] = None
    use_count: int = 0


# --- Request Models ---

class RoutineSetInput(BaseModel):
    set_number: int = Field(..., ge=1)
    target_reps: Optional[int] = Field(None, ge=0)
    set_type: SetType = "normal"


class RoutineExerciseInput(BaseModel):
    exercise_id: str
    sort_order: int = Field(..., ge=0)
    rest_timer_seconds: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=1000)
    sets: list[RoutineSetInput] = []


class SaveRoutineFullRequest(BaseModel):
    """Full routine save — name + all exercises + sets in one request."""
    name: str = Field(..., min_length=1, max_length=100)
    exercises: list[RoutineExerciseInput] = Field(..., min_length=1)


class SaveAsRoutineRequest(BaseModel):
    """Save a completed workout as a routine."""
    name: str = Field(..., min_length=1, max_length=100)
