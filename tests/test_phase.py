import chess

from chess_vision_ai.phase import GamePhase, detect_phase


def test_starting_position_is_opening():
    assert detect_phase(chess.Board()) == GamePhase.OPENING


def test_kr_vs_k_is_tablebase():
    board = chess.Board("8/8/8/4k3/8/8/4R3/4K3 w - - 0 1")
    assert detect_phase(board) == GamePhase.TABLEBASE


def test_few_pieces_but_above_syzygy_threshold_is_endgame():
    # 8 pieces total (2 kings + 6 pawns): above the 7-piece Syzygy cutoff,
    # at/under the 13-piece endgame cutoff.
    board = chess.Board("4k3/8/8/8/8/8/PPPPPP2/4K3 w - - 0 1")
    assert detect_phase(board) == GamePhase.ENDGAME


def test_middlegame_between_thresholds():
    # 18 pieces: fewer than the 24-piece opening cutoff, more than the 13-piece endgame cutoff.
    board = chess.Board("r3k2r/pppp1ppp/8/8/8/8/PPPP1PPP/R3K2R w KQkq - 0 1")
    assert detect_phase(board) == GamePhase.MIDDLEGAME
