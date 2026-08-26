"""Screen-capture helpers, isolated so they can be mocked in tests."""
from __future__ import annotations

import cv2
import mss
import numpy as np


def capture_region(x: int, y: int, w: int, h: int) -> np.ndarray:
    with mss.mss() as sct:
        return cv2.cvtColor(np.array(sct.grab({"left": x, "top": y, "width": w, "height": h})), cv2.COLOR_BGRA2BGR)


def take_full_screenshot() -> np.ndarray:
    with mss.mss() as sct:
        return cv2.cvtColor(np.array(sct.grab(sct.monitors[1])), cv2.COLOR_BGRA2BGR)
