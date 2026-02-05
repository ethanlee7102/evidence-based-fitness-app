from typing import Optional

from .base import BaseAnalyzer
from src.core.pose_estimator import PoseEstimator
from src.core.angle_calculator import (
    calculate_vertical_angle,
    calculate_horizontal_drift,
)


class SquatAnalyzer(BaseAnalyzer):
    """Analyze squat form from pose landmarks."""

    def analyze(self, landmarks_per_frame: list[Optional[dict[int, dict]]]) -> dict:
        issues = []
        scores = {
            "depth": 100,
            "knee_tracking": 100,
            "back_angle": 100,
            "bar_path": 100,
        }

        depth_info = self._analyze_depth(landmarks_per_frame)
        knee_info = self._analyze_knee_tracking(landmarks_per_frame)
        back_info = self._analyze_back_angle(landmarks_per_frame)
        bar_path = self.track_bar_path(landmarks_per_frame)

        if depth_info["achieved"]:
            pass
        elif depth_info["close"]:
            scores["depth"] -= 15
            issues.append({
                "issue": "slightly_high",
                "severity": "minor",
                "description": "Depth is close but hip crease doesn't quite break parallel.",
            })
        else:
            scores["depth"] -= 35
            issues.append({
                "issue": "insufficient_depth",
                "severity": "major",
                "description": "Squat depth is too high. Hip crease should go below the knee.",
            })

        if knee_info["caving_detected"]:
            severity = "major" if knee_info["severity"] > 0.1 else "moderate"
            penalty = min(35, int(knee_info["severity"] * 200))
            scores["knee_tracking"] -= penalty
            issues.append({
                "issue": "knee_valgus",
                "severity": severity,
                "description": "Knees caving inward detected. Push your knees out over your toes.",
                "frames": knee_info.get("frames", []),
            })

        if back_info["rounding_detected"]:
            scores["back_angle"] -= 25
            issues.append({
                "issue": "back_rounding",
                "severity": "moderate",
                "description": "Back rounding detected during ascent.",
            })

        if back_info["excessive_lean"]:
            scores["back_angle"] -= 20
            issues.append({
                "issue": "excessive_forward_lean",
                "severity": "moderate",
                "description": f"Forward lean is excessive ({back_info['max_angle']:.0f}°).",
            })

        if bar_path:
            drift = calculate_horizontal_drift(bar_path)
            if drift > 0.1:
                penalty = min(25, int(drift * 150))
                scores["bar_path"] -= penalty
                issues.append({
                    "issue": "bar_path_drift",
                    "severity": "moderate" if drift > 0.15 else "minor",
                    "description": "Bar path shows horizontal drift. Keep the bar over midfoot.",
                })

        total_score = (
            scores["depth"] * 0.30 +
            scores["knee_tracking"] * 0.25 +
            scores["back_angle"] * 0.25 +
            scores["bar_path"] * 0.20
        )

        return {
            "technique_score": max(0, min(100, int(total_score))),
            "issues": issues,
            "bar_path": bar_path,
            "component_scores": scores,
        }

    def _analyze_depth(self, landmarks_per_frame: list[Optional[dict[int, dict]]]) -> dict:
        min_hip_to_knee_diff = float("inf")

        for frame in landmarks_per_frame:
            if frame is None:
                continue

            left_hip = PoseEstimator.get_landmark(frame, self.LEFT_HIP)
            left_knee = PoseEstimator.get_landmark(frame, self.LEFT_KNEE)

            if PoseEstimator.is_visible(left_hip) and PoseEstimator.is_visible(left_knee):
                diff = left_hip["y"] - left_knee["y"]
                min_hip_to_knee_diff = min(min_hip_to_knee_diff, diff)

        if min_hip_to_knee_diff == float("inf"):
            return {"achieved": True, "close": False}

        if min_hip_to_knee_diff > 0.02:
            return {"achieved": True, "close": False}
        elif min_hip_to_knee_diff > -0.03:
            return {"achieved": False, "close": True}
        else:
            return {"achieved": False, "close": False}

    def _analyze_knee_tracking(self, landmarks_per_frame: list[Optional[dict[int, dict]]]) -> dict:
        caving_frames = []
        max_caving = 0.0

        for i, frame in enumerate(landmarks_per_frame):
            if frame is None:
                continue

            left_hip = PoseEstimator.get_landmark(frame, self.LEFT_HIP)
            left_knee = PoseEstimator.get_landmark(frame, self.LEFT_KNEE)
            left_ankle = PoseEstimator.get_landmark(frame, self.LEFT_ANKLE)
            right_hip = PoseEstimator.get_landmark(frame, self.RIGHT_HIP)
            right_knee = PoseEstimator.get_landmark(frame, self.RIGHT_KNEE)
            right_ankle = PoseEstimator.get_landmark(frame, self.RIGHT_ANKLE)

            if all([
                PoseEstimator.is_visible(left_hip),
                PoseEstimator.is_visible(left_knee),
                PoseEstimator.is_visible(left_ankle),
                PoseEstimator.is_visible(right_hip),
                PoseEstimator.is_visible(right_knee),
                PoseEstimator.is_visible(right_ankle),
            ]):
                hip_width = abs(right_hip["x"] - left_hip["x"])
                knee_width = abs(right_knee["x"] - left_knee["x"])
                ankle_width = abs(right_ankle["x"] - left_ankle["x"])

                if hip_width > 0 and ankle_width > 0:
                    expected_knee_width = (hip_width + ankle_width) / 2
                    caving = max(0, (expected_knee_width - knee_width) / expected_knee_width)

                    if caving > 0.1:
                        caving_frames.append(i)
                        max_caving = max(max_caving, caving)

        return {
            "caving_detected": len(caving_frames) > 5,
            "severity": max_caving,
            "frames": caving_frames[:5],
        }

    def _analyze_back_angle(self, landmarks_per_frame: list[Optional[dict[int, dict]]]) -> dict:
        back_angles = []

        for frame in landmarks_per_frame:
            if frame is None:
                continue

            left_shoulder = PoseEstimator.get_landmark(frame, self.LEFT_SHOULDER)
            left_hip = PoseEstimator.get_landmark(frame, self.LEFT_HIP)

            if PoseEstimator.is_visible(left_shoulder) and PoseEstimator.is_visible(left_hip):
                angle = calculate_vertical_angle(left_shoulder, left_hip)
                back_angles.append(angle)

        if not back_angles:
            return {"rounding_detected": False, "excessive_lean": False, "max_angle": 0}

        max_angle = max(back_angles)
        angle_variation = max(back_angles) - min(back_angles)

        return {
            "rounding_detected": angle_variation > 20,
            "excessive_lean": max_angle > 55,
            "max_angle": max_angle,
        }
