"""Central configuration: paths, constants and download URLs.

Nothing in this module has side effects besides creating the small set of
data directories the app needs (engines/syzygy/lc0/templates), so it is
safe to import from anywhere, including tests.
"""
from __future__ import annotations

import platform
from pathlib import Path

# ── Directory layout ─────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
ENGINES_DIR = BASE_DIR / "engines"
SYZYGY_DIR = BASE_DIR / "syzygy"
LCO_DIR = BASE_DIR / "lc0"
LCO_NET_DIR = LCO_DIR / "networks"
TEMPLATE_DIR = BASE_DIR / "piece_templates"

for _d in (ENGINES_DIR, SYZYGY_DIR, LCO_DIR, LCO_NET_DIR, TEMPLATE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

OS_NAME = platform.system()

# ── Download URLs ────────────────────────────────────────────────────────────
SF18_URLS = {
    "bmi2": {
        "Windows": "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-x86-64-bmi2.zip",
        "Linux": "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-ubuntu-x86-64-bmi2.tar",
        "Darwin": "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-macos-x86-64-bmi2.zip",
    },
    "avx2": {
        "Windows": "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-x86-64-avx2.zip",
        "Linux": "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-ubuntu-x86-64-avx2.tar",
        "Darwin": "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-macos-x86-64-avx2.zip",
    },
    "base": {
        "Windows": "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-x86-64.zip",
        "Linux": "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-ubuntu-x86-64.tar",
        "Darwin": "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-macos-x86-64.zip",
    },
}

LCO_BIN_URLS = {
    "Windows": "https://github.com/LeelaChessZero/lc0/releases/download/v0.31.2/lc0-v0.31.2-windows-cpu-openblas.zip",
    "Linux": "https://github.com/LeelaChessZero/lc0/releases/download/v0.31.2/lc0-v0.31.2-linux-cpu.tar.gz",
    "Darwin": "https://github.com/LeelaChessZero/lc0/releases/download/v0.31.2/lc0-v0.31.2-macos-cpu.tar.gz",
}

MAIA_NET_URL = "https://github.com/CSSLab/maia-chess/releases/download/v1.0/maia-1900.pb.gz"
MAIA_NET_NAME = "maia-1900.pb.gz"

SYZYGY_3PC = ["KBvK", "KNvK", "KPvK", "KQvK", "KRvK"]
SYZYGY_4PC = [
    "KBBvK", "KBNvK", "KBPvK", "KBvKB", "KBvKN", "KBvKP",
    "KNNvK", "KNPvK", "KNvKN", "KNvKP", "KPPvK", "KPvKP",
    "KQBvK", "KQNvK", "KQPvK", "KQvKB", "KQvKN", "KQvKP", "KQvKQ", "KQvKR",
    "KRBvK", "KRNvK", "KRPvK", "KRvKB", "KRvKN", "KRvKP", "KRvKR",
]
SYZYGY_MIRRORS = [
    "https://tablebase.sesse.net/syzygy/3-4-5/",
    "https://chess.cygni.se/syzygy/3-4-5/",
    "https://tablebase.lichess.ovh/tables/standard/3-4-5/",
]

# ── Analysis tuning ───────────────────────────────────────────────────────────
ENGINE_DEPTH = 20
LCO_NODES = 800
TOP_K_MOVES = 3
ENDGAME_THRESHOLD = 13
SYZYGY_THRESHOLD = 7
MIDDLEGAME_THRESHOLD = 24

# Analysis cache: how many distinct (fen, depth, k) results to keep in memory.
ANALYSIS_CACHE_SIZE = 256

# Piece-detection confidence below this triggers the optional Vision-LLM
# fallback (if the user has enabled it and an API key is configured).
DETECTION_CONFIDENCE_THRESHOLD = 0.35

# ── Piece metadata ────────────────────────────────────────────────────────────
import chess  # noqa: E402  (after constants, keeps import order obvious)

PIECES = {
    "P": ("white", "pawn"), "N": ("white", "knight"), "B": ("white", "bishop"),
    "R": ("white", "rook"), "Q": ("white", "queen"), "K": ("white", "king"),
    "p": ("black", "pawn"), "n": ("black", "knight"), "b": ("black", "bishop"),
    "r": ("black", "rook"), "q": ("black", "queen"), "k": ("black", "king"),
}
PIECE_VALUE = {
    chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
    chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100,
}
PIECE_NAME = {
    chess.PAWN: "Pawn", chess.KNIGHT: "Knight", chess.BISHOP: "Bishop",
    chess.ROOK: "Rook", chess.QUEEN: "Queen", chess.KING: "King",
}

FILES_NORMAL = "abcdefgh"
FILES_FLIPPED = "hgfedcba"

# ── UI theme ──────────────────────────────────────────────────────────────────
COLORS = {
    "bg": "#1a1d23", "panel": "#22262f", "accent": "#00c98d",
    "text": "#e8eaf0", "muted": "#7a8099",
    "sq_light": "#b0bec5", "sq_dark": "#455a64",
    "gold": "#f6c90e", "red": "#ff6b6b", "orange": "#ff8800",
}
