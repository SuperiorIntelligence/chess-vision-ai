"""Typed data structures shared across the app.

Using dataclasses instead of ad-hoc dicts makes the engine/UI boundary
explicit, gives editors/type-checkers something to work with, and prevents
typo bugs like ``m["scor"]`` from silently returning ``None``.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MoveInfo:
    """A single candidate move returned by the engine stack."""

    move: str                 # UCI, e.g. "e2e4", or "—" for trivial positions
    san: str                  # Standard Algebraic Notation, e.g. "e4"
    score: str                # Display string, e.g. "+0.35" or "M3"
    mate: int | None          # Mate-in-N (signed), or None if not forced mate
    pv: list[str] = field(default_factory=list)  # Principal variation, in SAN
    score_cp: int = 0         # Centipawns, relative to the side to move

    def as_dict(self) -> dict:
        """Backwards-compatible dict view (legacy UI code expects dicts)."""
        return {
            "move": self.move, "san": self.san, "score": self.score,
            "mate": self.mate, "pv": self.pv, "score_cp": self.score_cp,
        }


@dataclass(slots=True)
class AnalysisResult:
    """Full result of analysing one FEN with the multi-engine stack."""

    moves: list[MoveInfo]
    lc0_eval: int | None
    phase: str
    engine_used: str
    syzygy_active: bool
    turn: bool          # chess.WHITE / chess.BLACK
    cached: bool = False  # True if this result was served from the analysis cache


@dataclass(slots=True)
class TacticInfo:
    name: str
    icon: str
    color: str
    desc: str


@dataclass(slots=True)
class TacticResult:
    tactics: list[TacticInfo]
    explanation: str


@dataclass(slots=True)
class DetectionResult:
    """Result of reading piece positions off a captured board image."""

    board_map: dict[str, str | None]
    warnings: list[str]
    confidence: float                 # average match confidence, 0..1
    low_confidence_squares: list[str]  # squares the detector wasn't sure about
    source: str = "template"          # "template" or "vision-llm"
