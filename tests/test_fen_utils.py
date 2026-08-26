import chess

from chess_vision_ai.fen_utils import board_map_to_fen, infer_castling, sanitize_board_map

STARTING_MAP = {
    "a1": "R", "b1": "N", "c1": "B", "d1": "Q", "e1": "K", "f1": "B", "g1": "N", "h1": "R",
    "a2": "P", "b2": "P", "c2": "P", "d2": "P", "e2": "P", "f2": "P", "g2": "P", "h2": "P",
    "a7": "p", "b7": "p", "c7": "p", "d7": "p", "e7": "p", "f7": "p", "g7": "p", "h7": "p",
    "a8": "r", "b8": "n", "c8": "b", "d8": "q", "e8": "k", "f8": "b", "g8": "n", "h8": "r",
}


def test_board_map_to_fen_starting_position_is_valid():
    fen = board_map_to_fen(STARTING_MAP, active="w")
    board = chess.Board(fen)  # raises ValueError if invalid
    assert board.piece_at(chess.E1).symbol() == "K"
    assert fen.split(" ")[0] == chess.STARTING_BOARD_FEN


def test_castling_rights_full_when_king_and_rooks_home():
    assert infer_castling(STARTING_MAP) == "KQkq"


def test_castling_rights_partial_when_one_rook_moved():
    m = dict(STARTING_MAP)
    del m["h1"]  # white kingside rook moved away
    assert infer_castling(m) == "Qkq"


def test_castling_rights_dash_when_king_moved():
    m = dict(STARTING_MAP)
    del m["e1"]
    m["e2"] = "K"  # overwrite pawn with king, doesn't matter for this check
    assert "K" not in infer_castling(m) and "Q" not in infer_castling(m)


def test_sanitize_removes_extra_pieces_over_the_physical_maximum():
    too_many_queens = {f"{f}{r}": "Q" for f in "abcdefgh" for r in (1, 2)}  # 16 white queens
    clean, warnings = sanitize_board_map(too_many_queens)
    assert sum(1 for v in clean.values() if v == "Q") <= 9
    assert any("removed" in w for w in warnings)


def test_sanitize_adds_missing_kings():
    clean, warnings = sanitize_board_map({"e4": "P"})
    assert clean["e1"] == "K"
    assert clean["e8"] == "k"
    assert len(warnings) == 2


def test_empty_board_produces_all_dashes_rank():
    fen = board_map_to_fen({})
    assert fen.split(" ")[0] == "8/8/8/8/8/8/8/8"
