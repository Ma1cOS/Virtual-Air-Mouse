# ============================================================
#  Main — Ενορχηστρωτής κύριου βρόχου
# -----------------------------------------------------------
#  Συνδέει: vision → smoothing → output
#  REL-only pipeline: camera deltas → REL_X/REL_Y events
# ============================================================

import time
import cv2
from app import config
from app.state import CursorState
from app.display import landmark_pos, draw_cursor_feedback, draw_status_bar, draw_fps
from app.vision import HandDetector
from app.smoothing import CursorController
from app.output import MouseOutput


def handle_key(key, state, controller):
    """Χειρίζεται 'q'=έξοδος, 'm'=toggle κέρσορα."""
    if key == ord('q'):
        return False
    if key == ord('m'):
        state.active = not state.active
        if state.active:
            state.prev_x = None
            state.prev_y = None
            state.accum_x = 0.0
            state.accum_y = 0.0
            controller.reset_filter()
        print(f"Mouse: {'ON' if state.active else 'OFF'}")
    return True


def handle_reacquire(state, controller):
    """Επαναφορά φίλτρου + μηδενισμός prev και accumulators."""
    controller.reset_filter()
    state.hand_lost = False
    state.prev_x = None
    state.prev_y = None
    state.accum_x = 0.0
    state.accum_y = 0.0


def compute_movement(state, smooth_cam_x, smooth_cam_y):
    """Υπολογίζει (dx, dy) σε REL units με sub-pixel accumulation."""
    dx = dy = 0
    if state.active and state.prev_x is not None:
        cam_dx = smooth_cam_x - state.prev_x
        cam_dy = smooth_cam_y - state.prev_y
        state.accum_x += cam_dx * config.DELTA_SCALE
        state.accum_y += cam_dy * config.DELTA_SCALE
        dx = int(state.accum_x)
        dy = int(state.accum_y)
        state.accum_x -= dx
        state.accum_y -= dy
    state.prev_x = smooth_cam_x
    state.prev_y = smooth_cam_y
    return dx, dy


def process_landmarks(img, lm_list, state, controller):
    """
    Διαχείριση landmark detection, EMA smoothing, movement, και
    drawing με οπτική ανατροφοδότηση.

    @param img: τρέχον frame
    @param lm_list: λίστα landmarks
    @param state: CursorState
    @param controller: CursorController
    @returns: (img, dx, dy)
    """
    dx = dy = 0

    if lm_list:
        state.last_seen = time.time()
        state.hold_frames = 0

        if state.hand_lost:
            handle_reacquire(state, controller)

        smooth_cam_x, smooth_cam_y = controller.update(lm_list)
        if smooth_cam_x is not None:
            dx, dy = compute_movement(state, smooth_cam_x, smooth_cam_y)

        state.last_dx = dx
        state.last_dy = dy

        raw_x, raw_y = landmark_pos(lm_list, config.CURSOR_FINGER)
        display_x, display_y = controller.get_display_pos()
        if display_x is not None:
            display_x, display_y = int(display_x), int(display_y)
            draw_cursor_feedback(img, raw_x, raw_y, display_x, display_y)

        cv2.putText(img, f"Delta: ({dx}, {dy})",
                    (20, 110), cv2.FONT_HERSHEY_PLAIN, 1.1,
                    (0, 255, 255) if state.active else (128, 128, 128), 2)
    else:
        state.hold_frames += 1
        if state.hold_frames <= config.VELOCITY_HOLD_FRAMES:
            dx, dy = state.last_dx, state.last_dy
        if time.time() - state.last_seen > config.HAND_LOST_TIMEOUT and not state.hand_lost:
            state.hand_lost = True

    return img, dx, dy


def main():
    mouse = MouseOutput()
    if not mouse.ok:
        print("[!] evdev not available")
        print("    pip install evdev, user in 'uinput' group")
        print()
    else:
        print(f"[OK] Virtual mouse: {mouse.device_path}")

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    if not cap.isOpened():
        print("No camera found.")
        mouse.close()
        return

    detector = HandDetector()
    controller = CursorController()

    state = CursorState()

    fps = 0.0
    prev_time = 0.0

    try:
        while True:
            now = time.time()
            if prev_time > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / (now - prev_time))
            prev_time = now

            success, img = cap.read()
            if not success:
                break

            img = cv2.flip(img, 1)

            img = detector.find_hands(img)
            lm_list = detector.find_position(img)

            img, dx, dy = process_landmarks(img, lm_list, state, controller)

            draw_status_bar(img, state, mouse)
            draw_fps(img, fps)
            cv2.imshow("Virtual Air Mouse", img)

            elapsed = time.time() - now
            wait_ms = max(1, int(((1.0 / config.FRAME_TARGET) - elapsed) * 1000))

            sub = config.MOUSE_SUBDIVISIONS
            sub_wait = max(1, wait_ms // sub)
            rx = ry = 0.0
            step_x = dx / sub
            step_y = dy / sub
            running = True

            for _ in range(sub):
                rx += step_x
                ry += step_y
                sx = int(rx); rx -= sx
                sy = int(ry); ry -= sy
                if sx or sy:
                    mouse.move(sx, sy)
                key = cv2.waitKey(sub_wait) & 0xFF
                if not handle_key(key, state, controller):
                    running = False
                    break

            if not running:
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()
        mouse.close()
        if mouse.ok:
            print("[OK] Virtual mouse released.")
