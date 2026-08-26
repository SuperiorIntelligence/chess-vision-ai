#!/usr/bin/env python3
"""Entry point: launches the Chess Analyzer window.

The real implementation lives in the ``chess_vision_ai`` package
(``chess_vision_ai/ui/analyzer_app.py`` and friends) — this file just
does the friendly "you're missing a dependency" check and starts Tk.
"""
import sys

MISSING = []
for pkg, module in [
    ("opencv-python", "cv2"), ("numpy", "numpy"),
    ("Pillow", "PIL"), ("python-chess", "chess"), ("mss", "mss"),
]:
    try:
        __import__(module)
    except ImportError:
        MISSING.append(pkg)
if MISSING:
    print(f"Missing dependencies. Run:\n  pip install {' '.join(MISSING)}")
    sys.exit(1)

import tkinter as tk

from chess_vision_ai.logging_setup import setup_logging
from chess_vision_ai.ui.analyzer_app import ChessAnalyzerApp


def main() -> None:
    setup_logging()
    root = tk.Tk()
    ChessAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
