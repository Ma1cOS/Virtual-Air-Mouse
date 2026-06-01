"""Adaptive EMA filter and CursorController. The smoothing pipeline."""

import numpy as np
from app import config


class SmoothingFilter:
    """Adaptive EMA for 2D coordinates. O(1), no history buffer.

    When the hand is nearly still (distance < stability_threshold),
    alpha gets cut by STABILITY_REDUCTION to lock the cursor in place
    and kill micro-jitter. In motion it snaps back to full alpha.
    """

    def __init__(self, alpha: float = config.ALPHA,
                 stability_threshold: float = config.STABILITY_THRESHOLD):
        self.alpha: float = alpha
        self.stability_threshold: float = stability_threshold
        self.smoothed_x: float | None = None
        self.smoothed_y: float | None = None

    def update(self, raw_x: float, raw_y: float) -> tuple[float, float]:
        """One EMA step: s_t = α·x_t + (1-α)·s_{t-1}.

        First call seeds the filter with the raw value, no lag.

        Returns:
            (smoothed_x, smoothed_y). The filtered position.
        """
        if self.smoothed_x is None:
            self.smoothed_x = raw_x
            self.smoothed_y = raw_y
            return self.smoothed_x, self.smoothed_y

        # How far did the raw point move from the smoothed one?
        # If the answer is "barely", we lock.
        distance = np.hypot(
            raw_x - self.smoothed_x,
            raw_y - self.smoothed_y)

        alpha = (self.alpha * config.STABILITY_REDUCTION
                 if distance < self.stability_threshold
                 else self.alpha)

        self.smoothed_x = alpha * raw_x + (1 - alpha) * self.smoothed_x
        self.smoothed_y = alpha * raw_y + (1 - alpha) * self.smoothed_y
        return self.smoothed_x, self.smoothed_y

    def reset(self):
        """Wipe state. Next update() will start fresh."""
        self.smoothed_x = None
        self.smoothed_y = None


class CursorController:
    """One SmoothingFilter per landmark we care about.

    Public methods:
        update(lm_list)               -> (cursor_x, cursor_y)
        update_click_points(lm_list)  -> {finger_id: (x, y), ...}
        get_display_pos()             -> (cursor_x, cursor_y) without running the filter
        reset_filter()                -> toss all smoothed state
    """

    def __init__(self, cursor_finger: int = config.CURSOR_FINGER,
                 alpha: float = config.ALPHA,
                 click_alpha: float = config.CLICK_ALPHA):
        self.cursor_finger: int = cursor_finger
        self.cursor_filter = SmoothingFilter(alpha=alpha)

        # Click fingers need a faster alpha. Otherwise pinch gestures feel laggy.
        self.click_ids: dict[int, SmoothingFilter] = {
            config.FINGER_BASE_CLICK:   SmoothingFilter(alpha=click_alpha),
            config.FINGER_LEFT_CLICK:   SmoothingFilter(alpha=click_alpha),
            config.FINGER_RIGHT_CLICK:  SmoothingFilter(alpha=click_alpha),
            config.FINGER_MIDDLE_CLICK: SmoothingFilter(alpha=click_alpha),
        }

    def update(self, lm_list: list) -> tuple[float | None, float | None]:
        """Filter the cursor finger through EMA.

        Returns (None, None) if there's no hand in the frame.
        """
        if not lm_list or len(lm_list) <= self.cursor_finger:
            return None, None
        raw_x = lm_list[self.cursor_finger][1]
        raw_y = lm_list[self.cursor_finger][2]
        return self.cursor_filter.update(raw_x, raw_y)

    def update_click_points(self, lm_list: list) -> dict[int, tuple[float, float]] | None:
        """Run every click finger through its own EMA.

        Returns a dict landmark_id -> (x, y), or None if lm_list is empty.
        """
        if not lm_list:
            return None
        result: dict[int, tuple[float, float]] = {}
        for finger_id, flt in self.click_ids.items():
            if finger_id < len(lm_list):
                result[finger_id] = flt.update(
                    lm_list[finger_id][1],
                    lm_list[finger_id][2])
        return result

    def get_display_pos(self) -> tuple[float | None, float | None]:
        """Peek at the current smoothed cursor position. No filter step."""
        return self.cursor_filter.smoothed_x, self.cursor_filter.smoothed_y

    def reset_filter(self):
        """Dump all filter state. Called when the hand reappears after being lost."""
        self.cursor_filter.reset()
        for flt in self.click_ids.values():
            flt.reset()
