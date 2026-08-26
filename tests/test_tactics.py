import chess

from chess_vision_ai.tactics import TacticalAnalyzer

analyzer = TacticalAnalyzer()


def _tactic_names(board_fen: str, uci_move: str) -> set[str]:
    board = chess.Board(board_fen)
    move = chess.Move.from_uci(uci_move)
    result = analyzer.analyse_move(board, move, score_before=0.0, score_after=1.0)
    return {t.name for t in result.tactics}


def test_knight_fork_on_king_and_rook():
    names = _tactic_names("2r1k3/8/8/1N6/8/8/8/4K3 w - - 0 1", "b5d6")
    assert "Fork" in names
    assert "Check" in names  # Nd6+ also checks the king


def test_rook_pin_against_king():
    names = _tactic_names("k7/8/n7/8/7R/8/8/4K3 w - - 0 1", "h4a4")
    assert "Pin" in names


def test_rook_skewer_through_queen_to_rook():
    names = _tactic_names("7k/4r3/4q3/8/8/8/8/R5K1 w - - 0 1", "a1e1")
    assert "Skewer" in names


def test_discovered_attack_when_blocker_moves_away():
    names = _tactic_names("7k/8/r7/8/8/8/4N3/5BK1 w - - 0 1", "e2d4")
    assert "Discovered Attack" in names


def test_checkmate_detected():
    names = _tactic_names("6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1", "a1a8")
    assert "Checkmate!" in names


def test_material_gain_on_favorable_capture():
    names = _tactic_names("4k3/8/8/4n3/3P4/8/8/4K3 w - - 0 1", "d4e5")
    assert "Material Gain" in names


def test_promotion_detected():
    names = _tactic_names("7k/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8q")
    assert "Promotion" in names


def test_quiet_move_without_tactics_has_no_tactic_entries():
    board = chess.Board()  # starting position
    move = chess.Move.from_uci("g1f3")  # quiet knight development, no captures/checks
    result = analyzer.analyse_move(board, move, score_before=0.0, score_after=0.1)
    assert result.tactics == []
    assert "Positional move" in result.explanation
