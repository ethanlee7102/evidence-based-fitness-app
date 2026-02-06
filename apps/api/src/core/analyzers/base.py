from abc import ABC, abstractmethod
from typing import Literal, Optional

from src.core.pose_estimator import PoseEstimator


class BaseAnalyzer(ABC):
    """Base class for exercise-specific analyzers."""

    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def get_side_indices(self, camera_side: Literal["left", "right"]) -> dict[str, int]:
        """Get keypoint indices for the side facing the camera."""
        if camera_side == "left":
            return {
                "shoulder": self.LEFT_SHOULDER,
                "elbow": self.LEFT_ELBOW,
                "wrist": self.LEFT_WRIST,
                "hip": self.LEFT_HIP,
                "knee": self.LEFT_KNEE,
                "ankle": self.LEFT_ANKLE,
            }
        else:
            return {
                "shoulder": self.RIGHT_SHOULDER,
                "elbow": self.RIGHT_ELBOW,
                "wrist": self.RIGHT_WRIST,
                "hip": self.RIGHT_HIP,
                "knee": self.RIGHT_KNEE,
                "ankle": self.RIGHT_ANKLE,
            }

    @abstractmethod
    def analyze(
        self,
        landmarks_per_frame: list[Optional[dict[int, dict]]],
        camera_side: Literal["left", "right"],
    ) -> dict:
        """
        Analyze pose landmarks and return results.

        Returns:
            dict with:
            - technique_score: int (0-100)
            - issues: list of issue dicts
            - bar_path: optional list of bar positions
            - component_scores: dict of individual component scores
        """
        pass

    def track_bar_path(
        self,
        landmarks_per_frame: list[Optional[dict[int, dict]]],
    ) -> list[dict]:
        """Track bar position via wrist midpoint across frames."""
        bar_path = []

        for i, frame in enumerate(landmarks_per_frame):
            if frame is None:
                continue

            left_wrist = PoseEstimator.get_landmark(frame, self.LEFT_WRIST)
            right_wrist = PoseEstimator.get_landmark(frame, self.RIGHT_WRIST)

            if (
                PoseEstimator.is_visible(left_wrist) and
                PoseEstimator.is_visible(right_wrist)
            ):
                bar_pos = PoseEstimator.midpoint(left_wrist, right_wrist)
                bar_path.append({
                    "x": bar_pos["x"],
                    "y": bar_pos["y"],
                    "frame": i,
                })

        return bar_path
