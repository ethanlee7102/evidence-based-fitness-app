import pytest
from src.core.landmark_postprocessor import LandmarkPostProcessor


class TestLandmarkPostProcessor:
    def setup_method(self):
        self.processor = LandmarkPostProcessor()

    def test_process_returns_original_for_unknown_exercise(self):
        landmarks = [
            {27: {"x": 0.5, "y": 0.8, "z": 0, "visibility": 0.9}}
        ]

        result = self.processor.process(landmarks, "unknown_exercise")

        assert result == landmarks

    def test_process_returns_original_when_no_frames(self):
        result = self.processor.process([], "deadlift")

        assert result == []

    def test_process_handles_none_frames(self):
        landmarks = [None, None, None]

        result = self.processor.process(landmarks, "deadlift")

        assert result == [None, None, None]

    def test_find_anchor_positions_averages_high_confidence(self):
        landmarks = [
            {27: {"x": 0.4, "y": 0.8, "visibility": 0.9}},
            {27: {"x": 0.6, "y": 0.8, "visibility": 0.9}},
            {27: {"x": 0.5, "y": 0.2, "visibility": 0.3}},  # low confidence, ignored
        ]

        anchors = self.processor._find_anchor_positions(landmarks, [27], 0.7)

        assert 27 in anchors
        assert anchors[27]["x"] == 0.5  # average of 0.4 and 0.6
        assert anchors[27]["y"] == 0.8

    def test_find_anchor_positions_returns_empty_when_no_high_confidence(self):
        landmarks = [
            {27: {"x": 0.5, "y": 0.8, "visibility": 0.3}},
            {27: {"x": 0.5, "y": 0.8, "visibility": 0.4}},
        ]

        anchors = self.processor._find_anchor_positions(landmarks, [27], 0.7)

        assert anchors == {}

    def test_apply_anchors_replaces_low_confidence(self):
        landmarks = [
            {27: {"x": 0.5, "y": 0.8, "z": 0.1, "visibility": 0.3}},  # low confidence
        ]
        anchors = {27: {"x": 0.6, "y": 0.9}}

        result, count = self.processor._apply_anchors(landmarks, anchors, 0.7)

        assert result[0][27]["x"] == 0.6
        assert result[0][27]["y"] == 0.9
        assert result[0][27]["z"] == 0.1  # preserved
        assert result[0][27]["visibility"] == 0.7  # boosted to threshold
        assert result[0][27]["corrected"] is True
        assert count == 1

    def test_apply_anchors_preserves_high_confidence(self):
        landmarks = [
            {27: {"x": 0.5, "y": 0.8, "z": 0.1, "visibility": 0.9}},  # high confidence
        ]
        anchors = {27: {"x": 0.6, "y": 0.9}}

        result, count = self.processor._apply_anchors(landmarks, anchors, 0.7)

        assert result[0][27]["x"] == 0.5  # unchanged
        assert result[0][27]["y"] == 0.8  # unchanged
        assert "corrected" not in result[0][27]
        assert count == 0

    def test_full_process_deadlift_ankles(self):
        # Simulate a deadlift where ankles are visible at start/end but occluded mid-lift
        landmarks = [
            {27: {"x": 0.3, "y": 0.9, "z": 0, "visibility": 0.9},
             28: {"x": 0.7, "y": 0.9, "z": 0, "visibility": 0.9}},
            {27: {"x": 0.1, "y": 0.5, "z": 0, "visibility": 0.2},  # occluded, jumps
             28: {"x": 0.9, "y": 0.5, "z": 0, "visibility": 0.2}},
            {27: {"x": 0.3, "y": 0.9, "z": 0, "visibility": 0.9},
             28: {"x": 0.7, "y": 0.9, "z": 0, "visibility": 0.9}},
        ]

        result = self.processor.process(landmarks, "deadlift")

        # For deadlifts, ALL frames should be corrected to anchor position
        # because ankles are in FORCE_ANCHOR_LANDMARKS
        assert result[0][27]["x"] == 0.3
        assert result[0][27]["corrected"] is True  # even high-vis frames get anchored
        assert result[2][27]["x"] == 0.3
        assert result[2][27]["corrected"] is True

        # Frame 1 should also be corrected to anchor position
        assert result[1][27]["x"] == 0.3
        assert result[1][27]["y"] == 0.9
        assert result[1][27]["corrected"] is True
        assert result[1][28]["x"] == 0.7
        assert result[1][28]["corrected"] is True

    def test_does_not_modify_original_landmarks(self):
        original_landmarks = [
            {27: {"x": 0.5, "y": 0.8, "z": 0, "visibility": 0.3}},
        ]

        self.processor.process(original_landmarks, "deadlift")

        # Original should be unchanged
        assert original_landmarks[0][27]["x"] == 0.5
        assert "corrected" not in original_landmarks[0][27]
