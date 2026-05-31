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
from app.input import ThreadedCamera

from app.state import GestureState

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
        # print(f"Raw delta: ({cam_dx}, {cam_dy})")
        state.accum_x += cam_dx * config.DELTA_SCALE
        state.accum_y += cam_dy * config.DELTA_SCALE
        dx, state.accum_x = _split_int(state.accum_x)
        dy, state.accum_y = _split_int(state.accum_y) 
        # Round dx to 8 digits
        dx = round(dx+state.accum_x, 8)
        dy = round(dy+state.accum_y, 8)
        

        #print(f"With Delta and split_int which does: ({dx}, {dy})")

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

        # Εύρεση της μεταβολής (dx, dy) σε relative units με sub-pixel accumulation
        if smooth_cam_x is not None:
            dx, dy = compute_movement(state, smooth_cam_x, smooth_cam_y)

        # print(f"dx: {dx}, dy: {dy}")

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

def watch_for_clicks(state: CursorState, lm_list: list, mouse: MouseOutput):
    """Παρακολουθεί για gestures κλικ (π.χ. pinching) και ενημερώνει το state."""
    if not lm_list:
        return
    
    # Πρώτα, υπολογίζω την απόσταση μεταξύ του base finger και όλων των click

    base_x, base_y = landmark_pos(lm_list, config.FINGER_BASE_CLICK) 
    click_distances = {}
    for click_type, click_id in [(GestureState.LEFT, config.FINGER_LEFT_CLICK),
                                (GestureState.RIGHT, config.FINGER_RIGHT_CLICK),
                                (GestureState.MIDDLE, config.FINGER_MIDDLE_CLICK)]:
        click_x, click_y = landmark_pos(lm_list, click_id)

        # Υπολογίζω την ευκλείδια απόσταση μεταξύ του base finger και του click finger
        dist = ((click_x - base_x) ** 2 + (click_y - base_y) ** 2) ** 0.5
        click_distances[click_type] = dist
    
    # Παίρνω την ελάχιστη απόσταση και τον αντίστοιχο τύπο κλικ
    min_click_state = min(click_distances, key=click_distances.get)
    min_distance = click_distances[min_click_state]

    extrasensitivity=0
    if state.currently_holding:
        extrasensitivity= 10
    if min_distance < config.CLICK_DISTANCE_THRESHOLD + extrasensitivity:
        #print(f"Detected match with thumb and : {min_click_state.name} (distance: {min_distance:.1f})")
        state.updateClickState(min_click_state,mouse)
    else: 
        #print(f"Detected unmatch with thumb.")
        state.updateClickState(GestureState.NONE, mouse)


def main():
    mouse = init_mouse()

    # Αρχικοποίηση και εκκίνηση του Thread της κάμερας
    threaded_cam = ThreadedCamera(config.CAMERA_INDEX).start()
    
    time.sleep(0.1) #Αναμονή μέχρι να ανοίξει

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

            # Διαβάζουμε το τελευταίο frame από την κάμερα στο παράλληλο νήμα
            ret, img = threaded_cam.read()
            if not ret or img is None:
                continue # Ή break, αν έκλεισε η κάμερα

            img, lm_list = detect_landmarks(detector, img)
            img, dx, dy = process_landmarks(img, lm_list, state, controller)

            watch_for_clicks(state, lm_list, mouse)

            #print(f"FPS: {fps:.1f}, dx: {dx}, dy: {dy}, Active: {state.active}, Hand Lost: {state.hand_lost}")
            
            draw_status_bar(img, state, mouse)
            draw_fps(img, fps)
            cv2.imshow("Virtual Air Mouse", img)

            if not emit_subframes(mouse, dx, dy, t0, state, controller):
                break
    finally:
        threaded_cam.stop()
        cv2.destroyAllWindows()
        detector.close()
        mouse.close()
        if mouse.ok:
            print("[OK] Virtual mouse released.")
