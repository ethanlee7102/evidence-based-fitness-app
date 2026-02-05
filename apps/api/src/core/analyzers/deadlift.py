from typing import Optional

from .base import BaseAnalyzer
from src.core.pose_estimator import PoseEstimator
from src.core.angle_calculator import (
    calculate_angle,
    calculate_vertical_angle,
    calculate_horizontal_drift,
    calculate_path_straightness,
)


class DeadliftAnalyzer(BaseAnalyzer):
    """
    Analyze deadlift form from pose landmarks.

    Key checks:
    1. Bar path (wrist tracking) - should be vertical and close to body
    2. Back angle - should maintain neutral spine, not round
    3. Hip hinge pattern - proper hip/knee coordination
    4. Lockout position - full hip extension at top
    """

    def analyze(self, landmarks_per_frame: list[Optional[dict[int, dict]]]) -> dict:
        issues = []
        scores = {
            "bar_path": 100,
            "back_position": 100,
            "hip_hinge": 100,
            "lockout": 100,
        }

        bar_path = self.track_bar_path(landmarks_per_frame)
        back_angles = self._analyze_back_position(landmarks_per_frame)
        hip_angles = self._analyze_hip_hinge(landmarks_per_frame)
        lockout_ok, lockout_issue = self._analyze_lockout(landmarks_per_frame)

        if bar_path:
            drift = calculate_horizontal_drift(bar_path)
            straightness = calculate_path_straightness(bar_path)

            if drift > 0.15:
                penalty = min(40, int(drift * 200))
                scores["bar_path"] -= penalty
                issues.append({
                    "issue": "excessive_bar_drift",
                    "severity": "major" if drift > 0.2 else "moderate",
                    "description": f"Bar path drifts {drift*100:.0f}% horizontally. Keep the bar close to your body.",
                })
            elif drift > 0.08:
                scores["bar_path"] -= 15
                issues.append({
                    "issue": "minor_bar_drift",
                    "severity": "minor",
                    "description": "Slight horizontal drift in bar path. Focus on dragging the bar up your legs.",
                })

            if straightness < 0.85:
                penalty = min(30, int((1 - straightness) * 100))
                scores["bar_path"] -= penalty
                if straightness < 0.7:
                    issues.append({
                        "issue": "curved_bar_path",
                        "severity": "moderate",
                        "description": "Bar path shows S-curve pattern. Work on pulling straight up.",
                    })

        if back_angles:
            max_back_angle = max(back_angles)
            angle_variation = max(back_angles) - min(back_angles)

            if max_back_angle > 60:
                penalty = min(40, int((max_back_angle - 60) * 2))
                scores["back_position"] -= penalty
                issues.append({
                    "issue": "excessive_forward_lean",
                    "severity": "major" if max_back_angle > 70 else "moderate",
                    "description": f"Back angle reaches {max_back_angle:.0f}° from vertical.",
                })

            if angle_variation > 25:
                scores["back_position"] -= 20
                issues.append({
                    "issue": "back_angle_inconsistent",
                    "severity": "moderate",
                    "description": "Back angle changes significantly during the lift.",
                })

        if hip_angles:
            min_hip_angle = min(hip_angles)

            if min_hip_angle < 70:
                penalty = min(20, int((70 - min_hip_angle) / 2))
                scores["hip_hinge"] -= penalty
                issues.append({
                    "issue": "limited_hip_hinge",
                    "severity": "minor",
                    "description": "Hip flexion may be limited. Ensure you're hinging at the hips.",
                })

        if not lockout_ok:
            scores["lockout"] -= 25
            issues.append({
                "issue": "incomplete_lockout",
                "severity": "moderate",
                "description": lockout_issue,
            })

        total_score = (
            scores["bar_path"] * 0.30 +
            scores["back_position"] * 0.35 +
            scores["hip_hinge"] * 0.20 +
            scores["lockout"] * 0.15
        )

        return {
            "technique_score": max(0, min(100, int(total_score))),
            "issues": issues,
            "bar_path": bar_path,
            "component_scores": scores,
        }

    def _analyze_back_position(
        self,
        landmarks_per_frame: list[Optional[dict[int, dict]]],
    ) -> list[float]:
        back_angles = []

        for frame in landmarks_per_frame:
            if frame is None:
                continue

            left_shoulder = PoseEstimator.get_landmark(frame, self.LEFT_SHOULDER)
            right_shoulder = PoseEstimator.get_landmark(frame, self.RIGHT_SHOULDER)
            left_hip = PoseEstimator.get_landmark(frame, self.LEFT_HIP)
            right_hip = PoseEstimator.get_landmark(frame, self.RIGHT_HIP)

            if not all([
                PoseEstimator.is_visible(left_shoulder),
                PoseEstimator.is_visible(right_shoulder),
                PoseEstimator.is_visible(left_hip),
                PoseEstimator.is_visible(right_hip),
            ]):
                continue

            shoulder_mid = PoseEstimator.midpoint(left_shoulder, right_shoulder)
            hip_mid = PoseEstimator.midpoint(left_hip, right_hip)

            angle = calculate_vertical_angle(shoulder_mid, hip_mid)
            back_angles.append(angle)

        return back_angles

    def _analyze_hip_hinge(
        self,
        landmarks_per_frame: list[Optional[dict[int, dict]]],
    ) -> list[float]:
        hip_angles = []

        for frame in landmarks_per_frame:
            if frame is None:
                continue

            left_shoulder = PoseEstimator.get_landmark(frame, self.LEFT_SHOULDER)
            left_hip = PoseEstimator.get_landmark(frame, self.LEFT_HIP)
            left_knee = PoseEstimator.get_landmark(frame, self.LEFT_KNEE)

            if all([
                PoseEstimator.is_visible(left_shoulder),
                PoseEstimator.is_visible(left_hip),
                PoseEstimator.is_visible(left_knee),
            ]):
                angle = calculate_angle(left_shoulder, left_hip, left_knee)
                hip_angles.append(angle)

        return hip_angles

    def _analyze_lockout(
        self,
        landmarks_per_frame: list[Optional[dict[int, dict]]],
    ) -> tuple[bool, str]:
        if not landmarks_per_frame:
            return True, ""

        final_frames = landmarks_per_frame[-10:]

        for frame in reversed(final_frames):
            if frame is None:
                continue

            left_shoulder = PoseEstimator.get_landmark(frame, self.LEFT_SHOULDER)
            left_hip = PoseEstimator.get_landmark(frame, self.LEFT_HIP)
            left_knee = PoseEstimator.get_landmark(frame, self.LEFT_KNEE)

            if not all([
                PoseEstimator.is_visible(left_shoulder),
                PoseEstimator.is_visible(left_hip),
                PoseEstimator.is_visible(left_knee),
            ]):
                continue

            hip_angle = calculate_angle(left_shoulder, left_hip, left_knee)

            if hip_angle < 160:
                return False, f"Hips not fully extended at lockout ({hip_angle:.0f}°)."

            break

        return True, ""
