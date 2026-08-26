"""Modal progress dialog shown while engines/networks/tablebases download."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

from ..config import COLORS as C
from ..download import DownloadManager


class DownloadDialog:
    def __init__(self, parent: tk.Misc, include_syzygy4: bool = True):
        self.result: dict = {}
        self.win = tk.Toplevel(parent)
        self.win.title("⬇ Downloading Engines & Models")
        self.win.geometry("580x480")
        self.win.configure(bg=C["bg"])
        self.win.resizable(False, False)
        self.win.grab_set()

        tk.Label(self.win, text="⬇ Downloading Engine Stack", bg=C["bg"], fg=C["accent"],
                 font=("Segoe UI", 14, "bold")).pack(pady=(16, 4))
        tk.Label(self.win, text="Stockfish 18  ·  Lc0/Maia-1900  ·  Syzygy 3+4pc\n(~80 MB — runs once)",
                 bg=C["bg"], fg=C["muted"], font=("Segoe UI", 9)).pack()
        tk.Label(self.win, text="⚠ If Stockfish shows 'Unsupported 16-bit': delete engines/sf18_bmi2/ and re-run.",
                 bg=C["bg"], fg=C["orange"], font=("Segoe UI", 8)).pack(padx=20)

        self.progress_var = tk.IntVar(value=0)
        ttk.Progressbar(self.win, variable=self.progress_var, maximum=100, length=520).pack(pady=10, padx=20)

        self.msg_var = tk.StringVar(value="Starting…")
        tk.Label(self.win, textvariable=self.msg_var, bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 9), wraplength=540).pack()

        self.log_area = scrolledtext.ScrolledText(self.win, height=12, width=70, bg="#12151c", fg="#88ccaa",
                                                    font=("Courier New", 8), relief="flat", state="disabled")
        self.log_area.pack(padx=20, pady=8, fill=tk.BOTH, expand=True)

        btn_row = tk.Frame(self.win, bg=C["bg"])
        btn_row.pack(pady=(0, 12))
        self.btn_cancel = tk.Button(btn_row, text="✖ Cancel", command=self._do_cancel, bg="#c0392b", fg="white",
                                     font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=5)
        self.btn_cancel.pack(side=tk.LEFT, padx=6)
        self.btn_close = tk.Button(btn_row, text="✔ Close", command=self.win.destroy, bg=C["accent"], fg="#000",
                                    font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=5, state="disabled")
        self.btn_close.pack(side=tk.LEFT, padx=6)

        self._dm = DownloadManager(progress_cb=self._on_progress, log_cb=self._on_log)
        threading.Thread(target=self._worker, kwargs={"include_syzygy4": include_syzygy4}, daemon=True).start()

    def _do_cancel(self):
        self._dm.cancel()
        self.msg_var.set("Cancelling…")

    def _on_progress(self, pct, msg):
        self.win.after(0, lambda: self.progress_var.set(max(0, pct)))
        self.win.after(0, lambda: self.msg_var.set(msg))

    def _on_log(self, msg):
        def _do():
            self.log_area.config(state="normal")
            self.log_area.insert(tk.END, msg + "\n")
            self.log_area.see(tk.END)
            self.log_area.config(state="disabled")
        self.win.after(0, _do)

    def _worker(self, include_syzygy4: bool = True):
        try:
            self.result = self._dm.download_all(include_syzygy4=include_syzygy4)
        except Exception as e:
            self._on_log(f"❌ Fatal: {e}")
        finally:
            self.win.after(0, self._done)

    def _done(self):
        self.progress_var.set(100)
        self.msg_var.set("Download complete ✅")
        self.btn_cancel.config(state="disabled")
        self.btn_close.config(state="normal")
