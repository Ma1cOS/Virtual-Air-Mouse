
import threading
import time
import cv2
from app import config

class ThreadedCamera:
    def __init__(self, camera_index):
        self.cap = self.init_camera(camera_index)
        self.ret = False
        self.frame = None
        self.started = False
        self.read_lock = threading.Lock()
    
    def init_camera(self, index=0):
        """Άνοιγμα κάμερας με MJPG codec. Επιστρέφει capture source ή None."""
        cap = cv2.VideoCapture(index)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        if not cap.isOpened():
            print("No camera found.")
            cap.release()
            return None
        return cap


    def grab_frame(self, cap):
        """Λήψη frame από κάμερα + οριζόντιο mirror."""
        success, img = cap.read()
        if not success:
            return None
        return cv2.flip(img, 1)
        
    def start(self):
        if self.started:
            return self
        self.started = True
        # thread που τρέχει τη συνάρτηση update συνεχώς
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True  # Κλείνει αυτόματα όταν κλείσει η main
        self.thread.start()
        return self

    def update(self):
        while self.started:
            img = self.grab_frame(self.cap)
            
            with self.read_lock:
                if img is not None:
                    self.frame = img
                    self.ret = True
                else:
                    self.ret = False
            
            time.sleep(config.CAMERA_POLL_SLEEP)

    def read(self):
        with self.read_lock:
            # Επιστρέφει άμεσα το τελευταίο frame που αποθηκεύτηκε
            return self.ret, self.frame

    def stop(self):
        self.started = False
        if self.thread.is_alive():
            self.thread.join()
        if self.cap is not None:
            self.cap.release()
