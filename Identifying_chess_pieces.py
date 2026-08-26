#!/usr/bin/env python3
"""Entry point: launches the Template Calibration wizard.

Kept at the repo root (same filename as before) so the documented
``python Identifying_chess_pieces.py`` command keeps working. The
implementation now lives in ``chess_vision_ai/ui/trainer_app.py``.
"""
import sys

MISSING = []
for pkg, module in [("opencv-python", "cv2"), ("numpy", "numpy"), ("Pillow", "PIL"), ("mss", "mss")]:
    try:
        __import__(module)
    except ImportError:
        MISSING.append(pkg)
if MISSING:
    print(f"Missing dependencies. Run:\n  pip install {' '.join(MISSING)}")
    sys.exit(1)

import tkinter as tk

from chess_vision_ai.ui.trainer_app import TrainerApp


def main() -> None:
    root = tk.Tk()
    TrainerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
