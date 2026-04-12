"""
piece_trainer.py  —  Template Calibration Tool (Wizard Mode)
=============================================================
The program will guide you step-by-step to click on each piece.
After each click, it automatically moves to the next piece until all 12 are saved.

Steps:
  1. Click the "Select Board Region" button and draw around the chessboard
  2. The program says: "Click on the White King" → click it
  3. Automatically moves to: "Click on the White Queen" → click it
  4. ... until all 12 pieces are saved
  5. Done! ✅
"""

from sys import prefix
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageTk
import mss

# ── Config ────────────────────────────────────────────────────────────────────
TEMPLATE_DIR = Path(__file__).parent / "piece_templates"
TEMPLATE_DIR.mkdir(exist_ok=True)

PIECE_ORDER = [
    ("K", "♔ White King",   "White King",    "#ffffff"),
    ("Q", "♕ White Queen",  "White Queen",   "#ffffff"),
    ("R", "♖ White Rook",   "White Rook",    "#ffffff"),
    ("B", "♗ White Bishop", "White Bishop",  "#ffffff"),
    ("N", "♘ White Knight", "White Knight",  "#ffffff"),
    ("P", "♙ White Pawn",   "White Pawn",    "#ffffff"),
    ("k", "♚ Black King",   "Black King",    "#aaddff"),
    ("q", "♛ Black Queen",  "Black Queen",   "#aaddff"),
    ("r", "♜ Black Rook",   "Black Rook",    "#aaddff"),
    ("b", "♝ Black Bishop", "Black Bishop",  "#aaddff"),
    ("n", "♞ Black Knight", "Black Knight",  "#aaddff"),
    ("p", "♟ Black Pawn",   "Black Pawn",    "#aaddff"),
]

C = {
    "bg":     "#1a1d23",
    "panel":  "#22262f",
    "accent": "#00c98d",
    "text":   "#e8eaf0",
    "muted":  "#7a8099",
    "gold":   "#f6c90e",
    "dark_green": "#0d3d2a",
}


# ── Screen helpers ────────────────────────────────────────────────────────────

def take_full_screenshot() -> np.ndarray:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sshot = sct.grab(monitor)
        return cv2.cvtColor(np.array(sshot), cv2.COLOR_BGRA2BGR)


def capture_region(x, y, w, h) -> np.ndarray:
    with mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": w, "height": h}
        sshot = sct.grab(monitor)
        return cv2.cvtColor(np.array(sshot), cv2.COLOR_BGRA2BGR)


# ── Main App ──────────────────────────────────────────────────────────────────

class TrainerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("♟ Chess Piece Template Trainer — Wizard")
        self.root.configure(bg=C["bg"])
        self.root.geometry("920x700")
        self.root.resizable(True, True)

        self.board_img = None
        self.region = None
        self.current_step = 0
        self.saved_steps = set()
        self.saved_positions = {}
        self._canvas_w = 480          # ← default value
        self._canvas_h = 280          # ← default value

        for sym, *_ in PIECE_ORDER:
            # if (TEMPLATE_DIR / f"{sym}.png").exists():
            prefix = "w" if sym.isupper() else "b"
            if (TEMPLATE_DIR / f"{prefix}_{sym.upper()}.png").exists():
                self.saved_steps.add(sym)

        for i, (sym, *_) in enumerate(PIECE_ORDER):
            if sym not in self.saved_steps:
                self.current_step = i
                break
        else:
            self.current_step = len(PIECE_ORDER)

        self._build_ui()
        self._refresh_wizard_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        title_f = tk.Frame(self.root, bg=C["bg"])
        title_f.pack(fill=tk.X, padx=16, pady=(12, 0))
        tk.Label(title_f, text="♟ Template Trainer — Wizard",
                 bg=C["bg"], fg=C["accent"],
                 font=("Segoe UI", 17, "bold")).pack(side=tk.LEFT)
        tk.Label(title_f,
                 text="  |  Click on the square of each piece",
                 bg=C["bg"], fg=C["muted"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)

        btn_f = tk.Frame(self.root, bg=C["bg"])
        btn_f.pack(fill=tk.X, padx=16, pady=8)

        self.btn_select = tk.Button(
            btn_f,
            text="📷  Step 1: Select Board Region  (Draw around the chessboard)",
            command=self._select_region,
            bg=C["accent"], fg="#000",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=14, pady=7, cursor="hand2")
        self.btn_select.pack(side=tk.LEFT)

        tk.Button(btn_f, text="⏭ Skip current piece",
                  command=self._skip_step,
                  bg=C["panel"], fg=C["muted"],
                  font=("Segoe UI", 9),
                  relief="flat", padx=10, pady=7,
                  cursor="hand2").pack(side=tk.LEFT, padx=8)

        tk.Button(btn_f, text="💾 Finish & Exit",
                  command=self._finish,
                  bg="#2a3040", fg=C["text"],
                  font=("Segoe UI", 9),
                  relief="flat", padx=10, pady=7,
                  cursor="hand2").pack(side=tk.LEFT, padx=4)

        prog_outer = tk.Frame(self.root, bg=C["panel"], padx=12, pady=8)
        prog_outer.pack(fill=tk.X, padx=16)

        tk.Label(prog_outer, text="Progress  (0 of 12 saved)",
                 bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.progress_label = prog_outer.winfo_children()[-1]

        ind_row = tk.Frame(prog_outer, bg=C["panel"])
        ind_row.pack(anchor="w", pady=(6, 0))

        self.step_indicators = []
        for sym, eng, fa, color in PIECE_ORDER:
            col_frame = tk.Frame(ind_row, bg=C["panel"])
            col_frame.pack(side=tk.LEFT, padx=4)
            glyph_lbl = tk.Label(col_frame,
                                 text=eng.split()[0],
                                 bg=C["panel"], fg=C["muted"],
                                 font=("Arial", 20), width=2)
            glyph_lbl.pack()
            name_lbl = tk.Label(col_frame,
                                text=fa,
                                bg=C["panel"], fg=C["muted"],
                                font=("Segoe UI", 7), wraplength=60)
            name_lbl.pack()
            self.step_indicators.append((glyph_lbl, name_lbl))

        inst_outer = tk.Frame(self.root, bg=C["dark_green"],
                              padx=14, pady=10)
        inst_outer.pack(fill=tk.X, padx=16, pady=(8, 0))

        self.inst_glyph = tk.Label(inst_outer, text="?",
                                   bg=C["dark_green"], fg=C["accent"],
                                   font=("Arial", 40), width=2)
        self.inst_glyph.pack(side=tk.LEFT, padx=(0, 16))

        inst_text_col = tk.Frame(inst_outer, bg=C["dark_green"])
        inst_text_col.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.inst_counter = tk.Label(inst_text_col, text="",
                                     bg=C["dark_green"], fg=C["muted"],
                                     font=("Segoe UI", 9))
        self.inst_counter.pack(anchor="w")

        self.inst_main = tk.Label(inst_text_col, text="",
                                  bg=C["dark_green"], fg=C["accent"],
                                  font=("Segoe UI", 13, "bold"))
        self.inst_main.pack(anchor="w")

        self.inst_sub = tk.Label(inst_text_col, text="",
                                 bg=C["dark_green"], fg="#88ccaa",
                                 font=("Segoe UI", 10))
        self.inst_sub.pack(anchor="w")

        self.canvas = tk.Canvas(self.root, bg=C["panel"],
                                highlightthickness=1,
                                highlightbackground=C["accent"])
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        self.canvas.bind("<Button-1>", self._on_click)

        self.canvas.create_text(
            440, 120,
            text="First click the button above to capture the board",
            fill=C["muted"], font=("Segoe UI", 13),
            justify="center", tags="placeholder")

        self.status_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self.status_var,
                 bg=C["bg"], fg=C["accent"],
                 font=("Segoe UI", 9)).pack(pady=(0, 6))

    # ── Wizard refresh ────────────────────────────────────────────────────────

    def _refresh_wizard_ui(self):
        total = len(PIECE_ORDER)
        saved_count = len(self.saved_steps)

        self.progress_label.config(
            text=f"Progress  —  {saved_count} of {total} saved")

        for i, (sym, eng, fa, color) in enumerate(PIECE_ORDER):
            glyph_lbl, name_lbl = self.step_indicators[i]
            is_saved   = sym in self.saved_steps
            is_current = (i == self.current_step)

            if is_saved:
                glyph_lbl.config(bg="#003d28", fg=C["accent"])
                name_lbl.config(bg="#003d28", fg=C["accent"], text="✅ " + fa)
            elif is_current:
                glyph_lbl.config(bg=C["gold"], fg="#000")
                name_lbl.config(bg=C["panel"], fg=C["gold"], text="👉 " + fa)
            else:
                glyph_lbl.config(bg=C["panel"], fg=C["muted"])
                name_lbl.config(bg=C["panel"], fg=C["muted"], text=fa)

        if self.current_step < total:
            sym, eng, fa, color = PIECE_ORDER[self.current_step]
            remaining = total - saved_count
            self.inst_glyph.config(text=eng.split()[0], fg=color)
            self.inst_counter.config(
                text=f"Step {self.current_step + 1} of {total}  —  "
                     f"{saved_count} saved, {remaining} remaining")
            self.inst_main.config(
                text=f"Click on the  {fa}   ←   Click on the  {' '.join(eng.split()[1:])}")
            self.inst_sub.config(
                text=f"Find the piece on the chessboard and click on its square  |  piece code: [{sym}]")
        else:
            self.inst_glyph.config(text="✅", fg=C["accent"])
            self.inst_counter.config(text="")
            self.inst_main.config(
                text="All 12 pieces saved!")
            self.inst_sub.config(
                text="Close this window and run main.py.")

    def _advance_step(self):
        total = len(PIECE_ORDER)
        for i in range(self.current_step + 1, total):
            if PIECE_ORDER[i][0] not in self.saved_steps:
                self.current_step = i
                self._refresh_wizard_ui()
                return
        self.current_step = total
        self._refresh_wizard_ui()
        messagebox.showinfo(
            "✅ All saved!",
            f"All 12 pieces saved!\n"
            f"All 12 templates saved in:\n{TEMPLATE_DIR}\n\n"
            "You can now run main.py.")

    def _skip_step(self):
        self._advance_step()

    # ── Region selection ──────────────────────────────────────────────────────

    def _select_region(self):
        screenshot = take_full_screenshot()
        h_s, w_s = screenshot.shape[:2]
        pil_img = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))

        result_holder = [None]
        win = tk.Toplevel(self.root)
        win.attributes("-fullscreen", True)
        win.attributes("-topmost", True)
        win.configure(bg="black")

        cv = tk.Canvas(win, cursor="crosshair", bg="black",
                       highlightthickness=0)
        cv.pack(fill=tk.BOTH, expand=True)
        tk_img = ImageTk.PhotoImage(pil_img)
        cv.create_image(0, 0, anchor="nw", image=tk_img)
        cv.create_rectangle(0, 0, w_s, 56, fill="black")
        cv.create_text(w_s // 2, 28,
                       text="Drag around the chessboard   |   ESC = cancel",
                       fill="white", font=("Helvetica", 14, "bold"))

        state = {"start": None, "rect": None}

        def on_press(e):
            state["start"] = (e.x, e.y)

        def on_drag(e):
            if state["start"]:
                x0, y0 = state["start"]
                if state["rect"]:
                    cv.delete(state["rect"])
                state["rect"] = cv.create_rectangle(
                    x0, y0, e.x, e.y,
                    outline="#00FF88", width=2, dash=(6, 3))

        def on_release(e):
            if state["start"]:
                x0, y0 = state["start"]
                x1, y1 = e.x, e.y
                rx, ry = min(x0, x1), min(y0, y1)
                rw, rh = abs(x1 - x0), abs(y1 - y0)
                if rw > 40 and rh > 40:
                    result_holder[0] = (rx, ry, rw, rh)
                win.destroy()

        cv.bind("<ButtonPress-1>", on_press)
        cv.bind("<B1-Motion>", on_drag)
        cv.bind("<ButtonRelease-1>", on_release)
        win.bind("<Escape>", lambda e: win.destroy())
        self.root.wait_window(win)

        if result_holder[0]:
            self.region = result_holder[0]
            x, y, w, h = self.region
            self.board_img = capture_region(x, y, w, h)
            self._show_board()
            self.btn_select.config(
                text="📷  Re-select Region",
                bg="#1a4a38")
            self.status_var.set(
                f"✅ Board captured ({w}×{h}px)  —  "
                f"Now click on the piece shown above (step {self.current_step + 1}/12)")

    # ── Board rendering ───────────────────────────────────────────────────────

    def _show_board(self):
        if self.board_img is None:
            return

        self.canvas.update_idletasks()                        # ← ensure canvas is rendered
        self._canvas_w = max(self.canvas.winfo_width(), 480)  # ← store for use in _on_click
        self._canvas_h = max(self.canvas.winfo_height(), 280) # ← store for use in _on_click
        cw, ch = self._canvas_w, self._canvas_h

        self.canvas.delete("all")

        preview = cv2.resize(self.board_img, (cw, ch))
        pil_p = Image.fromarray(cv2.cvtColor(preview, cv2.COLOR_BGR2RGB))
        self._tk_img = ImageTk.PhotoImage(pil_p)
        self.canvas.create_image(0, 0, anchor="nw", image=self._tk_img)

        sq_w = cw // 8
        sq_h = ch // 8

        for i in range(9):
            self.canvas.create_line(i * sq_w, 0, i * sq_w, ch,
                                    fill="#00c98d44", width=1)
            self.canvas.create_line(0, i * sq_h, cw, i * sq_h,
                                    fill="#00c98d44", width=1)

        for fi, letter in enumerate("abcdefgh"):
            self.canvas.create_text(
                fi * sq_w + sq_w // 2, ch - 9,
                text=letter, fill="#00c98dcc",
                font=("Courier New", 8))

        for ri in range(8):
            self.canvas.create_text(
                9, ri * sq_h + sq_h // 2,
                text=str(8 - ri), fill="#00c98dcc",
                font=("Courier New", 8))

        for sym, eng, fa, color in PIECE_ORDER:
            if sym in self.saved_steps:
                pos = self.saved_positions.get(sym)
                if pos:
                    fc, fr = pos
                    x0, y0 = fc * sq_w, fr * sq_h
                    x1, y1 = x0 + sq_w, y0 + sq_h
                    self.canvas.create_rectangle(
                        x0, y0, x1, y1,
                        outline=C["accent"], width=2)
                    self.canvas.create_text(
                        x0 + sq_w // 2, y0 + sq_h // 2,
                        text=eng.split()[0],
                        fill=C["accent"],
                        font=("Arial", max(12, sq_w // 3), "bold"))

    # ── Click handler ─────────────────────────────────────────────────────────

    def _on_click(self, event):
        if self.board_img is None:
            self.status_var.set(
                "⚠  First click the 'Select Board Region' button!")
            return

        if self.current_step >= len(PIECE_ORDER):
            return

        # ← use the same dimensions stored in _show_board
        cw = self._canvas_w
        ch = self._canvas_h
        sq_w = cw // 8
        sq_h = ch // 8

        col = event.x // sq_w
        row = event.y // sq_h
        if not (0 <= col < 8 and 0 <= row < 8):
            return

        # Crop cell from original image
        h_b, w_b = self.board_img.shape[:2]
        cell_h = h_b // 8
        cell_w = w_b // 8
        y1, y2 = row * cell_h, (row + 1) * cell_h
        x1, x2 = col * cell_w, (col + 1) * cell_w
        cell = self.board_img[y1:y2, x1:x2]

        sym, eng, fa, color = PIECE_ORDER[self.current_step]
        # out_path = TEMPLATE_DIR / f"{sym}.png"
        prefix = "w" if sym.isupper() else "b"
        out_path = TEMPLATE_DIR / f"{prefix}_{sym.upper()}.png"
        cv2.imwrite(str(out_path), cell)

        self.saved_steps.add(sym)
        self.saved_positions[sym] = (col, row)

        file_letter = "abcdefgh"[col]
        rank_num = 8 - row
        self.status_var.set(
            f"✅  [{sym}] {fa}  saved from square {file_letter}{rank_num}"
            f"   —   {len(self.saved_steps)} / 12  done")

        self._show_board()
        self._advance_step()

    # ── Finish ────────────────────────────────────────────────────────────────

    def _finish(self):
        saved = list(TEMPLATE_DIR.glob("*.png"))
        messagebox.showinfo(
            "Saved",
            f"{len(saved)} templates saved in:\n{TEMPLATE_DIR}\n\n"
            "You can now run main.py for accurate piece detection.")
        self.root.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = TrainerApp(root)
    root.mainloop()
