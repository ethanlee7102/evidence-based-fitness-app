import pytest


@pytest.fixture
def sample_landmarks():
    """Sample pose landmarks for testing (static position)."""
    return {
        11: {"x": 0.4, "y": 0.3, "z": 0.0, "visibility": 0.9},  # left shoulder
        12: {"x": 0.6, "y": 0.3, "z": 0.0, "visibility": 0.9},  # right shoulder
        13: {"x": 0.35, "y": 0.4, "z": 0.0, "visibility": 0.9},  # left elbow
        14: {"x": 0.65, "y": 0.4, "z": 0.0, "visibility": 0.9},  # right elbow
        15: {"x": 0.35, "y": 0.5, "z": 0.0, "visibility": 0.9},  # left wrist
        16: {"x": 0.65, "y": 0.5, "z": 0.0, "visibility": 0.9},  # right wrist
        23: {"x": 0.45, "y": 0.6, "z": 0.0, "visibility": 0.9},  # left hip
        24: {"x": 0.55, "y": 0.6, "z": 0.0, "visibility": 0.9},  # right hip
        25: {"x": 0.45, "y": 0.8, "z": 0.0, "visibility": 0.9},  # left knee
        26: {"x": 0.55, "y": 0.8, "z": 0.0, "visibility": 0.9},  # right knee
        27: {"x": 0.45, "y": 1.0, "z": 0.0, "visibility": 0.9},  # left ankle
        28: {"x": 0.55, "y": 1.0, "z": 0.0, "visibility": 0.9},  # right ankle
    }


@pytest.fixture
def deadlift_movement_frames():
    """
    Generate realistic deadlift movement frames from floor to lockout.

    Returns 40 frames simulating a deadlift:
    - Frames 0-9: Phase 1 (floor to 25%)
    - Frames 10-19: Phase 2 (25% to 50%)
    - Frames 20-29: Phase 3 (50% to 75%)
    - Frames 30-39: Phase 4 (75% to lockout)

    Key movements:
    - Wrists move from y=0.85 (floor) to y=0.45 (lockout)
    - Back angle increases (becomes more upright)
    - Hip and knee angles increase (extend)
    """
    frames = []

    for i in range(40):
        progress = i / 39  # 0 to 1

        # Wrist Y: starts at 0.85 (floor), ends at 0.45 (lockout)
        wrist_y = 0.85 - (progress * 0.40)

        # Hip Y: starts at 0.65 (low), ends at 0.55 (standing)
        hip_y = 0.65 - (progress * 0.10)

        # Shoulder Y: starts at 0.45, ends at 0.35 (more upright)
        shoulder_y = 0.45 - (progress * 0.10)

        # Knee Y: starts at 0.78, ends at 0.70 (legs straighten)
        knee_y = 0.78 - (progress * 0.08)

        # Shoulder X: starts slightly forward (0.42), ends more back (0.50)
        shoulder_x_left = 0.42 + (progress * 0.03)
        shoulder_x_right = 0.58 + (progress * 0.02)

        frame = {
            11: {"x": shoulder_x_left, "y": shoulder_y, "z": 0.0, "visibility": 0.9},  # left shoulder
            12: {"x": shoulder_x_right, "y": shoulder_y, "z": 0.0, "visibility": 0.9},  # right shoulder
            13: {"x": 0.38, "y": (shoulder_y + wrist_y) / 2, "z": 0.0, "visibility": 0.9},  # left elbow
            14: {"x": 0.62, "y": (shoulder_y + wrist_y) / 2, "z": 0.0, "visibility": 0.9},  # right elbow
            15: {"x": 0.45, "y": wrist_y, "z": 0.0, "visibility": 0.9},  # left wrist
            16: {"x": 0.55, "y": wrist_y, "z": 0.0, "visibility": 0.9},  # right wrist
            23: {"x": 0.47, "y": hip_y, "z": 0.0, "visibility": 0.9},  # left hip
            24: {"x": 0.53, "y": hip_y, "z": 0.0, "visibility": 0.9},  # right hip
            25: {"x": 0.47, "y": knee_y, "z": 0.0, "visibility": 0.9},  # left knee
            26: {"x": 0.53, "y": knee_y, "z": 0.0, "visibility": 0.9},  # right knee
            27: {"x": 0.47, "y": 0.95, "z": 0.0, "visibility": 0.9},  # left ankle (fixed)
            28: {"x": 0.53, "y": 0.95, "z": 0.0, "visibility": 0.9},  # right ankle (fixed)
        }
        frames.append(frame)

    return frames
