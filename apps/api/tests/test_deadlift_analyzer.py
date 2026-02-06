import pytest
from src.core.analyzers.deadlift import DeadliftAnalyzer


class TestDeadliftAnalyzer:
    def test_analyze_returns_required_fields(self, deadlift_movement_frames):
        analyzer = DeadliftAnalyzer()

        result = analyzer.analyze(deadlift_movement_frames, "left")

        assert "technique_score" in result
        assert "issues" in result
        assert "bar_path" in result
        assert "component_scores" in result
        assert "phase_data" in result

    def test_score_in_valid_range(self, deadlift_movement_frames):
        analyzer = DeadliftAnalyzer()

        result = analyzer.analyze(deadlift_movement_frames, "left")

        assert 0 <= result["technique_score"] <= 100

    def test_handles_empty_frames(self):
        analyzer = DeadliftAnalyzer()

        result = analyzer.analyze([], "left")

        assert result["technique_score"] >= 0
        assert "insufficient_data" in result["issues"][0]["issue"]

    def test_handles_none_frames(self):
        analyzer = DeadliftAnalyzer()
        frames = [None] * 10

        result = analyzer.analyze(frames, "left")

        assert result["technique_score"] >= 0

    def test_bar_path_tracked(self, deadlift_movement_frames):
        analyzer = DeadliftAnalyzer()

        result = analyzer.analyze(deadlift_movement_frames, "left")

        assert len(result["bar_path"]) > 0
        assert "x" in result["bar_path"][0]
        assert "y" in result["bar_path"][0]
        assert "frame" in result["bar_path"][0]

    def test_phase_detection(self, deadlift_movement_frames):
        """Verify that the lift is correctly divided into 4 phases."""
        analyzer = DeadliftAnalyzer()

        result = analyzer.analyze(deadlift_movement_frames, "left")

        assert "phase_data" in result
        assert len(result["phase_data"]) == 4

        phases = [p["phase"] for p in result["phase_data"]]
        assert phases == [1, 2, 3, 4]

    def test_phase_frame_ranges_are_sequential(self, deadlift_movement_frames):
        """Verify that phase frame ranges don't overlap and cover the lift."""
        analyzer = DeadliftAnalyzer()

        result = analyzer.analyze(deadlift_movement_frames, "left")

        phase_data = result["phase_data"]
        if len(phase_data) < 2:
            pytest.skip("Not enough phases detected")

        for i in range(len(phase_data) - 1):
            current_end = phase_data[i]["frame_range"][1]
            next_start = phase_data[i + 1]["frame_range"][0]
            # Phases should be sequential (next starts at or after current ends)
            assert next_start >= current_end

    def test_phase_metrics_calculated(self, deadlift_movement_frames):
        """Verify that all 7 metrics are calculated for each phase."""
        analyzer = DeadliftAnalyzer()

        result = analyzer.analyze(deadlift_movement_frames, "left")

        expected_metrics = [
            "back_angle",
            "thigh_angle",
            "hip_angle",
            "knee_angle",
            "shoulder_position",
            "bar_drift",
            "wrist_to_leg",
        ]

        for phase_data in result["phase_data"]:
            for metric in expected_metrics:
                assert metric in phase_data["metrics"], f"Missing {metric} in phase {phase_data['phase']}"

    def test_component_scores_include_new_metrics(self, deadlift_movement_frames):
        """Verify that component scores include the new metrics."""
        analyzer = DeadliftAnalyzer()

        result = analyzer.analyze(deadlift_movement_frames, "left")

        expected_components = [
            "back_angle",
            "hip_angle",
            "knee_angle",
            "bar_path",
            "thigh_angle",
            "shoulder_position",
            "wrist_to_leg",
        ]

        for component in expected_components:
            assert component in result["component_scores"]
            assert 0 <= result["component_scores"][component] <= 100

    def test_issues_include_phase_context(self, deadlift_movement_frames):
        """If there are issues, they should include phase information."""
        analyzer = DeadliftAnalyzer()

        result = analyzer.analyze(deadlift_movement_frames, "left")

        # Skip if no issues
        if not result["issues"]:
            pytest.skip("No issues generated to test")

        for issue in result["issues"]:
            assert "issue" in issue
            assert "severity" in issue
            assert "description" in issue
            # Phase should be mentioned in issue name or description
            has_phase_context = (
                "phase" in issue["issue"].lower() or
                "phase" in issue["description"].lower()
            )
            assert has_phase_context, f"Issue missing phase context: {issue}"

    def test_first_rep_detection_stops_at_lockout(self):
        """Verify that analysis stops at lockout even if there are more frames."""
        analyzer = DeadliftAnalyzer()

        # Create frames that go up and then back down (multi-rep)
        frames = []
        for i in range(60):
            if i < 30:
                # Going up
                progress = i / 29
                wrist_y = 0.85 - (progress * 0.40)
            else:
                # Going back down (second rep start)
                progress = (i - 30) / 29
                wrist_y = 0.45 + (progress * 0.20)

            frame = {
                11: {"x": 0.45, "y": 0.40, "z": 0.0, "visibility": 0.9},
                12: {"x": 0.55, "y": 0.40, "z": 0.0, "visibility": 0.9},
                13: {"x": 0.40, "y": 0.50, "z": 0.0, "visibility": 0.9},
                14: {"x": 0.60, "y": 0.50, "z": 0.0, "visibility": 0.9},
                15: {"x": 0.45, "y": wrist_y, "z": 0.0, "visibility": 0.9},
                16: {"x": 0.55, "y": wrist_y, "z": 0.0, "visibility": 0.9},
                23: {"x": 0.47, "y": 0.60, "z": 0.0, "visibility": 0.9},
                24: {"x": 0.53, "y": 0.60, "z": 0.0, "visibility": 0.9},
                25: {"x": 0.47, "y": 0.75, "z": 0.0, "visibility": 0.9},
                26: {"x": 0.53, "y": 0.75, "z": 0.0, "visibility": 0.9},
                27: {"x": 0.47, "y": 0.95, "z": 0.0, "visibility": 0.9},
                28: {"x": 0.53, "y": 0.95, "z": 0.0, "visibility": 0.9},
            }
            frames.append(frame)

        result = analyzer.analyze(frames, "left")

        # Should only analyze first rep (roughly frames 0-29)
        if result["phase_data"]:
            max_frame = max(p["frame_range"][1] for p in result["phase_data"])
            # Max frame should be around lockout (frame 29-30), not 60
            assert max_frame < 40, f"Analysis extended beyond first rep: max_frame={max_frame}"

    def test_camera_side_right(self, deadlift_movement_frames):
        """Verify analysis works with right camera side."""
        analyzer = DeadliftAnalyzer()

        result = analyzer.analyze(deadlift_movement_frames, "right")

        assert result["technique_score"] >= 0
        assert "phase_data" in result

    def test_minimal_movement_not_detected_as_rep(self):
        """Frames with minimal vertical movement should not be detected as a rep."""
        analyzer = DeadliftAnalyzer()

        # Create frames with very little vertical wrist movement
        frames = []
        for i in range(20):
            frame = {
                11: {"x": 0.45, "y": 0.40, "z": 0.0, "visibility": 0.9},
                12: {"x": 0.55, "y": 0.40, "z": 0.0, "visibility": 0.9},
                13: {"x": 0.40, "y": 0.50, "z": 0.0, "visibility": 0.9},
                14: {"x": 0.60, "y": 0.50, "z": 0.0, "visibility": 0.9},
                15: {"x": 0.45, "y": 0.55 - (i * 0.002), "z": 0.0, "visibility": 0.9},  # Very small movement
                16: {"x": 0.55, "y": 0.55 - (i * 0.002), "z": 0.0, "visibility": 0.9},
                23: {"x": 0.47, "y": 0.60, "z": 0.0, "visibility": 0.9},
                24: {"x": 0.53, "y": 0.60, "z": 0.0, "visibility": 0.9},
                25: {"x": 0.47, "y": 0.75, "z": 0.0, "visibility": 0.9},
                26: {"x": 0.53, "y": 0.75, "z": 0.0, "visibility": 0.9},
                27: {"x": 0.47, "y": 0.95, "z": 0.0, "visibility": 0.9},
                28: {"x": 0.53, "y": 0.95, "z": 0.0, "visibility": 0.9},
            }
            frames.append(frame)

        result = analyzer.analyze(frames, "left")

        # Should return empty result or insufficient data
        assert result["phase_data"] == [] or "insufficient_data" in result["issues"][0]["issue"]

    def test_wrist_to_leg_uses_upper_arm_threshold(self):
        """Wrist-to-leg should be scored based on upper arm length, not body width."""
        analyzer = DeadliftAnalyzer()

        # Create frames where:
        # - Upper arm (shoulder to elbow) length is ~0.10 units
        # - Wrist-to-leg distance is ~0.03 units (less than half upper arm = good)
        frames = []
        for i in range(40):
            progress = i / 39
            wrist_y = 0.85 - (progress * 0.40)
            wrist_x = 0.48  # Close to leg (knee at 0.47)

            frame = {
                11: {"x": 0.45, "y": 0.40, "z": 0.0, "visibility": 0.9},  # left shoulder
                12: {"x": 0.55, "y": 0.40, "z": 0.0, "visibility": 0.9},  # right shoulder
                13: {"x": 0.40, "y": 0.50, "z": 0.0, "visibility": 0.9},  # left elbow (0.10 from shoulder)
                14: {"x": 0.60, "y": 0.50, "z": 0.0, "visibility": 0.9},  # right elbow
                15: {"x": wrist_x, "y": wrist_y, "z": 0.0, "visibility": 0.9},  # left wrist
                16: {"x": 0.52, "y": wrist_y, "z": 0.0, "visibility": 0.9},  # right wrist
                23: {"x": 0.47, "y": 0.60, "z": 0.0, "visibility": 0.9},  # left hip
                24: {"x": 0.53, "y": 0.60, "z": 0.0, "visibility": 0.9},  # right hip
                25: {"x": 0.47, "y": 0.78, "z": 0.0, "visibility": 0.9},  # left knee
                26: {"x": 0.53, "y": 0.78, "z": 0.0, "visibility": 0.9},  # right knee
                27: {"x": 0.47, "y": 0.95, "z": 0.0, "visibility": 0.9},  # left ankle
                28: {"x": 0.53, "y": 0.95, "z": 0.0, "visibility": 0.9},  # right ankle
            }
            frames.append(frame)

        result = analyzer.analyze(frames, "left")

        # Check that wrist_to_leg metrics include ratio
        for phase_data in result["phase_data"]:
            wrist_metrics = phase_data["metrics"]["wrist_to_leg"]
            if wrist_metrics["status"] != "no_data":
                assert "ratio" in wrist_metrics, "wrist_to_leg should include ratio"
                # Bar is close to leg, ratio should be low
                assert wrist_metrics["ratio"] < 0.5, f"Expected ratio < 0.5, got {wrist_metrics['ratio']}"

    def test_wrist_to_leg_deducts_when_far(self):
        """Wrist-to-leg should deduct points when bar is far from legs."""
        analyzer = DeadliftAnalyzer()

        # Create frames where wrist is far from leg
        frames = []
        for i in range(40):
            progress = i / 39
            wrist_y = 0.85 - (progress * 0.40)
            wrist_x = 0.35  # Far from leg (knee at 0.47)

            frame = {
                11: {"x": 0.45, "y": 0.40, "z": 0.0, "visibility": 0.9},  # left shoulder
                12: {"x": 0.55, "y": 0.40, "z": 0.0, "visibility": 0.9},  # right shoulder
                13: {"x": 0.40, "y": 0.50, "z": 0.0, "visibility": 0.9},  # left elbow
                14: {"x": 0.60, "y": 0.50, "z": 0.0, "visibility": 0.9},  # right elbow
                15: {"x": wrist_x, "y": wrist_y, "z": 0.0, "visibility": 0.9},  # left wrist - far
                16: {"x": 0.65, "y": wrist_y, "z": 0.0, "visibility": 0.9},  # right wrist
                23: {"x": 0.47, "y": 0.60, "z": 0.0, "visibility": 0.9},  # left hip
                24: {"x": 0.53, "y": 0.60, "z": 0.0, "visibility": 0.9},  # right hip
                25: {"x": 0.47, "y": 0.78, "z": 0.0, "visibility": 0.9},  # left knee
                26: {"x": 0.53, "y": 0.78, "z": 0.0, "visibility": 0.9},  # right knee
                27: {"x": 0.47, "y": 0.95, "z": 0.0, "visibility": 0.9},  # left ankle
                28: {"x": 0.53, "y": 0.95, "z": 0.0, "visibility": 0.9},  # right ankle
            }
            frames.append(frame)

        result = analyzer.analyze(frames, "left")

        # Check that at least one phase has a wrist_to_leg issue
        wrist_issues = [
            issue for issue in result["issues"]
            if "wrist_to_leg" in issue["issue"]
        ]
        assert len(wrist_issues) > 0, "Expected wrist_to_leg issues when bar is far from legs"

        # Check that status is not ideal for phases where bar is far
        for phase_data in result["phase_data"]:
            wrist_metrics = phase_data["metrics"]["wrist_to_leg"]
            if wrist_metrics["status"] != "no_data":
                assert wrist_metrics["ratio"] > 0.5, f"Expected ratio > 0.5 when bar is far"

    def test_phase_boundaries_returned(self, deadlift_movement_frames):
        """Phase boundaries should be returned for frontend visualization."""
        analyzer = DeadliftAnalyzer()

        result = analyzer.analyze(deadlift_movement_frames, "left")

        assert "phase_boundaries" in result
        assert len(result["phase_boundaries"]) == 3  # 3 boundaries between 4 phases

        for boundary in result["phase_boundaries"]:
            assert "y" in boundary
            assert "between_phases" in boundary
            assert len(boundary["between_phases"]) == 2
            assert 0 <= boundary["y"] <= 1  # Y should be normalized
