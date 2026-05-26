"""
Πακέτο εξομάλυνσης (Smoothing).

Περιέχει:
    SmoothingFilter  — προσαρμοστικό EMA
    CursorController — extract landmark → EMA
"""
from .controller import CursorController
__all__ = ["CursorController"]
