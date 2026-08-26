"""Syzygy tablebase directory inspection (no downloading here, see download.py)."""
from __future__ import annotations

from pathlib import Path

from . import config


class SyzygyManager:
    def __init__(self, path: Path = config.SYZYGY_DIR):
        self.path = path

    def is_available(self) -> bool:
        return any(self.path.glob("*.rtbw"))

    def file_count(self) -> int:
        return len(list(self.path.glob("*.rtb*")))

    def max_pieces(self) -> int:
        max_n = 2
        for stem in {f.stem for f in self.path.glob("*.rtbw")}:
            max_n = max(max_n, len([c for c in stem.replace("v", "") if c.isalpha()]))
        return max_n

    def path_str(self) -> str:
        return str(self.path)
