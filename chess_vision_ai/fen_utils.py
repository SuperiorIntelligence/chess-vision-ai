"""Pure functions for turning a detected board map into a valid FEN.

Nothing here touches the filesystem, the network, or an engine, which makes
this the easiest module in the project to unit test exhaustively.
"""
from __future__ import annotations

MAX_COUNT = {"K": 1, "k": 1, "Q": 9, "q": 9, "R": 10, "r": 10,
             "B": 10, "b": 10, "N": 10, "n": 10, "P": 8, "p": 8}


def sanitize_board_map(board_map: dict[str, str | None]) -> tuple[dict[str, str | None], list[str]]:
    """Drop physically-impossible extra pieces and guarantee both kings exist.

    Returns ``(clean_map, warnings)``.
    """
    tracker: dict[str, int] = {}
    clean: dict[str, str | None] = {}
    warnings: list[str] = []

    for sq in sorted(board_map.keys()):
        piece = board_map[sq]
        if not piece:
            clean[sq] = None
            continue
        count = tracker.get(piece, 0)
        if count < MAX_COUNT.get(piece, 1):
            tracker[piece] = count + 1
            clean[sq] = piece
        else:
            warnings.append(f"Extra {piece} at {sq} removed")
            clean[sq] = None

    if tracker.get("K", 0) == 0:
        clean["e1"] = "K"
        warnings.append("White King added at e1")
    if tracker.get("k", 0) == 0:
        clean["e8"] = "k"
        warnings.append("Black King added at e8")

    return clean, warnings


def infer_castling(board_map: dict[str, str | None]) -> str:
    """Infer castling rights from piece positions (king/rook still home)."""
    rights = ""
    if board_map.get("e1") == "K":
        if board_map.get("h1") == "R":
            rights += "K"
        if board_map.get("a1") == "R":
            rights += "Q"
    if board_map.get("e8") == "k":
        if board_map.get("h8") == "r":
            rights += "k"
        if board_map.get("a8") == "r":
            rights += "q"
    return rights or "-"


def board_map_to_fen(
    board_map: dict[str, str | None],
    active: str = "w",
    ep: str = "-",
    halfmove: int = 0,
    fullmove: int = 1,
) -> str:
    """Serialize a ``{"e4": "P", ...}`` map into a full FEN string."""
    castling = infer_castling(board_map)
    rows = []
    for rank in range(8, 0, -1):
        empty = 0
        row = ""
        for file_letter in "abcdefgh":
            piece = board_map.get(f"{file_letter}{rank}")
            if piece:
                if empty:
                    row += str(empty)
                    empty = 0
                row += piece
            else:
                empty += 1
        if empty:
            row += str(empty)
        rows.append(row)
    return f"{'/'.join(rows)} {active} {castling} {ep} {halfmove} {fullmove}"
