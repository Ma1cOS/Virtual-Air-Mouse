"""
GUI κλάση που τρέχει σε παράλληλλο thread, ανανεώνει την εικόνα και το interface.
Επιπλέον, διαχειρίζεται τα κουμπιά της εφαρμογής όπως το start/stop του tracking του mouse με m και το κλείσιμο της εφαρμογής με q.
"""
import threading
import queue
import time
import cv2
from app import config
from app.output.mouse import MouseOutput
from app.state import CursorState
import numpy as np

_KEY_NOOP  = (-1, 255)   # waitKey returned no key
_KEY_ESC   = 27
_KEY_GREEK = (181, 230)  # μ/Μ variants on Greek keyboard layouts
_KEY_QUIT  = {'q', ';'}   # Q and common nearby key on different layouts


_HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),       # αντίχειρας
    (0, 5), (5, 6), (6, 7), (7, 8),       # δείκτης
    (0, 9), (9, 10), (10, 11), (11, 12),  # μεσαίος
    (0, 13), (13, 14), (14, 15), (15, 16),# παράμεσος
    (0, 17), (17, 18), (18, 19), (19, 20),# μικρός
    (5, 9), (9, 13), (13, 17)             # παλάμη
)

class GUIWorker:
    """"
    Τρέχει σε ξεχωριστό thread, διαχειρίζεται την εικόνα και το interface.
    """
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    state = CursorState()
    def __init__(self, pause_mouse_event,image_queue: queue.Queue, state_queue: queue.Queue):
        self.pause_mouse_event = pause_mouse_event
        self.image_queue = image_queue
        self.state_queue = state_queue
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()  # Ξεκινάει αμέσως το thread

    def _loop(self):
        while True:

            try:
                current_img = self.image_queue.get_nowait()
                self.image = current_img
            except queue.Empty:
                pass # Δεν υπήρχε νέα εικόνα, κρατάει την παλιά

            # 2. Έλεγχος για νέο state
            try:
                current_state = self.state_queue.get_nowait()
                self.state = current_state
            except queue.Empty:
                pass # Δεν υπήρχε νέο state, κρατάει το παλιό
            self.update(self.image,self.state)
             

    def handle_key(self,key):
        """Χειρίζεται 'q'=έξοδος, 'm'=toggle κέρσορα."""
        if key in _KEY_NOOP:
            return True

        low = key & 0xFF
        ch = chr(low).lower()

        if low == _KEY_ESC or ch in _KEY_QUIT:
            return False

        if ch == 'm' or low in _KEY_GREEK:
            self.pause_mouse_event.clear() if self.pause_mouse_event.is_set() else self.pause_mouse_event.set()
        return True

    def update(self,img,state):
                self.image = img
                self.state = state
                self.draw_status_bar(state)
                self.draw_fps(self.state.fps)
                self.updateDeltaLabel()
                self.draw_cursor_feedback(self.image,self.state.raw_x,self.state.raw_y,self.state.smooth_cam_x,self.state.smooth_cam_y)
                self._draw_landmarks()
                cv2.imshow("Virtual Air Mouse", img)
                #wait_ms = max(1, int(((1.0 / config.FRAME_TARGET) - elapsed) * 1000))
                #sub_wait = max(1, wait_ms // sub)
                #key = cv2.waitKey(sub_wait) & 0xFF
                key = cv2.waitKey(1) & 0xFF
                self.handle_key(key)

    def getIsMouseActive(self):
         return self.state.active            

    def stop(self):
            cv2.destroyAllWindows()
    
    """
    Συναρτήσεις οπτικής ανατροφοδότησης (drawing) πάνω στην εικόνα της κάμερας.
    """
    
    def updateDeltaLabel(self):
                cv2.putText(self.image, f"Delta: ({self.state.last_dx}, {self.state.last_dy})",
                            (20, 110), cv2.FONT_HERSHEY_PLAIN, 1.1,
                            (0, 255, 255) if self.state.active else (128, 128, 128), 2)



    def draw_cursor_feedback(self, img, raw_x, raw_y, smooth_cam_x, smooth_cam_y):
        """
        Σχεδιάζει: πράσινος κύκλος = raw, κόκκινος = smooth, κίτρινη γραμμή.

        @param img: εικόνα OpenCV (BGR)
        @param raw_x, raw_y: ακατέργαστη θέση στην κάμερα
        @param smooth_cam_x, smooth_cam_y: εξομαλυμένη θέση στην κάμερα
        """
        
        if None in (raw_x, raw_y, smooth_cam_x, smooth_cam_y):
            return
        smooth_cam_x = int(smooth_cam_x)
        smooth_cam_y = int(smooth_cam_y)

        cv2.circle(img, (raw_x, raw_y), 8, (0, 255, 0), 2)
        cv2.circle(img, (smooth_cam_x, smooth_cam_y), 8, (0, 0, 255), -1)
        cv2.line(img, (raw_x, raw_y), (smooth_cam_x, smooth_cam_y), (255, 255, 0), 1)


    def draw_status_bar(self, state):
        """
        Γραμμή κατάστασης: UNAVAILABLE / ON / OFF.

        @param img: εικόνα OpenCV (BGR)
        @param state: CursorState
        @param mouse: MouseOutput
        """
        #if not mouse.ok:
        #    status, color = "UNAVAILABLE", (0, 0, 255)
        if state.active:
            status, color = "ON", (0, 255, 0)
        else:
            status, color = "OFF", (0, 0, 255)
        cv2.putText(self.image, f"Mouse: {status}", (20, 50),
                    cv2.FONT_HERSHEY_PLAIN, 2, color, 2)


    def draw_fps(self, fps):
        """
        Ένδειξη FPS πάνω δεξιά. Πράσινο ≥20, πορτοκαλί 10-19, κόκκινο <10.

        @param img: εικόνα OpenCV (BGR)
        @param fps: τιμή FPS (float)
        """
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
