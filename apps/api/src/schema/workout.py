"""Pydantic models for workout logging endpoints."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Equipment = Literal[
    "barbell", "dumbbell", "cable", "machine", "bodyweight",
    "band", "kettlebell", "other"
]
MovementPattern = Literal["push", "pull", "squat", "hinge", "carry", "isolation", "other"]
ForceType = Literal["push", "pull", "static"]
BodyRegion = Literal["upper", "lower", "full"]
Laterality = Literal["bilateral", "unilateral"]
ActivationLevel = Literal["maximum", "high", "medium", "partial"]
SetType = Literal["normal", "warmup", "dropset", "failure"]


# --- Muscle Groups ---

class MuscleGroupResponse(BaseModel):
    id: str
    name: str
    category: str
    display_order: int


# --- Exercises ---

class ExerciseMuscleResponse(BaseModel):
    muscle_group_id: str
    muscle_group_name: str
    muscle_group_category: str
    activation_level: ActivationLevel


class ExerciseResponse(BaseModel):
    id: str
    name: str
    aliases: list[str] = []
    equipment: Optional[Equipment] = None
    movement_pattern: Optional[MovementPattern] = None
    force_type: Optional[ForceType] = None
    body_region: Optional[BodyRegion] = None
    laterality: Laterality = "bilateral"
    is_compound: bool = True
    instructions: list[str] = []
    video_url: Optional[str] = None
    is_global: bool = False
    muscles: list[ExerciseMuscleResponse] = []


class CreateExerciseRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    equipment: Optional[Equipment] = None
    movement_pattern: Optional[MovementPattern] = None
    force_type: Optional[ForceType] = None
    body_region: Optional[BodyRegion] = None
    laterality: Laterality = "bilateral"
    is_compound: bool = True
    instructions: list[str] = []
    muscle_group_ids: list[str] = Field(default=[], description="Muscle group IDs with default 'high' activation")


# --- Sets ---

class SetResponse(BaseModel):
    id: str
    workout_exercise_id: str
    set_number: int
    weight_kg: Optional[float] = None
    reps: Optional[int] = None
    rpe: Optional[float] = None
    set_type: SetType = "normal"
    duration_seconds: Optional[int] = None
    rest_seconds: Optional[int] = None
    is_to_failure: bool = False
    completed: bool = False
    completed_at: Optional[str] = None
    created_at: str


class CreateSetRequest(BaseModel):
    set_number: int = Field(..., ge=1)
    weight_kg: Optional[float] = Field(None, ge=0)
    reps: Optional[int] = Field(None, ge=0)
    set_type: SetType = "normal"


class UpdateSetRequest(BaseModel):
    weight_kg: Optional[float] = Field(None, ge=0)
    reps: Optional[int] = Field(None, ge=0)
    rpe: Optional[float] = Field(None, ge=1, le=10)
    set_type: Optional[SetType] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    rest_seconds: Optional[int] = Field(None, ge=0)
    is_to_failure: Optional[bool] = None
    completed: Optional[bool] = None


class UpdateWorkoutExerciseRequest(BaseModel):
    rest_timer_seconds: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=1000)


# --- Workout Exercises ---

class WorkoutExerciseResponse(BaseModel):
    id: str
    workout_id: str
    exercise_id: str
    exercise: ExerciseResponse
    sort_order: int
    superset_group: Optional[int] = None
    rest_timer_seconds: Optional[int] = None
    notes: Optional[str] = None
    sets: list[SetResponse] = []


class AddExerciseRequest(BaseModel):
    exercise_id: str
    sort_order: int = Field(..., ge=0)


class ReorderItem(BaseModel):
    workout_exercise_id: str
    sort_order: int = Field(..., ge=0)


class ReorderExercisesRequest(BaseModel):
    """List of {workout_exercise_id, sort_order} pairs."""
    order: list[ReorderItem]


# --- Workouts ---

class WorkoutResponse(BaseModel):
    id: str
    user_id: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    body_weight_kg: Optional[float] = None
    rating: Optional[int] = None
    notes: Optional[str] = None
    created_at: str
    exercises: list[WorkoutExerciseResponse] = []


class WorkoutSummaryResponse(BaseModel):
    """Lightweight workout for history listing."""
    id: str
    user_id: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    rating: Optional[int] = None
    notes: Optional[str] = None
    exercise_count: int = 0
    set_count: int = 0
    total_volume_kg: float = 0


class FinishWorkoutRequest(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    body_weight_kg: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = Field(None, max_length=1000)
    duration_seconds: Optional[int] = Field(None, ge=0)


class PreviousSetData(BaseModel):
    set_number: int
    weight_kg: Optional[float] = None
    reps: Optional[int] = None
