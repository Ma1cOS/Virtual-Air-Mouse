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
from enum import Enum, auto
from time import time
from app import config

class GestureState(Enum):
    NONE = auto()    
    LEFT = auto()   
    RIGHT = auto()   
    MIDDLE = auto() 

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

        self.raw_x = 0
        self.raw_y = 0

        self.smooth_cam_x = 0
        self.smooth_cam_y = 0

        self.accum_x = 0.0
        self.accum_y = 0.0
        self.thumb_connection: GestureState | None = None
        self.last_thumb_connection_time: time = 0.0
        self.last_thumb_disconnection_time: time = 0.0
        self.thumb_connected_duration: time = 0.0
        self.currently_holding = False
        self.currently_holding_state: GestureState = GestureState.NONE

        self.last_click_time: time = 0.0
    

    def updateClickState(self, new_thumb_connection: GestureState, mouse):
        

        old_thumb_connection: GestureState = self.thumb_connection
        
        now: time = time()


        fingers_were_connected_then_released : bool = new_thumb_connection == GestureState.NONE and old_thumb_connection in [GestureState.LEFT, GestureState.RIGHT, GestureState.MIDDLE]

        fingers_connected : bool = new_thumb_connection in [GestureState.LEFT, GestureState.RIGHT, GestureState.MIDDLE]

        # Αν ενεργοποιήσαμε λειτουργία αντίχειρα, ξεκινάμε το χρονόμετρο
        if (fingers_connected):
            
            # Η ενεργοποίηση άλλης λειτουργίας αντίχειρα (π.χ. από LEFT σε RIGHT) θεωρείται σαν αποσύνδεση της προηγούμενης και σύνδεση της νέας, οπότε επανεκκινούμε το χρονόμετρο
            if new_thumb_connection != old_thumb_connection:
                self.last_thumb_connection_time = now # Εκκίνηση χρονομέτρου σύνδεσης δαχτύλου με αντίχειρα
                self.thumb_connected_duration = 0.0
            # Σε κάθε άλλη περίπτωση (λογικά μόνο όταν έχουμε τα ίδια old με new thumb connections)
            else :
                # 
                self.thumb_connected_duration = now - self.last_thumb_connection_time
                
                # Εάν έχουμε περάσει το κατώφλι για hold, ενεργοποιούμε παρατεταμένο κλικ
                if self.thumb_connected_duration >= config.TIME_TO_HOLD and not self.currently_holding:
                    print(f"Live hold triggered for {new_thumb_connection.name}! Locking down.")
                    mouse.set_click_state(new_thumb_connection, down=True)
                    self.currently_holding = True
                    self.currently_holding_state = new_thumb_connection

        elif (fingers_were_connected_then_released):
            # Η στιγμή που ανοίγει η παλάμη και αποσυνδέεται ο αντίχειρας με κάποιο από τα ειδικά δάχτυλα
            self.last_thumb_disconnection_time = now # Καταγραφή χρόνου αποσύνδεσης δαχτύλου με αντίχειρα
            self.thumb_connected_duration = self.last_thumb_disconnection_time - self.last_thumb_connection_time # Υπολογισμός συνολικής διάρκειας σύνδεσης δαχτύλου με αντίχειρα
            #print(f"Detected release of {old_thumb_connection.name} after {self.thumb_connected_duration:.2f} seconds.")
            
            # Σε περίπτωση που ήταν κρατημένο, το απελευθερώνουμε και δεν κάνουμε τίποτα άλλο
            if self.currently_holding:
                #print(f"{old_thumb_connection.name} is held down right now. Releasing it due to disconnection.")
                self.thumb_connection = new_thumb_connection

                mouse.set_click_state(old_thumb_connection, down=False)
                self.currently_holding = False 
                return
            
            '''
            Διαχείριση στιγμιαίου κλικ 
            '''

            # Αν δεν έχουμε φτάσει στο κατώφλι για στιγμιαίο κλικ, δεν κάνουμε τίποτα

            if self.thumb_connected_duration < config.TIME_TO_CLICK:
                return
            
            # Αν έχουμε περάσει το κατώφλι του στιγμιαίου κλικ αλλά όχι του hold, εκτελούμε στιγμιαίο κλικ
            elif self.thumb_connected_duration >= config.TIME_TO_CLICK and self.thumb_connected_duration < config.TIME_TO_HOLD:
                #print("Attempting to do a simple click.")
                
                # Debounce για να αποφύγουμε πολλαπλά κλικ από ένα μόνο gesture
                if now - self.last_click_time < config.TIME_TO_CLICK:
                    #print(f"Click ignored due to debounce (only {now - self.last_click_time:.2f} seconds since last click).")
                    return

                self.last_click_time = now
                mouse.click(old_thumb_connection)

        self.thumb_connection = new_thumb_connection
        

        
