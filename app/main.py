# ============================================================
#  Main: ενορχηστρωτής κύριου βρόχου
# ============================================================

import time
import cv2
from app import config
from app.state import CursorState
from app.display import landmark_pos, draw_cursor_feedback, draw_status_bar, draw_fps
from app.vision import HandDetector
from app.smoothing import CursorController
from app.output import MouseOutput


_KEY_NOOP  = (-1, 255)   # waitKey returned no key
_KEY_ESC   = 27
_KEY_GREEK = (181, 230)  # μ/Μ variants on Greek keyboard layouts
_KEY_QUIT  = {'q', ';'}   # Q and common nearby key on different layouts


def handle_key(key, state, controller):
    """Χειρίζεται 'q'=έξοδος, 'm'=toggle κέρσορα."""
    if key in _KEY_NOOP:
        return True

    low = key & 0xFF
    ch = chr(low).lower()

    if low == _KEY_ESC or ch in _KEY_QUIT:
        return False

    if ch == 'm' or low in _KEY_GREEK:
        state.active = not state.active
        if state.active:
            state.prev_x = None
            state.prev_y = None
            state.accum_x = 0.0
            state.accum_y = 0.0
            controller.reset_filter()
        print(f"Mouse: {'ON' if state.active else 'OFF'}")
    return True


def _split_int(accum):
    """Επιστρέφει το ακέραιο μέρος και κρατά το υπόλοιπο in-place."""
    value = int(accum)
    return value, accum - value


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
        dx, state.accum_x = _split_int(state.accum_x)
        dy, state.accum_y = _split_int(state.accum_y)
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


def init_mouse():
    """Δημιουργία εικονικού ποντικιού + status print."""
    mouse = MouseOutput()
    if not mouse.ok:
        print("[!] evdev not available")
        print("    pip install evdev, user in 'uinput' group")
        print()
    else:
        print(f"[OK] Virtual mouse: {mouse.device_path}")
    return mouse


def init_camera(index=0):
    """Άνοιγμα κάμερας με MJPG codec. Επιστρέφει cap ή None."""
    cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    if not cap.isOpened():
        print("No camera found.")
        cap.release()
        return None
    return cap


def grab_frame(cap):
    """Λήψη frame από κάμερα + οριζόντιο mirror."""
    success, img = cap.read()
    if not success:
        return None
    return cv2.flip(img, 1)


def detect_landmarks(detector, img):
    """Ανίχνευση χεριού + εξαγωγή συντεταγμένων."""
    img = detector.find_hands(img)
    lm_list = detector.find_position(img)
    return img, lm_list


def emit_subframes(mouse, dx, dy, t0, state, controller):
    """
    Σπάσιμο (dx, dy) σε sub-frames με τοπικό accumulator.
    Στέλνει REL events και ελέγχει πλήκτρα κάθε sub-frame.
    Επιστρέφει False για έξοδο, True για συνέχεια.
    """
    elapsed = time.time() - t0
    wait_ms = max(1, int(((1.0 / config.FRAME_TARGET) - elapsed) * 1000))

    sub = config.MOUSE_SUBDIVISIONS
    sub_wait = max(1, wait_ms // sub)
    rx = ry = 0.0
    step_x = dx / sub
    step_y = dy / sub

    for _ in range(sub):
        rx += step_x
        ry += step_y
        sx, rx = _split_int(rx)
        sy, ry = _split_int(ry)
        if sx or sy:
            mouse.move(sx, sy)
        key = cv2.waitKey(sub_wait) & 0xFF
        if not handle_key(key, state, controller):
            return False
    return True


def main():
    mouse = init_mouse()

    cap = init_camera(config.CAMERA_INDEX)
    if cap is None:
        mouse.close()
        return

    detector = HandDetector()
    controller = CursorController()
    state = CursorState()

    fps = 0.0
    prev_time = 0.0

    try:
        while True:
            t0 = time.time()
            if prev_time > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / (t0 - prev_time))
            prev_time = t0

            img = grab_frame(cap)
            if img is None:
                break

            img, lm_list = detect_landmarks(detector, img)
            img, dx, dy = process_landmarks(img, lm_list, state, controller)

            draw_status_bar(img, state, mouse)
            draw_fps(img, fps)
            cv2.imshow("Virtual Air Mouse", img)

            if not emit_subframes(mouse, dx, dy, t0, state, controller):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()
        mouse.close()
        if mouse.ok:
            print("[OK] Virtual mouse released.")
