from enum import Enum, auto
from time import time
from app import config
from app.utils import distance


class GestureState(Enum):
    NONE = auto()
    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()


_CLICK_MAP = (
    (GestureState.LEFT, config.FINGER_LEFT_CLICK),
    (GestureState.RIGHT, config.FINGER_RIGHT_CLICK),
    (GestureState.MIDDLE, config.FINGER_MIDDLE_CLICK),
)


def release_hold(state, mouse):
    if state.currently_holding:
        mouse.set_click_state(state.currently_holding_state, down=False)
        state.currently_holding = False
        state.thumb_connection = None


def watch_for_clicks(state, lm_list, mouse):
    if not lm_list:
        release_hold(state, mouse)
        return

    if None in (state.filtered_positions.get(config.FINGER_BASE_CLICK),
                state.filtered_positions.get(config.FINGER_LEFT_CLICK),
                state.filtered_positions.get(config.FINGER_RIGHT_CLICK),
                state.filtered_positions.get(config.FINGER_MIDDLE_CLICK)):
        return

    base = state.filtered_positions[config.FINGER_BASE_CLICK]

    click_distances = {}
    for click_type, click_id in _CLICK_MAP:
        click_distances[click_type] = distance(base, state.filtered_positions[click_id])

    min_click_state = min(click_distances, key=click_distances.get)
    min_distance = click_distances[min_click_state]

    extra = 5 if state.currently_holding else 0
    if min_distance < config.CLICK_DISTANCE_THRESHOLD + extra:
        _update_click_state(state, min_click_state, mouse)
    else:
        _update_click_state(state, GestureState.NONE, mouse)


def _update_click_state(state, new_connection, mouse):
    old = state.thumb_connection
    now = time()

    released = (new_connection == GestureState.NONE and
                old in (GestureState.LEFT, GestureState.RIGHT, GestureState.MIDDLE))
    connected = new_connection in (GestureState.LEFT, GestureState.RIGHT, GestureState.MIDDLE)

    if connected:
        if new_connection != old:
            state.last_thumb_connection_time = now
            state.thumb_connected_duration = 0.0
        else:
            state.thumb_connected_duration = now - state.last_thumb_connection_time
            if state.thumb_connected_duration >= config.TIME_TO_HOLD and not state.currently_holding:
                mouse.set_click_state(new_connection, down=True)
                state.currently_holding = True
                state.currently_holding_state = new_connection

    elif released:
        state.thumb_connected_duration = now - state.last_thumb_connection_time

        if state.currently_holding:
            state.thumb_connection = new_connection
            mouse.set_click_state(old, down=False)
            state.currently_holding = False
            return

        if state.thumb_connected_duration < config.TIME_TO_CLICK:
            return

        if state.thumb_connected_duration < config.TIME_TO_HOLD:
            if now - state.last_click_time < config.TIME_TO_CLICK:
                return
            state.last_click_time = now
            mouse.click(old)

    state.thumb_connection = new_connection
