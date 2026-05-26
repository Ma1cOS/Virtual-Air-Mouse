"""
Mutable κατάσταση κέρσορα που ενημερώνεται σε κάθε καρέ.

Πεδία:
    active (bool)       – αν η κίνηση κέρσορα είναι ενεργοποιημένη
    prev_x (float|None) – προηγούμενη θέση X στην κάμερα (EMA smoothed)
    prev_y (float|None) – προηγούμενη θέση Y στην κάμερα (EMA smoothed)
    hand_lost (bool)    – αν το χέρι έχει χαθεί επιβεβαιωμένα
    last_seen (float)   – timestamp τελευταίας ανίχνευσης χεριού
    hold_frames (int)   – frames που το χέρι λείπει (velocity hold)
    last_dx (int)       – τελευταίο γνωστό delta X (για velocity hold)
    last_dy (int)       – τελευταίο γνωστό delta Y (για velocity hold)
    accum_x (float)     – sub-pixel accumulator X
    accum_y (float)     – sub-pixel accumulator Y
"""


class CursorState:
    def __init__(self):
        self.active = False
        self.prev_x = None
        self.prev_y = None
        self.hand_lost = True
        self.last_seen = 0.0
        self.hold_frames = 0
        self.last_dx = 0
        self.last_dy = 0
        self.accum_x = 0.0
        self.accum_y = 0.0
