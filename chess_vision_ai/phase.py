"""Game-phase classification, used to decide which engines to consult."""
from __future__ import annotations

import chess

from .config import ENDGAME_THRESHOLD, MIDDLEGAME_THRESHOLD, SYZYGY_THRESHOLD


class GamePhase:
    OPENING = "opening"
    MIDDLEGAME = "middlegame"
    ENDGAME = "endgame"
    TABLEBASE = "tablebase"


def detect_phase(board: "chess.Board") -> str:
    n = len(board.piece_map())
    if n <= SYZYGY_THRESHOLD:
        return GamePhase.TABLEBASE
    if n <= ENDGAME_THRESHOLD:
        return GamePhase.ENDGAME
    if n >= MIDDLEGAME_THRESHOLD:
        return GamePhase.OPENING
    return GamePhase.MIDDLEGAME


PHASE_LABEL = {
    GamePhase.OPENING: "Opening",
    GamePhase.MIDDLEGAME: "Middlegame",
    GamePhase.ENDGAME: "Endgame",
    GamePhase.TABLEBASE: "Tablebase Endgame",
}
PHASE_COLOR = {
    GamePhase.OPENING: "#4fc3f7",
    GamePhase.MIDDLEGAME: "#f6c90e",
    GamePhase.ENDGAME: "#ff8800",
    GamePhase.TABLEBASE: "#00c98d",
}
