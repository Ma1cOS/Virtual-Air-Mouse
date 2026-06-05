"""Click detection: thumb touches finger -> pinch gesture.

Timeline for one pinch:
    0 --- connected --- TIME_TO_CLICK --- TIME_TO_HOLD --- released
                             |                      |
                       simple click            hold (drag)
"""

from __future__ import annotations

from enum import Enum, auto
from time import time
from app import config
from app.utils import distance


class GestureState(Enum):
    """What the thumb is currently touching (or not)."""
    NONE = auto()
    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()


# Maps each gesture to the MediaPipe landmark that triggers it.
_CLICK_MAP: tuple[tuple[GestureState, int], ...] = (
    (GestureState.LEFT,   config.FINGER_LEFT_CLICK),
    (GestureState.RIGHT,  config.FINGER_RIGHT_CLICK),
    (GestureState.MIDDLE, config.FINGER_MIDDLE_CLICK),
)


def release_hold(state: 'CursorState', mouse: 'MouseOutput') -> None:
    """Let go of any held button right now.

    We call this when the hand vanishes or the user pauses tracking.
    Otherwise the virtual mouse gets stuck with a button pressed and
    your real mouse acts like it's in a permanent drag.
    """
    if state.currently_holding:
        mouse.set_click_state(state.currently_holding_state, down=False)
        state.currently_holding = False
        state.thumb_connection = None


def watch_for_clicks(state: 'CursorState', lm_list: list, mouse: 'MouseOutput') -> None:
    """Run pinch detection on the current frame.

    Measures the Euclidean distance from the thumb tip (4) to each of
    the click fingers (8, 12, 16). The closest one under threshold wins.
    During an active hold we add HOLD_HYSTERESIS pixels of slack so the
    user can drift a little without losing the hold.
    """
    if not lm_list:
        release_hold(state, mouse)
        return

    # Bail if the EMA filters haven't warmed up yet.
    if None in (state.filtered_positions.get(config.FINGER_BASE_CLICK),
                state.filtered_positions.get(config.FINGER_LEFT_CLICK),
                state.filtered_positions.get(config.FINGER_RIGHT_CLICK),
                state.filtered_positions.get(config.FINGER_MIDDLE_CLICK)):
        return

    base = state.filtered_positions[config.FINGER_BASE_CLICK]

    click_distances: dict[GestureState, float] = {}
    for click_type, click_id in _CLICK_MAP:
        click_distances[click_type] = distance(base, state.filtered_positions[click_id])

    min_click_state = min(click_distances, key=click_distances.get)
    min_distance = click_distances[min_click_state]

    extra = config.HOLD_HYSTERESIS if state.currently_holding else 0

    if min_distance < config.CLICK_DISTANCE_THRESHOLD + extra:
        _update_click_state(state, min_click_state, mouse)
    else:
        _update_click_state(state, GestureState.NONE, mouse)


def _update_click_state(state: 'CursorState', new_connection: GestureState, mouse: 'MouseOutput') -> None:
    """The click state machine. Runs once per frame.

    We track how long the thumb has been connected to the same finger:
      - Less than TIME_TO_CLICK:                noise, ignore
      - Between TIME_TO_CLICK and TIME_TO_HOLD: simple click on release
      - Over TIME_TO_HOLD:                      hold (button stays down)

    We also debounce: at most one simple click per TIME_TO_CLICK window.
    Without this a single slow pinch triggers multiple clicks.
    """
    old = state.thumb_connection
    now = time()

    released = (new_connection == GestureState.NONE and
                old in (GestureState.LEFT, GestureState.RIGHT, GestureState.MIDDLE))
    connected = new_connection in (GestureState.LEFT, GestureState.RIGHT, GestureState.MIDDLE)

    if connected:
        if new_connection != old:
            # New finger touched or switched fingers. Restart the timer.
            state.last_thumb_connection_time = now
            state.thumb_connected_duration = 0.0
        else:
            # Same finger, still touching. Accumulate.
            state.thumb_connected_duration = now - state.last_thumb_connection_time
            if state.thumb_connected_duration >= config.TIME_TO_HOLD and not state.currently_holding:
                mouse.set_click_state(new_connection, down=True)
                state.currently_holding = True
                state.currently_holding_state = new_connection

    elif released:
        state.thumb_connected_duration = now - state.last_thumb_connection_time

        # Were we holding? Release and we're done.
        if state.currently_holding:
            state.thumb_connection = new_connection
            mouse.set_click_state(old, down=False)
            state.currently_holding = False
            return

        # Too fast. Probably accidental.
        if state.thumb_connected_duration < config.TIME_TO_CLICK:
            return

        # Simple click window.
        if state.thumb_connected_duration < config.TIME_TO_HOLD:
            if now - state.last_click_time < config.TIME_TO_CLICK:
                return
            state.last_click_time = now
            mouse.click(old)

    state.thumb_connection = new_connection
