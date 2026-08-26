"""Optional Vision-LLM fallback for piece detection.

Design goal: keep LLM usage *optional and minimal*. The default,
zero-cost path is the deterministic OpenCV template matcher in
:mod:`chess_vision_ai.vision_detection`. This module is only consulted
when:

1. the user has explicitly enabled it in the UI, **and**
2. an API key is configured (``OPENAI_API_KEY``), **and**
3. the template matcher's average confidence for the current capture
   fell below :data:`chess_vision_ai.config.DETECTION_CONFIDENCE_THRESHOLD`
   (e.g. an unfamiliar board theme with no trained templates yet).

That keeps token spend at zero for the common case while still giving
users a robust fallback that works on *any* visual theme without having
to run the template-training wizard first.
"""
from __future__ import annotations

import base64
import json
import os
import re

import cv2
import numpy as np

from .fen_utils import sanitize_board_map
from .logging_setup import get_logger
from .models import DetectionResult

log = get_logger("vision_llm")

DEFAULT_MODEL = os.environ.get("CHESS_VISION_LLM_MODEL", "gpt-4o-mini")

_SYSTEM_PROMPT = (
    "You are a precise chess board digitizer. You will be shown a cropped image "
    "containing exactly one 8x8 chessboard. Identify every occupied square and "
    "its piece. Respond with ONLY a compact JSON object mapping algebraic square "
    "names to a single FEN piece letter (uppercase = white, lowercase = black), "
    "e.g. {\"e2\": \"P\", \"e7\": \"p\", \"e1\": \"K\", \"e8\": \"k\"}. "
    "Omit empty squares entirely. No prose, no markdown fences, no explanation."
)


class VisionLLMError(RuntimeError):
    pass


def is_available() -> bool:
    """True if the optional dependency and an API key are both present."""
    if not os.environ.get("OPENAI_API_KEY"):
        return False
    try:
        import openai  # noqa: F401
    except ImportError:
        return False
    return True


def _encode_image(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise VisionLLMError("Failed to encode image for the Vision-LLM request")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _orientation_hint(flipped: bool) -> str:
    if flipped:
        return "Board orientation: viewed from Black's side (rank 1 at the top, file h on the left)."
    return "Board orientation: viewed from White's side (rank 8 at the top, file a on the left)."


def _parse_response(text: str) -> dict[str, str]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise VisionLLMError(f"Model did not return valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise VisionLLMError("Model JSON was not an object")
    return data


class VisionLLMDetector:
    """Thin wrapper around an OpenAI-compatible vision chat completion call."""

    def __init__(self, model: str | None = None):
        if not is_available():
            raise VisionLLMError(
                "Vision-LLM fallback unavailable: set OPENAI_API_KEY and "
                "`pip install openai` to enable it."
            )
        import openai
        self._client = openai.OpenAI()
        self.model = model or DEFAULT_MODEL

    def detect(self, img: np.ndarray, flipped: bool = False) -> DetectionResult:
        b64 = _encode_image(img)
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _orientation_hint(flipped)},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        ],
                    },
                ],
                temperature=0,
                max_tokens=600,
            )
        except Exception as e:  # network / auth / rate-limit errors
            raise VisionLLMError(f"Vision-LLM request failed: {e}") from e

        content = response.choices[0].message.content or ""
        parsed = _parse_response(content)

        board_map: dict[str, str | None] = {
            f"{f}{r}": None for r in range(1, 9) for f in "abcdefgh"
        }
        warnings: list[str] = []
        valid_letters = set("KQRBNPkqrbnp")
        for sq, piece in parsed.items():
            sq = sq.strip().lower()
            if sq not in board_map:
                warnings.append(f"Vision-LLM returned unknown square '{sq}' — ignored")
                continue
            if piece not in valid_letters:
                warnings.append(f"Vision-LLM returned invalid piece '{piece}' at {sq} — ignored")
                continue
            board_map[sq] = piece

        clean, sanitize_warnings = sanitize_board_map(board_map)
        warnings.extend(sanitize_warnings)

        log.info("Vision-LLM detected %d pieces via %s", sum(1 for v in clean.values() if v), self.model)
        return DetectionResult(
            board_map=clean, warnings=warnings, confidence=0.9,
            low_confidence_squares=[], source="vision-llm",
        )
