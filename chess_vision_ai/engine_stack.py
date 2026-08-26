"""Orchestrates Stockfish + Lc0/Maia + Syzygy and returns a single
:class:`~chess_vision_ai.models.AnalysisResult`.

Performance note
-----------------
Re-analysing the exact same position (same FEN, depth and move count) is
common — e.g. the user clicks "Analyze" twice, or re-captures a screenshot
of a board that hasn't changed yet. ``MultiEngineStack`` keeps a small
LRU cache keyed by ``(fen, depth, k)`` so repeated calls skip the engine
entirely instead of burning CPU/time on an identical search.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import replace
from pathlib import Path

import chess
import chess.engine

from . import config
from .engine_process import SingleEngine, find_lc0, find_stockfish
from .logging_setup import get_logger
from .models import AnalysisResult, MoveInfo
from .phase import GamePhase, detect_phase
from .syzygy import SyzygyManager

log = get_logger("engine_stack")


class MultiEngineStack:
    def __init__(self, syzygy: SyzygyManager, cache_size: int = config.ANALYSIS_CACHE_SIZE):
        self.syzygy = syzygy
        self._sf: SingleEngine | None = None
        self._lc0: SingleEngine | None = None
        self._ready = threading.Event()
        self._error = ""
        self._cache_size = cache_size
        self._cache: "OrderedDict[tuple[str, int, int], AnalysisResult]" = OrderedDict()
        self._cache_lock = threading.Lock()

    # ── lifecycle ────────────────────────────────────────────────────────────
    def init(self, log_cb=None) -> bool:
        emit = log_cb or log.info
        ok = False
        try:
            sf_path = find_stockfish()
            opts = {}
            if self.syzygy.is_available():
                opts["SyzygyPath"] = self.syzygy.path_str()
                opts["SyzygyProbeLimit"] = self.syzygy.max_pieces()
                emit(f"📖  Syzygy: {self.syzygy.file_count()} files active")
            self._sf = SingleEngine(sf_path, opts)
            emit(f"♜  Stockfish: {sf_path}")
            ok = True
        except RuntimeError as e:
            self._error = str(e)
            emit(f"❌ {e}")

        lc0_path, net_path = find_lc0()
        if lc0_path and net_path:
            try:
                self._lc0 = SingleEngine(lc0_path, {"WeightsFile": net_path})
                emit(f"🧠  Lc0+{Path(net_path).name}: ready")
            except Exception as e:
                emit(f"⚠  Lc0: {e}")
                self._lc0 = None
        else:
            emit("🧠  Lc0 not found (optional)")

        if ok:
            self._ready.set()
        return ok

    def is_ready(self) -> bool:
        return self._ready.is_set() and self._sf is not None

    def has_lc0(self) -> bool:
        return self._lc0 is not None

    def status_text(self) -> str:
        parts = []
        if self._sf:
            parts.append("♜ SF18 ✓")
        if self._lc0:
            parts.append("🧠 Lc0/Maia ✓")
        if self.syzygy.is_available():
            parts.append(f"📖 Syzygy {self.syzygy.file_count()}f ✓")
        return "  ".join(parts) if parts else "⚠ no engine"

    # ── cache ────────────────────────────────────────────────────────────────
    def clear_cache(self) -> None:
        with self._cache_lock:
            self._cache.clear()

    def cache_info(self) -> dict:
        with self._cache_lock:
            return {"size": len(self._cache), "max_size": self._cache_size}

    def _cache_get(self, key) -> AnalysisResult | None:
        with self._cache_lock:
            result = self._cache.get(key)
            if result is not None:
                self._cache.move_to_end(key)  # LRU touch
                return replace(result, cached=True)
        return None

    def _cache_put(self, key, result: AnalysisResult) -> None:
        with self._cache_lock:
            self._cache[key] = result
            self._cache.move_to_end(key)
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)

    # ── analysis ─────────────────────────────────────────────────────────────
    def analyse(self, fen: str, depth: int = config.ENGINE_DEPTH, k: int = config.TOP_K_MOVES) -> AnalysisResult:
        cache_key = (fen, depth, k)
        cached = self._cache_get(cache_key)
        if cached is not None:
            log.debug("cache hit for %s", fen)
            return cached

        board = chess.Board(fen)
        phase = detect_phase(board)
        turn = board.turn

        if board.is_checkmate():
            result = self._trivial("Checkmate!", phase, turn)
        elif board.is_stalemate() or board.is_insufficient_material():
            result = self._trivial("Draw", phase, turn)
        else:
            if not self._sf:
                raise RuntimeError("Stockfish not ready")
            sf_results = self._sf.analyse(
                board, chess.engine.Limit(depth=depth),
                multipv=min(k, max(1, board.legal_moves.count())),
            )
            moves = self._parse_sf(sf_results, board)

            lc0_eval = None
            if self._lc0 and phase == GamePhase.MIDDLEGAME:
                try:
                    lc0_results = self._lc0.analyse(board, chess.engine.Limit(nodes=config.LCO_NODES), multipv=1)
                    if lc0_results:
                        score = lc0_results[0]["score"].relative
                        lc0_eval = score.score() if not score.is_mate() else (10000 if score.mate() > 0 else -10000)
                except Exception:
                    log.debug("Lc0 analysis failed, continuing without it", exc_info=True)

            engine_used = "Stockfish 18"
            if lc0_eval is not None:
                engine_used += " + Lc0/Maia"
            if self.syzygy.is_available() and phase in (GamePhase.ENDGAME, GamePhase.TABLEBASE):
                engine_used += " + Syzygy"

            result = AnalysisResult(
                moves=moves, lc0_eval=lc0_eval, phase=phase,
                engine_used=engine_used, syzygy_active=self.syzygy.is_available(), turn=turn,
            )

        self._cache_put(cache_key, result)
        return result

    @staticmethod
    def _trivial(msg: str, phase: str, turn: bool) -> AnalysisResult:
        return AnalysisResult(
            moves=[MoveInfo(move="—", san=msg, score="0.00", mate=None, pv=[], score_cp=0)],
            lc0_eval=None, phase=phase, engine_used="—", syzygy_active=False, turn=turn,
        )

    @staticmethod
    def _parse_sf(results: list, board: chess.Board) -> list[MoveInfo]:
        out = []
        for info in results:
            pv = info.get("pv", [])
            if not pv:
                continue
            move = pv[0]
            try:
                san = board.san(move)
            except Exception:
                continue

            score_rel = info["score"].relative
            if score_rel.is_mate():
                mate_in = score_rel.mate()
                score_str = f"M{mate_in}"
                cp = 10000 if mate_in > 0 else -10000
            else:
                cp = score_rel.score()
                score_str = f"{'+' if cp >= 0 else ''}{cp / 100:.2f}"
                mate_in = None

            pv_sans, walker = [], board.copy()
            for mv in pv[:6]:
                try:
                    pv_sans.append(walker.san(mv))
                    walker.push(mv)
                except Exception:
                    break

            out.append(MoveInfo(move=move.uci(), san=san, score=score_str, mate=mate_in, pv=pv_sans, score_cp=cp))
        return out

    def close(self) -> None:
        if self._sf:
            self._sf.close()
            self._sf = None
        if self._lc0:
            self._lc0.close()
            self._lc0 = None

    def __del__(self):
        self.close()
