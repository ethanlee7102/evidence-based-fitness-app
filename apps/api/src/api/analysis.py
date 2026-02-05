from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
import logging

from src.schema.analysis import (
    AnalyzeRequest,
    AnalysisResponse,
    IssueResponse,
    FrameLandmarks,
    LandmarkPoint,
)
from src.service.analysis_service import AnalysisService
from src.service.db_service import DBService
from src.utils.auth import get_current_user

router = APIRouter(prefix="/analysis", tags=["analysis"])
logger = logging.getLogger(__name__)


def _format_landmarks_response(landmarks: list[dict] | None) -> list[FrameLandmarks] | None:
    """Convert raw landmarks dict to response model."""
    if not landmarks:
        return None
    return [
        FrameLandmarks(
            frame=lm["frame"],
            points={
                int(k): LandmarkPoint(**v)
                for k, v in lm["points"].items()
            },
        )
        for lm in landmarks
    ]


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_video(request: AnalyzeRequest, user_id: str = Depends(get_current_user)):
    """Analyze a video for form issues."""
    try:
        analysis_service = AnalysisService()
        result = await analysis_service.analyze(
            video_url=request.video_url,
            exercise_type=request.exercise_type,
        )

        analysis_id = str(uuid4())

        db_service = DBService()
        db_service.save_analysis(
            analysis_id=analysis_id,
            user_id=user_id,
            video_url=request.video_url,
            exercise_type=request.exercise_type,
            technique_score=result["technique_score"],
            issues=result["issues"],
            bar_path=result.get("bar_path"),
            landmarks_data=result.get("landmarks"),
            fps=result.get("fps"),
        )

        return AnalysisResponse(
            id=analysis_id,
            techniqueScore=result["technique_score"],
            issues=[
                IssueResponse(
                    issue=issue["issue"],
                    severity=issue["severity"],
                    description=issue["description"],
                    frames=issue.get("frames"),
                )
                for issue in result["issues"]
            ],
            barPath=result.get("bar_path"),
            videoUrl=request.video_url,
            landmarks=_format_landmarks_response(result.get("landmarks")),
            fps=result.get("fps"),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.")


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: str, user_id: str = Depends(get_current_user)):
    """Get a previously completed analysis."""
    try:
        db_service = DBService()
        result = db_service.get_analysis_by_id(analysis_id, user_id)

        if not result:
            raise HTTPException(status_code=404, detail="Analysis not found")

        # Get video URL from the joined videos table
        video_url = None
        fps = None
        if "videos" in result:
            video_url = result["videos"].get("storage_path")
            fps = result["videos"].get("fps")

        return AnalysisResponse(
            id=result["id"],
            techniqueScore=result["technique_score"],
            issues=[
                IssueResponse(
                    issue=issue["issue"],
                    severity=issue["severity"],
                    description=issue["description"],
                    frames=issue.get("frames"),
                )
                for issue in result["issues"]
            ],
            barPath=result.get("bar_path_data"),
            videoUrl=video_url,
            landmarks=_format_landmarks_response(result.get("landmarks_data")),
            fps=fps,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get analysis")
        raise HTTPException(status_code=500, detail="Failed to retrieve analysis")
