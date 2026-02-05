import pytest


@pytest.fixture
def sample_landmarks():
    """Sample pose landmarks for testing."""
    return {
        11: {"x": 0.4, "y": 0.3, "z": 0.0, "visibility": 0.9},  # left shoulder
        12: {"x": 0.6, "y": 0.3, "z": 0.0, "visibility": 0.9},  # right shoulder
        15: {"x": 0.35, "y": 0.5, "z": 0.0, "visibility": 0.9},  # left wrist
        16: {"x": 0.65, "y": 0.5, "z": 0.0, "visibility": 0.9},  # right wrist
        23: {"x": 0.45, "y": 0.6, "z": 0.0, "visibility": 0.9},  # left hip
        24: {"x": 0.55, "y": 0.6, "z": 0.0, "visibility": 0.9},  # right hip
        25: {"x": 0.45, "y": 0.8, "z": 0.0, "visibility": 0.9},  # left knee
        26: {"x": 0.55, "y": 0.8, "z": 0.0, "visibility": 0.9},  # right knee
        27: {"x": 0.45, "y": 1.0, "z": 0.0, "visibility": 0.9},  # left ankle
        28: {"x": 0.55, "y": 1.0, "z": 0.0, "visibility": 0.9},  # right ankle
    }
