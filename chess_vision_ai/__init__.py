"""Chess Vision AI — screenshot-driven multi-engine chess analyzer.

This package is organized by responsibility so each part can be tested and
modified independently:

    config        constants, paths, download URLs
    models        typed dataclasses shared across the app
    fen_utils     pure FEN / board-map helpers (no I/O)
    phase         game-phase detection
    logging_setup application-wide logging configuration
    download      DownloadManager for engines/networks/tablebases
    syzygy        SyzygyManager
    engine_process SingleEngine process wrapper + engine discovery
    engine_stack  MultiEngineStack — orchestrates Stockfish + Lc0 + Syzygy
    tactics       TacticalAnalyzer — pure rule-based tactic detection
    templates     synthetic piece template generation/loading
    vision_detection BoardDetector — OpenCV template-matching piece detector
    vision_llm    optional Vision-LLM fallback detector
    capture       screen-capture helpers
    ui/*          Tkinter application windows
"""

__version__ = "2.3.0"
