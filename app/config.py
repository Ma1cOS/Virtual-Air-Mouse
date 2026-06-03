# ============================================================
#  Config: κεντρικές ρυθμίσεις
# -----------------------------------------------------------
#  Κάθε παράμετρος της εφαρμογής ορίζεται εδώ.
#  Τα modules διαβάζουν τις τιμές μέσω `from app import config`.
#  Τροποποίησε και επανεκκίνησε.
# ============================================================

# ---- Κάμερα ------------------------------
CAMERA_INDEX = 0          # /dev/video0
FRAME_TARGET = 60         # fps-στόχος

# ---- Ανίχνευση χεριού (MediaPipe) --------
MAX_NUM_HANDS            = 1      # απαιτείται 2 για σωστό handedness
MIN_DETECTION_CONFIDENCE = 0.7    # ελάχιστη βεβαιότητα εντοπισμού
MIN_TRACKING_CONFIDENCE  = 0.4    # ελάχιστη βεβαιότητα παρακολούθησης
PREFERRED_HAND           = "Left" # "Right" | "Left" | "Any"

# ---- Εξομάλυνση (EMA) --------------------
ALPHA              = 0.12  # συντελεστής EMA κέρσορα (μικρότερος = πιο ομαλό)
CLICK_ALPHA        = 0.50  # συντελεστής EMA για click fingers (μεγαλύτερος = πιο άμεσο)
STABILITY_THRESHOLD = 15.0  # pixels κάμερας, κατώφλι κλειδώματος
CURSOR_FINGER      = 0     # landmark ID (0= κάτω άκρη παλάμης)
FINGER_BASE_CLICK = 4    # landmark ID για ανίχνευση κλικ βάσης (συνδυάζεται με τα παρακάτω) (π.χ. 4 = άκρη αντίχειρα)
FINGER_LEFT_CLICK = 8     # landmark ID για ανίχνευση κλικ (π.χ. 8 = άκρη δείκτη)
FINGER_RIGHT_CLICK = 12   # landmark ID για ανίχνευση δεξιού κλικ (π.χ. 12 = άκρη μεσαίου)
FINGER_MIDDLE_CLICK = 16  # landmark ID για ανίχνευση μεσαίου κλικ (π.χ. 16 = άκρη παράμεσου)
CLICK_DISTANCE_THRESHOLD = 40.0  # η απόσταση σε pixels μεταξύ του base finger και των click fingers για να θεωρηθεί κλικ
TIME_TO_CLICK = 0.2  # δευτερόλεπτα που πρέπει να διατηρείται το gesture για να εκτελεστεί το κλικ
TIME_TO_HOLD = 0.4  # δευτερόλεπτα που πρέπει να διατηρείται το gesture για να θεωρηθεί "hold" (παρατεταμένο κλικ) 

# ---- Κέρσορας (evdev) --------------------

DELTA_SCALE          = 4.0   # camera-pixel σε REL units (>1 = ταχύτερα)
VELOCITY_HOLD_FRAMES = 1     # frames επανάληψης τελευταίου delta όταν χάνεται το χέρι
HAND_LOST_TIMEOUT    = 0.5   # δευτερόλεπτα μέχρι να θεωρηθεί χαμένο το χέρι
MOVE_DEAD_ZONE       = 1     # ελάχιστη κίνηση σε REL units για αποστολή event (κόβει θόρυβο)

# ---- Timing / calibration --------------------

FPS_SMOOTHING        = 0.9   # βάρος EMA για rolling FPS counter
STABILITY_REDUCTION  = 0.1   # πολλαπλασιαστής alpha όταν το χέρι είναι σταθερό
HOLD_HYSTERESIS      = 5     # extra pixels ανοχής στο click threshold κατά το hold
CAMERA_POLL_SLEEP    = 0.016 # sec ύπνου στο camera thread (~62Hz poll rate)
