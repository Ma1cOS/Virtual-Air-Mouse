# ============================================================
#  Config: κεντρικές ρυθμίσεις
# -----------------------------------------------------------
#  Κάθε παράμετρος της εφαρμογής ορίζεται εδώ.
#  Τα modules διαβάζουν τις τιμές μέσω `from app import config`.
#  Τροποποίησε και επανεκκίνησε.
# ============================================================

# ---- Κάμερα ------------------------------
CAMERA_INDEX = 0          # /dev/video0
FRAME_TARGET = 30         # fps-στόχος

# ---- Ανίχνευση χεριού (MediaPipe) --------
MAX_NUM_HANDS            = 2      # απαιτείται 2 για σωστό handedness
MIN_DETECTION_CONFIDENCE = 0.7    # ελάχιστη βεβαιότητα εντοπισμού
MIN_TRACKING_CONFIDENCE  = 0.4    # ελάχιστη βεβαιότητα παρακολούθησης
PREFERRED_HAND           = "Left" # "Right" | "Left" | "Any"

# ---- Εξομάλυνση (EMA) --------------------
ALPHA              = 0.20  # συντελεστής EMA (μικρότερος = πιο ομαλό)
STABILITY_THRESHOLD = 15.0  # pixels κάμερας, κατώφλι κλειδώματος
CURSOR_FINGER      = 8     # landmark ID (8 = άκρη δείκτη)

# ---- Κέρσορας (evdev) --------------------
DELTA_SCALE          = 4.0   # camera-pixel σε REL units (>1 = ταχύτερα)
VELOCITY_HOLD_FRAMES = 4     # frames επανάληψης τελευταίου delta όταν χάνεται το χέρι
HAND_LOST_TIMEOUT    = 1.5   # δευτερόλεπτα μέχρι να θεωρηθεί χαμένο το χέρι
MOUSE_SUBDIVISIONS   = 4     # υπο-βήματα κίνησης ανά frame (×FRAME_TARGET = update rate)
