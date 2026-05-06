import cv2
import mediapipe as mp
import time
import math

class HandDetector:
    def __init__(self):
        # Χρησιμοποιούμε απευθείας το mp.solutions
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            # 0 for no hand, 1 for one hand, 2 fro both hands
            max_num_hands=1,
            # gia na trejei me perissotera fps 
            model_complexity=0,
            # the system has to be at least 70% sure its a hand before it starts mapping it
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )


    # Finding the hand 
    def find_hands(self, img):
        # Converting colour for the camera (bgr of cv2 to rbg of camera)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        #trying to find the hand by the img_rgb we converted
        self.results = self.hands.process(img_rgb)
        
        if self.results.multi_hand_landmarks:
            #pass
            for hand_lms in self.results.multi_hand_landmarks:
                # if the hand is found, we draw the connections
                self.mp_draw.draw_landmarks(img, hand_lms, self.mp_hands.HAND_CONNECTIONS)
        return img
    
    def find_position(self, img):
        lm_list = []
        if self.results.multi_hand_landmarks:
            my_hand = self.results.multi_hand_landmarks[0]
            for id, lm in enumerate(my_hand.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append([id, cx, cy])
        return lm_list

def main():
    # Δοκίμασε το 0, αν δεν ανοίγει η κάμερα δοκίμασε 1 ή 2
    cap = cv2.VideoCapture(0)
    # blepw thn analush ths kameras
    # width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    # height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    # print(f"Ανάλυση Κάμερας: {width}x{height}")
    
    # Μεταβλητές για τον υπολογισμό FPS
    pTime = 0
    cTime = 0
    
    if not cap.isOpened():
        print("Σφάλμα: Δεν βρέθηκε κάμερα.")
        return

    detector = HandDetector()

    while True:
        success, img = cap.read()
        if not success: break

        img = cv2.flip(img, 1)
        img = detector.find_hands(img)
        lm_list = detector.find_position(img)

        if len(lm_list) != 0:
            # Σημεία ενδιαφέροντος
            x4, y4 = lm_list[4][1], lm_list[4][2]   # Αντίχειρας
            x8, y8 = lm_list[8][1], lm_list[8][2]   # Δείκτης
            x12, y12 = lm_list[12][1], lm_list[12][2] # Μεσαίος

            # Σχεδίαση κύκλων στα 3 βασικά δάκτυλα
            cv2.circle(img, (x4, y4), 10, (0, 255, 255), cv2.FILLED) # Κίτρινο
            cv2.circle(img, (x8, y8), 10, (0, 255, 0), cv2.FILLED)   # Πράσινο
            cv2.circle(img, (x12, y12), 10, (255, 0, 0), cv2.FILLED) # Μπλε

            # Παράδειγμα υπολογισμού απόστασης (για το Μέλος 3)
            distance = math.hypot(x8 - x4, y8 - y4)
            if distance < 30: # Αν "τσιμπήσεις" τον δείκτη
                cv2.circle(img, (x8, y8), 15, (0, 0, 255), cv2.FILLED) # Γίνεται κόκκινο

        # Υπολογισμός και εμφάνιση FPS
        cTime = time.time()
        fps = 1 / (cTime - pTime)
        pTime = cTime
        cv2.putText(img, f'FPS: {int(fps)}', (20, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 255), 2)

        cv2.imshow("Vision Test - 3 Fingers", img)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()