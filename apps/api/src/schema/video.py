from pydantic import BaseModel
from datetime import datetime

from .common import ExerciseType


class VideoMetadata(BaseModel):
    id: str
    user_id: str
    storage_path: str
    exercise_type: ExerciseType
    duration_seconds: int | None = None
    uploaded_at: datetime
