from time import time
from app.gestures import GestureState


class CursorState:
    def __init__(self):
        self.active = False
        self.prev_x = None
        self.prev_y = None
        self.hand_lost = True
        self.last_seen = 0.0
        self.hold_frames = 0
        self.last_dx = 0
        self.last_dy = 0
        self.accum_x = 0.0
        self.accum_y = 0.0

        self.landmarks = []
        self.lm_list = []

        self.fps = 0.0
        self.raw_x = 0
        self.raw_y = 0
        self.smooth_cam_x = 0.0
        self.smooth_cam_y = 0.0

        self.filtered_positions = {}

        self.display_x = None
        self.display_y = None
        self.dx = 0
        self.dy = 0

        self.thumb_connection = None
        self.last_thumb_connection_time = 0.0
        self.last_thumb_disconnection_time = 0.0
        self.thumb_connected_duration = 0.0
        self.currently_holding = False
        self.currently_holding_state = GestureState.NONE

        self.last_click_time = 0.0
