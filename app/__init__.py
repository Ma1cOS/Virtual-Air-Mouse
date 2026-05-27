"""
Πακέτο εφαρμογής Virtual Air Mouse.

Συνδυάζει:
    vision/: ανίχνευση χεριού (MediaPipe Tasks, GPU)
    smoothing/: εξομάλυνση (adaptive EMA)
    output/: έξοδος κέρσορα (evdev/UInput, X11 και Wayland)

Σημείο εισόδου: app.main.main()
"""
