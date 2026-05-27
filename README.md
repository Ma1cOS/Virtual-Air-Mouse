# Virtual Air Mouse

Έλεγχος κέρσορα μέσω υπολογιστικής όρασης σε Linux (X11 και Wayland).
Χρησιμοποιεί MediaPipe για ανίχνευση χεριού, EMA φίλτρο για εξομάλυνση,
και evdev/UInput για απευθείας αποστολή REL events στον Kernel.

---

## Γρήγορη εκκίνηση

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Ο χρήστης πρέπει να ανήκει στην ομάδα uinput
sudo usermod -a -G uinput $USER
# (logout/login για να ενεργοποιηθεί)

venv/bin/python main.py
```

**Πλήκτρα:**

| Πλήκτρο | Λειτουργία |
|---------|------------|
| `m` | Ενεργοποίηση/Απενεργοποίηση κέρσορα |
| `q` ή `ESC` | Έξοδος |

---

## Δομή project

```
app/
├── main.py              # orchestrator — κύριος βρόχος, pipeline, key handling
├── config.py            # Όλες οι παράμετροι (κάμερα, EMA, κέρσορας)
├── state.py             # CursorState — mutable κατάσταση ανά frame
├── display.py           # Συναρτήσεις σχεδίασης (HUD, feedback, FPS)
├── vision/
│   └── detector.py      # HandDetector — MediaPipe Tasks, GPU fallback, 21 landmarks
├── smoothing/
│   └── controller.py    # SmoothingFilter (adaptive EMA) + CursorController
└── output/
    └── mouse.py         # MouseOutput — evdev/UInput εικονικό ποντίκι
```

**Ροή δεδομένων:** Camera → Vision (landmarks) → Smoothing (EMA) → Output (REL events) → Kernel

---

## Παράμετροι (`app/config.py`)

| Παράμετρος | Default | Επίδραση |
|---|---|---|
| `DELTA_SCALE` | 4.0 | Ταχύτητα κέρσορα (>1 = πιο γρήγορα) |
| `ALPHA` | 0.20 | Απόκριση EMA (>0.20 = πιο snappy) |
| `STABILITY_THRESHOLD` | 15.0 | Pixels ακινησίας για κλείδωμα κέρσορα |
| `MOUSE_SUBDIVISIONS` | 4 | Υπο-βήματα ανά frame (×30fps = Hz εξόδου) |
| `VELOCITY_HOLD_FRAMES` | 4 | Frames επανάληψης τελευταίου delta σε απώλεια |
| `CURSOR_FINGER` | 8 | Landmark ID (8 = άκρη δείκτη) |
| `PREFERRED_HAND` | "Left" | "Right", "Left", ή "Any" |

---

## Troubleshooting

**Η κάμερα δεν ανοίγει (κλειδωμένη από προηγούμενο process):**
```bash
fuser /dev/video0 && kill $(fuser /dev/video0)
```

**Ο κέρσορας δεν κουνιέται:**
```bash
# Βεβαιώσου ότι είσαι στην ομάδα uinput
groups $USER | grep uinput

# Το /dev/uinput πρέπει να υπάρχει
ls -la /dev/uinput
```

**Το evdev δεν βρέθηκε:**
```bash
venv/bin/pip install evdev==1.9.3
```

---

## Απαιτήσεις

| Πακέτο | Έκδοση | Χρήση |
|---|---|---|
| mediapipe | 0.10.35 | Ανίχνευση χεριού (Tasks API, GPU) |
| opencv-contrib-python | 4.13.0 | Κάμερα, επεξεργασία εικόνας |
| numpy | 2.4.6 | EMA, υπολογισμοί |
| evdev | 1.9.3 | Εικονικό ποντίκι (uinput) |
