# ============================================================
#  Main: ενορχηστρωτής κύριου βρόχου
# ============================================================

import threading
import time
from app import config
from app.gui import GUIWorker
from app.state import CursorState
from app.vision import HandDetector
from app.smoothing import CursorController
from app.output import MouseOutput
from app.input import ThreadedCamera

from app.state import GestureState



import queue




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
        if abs(cam_dx) < config.CAM_DEAD_ZONE and abs(cam_dy) < config.CAM_DEAD_ZONE:
            state.accum_x = 0.0
            state.accum_y = 0.0
        else:
            state.accum_x += cam_dx * config.DELTA_SCALE
            state.accum_y += cam_dy * config.DELTA_SCALE
            dx, state.accum_x = _split_int(state.accum_x)
            dy, state.accum_y = _split_int(state.accum_y)
        

        #print(f"With Delta and split_int which does: ({dx}, {dy})")

    state.prev_x = smooth_cam_x
    state.prev_y = smooth_cam_y
    return dx, dy

def landmark_pos(lm_list, finger_id):
        """
        Επιστρέφει τις (x, y) συντεταγμένες ενός landmark από τη λίστα.

        @param lm_list: [[id, x, y], ...]
        @param finger_id: ID ορόσημου (π.χ. 8 = δείκτης)
        @returns: (x, y)
        """
        return lm_list[finger_id][1], lm_list[finger_id][2]

def process_landmarks(lm_list, state, controller):
    """
    Διαχείριση landmark detection, EMA smoothing, movement, και
    drawing με οπτική ανατροφοδότηση.

    @param img: τρέχον frame
    @param lm_list: λίστα landmarks
    @param state: CursorState
    @param controller: CursorController
    @returns: (img, dx, dy)
    """
    state.dx = state.dy = 0

    if lm_list:
        state.last_seen = time.time()
        state.hold_frames = 0

        if state.hand_lost:
            handle_reacquire(state, controller)

        state.smooth_cam_x, state.smooth_cam_y = controller.update(lm_list)

        filtered = controller.update_click_points(lm_list)
        if filtered is not None:
            (state.filtered_base_x, state.filtered_base_y), \
            (state.filtered_left_x, state.filtered_left_y), \
            (state.filtered_right_x, state.filtered_right_y), \
            (state.filtered_middle_x, state.filtered_middle_y) = filtered

        # Εύρεση της μεταβολής (dx, dy) σε relative units με sub-pixel accumulation
        if state.smooth_cam_x is not None:
            state.dx, state.dy = compute_movement(state, state.smooth_cam_x, state.smooth_cam_y)

        # print(f"dx: {dx}, dy: {dy}")

        state.last_dx = state.dx
        state.last_dy = state.dy

        state.raw_x, state.raw_y = landmark_pos(lm_list, config.CURSOR_FINGER)
        state.display_x, state.display_y = controller.get_display_pos()
        if state.display_x is not None:
            state.display_x, state.display_y = int(state.display_x), int(state.display_y)


        
    else:
        state.hold_frames += 1
        if state.hold_frames <= config.VELOCITY_HOLD_FRAMES:
            state.dx, state.dy = state.last_dx, state.last_dy
        if time.time() - state.last_seen > config.HAND_LOST_TIMEOUT and not state.hand_lost:
            state.hand_lost = True

    return state


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



def detect_landmarks(detector, img,state):
    """Ανίχνευση χεριού + εξαγωγή συντεταγμένων."""
    img,landmarks = detector.find_hands(img)
    lm_list = detector.find_position(img)
    state.landmarks = landmarks
    state.lm_list = lm_list
    return img


def emit_subframes(mouse, dx, dy):
    """
    Σπάσιμο (dx, dy) σε sub-frames με τοπικό accumulator.
    Στέλνει REL events μόνο όταν υπάρχει αξιοσημείωτη κίνηση.
    """
    if dx == 0 and dy == 0:
        return

    sub = config.MOUSE_SUBDIVISIONS
    total = abs(dx) + abs(dy)
    if total < config.MOVE_DEAD_ZONE:
        return

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

def watch_for_clicks(state: CursorState, lm_list: list, mouse: MouseOutput):
    """Παρακολουθεί για gestures κλικ (π.χ. pinching) και ενημερώνει το state."""
    if not lm_list:
        if state.currently_holding:
            mouse.set_click_state(state.currently_holding_state, down=False)
            state.currently_holding = False
            state.thumb_connection = None
        return

    if None in (state.filtered_base_x, state.filtered_left_x,
                state.filtered_right_x, state.filtered_middle_x):
        return

    base_x, base_y = state.filtered_base_x, state.filtered_base_y

    click_positions = {
        GestureState.LEFT: (state.filtered_left_x, state.filtered_left_y),
        GestureState.RIGHT: (state.filtered_right_x, state.filtered_right_y),
        GestureState.MIDDLE: (state.filtered_middle_x, state.filtered_middle_y),
    }

    click_distances = {}
    for click_type, (click_x, click_y) in click_positions.items():
        dist = ((click_x - base_x) ** 2 + (click_y - base_y) ** 2) ** 0.5
        click_distances[click_type] = dist
    
    # Παίρνω την ελάχιστη απόσταση και τον αντίστοιχο τύπο κλικ
    min_click_state = min(click_distances, key=click_distances.get)
    min_distance = click_distances[min_click_state]

    extrasensitivity=0
    if state.currently_holding:
        extrasensitivity= 5
    if min_distance < config.CLICK_DISTANCE_THRESHOLD + extrasensitivity:
        #print(f"Detected match with thumb and : {min_click_state.name} (distance: {min_distance:.1f})")
        state.updateClickState(min_click_state,mouse)
    else: 
        #print(f"Detected unmatch with thumb.")
        state.updateClickState(GestureState.NONE, mouse)


def main():
    # Δημιουργία ουράς που κρατάει μόνο 1 αντικείμενο τη φορά
    image_queue = queue.Queue(maxsize=1)
    state_queue = queue.Queue(maxsize=1)

    mouse = init_mouse()

    # Αρχικοποίηση και εκκίνηση του Thread της κάμερας
    threaded_cam = ThreadedCamera(config.CAMERA_INDEX).start()
    
    time.sleep(0.1) #Αναμονή μέχρι να ανοίξει

    detector = HandDetector()
    controller = CursorController()
    state = CursorState()

    state.fps = 0.0
    prev_time = 0.0

    pause_mouse_event = threading.Event()
    pause_mouse_event.set()  # ξεκινάει paused/OFF
    quit_event = threading.Event()
    gui_worker = GUIWorker(pause_mouse_event, quit_event, image_queue, state_queue)

    
    TARGET_FPS = config.FRAME_TARGET
    FRAME_DURATION = 1.0 / TARGET_FPS

    # ------------- Κύριος βρόχος -----------------
    try:
        while True:
            if quit_event.is_set():
                break
            t0 = time.time()
            if prev_time > 0:
                state.fps = 0.9 * state.fps + 0.1 * (1.0 / (t0 - prev_time))
            

            # Διαβάζουμε το τελευταίο frame από την κάμερα στο παράλληλο νήμα
            ret, img = threaded_cam.read()
            if not ret or img is None:
                continue # Ή break, αν έκλεισε η κάμερα

            img = detect_landmarks(detector, img, state)
            state = process_landmarks(state.lm_list, state, controller)

            
            # Ενημέρωση GUI μέσω των ουρών (κρατάει μόνο το τελευταίο frame)
            if not image_queue.empty():
                try: image_queue.get_nowait()
                except queue.Empty: pass
            image_queue.put(img)

            # Ενημέρωση state στην GUI μέσω της ουράς (κρατάει μόνο το τελευταίο state)
            if not state_queue.empty():
                try: state_queue.get_nowait()
                except queue.Empty: pass
            state_queue.put(state)

            #print(f"FPS: {fps:.1f}, dx: {dx}, dy: {dy}, Active: {state.active}, Hand Lost: {state.hand_lost}")
            
            if not pause_mouse_event.is_set(): # Αν το mouse δεν ειναι paused
                state.active = True
                watch_for_clicks(state, state.lm_list, mouse)
                emit_subframes(mouse, state.dx, state.dy)
            else:
                state.active = False
                if state.currently_holding:
                    mouse.set_click_state(state.currently_holding_state, down=False)
                    state.currently_holding = False
                    state.thumb_connection = None
    

            # Πόση ώρα πέρασε από την αρχή του loop
            elapsed_in_loop = time.time() - t0
            sleep_time = FRAME_DURATION - elapsed_in_loop
            
            if sleep_time > 0:
                time.sleep(sleep_time) # Τεχνητή καθυστέρηση για να ματσάρουμε τα fps
                
            
            prev_time = t0  # Αποθήκευση του χρόνου έναρξης του loop  
                
    finally:
        threaded_cam.stop()
        gui_worker.stop()
        
        detector.close()
        mouse.close()
        if mouse.ok:
            print("[OK] Virtual mouse released.")
