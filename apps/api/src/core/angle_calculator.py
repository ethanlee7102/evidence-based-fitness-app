import math
from typing import Optional


def calculate_angle(a: dict, b: dict, c: dict) -> float:
    """
    Calculate the angle at point B formed by points A, B, C.
    Returns angle in degrees (0-180).

    This is useful for measuring joint angles:
    - Hip angle: shoulder-hip-knee
    - Knee angle: hip-knee-ankle
    - Back angle: vertical-shoulder-hip
    """
    ba = (a["x"] - b["x"], a["y"] - b["y"])
    bc = (c["x"] - b["x"], c["y"] - b["y"])

    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.sqrt(ba[0] ** 2 + ba[1] ** 2)
    mag_bc = math.sqrt(bc[0] ** 2 + bc[1] ** 2)

    if mag_ba == 0 or mag_bc == 0:
        return 0.0

    cos_angle = max(-1, min(1, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))


def calculate_vertical_angle(top: dict, bottom: dict) -> float:
    """
    Calculate the angle from vertical for a line segment.
    Returns angle in degrees (0 = vertical, 90 = horizontal).

    Useful for measuring back angle (torso vs vertical).
    """
    dx = top["x"] - bottom["x"]
    dy = top["y"] - bottom["y"]

    if dy == 0:
        return 90.0

    return math.degrees(math.atan(abs(dx) / abs(dy)))


def calculate_horizontal_drift(points: list[dict]) -> float:
    """
    Calculate total horizontal drift of a path.
    Returns the max deviation from the starting x position.

    Useful for bar path analysis.
    """
    if not points:
        return 0.0

    start_x = points[0]["x"]
    max_drift = 0.0

    for point in points:
        drift = abs(point["x"] - start_x)
        max_drift = max(max_drift, drift)

    return max_drift


def calculate_path_straightness(points: list[dict]) -> float:
    """
    Calculate how straight a path is (0-1, where 1 is perfectly straight).

    Uses the ratio of direct distance to path length.
    """
    if len(points) < 2:
        return 1.0

    direct_distance = math.sqrt(
        (points[-1]["x"] - points[0]["x"]) ** 2 +
        (points[-1]["y"] - points[0]["y"]) ** 2
    )

    path_length = 0.0
    for i in range(1, len(points)):
        segment = math.sqrt(
            (points[i]["x"] - points[i - 1]["x"]) ** 2 +
            (points[i]["y"] - points[i - 1]["y"]) ** 2
        )
        path_length += segment

    if path_length == 0:
        return 1.0

    return min(1.0, direct_distance / path_length)
