"""OpenCV GUI in a daemon thread. Reads frames and state from queues.

Keyboard shortcuts (via cv2.waitKey):
    Q / Esc    quit
    M          toggle mouse tracking on/off

On Greek keyboards 'μ' (keycode 181) also counts as M.
"""

from __future__ import annotations

import threading
import queue
import time
import cv2
import numpy as np
from app import config
from app.state import CursorState

# cv2.waitKey returns -1 when no key was pressed. Some window managers
# also report 255 as "no key". Both count as nothing.
_KEY_NOOP = (-1, 255)
_KEY_ESC = 27

# Greek keyboard: 'μ' produces keycode 181 (lowercase) or 230 (uppercase).
# We treat both as the 'm' toggle.
_KEY_GREEK = (181, 230)

# ';' closes the app too. On a Greek keyboard the physical key that
# produces 'q' on US layout produces ';' instead.
_KEY_QUIT = {'q', ';'}

# MediaPipe hand skeleton: 21 landmarks, 21 edges.
_HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
)


class GUIWorker:
    """Grabs frames and state from queues, draws the overlay on top.

    Lives in a daemon thread. The main thread pushes images and state
    into queues, this thread pulls them out and calls imshow.
    cv2.imshow has to run in the thread that created the window,
    so we can't do this from main.
    """

    def __init__(self, pause_event: threading.Event, quit_event: threading.Event,
                 image_queue: queue.Queue, state_queue: queue.Queue):
        self.pause_event = pause_event
        self.quit_event = quit_event
        self.image_queue = image_queue
        self.state_queue = state_queue
        self.image = np.zeros((480, 640, 3), dtype=np.uint8)
        self.state = CursorState()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        """Pull from queues, draw, check for keypresses. Repeat."""
        while not self.quit_event.is_set():
            try:
                current_img = self.image_queue.get_nowait()
                self.image = current_img
            except queue.Empty:
                pass  # keep previous frame

            try:
                current_state = self.state_queue.get_nowait()
                self.state = current_state
            except queue.Empty:
                pass  # keep previous state

            if not self.update(self.image, self.state):
                break

    def handle_key(self, key: int) -> bool:
        """Turn a raw cv2.waitKey value into an action.

        Returns False when the user asked to quit.
        """
        if key in _KEY_NOOP:
            return True

        low = key & 0xFF
        ch = chr(low).lower()

        if low == _KEY_ESC or ch in _KEY_QUIT:
            self.quit_event.set()
            return False

        # Toggle: 'm' on US layout, 'μ' on Greek.
        if ch == 'm' or low in _KEY_GREEK:
            if self.pause_event.is_set():
                self.pause_event.clear()
            else:
                self.pause_event.set()
        return True

    def update(self, img: np.ndarray, state: CursorState) -> bool:
        """Draw overlays on the frame, show it, check for key input.

        Returns False if the user pressed quit.
        """
        self.image = img
        self.state = state

        self.draw_status_bar(state)
        self.draw_fps(state.fps)
        self.draw_delta_label(state)
        self.draw_filter_feedback(img, state)
        self.draw_shortcuts()
        self._draw_landmarks()

        cv2.imshow("Virtual Air Mouse", img)
        key = cv2.waitKey(1) & 0xFF
        return self.handle_key(key)

    def stop(self) -> None:
        cv2.destroyAllWindows()

    # ---- Drawing helpers ----

    def draw_shortcuts(self) -> None:
        """Shortcut legend, bottom left."""
        h = self.image.shape[0]
        cv2.putText(self.image, "M: toggle mouse   Q: quit", (20, h - 20),
                    cv2.FONT_HERSHEY_PLAIN, 1.0, (200, 200, 200), 1)

    def draw_delta_label(self, state: CursorState) -> None:
        """Current REL delta, top left info panel."""
        color = (0, 255, 255) if state.active else (128, 128, 128)
        cv2.putText(self.image, f"Delta: ({state.last_dx}, {state.last_dy})",
                    (20, 110), cv2.FONT_HERSHEY_PLAIN, 1.1, color, 2)

    def draw_filter_feedback(self, img: np.ndarray, state: CursorState) -> None:
        """EMA filter visualisation for every tracked landmark.

        Red filled circle: the smoothed (filtered) position.
        Yellow line:       connects raw -> smoothed.
        """
        if not state.lm_list or not state.filtered_positions:
            return

        for finger_id, (smooth_x, smooth_y) in state.filtered_positions.items():
            if finger_id >= len(state.lm_list):
                continue
            raw_x = state.lm_list[finger_id][1]
            raw_y = state.lm_list[finger_id][2]
            sx, sy = int(smooth_x), int(smooth_y)
            cv2.circle(img, (sx, sy), 6, (0, 0, 255), -1)
            cv2.line(img, (raw_x, raw_y), (sx, sy), (255, 255, 0), 1)

    def draw_status_bar(self, state: CursorState) -> None:
        """ON / OFF indicator, top left."""
        status, color = ("ON", (0, 255, 0)) if state.active else ("OFF", (0, 0, 255))
        cv2.putText(self.image, f"Mouse: {status}", (20, 50),
                    cv2.FONT_HERSHEY_PLAIN, 2, color, 2)

    def draw_fps(self, fps: float) -> None:
        """FPS counter, top right. Green ≥20, orange 10-19, red below."""
        if fps >= 20:
            color = (0, 255, 0)
        elif fps >= 10:
            color = (0, 165, 255)
        else:
            color = (0, 0, 255)
        cv2.putText(self.image, f"FPS: {fps:.0f}",
                    (self.image.shape[1] - 120, 50), cv2.FONT_HERSHEY_PLAIN, 1.5, color, 2)

    def _draw_landmarks(self) -> None:
        """Green circles + green lines for the MediaPipe hand skeleton."""
        if not self.state.landmarks:
            return
        h, w, _ = self.image.shape

        for lm in self.state.landmarks:
            x, y = int(lm.x * w), int(lm.y * h)
            cv2.circle(self.image, (x, y), 4, (0, 255, 0), cv2.FILLED)

        for a, b in _HAND_CONNECTIONS:
            if a < len(self.state.landmarks) and b < len(self.state.landmarks):
                x1, y1 = int(self.state.landmarks[a].x * w), int(self.state.landmarks[a].y * h)
                x2, y2 = int(self.state.landmarks[b].x * w), int(self.state.landmarks[b].y * h)
                cv2.line(self.image, (x1, y1), (x2, y2), (0, 255, 0), 2)

    def get_is_mouse_active(self) -> bool:
        return self.state.active
