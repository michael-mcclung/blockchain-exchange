"""Landmark geometry for the virtual mouse.

These are the same ratios as utils.py in
https://github.com/michael-mcclung/Blockchain-Virtual-Mouse
(Zarka McClung, "Virtual Mouse Integration"). They use the standard library
so the exchange tests do not need OpenCV or dlib.
"""

from __future__ import annotations

import math
from typing import Sequence


def _point(value) -> tuple[float, float]:
    return (float(value[0]), float(value[1]))


def _distance(a, b) -> float:
    ax, ay = _point(a)
    bx, by = _point(b)
    return math.dist((ax, ay), (bx, by))


def eye_aspect_ratio(eye: Sequence) -> float:
    """Eye aspect ratio from the six eye landmarks.

    A closed eye is near 0. A missing horizontal span returns 0 instead of
    dividing by zero.
    """
    horizontal = _distance(eye[0], eye[3])
    if horizontal == 0:
        return 0.0
    vertical = _distance(eye[1], eye[5]) + _distance(eye[2], eye[4])
    return vertical / (2.0 * horizontal)


def mouth_aspect_ratio(mouth: Sequence) -> float:
    """Mouth aspect ratio from the 20 mouth landmarks.

    Indexes 12–19 match the original helper. A missing horizontal span
    returns 0.
    """
    horizontal = _distance(mouth[12], mouth[16])
    if horizontal == 0:
        return 0.0
    vertical = (
        _distance(mouth[13], mouth[19])
        + _distance(mouth[14], mouth[18])
        + _distance(mouth[15], mouth[17])
    )
    return vertical / (2.0 * horizontal)


def direction(nose_point, anchor_point, width: float, height: float, multiple: float = 1) -> str:
    """Return right, left, down, up, or '-' from the nose relative to the anchor.

    Horizontal movement wins when both axes are outside the box, matching the
    original helper.
    """
    nx, ny = _point(nose_point)
    x, y = _point(anchor_point)

    if nx > x + multiple * width:
        return "right"
    if nx < x - multiple * width:
        return "left"
    if ny > y + multiple * height:
        return "down"
    if ny < y - multiple * height:
        return "up"
    return "-"
