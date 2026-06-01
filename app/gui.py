import threading
import queue
import time
import cv2
import numpy as np
from app import config
from app.state import CursorState

_KEY_NOOP = (-1, 255)
_KEY_ESC = 27
_KEY_GREEK = (181, 230)
_KEY_QUIT = {'q', ';'}

_HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
)


class GUIWorker:
    def __init__(self, pause_event, quit_event, image_queue: queue.Queue, state_queue: queue.Queue):
        self.pause_event = pause_event
        self.quit_event = quit_event
        self.image_queue = image_queue
        self.state_queue = state_queue
        self.image = np.zeros((480, 640, 3), dtype=np.uint8)
        self.state = CursorState()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self.quit_event.is_set():
            try:
                current_img = self.image_queue.get_nowait()
                self.image = current_img
            except queue.Empty:
                pass

            try:
                current_state = self.state_queue.get_nowait()
                self.state = current_state
            except queue.Empty:
                pass

            if not self.update(self.image, self.state):
                break

    def handle_key(self, key):
        if key in _KEY_NOOP:
            return True

        low = key & 0xFF
        ch = chr(low).lower()

        if low == _KEY_ESC or ch in _KEY_QUIT:
            self.quit_event.set()
            return False

        if ch == 'm' or low in _KEY_GREEK:
            if self.pause_event.is_set():
                self.pause_event.clear()
            else:
                self.pause_event.set()
        return True

    def update(self, img, state):
        self.image = img
        self.state = state
        self.draw_status_bar(state)
        self.draw_fps(state.fps)
        self.draw_delta_label(state)
        self.draw_filter_feedback(img, state)
        self._draw_landmarks()
        cv2.imshow("Virtual Air Mouse", img)
        key = cv2.waitKey(1) & 0xFF
        return self.handle_key(key)

    def stop(self):
        cv2.destroyAllWindows()

    def draw_delta_label(self, state):
        color = (0, 255, 255) if state.active else (128, 128, 128)
        cv2.putText(self.image, f"Delta: ({state.last_dx}, {state.last_dy})",
                    (20, 110), cv2.FONT_HERSHEY_PLAIN, 1.1, color, 2)

    def draw_filter_feedback(self, img, state):
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

    def draw_status_bar(self, state):
        status, color = ("ON", (0, 255, 0)) if state.active else ("OFF", (0, 0, 255))
        cv2.putText(self.image, f"Mouse: {status}", (20, 50),
                    cv2.FONT_HERSHEY_PLAIN, 2, color, 2)

    def draw_fps(self, fps):
        if fps >= 20:
            color = (0, 255, 0)
        elif fps >= 10:
            color = (0, 165, 255)
        else:
            color = (0, 0, 255)
        cv2.putText(self.image, f"FPS: {fps:.0f}",
                    (self.image.shape[1] - 120, 50), cv2.FONT_HERSHEY_PLAIN, 1.5, color, 2)

    def _draw_landmarks(self):
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

    def get_is_mouse_active(self):
        return self.state.active
