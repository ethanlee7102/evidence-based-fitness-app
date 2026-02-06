import pytest
from src.core.analyzers.deadlift import DeadliftAnalyzer


class TestDeadliftAnalyzer:
    def test_analyze_returns_required_fields(self, sample_landmarks):
        analyzer = DeadliftAnalyzer()
        frames = [sample_landmarks] * 30

        result = analyzer.analyze(frames, "left")

        assert "technique_score" in result
        assert "issues" in result
        assert "bar_path" in result
        assert "component_scores" in result

    def test_score_in_valid_range(self, sample_landmarks):
        analyzer = DeadliftAnalyzer()
        frames = [sample_landmarks] * 30

        result = analyzer.analyze(frames, "left")

        assert 0 <= result["technique_score"] <= 100

    def test_handles_empty_frames(self):
        analyzer = DeadliftAnalyzer()

        result = analyzer.analyze([], "left")

        assert result["technique_score"] >= 0

    def test_handles_none_frames(self):
        analyzer = DeadliftAnalyzer()
        frames = [None] * 10

        result = analyzer.analyze(frames, "left")

        assert result["technique_score"] >= 0

    def test_bar_path_tracked(self, sample_landmarks):
        analyzer = DeadliftAnalyzer()
        frames = [sample_landmarks] * 30

        result = analyzer.analyze(frames, "left")

        assert len(result["bar_path"]) > 0
        assert "x" in result["bar_path"][0]
        assert "y" in result["bar_path"][0]
        assert "frame" in result["bar_path"][0]
