import numpy as np
from app import config


class SmoothingFilter:
    def __init__(self, alpha=config.ALPHA,
                 stability_threshold=config.STABILITY_THRESHOLD):
        self.alpha = alpha
        self.stability_threshold = stability_threshold
        self.smoothed_x = None
        self.smoothed_y = None

    def update(self, raw_x, raw_y):
        if self.smoothed_x is None:
            self.smoothed_x = raw_x
            self.smoothed_y = raw_y
            return self.smoothed_x, self.smoothed_y

        distance = np.hypot(
            raw_x - self.smoothed_x,
            raw_y - self.smoothed_y)

        alpha = self.alpha * 0.1 if distance < self.stability_threshold \
                else self.alpha

        self.smoothed_x = alpha * raw_x + (1 - alpha) * self.smoothed_x
        self.smoothed_y = alpha * raw_y + (1 - alpha) * self.smoothed_y
        return self.smoothed_x, self.smoothed_y

    def reset(self):
        self.smoothed_x = None
        self.smoothed_y = None


class CursorController:
    def __init__(self, cursor_finger=config.CURSOR_FINGER,
                 alpha=config.ALPHA,
                 click_alpha=config.CLICK_ALPHA):
        self.cursor_finger = cursor_finger
        self.cursor_filter = SmoothingFilter(alpha=alpha)

        self.click_ids = {
            config.FINGER_BASE_CLICK:   SmoothingFilter(alpha=click_alpha),
            config.FINGER_LEFT_CLICK:   SmoothingFilter(alpha=click_alpha),
            config.FINGER_RIGHT_CLICK:  SmoothingFilter(alpha=click_alpha),
            config.FINGER_MIDDLE_CLICK: SmoothingFilter(alpha=click_alpha),
        }

    def update(self, lm_list):
        if not lm_list or len(lm_list) <= self.cursor_finger:
            return None, None
        raw_x = lm_list[self.cursor_finger][1]
        raw_y = lm_list[self.cursor_finger][2]
        return self.cursor_filter.update(raw_x, raw_y)

    def update_click_points(self, lm_list):
        if not lm_list:
            return None
        result = {}
        for finger_id, flt in self.click_ids.items():
            if finger_id < len(lm_list):
                result[finger_id] = flt.update(
                    lm_list[finger_id][1],
                    lm_list[finger_id][2])
        return result

    def get_display_pos(self):
        return self.cursor_filter.smoothed_x, self.cursor_filter.smoothed_y

    def reset_filter(self):
        self.cursor_filter.reset()
        for flt in self.click_ids.values():
            flt.reset()
