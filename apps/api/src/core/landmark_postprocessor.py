import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LandmarkPostProcessor:
    """Post-process landmarks to fix occlusion issues.

    During exercises like deadlifts, weights/plates can occlude body parts
    (especially ankles). MediaPipe returns inaccurate positions for occluded
    landmarks, causing them to "jump" when revealed.

    This processor identifies landmarks that should remain stationary during
    an exercise and uses high-confidence frames to establish "anchor points"
    that replace low-confidence positions.
    """

    # Landmarks that stay stationary during each exercise
    ANCHOR_LANDMARKS = {
        "deadlift": [27, 28],  # ankles - feet stay planted
        "squat": [27, 28],     # ankles - feet stay planted
        "bench": [27, 28],     # ankles - feet stay planted
    }

    # Landmarks that should be forced to anchor position in ALL frames
    # (not just low-visibility frames) because they truly don't move
    FORCE_ANCHOR_LANDMARKS = {
        "deadlift": [27, 28],  # ankles never move in deadlift
        "squat": [],           # ankles may shift slightly in squat
        "bench": [27, 28],     # ankles don't move in bench
    }

    def process(
        self,
        landmarks_per_frame: list[Optional[dict[int, dict]]],
        exercise_type: str,
        visibility_threshold: float = 0.7,
    ) -> list[Optional[dict[int, dict]]]:
        """Apply anchor point correction to landmarks.

        Args:
            landmarks_per_frame: List of frame landmark dicts from PoseEstimator
            exercise_type: Type of exercise (deadlift, squat, bench)
            visibility_threshold: Minimum visibility to trust a landmark position

        Returns:
            Processed landmarks with anchor corrections applied
        """
        anchor_indices = self.ANCHOR_LANDMARKS.get(exercise_type, [])
        if not anchor_indices:
            logger.info(f"No anchor landmarks defined for exercise: {exercise_type}")
            return landmarks_per_frame

        # Log visibility stats for debugging
        self._log_visibility_stats(landmarks_per_frame, anchor_indices)

        # Find anchor positions from high-confidence frames
        anchors = self._find_anchor_positions(
            landmarks_per_frame,
            anchor_indices,
            visibility_threshold,
        )

        # If no anchors found, return original
        if not anchors:
            logger.warning(f"No high-confidence frames found for anchors (threshold={visibility_threshold})")
            return landmarks_per_frame

        logger.info(f"Found anchors for landmarks: {list(anchors.keys())}")

        # Get landmarks that should be forced to anchor in all frames
        force_anchor_indices = set(self.FORCE_ANCHOR_LANDMARKS.get(exercise_type, []))

        # Apply anchors to low-confidence frames (or all frames for forced anchors)
        result, correction_count = self._apply_anchors(
            landmarks_per_frame,
            anchors,
            visibility_threshold,
            force_anchor_indices,
        )

        logger.info(f"Applied {correction_count} corrections across {len(landmarks_per_frame)} frames")
        return result

    def _log_visibility_stats(
        self,
        landmarks_per_frame: list[Optional[dict[int, dict]]],
        anchor_indices: list[int],
    ) -> None:
        """Log visibility statistics for anchor landmarks."""
        for idx in anchor_indices:
            visibilities = []
            for frame in landmarks_per_frame:
                if frame is None:
                    continue
                landmark = frame.get(idx)
                if landmark:
                    visibilities.append(landmark.get("visibility", 0))

            if visibilities:
                min_vis = min(visibilities)
                max_vis = max(visibilities)
                avg_vis = sum(visibilities) / len(visibilities)
                logger.info(
                    f"Landmark {idx} visibility: min={min_vis:.3f}, max={max_vis:.3f}, "
                    f"avg={avg_vis:.3f}, frames={len(visibilities)}"
                )

    def _find_anchor_positions(
        self,
        landmarks_per_frame: list[Optional[dict[int, dict]]],
        anchor_indices: list[int],
        threshold: float,
    ) -> dict[int, dict]:
        """Find average position of anchors from high-visibility frames.

        Args:
            landmarks_per_frame: List of frame landmark dicts
            anchor_indices: Landmark indices to find anchors for
            threshold: Minimum visibility to include in average

        Returns:
            Dict mapping landmark index to averaged anchor position {x, y}
        """
        anchors = {}

        for idx in anchor_indices:
            positions = []

            for frame in landmarks_per_frame:
                if frame is None:
                    continue

                landmark = frame.get(idx)
                if landmark and landmark.get("visibility", 0) >= threshold:
                    positions.append((landmark["x"], landmark["y"]))

            if positions:
                # Average the high-confidence positions
                avg_x = sum(p[0] for p in positions) / len(positions)
                avg_y = sum(p[1] for p in positions) / len(positions)
                anchors[idx] = {"x": avg_x, "y": avg_y}
                logger.info(
                    f"Landmark {idx} anchor: x={avg_x:.3f}, y={avg_y:.3f} "
                    f"(from {len(positions)} high-confidence frames)"
                )

        return anchors

    def _apply_anchors(
        self,
        landmarks_per_frame: list[Optional[dict[int, dict]]],
        anchors: dict[int, dict],
        threshold: float,
        force_anchor_indices: set[int] = None,
    ) -> tuple[list[Optional[dict[int, dict]]], int]:
        """Replace low-visibility landmarks with anchor positions.

        Args:
            landmarks_per_frame: List of frame landmark dicts
            anchors: Dict of anchor positions per landmark index
            threshold: Visibility below which to apply anchor correction
            force_anchor_indices: Landmark indices to always replace with anchor

        Returns:
            Tuple of (processed landmarks, number of corrections made)
        """
        if force_anchor_indices is None:
            force_anchor_indices = set()

        processed = []
        correction_count = 0

        for frame in landmarks_per_frame:
            if frame is None:
                processed.append(None)
                continue

            # Create a shallow copy of the frame dict
            new_frame = dict(frame)

            for idx, anchor_pos in anchors.items():
                landmark = new_frame.get(idx)
                if not landmark:
                    continue

                # Apply anchor if: low visibility OR forced anchor landmark
                should_correct = (
                    landmark.get("visibility", 0) < threshold
                    or idx in force_anchor_indices
                )

                if should_correct:
                    new_frame[idx] = {
                        "x": anchor_pos["x"],
                        "y": anchor_pos["y"],
                        "z": landmark.get("z", 0),
                        "visibility": max(threshold, landmark.get("visibility", 0)),
                        "corrected": True,
                    }
                    correction_count += 1

            processed.append(new_frame)

        return processed, correction_count
