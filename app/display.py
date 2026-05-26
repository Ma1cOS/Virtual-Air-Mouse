"""
Συναρτήσεις οπτικής ανατροφοδότησης (drawing) πάνω στην εικόνα της κάμερας.
"""
import cv2


def landmark_pos(lm_list, finger_id):
    """
    Επιστρέφει τις (x, y) συντεταγμένες ενός landmark από τη λίστα.

    @param lm_list: [[id, x, y], ...]
    @param finger_id: ID ορόσημου (π.χ. 8 = δείκτης)
    @returns: (x, y)
    """
    return lm_list[finger_id][1], lm_list[finger_id][2]


def draw_cursor_feedback(img, raw_x, raw_y, smooth_cam_x, smooth_cam_y):
    """
    Σχεδιάζει: πράσινος κύκλος = raw, κόκκινος = smooth, κίτρινη γραμμή.

    @param img: εικόνα OpenCV (BGR)
    @param raw_x, raw_y: ακατέργαστη θέση στην κάμερα
    @param smooth_cam_x, smooth_cam_y: εξομαλυμένη θέση στην κάμερα
    """
    cv2.circle(img, (raw_x, raw_y), 8, (0, 255, 0), 2)
    cv2.circle(img, (smooth_cam_x, smooth_cam_y), 8, (0, 0, 255), -1)
    cv2.line(img, (raw_x, raw_y), (smooth_cam_x, smooth_cam_y), (255, 255, 0), 1)


def draw_status_bar(img, state, mouse):
    """
    Γραμμή κατάστασης: ON / OFF / UNAVAILABLE.

    @param img: εικόνα OpenCV (BGR)
    @param state: CursorState
    @param mouse: MouseOutput
    """
    if state.active:
        status = "ON"
        color = (0, 255, 0)
    else:
        status = "OFF"
        color = (0, 0, 255)
    if not mouse.ok:
        status = "UNAVAILABLE"
        color = (0, 0, 255)
    cv2.putText(img, f"Mouse: {status}", (20, 50),
                cv2.FONT_HERSHEY_PLAIN, 2, color, 2)


def draw_fps(img, fps):
    """
    Ένδειξη FPS πάνω δεξιά. Πράσινο ≥20, πορτοκαλί 10-19, κόκκινο <10.

    @param img: εικόνα OpenCV (BGR)
    @param fps: τιμή FPS (float)
    """
    cv2.putText(img, f"FPS: {fps:.0f}",
                (img.shape[1] - 120, 50), cv2.FONT_HERSHEY_PLAIN, 1.5,
                (0, 255, 0) if fps >= 20 else (0, 165, 255) if fps >= 10 else (0, 0, 255), 2)
