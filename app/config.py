# ============================================================
#  Config: κεντρικές ρυθμίσεις
# -----------------------------------------------------------
#  Κάθε παράμετρος της εφαρμογής ορίζεται εδώ.
#  Τα modules διαβάζουν τις τιμές μέσω `from app import config`.
#  Τροποποίησε και επανεκκίνησε.
# ============================================================

# ---- Κάμερα ------------------------------------------
CAMERA_INDEX = 0    # /dev/video0
FRAME_TARGET = 60   # fps-στόχος (και ρυθμός poll κάμερας)

# ---- Ανίχνευση χεριού (MediaPipe) --------------------
MAX_NUM_HANDS            = 1      # απαιτείται 2 για σωστό handedness
MIN_DETECTION_CONFIDENCE = 0.7    # ελάχιστη βεβαιότητα εντοπισμού
MIN_TRACKING_CONFIDENCE  = 0.4    # ελάχιστη βεβαιότητα παρακολούθησης
PREFERRED_HAND           = "Left" # "Right" | "Left" | "Any"

# ---- Αντιστοίχιση Landmarks --------------------------
CURSOR_FINGER       = 0   # landmark ID κέρσορα (0 = κάτω άκρη παλάμης)
FINGER_BASE_CLICK   = 4   # landmark ID βάσης κλικ (4 = άκρη αντίχειρα)
FINGER_LEFT_CLICK   = 8   # landmark ID αριστερού κλικ (8 = άκρη δείκτη)
FINGER_RIGHT_CLICK  = 12  # landmark ID δεξιού κλικ (12 = άκρη μεσαίου)
FINGER_MIDDLE_CLICK = 16  # landmark ID μεσαίου κλικ (16 = άκρη παράμεσου)

# ---- Εξομάλυνση (EMA) --------------------------------
ALPHA               = 0.12  # συντελεστής EMA κέρσορα (μικρότερος = πιο ομαλό)
CLICK_ALPHA         = 0.50  # συντελεστής EMA για click fingers (μεγαλύτερος = πιο άμεσο)
STABILITY_THRESHOLD = 15.0  # pixels κάμερας, κατώφλι κλειδώματος
STABILITY_REDUCTION = 0.1   # πολλαπλασιαστής alpha όταν το χέρι είναι σταθερό

# ---- Χειρονομίες / Κλικ ------------------------------
CLICK_DISTANCE_THRESHOLD = 40.0  # pixels απόστασης μεταξύ base και click finger για κλικ
TIME_TO_CLICK            = 0.2   # sec που πρέπει να διατηρείται το gesture για απλό κλικ
TIME_TO_HOLD             = 0.4   # sec που πρέπει να διατηρείται το gesture για hold/drag
HOLD_HYSTERESIS          = 5     # extra pixels ανοχής στο click threshold κατά το hold

# ---- Κέρσορας (evdev) --------------------------------
DELTA_SCALE          = 4.0  # camera-pixel σε REL units (>1 = ταχύτερα)
VELOCITY_HOLD_FRAMES = 1    # frames επανάληψης τελευταίου delta όταν χάνεται το χέρι
HAND_LOST_TIMEOUT    = 0.5  # sec μέχρι να θεωρηθεί χαμένο το χέρι

# ---- FPS ---------------------------------------------
FPS_SMOOTHING = 0.9  # βάρος EMA για rolling FPS counter