"""UCI engine process wrapper + discovery of local Stockfish/Lc0 binaries."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import chess
import chess.engine

from . import config
from .logging_setup import get_logger

log = get_logger("engine_process")

ILLEGAL_INSTRUCTION_EXIT_CODE = 3221225477


def _test_engine(path: str, depth: int = 3) -> bool:
    try:
        engine = chess.engine.SimpleEngine.popen_uci(path, timeout=8)
        engine.analyse(chess.Board(), chess.engine.Limit(depth=depth))
        engine.quit()
        return True
    except Exception:
        return False


def find_stockfish() -> str:
    for variant in ["bmi2", "avx2", "base"]:
        exe = "stockfish.exe" if config.OS_NAME == "Windows" else "stockfish"
        candidate = config.ENGINES_DIR / f"sf18_{variant}" / exe
        if candidate.exists() and _test_engine(str(candidate)):
            return str(candidate)

    legacy_candidates = [
        r"stockfish-windows-x86-64-bmi2\stockfish\stockfish-windows-x86-64-bmi2.exe",
        r"stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe",
        r"stockfish-windows-x86-64\stockfish\stockfish-windows-x86-64.exe",
        "stockfish.exe", "stockfish",
    ]
    for rel in legacy_candidates:
        for candidate in (str(config.BASE_DIR / rel), rel):
            if Path(candidate).exists() and _test_engine(candidate):
                return candidate

    for exe_path in config.BASE_DIR.rglob("stockfish*.exe"):
        if _test_engine(str(exe_path)):
            return str(exe_path)

    found = shutil.which("stockfish")
    if found and _test_engine(found):
        return found

    raise RuntimeError(
        "Stockfish not found.\nClick '⬇ Download Engines' to auto-download.\n"
        "Or manually: https://stockfishchess.org/download/\n"
        "Place stockfish.exe next to main.py"
    )


def find_lc0() -> tuple[str | None, str | None]:
    exe = "lc0.exe" if config.OS_NAME == "Windows" else "lc0"
    lc0_path = config.LCO_DIR / exe
    networks = sorted(config.LCO_NET_DIR.glob("*.pb"), reverse=True) + \
        sorted(config.LCO_NET_DIR.glob("*.pb.gz"), reverse=True)
    network = networks[0] if networks else None
    if lc0_path.exists() and network and _test_engine(str(lc0_path)):
        return str(lc0_path), str(network)
    return None, None


class SingleEngine:
    """A UCI engine process that transparently restarts itself if it dies."""

    def __init__(self, path: str, options: dict | None = None):
        self.path = path
        self.options = options or {}
        self._engine: chess.engine.SimpleEngine | None = None
        self._dead = False
        self._open()

    def _open(self) -> None:
        if self._engine:
            try:
                self._engine.quit()
            except Exception:
                pass
        self._engine = chess.engine.SimpleEngine.popen_uci(self.path, timeout=10)
        for key, value in self.options.items():
            try:
                self._engine.configure({key: value})
            except Exception:
                log.warning("Engine option %s=%s rejected", key, value)
        self._dead = False

    def analyse(self, board: chess.Board, limit: chess.engine.Limit, multipv: int = 1) -> list:
        if self._dead:
            self._open()
        try:
            result = self._engine.analyse(board, limit, multipv=multipv)
            return result if isinstance(result, list) else [result]
        except chess.engine.EngineTerminatedError as e:
            self._dead = True
            match = re.search(r"exit code[:\s]+(\d+)", str(e), re.I)
            code = int(match.group(1)) if match else None
            if code == ILLEGAL_INSTRUCTION_EXIT_CODE:
                raise RuntimeError(
                    f"Stockfish CPU incompatible (exit {code}).\n"
                    "Delete engines/sf18_bmi2/ folder, then click ⬇ Download Engines again."
                ) from e
            self._open()
            result = self._engine.analyse(board, limit, multipv=multipv)
            return result if isinstance(result, list) else [result]

    def close(self) -> None:
        if self._engine:
            try:
                self._engine.quit()
            except Exception:
                pass
            self._engine = None

    def __del__(self):
        self.close()
