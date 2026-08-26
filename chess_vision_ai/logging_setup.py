"""Standard-library logging configuration for the whole app.

The Tkinter UI still wants a human-readable, line-by-line log for its
on-screen "Log" tab — that behaviour is preserved by attaching a callback
handler (see ``attach_ui_handler``) instead of routing everything through
scattered ``print()`` calls.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Callable

LOG_FORMAT = "%(asctime)s  %(levelname)-7s  %(name)s: %(message)s"
DATE_FORMAT = "%H:%M:%S"


def setup_logging(log_file: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """Configure the root ``chess_vision_ai`` logger once at startup."""
    logger = logging.getLogger("chess_vision_ai")
    logger.setLevel(level)
    if logger.handlers:
        return logger  # already configured (e.g. re-entrant import)

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class _CallbackHandler(logging.Handler):
    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._callback(self.format(record))
        except Exception:
            pass  # UI widget may already be destroyed — never crash on log


def attach_ui_handler(logger: logging.Logger, callback: Callable[[str], None]) -> _CallbackHandler:
    """Mirror log records into a UI callback (e.g. a Tkinter ScrolledText)."""
    handler = _CallbackHandler(callback)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return handler


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"chess_vision_ai.{name}")
