import pytest
from unittest.mock import patch, MagicMock
from src.core.pose_estimator import (
    PoseEstimator,
    OneEuroFilter,
    COCO_TO_MEDIAPIPE,
    REQUIRED_MEDIAPIPE_INDICES,
)


class TestPoseEstimator:
    def test_get_landmark_returns_none_for_missing(self):
        frame = {0: {"x": 0.5, "y": 0.5, "z": 0, "visibility": 1.0}}

        result = PoseEstimator.get_landmark(frame, 99)

        assert result is None

    def test_get_landmark_returns_value(self):
        frame = {0: {"x": 0.5, "y": 0.5, "z": 0, "visibility": 1.0}}

        result = PoseEstimator.get_landmark(frame, 0)

        assert result == {"x": 0.5, "y": 0.5, "z": 0, "visibility": 1.0}

    def test_get_landmark_handles_none_frame(self):
        result = PoseEstimator.get_landmark(None, 0)

        assert result is None

    def test_midpoint_calculation(self):
        p1 = {"x": 0.0, "y": 0.0, "z": 0.0}
        p2 = {"x": 1.0, "y": 1.0, "z": 1.0}

        result = PoseEstimator.midpoint(p1, p2)

        assert result["x"] == 0.5
        assert result["y"] == 0.5
        assert result["z"] == 0.5

    def test_is_visible_above_threshold(self):
        landmark = {"x": 0.5, "y": 0.5, "z": 0, "visibility": 0.9}

        assert PoseEstimator.is_visible(landmark) is True

    def test_is_visible_below_threshold(self):
        landmark = {"x": 0.5, "y": 0.5, "z": 0, "visibility": 0.3}

        assert PoseEstimator.is_visible(landmark) is False

    def test_is_visible_none(self):
        assert PoseEstimator.is_visible(None) is False


class TestCocoToMediaPipeMapping:
    def test_mapping_covers_all_required_indices(self):
        """All required MediaPipe landmarks are mapped from COCO."""
        mapped_mediapipe_indices = set(COCO_TO_MEDIAPIPE.values())

        assert REQUIRED_MEDIAPIPE_INDICES.issubset(mapped_mediapipe_indices)

    def test_mapping_has_correct_body_parts(self):
        """Verify specific body part mappings."""
        # Shoulders: COCO 5,6 -> MediaPipe 11,12
        assert COCO_TO_MEDIAPIPE[5] == 11
        assert COCO_TO_MEDIAPIPE[6] == 12

        # Elbows: COCO 7,8 -> MediaPipe 13,14
        assert COCO_TO_MEDIAPIPE[7] == 13
        assert COCO_TO_MEDIAPIPE[8] == 14

        # Wrists: COCO 9,10 -> MediaPipe 15,16
        assert COCO_TO_MEDIAPIPE[9] == 15
        assert COCO_TO_MEDIAPIPE[10] == 16

        # Hips: COCO 11,12 -> MediaPipe 23,24
        assert COCO_TO_MEDIAPIPE[11] == 23
        assert COCO_TO_MEDIAPIPE[12] == 24

        # Knees: COCO 13,14 -> MediaPipe 25,26
        assert COCO_TO_MEDIAPIPE[13] == 25
        assert COCO_TO_MEDIAPIPE[14] == 26

        # Ankles: COCO 15,16 -> MediaPipe 27,28
        assert COCO_TO_MEDIAPIPE[15] == 27
        assert COCO_TO_MEDIAPIPE[16] == 28


@pytest.fixture
def mock_pose_estimator():
    """Create a PoseEstimator with mocked model loading."""
    with patch("src.core.pose_estimator.ensure_model_downloaded"):
        with patch("src.core.pose_estimator.ort.InferenceSession") as mock_session:
            mock_session.return_value.get_inputs.return_value = [
                MagicMock(name="input")
            ]
            estimator = PoseEstimator()
            yield estimator


class TestOutputFormat:
    def test_convert_to_mediapipe_format_structure(self, mock_pose_estimator):
        """Output format has correct structure with x, y, z, visibility keys."""
        # Simulate COCO keypoints (17 points)
        keypoints = [(0.5, 0.5, 0.9)] * 17

        result = mock_pose_estimator._convert_to_mediapipe_format(keypoints)

        # Check all required indices are present
        for idx in REQUIRED_MEDIAPIPE_INDICES:
            assert idx in result
            assert "x" in result[idx]
            assert "y" in result[idx]
            assert "z" in result[idx]
            assert "visibility" in result[idx]

    def test_convert_to_mediapipe_format_values(self, mock_pose_estimator):
        """Values are correctly transferred from COCO to MediaPipe format."""
        # Different values for each keypoint
        keypoints = [(i * 0.05, i * 0.05 + 0.1, 0.8 + i * 0.01) for i in range(17)]

        result = mock_pose_estimator._convert_to_mediapipe_format(keypoints)

        # Check left shoulder (COCO 5 -> MediaPipe 11)
        assert result[11]["x"] == pytest.approx(5 * 0.05)
        assert result[11]["y"] == pytest.approx(5 * 0.05 + 0.1)
        assert result[11]["visibility"] == pytest.approx(0.8 + 5 * 0.01)

        # Check left hip (COCO 11 -> MediaPipe 23)
        assert result[23]["x"] == pytest.approx(11 * 0.05)
        assert result[23]["y"] == pytest.approx(11 * 0.05 + 0.1)

    def test_z_coordinate_is_zero(self, mock_pose_estimator):
        """Z coordinate is set to 0.0 since COCO doesn't provide depth."""
        keypoints = [(0.5, 0.5, 0.9)] * 17

        result = mock_pose_estimator._convert_to_mediapipe_format(keypoints)

        for idx in REQUIRED_MEDIAPIPE_INDICES:
            assert result[idx]["z"] == 0.0


class TestOneEuroFilter:
    def test_first_sample_returns_input(self):
        """First sample should return unchanged."""
        f = OneEuroFilter()

        result = f(0.5, 0.0)

        assert result == 0.5

    def test_smoothing_reduces_jitter(self):
        """Filter should reduce variance of noisy input."""
        f = OneEuroFilter(min_cutoff=0.5, beta=0.007)

        # Simulate jittery input around 0.5
        noisy_values = [0.5, 0.52, 0.48, 0.51, 0.49, 0.50, 0.52, 0.48, 0.51, 0.49]
        filtered_values = []

        for i, val in enumerate(noisy_values):
            filtered_values.append(f(val, i * 0.033))  # ~30fps

        # Calculate variance
        noisy_variance = sum((v - 0.5) ** 2 for v in noisy_values) / len(noisy_values)
        filtered_variance = sum((v - 0.5) ** 2 for v in filtered_values) / len(
            filtered_values
        )

        assert filtered_variance < noisy_variance

    def test_tracks_movement_direction(self):
        """Filter should follow movement direction."""
        f = OneEuroFilter(min_cutoff=0.5, beta=0.5)  # Higher beta for faster tracking

        # Movement from 0 to 1
        values = [0.0, 0.25, 0.5, 0.75, 1.0]
        filtered = []

        for i, val in enumerate(values):
            filtered.append(f(val, i * 0.033))

        # Filtered values should be increasing
        for i in range(1, len(filtered)):
            assert filtered[i] >= filtered[i - 1]

        # Final value should be reasonably close to target
        assert filtered[-1] > 0.6

    def test_reset_clears_state(self):
        """Reset should clear filter state."""
        f = OneEuroFilter()

        # Process some values
        f(0.5, 0.0)
        f(0.6, 0.033)
        f(0.7, 0.066)

        # Reset
        f.reset()

        # Next value should be returned unchanged
        result = f(0.3, 0.0)
        assert result == 0.3

    def test_handles_same_timestamp(self):
        """Filter should handle duplicate timestamps gracefully."""
        f = OneEuroFilter()

        f(0.5, 0.0)
        result = f(0.6, 0.0)  # Same timestamp

        # Should return previous value when dt=0
        assert result == 0.5


class TestTemporalSmoothing:
    def test_smoothing_enabled_by_default(self, mock_pose_estimator):
        """Temporal smoothing should be enabled by default."""
        assert mock_pose_estimator.use_temporal_smoothing is True

    def test_smoothing_can_be_disabled(self):
        """Temporal smoothing can be disabled."""
        with patch("src.core.pose_estimator.ensure_model_downloaded"):
            with patch("src.core.pose_estimator.ort.InferenceSession") as mock_session:
                mock_session.return_value.get_inputs.return_value = [
                    MagicMock(name="input")
                ]
                estimator = PoseEstimator(use_temporal_smoothing=False)

                assert estimator.use_temporal_smoothing is False

    def test_filters_initialized_empty(self, mock_pose_estimator):
        """Filters dict should be empty on init."""
        assert len(mock_pose_estimator._filters) == 0

    def test_apply_temporal_smoothing_creates_filters(self, mock_pose_estimator):
        """Applying smoothing should create filters for each keypoint."""
        keypoints = [(0.5, 0.5, 0.9)] * 17

        mock_pose_estimator._apply_temporal_smoothing(keypoints, 0.0)

        # Should have 2 filters per keypoint (x and y)
        assert len(mock_pose_estimator._filters) == 17 * 2
