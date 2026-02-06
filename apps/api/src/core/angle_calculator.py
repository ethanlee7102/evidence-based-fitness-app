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


def calculate_angle_from_horizontal(point_a: dict, point_b: dict) -> float:
    """
    Calculate the angle from a horizontal line through point_a to the line point_a -> point_b.

    Returns angle in degrees:
    - 0° = horizontal (point_b at same height as point_a)
    - 90° = vertical (point_b directly above or below point_a)

    Used for:
    - Back angle: hip -> shoulder (how upright the torso is)
    - Thigh angle: hip -> knee (how upright the thigh is)

    Note: In normalized coordinates, lower Y = higher on screen.
    The angle is always positive, measured as deviation from horizontal.
    """
    dx = point_b["x"] - point_a["x"]
    dy = point_a["y"] - point_b["y"]  # Inverted because lower Y = higher on screen

    if dx == 0 and dy == 0:
        return 0.0

    # Calculate angle from horizontal (atan2 gives angle from positive x-axis)
    angle_rad = math.atan2(abs(dy), abs(dx))
    return math.degrees(angle_rad)


def calculate_knee_angle(hip: dict, knee: dict, ankle: dict) -> float:
    """
    Calculate the angle at the knee joint.

    Returns angle in degrees:
    - 180° = leg fully extended (straight)
    - Smaller values = more bent knee

    This is a convenience wrapper around calculate_angle.
    """
    return calculate_angle(hip, knee, ankle)


def calculate_distance(point_a: dict, point_b: dict) -> float:
    """
    Calculate the Euclidean distance between two points.

    Args:
        point_a: First point with x, y coordinates
        point_b: Second point with x, y coordinates

    Returns:
        Distance in normalized coordinate units
    """
    dx = point_b["x"] - point_a["x"]
    dy = point_b["y"] - point_a["y"]
    return math.sqrt(dx * dx + dy * dy)


def calculate_wrist_to_leg_distance(
    wrist: dict,
    leg_top: dict,
    leg_bottom: dict,
) -> float:
    """
    Calculate horizontal distance from wrist to the leg line.

    For lower phases (bar near shins): use ankle as leg_bottom, knee as leg_top
    For upper phases (bar near thighs): use knee as leg_bottom, hip as leg_top

    Args:
        wrist: Wrist position (bar position proxy)
        leg_top: Upper point of leg segment
        leg_bottom: Lower point of leg segment

    Returns:
        Horizontal distance in normalized coordinate units
    """
    # Interpolate the X position of the leg line at the wrist's Y height
    wrist_y = wrist["y"]
    top_y = leg_top["y"]
    bottom_y = leg_bottom["y"]

    # Handle edge cases
    if abs(top_y - bottom_y) < 0.001:
        # Leg segment is nearly horizontal, use average X
        leg_x_at_wrist = (leg_top["x"] + leg_bottom["x"]) / 2
    else:
        # Linear interpolation: find X on leg line at wrist's Y
        t = (wrist_y - bottom_y) / (top_y - bottom_y)
        t = max(0.0, min(1.0, t))  # Clamp to valid range
        leg_x_at_wrist = leg_bottom["x"] + t * (leg_top["x"] - leg_bottom["x"])

    return abs(wrist["x"] - leg_x_at_wrist)


def calculate_shoulder_bar_position(
    shoulder: dict,
    wrist: dict,
    body_width: float
) -> float:
    """
    Calculate shoulder position relative to the bar (wrist).

    Returns percentage of body width:
    - Negative = shoulder in front of bar (leaning forward)
    - Zero = shoulder directly over bar (ideal for setup)
    - Positive = shoulder behind bar (leaning back)

    Args:
        shoulder: Shoulder position
        wrist: Wrist position (bar proxy)
        body_width: Reference width for normalization

    Returns:
        Signed percentage: negative = in front, positive = behind
    """
    if body_width <= 0:
        return 0.0

    # Positive means shoulder is to the right of wrist (behind bar in side view)
    # Negative means shoulder is to the left of wrist (in front of bar in side view)
    horizontal_offset = shoulder["x"] - wrist["x"]
    return (horizontal_offset / body_width) * 100


def calculate_body_width(
    left_shoulder: dict,
    right_shoulder: dict,
    left_hip: dict,
    right_hip: dict
) -> float:
    """
    Estimate body width as average of shoulder and hip widths.

    Used as a normalization factor for horizontal distance metrics.
    """
    shoulder_width = abs(left_shoulder["x"] - right_shoulder["x"])
    hip_width = abs(left_hip["x"] - right_hip["x"])
    return (shoulder_width + hip_width) / 2
