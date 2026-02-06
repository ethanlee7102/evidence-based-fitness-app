from typing import Literal, Optional
from dataclasses import dataclass

from .base import BaseAnalyzer
from src.core.pose_estimator import PoseEstimator
from src.core.angle_calculator import (
    calculate_angle,
    calculate_angle_from_horizontal,
    calculate_knee_angle,
    calculate_horizontal_drift,
    calculate_wrist_to_leg_distance,
    calculate_shoulder_bar_position,
    calculate_body_width,
    calculate_distance,
)


@dataclass
class PhaseThresholds:
    """Thresholds for a single metric within a phase."""
    ideal_min: float
    ideal_max: float
    minor_min: float
    minor_max: float
    minor_penalty: int
    major_penalty: int


@dataclass
class PhaseConfig:
    """Configuration for all metrics in a single phase."""
    back_angle: PhaseThresholds
    thigh_angle: PhaseThresholds
    hip_angle: PhaseThresholds
    knee_angle: PhaseThresholds
    shoulder_position: PhaseThresholds
    bar_drift: PhaseThresholds


# Default thresholds per phase
# Angles: back_angle and thigh_angle are from horizontal (0°=horizontal, 90°=upright)
# Hip and knee angles are joint angles (180°=fully extended)
# Shoulder position: percentage (-=in front, +=behind bar)
# Bar drift: percentage of body width from start
#
# Note: wrist_to_leg uses a different threshold system based on upper arm length
# (see WRIST_TO_LEG_THRESHOLD below)

PHASE_THRESHOLDS: dict[int, PhaseConfig] = {
    1: PhaseConfig(
        back_angle=PhaseThresholds(30, 50, 25, 55, 5, 15),
        thigh_angle=PhaseThresholds(30, 50, 25, 55, 5, 10),
        hip_angle=PhaseThresholds(70, 90, 60, 100, 5, 15),
        knee_angle=PhaseThresholds(90, 120, 80, 130, 5, 10),
        shoulder_position=PhaseThresholds(-5, 5, -10, 10, 5, 15),
        bar_drift=PhaseThresholds(0, 3, 0, 6, 5, 15),
    ),
    2: PhaseConfig(
        back_angle=PhaseThresholds(40, 55, 35, 60, 5, 15),
        thigh_angle=PhaseThresholds(45, 65, 40, 70, 5, 10),
        hip_angle=PhaseThresholds(90, 120, 80, 130, 5, 15),
        knee_angle=PhaseThresholds(120, 150, 110, 160, 5, 10),
        shoulder_position=PhaseThresholds(-3, 8, -8, 12, 5, 15),
        bar_drift=PhaseThresholds(0, 4, 0, 7, 5, 15),
    ),
    3: PhaseConfig(
        back_angle=PhaseThresholds(55, 75, 50, 80, 5, 15),
        thigh_angle=PhaseThresholds(65, 80, 60, 85, 5, 10),
        hip_angle=PhaseThresholds(130, 160, 120, 165, 5, 15),
        knee_angle=PhaseThresholds(150, 170, 140, 175, 5, 10),
        shoulder_position=PhaseThresholds(0, 10, -5, 15, 5, 15),
        bar_drift=PhaseThresholds(0, 5, 0, 8, 5, 15),
    ),
    4: PhaseConfig(
        back_angle=PhaseThresholds(80, 90, 75, 90, 5, 20),
        thigh_angle=PhaseThresholds(80, 90, 75, 90, 5, 15),
        hip_angle=PhaseThresholds(165, 180, 155, 180, 5, 20),
        knee_angle=PhaseThresholds(170, 180, 160, 180, 5, 15),
        shoulder_position=PhaseThresholds(5, 15, 0, 20, 5, 15),
        bar_drift=PhaseThresholds(0, 5, 0, 8, 5, 15),
    ),
}

# Wrist-to-leg threshold as a ratio of upper arm (shoulder-to-elbow) length
# If distance < upper_arm * threshold: ideal (no deduction)
# If distance >= upper_arm * threshold: deduct points proportionally
WRIST_TO_LEG_THRESHOLD = 0.5  # Half the upper arm length


@dataclass
class FrameMetrics:
    """All calculated metrics for a single frame."""
    frame: int
    phase: int
    back_angle: Optional[float]
    thigh_angle: Optional[float]
    hip_angle: Optional[float]
    knee_angle: Optional[float]
    shoulder_position: Optional[float]
    bar_drift: Optional[float]
    wrist_to_leg: Optional[float]  # Raw distance
    upper_arm_length: Optional[float]  # Shoulder-to-elbow distance for reference


@dataclass
class PhaseResult:
    """Analysis result for a single phase."""
    phase: int
    frame_range: tuple[int, int]
    metrics: dict[str, dict]  # metric_name -> {avg, min, max, status}
    deductions: int
    issues: list[dict]


class DeadliftAnalyzer(BaseAnalyzer):
    """
    Analyze deadlift form from pose landmarks using phase-based analysis.

    Divides the lift into 4 phases based on bar (wrist) vertical position:
    - Phase 1 (0-25%): Floor to quarter height
    - Phase 2 (25-50%): Quarter to halfway
    - Phase 3 (50-75%): Halfway to three-quarters
    - Phase 4 (75-100%): Three-quarters to lockout

    Metrics checked per phase:
    1. Back angle (from horizontal) - torso inclination
    2. Thigh angle (from horizontal) - leg inclination
    3. Hip angle (joint angle) - hip flexion
    4. Knee angle (joint angle) - knee flexion
    5. Shoulder position - relative to bar
    6. Bar drift - horizontal deviation
    7. Wrist-to-leg distance - bar proximity to legs
    """

    def analyze(
        self,
        landmarks_per_frame: list[Optional[dict[int, dict]]],
        camera_side: Literal["left", "right"],
    ) -> dict:
        side = self.get_side_indices(camera_side)

        # Track bar path and detect phases
        bar_path = self.track_bar_path(landmarks_per_frame)
        if not bar_path:
            return self._empty_result()

        # Detect first rep and get phase boundaries
        first_rep_frames = self._detect_first_rep(bar_path)
        if not first_rep_frames:
            return self._empty_result()

        phase_boundaries = self._calculate_phase_boundaries(bar_path, first_rep_frames)

        # Calculate metrics for each frame in first rep
        frame_metrics = self._calculate_all_frame_metrics(
            landmarks_per_frame, side, bar_path, first_rep_frames, phase_boundaries
        )

        # Analyze each phase
        phase_results = self._analyze_phases(frame_metrics, phase_boundaries)

        # Aggregate results
        total_deductions = sum(pr.deductions for pr in phase_results)
        all_issues = []
        for pr in phase_results:
            all_issues.extend(pr.issues)

        technique_score = max(0, min(100, 100 - total_deductions))

        # Build component scores from phase metrics
        component_scores = self._build_component_scores(phase_results)

        # Build phase data for response
        phase_data = [
            {
                "phase": pr.phase,
                "frame_range": list(pr.frame_range),
                "metrics": pr.metrics,
                "deductions": pr.deductions,
            }
            for pr in phase_results
        ]

        # Build phase boundaries for frontend visualization (Y-coordinates for horizontal lines)
        # Each boundary is the Y-position where one phase ends and the next begins
        phase_boundaries_list = []
        for phase in range(1, 4):  # 3 boundaries between 4 phases
            if phase in phase_boundaries:
                # The top of this phase is the boundary line
                boundary_y = phase_boundaries[phase][0]  # min_y (top of phase)
                phase_boundaries_list.append({
                    "y": boundary_y,
                    "between_phases": [phase, phase + 1],
                })

        return {
            "technique_score": technique_score,
            "issues": all_issues,
            "bar_path": bar_path,
            "component_scores": component_scores,
            "phase_data": phase_data,
            "phase_boundaries": phase_boundaries_list,
        }

    def _empty_result(self) -> dict:
        """Return an empty result when analysis can't be performed."""
        return {
            "technique_score": 0,
            "issues": [{
                "issue": "insufficient_data",
                "severity": "major",
                "description": "Could not detect enough pose data for analysis.",
            }],
            "bar_path": [],
            "component_scores": {
                "back_angle": 0,
                "hip_angle": 0,
                "knee_angle": 0,
                "bar_path": 0,
            },
            "phase_data": [],
            "phase_boundaries": [],
        }

    def _detect_first_rep(self, bar_path: list[dict]) -> Optional[tuple[int, int]]:
        """
        Detect the first rep by finding when the bar reaches its highest point.

        Returns (start_frame, end_frame) for the first rep, or None if no rep detected.

        In normalized coordinates, lower Y = higher on screen, so we look for minimum Y.
        """
        if len(bar_path) < 5:
            return None

        # Find the frame with minimum Y (highest point = lockout)
        min_y = float("inf")
        lockout_idx = 0

        for i, point in enumerate(bar_path):
            if point["y"] < min_y:
                min_y = point["y"]
                lockout_idx = i

        # Start frame is the first frame
        start_frame = bar_path[0]["frame"]

        # End frame is the lockout frame
        end_frame = bar_path[lockout_idx]["frame"]

        # Require meaningful vertical travel (at least 15% of frame height)
        start_y = bar_path[0]["y"]
        vertical_travel = start_y - min_y

        if vertical_travel < 0.15:
            return None

        return (start_frame, end_frame)

    def _calculate_phase_boundaries(
        self,
        bar_path: list[dict],
        first_rep_frames: tuple[int, int],
    ) -> dict[int, tuple[float, float]]:
        """
        Calculate Y-coordinate boundaries for each phase.

        Returns dict mapping phase number (1-4) to (min_y, max_y) ranges.
        Note: lower Y = higher position.
        """
        start_frame, end_frame = first_rep_frames

        # Find start and end Y positions within first rep
        start_y = None
        end_y = None

        for point in bar_path:
            if point["frame"] == start_frame:
                start_y = point["y"]
            if point["frame"] == end_frame:
                end_y = point["y"]

        if start_y is None or end_y is None:
            # Fallback to first/last points
            start_y = bar_path[0]["y"]
            end_y = min(p["y"] for p in bar_path)

        # Calculate phase boundaries (quarters of vertical range)
        total_range = start_y - end_y  # Positive since start_y > end_y

        boundaries = {}
        for phase in range(1, 5):
            # Phase 1: start_y to 75% up
            # Phase 2: 75% to 50% up
            # Phase 3: 50% to 25% up
            # Phase 4: 25% to end_y (lockout)
            phase_bottom = start_y - ((phase - 1) / 4) * total_range
            phase_top = start_y - (phase / 4) * total_range
            boundaries[phase] = (phase_top, phase_bottom)  # (min_y, max_y)

        return boundaries

    def _get_phase_for_y(
        self,
        y: float,
        phase_boundaries: dict[int, tuple[float, float]],
    ) -> int:
        """Determine which phase a Y coordinate falls into."""
        for phase, (min_y, max_y) in phase_boundaries.items():
            if min_y <= y <= max_y:
                return phase

        # Fallback: return closest phase
        if y > phase_boundaries[1][1]:
            return 1
        return 4

    def _calculate_all_frame_metrics(
        self,
        landmarks_per_frame: list[Optional[dict[int, dict]]],
        side: dict[str, int],
        bar_path: list[dict],
        first_rep_frames: tuple[int, int],
        phase_boundaries: dict[int, tuple[float, float]],
    ) -> list[FrameMetrics]:
        """Calculate all metrics for each frame in the first rep."""
        start_frame, end_frame = first_rep_frames

        # Create a lookup for bar path by frame
        bar_by_frame = {p["frame"]: p for p in bar_path}

        # Get start X for drift calculation
        start_x = bar_path[0]["x"]

        frame_metrics = []

        for frame_idx in range(start_frame, end_frame + 1):
            if frame_idx >= len(landmarks_per_frame):
                continue

            frame = landmarks_per_frame[frame_idx]
            if frame is None:
                continue

            bar_point = bar_by_frame.get(frame_idx)
            if bar_point is None:
                continue

            # Determine phase
            phase = self._get_phase_for_y(bar_point["y"], phase_boundaries)

            # Get landmarks
            shoulder = PoseEstimator.get_landmark(frame, side["shoulder"])
            hip = PoseEstimator.get_landmark(frame, side["hip"])
            knee = PoseEstimator.get_landmark(frame, side["knee"])
            ankle = PoseEstimator.get_landmark(frame, side["ankle"])
            wrist = PoseEstimator.get_landmark(frame, side["wrist"])

            # Also get opposite side for body width calculation
            left_shoulder = PoseEstimator.get_landmark(frame, self.LEFT_SHOULDER)
            right_shoulder = PoseEstimator.get_landmark(frame, self.RIGHT_SHOULDER)
            left_hip = PoseEstimator.get_landmark(frame, self.LEFT_HIP)
            right_hip = PoseEstimator.get_landmark(frame, self.RIGHT_HIP)

            # Calculate body width if possible
            body_width = 0.0
            if all(PoseEstimator.is_visible(p) for p in [left_shoulder, right_shoulder, left_hip, right_hip]):
                body_width = calculate_body_width(left_shoulder, right_shoulder, left_hip, right_hip)

            # Get elbow for upper arm length calculation
            elbow = PoseEstimator.get_landmark(frame, side["elbow"])

            # Calculate metrics
            metrics = FrameMetrics(
                frame=frame_idx,
                phase=phase,
                back_angle=None,
                thigh_angle=None,
                hip_angle=None,
                knee_angle=None,
                shoulder_position=None,
                bar_drift=None,
                wrist_to_leg=None,
                upper_arm_length=None,
            )

            # Upper arm length (shoulder to elbow) - used as reference for wrist-to-leg
            if PoseEstimator.is_visible(shoulder) and PoseEstimator.is_visible(elbow):
                metrics.upper_arm_length = calculate_distance(shoulder, elbow)

            # Back angle (from horizontal)
            if PoseEstimator.is_visible(hip) and PoseEstimator.is_visible(shoulder):
                metrics.back_angle = calculate_angle_from_horizontal(hip, shoulder)

            # Thigh angle (from horizontal)
            if PoseEstimator.is_visible(hip) and PoseEstimator.is_visible(knee):
                metrics.thigh_angle = calculate_angle_from_horizontal(hip, knee)

            # Hip angle (joint angle: shoulder-hip-knee)
            if all(PoseEstimator.is_visible(p) for p in [shoulder, hip, knee]):
                metrics.hip_angle = calculate_angle(shoulder, hip, knee)

            # Knee angle (joint angle: hip-knee-ankle)
            if all(PoseEstimator.is_visible(p) for p in [hip, knee, ankle]):
                metrics.knee_angle = calculate_knee_angle(hip, knee, ankle)

            # Shoulder position relative to bar
            if PoseEstimator.is_visible(shoulder) and PoseEstimator.is_visible(wrist) and body_width > 0:
                metrics.shoulder_position = calculate_shoulder_bar_position(shoulder, wrist, body_width)

            # Bar drift from start position
            if body_width > 0:
                drift = abs(bar_point["x"] - start_x)
                metrics.bar_drift = (drift / body_width) * 100

            # Wrist-to-leg distance (raw distance, compared against upper arm length)
            if PoseEstimator.is_visible(wrist):
                if phase <= 2:
                    # Lower phases: distance to shin
                    if PoseEstimator.is_visible(ankle) and PoseEstimator.is_visible(knee):
                        metrics.wrist_to_leg = calculate_wrist_to_leg_distance(
                            wrist, knee, ankle
                        )
                else:
                    # Upper phases: distance to thigh
                    if PoseEstimator.is_visible(knee) and PoseEstimator.is_visible(hip):
                        metrics.wrist_to_leg = calculate_wrist_to_leg_distance(
                            wrist, hip, knee
                        )

            frame_metrics.append(metrics)

        return frame_metrics

    def _analyze_phases(
        self,
        frame_metrics: list[FrameMetrics],
        phase_boundaries: dict[int, tuple[float, float]],
    ) -> list[PhaseResult]:
        """Analyze each phase and calculate deductions."""
        results = []

        for phase in range(1, 5):
            phase_frames = [fm for fm in frame_metrics if fm.phase == phase]

            if not phase_frames:
                continue

            frame_range = (
                min(fm.frame for fm in phase_frames),
                max(fm.frame for fm in phase_frames),
            )

            # Get thresholds for this phase
            thresholds = PHASE_THRESHOLDS[phase]

            # Calculate metrics statistics and check thresholds
            metrics_result = {}
            total_deductions = 0
            issues = []

            # Check standard metrics (with PhaseThresholds)
            metric_checks = [
                ("back_angle", [fm.back_angle for fm in phase_frames], thresholds.back_angle, "Back angle"),
                ("thigh_angle", [fm.thigh_angle for fm in phase_frames], thresholds.thigh_angle, "Thigh angle"),
                ("hip_angle", [fm.hip_angle for fm in phase_frames], thresholds.hip_angle, "Hip angle"),
                ("knee_angle", [fm.knee_angle for fm in phase_frames], thresholds.knee_angle, "Knee angle"),
                ("shoulder_position", [fm.shoulder_position for fm in phase_frames], thresholds.shoulder_position, "Shoulder position"),
                ("bar_drift", [fm.bar_drift for fm in phase_frames], thresholds.bar_drift, "Bar drift"),
            ]

            for metric_name, values, thresh, display_name in metric_checks:
                valid_values = [v for v in values if v is not None]

                if not valid_values:
                    metrics_result[metric_name] = {
                        "avg": None,
                        "min": None,
                        "max": None,
                        "status": "no_data",
                    }
                    continue

                avg_val = sum(valid_values) / len(valid_values)
                min_val = min(valid_values)
                max_val = max(valid_values)

                # Determine status and deductions
                status = "ideal"
                deduction = 0

                # For most metrics, check the average value
                check_val = avg_val

                # Check if in ideal range
                if thresh.ideal_min <= check_val <= thresh.ideal_max:
                    status = "ideal"
                elif thresh.minor_min <= check_val <= thresh.minor_max:
                    status = "minor"
                    deduction = thresh.minor_penalty
                else:
                    status = "major"
                    deduction = thresh.major_penalty

                metrics_result[metric_name] = {
                    "avg": round(avg_val, 1),
                    "min": round(min_val, 1),
                    "max": round(max_val, 1),
                    "status": status,
                }

                if deduction > 0:
                    total_deductions += deduction

                    # Generate issue
                    issue = self._generate_issue(
                        metric_name, display_name, phase, avg_val, thresh, status, frame_range
                    )
                    if issue:
                        issues.append(issue)

            # Handle wrist_to_leg separately (uses upper arm length threshold)
            wrist_to_leg_result = self._analyze_wrist_to_leg(phase_frames, phase, frame_range)
            metrics_result["wrist_to_leg"] = wrist_to_leg_result["metrics"]
            total_deductions += wrist_to_leg_result["deduction"]
            if wrist_to_leg_result["issue"]:
                issues.append(wrist_to_leg_result["issue"])

            results.append(PhaseResult(
                phase=phase,
                frame_range=frame_range,
                metrics=metrics_result,
                deductions=total_deductions,
                issues=issues,
            ))

        return results

    def _analyze_wrist_to_leg(
        self,
        phase_frames: list[FrameMetrics],
        phase: int,
        frame_range: tuple[int, int],
    ) -> dict:
        """
        Analyze wrist-to-leg distance using upper arm length as reference.

        Good: distance < (upper_arm_length * 0.5)
        Deductions increase the further beyond the threshold.
        """
        # Get valid pairs of wrist_to_leg and upper_arm_length
        valid_pairs = [
            (fm.wrist_to_leg, fm.upper_arm_length)
            for fm in phase_frames
            if fm.wrist_to_leg is not None and fm.upper_arm_length is not None and fm.upper_arm_length > 0
        ]

        if not valid_pairs:
            return {
                "metrics": {
                    "avg": None,
                    "min": None,
                    "max": None,
                    "ratio": None,
                    "status": "no_data",
                },
                "deduction": 0,
                "issue": None,
            }

        # Calculate ratio of wrist-to-leg distance to upper arm length
        ratios = [wtl / ual for wtl, ual in valid_pairs]
        avg_ratio = sum(ratios) / len(ratios)

        # Also calculate raw distance stats for display
        distances = [p[0] for p in valid_pairs]
        avg_dist = sum(distances) / len(distances)
        min_dist = min(distances)
        max_dist = max(distances)

        # Determine status and deduction based on ratio
        threshold = WRIST_TO_LEG_THRESHOLD  # 0.5

        if avg_ratio <= threshold:
            status = "ideal"
            deduction = 0
        elif avg_ratio <= threshold * 1.5:  # Up to 0.75 of upper arm
            status = "minor"
            # Deduct 5-10 points based on how far over threshold
            overage = (avg_ratio - threshold) / (threshold * 0.5)  # 0 to 1
            deduction = 5 + int(overage * 5)
        else:
            status = "major"
            # Deduct 10-20 points based on how far over threshold
            overage = min(1.0, (avg_ratio - threshold * 1.5) / threshold)  # 0 to 1
            deduction = 10 + int(overage * 10)

        # Generate issue if not ideal
        issue = None
        if status != "ideal":
            ratio_pct = avg_ratio * 100
            severity = "minor" if status == "minor" else "moderate"
            issue = {
                "issue": f"wrist_to_leg_too_far_phase{phase}",
                "severity": severity,
                "description": f"Bar too far from legs in phase {phase} ({ratio_pct:.0f}% of upper arm length, should be <{threshold*100:.0f}%). Keep bar closer to body.",
                "frames": list(range(frame_range[0], frame_range[1] + 1)),
            }

        return {
            "metrics": {
                "avg": round(avg_dist * 100, 1),  # Convert to percentage for display
                "min": round(min_dist * 100, 1),
                "max": round(max_dist * 100, 1),
                "ratio": round(avg_ratio, 2),
                "status": status,
            },
            "deduction": deduction,
            "issue": issue,
        }

    def _generate_issue(
        self,
        metric_name: str,
        display_name: str,
        phase: int,
        value: float,
        thresh: PhaseThresholds,
        status: str,
        frame_range: tuple[int, int],
    ) -> Optional[dict]:
        """Generate an issue description based on metric violation."""
        severity = "minor" if status == "minor" else "moderate"
        if metric_name in ["back_angle", "hip_angle"] and status == "major":
            severity = "major"

        # Determine direction of violation
        if value < thresh.ideal_min:
            direction = "too_low"
        else:
            direction = "too_high"

        descriptions = {
            "back_angle": {
                "too_low": f"Back angle too horizontal ({value:.0f}°) in phase {phase}. Maintain more upright torso.",
                "too_high": f"Back angle too upright ({value:.0f}°) in phase {phase}. May indicate early hip rise.",
            },
            "thigh_angle": {
                "too_low": f"Thighs too horizontal ({value:.0f}°) in phase {phase}. Hips may be too low.",
                "too_high": f"Thighs too vertical ({value:.0f}°) in phase {phase}. Hips may be rising too fast.",
            },
            "hip_angle": {
                "too_low": f"Hip angle too closed ({value:.0f}°) in phase {phase}. Hip mobility may be limited.",
                "too_high": f"Hip angle too open ({value:.0f}°) in phase {phase}. Lockout position may be reached early.",
            },
            "knee_angle": {
                "too_low": f"Knees too bent ({value:.0f}°) in phase {phase}. Straighten legs earlier.",
                "too_high": f"Knees straightening too early ({value:.0f}°) in phase {phase}. May cause stiff-legged pull.",
            },
            "shoulder_position": {
                "too_low": f"Shoulders too far in front of bar ({value:.0f}%) in phase {phase}. Pull back over the bar.",
                "too_high": f"Shoulders too far behind bar ({value:.0f}%) in phase {phase}. Maintain position over bar longer.",
            },
            "bar_drift": {
                "too_low": "",  # Bar drift can't be too low
                "too_high": f"Excessive bar drift ({value:.0f}%) in phase {phase}. Keep bar closer to body.",
            },
        }

        desc = descriptions.get(metric_name, {}).get(direction, "")
        if not desc:
            return None

        return {
            "issue": f"{metric_name}_{direction}_phase{phase}",
            "severity": severity,
            "description": desc,
            "frames": list(range(frame_range[0], frame_range[1] + 1)),
        }

    def _build_component_scores(self, phase_results: list[PhaseResult]) -> dict:
        """Build component scores from phase results."""
        scores = {
            "back_angle": 100,
            "hip_angle": 100,
            "knee_angle": 100,
            "bar_path": 100,
            "thigh_angle": 100,
            "shoulder_position": 100,
            "wrist_to_leg": 100,
        }

        for pr in phase_results:
            for metric_name, metric_data in pr.metrics.items():
                if metric_data["status"] == "minor":
                    scores[metric_name] = min(scores.get(metric_name, 100), 85)
                elif metric_data["status"] == "major":
                    scores[metric_name] = min(scores.get(metric_name, 100), 60)

            # Bar drift contributes to bar_path score
            if "bar_drift" in pr.metrics:
                if pr.metrics["bar_drift"]["status"] == "minor":
                    scores["bar_path"] = min(scores["bar_path"], 85)
                elif pr.metrics["bar_drift"]["status"] == "major":
                    scores["bar_path"] = min(scores["bar_path"], 60)

        return scores
