# ============================================================
#  CursorController: EMA smoothing pipeline
# -----------------------------------------------------------
#  Pipeline (per-frame):
#    lm_list, extract cursor finger, EMA filter, smooth_cam
#
#  SmoothingFilter: adaptive EMA
#    s_t = α·x_t + (1-α)·s_{t-1}
#    α drops to 0.1× when hand is still (< STABILITY_THRESHOLD)
# ============================================================

import numpy as np
from app import config


class SmoothingFilter:
    """
    Προσαρμοστικό φίλτρο EMA (Exponential Moving Average).

    Όταν το χέρι είναι σταθερό, το alpha μειώνεται δραστικά
    ώστε ο κέρσορας να «κλειδώνει», εξαλείφοντας το τρέμουλο.
    Σε κίνηση επιστρέφει στο κανονικό alpha για άμεση απόκριση.
    O(1) ανά καρέ.
    """

    def __init__(self, alpha=config.ALPHA,
                 stability_threshold=config.STABILITY_THRESHOLD):
        self.alpha = alpha
        self.stability_threshold = stability_threshold
        self.smoothed_x = None
        self.smoothed_y = None

    def update(self, raw_x, raw_y):
        if self.smoothed_x is None: # αρχικοποίηση με την πρώτη μέτρηση
            self.smoothed_x = raw_x
            self.smoothed_y = raw_y
            return self.smoothed_x, self.smoothed_y

        # Υπολογισμός ευκλείδιας απόστασης μεταξύ ακατέργαστων και εξομαλυμένων συντεταγμένων
        distance = np.hypot(
            raw_x - self.smoothed_x,
            raw_y - self.smoothed_y)

        # Προσαρμογή alpha: αν το χέρι είναι σταθερό (μικρή απόσταση), μειώνουμε το alpha
        alpha = self.alpha * 0.1 if distance < self.stability_threshold \
                else self.alpha

        # Το νέο smoothed σημείο είναι ο σταθμισμένος μέσος όρος των raw και smoothed σημείων
        self.smoothed_x = alpha * raw_x + (1 - alpha) * self.smoothed_x
        self.smoothed_y = alpha * raw_y + (1 - alpha) * self.smoothed_y
        return self.smoothed_x, self.smoothed_y

    def reset(self):
        self.smoothed_x = None
        self.smoothed_y = None


class CursorController:
    """
    Ελεγκτής κέρσορα, thin wrapper over EMA filter.

    Δέχεται landmarks χεριού και επιστρέφει εξομαλυμένες
    συντεταγμένες στον χώρο της κάμερας μέσω του SmoothingFilter.
    """

    def __init__(self, cursor_finger=config.CURSOR_FINGER,
                 alpha=config.ALPHA):
        self.cursor_finger = cursor_finger
        self.filter = SmoothingFilter(alpha=alpha)

    def update(self, lm_list):
        if not lm_list or len(lm_list) <= self.cursor_finger:
            return None, None
        
        # Εξαγωγή ακατέργαστων συντεταγμένων του επιλεγμένου landmark
        raw_x = lm_list[self.cursor_finger][1]
        raw_y = lm_list[self.cursor_finger][2]
        # Ενημέρωση του φίλτρου με τις ακατέργαστες συντεταγμένες και λήψη των εξομαλυμένων συντεταγμένων
        return self.filter.update(raw_x, raw_y)

    def get_display_pos(self):
        return self.filter.smoothed_x, self.filter.smoothed_y

    def reset_filter(self):
        self.filter.reset()
