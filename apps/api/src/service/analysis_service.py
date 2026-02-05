from typing import Literal

from src.core.video_processor import VideoProcessor
from src.core.pose_estimator import PoseEstimator
from src.core.landmark_postprocessor import LandmarkPostProcessor
from src.core.analyzers import DeadliftAnalyzer, SquatAnalyzer, BenchAnalyzer


class AnalysisService:
    """Orchestrates the video analysis flow."""

    # Key landmark indices to include (body parts relevant for lifting)
    KEY_LANDMARKS = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

    def __init__(self):
        self.video_processor = VideoProcessor()
        self.pose_estimator = PoseEstimator()
        self.landmark_postprocessor = LandmarkPostProcessor()

    async def analyze(
        self,
        video_url: str,
        exercise_type: Literal["squat", "bench", "deadlift"],
    ) -> dict:
        """
        Main analysis pipeline: download video, extract landmarks, run analysis.
        """
        video_path, fps = await self.video_processor.download_video(video_url)

        try:
            landmarks_per_frame = self.pose_estimator.extract_landmarks(video_path)

            # Post-process landmarks to fix occlusion issues (e.g., ankles hidden by plates)
            # Lower threshold (0.5) since ankle visibility is often poor during deadlifts
            landmarks_per_frame = self.landmark_postprocessor.process(
                landmarks_per_frame,
                exercise_type,
                visibility_threshold=0.5,
            )

            if not landmarks_per_frame:
                return {
                    "technique_score": 0,
                    "issues": [
                        {
                            "issue": "no_pose_detected",
                            "severity": "major",
                            "description": "Could not detect a person in the video.",
                        }
                    ],
                    "fps": fps,
                }

            analyzer = self._get_analyzer(exercise_type)
            result = analyzer.analyze(landmarks_per_frame)

            # Convert landmarks to serializable format (sample every 2nd frame)
            result["landmarks"] = self._format_landmarks(landmarks_per_frame, sample_rate=2)
            result["fps"] = fps

            return result

        finally:
            self.video_processor.cleanup(video_path)

    def _format_landmarks(
        self,
        landmarks_per_frame: list,
        sample_rate: int = 1,
    ) -> list[dict]:
        """Convert landmarks to frontend-friendly format, sampling frames."""
        formatted = []

        for i, frame in enumerate(landmarks_per_frame):
            if i % sample_rate != 0:
                continue
            if frame is None:
                continue

            points = {}
            for idx in self.KEY_LANDMARKS:
                if idx in frame:
                    lm = frame[idx]
                    points[idx] = {
                        "x": lm["x"],
                        "y": lm["y"],
                        "visibility": lm.get("visibility", 1.0),
                    }

            if points:
                formatted.append({"frame": i, "points": points})

        return formatted

    def _get_analyzer(self, exercise_type: str):
        analyzers = {
            "deadlift": DeadliftAnalyzer,
            "squat": SquatAnalyzer,
            "bench": BenchAnalyzer,
        }

        analyzer_class = analyzers.get(exercise_type)
        if not analyzer_class:
            raise ValueError(f"Unknown exercise type: {exercise_type}")

        return analyzer_class()
