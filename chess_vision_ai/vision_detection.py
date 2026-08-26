"""OpenCV template-matching piece detector.

``BoardDetector.detect_with_confidence`` returns a
:class:`~chess_vision_ai.models.DetectionResult` that includes an average
match-confidence score and the list of squares the matcher wasn't sure
about. The UI/analysis layer uses that confidence to decide whether it's
worth falling back to the optional Vision-LLM detector
(:mod:`chess_vision_ai.vision_llm`) — deterministic, free, local detection
stays the default path; the LLM is only consulted when it's actually
needed, which keeps the app fast and avoids unnecessary API costs.
"""
from __future__ import annotations

import cv2
import numpy as np

from . import config
from .fen_utils import sanitize_board_map
from .models import DetectionResult
from .templates import load_templates


class BoardDetector:
    def __init__(self):
        self.cell_size = 60
        self.templates: dict = {}

    def detect(self, img: np.ndarray, flipped: bool = False) -> tuple[dict, list[str]]:
        """Backwards-compatible shortcut that discards confidence info."""
        result = self.detect_with_confidence(img, flipped)
        return result.board_map, result.warnings

    def detect_with_confidence(self, img: np.ndarray, flipped: bool = False) -> DetectionResult:
        h, w = img.shape[:2]
        self.cell_size = min(h, w) // 8
        self.templates = load_templates(self.cell_size)

        raw, confidences = self._split_and_id(img, h, w, flipped)
        clean, warnings = sanitize_board_map(raw)

        scored = list(confidences.values())
        avg_confidence = float(np.mean(scored)) if scored else 0.0
        low_conf_squares = [
            sq for sq, c in confidences.items()
            if c < config.DETECTION_CONFIDENCE_THRESHOLD
        ]

        return DetectionResult(
            board_map=clean, warnings=warnings, confidence=avg_confidence,
            low_confidence_squares=low_conf_squares, source="template",
        )

    def _split_and_id(self, img: np.ndarray, h: int, w: int, flipped: bool):
        ch, cw = h // 8, w // 8
        cells: dict[str, str | None] = {}
        confidences: dict[str, float] = {}
        for r in range(8):
            for c in range(8):
                if flipped:
                    rank = r + 1
                    file_c = config.FILES_FLIPPED[c]
                else:
                    rank = 8 - r
                    file_c = config.FILES_NORMAL[c]
                sq = f"{file_c}{rank}"
                cell = img[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw]
                sym, conf = self._identify(cell)
                cells[sq] = sym
                confidences[sq] = conf
        return cells, confidences

    def _identify(self, cell: np.ndarray) -> tuple[str | None, float]:
        gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
        if gray.std() < 22:
            return None, 1.0  # confidently empty square

        resized = cv2.resize(cell, (self.cell_size, self.cell_size))
        best_sym, best_score = None, 0.0
        for sym, tmpl in self.templates.items():
            score = self._ncc(resized, tmpl)
            if score > best_score:
                best_score, best_sym = score, sym
        if best_score >= 0.30:
            return best_sym, best_score

        h, w = gray.shape
        cy, cx = h // 2, w // 2
        my, mx = h // 5, w // 5
        center = gray[cy - my:cy + my, cx - mx:cx + mx]
        if center.size == 0 or center.std() < 15:
            return None, 0.5
        mean = float(center.mean())
        if mean > 160:
            return "P", 0.2  # heuristic guess — deliberately low confidence
        if mean < 90:
            return "p", 0.2
        return None, 0.3

    def _ncc(self, cell: np.ndarray, tmpl: np.ndarray) -> float:
        c3 = cell[:, :, :3] if cell.shape[2] >= 3 else cell
        gc = cv2.cvtColor(c3, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if tmpl.shape[2] == 4:
            gt = cv2.cvtColor(tmpl[:, :, :3], cv2.COLOR_BGR2GRAY).astype(np.float32)
            mask = (tmpl[:, :, 3] > 128).astype(np.float32)
        else:
            gt = cv2.cvtColor(tmpl[:, :, :3], cv2.COLOR_BGR2GRAY).astype(np.float32)
            mask = np.ones(gt.shape, np.float32)
        n = mask.sum()
        if n == 0:
            return 0.0
        mc = (gc * mask).sum() / n
        mt = (gt * mask).sum() / n
        dc = (gc - mc) * mask
        dt = (gt - mt) * mask
        return float((dc * dt).sum() / (np.sqrt((dc ** 2).sum() * (dt ** 2).sum()) + 1e-9))
