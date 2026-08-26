"""Synthetic piece-template generation and loading.

If the user never runs the trainer wizard, we still want the app to work
out of the box, so a simple procedural (OpenCV-drawn) template set is
generated on first use.
"""
from __future__ import annotations

import cv2
import numpy as np

from . import config


def _template_path(symbol: str):
    direct = config.TEMPLATE_DIR / f"{symbol}.png"
    if direct.exists():
        return direct
    prefix = "w" if symbol.isupper() else "b"
    return config.TEMPLATE_DIR / f"{prefix}_{symbol.upper()}.png"


def generate_synthetic_templates(cell_size: int = 60) -> None:
    config.TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    s, h = cell_size, cell_size // 2

    def base(color):
        img = np.zeros((s, s, 4), dtype=np.uint8)
        fill = (255, 255, 255, 230) if color == "white" else (30, 30, 30, 230)
        outline = (40, 40, 40, 255) if color == "white" else (200, 200, 200, 255)
        return img, fill, outline

    def pawn(c):
        img, f, o = base(c); cx = h
        cv2.circle(img, (cx, s // 4), s // 6, f, -1); cv2.circle(img, (cx, s // 4), s // 6, o, 1)
        cv2.rectangle(img, (cx - s // 8, s // 4), (cx + s // 8, s * 3 // 4), f, -1)
        cv2.rectangle(img, (cx - s // 8, s // 4), (cx + s // 8, s * 3 // 4), o, 1)
        cv2.rectangle(img, (cx - s // 5, s * 3 // 4), (cx + s // 5, s - 4), f, -1)
        cv2.rectangle(img, (cx - s // 5, s * 3 // 4), (cx + s // 5, s - 4), o, 1)
        return img

    def rook(c):
        img, f, o = base(c); cx = h
        pts = np.array([
            [cx - s // 4, 4], [cx - s // 5, 4], [cx - s // 5, s // 5], [cx - s // 8, s // 5], [cx - s // 8, 4],
            [cx + s // 8, 4], [cx + s // 8, s // 5], [cx + s // 5, s // 5], [cx + s // 5, 4], [cx + s // 4, 4],
            [cx + s // 4, s * 3 // 4], [cx - s // 4, s * 3 // 4],
        ], np.int32)
        cv2.fillPoly(img, [pts], f); cv2.polylines(img, [pts], True, o, 1)
        cv2.rectangle(img, (cx - s // 4, s * 3 // 4), (cx + s // 4, s - 4), f, -1)
        cv2.rectangle(img, (cx - s // 4, s * 3 // 4), (cx + s // 4, s - 4), o, 1)
        return img

    def knight(c):
        img, f, o = base(c); cx = h
        pts = np.array([[cx - s // 5, s - 4], [cx + s // 4, s - 4], [cx + s // 4, s // 3],
                         [cx + s // 8, s // 5], [cx - s // 8, s // 6], [cx - s // 5, s // 3]], np.int32)
        cv2.fillPoly(img, [pts], f); cv2.polylines(img, [pts], True, o, 1)
        cv2.circle(img, (cx - s // 10, s // 5), s // 8, f, -1); cv2.circle(img, (cx - s // 10, s // 5), s // 8, o, 1)
        return img

    def bishop(c):
        img, f, o = base(c); cx = h
        cv2.circle(img, (cx, s // 4), s // 6, f, -1); cv2.circle(img, (cx, s // 4), s // 6, o, 1)
        pts = np.array([[cx, s // 8], [cx + s // 5, s * 2 // 3], [cx - s // 5, s * 2 // 3]], np.int32)
        cv2.fillPoly(img, [pts], f); cv2.polylines(img, [pts], True, o, 1)
        cv2.rectangle(img, (cx - s // 4, s * 2 // 3), (cx + s // 4, s - 4), f, -1)
        cv2.rectangle(img, (cx - s // 4, s * 2 // 3), (cx + s // 4, s - 4), o, 1)
        return img

    def queen(c):
        img, f, o = base(c); cx = h
        crown = np.array([[cx - s // 3, s // 2], [cx - s // 4, s // 5], [cx, s // 3],
                           [cx + s // 4, s // 5], [cx + s // 3, s // 2]], np.int32)
        cv2.fillPoly(img, [crown], f); cv2.polylines(img, [crown], False, o, 1)
        for px in [cx - s // 3, cx - s // 4, cx, cx + s // 4, cx + s // 3]:
            cv2.circle(img, (px, s // 5), 3, f, -1); cv2.circle(img, (px, s // 5), 3, o, 1)
        cv2.ellipse(img, (cx, s * 2 // 3), (s // 3, s // 6), 0, 0, 360, f, -1)
        cv2.ellipse(img, (cx, s * 2 // 3), (s // 3, s // 6), 0, 0, 360, o, 1)
        cv2.rectangle(img, (cx - s // 3, s * 3 // 4), (cx + s // 3, s - 4), f, -1)
        cv2.rectangle(img, (cx - s // 3, s * 3 // 4), (cx + s // 3, s - 4), o, 1)
        return img

    def king(c):
        img, f, o = base(c); cx = h
        cv2.rectangle(img, (cx - 2, 4), (cx + 2, s // 5), f, -1); cv2.rectangle(img, (cx - 2, 4), (cx + 2, s // 5), o, 1)
        cv2.rectangle(img, (cx - s // 8, s // 8), (cx + s // 8, s // 6), f, -1)
        cv2.rectangle(img, (cx - s // 8, s // 8), (cx + s // 8, s // 6), o, 1)
        cv2.ellipse(img, (cx, s * 5 // 12), (s // 4, s // 5), 0, 0, 360, f, -1)
        cv2.ellipse(img, (cx, s * 5 // 12), (s // 4, s // 5), 0, 0, 360, o, 1)
        cv2.rectangle(img, (cx - s // 3, s * 3 // 5), (cx + s // 3, s - 4), f, -1)
        cv2.rectangle(img, (cx - s // 3, s * 3 // 5), (cx + s // 3, s - 4), o, 1)
        return img

    makers = {"pawn": pawn, "rook": rook, "knight": knight, "bishop": bishop, "queen": queen, "king": king}
    for symbol, (color, ptype) in config.PIECES.items():
        cv2.imwrite(str(config.TEMPLATE_DIR / f"{symbol}.png"), makers[ptype](color))


def load_templates(cell_size: int) -> dict:
    if not all(_template_path(s).exists() for s in config.PIECES):
        generate_synthetic_templates(cell_size)
    out = {}
    for symbol in config.PIECES:
        path = _template_path(symbol)
        if path.exists():
            img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            if img is not None:
                out[symbol] = cv2.resize(img, (cell_size, cell_size))
    return out
