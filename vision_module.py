import cv2
import mediapipe as mp

class HandDetector:
    def __init__(self):
        # Χρησιμοποιούμε απευθείας το mp.solutions
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )

    def find_hands(self, img):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.hands.process(img_rgb)
        
        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    img, 
                    hand_lms, 
                    self.mp_hands.HAND_CONNECTIONS
                )
        return img

def main():
    # Δοκίμασε το 0, αν δεν ανοίγει η κάμερα δοκίμασε 1 ή 2
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Σφάλμα: Δεν βρέθηκε κάμερα.")
        return

    detector = HandDetector()

    while True:
        success, img = cap.read()
        if not success:
            print("Αποτυχία λήψης καρέ.")
            break

        img = cv2.flip(img, 1)
        img = detector.find_hands(img)

        cv2.imshow("Vision Module - Member 1", img)
        
        # Κλείνει με το πλήκτρο 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()