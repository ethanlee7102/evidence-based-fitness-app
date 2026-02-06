from typing import Literal, Optional

from .base import BaseAnalyzer
from src.core.pose_estimator import PoseEstimator
from src.core.angle_calculator import calculate_angle


class BenchAnalyzer(BaseAnalyzer):
    """Analyze bench press form from pose landmarks."""

    def analyze(
        self,
        landmarks_per_frame: list[Optional[dict[int, dict]]],
        camera_side: Literal["left", "right"],
    ) -> dict:
        # Bench press is typically filmed from front or above, so we use both sides
        # for symmetry checks. camera_side is accepted for interface compatibility.
        _ = camera_side  # Bench uses both sides for symmetry analysis

        issues = []
        scores = {
            "bar_path": 100,
            "elbow_position": 100,
            "wrist_alignment": 100,
            "symmetry": 100,
        }

        bar_path = self.track_bar_path(landmarks_per_frame)
        elbow_info = self._analyze_elbow_angle(landmarks_per_frame)
        wrist_info = self._analyze_wrist_alignment(landmarks_per_frame)
        symmetry_info = self._analyze_symmetry(landmarks_per_frame)

        if bar_path and len(bar_path) > 10:
            path_pattern = self._analyze_bar_path_pattern(bar_path)

            if path_pattern["vertical_only"]:
                scores["bar_path"] -= 10
                issues.append({
                    "issue": "too_vertical_path",
                    "severity": "minor",
                    "description": "Bar path is very vertical. A slight J-curve is more efficient.",
                })

            if path_pattern["excessive_horizontal"]:
                scores["bar_path"] -= 25
                issues.append({
                    "issue": "excessive_horizontal_movement",
                    "severity": "moderate",
                    "description": "Bar path has excessive horizontal movement.",
                })

        if elbow_info["flare_detected"]:
            severity = "major" if elbow_info["avg_angle"] > 85 else "moderate"
            penalty = min(35, int((elbow_info["avg_angle"] - 75) * 2))
            scores["elbow_position"] -= penalty
            issues.append({
                "issue": "elbow_flare",
                "severity": severity,
                "description": f"Elbows flaring too wide ({elbow_info['avg_angle']:.0f}°).",
            })

        if elbow_info["too_tucked"]:
            scores["elbow_position"] -= 15
            issues.append({
                "issue": "elbows_too_tucked",
                "severity": "minor",
                "description": "Elbows may be tucked too much.",
            })

        if wrist_info["misalignment_detected"]:
            scores["wrist_alignment"] -= 20
            issues.append({
                "issue": "wrist_misalignment",
                "severity": "moderate",
                "description": "Wrists not stacking over elbows at bottom.",
            })

        if symmetry_info["asymmetric"]:
            scores["symmetry"] -= 15
            issues.append({
                "issue": "asymmetric_press",
                "severity": "minor",
                "description": "Left/right asymmetry detected.",
            })

        total_score = (
            scores["bar_path"] * 0.30 +
            scores["elbow_position"] * 0.30 +
            scores["wrist_alignment"] * 0.20 +
            scores["symmetry"] * 0.20
        )

        return {
            "technique_score": max(0, min(100, int(total_score))),
            "issues": issues,
            "bar_path": bar_path,
            "component_scores": scores,
        }

    def _analyze_bar_path_pattern(self, bar_path: list[dict]) -> dict:
        if len(bar_path) < 10:
            return {"vertical_only": False, "excessive_horizontal": False}

        x_values = [p["x"] for p in bar_path]
        y_values = [p["y"] for p in bar_path]

        x_range = max(x_values) - min(x_values)
        y_range = max(y_values) - min(y_values)

        if y_range == 0:
            return {"vertical_only": True, "excessive_horizontal": x_range > 0.1}

        ratio = x_range / y_range

        return {
            "vertical_only": ratio < 0.05,
            "excessive_horizontal": ratio > 0.3,
        }

    def _analyze_elbow_angle(self, landmarks_per_frame: list[Optional[dict[int, dict]]]) -> dict:
        elbow_angles = []

        for frame in landmarks_per_frame:
            if frame is None:
                continue

            left_shoulder = PoseEstimator.get_landmark(frame, self.LEFT_SHOULDER)
            right_shoulder = PoseEstimator.get_landmark(frame, self.RIGHT_SHOULDER)
            left_elbow = PoseEstimator.get_landmark(frame, self.LEFT_ELBOW)
            right_elbow = PoseEstimator.get_landmark(frame, self.RIGHT_ELBOW)

            if all([
                PoseEstimator.is_visible(left_shoulder),
                PoseEstimator.is_visible(right_shoulder),
                PoseEstimator.is_visible(left_elbow),
                PoseEstimator.is_visible(right_elbow),
            ]):
                shoulder_mid = PoseEstimator.midpoint(left_shoulder, right_shoulder)

                left_angle = calculate_angle(shoulder_mid, left_shoulder, left_elbow)
                right_angle = calculate_angle(shoulder_mid, right_shoulder, right_elbow)

                avg_angle = (left_angle + right_angle) / 2
                elbow_angles.append(avg_angle)

        if not elbow_angles:
            return {"flare_detected": False, "too_tucked": False, "avg_angle": 60}

        avg_angle = sum(elbow_angles) / len(elbow_angles)

        return {
            "flare_detected": avg_angle > 75,
            "too_tucked": avg_angle < 35,
            "avg_angle": avg_angle,
        }

    def _analyze_wrist_alignment(self, landmarks_per_frame: list[Optional[dict[int, dict]]]) -> dict:
        misalignment_count = 0
        total_frames = 0

        for frame in landmarks_per_frame:
            if frame is None:
                continue

            left_elbow = PoseEstimator.get_landmark(frame, self.LEFT_ELBOW)
            right_elbow = PoseEstimator.get_landmark(frame, self.RIGHT_ELBOW)
            left_wrist = PoseEstimator.get_landmark(frame, self.LEFT_WRIST)
            right_wrist = PoseEstimator.get_landmark(frame, self.RIGHT_WRIST)

            if all([
                PoseEstimator.is_visible(left_elbow),
                PoseEstimator.is_visible(right_elbow),
                PoseEstimator.is_visible(left_wrist),
                PoseEstimator.is_visible(right_wrist),
            ]):
                total_frames += 1

                left_diff = abs(left_wrist["x"] - left_elbow["x"])
                right_diff = abs(right_wrist["x"] - right_elbow["x"])

                if left_diff > 0.05 or right_diff > 0.05:
                    misalignment_count += 1

        if total_frames == 0:
            return {"misalignment_detected": False}

        return {"misalignment_detected": misalignment_count / total_frames > 0.3}

    def _analyze_symmetry(self, landmarks_per_frame: list[Optional[dict[int, dict]]]) -> dict:
        asymmetry_count = 0
        total_frames = 0

        for frame in landmarks_per_frame:
            if frame is None:
                continue

            left_wrist = PoseEstimator.get_landmark(frame, self.LEFT_WRIST)
            right_wrist = PoseEstimator.get_landmark(frame, self.RIGHT_WRIST)

            if PoseEstimator.is_visible(left_wrist) and PoseEstimator.is_visible(right_wrist):
                total_frames += 1

                if abs(left_wrist["y"] - right_wrist["y"]) > 0.05:
                    asymmetry_count += 1

        if total_frames == 0:
            return {"asymmetric": False}

        return {"asymmetric": asymmetry_count / total_frames > 0.4}
