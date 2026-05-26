"""
Πακέτο υπολογιστικής όρασης (Vision).

Περιέχει:
    HandDetector — ανίχνευση χεριού μέσω MediaPipe Tasks (GPU)
"""
from .detector import HandDetector
__all__ = ["HandDetector"]
