"""Rule-based tactical motif detection: forks, pins, skewers, discovered
attacks, checks, captures and promotions.

This module only depends on ``python-chess`` board state, so it is fully
unit-testable without spinning up an engine or the UI.
"""
from __future__ import annotations

import chess

from .config import PIECE_NAME, PIECE_VALUE
from .models import TacticInfo, TacticResult


class TacticalAnalyzer:
    def analyse_move(
        self,
        board: chess.Board,
        move: chess.Move,
        score_before: float,
        score_after: float,
    ) -> TacticResult:
        """``score_before``/``score_after`` are pawns, relative to the mover."""
        tactics: list[TacticInfo] = []
        board_after = board.copy()
        board_after.push(move)

        if board_after.is_checkmate():
            tactics.append(TacticInfo("Checkmate!", "♛", "#ff4444", "Game over!"))
        elif board_after.is_check():
            tactics.append(TacticInfo("Check", "⚔", "#ff8800", "King is in check"))

        for finder in (self._fork, self._pin, self._skewer, self._discovered_attack):
            found = finder(board, move, board_after)
            if found:
                tactics.append(found)

        if board.is_capture(move):
            captured = board.piece_at(move.to_square)
            mover = board.piece_at(move.from_square)
            if captured and mover:
                cap_value = PIECE_VALUE.get(captured.piece_type, 0)
                mov_value = PIECE_VALUE.get(mover.piece_type, 0)
                if cap_value > mov_value:
                    tactics.append(TacticInfo(
                        "Material Gain", "💰", "#00c98d",
                        f"Win {PIECE_NAME[captured.piece_type]} with {PIECE_NAME[mover.piece_type]}",
                    ))
                elif cap_value == mov_value:
                    tactics.append(TacticInfo("Equal Exchange", "⚖", "#aaaaaa", "Equal exchange"))

        if move.promotion:
            tactics.append(TacticInfo("Promotion", "👑", "#f6c90e", "Pawn promotes!"))

        delta = score_after - score_before
        if not tactics and delta > 0.5:
            tactics.append(TacticInfo("Positional Improvement", "📈", "#00c98d", f"+{delta:.2f} pawns"))

        piece = board.piece_at(move.from_square)
        piece_name = PIECE_NAME.get(piece.piece_type, "Piece") if piece else "Piece"
        from_sq = chess.square_name(move.from_square)
        to_sq = chess.square_name(move.to_square)

        if score_after > 2.0:
            quality = "Excellent ✨"
        elif score_after > 0.5:
            quality = "Good 👍"
        elif score_after > -0.5:
            quality = "Equal ⚖"
        else:
            quality = "Defensive 🛡"

        tactic_str = " + ".join(t.name for t in tactics) if tactics else "Positional move"
        explanation = (
            f"{piece_name} {from_sq}→{to_sq}\n"
            f"Tactic: {tactic_str}\n"
            f"Eval: {score_after:+.2f}  ({quality})"
        )
        return TacticResult(tactics=tactics, explanation=explanation)

    def _fork(self, board: chess.Board, move: chess.Move, ba: chess.Board) -> TacticInfo | None:
        moved = ba.piece_at(move.to_square)
        if not moved:
            return None
        threatened = [
            ba.piece_at(sq) for sq in ba.attacks(move.to_square)
            if ba.piece_at(sq) and ba.piece_at(sq).color != moved.color
            and ba.piece_at(sq).piece_type != chess.PAWN
        ]
        if len(threatened) >= 2:
            names = " & ".join(PIECE_NAME[p.piece_type] for p in threatened[:3])
            return TacticInfo("Fork", "🍴", "#ff6b35", f"Simultaneous attack on {names}")
        return None

    def _pin(self, board: chess.Board, move: chess.Move, ba: chess.Board) -> TacticInfo | None:
        enemy = not board.turn
        for sq in chess.SQUARES:
            piece = ba.piece_at(sq)
            if not piece or piece.color != enemy:
                continue
            if ba.is_pinned(enemy, sq) and not board.is_pinned(enemy, sq):
                return TacticInfo("Pin", "📌", "#9b59b6", f"{PIECE_NAME[piece.piece_type]} is pinned!")
        return None

    def _skewer(self, board: chess.Board, move: chess.Move, ba: chess.Board) -> TacticInfo | None:
        color = board.turn
        moved = ba.piece_at(move.to_square)
        if not moved:
            return None
        for sq in ba.attacks(move.to_square):
            front = ba.piece_at(sq)
            if not front or front.color == color:
                continue
            if PIECE_VALUE.get(front.piece_type, 0) < PIECE_VALUE.get(moved.piece_type, 0):
                continue
            df = chess.square_file(sq) - chess.square_file(move.to_square)
            dr = chess.square_rank(sq) - chess.square_rank(move.to_square)
            behind_file = chess.square_file(sq) + (1 if df > 0 else -1 if df < 0 else 0)
            behind_rank = chess.square_rank(sq) + (1 if dr > 0 else -1 if dr < 0 else 0)
            if 0 <= behind_file <= 7 and 0 <= behind_rank <= 7:
                behind = ba.piece_at(chess.square(behind_file, behind_rank))
                if behind and behind.color != color:
                    return TacticInfo("Skewer", "🗡", "#e74c3c", f"{PIECE_NAME[front.piece_type]} must move")
        return None

    def _discovered_attack(self, board: chess.Board, move: chess.Move, ba: chess.Board) -> TacticInfo | None:
        color = board.turn
        for sq in chess.SQUARES:
            piece = ba.piece_at(sq)
            if not piece or piece.color != color or sq == move.to_square:
                continue
            if piece.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
                continue
            for target_sq in ba.attacks(sq) - board.attacks(sq):
                target = ba.piece_at(target_sq)
                if target and target.color != color and PIECE_VALUE.get(target.piece_type, 0) >= 3:
                    origin = board.piece_at(move.from_square)
                    origin_name = PIECE_NAME.get(origin.piece_type, "Piece") if origin else "Piece"
                    return TacticInfo(
                        "Discovered Attack", "💥", "#e67e22",
                        f"Moving {origin_name} reveals {PIECE_NAME[piece.piece_type]}'s attack!",
                    )
        return None
