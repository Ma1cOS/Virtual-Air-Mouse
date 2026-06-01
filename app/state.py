from __future__ import annotations

from time import time
from app.gestures import GestureState


class CursorState:
    def __init__(self):
        self.active: bool = False
        self.prev_x: float | None = None
        self.prev_y: float | None = None
        self.hand_lost: bool = True
        self.last_seen: float = 0.0
        self.hold_frames: int = 0
        self.last_dx: int = 0
        self.last_dy: int = 0
        self.accum_x: float = 0.0
        self.accum_y: float = 0.0

        self.landmarks: list = []
        self.lm_list: list = []

        self.fps: float = 0.0
        self.raw_x: int = 0
        self.raw_y: int = 0
        self.smooth_cam_x: float | None = 0.0
        self.smooth_cam_y: float | None = 0.0

        self.filtered_positions: dict[int, tuple[float, float]] = {}

        self.display_x: int | None = None
        self.display_y: int | None = None
        self.dx: int = 0
        self.dy: int = 0

        self.thumb_connection: GestureState | None = None
        self.last_thumb_connection_time: float = 0.0
        self.last_thumb_disconnection_time: float = 0.0
        self.thumb_connected_duration: float = 0.0
        self.currently_holding: bool = False
        self.currently_holding_state: GestureState = GestureState.NONE

        self.last_click_time: float = 0.0
