import math


def split_int(accum):
    value = int(accum)
    return value, accum - value


def landmark_pos(lm_list, finger_id):
    return lm_list[finger_id][1], lm_list[finger_id][2]


def distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])
