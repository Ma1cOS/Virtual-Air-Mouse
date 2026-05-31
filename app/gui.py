"""
GUI κλάση που τρέχει σε παράλληλλο thread, ανανεώνει την εικόνα και το interface.
Επιπλέον, διαχειρίζεται τα κουμπιά της εφαρμογής όπως το start/stop του tracking του mouse με m και το κλείσιμο της εφαρμογής με q.
"""

import cv2
from app import config
_KEY_NOOP  = (-1, 255)   # waitKey returned no key
_KEY_ESC   = 27
_KEY_GREEK = (181, 230)  # μ/Μ variants on Greek keyboard layouts
_KEY_QUIT  = {'q', ';'}   # Q and common nearby key on different layouts

class GUIWorker:
    image = 0

    def __init__(self):
         pass

    def handle_key(self,key):
        """Χειρίζεται 'q'=έξοδος, 'm'=toggle κέρσορα."""
        if key in _KEY_NOOP:
            return True

        low = key & 0xFF
        ch = chr(low).lower()

        if low == _KEY_ESC or ch in _KEY_QUIT:
            return False

        if ch == 'm' or low in _KEY_GREEK:
            self.state.active = not self.state.active
        
            self.state.prev_x = None
            self.state.prev_y = None
            self.state.accum_x = 0.0
            self.state.accum_y = 0.0
            #controller.reset_filter()  
            #print(f"Mouse: {'ON' if state.active else 'OFF'}")
        return True

    def update(self,img,state,mouse,fps,controller):
                self.image = img
                self.state = state
                self.draw_status_bar(self.image, state, mouse)
                self.draw_fps(self.image, fps)
                self.updateDeltaLabel()
                self.draw_cursor_feedback(self.image,self.state.raw_x,self.state.raw_y,self.state.smooth_cam_x,self.state.smooth_cam_y)
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


    def draw_status_bar(self, img, state, mouse):
        """
        Γραμμή κατάστασης: UNAVAILABLE / ON / OFF.

        @param img: εικόνα OpenCV (BGR)
        @param state: CursorState
        @param mouse: MouseOutput
        """
        if not mouse.ok:
            status, color = "UNAVAILABLE", (0, 0, 255)
        elif state.active:
            status, color = "ON", (0, 255, 0)
        else:
            status, color = "OFF", (0, 0, 255)
        cv2.putText(self.image, f"Mouse: {status}", (20, 50),
                    cv2.FONT_HERSHEY_PLAIN, 2, color, 2)


    def draw_fps(self, img, fps):
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
        cv2.putText(img, f"FPS: {fps:.0f}",
                    (img.shape[1] - 120, 50), cv2.FONT_HERSHEY_PLAIN, 1.5, color, 2)
    
