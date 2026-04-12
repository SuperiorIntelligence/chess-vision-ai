<div align="center">

# ♟️ Chess Board Analyzer
### *Real-time AI-powered chess analysis from your screen*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Stockfish](https://img.shields.io/badge/Stockfish-18-00c98d?style=for-the-badge)](https://stockfishchess.org)
[![Lc0](https://img.shields.io/badge/Lc0-v0.31.2-f6c90e?style=for-the-badge)](https://lczero.org)
[![License](https://img.shields.io/badge/License-MIT-ff6b6b?style=for-the-badge)](LICENSE)

<br/>

> 📸 **Screenshot your chessboard → 🤖 AI detects all pieces → ♟ Multi-engine analysis → 💡 Tactical insights**

<br/>

![Chess Analyzer Banner](https://img.shields.io/badge/-%E2%99%9F%20%20Screenshot%20%20%E2%86%92%20%20%F0%9F%94%8D%20Detect%20%20%E2%86%92%20%20%E2%9A%99%EF%B8%8F%20Analyze%20%20%E2%86%92%20%20%F0%9F%92%A1%20Tactics-1a1d23?style=for-the-badge)

</div>

---

## 🌟 What Is This?

**Chess Board Analyzer** is a two-file Python toolkit that lets you point at *any* chessboard on your screen — whether it's on Chess.com, Lichess, a local engine GUI, or even a photo — and get **instant grandmaster-level analysis** powered by a professional 3-engine stack.

No manual FEN entry. No copy-pasting. Just click, capture, and analyze.

---

## 🗂️ Project Structure

```
chess-analyzer/
│
├── 📄 Identifying_chess_pieces.py   ← Step 1: Train the piece detector
├── 📄 main.py                       ← Step 2: Run the full analyzer
│
├── 📁 piece_templates/              ← Auto-created after training
├── 📁 engines/                      ← Auto-created, holds Stockfish 18
├── 📁 lc0/                          ← Auto-created, holds Lc0 + Maia
└── 📁 syzygy/                       ← Auto-created, holds tablebases
```

---

## ⚙️ Engine Stack

| Engine | Role | Size |
|--------|------|------|
| ♜ **Stockfish 18** | Tactics, checkmate, sharp lines | ~5 MB |
| 🧠 **Lc0 + Maia-1900** | Neural / strategic / positional understanding | ~50 MB |
| 📖 **Syzygy 3+4pc** | Perfect endgame tablebase play | ~70 MB |

### 🔄 Automatic Phase Switching

```
Opening   (≥ 24 pieces) → Stockfish 18
Middlegame              → Stockfish 18  +  Lc0/Maia strategic score
Endgame   (≤ 13 pieces) → Stockfish 18  +  Syzygy guidance
Tablebase (≤  7 pieces) → Syzygy perfect play
```

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/chess-analyzer.git
cd chess-analyzer
```

### 2. Install dependencies

```bash
pip install opencv-python numpy Pillow python-chess mss
```

### 3. Train the piece detector

```bash
python Identifying_chess_pieces.py
```

> Follow the wizard: click **"Select Board Region"**, draw around your chessboard, then click on each piece when prompted. Takes ~2 minutes once.

### 4. Launch the analyzer

```bash
python main.py
```

> On first launch, click **"⬇ Download Engines"** to auto-download Stockfish 18, Lc0, and Syzygy tablebases (~80 MB total, one-time only).

---

## 🎓 How To Use

### `Identifying_chess_pieces.py` — Template Trainer

This wizard-style tool teaches the AI what your chessboard's pieces look like.

```
Step 1 → Click "Select Board Region" → draw a box around your board
Step 2 → Click on the White King when prompted
Step 3 → Click on the White Queen ...
...
Step 12 → Click on the Black Pawn → Done! ✅
```

- ✅ Auto-saves each piece template as a `.png` file
- ✅ Shows real-time progress for all 12 piece types
- ✅ Skip button if a piece isn't currently on the board
- ✅ Re-run anytime to update templates for a different board theme

---

### `main.py` — Chess Analyzer

| Button | Action |
|--------|--------|
| 📷 **Select Region** | Draw around your chessboard once |
| 🔍 **Analyze** | Capture + detect + analyze in one click |
| ♻ **Re-capture** | Refresh the board image without re-selecting region |
| ⬇ **Download Engines** | Auto-download all engines (first run) |
| 🔄 **Retry** | Reconnect engines if something went wrong |

**Tabs in the right panel:**

- 🎯 **Moves** — Top 3 best moves with scores, UCI notation, and continuation lines
- 💡 **Tactics** — Detected tactical motifs: forks, pins, skewers, discovered attacks, promotions, material gain
- 📋 **Log** — Full engine log for debugging

---

## 🖥️ Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.10 or higher |
| opencv-python | any recent |
| numpy | any recent |
| Pillow | any recent |
| python-chess | any recent |
| mss | any recent |

Install everything at once:

```bash
pip install opencv-python numpy Pillow python-chess mss
```

---

## ⬇️ Manual Engine Downloads (if auto-download fails)

The app tries to auto-download all engines on first run. If anything fails, here are the **direct download links**:

---

### ♜ Stockfish 18

> Official page: **https://stockfishchess.org/download/**

| OS | Variant | Direct Link |
|----|---------|-------------|
| Windows | BMI2 (fastest) | [stockfish-windows-x86-64-bmi2.zip](https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-x86-64-bmi2.zip) |
| Windows | AVX2 | [stockfish-windows-x86-64-avx2.zip](https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-x86-64-avx2.zip) |
| Windows | Base (compatible) | [stockfish-windows-x86-64.zip](https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-x86-64.zip) |
| Linux | BMI2 | [stockfish-ubuntu-x86-64-bmi2.tar](https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-ubuntu-x86-64-bmi2.tar) |
| Linux | AVX2 | [stockfish-ubuntu-x86-64-avx2.tar](https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-ubuntu-x86-64-avx2.tar) |
| macOS | BMI2 | [stockfish-macos-x86-64-bmi2.zip](https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-macos-x86-64-bmi2.zip) |

**After downloading**, extract and place the executable here:
```
engines/sf18_bmi2/stockfish      ← Linux/macOS
engines/sf18_bmi2/stockfish.exe  ← Windows
```

> ⚠️ **If you get an "illegal instruction" or crash**, your CPU doesn't support that variant. Try the next one (avx2 → base).

---

### 🧠 Lc0 (CPU Build)

> Official page: **https://lczero.org/play/download/**

| OS | Direct Link |
|----|-------------|
| Windows | [lc0-v0.31.2-windows-cpu-openblas.zip](https://github.com/LeelaChessZero/lc0/releases/download/v0.31.2/lc0-v0.31.2-windows-cpu-openblas.zip) |
| Linux | [lc0-v0.31.2-linux-cpu.tar.gz](https://github.com/LeelaChessZero/lc0/releases/download/v0.31.2/lc0-v0.31.2-linux-cpu.tar.gz) |
| macOS | [lc0-v0.31.2-macos-cpu.tar.gz](https://github.com/LeelaChessZero/lc0/releases/download/v0.31.2/lc0-v0.31.2-macos-cpu.tar.gz) |

**After downloading**, place:
```
lc0/lc0        ← Linux/macOS
lc0/lc0.exe    ← Windows
```

---

### 🧠 Maia-1900 Network (for Lc0)

> Direct download (~8 MB):
> **https://github.com/CSSLab/maia-chess/releases/download/v1.0/maia-1900.pb.gz**

**After downloading**, decompress and place:
```
lc0/networks/maia-1900.pb
```

To decompress `.gz` manually:
```bash
# Linux / macOS
gunzip maia-1900.pb.gz

# Python (any OS)
python -c "import gzip, shutil; shutil.copyfileobj(gzip.open('maia-1900.pb.gz','rb'), open('maia-1900.pb','wb'))"
```

---

### 📖 Syzygy Tablebases

> Mirror 1: **https://tablebase.sesse.net/syzygy/3-4-5/**
> Mirror 2: **https://chess.cygni.se/syzygy/3-4-5/**

Download all `.rtbw` and `.rtbz` files for the piece combinations you need and place them in:
```
syzygy/
```

Recommended minimum (3-piece, ~1 MB):
```
KBvK.rtbw  KBvK.rtbz
KNvK.rtbw  KNvK.rtbz
KPvK.rtbw  KPvK.rtbz
KQvK.rtbw  KQvK.rtbz
KRvK.rtbw  KRvK.rtbz
```

Full 4-piece set adds ~68 MB and covers all standard endgames.

---

## 🐛 Troubleshooting

<details>
<summary><b>❌ "Stockfish not found" on startup</b></summary>

1. Click **"⬇ Download Engines"** in the app
2. If that fails, download manually from the links above
3. Place the binary in `engines/sf18_bmi2/stockfish` (or `stockfish.exe`)
4. Click **"🔄 Retry"**

</details>

<details>
<summary><b>❌ Engine crashes with "illegal instruction" / exit code 3221225477</b></summary>

Your CPU doesn't support the BMI2 instruction set. Download the **AVX2** or **Base** variant of Stockfish instead.

</details>

<details>
<summary><b>❌ Pieces not detected correctly</b></summary>

1. Re-run `Identifying_chess_pieces.py`
2. Make sure your chessboard is fully visible and not partially covered
3. Use a clean, standard board theme for best results
4. Try a larger/clearer board size on screen

</details>

<details>
<summary><b>❌ Lc0 not working</b></summary>

Lc0 is **optional** — the app works perfectly with just Stockfish. If you want Lc0:

1. Make sure `lc0/lc0` (or `lc0.exe`) exists and is executable
2. Make sure `lc0/networks/maia-1900.pb` exists (decompressed, not `.gz`)
3. On Linux/macOS: `chmod +x lc0/lc0`

</details>

<details>
<summary><b>❌ tkinter not found (Linux)</b></summary>

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

</details>

---

## 🔬 Tactical Motifs Detected

| Icon | Tactic | Description |
|------|--------|-------------|
| 🍴 | **Fork** | One piece attacks two or more enemy pieces simultaneously |
| 📌 | **Pin** | An enemy piece is pinned against a more valuable piece behind it |
| 🗡 | **Skewer** | A high-value piece is attacked, forcing it to move and expose a weaker piece |
| 💥 | **Discovered Attack** | Moving one piece opens a line of attack for another |
| ⚔ | **Check** | The king is under direct attack |
| ♛ | **Checkmate** | The king has no escape — game over |
| 👑 | **Promotion** | A pawn reaches the back rank and transforms |
| 💰 | **Material Gain** | A capture wins material advantage |

---

## 📸 Workflow at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   1. Open any chess game on your screen                     │
│                                                             │
│   2. Run: python main.py                                    │
│                                                             │
│   3. Click "📷 Select Region"                               │
│      └─ Draw a box around your board                        │
│                                                             │
│   4. Click "🔍 Analyze"                                     │
│      ├─ Board is captured from screen                       │
│      ├─ Pieces are detected using your templates            │
│      ├─ FEN is generated automatically                      │
│      ├─ Multi-engine stack analyzes the position            │
│      └─ Results shown: top moves + tactical breakdown       │
│                                                             │
│   5. Best move is highlighted with an arrow on the board ✅ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 File Overview

### `Identifying_chess_pieces.py`
A guided wizard that captures your chessboard's piece images and saves them as templates. These templates are used by the AI detector in `main.py` to recognize pieces. Run this once per board theme/style.

### `main.py`
The main application. Captures the board from your screen, detects pieces using the saved templates, generates a FEN string, feeds it to the multi-engine stack (Stockfish 18 + Lc0/Maia + Syzygy), and displays top moves with full tactical commentary.

---

## 🤝 Contributing

Pull requests are welcome! Some ideas for contributions:

- 🎨 Support for more board themes out of the box
- 🌐 Web interface instead of tkinter
- 📱 Support for mobile screenshots
- 🔔 Real-time mode (auto-analyze on board change detection)
- 🗣️ Voice output for move suggestions

---

## 📜 License

This project is licensed under the **MIT License** — feel free to use, modify, and distribute.

---

<div align="center">

**Made with ♟️ and Python**

*If this helped your chess game, consider leaving a ⭐ on GitHub!*

</div>
