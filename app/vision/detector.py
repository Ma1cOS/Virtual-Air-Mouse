# ============================================================
#  HandDetector — Ανίχνευση χεριού (MediaPipe Tasks)
# -----------------------------------------------------------
#  Λειτουργίες:
#    • Εντοπισμός χεριού και 21 landmarks (αρθρώσεις)
#    • Φιλτράρισμα κατά handedness (Right/Left/Any)
#    • Εξαγωγή συντεταγμένων σε pixel
#    • Σχεδίαση σκελετού πάνω στην εικόνα
#
#  Σημαντικό:
#    Το find_position() ΠΡΕΠΕΙ να καλείται ΜΕΤΑ την find_hands()
#    στο ίδιο καρέ — διαβάζει το self.results.
#
#  GPU delegate με αυτόματο fallback σε CPU.
# ============================================================

import os
import cv2
from mediapipe.tasks.python import vision, BaseOptions
from mediapipe.tasks.python.vision import RunningMode
from mediapipe import Image, ImageFormat

from app import config


_HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),       # αντίχειρας
    (0, 5), (5, 6), (6, 7), (7, 8),       # δείκτης
    (0, 9), (9, 10), (10, 11), (11, 12),  # μεσαίος
    (0, 13), (13, 14), (14, 15), (15, 16),# παράμεσος
    (0, 17), (17, 18), (18, 19), (19, 20),# μικρός
    (5, 9), (9, 13), (13, 17)             # παλάμη
)


def _model_path():
    return os.path.join(os.path.dirname(__file__), "models",
                        "hand_landmarker.task")


class HandDetector:
    """
    Ανιχνευτής χεριού μέσω MediaPipe Tasks (mp.tasks).

    Χρησιμοποιεί GPU delegate όταν είναι διαθέσιμη, με
    αυτόματο fallback σε CPU αν αποτύχει.

    Pipeline ανά καρέ:
        find_hands(img)   → BGR→RGB → mp.Image → detect() → σχεδίαση
        find_position(img)→ pixel conversion από self.results
    """

    def __init__(self, max_num_hands=config.MAX_NUM_HANDS,
                 min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                 min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
                 preferred_hand=config.PREFERRED_HAND):
        """
        @param max_num_hands: μέγιστος αριθμός χεριών (2 για handedness)
        @param min_detection_confidence: βεβαιότητα εντοπισμού
        @param min_tracking_confidence: βεβαιότητα παρακολούθησης
        @param preferred_hand: "Right", "Left", "Any"
        """
        self.results = None
        self.preferred_hand = preferred_hand

        for delegate in (BaseOptions.Delegate.GPU, BaseOptions.Delegate.CPU):
            try:
                options = vision.HandLandmarkerOptions(
                    base_options=BaseOptions(
                        model_asset_path=_model_path(),
                        delegate=delegate),
                    running_mode=RunningMode.IMAGE,
                    num_hands=max_num_hands,
                    min_hand_detection_confidence=min_detection_confidence,
                    min_hand_presence_confidence=min_tracking_confidence,
                    min_tracking_confidence=min_tracking_confidence)
                self._landmarker = vision.HandLandmarker.create_from_options(options)
                break
            except Exception:
                continue
        else:
            raise RuntimeError("HandLandmarker: αποτυχία δημιουργίας (GPU & CPU)")

    def close(self):
        self._landmarker.close()

    def _get_hand_index(self):
        """
        Επιστρέφει τον δείκτη του χεριού με το επιθυμητό handedness.
        Αν preferred_hand = "Any", επιστρέφει το πρώτο χέρι.

        @returns: δείκτης χεριού (int) ή None
        """
        if self.preferred_hand == "Any":
            return 0 if (self.results and self.results.hand_landmarks) else None

        if (self.results and self.results.handedness
                and self.results.hand_landmarks):
            for idx, categories in enumerate(self.results.handedness):
                label = categories[0].category_name
                if label == self.preferred_hand:
                    return idx
        return None

    def find_hands(self, img, draw=True):
        """
        Ανίχνευση χεριού και προαιρετική σχεδίαση σκελετού.

        @param img: εικόνα OpenCV (BGR)
        @param draw: σχεδίαση landmarks + συνδέσεις
        @returns: η εικόνα (τροποποιημένη αν draw=True)
        """
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = Image(image_format=ImageFormat.SRGB, data=img_rgb)
        self.results = self._landmarker.detect(mp_image)

        hand_index = self._get_hand_index()
        if draw and hand_index is not None:
            landmarks = self.results.hand_landmarks[hand_index]
            self._draw_landmarks(img, landmarks)

        return img

    def _draw_landmarks(self, img, landmarks):
        h, w, _ = img.shape

        for lm in landmarks:
            x, y = int(lm.x * w), int(lm.y * h)
            cv2.circle(img, (x, y), 4, (0, 255, 0), cv2.FILLED)

        for a, b in _HAND_CONNECTIONS:
            if a < len(landmarks) and b < len(landmarks):
                x1, y1 = int(landmarks[a].x * w), int(landmarks[a].y * h)
                x2, y2 = int(landmarks[b].x * w), int(landmarks[b].y * h)
                cv2.line(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

    def find_position(self, img, hand_no=None):
        """
        Συντεταγμένες landmarks σε pixels — από το self.results.
        Πρέπει να καλείται ΜΕΤΑ την find_hands() στο ίδιο καρέ.

        @param img: εικόνα OpenCV (για διαστάσεις)
        @param hand_no: δείκτης χεριού (None = αυτόματο)
        @returns: [[id, x, y], ...] (21 στοιχεία, κενή αν δεν βρέθηκε)
        """
        lm_list = []
        h, w, _ = img.shape

        if hand_no is None:
            hand_no = self._get_hand_index()

        if (hand_no is not None and self.results
                and self.results.hand_landmarks
                and hand_no < len(self.results.hand_landmarks)):
            hand_lms = self.results.hand_landmarks[hand_no]
            for id, lm in enumerate(hand_lms):
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append([id, cx, cy])

        return lm_list
