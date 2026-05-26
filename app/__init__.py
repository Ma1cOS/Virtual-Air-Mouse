"""
Πακέτο εφαρμογής Virtual Air Mouse.

Συνδυάζει:
    vision/    — ανίχνευση χεριού (MediaPipe Tasks, GPU)
    smoothing/ — εξομάλυνση (adaptive EMA)
    output/    — έξοδος κέρσορα (evdev/UInput, Wayland-native)

Σημείο εισόδου: app.main.main()
"""
