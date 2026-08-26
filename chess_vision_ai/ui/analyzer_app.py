"""Main Tkinter application: capture → detect → analyze → explain."""
from __future__ import annotations

import math
import threading
import time
import tkinter as tk
import traceback
from tkinter import messagebox, scrolledtext, ttk

import chess
import cv2
from PIL import Image, ImageTk

from .. import vision_llm
from ..capture import capture_region, take_full_screenshot
from ..config import COLORS as C
from ..config import DETECTION_CONFIDENCE_THRESHOLD, ENGINE_DEPTH, FILES_FLIPPED, FILES_NORMAL, TOP_K_MOVES
from ..engine_stack import MultiEngineStack
from ..fen_utils import board_map_to_fen
from ..logging_setup import attach_ui_handler, get_logger
from ..phase import PHASE_COLOR, PHASE_LABEL, GamePhase, detect_phase
from ..syzygy import SyzygyManager
from ..tactics import TacticalAnalyzer
from ..vision_detection import BoardDetector
from .download_dialog import DownloadDialog

log = get_logger("ui.analyzer")


class ChessAnalyzerApp:
    FONT_MONO = ("Courier New", 9)
    FONT_UI = ("Segoe UI", 10)

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("♟ Chess Analyzer v2.3 — Multi-Engine Stack")
        self.root.configure(bg=C["bg"])
        self.root.geometry("1200x900")
        self.root.minsize(950, 720)

        self.detector = BoardDetector()
        self.tactician = TacticalAnalyzer()
        self.syzygy = SyzygyManager()
        self.stack = MultiEngineStack(self.syzygy)

        self._eng_lock = threading.Lock()
        self.region: tuple[int, int, int, int] | None = None
        self.board_img = None
        self.board_map: dict = {}
        self.last_fen: str | None = None

        self.fen_var = tk.StringVar(value="—")
        self.turn_var = tk.StringVar(value="white")
        self.depth_var = tk.IntVar(value=ENGINE_DEPTH)
        self.status_var = tk.StringVar(value="Initializing…")
        self.phase_var = tk.StringVar(value="—")
        self.eng_var = tk.StringVar(value="—")
        self.ai_fallback_var = tk.BooleanVar(value=False)

        self._build_ui()
        attach_ui_handler(log, self._log)
        self._init_engine_async()

    def _is_flipped(self) -> bool:
        return self.turn_var.get() == "black"

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        top = tk.Frame(self.root, bg=C["bg"], pady=8)
        top.pack(fill=tk.X, padx=16)
        tk.Label(top, text="♟ Chess Analyzer v2.3", bg=C["bg"], fg=C["accent"],
                 font=("Segoe UI", 18, "bold")).pack(side=tk.LEFT)
        tk.Label(top, text="  SF18 + Lc0/Maia + Syzygy  |  cached + AI-vision fallback",
                 bg=C["bg"], fg=C["muted"], font=("Segoe UI", 10)).pack(side=tk.LEFT)

        sb = tk.Frame(self.root, bg=C["panel"], pady=5)
        sb.pack(fill=tk.X, padx=16)
        tk.Label(sb, textvariable=self.status_var, bg=C["panel"], fg=C["accent"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)
        tk.Label(sb, textvariable=self.eng_var, bg=C["panel"], fg=C["gold"], font=("Segoe UI", 9, "bold")).pack(side=tk.RIGHT, padx=8)

        content = tk.Frame(self.root, bg=C["bg"])
        content.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        left = tk.Frame(content, bg=C["bg"])
        left.pack(side=tk.LEFT, fill=tk.BOTH)
        self.board_canvas = tk.Canvas(left, width=480, height=480, bg=C["panel"], highlightthickness=1, highlightbackground=C["accent"])
        self.board_canvas.pack(pady=(0, 6))
        self._draw_empty_board(False)

        ctrl = tk.Frame(left, bg=C["bg"])
        ctrl.pack(fill=tk.X)
        b = {"bg": C["accent"], "fg": "#000", "font": ("Segoe UI", 9, "bold"), "relief": "flat", "cursor": "hand2", "padx": 10, "pady": 5}
        tk.Button(ctrl, text="📷 Select Region", command=self._select_region, **b).pack(side=tk.LEFT, padx=3)
        tk.Button(ctrl, text="🔍 Analyze", command=self._analyze, **b).pack(side=tk.LEFT, padx=3)
        tk.Button(ctrl, text="♻ Re-capture", command=self._recapture, **b).pack(side=tk.LEFT, padx=3)
        tk.Button(ctrl, text="⬇ Download Engines", command=self._open_download_dialog,
                  bg="#4a90d9", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=10, pady=5).pack(side=tk.LEFT, padx=3)
        self.btn_retry = tk.Button(ctrl, text="🔄 Retry", command=self._retry_engine,
                                    bg="#c0392b", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=8, pady=5)
        self.btn_retry.pack(side=tk.LEFT, padx=3)
        self.btn_retry.pack_forget()

        srow = tk.Frame(left, bg=C["bg"], pady=4)
        srow.pack(fill=tk.X)
        tk.Label(srow, text="Turn:", bg=C["bg"], fg=C["text"], font=self.FONT_UI).pack(side=tk.LEFT, padx=4)
        tk.Radiobutton(srow, text="White ♔", variable=self.turn_var, value="white", bg=C["bg"], fg=C["text"],
                       selectcolor=C["panel"], activebackground=C["bg"], font=self.FONT_UI, command=self._on_turn_change).pack(side=tk.LEFT, padx=3)
        tk.Radiobutton(srow, text="Black ♚", variable=self.turn_var, value="black", bg=C["bg"], fg=C["gold"],
                       selectcolor=C["panel"], activebackground=C["bg"], font=self.FONT_UI, command=self._on_turn_change).pack(side=tk.LEFT, padx=3)
        self.flip_indicator = tk.Label(srow, text="", bg=C["bg"], fg=C["orange"], font=("Segoe UI", 8, "italic"))
        self.flip_indicator.pack(side=tk.LEFT, padx=6)
        tk.Label(srow, text="Depth:", bg=C["bg"], fg=C["text"], font=self.FONT_UI).pack(side=tk.LEFT, padx=4)
        tk.Spinbox(srow, from_=10, to=30, textvariable=self.depth_var, width=4, bg=C["panel"], fg=C["text"],
                   font=self.FONT_UI, buttonbackground=C["panel"], relief="flat").pack(side=tk.LEFT)

        ai_row = tk.Frame(left, bg=C["bg"], pady=2)
        ai_row.pack(fill=tk.X)
        ai_available = vision_llm.is_available()
        state = "normal" if ai_available else "disabled"
        tip = "" if ai_available else "  (set OPENAI_API_KEY to enable)"
        tk.Checkbutton(ai_row, text=f"🤖 AI vision fallback on low confidence{tip}", variable=self.ai_fallback_var,
                       bg=C["bg"], fg=C["gold"] if ai_available else C["muted"], selectcolor=C["panel"],
                       activebackground=C["bg"], font=("Segoe UI", 8), state=state).pack(side=tk.LEFT)

        prow = tk.Frame(left, bg=C["bg"], pady=2)
        prow.pack(fill=tk.X)
        tk.Label(prow, text="Game Phase:", bg=C["bg"], fg=C["muted"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)
        self.phase_lbl = tk.Label(prow, textvariable=self.phase_var, bg=C["bg"], fg=C["gold"], font=("Segoe UI", 9, "bold"))
        self.phase_lbl.pack(side=tk.LEFT)

        self.coord_label = tk.Label(left, text="a  b  c  d  e  f  g  h", bg=C["bg"], fg=C["muted"], font=("Courier New", 9))
        self.coord_label.pack()

        ef = tk.Frame(content, bg=C["bg"], padx=6)
        ef.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(ef, text="Eval", bg=C["bg"], fg=C["muted"], font=("Segoe UI", 8)).pack()
        self.eval_canvas = tk.Canvas(ef, width=28, height=480, bg=C["panel"], highlightthickness=0)
        self.eval_canvas.pack()
        self.eval_label = tk.Label(ef, text="0.00", bg=C["bg"], fg=C["text"], font=("Segoe UI", 8))
        self.eval_label.pack()
        self.eval_side = tk.Label(ef, text="", bg=C["bg"], fg=C["muted"], font=("Segoe UI", 7))
        self.eval_side.pack()
        tk.Label(ef, text="Lc0", bg=C["bg"], fg=C["muted"], font=("Segoe UI", 7)).pack(pady=(8, 0))
        self.lc0_label = tk.Label(ef, text="—", bg=C["bg"], fg="#88ccaa", font=("Segoe UI", 8))
        self.lc0_label.pack()
        self._draw_eval_bar(0, chess.WHITE)

        right = tk.Frame(content, bg=C["panel"], padx=12, pady=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        style = ttk.Style()
        style.configure("TNotebook", background=C["panel"], borderwidth=0)
        style.configure("TNotebook.Tab", background=C["bg"], foreground=C["text"], padding=[10, 4], font=("Segoe UI", 9))
        style.map("TNotebook.Tab", background=[("selected", C["accent"])], foreground=[("selected", "#000")])

        self.tab_moves = tk.Frame(self.notebook, bg=C["panel"])
        self.notebook.add(self.tab_moves, text="🎯 Moves")
        ff = tk.Frame(self.tab_moves, bg=C["panel"])
        ff.pack(fill=tk.X, pady=(4, 6))
        tk.Label(ff, text="FEN:", bg=C["panel"], fg=C["muted"], font=self.FONT_UI).pack(anchor="w")
        tk.Entry(ff, textvariable=self.fen_var, font=("Courier New", 8), bg="#2d3240", fg=C["text"], relief="flat", width=46).pack(fill=tk.X)
        self.moves_frame = tk.Frame(self.tab_moves, bg=C["panel"])
        self.moves_frame.pack(fill=tk.X)

        self.tab_tactics = tk.Frame(self.notebook, bg=C["panel"])
        self.notebook.add(self.tab_tactics, text="💡 Tactics")
        self.tactics_area = scrolledtext.ScrolledText(self.tab_tactics, height=22, width=44, bg="#12151c", fg=C["text"],
                                                        font=("Segoe UI", 10), relief="flat", state="disabled", wrap=tk.WORD)
        self.tactics_area.pack(fill=tk.BOTH, expand=True)
        for tag, cfg in [
            ("header", {"foreground": C["accent"], "font": ("Segoe UI", 11, "bold")}),
            ("tactic", {"foreground": C["gold"], "font": ("Segoe UI", 10, "bold")}),
            ("desc", {"foreground": C["text"], "font": ("Segoe UI", 9)}),
            ("var", {"foreground": "#88ccaa", "font": ("Courier New", 9)}),
            ("phase", {"foreground": C["orange"], "font": ("Segoe UI", 9, "bold")}),
            ("info", {"foreground": "#88ccff", "font": ("Segoe UI", 9, "italic")}),
            ("sep", {"foreground": C["muted"]}),
        ]:
            self.tactics_area.tag_config(tag, **cfg)

        self.tab_log = tk.Frame(self.notebook, bg=C["panel"])
        self.notebook.add(self.tab_log, text="📋 Log")
        self.log = scrolledtext.ScrolledText(self.tab_log, height=22, width=44, bg="#12151c", fg=C["text"],
                                              font=self.FONT_MONO, relief="flat", state="disabled")
        self.log.pack(fill=tk.BOTH, expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_turn_change(self):
        flipped = self._is_flipped()
        if flipped:
            self.flip_indicator.config(text="🔄 Black's view — h at left, rank 1 at top")
            self.coord_label.config(text="h  g  f  e  d  c  b  a")
        else:
            self.flip_indicator.config(text="")
            self.coord_label.config(text="a  b  c  d  e  f  g  h")
        if self.board_map:
            self._draw_board(self.board_map, flipped=flipped)

    def _sq_to_canvas(self, sq_name: str, flipped: bool):
        f = "abcdefgh".index(sq_name[0])
        r = int(sq_name[1]) - 1
        if flipped:
            return 7 - f, r
        return f, 7 - r

    # ── Board drawing ─────────────────────────────────────────────────────────
    def _draw_empty_board(self, flipped: bool = False):
        c = self.board_canvas
        sq = 60
        c.delete("all")
        for r in range(8):
            for f in range(8):
                color = C["sq_light"] if (r + f) % 2 == 0 else C["sq_dark"]
                c.create_rectangle(f * sq, r * sq, (f + 1) * sq, (r + 1) * sq, fill=color, outline="")
        for row in range(8):
            rank_num = row + 1 if flipped else 8 - row
            c.create_text(6, row * sq + sq // 2, text=str(rank_num), fill=C["muted"], font=("Courier New", 8))

    def _draw_board(self, bmap: dict, hl_from=None, hl_to=None, arrow_move=None, flipped=False):
        c = self.board_canvas
        sq = 60
        c.delete("all")
        glyphs = {"K": "♔", "Q": "♕", "R": "♖", "B": "♗", "N": "♘", "P": "♙",
                  "k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟"}
        for sn in [f"{f}{r}" for r in range(1, 9) for f in "abcdefgh"]:
            col, row = self._sq_to_canvas(sn, flipped)
            bg = C["sq_light"] if (col + row) % 2 == 0 else C["sq_dark"]
            if sn == hl_from:
                bg = "#a8d8a8"
            if sn == hl_to:
                bg = C["gold"]
            c.create_rectangle(col * sq, row * sq, (col + 1) * sq, (row + 1) * sq, fill=bg, outline="")
        for row in range(8):
            rank_num = row + 1 if flipped else 8 - row
            c.create_text(6, row * sq + sq // 2, text=str(rank_num), fill=C["muted"], font=("Courier New", 8))
        for col in range(8):
            file_lbl = FILES_FLIPPED[col] if flipped else FILES_NORMAL[col]
            c.create_text(col * sq + sq // 2, 478, text=file_lbl, fill=C["muted"], font=("Courier New", 8))
        if arrow_move and len(arrow_move) >= 4:
            try:
                fc, fr = self._sq_to_canvas(arrow_move[:2], flipped)
                tc, tr = self._sq_to_canvas(arrow_move[2:4], flipped)
                c.create_line(fc * sq + sq // 2, fr * sq + sq // 2, tc * sq + sq // 2, tr * sq + sq // 2,
                              fill="#00c98d", width=4, arrow=tk.LAST, arrowshape=(14, 16, 6))
            except Exception:
                pass
        for sn, piece in bmap.items():
            if piece and piece in glyphs:
                pc, pr = self._sq_to_canvas(sn, flipped)
                cx_, cy_ = pc * sq + sq // 2, pr * sq + sq // 2
                col_ = "white" if piece.isupper() else "#111"
                c.create_text(cx_ + 1, cy_ + 1, text=glyphs[piece], font=("Arial", 26), fill="#0006")
                c.create_text(cx_, cy_, text=glyphs[piece], font=("Arial", 26), fill=col_)

    def _draw_eval_bar(self, score_cp_relative: float, turn: bool):
        c = self.eval_canvas
        c.delete("all")
        h = 480
        white_cp = score_cp_relative if turn == chess.WHITE else -score_cp_relative
        clamped = max(-10.0, min(10.0, white_cp / 100))
        pct = 0.5 + 0.5 * (2 / (1 + math.exp(-clamped * 0.4)) - 1)
        wh = int(h * pct)
        c.create_rectangle(0, 0, 28, wh, fill="#e8e8e8", outline="")
        c.create_rectangle(0, wh, 28, h, fill="#222", outline="")
        c.create_line(0, h // 2, 28, h // 2, fill="#444", width=1)
        self.eval_label.config(text=f"{white_cp / 100:+.2f}" if abs(white_cp) < 9900 else "M")
        if white_cp > 50:
            self.eval_side.config(text="♔ better", fg="#ddd")
        elif white_cp < -50:
            self.eval_side.config(text="♚ better", fg="#888")
        else:
            self.eval_side.config(text="equal", fg=C["muted"])

    # ── Engine init ───────────────────────────────────────────────────────────
    def _init_engine_async(self):
        def _go():
            with self._eng_lock:
                ok = self.stack.init(log_cb=self._log)
                if ok:
                    self._set_status("Engine ready ✅")
                    self.root.after(0, lambda: self.btn_retry.pack_forget())
                    self.root.after(0, lambda: self.eng_var.set(self.stack.status_text()))
                else:
                    self._set_status("⚠ Stockfish not found — click '⬇ Download Engines'")
                    self.root.after(0, lambda: self.btn_retry.pack(side=tk.LEFT, padx=3))
        threading.Thread(target=_go, daemon=True).start()

    def _retry_engine(self):
        self.stack.close()
        self._log("🔄 Retrying…")
        self._set_status("Reconnecting…")
        self._init_engine_async()

    def _open_download_dialog(self):
        dlg = DownloadDialog(self.root, include_syzygy4=True)
        self.root.wait_window(dlg.win)
        self._log("🔄 Re-initializing after download…")
        self.stack.close()
        self._init_engine_async()

    # ── Region capture ───────────────────────────────────────────────────────
    def _select_region(self):
        self.root.withdraw()
        self.root.update()
        time.sleep(0.2)
        result = self._run_selector()
        self.root.deiconify()
        if result:
            self.region = result
            x, y, w, h = result
            self._log(f"📐 Region: ({x},{y}) {w}×{h}")
            self._set_status(f"Region set: {w}×{h} — Press Analyze")
            self._capture_and_preview()
        else:
            self._set_status("Cancelled.")

    def _run_selector(self):
        sc = take_full_screenshot()
        hs, ws = sc.shape[:2]
        pil = Image.fromarray(cv2.cvtColor(sc, cv2.COLOR_BGR2RGB))
        result = [None]
        win = tk.Toplevel(self.root)
        win.attributes("-fullscreen", True, "-topmost", True)
        win.configure(bg="black")
        cv_canvas = tk.Canvas(win, cursor="crosshair", bg="black", highlightthickness=0)
        cv_canvas.pack(fill=tk.BOTH, expand=True)
        tki = ImageTk.PhotoImage(pil)
        cv_canvas.create_image(0, 0, anchor="nw", image=tki)
        cv_canvas.create_text(ws // 2, 30, text="Drag around the chessboard  |  ESC=cancel", fill="white", font=("Helvetica", 15, "bold"))
        st = {"s": None, "r": None}

        def press(e):
            st["s"] = (e.x, e.y)

        def drag(e):
            if st["s"]:
                if st["r"]:
                    cv_canvas.delete(st["r"])
                st["r"] = cv_canvas.create_rectangle(*st["s"], e.x, e.y, outline="#00FF88", width=2, dash=(6, 3))

        def release(e):
            if st["s"]:
                x0, y0 = st["s"]
                rx, ry = min(x0, e.x), min(y0, e.y)
                rw, rh = abs(e.x - x0), abs(e.y - y0)
                if rw > 30 and rh > 30:
                    result[0] = (rx, ry, rw, rh)
                win.destroy()

        cv_canvas.bind("<ButtonPress-1>", press)
        cv_canvas.bind("<B1-Motion>", drag)
        cv_canvas.bind("<ButtonRelease-1>", release)
        win.bind("<Escape>", lambda e: win.destroy())
        self.root.wait_window(win)
        return result[0]

    def _recapture(self):
        if not self.region:
            self._set_status("No region selected.")
            return
        self._capture_and_preview()

    def _capture_and_preview(self):
        if not self.region:
            return
        x, y, w, h = self.region
        self.board_img = capture_region(x, y, w, h)
        prev = cv2.resize(self.board_img, (480, 480))
        pil = Image.fromarray(cv2.cvtColor(prev, cv2.COLOR_BGR2RGB))
        self._prev_tk = ImageTk.PhotoImage(pil)
        self.board_canvas.delete("all")
        self.board_canvas.create_image(0, 0, anchor="nw", image=self._prev_tk)
        flipped = self._is_flipped()
        self._log(f"📸 Board captured. {'(Black-side view)' if flipped else '(White-side view)'}")

    # ── Analyze ──────────────────────────────────────────────────────────────
    def _analyze(self):
        if not self.region:
            messagebox.showwarning("", "Please select a region first.")
            return
        if not self.stack.is_ready():
            messagebox.showwarning("", "Engine not ready. Click '⬇ Download Engines'.")
            return
        self._set_status("Analyzing…")
        self._log("─" * 44)

        def _run():
            try:
                x, y, w, h = self.region
                self.board_img = capture_region(x, y, w, h)
                self._log("🔍 Detecting pieces…")
                flipped = self._is_flipped()
                is_black = flipped

                detection = self.detector.detect_with_confidence(self.board_img, flipped=flipped)
                self._log(f"   template match confidence: {detection.confidence:.2f}")

                if (
                    detection.confidence < DETECTION_CONFIDENCE_THRESHOLD
                    and self.ai_fallback_var.get()
                    and vision_llm.is_available()
                ):
                    self._log("   ⚠ low confidence — asking Vision-LLM fallback…")
                    try:
                        llm_detector = vision_llm.VisionLLMDetector()
                        detection = llm_detector.detect(self.board_img, flipped=flipped)
                        self._log(f"   🤖 Vision-LLM board read ({detection.source})")
                    except vision_llm.VisionLLMError as e:
                        self._log(f"   ⚠ Vision-LLM fallback failed: {e}")

                self.board_map = detection.board_map
                n = sum(1 for v in self.board_map.values() if v)
                self._log(f"   {n} pieces found  (flipped={flipped}, source={detection.source})")
                for w_ in detection.warnings:
                    self._log(f"   ⚠ {w_}")

                active = "b" if is_black else "w"
                fen = board_map_to_fen(self.board_map, active)
                self._log(f"   FEN: {fen}")
                try:
                    board = chess.Board(fen)
                except ValueError as e:
                    self._log(f"❌ Invalid FEN: {e}")
                    self._set_status("FEN error")
                    return

                phase = detect_phase(board)
                phase_lbl = PHASE_LABEL.get(phase, phase)
                phase_col = PHASE_COLOR.get(phase, C["text"])
                self._log(f"   Phase: {phase_lbl}")
                self.root.after(0, lambda: self.phase_var.set(phase_lbl))
                self.root.after(0, lambda: self.phase_lbl.config(fg=phase_col))

                self.last_fen = fen
                self.root.after(0, lambda: self.fen_var.set(fen))
                self.root.after(0, lambda: self._draw_board(self.board_map, flipped=flipped))

                depth = self.depth_var.get()
                self._log(f"⚙ Analyzing (depth={depth})…")
                try:
                    result = self.stack.analyse(fen, depth=depth, k=TOP_K_MOVES)
                except RuntimeError as e:
                    self._log(f"❌ {e}")
                    self.root.after(0, lambda: self.btn_retry.pack(side=tk.LEFT, padx=3))
                    self._set_status("Engine error")
                    return

                if result.cached:
                    self._log("   ⚡ served from analysis cache (identical position)")

                moves = result.moves
                self._log(f"   Engine: {result.engine_used}")
                self.root.after(0, lambda: self.eng_var.set(result.engine_used))

                if result.lc0_eval is not None:
                    lc0_txt = f"{result.lc0_eval / 100:+.2f}" if abs(result.lc0_eval) < 9900 else "M"
                    self.root.after(0, lambda: self.lc0_label.config(text=lc0_txt))
                else:
                    self.root.after(0, lambda: self.lc0_label.config(text="—"))

                best_cp = moves[0].score_cp if moves else 0
                self.root.after(0, lambda: self._draw_eval_bar(best_cp or 0, result.turn))
                self.root.after(0, lambda: self._display_moves(moves))

                tactic_results = []
                for mv_info in moves:
                    if mv_info.move in ("—", ""):
                        tactic_results.append(None)
                        continue
                    try:
                        move_obj = chess.Move.from_uci(mv_info.move)
                        sc_cp = mv_info.score_cp or 0
                        tactic_results.append(self.tactician.analyse_move(board, move_obj, 0.0, sc_cp / 100))
                    except Exception:
                        tactic_results.append(None)

                self.root.after(0, lambda: self._display_tactics(moves, tactic_results, phase, result))

                if moves and moves[0].move not in ("—", ""):
                    uci = moves[0].move
                    fsq, tsq = uci[:2], uci[2:4]
                    self.root.after(0, lambda: self._draw_board(self.board_map, hl_from=fsq, hl_to=tsq, arrow_move=uci, flipped=flipped))
                    self._log(f"✅ Best: {moves[0].san}  ({moves[0].score})")

                side_str = "Black ♚" if is_black else "White ♔"
                cache_note = " (cached)" if result.cached else ""
                self._set_status(f"Done ✅  {side_str}  depth={depth}  {result.engine_used}{cache_note}")

            except Exception as e:
                self._log(f"❌ {e}\n{traceback.format_exc()}")
                self._set_status("Error — check log")

        threading.Thread(target=_run, daemon=True).start()

    # ── Display ──────────────────────────────────────────────────────────────
    def _display_moves(self, moves):
        for w_ in self.moves_frame.winfo_children():
            w_.destroy()
        medals = ["🥇", "🥈", "🥉"]
        for i, m in enumerate(moves):
            row = tk.Frame(self.moves_frame, bg="#2a3040", pady=5, padx=8)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=medals[i] if i < 3 else f"#{i + 1}", bg="#2a3040", fg=C["text"], font=("Segoe UI", 13)).pack(side=tk.LEFT)
            tk.Label(row, text=f"  {m.san}", bg="#2a3040", fg=C["text"], font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT)
            tk.Label(row, text=f"  ({m.move})", bg="#2a3040", fg=C["muted"], font=("Segoe UI", 9)).pack(side=tk.LEFT)
            if m.mate is not None and m.mate != 0:
                score_str, score_color = f"Mate {m.mate}", (C["accent"] if m.mate > 0 else C["red"])
            else:
                score_str = m.score
                try:
                    score_color = C["accent"] if float(score_str.replace("+", "")) >= 0 else C["red"]
                except Exception:
                    score_color = C["text"]
            tk.Label(row, text=score_str, bg="#2a3040", fg=score_color, font=("Segoe UI", 11, "bold")).pack(side=tk.RIGHT)
            if m.pv:
                tk.Label(row, text="  ↪ " + " ".join(m.pv[:5]), bg="#2a3040", fg="#6699aa", font=("Courier New", 8)).pack(anchor="w", pady=(0, 2))

    def _display_tactics(self, moves, tactic_results, phase, result):
        ta = self.tactics_area
        ta.config(state="normal")
        ta.delete("1.0", tk.END)
        phase_lbl = PHASE_LABEL.get(phase, phase)
        side_str = "Black ♚" if result.turn == chess.BLACK else "White ♔"
        ta.insert(tk.END, f"Phase: {phase_lbl}\n", "phase")
        ta.insert(tk.END, f"Engine: {result.engine_used}\n", "info")
        ta.insert(tk.END, f"Turn: {side_str}  — scores from this side's perspective\n", "info")
        if result.lc0_eval is not None:
            lc0_txt = f"{result.lc0_eval / 100:+.2f}" if abs(result.lc0_eval) < 9900 else "Mate"
            ta.insert(tk.END, f"🧠 Lc0/Maia strategic eval: {lc0_txt}\n", "info")
        if self.syzygy.is_available() and phase in (GamePhase.ENDGAME, GamePhase.TABLEBASE):
            ta.insert(tk.END, f"📖 Syzygy ({self.syzygy.file_count()} files) active\n", "info")
        ta.insert(tk.END, "═" * 36 + "\n", "sep")

        medals = ["🥇", "🥈", "🥉"]
        for i, (m, tr) in enumerate(zip(moves, tactic_results)):
            if m.move in ("—", ""):
                continue
            medal = medals[i] if i < 3 else f"#{i + 1}"
            ta.insert(tk.END, f"\n{medal} {m.san}  ({m.score})\n", "header")
            ta.insert(tk.END, "─" * 36 + "\n", "sep")
            if tr:
                for t_ in tr.tactics:
                    ta.insert(tk.END, f"{t_.icon} {t_.name}\n", "tactic")
                    ta.insert(tk.END, f"   {t_.desc}\n\n", "desc")
                ta.insert(tk.END, tr.explanation + "\n", "desc")
            if m.pv:
                ta.insert(tk.END, "\n↪ Suggested continuation:\n", "desc")
                ta.insert(tk.END, "  " + " ".join(m.pv[:6]) + "\n", "var")
            ta.insert(tk.END, "\n", "sep")

        if not any(m.move not in ("—", "") for m in moves):
            ta.insert(tk.END, "Game over or no moves available.\n", "desc")

        ta.config(state="disabled")
        self.notebook.select(self.tab_tactics)

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _log(self, msg: str):
        def _do():
            self.log.config(state="normal")
            self.log.insert(tk.END, msg + "\n")
            self.log.see(tk.END)
            self.log.config(state="disabled")
        self.root.after(0, _do)

    def _set_status(self, msg: str):
        self.root.after(0, lambda: self.status_var.set(msg))

    def _on_close(self):
        self.stack.close()
        self.root.destroy()


def main() -> None:
    """Console-script entry point (``chess-vision-ai``)."""
    from ..logging_setup import setup_logging
    setup_logging()
    root = tk.Tk()
    ChessAnalyzerApp(root)
    root.mainloop()
