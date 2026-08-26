"""Downloads and unpacks Stockfish, Lc0, the Maia network and Syzygy
tablebases. Pure I/O module — no UI, no engine, no chess logic.
"""
from __future__ import annotations

import gzip
import shutil
import tarfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

from . import config
from .logging_setup import get_logger

log = get_logger("download")


class DownloadError(Exception):
    pass


ProgressCB = Callable[[int, str], None]
LogCB = Callable[[str], None]


class DownloadManager:
    def __init__(self, progress_cb: ProgressCB | None = None, log_cb: LogCB | None = None):
        self._progress = progress_cb or (lambda pct, msg: None)
        self._log = log_cb or log.info
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def fetch(self, url: str, dest: Path, label: str = "") -> Path:
        self._log(f"⬇  {label or dest.name}  ←  {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                done = 0
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as f:
                    while True:
                        if self._cancel:
                            raise DownloadError("cancelled")
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            self._progress(done * 100 // total, f"{label}: {done / 1048576:.1f}/{total / 1048576:.1f} MB")
                        else:
                            self._progress(-1, f"{label}: {done / 1048576:.1f} MB…")
        except urllib.error.URLError as e:
            raise DownloadError(f"URL error: {e}") from e
        return dest

    @staticmethod
    def extract_zip(src: Path, dest_dir: Path) -> list[Path]:
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = []
        with zipfile.ZipFile(src) as zf:
            for info in zf.infolist():
                name = Path(info.filename).name
                if not name or info.filename.endswith("/"):
                    continue
                target = dest_dir / name
                with zf.open(info) as r, open(target, "wb") as w:
                    shutil.copyfileobj(r, w)
                out.append(target)
                if config.OS_NAME != "Windows":
                    target.chmod(0o755)
        return out

    @staticmethod
    def extract_tar(src: Path, dest_dir: Path) -> list[Path]:
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = []
        mode = "r:gz" if str(src).endswith(".gz") else "r:*"
        with tarfile.open(src, mode) as tf:
            for member in tf.getmembers():
                if member.isfile():
                    member.name = Path(member.name).name
                    tf.extract(member, dest_dir)
                    target = dest_dir / member.name
                    out.append(target)
                    try:
                        target.chmod(0o755)
                    except Exception:
                        pass
        return out

    @staticmethod
    def decompress_gz(src: Path, dest: Path) -> None:
        with gzip.open(src, "rb") as gz, open(dest, "wb") as f:
            shutil.copyfileobj(gz, f)

    @staticmethod
    def _is_valid_binary(path: Path, min_bytes: int = 128) -> bool:
        if not path.exists() or path.stat().st_size < min_bytes:
            return False
        try:
            header = path.read_bytes()[:16]
            if header[0:1] in (b"<", b" ", b"\n", b"\r"):
                return False
            return True
        except Exception:
            return False

    def download_stockfish18(self) -> Path | None:
        self._log("🔽 Downloading Stockfish 18…")
        for variant in ["bmi2", "avx2", "base"]:
            url = config.SF18_URLS.get(variant, {}).get(config.OS_NAME)
            if not url:
                continue
            tmp = config.ENGINES_DIR / f"sf18_{variant}_dl"
            try:
                self._progress(0, f"Stockfish 18 [{variant}]…")
                self.fetch(url, tmp, f"Stockfish 18 [{variant}]")
                exe = "stockfish.exe" if config.OS_NAME == "Windows" else "stockfish"
                dest_dir = config.ENGINES_DIR / f"sf18_{variant}"
                files = self.extract_zip(tmp, dest_dir) if url.endswith(".zip") else self.extract_tar(tmp, dest_dir)
                tmp.unlink(missing_ok=True)
                for f in files:
                    if "stockfish" in f.name.lower() and not f.name.endswith(".txt"):
                        target = dest_dir / exe
                        f.rename(target)
                        self._log(f"   🎯 SF18 [{variant}] → {target}")
                        return target
            except DownloadError as e:
                self._log(f"   ⚠ {e}")
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
        return None

    def download_lc0(self) -> Path | None:
        url = config.LCO_BIN_URLS.get(config.OS_NAME)
        if not url:
            return None
        self._log("🔽 Downloading Lc0 (CPU)…")
        tmp = config.LCO_DIR / "lc0_dl"
        try:
            self.fetch(url, tmp, "Lc0 CPU binary")
            exe = "lc0.exe" if config.OS_NAME == "Windows" else "lc0"
            files = self.extract_zip(tmp, config.LCO_DIR) if url.endswith(".zip") else self.extract_tar(tmp, config.LCO_DIR)
            tmp.unlink(missing_ok=True)
            for f in files:
                if f.name.lower().startswith("lc0"):
                    target = config.LCO_DIR / exe
                    try:
                        f.rename(target)
                    except Exception:
                        shutil.copy2(f, target)
                        f.unlink(missing_ok=True)
                    self._log(f"   🎯 Lc0 → {target}")
                    return target
        except DownloadError as e:
            self._log(f"   ⚠ Lc0: {e}")
            if tmp.exists():
                tmp.unlink(missing_ok=True)
        return None

    def download_maia_network(self) -> Path | None:
        gz_path = config.LCO_NET_DIR / config.MAIA_NET_NAME
        out_path = config.LCO_NET_DIR / config.MAIA_NET_NAME.replace(".gz", "")
        if out_path.exists():
            return out_path
        try:
            self.fetch(config.MAIA_NET_URL, gz_path, "Maia-1900 network")
            self.decompress_gz(gz_path, out_path)
            gz_path.unlink(missing_ok=True)
            return out_path
        except DownloadError as e:
            self._log(f"   ⚠ Maia: {e}")
            return None

    def download_syzygy(self, include_4pc: bool = True) -> int:
        names = config.SYZYGY_3PC[:] + (config.SYZYGY_4PC if include_4pc else [])
        exts = [".rtbw", ".rtbz"]
        total = len(names) * len(exts)
        done = 0
        self._log(f"🔽 Syzygy {'3+4' if include_4pc else '3'}-piece ({total} files)…")
        self._log(f"   Destination: {config.SYZYGY_DIR}")
        for name in names:
            for ext in exts:
                fname = name + ext
                dest = config.SYZYGY_DIR / fname
                pct = done * 100 // total
                if self._is_valid_binary(dest):
                    done += 1
                    self._progress(pct, f"Syzygy: {fname} (cached)")
                    continue
                downloaded = False
                for mirror in config.SYZYGY_MIRRORS:
                    url = mirror + fname
                    try:
                        self._progress(pct, f"Syzygy: {fname}")
                        self.fetch(url, dest, f"Syzygy {fname}")
                        if self._is_valid_binary(dest):
                            done += 1
                            downloaded = True
                            break
                        self._log(f"   ⚠ {fname} was HTML — trying next mirror")
                        dest.unlink(missing_ok=True)
                    except DownloadError as e:
                        self._log(f"   ⚠ {fname}@{mirror}: {e}")
                        if dest.exists():
                            dest.unlink(missing_ok=True)
                if not downloaded:
                    self._log(f"   ✗ Skipped {fname}")
        self._log(f"   ✅ Syzygy: {done}/{total} files in {config.SYZYGY_DIR}")
        return done

    def download_all(self, include_syzygy4: bool = True) -> dict:
        status = {"sf18": None, "lc0": None, "maia": None, "syzygy": 0}
        status["sf18"] = self.download_stockfish18()
        status["lc0"] = self.download_lc0()
        status["maia"] = self.download_maia_network()
        status["syzygy"] = self.download_syzygy(include_4pc=include_syzygy4)
        return status
