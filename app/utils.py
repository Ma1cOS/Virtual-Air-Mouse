"""Tiny helpers: sub-pixel splitting, landmark access, Euclidean distance."""

import math


def split_int(accum: float) -> tuple[int, float]:
    """Split a float into its integer part and the remainder.

    We use this for sub-pixel accumulation. The integer goes out as a
    REL motion event, the leftover fraction rolls into the next frame.

    Args:
        accum: The value to split.

    Returns:
        (int_part, remainder). e.g. split_int(3.7) returns (3, 0.7)
    """
    value = int(accum)
    return value, accum - value


def landmark_pos(lm_list: list, finger_id: int) -> tuple[int, int]:
    """Grab (x, y) coordinates for one MediaPipe landmark.

    Args:
        lm_list: [[id, x, y], ...] straight from HandDetector.find_position()
        finger_id: landmark index. 0 is palm base, 8 is index tip, etc.

    Returns:
        (x, y) in camera pixel space.
    """
    return lm_list[finger_id][1], lm_list[finger_id][2]


def distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Plain Euclidean distance. No surprises.

    Args:
        p1, p2: (x, y) points.

    Returns:
        Distance in whatever units the coordinates are in.
    """
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])
