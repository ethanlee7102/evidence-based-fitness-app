from pydantic import BaseModel

from .common import ExerciseType, CameraSide, IssueSeverity


class AnalyzeRequest(BaseModel):
    video_url: str
    exercise_type: ExerciseType
    camera_side: CameraSide


class IssueResponse(BaseModel):
    issue: str
    severity: IssueSeverity
    description: str
    frames: list[int] | None = None


class LandmarkPoint(BaseModel):
    x: float
    y: float
    visibility: float


class FrameLandmarks(BaseModel):
    frame: int
    points: dict[int, LandmarkPoint]


class PhaseBoundary(BaseModel):
    y: float
    between_phases: list[int]


class AnalysisResponse(BaseModel):
    id: str
    techniqueScore: int
    issues: list[IssueResponse]
    barPath: list[dict] | None = None
    videoUrl: str | None = None
    landmarks: list[FrameLandmarks] | None = None
    fps: float | None = None
    phaseBoundaries: list[PhaseBoundary] | None = None
