import threading
import time
import queue

from app import config
from app.gui import GUIWorker
from app.state import CursorState
from app.vision import HandDetector
from app.smoothing import CursorController
from app.output import MouseOutput
from app.input import ThreadedCamera
from app.gestures import watch_for_clicks, release_hold
from app.utils import split_int, landmark_pos


def handle_reacquire(state, controller):
    controller.reset_filter()
    state.hand_lost = False
    state.prev_x = None
    state.prev_y = None
    state.accum_x = 0.0
    state.accum_y = 0.0


def compute_movement(state, smooth_x, smooth_y):
    dx = dy = 0
    if state.active and state.prev_x is not None:
        cam_dx = smooth_x - state.prev_x
        cam_dy = smooth_y - state.prev_y
        if abs(cam_dx) < config.CAM_DEAD_ZONE and abs(cam_dy) < config.CAM_DEAD_ZONE:
            state.accum_x = 0.0
            state.accum_y = 0.0
        else:
            state.accum_x += cam_dx * config.DELTA_SCALE
            state.accum_y += cam_dy * config.DELTA_SCALE
            dx, state.accum_x = split_int(state.accum_x)
            dy, state.accum_y = split_int(state.accum_y)

    state.prev_x = smooth_x
    state.prev_y = smooth_y
    return dx, dy


def process_landmarks(lm_list, state, controller):
    state.dx = state.dy = 0

    if lm_list:
        state.last_seen = time.time()
        state.hold_frames = 0

        if state.hand_lost:
            handle_reacquire(state, controller)

        state.smooth_cam_x, state.smooth_cam_y = controller.update(lm_list)

        filtered = controller.update_click_points(lm_list)
        if filtered is not None:
            if state.smooth_cam_x is not None:
                filtered[config.CURSOR_FINGER] = (state.smooth_cam_x, state.smooth_cam_y)
            state.filtered_positions = filtered

        if state.smooth_cam_x is not None:
            state.dx, state.dy = compute_movement(state, state.smooth_cam_x, state.smooth_cam_y)

        state.last_dx = state.dx
        state.last_dy = state.dy

        state.raw_x, state.raw_y = landmark_pos(lm_list, config.CURSOR_FINGER)

    else:
        state.hold_frames += 1
        if state.hold_frames <= config.VELOCITY_HOLD_FRAMES:
            state.dx, state.dy = state.last_dx, state.last_dy
        if time.time() - state.last_seen > config.HAND_LOST_TIMEOUT and not state.hand_lost:
            state.hand_lost = True


def init_mouse():
    mouse = MouseOutput()
    if not mouse.ok:
        print("[!] evdev not available")
        print("    pip install evdev, user in 'uinput' group")
        print()
    else:
        print(f"[OK] Virtual mouse: {mouse.device_path}")
    return mouse


def detect_landmarks(detector, img, state):
    img, landmarks = detector.find_hands(img)
    lm_list = detector.find_position(img)
    state.landmarks = landmarks
    state.lm_list = lm_list
    return img


def main():
    image_queue = queue.Queue(maxsize=1)
    state_queue = queue.Queue(maxsize=1)

    mouse = init_mouse()

    threaded_cam = ThreadedCamera(config.CAMERA_INDEX).start()
    time.sleep(0.1)

    detector = HandDetector()
    controller = CursorController()
    state = CursorState()

    state.fps = 0.0
    prev_time = 0.0

    pause_event = threading.Event()
    pause_event.set()
    quit_event = threading.Event()
    gui_worker = GUIWorker(pause_event, quit_event, image_queue, state_queue)

    TARGET_FPS = config.FRAME_TARGET
    FRAME_DURATION = 1.0 / TARGET_FPS

    try:
        while True:
            if quit_event.is_set():
                break
            t0 = time.time()
            if prev_time > 0:
                state.fps = 0.9 * state.fps + 0.1 * (1.0 / (t0 - prev_time))

            ret, img = threaded_cam.read()
            if not ret or img is None:
                continue

            img = detect_landmarks(detector, img, state)
            process_landmarks(state.lm_list, state, controller)

            if not image_queue.empty():
                try:
                    image_queue.get_nowait()
                except queue.Empty:
                    pass
            image_queue.put(img)

            if not state_queue.empty():
                try:
                    state_queue.get_nowait()
                except queue.Empty:
                    pass
            state_queue.put(state)

            if not pause_event.is_set():
                state.active = True
                watch_for_clicks(state, state.lm_list, mouse)
                dx, dy = state.dx, state.dy
                if dx or dy:
                    if abs(dx) + abs(dy) >= config.MOVE_DEAD_ZONE:
                        mouse.move(dx, dy)
            else:
                state.active = False
                release_hold(state, mouse)

            elapsed = time.time() - t0
            sleep_time = FRAME_DURATION - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

            prev_time = t0

    finally:
        threaded_cam.stop()
        gui_worker.stop()
        detector.close()
        mouse.close()
        if mouse.ok:
            print("[OK] Virtual mouse released.")
