"""
Chess Board Analyzer v2.2 — Multi-Engine Professional Stack
============================================================
FIXES in v2.2:
  ✅ Black-side board: correct square mapping (rank 8 at bottom, file h at left)
  ✅ Auto-flip when Black turn selected — no manual checkbox needed
  ✅ Board display labels match actual orientation
  ✅ Arrow and highlights correct for both orientations
  ✅ Syzygy download: validates each file is real binary (not HTML 404)
  ✅ Syzygy: added Lichess mirror as additional source
  ✅ score.relative — evaluations from side-to-move perspective
  ✅ Eval bar always white-relative (white=top, black=bottom)
  ✅ Castling rights inferred from piece positions
"""

import sys, re, threading, time, shutil, zipfile, tarfile, gzip
import urllib.request, urllib.error, platform, os
from pathlib import Path

MISSING = []
for pkg, imp in [
    ("opencv-python","cv2"), ("numpy","numpy"),
    ("Pillow","PIL"), ("python-chess","chess"), ("mss","mss"),
]:
    try: __import__(imp)
    except ImportError: MISSING.append(pkg)
if MISSING:
    print(f"pip install {' '.join(MISSING)}")
    sys.exit(1)

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import cv2, numpy as np, chess, chess.engine, mss
from PIL import Image, ImageTk

BASE_DIR    = Path(__file__).parent
ENGINES_DIR = BASE_DIR / "engines"
SYZYGY_DIR  = BASE_DIR / "syzygy"
LCO_DIR     = BASE_DIR / "lc0"
LCO_NET_DIR = LCO_DIR  / "networks"
TEMPLATE_DIR= BASE_DIR / "piece_templates"
for _d in (ENGINES_DIR, SYZYGY_DIR, LCO_DIR, LCO_NET_DIR):
    _d.mkdir(parents=True, exist_ok=True)

_OS = platform.system()

SF18_URLS = {
    "bmi2": {
        "Windows": "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-x86-64-bmi2.zip",
        "Linux":   "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-ubuntu-x86-64-bmi2.tar",
        "Darwin":  "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-macos-x86-64-bmi2.zip",
    },
    "avx2": {
        "Windows": "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-x86-64-avx2.zip",
        "Linux":   "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-ubuntu-x86-64-avx2.tar",
        "Darwin":  "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-macos-x86-64-avx2.zip",
    },
    "base": {
        "Windows": "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-x86-64.zip",
        "Linux":   "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-ubuntu-x86-64.tar",
        "Darwin":  "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-macos-x86-64.zip",
    },
}
LCO_BIN_URLS = {
    "Windows": "https://github.com/LeelaChessZero/lc0/releases/download/v0.31.2/lc0-v0.31.2-windows-cpu-openblas.zip",
    "Linux":   "https://github.com/LeelaChessZero/lc0/releases/download/v0.31.2/lc0-v0.31.2-linux-cpu.tar.gz",
    "Darwin":  "https://github.com/LeelaChessZero/lc0/releases/download/v0.31.2/lc0-v0.31.2-macos-cpu.tar.gz",
}
MAIA_NET_URL  = "https://github.com/CSSLab/maia-chess/releases/download/v1.0/maia-1900.pb.gz"
MAIA_NET_NAME = "maia-1900.pb.gz"

SYZYGY_3PC = ["KBvK","KNvK","KPvK","KQvK","KRvK"]
SYZYGY_4PC = [
    "KBBvK","KBNvK","KBPvK","KBvKB","KBvKN","KBvKP",
    "KNNvK","KNPvK","KNvKN","KNvKP","KPPvK","KPvKP",
    "KQBvK","KQNvK","KQPvK","KQvKB","KQvKN","KQvKP","KQvKQ","KQvKR",
    "KRBvK","KRNvK","KRPvK","KRvKB","KRvKN","KRvKP","KRvKR",
]
SYZYGY_MIRRORS = [
    "https://tablebase.sesse.net/syzygy/3-4-5/",
    "https://chess.cygni.se/syzygy/3-4-5/",
    "https://tablebase.lichess.ovh/tables/standard/3-4-5/",
]

ENGINE_DEPTH         = 20
LCO_NODES            = 800
TOP_K_MOVES          = 3
ENDGAME_THRESHOLD    = 13
SYZYGY_THRESHOLD     = 7
MIDDLEGAME_THRESHOLD = 24

PIECES = {
    "P":("white","pawn"),  "N":("white","knight"), "B":("white","bishop"),
    "R":("white","rook"),  "Q":("white","queen"),  "K":("white","king"),
    "p":("black","pawn"),  "n":("black","knight"), "b":("black","bishop"),
    "r":("black","rook"),  "q":("black","queen"),  "k":("black","king"),
}
PIECE_VALUE = {chess.PAWN:1,chess.KNIGHT:3,chess.BISHOP:3,chess.ROOK:5,chess.QUEEN:9,chess.KING:100}
PIECE_NAME  = {chess.PAWN:"Pawn",chess.KNIGHT:"Knight",chess.BISHOP:"Bishop",
               chess.ROOK:"Rook",chess.QUEEN:"Queen",chess.KING:"King"}

FILES_NORMAL  = "abcdefgh"
FILES_FLIPPED = "hgfedcba"

# ═══════════════════════════════════════════════════════════════════════════════
class DownloadError(Exception): pass

class DownloadManager:
    def __init__(self, progress_cb=None, log_cb=None):
        self._progress = progress_cb or (lambda p,m: None)
        self._log      = log_cb or print
        self._cancel   = False

    def cancel(self): self._cancel = True

    def fetch(self, url, dest, label=""):
        self._log(f"⬇  {label}  ←  {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                done  = 0
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as f:
                    while True:
                        if self._cancel: raise DownloadError("cancelled")
                        chunk = resp.read(65536)
                        if not chunk: break
                        f.write(chunk); done += len(chunk)
                        if total:
                            self._progress(done*100//total,
                                f"{label}: {done/1048576:.1f}/{total/1048576:.1f} MB")
                        else:
                            self._progress(-1, f"{label}: {done/1048576:.1f} MB…")
        except urllib.error.URLError as e:
            raise DownloadError(f"URL error: {e}") from e
        return dest

    @staticmethod
    def extract_zip(src, dest_dir):
        dest_dir.mkdir(parents=True, exist_ok=True); out=[]
        with zipfile.ZipFile(src) as zf:
            for info in zf.infolist():
                name = Path(info.filename).name
                if not name or info.filename.endswith("/"): continue
                t = dest_dir/name
                with zf.open(info) as r, open(t,"wb") as w: shutil.copyfileobj(r,w)
                out.append(t)
                if _OS!="Windows": t.chmod(0o755)
        return out

    @staticmethod
    def extract_tar(src, dest_dir):
        dest_dir.mkdir(parents=True,exist_ok=True); out=[]
        mode = "r:gz" if str(src).endswith(".gz") else "r:*"
        with tarfile.open(src,mode) as tf:
            for m in tf.getmembers():
                if m.isfile():
                    m.name=Path(m.name).name; tf.extract(m,dest_dir)
                    p=dest_dir/m.name; out.append(p)
                    try: p.chmod(0o755)
                    except: pass
        return out

    @staticmethod
    def decompress_gz(src, dest):
        with gzip.open(src,"rb") as gz, open(dest,"wb") as f: shutil.copyfileobj(gz,f)

    @staticmethod
    def _is_valid_binary(path, min_bytes=128):
        if not path.exists() or path.stat().st_size < min_bytes: return False
        try:
            header = path.read_bytes()[:16]
            if header[0:1] in (b'<', b' ', b'\n', b'\r'): return False
            return True
        except: return False

    def download_stockfish18(self):
        self._log("🔽 Downloading Stockfish 18…")
        for variant in ["bmi2","avx2","base"]:
            url = SF18_URLS.get(variant,{}).get(_OS)
            if not url: continue
            tmp = ENGINES_DIR/f"sf18_{variant}_dl"
            try:
                self._progress(0, f"Stockfish 18 [{variant}]…")
                self.fetch(url, tmp, f"Stockfish 18 [{variant}]")
                exe  = "stockfish.exe" if _OS=="Windows" else "stockfish"
                ddir = ENGINES_DIR/f"sf18_{variant}"
                files = self.extract_zip(tmp,ddir) if str(url).endswith(".zip") else self.extract_tar(tmp,ddir)
                tmp.unlink(missing_ok=True)
                for f in files:
                    if "stockfish" in f.name.lower() and not f.name.endswith(".txt"):
                        t=ddir/exe; f.rename(t)
                        self._log(f"   🎯 SF18 [{variant}] → {t}"); return t
            except DownloadError as e:
                self._log(f"   ⚠ {e}")
                if tmp.exists(): tmp.unlink(missing_ok=True)
        return None

    def download_lc0(self):
        url = LCO_BIN_URLS.get(_OS)
        if not url: return None
        self._log("🔽 Downloading Lc0 (CPU)…")
        tmp = LCO_DIR/"lc0_dl"
        try:
            self.fetch(url,tmp,"Lc0 CPU binary")
            exe="lc0.exe" if _OS=="Windows" else "lc0"
            files = self.extract_zip(tmp,LCO_DIR) if str(url).endswith(".zip") else self.extract_tar(tmp,LCO_DIR)
            tmp.unlink(missing_ok=True)
            for f in files:
                if f.name.lower().startswith("lc0"):
                    t=LCO_DIR/exe
                    try: f.rename(t)
                    except: shutil.copy2(f,t); f.unlink(missing_ok=True)
                    self._log(f"   🎯 Lc0 → {t}"); return t
        except DownloadError as e:
            self._log(f"   ⚠ Lc0: {e}")
            if tmp.exists(): tmp.unlink(missing_ok=True)
        return None

    def download_maia_network(self):
        gz=LCO_NET_DIR/MAIA_NET_NAME; out=LCO_NET_DIR/MAIA_NET_NAME.replace(".gz","")
        if out.exists(): return out
        try:
            self.fetch(MAIA_NET_URL,gz,"Maia-1900 network")
            self.decompress_gz(gz,out); gz.unlink(missing_ok=True); return out
        except DownloadError as e:
            self._log(f"   ⚠ Maia: {e}"); return None

    def download_syzygy(self, include_4pc=True):
        names = SYZYGY_3PC[:] + (SYZYGY_4PC if include_4pc else [])
        exts  = [".rtbw",".rtbz"]
        total = len(names)*len(exts); done=0
        self._log(f"🔽 Syzygy {'3+4' if include_4pc else '3'}-piece ({total} files)…")
        self._log(f"   Destination: {SYZYGY_DIR}")
        for name in names:
            for ext in exts:
                fname=name+ext; dest=SYZYGY_DIR/fname; pct=done*100//total
                if self._is_valid_binary(dest,min_bytes=128):
                    done+=1; self._progress(pct,f"Syzygy: {fname} (cached)"); continue
                downloaded=False
                for mirror in SYZYGY_MIRRORS:
                    url=mirror+fname
                    try:
                        self._progress(pct,f"Syzygy: {fname}")
                        self.fetch(url,dest,f"Syzygy {fname}")
                        if self._is_valid_binary(dest,min_bytes=128):
                            done+=1; downloaded=True; break
                        else:
                            self._log(f"   ⚠ {fname} was HTML — trying next mirror")
                            dest.unlink(missing_ok=True)
                    except DownloadError as e:
                        self._log(f"   ⚠ {fname}@{mirror}: {e}")
                        if dest.exists(): dest.unlink(missing_ok=True)
                if not downloaded:
                    self._log(f"   ✗ Skipped {fname}")
        self._log(f"   ✅ Syzygy: {done}/{total} files in {SYZYGY_DIR}")
        return done

    def download_all(self, include_syzygy4=True):
        s={"sf18":None,"lc0":None,"maia":None,"syzygy":0}
        s["sf18"]=self.download_stockfish18(); s["lc0"]=self.download_lc0()
        s["maia"]=self.download_maia_network(); s["syzygy"]=self.download_syzygy(include_4pc=include_syzygy4)
        return s

# ═══════════════════════════════════════════════════════════════════════════════
def _test_engine(path, depth=3):
    try:
        e=chess.engine.SimpleEngine.popen_uci(path,timeout=8)
        e.analyse(chess.Board(),chess.engine.Limit(depth=depth)); e.quit(); return True
    except: return False

def find_stockfish():
    for variant in ["bmi2","avx2","base"]:
        exe="stockfish.exe" if _OS=="Windows" else "stockfish"
        p=ENGINES_DIR/f"sf18_{variant}"/exe
        if p.exists() and _test_engine(str(p)): return str(p)
    for c in ["stockfish-windows-x86-64-bmi2\\stockfish\\stockfish-windows-x86-64-bmi2.exe",
              "stockfish-windows-x86-64-avx2\\stockfish\\stockfish-windows-x86-64-avx2.exe",
              "stockfish-windows-x86-64\\stockfish\\stockfish-windows-x86-64.exe",
              "stockfish.exe","stockfish"]:
        for p in [str(BASE_DIR/c),c]:
            if Path(p).exists() and _test_engine(p): return p
    for exe in BASE_DIR.rglob("stockfish*.exe"):
        if _test_engine(str(exe)): return str(exe)
    found=shutil.which("stockfish")
    if found and _test_engine(found): return found
    raise RuntimeError(
        "Stockfish not found.\nClick '⬇ Download Engines' to auto-download.\n"
        "Or manually: https://stockfishchess.org/download/\n"
        "Place stockfish.exe next to main.py")

def find_lc0():
    exe="lc0.exe" if _OS=="Windows" else "lc0"; lp=LCO_DIR/exe
    nets=sorted(LCO_NET_DIR.glob("*.pb"),reverse=True)+sorted(LCO_NET_DIR.glob("*.pb.gz"),reverse=True)
    net=nets[0] if nets else None
    if lp.exists() and net and _test_engine(str(lp)): return str(lp),str(net)
    return None,None

# ═══════════════════════════════════════════════════════════════════════════════
class GamePhase:
    OPENING="opening"; MIDDLEGAME="middlegame"; ENDGAME="endgame"; TABLEBASE="tablebase"

def detect_phase(board):
    n=len(board.piece_map())
    if n<=SYZYGY_THRESHOLD: return GamePhase.TABLEBASE
    if n<=ENDGAME_THRESHOLD: return GamePhase.ENDGAME
    if n>=MIDDLEGAME_THRESHOLD: return GamePhase.OPENING
    return GamePhase.MIDDLEGAME

PHASE_LABEL={GamePhase.OPENING:"Opening",GamePhase.MIDDLEGAME:"Middlegame",
             GamePhase.ENDGAME:"Endgame",GamePhase.TABLEBASE:"Tablebase Endgame"}
PHASE_COLOR={GamePhase.OPENING:"#4fc3f7",GamePhase.MIDDLEGAME:"#f6c90e",
             GamePhase.ENDGAME:"#ff8800",GamePhase.TABLEBASE:"#00c98d"}

class SyzygyManager:
    def __init__(self,path=SYZYGY_DIR): self.path=path
    def is_available(self): return any(self.path.glob("*.rtbw"))
    def file_count(self): return len(list(self.path.glob("*.rtb*")))
    def max_pieces(self):
        mx=2
        for n in {f.stem for f in self.path.glob("*.rtbw")}:
            mx=max(mx,len([c for c in n.replace("v","") if c.isalpha()]))
        return mx
    def path_str(self): return str(self.path)

class SingleEngine:
    def __init__(self,path,options=None):
        self.path=path; self.options=options or {}; self._eng=None; self._dead=False; self._open()
    def _open(self):
        if self._eng:
            try: self._eng.quit()
            except: pass
        self._eng=chess.engine.SimpleEngine.popen_uci(self.path,timeout=10)
        for k,v in self.options.items():
            try: self._eng.configure({k:v})
            except: pass
        self._dead=False
    def analyse(self,board,limit,multipv=1):
        if self._dead: self._open()
        try:
            r=self._eng.analyse(board,limit,multipv=multipv)
            return r if isinstance(r,list) else [r]
        except chess.engine.EngineTerminatedError as e:
            self._dead=True
            m=re.search(r'exit code[:\s]+(\d+)',str(e),re.I)
            code=int(m.group(1)) if m else None
            if code==3221225477:
                raise RuntimeError(
                    f"Stockfish CPU incompatible (exit {code}).\n"
                    "Delete engines/sf18_bmi2/ folder, then click ⬇ Download Engines again.") from e
            self._open()
            r=self._eng.analyse(board,limit,multipv=multipv)
            return r if isinstance(r,list) else [r]
    def close(self):
        if self._eng:
            try: self._eng.quit()
            except: pass
            self._eng=None
    def __del__(self): self.close()

class MultiEngineStack:
    def __init__(self,syzygy):
        self.syzygy=syzygy; self._sf=None; self._lc0=None
        self._ready=threading.Event(); self._error=""
    def init(self,log_cb=None):
        log=log_cb or print; ok=False
        try:
            sf_path=find_stockfish(); opts={}
            if self.syzygy.is_available():
                opts["SyzygyPath"]=self.syzygy.path_str()
                opts["SyzygyProbeLimit"]=self.syzygy.max_pieces()
                log(f"📖  Syzygy: {self.syzygy.file_count()} files active")
            self._sf=SingleEngine(sf_path,opts); log(f"♜  Stockfish: {sf_path}"); ok=True
        except RuntimeError as e:
            self._error=str(e); log(f"❌ {e}")
        lp,np_=find_lc0()
        if lp and np_:
            try:
                self._lc0=SingleEngine(lp,{"WeightsFile":np_}); log(f"🧠  Lc0+{Path(np_).name}: ready")
            except Exception as e:
                log(f"⚠  Lc0: {e}"); self._lc0=None
        else: log("🧠  Lc0 not found (optional)")
        if ok: self._ready.set()
        return ok
    def is_ready(self): return self._ready.is_set() and self._sf is not None
    def status_text(self):
        p=[]
        if self._sf: p.append("♜ SF18 ✓")
        if self._lc0: p.append("🧠 Lc0/Maia ✓")
        if self.syzygy.is_available(): p.append(f"📖 Syzygy {self.syzygy.file_count()}f ✓")
        return "  ".join(p) if p else "⚠ no engine"
    def analyse(self,fen,depth=ENGINE_DEPTH,k=TOP_K_MOVES):
        board=chess.Board(fen); phase=detect_phase(board); turn=board.turn
        if board.is_checkmate(): return self._trivial("Checkmate!",phase,turn)
        if board.is_stalemate() or board.is_insufficient_material(): return self._trivial("Draw",phase,turn)
        if not self._sf: raise RuntimeError("Stockfish not ready")
        sf_res=self._sf.analyse(board,chess.engine.Limit(depth=depth),
                                multipv=min(k,max(1,board.legal_moves.count())))
        moves=self._parse_sf(sf_res,board)
        lc0_eval=None
        if self._lc0 and phase==GamePhase.MIDDLEGAME:
            try:
                r=self._lc0.analyse(board,chess.engine.Limit(nodes=LCO_NODES),multipv=1)
                if r:
                    sc=r[0]["score"].relative
                    lc0_eval=sc.score() if not sc.is_mate() else (10000 if sc.mate()>0 else -10000)
            except: pass
        eu="Stockfish 18"
        if lc0_eval is not None: eu+=" + Lc0/Maia"
        if self.syzygy.is_available() and phase in (GamePhase.ENDGAME,GamePhase.TABLEBASE): eu+=" + Syzygy"
        return {"moves":moves,"lc0_eval":lc0_eval,"phase":phase,"engine_used":eu,
                "syzygy_active":self.syzygy.is_available(),"turn":turn}
    @staticmethod
    def _trivial(msg,phase,turn):
        return {"moves":[{"move":"—","san":msg,"score":"0.00","mate":None,"pv":[],"score_cp":0}],
                "lc0_eval":None,"phase":phase,"engine_used":"—","syzygy_active":False,"turn":turn}
    @staticmethod
    def _parse_sf(results,board):
        out=[]
        for info in results:
            pv=info.get("pv",[])
            if not pv: continue
            move=pv[0]
            try: san=board.san(move)
            except: continue
            sr=info["score"].relative
            if sr.is_mate():
                mi=sr.mate(); ss=f"M{mi}"; cp=10000 if mi>0 else -10000
            else:
                cp=sr.score(); ss=f"{'+' if cp>=0 else ''}{cp/100:.2f}"; mi=None
            pv_sans,b2=[],board.copy()
            for mv in pv[:6]:
                try: pv_sans.append(b2.san(mv)); b2.push(mv)
                except: break
            out.append({"move":move.uci(),"san":san,"score":ss,"mate":mi,"pv":pv_sans,"score_cp":cp})
        return out
    def close(self):
        if self._sf: self._sf.close(); self._sf=None
        if self._lc0: self._lc0.close(); self._lc0=None
    def __del__(self): self.close()

# ═══════════════════════════════════════════════════════════════════════════════
class TacticalAnalyzer:
    def analyse_move(self,board,move,score_before,score_after):
        tactics=[]; ba=board.copy(); ba.push(move)
        if ba.is_checkmate(): tactics.append({"name":"Checkmate!","icon":"♛","color":"#ff4444","desc":"Game over!"})
        elif ba.is_check(): tactics.append({"name":"Check","icon":"⚔","color":"#ff8800","desc":"King is in check"})
        for fn in [self._fork,self._pin,self._skewer,self._disc]:
            t=fn(board,move,ba)
            if t: tactics.append(t)
        if board.is_capture(move):
            cap=board.piece_at(move.to_square); mov_=board.piece_at(move.from_square)
            if cap and mov_:
                cv=PIECE_VALUE.get(cap.piece_type,0); mv_=PIECE_VALUE.get(mov_.piece_type,0)
                if cv>mv_: tactics.append({"name":"Material Gain","icon":"💰","color":"#00c98d","desc":f"Win {PIECE_NAME[cap.piece_type]} with {PIECE_NAME[mov_.piece_type]}"})
                elif cv==mv_: tactics.append({"name":"Equal Exchange","icon":"⚖","color":"#aaa","desc":"Equal exchange"})
        if move.promotion: tactics.append({"name":"Promotion","icon":"👑","color":"#f6c90e","desc":"Pawn promotes!"})
        delta=score_after-score_before
        if not tactics and delta>0.5: tactics.append({"name":"Positional Improvement","icon":"📈","color":"#00c98d","desc":f"+{delta:.2f} pawns"})
        p=board.piece_at(move.from_square); pnam=PIECE_NAME.get(p.piece_type,"Piece") if p else "Piece"
        from_sq=chess.square_name(move.from_square); to_sq=chess.square_name(move.to_square)
        if score_after>2.0: qual="Excellent ✨"
        elif score_after>0.5: qual="Good 👍"
        elif score_after>-0.5: qual="Equal ⚖"
        else: qual="Defensive 🛡"
        tstr=" + ".join(t["name"] for t in tactics) if tactics else "Positional move"
        exp=f"{pnam} {from_sq}→{to_sq}\nTactic: {tstr}\nEval: {score_after:+.2f}  ({qual})"
        return {"tactics":tactics,"explanation":exp}
    def _fork(self,board,move,ba):
        mr=ba.piece_at(move.to_square)
        if not mr: return None
        thr=[ba.piece_at(s) for s in ba.attacks(move.to_square)
             if ba.piece_at(s) and ba.piece_at(s).color!=mr.color and ba.piece_at(s).piece_type!=chess.PAWN]
        if len(thr)>=2:
            return {"name":"Fork","icon":"🍴","color":"#ff6b35","desc":"Simultaneous attack on "+" & ".join(PIECE_NAME[p.piece_type] for p in thr[:3])}
        return None
    def _pin(self,board,move,ba):
        enemy=not board.turn
        for sq in chess.SQUARES:
            p=ba.piece_at(sq)
            if not p or p.color!=enemy: continue
            if ba.is_pinned(enemy,sq) and not board.is_pinned(enemy,sq):
                return {"name":"Pin","icon":"📌","color":"#9b59b6","desc":f"{PIECE_NAME[p.piece_type]} is pinned!"}
        return None
    def _skewer(self,board,move,ba):
        col=board.turn; mr=ba.piece_at(move.to_square)
        if not mr: return None
        for sq in ba.attacks(move.to_square):
            front=ba.piece_at(sq)
            if not front or front.color==col: continue
            if PIECE_VALUE.get(front.piece_type,0)<PIECE_VALUE.get(mr.piece_type,0): continue
            df=chess.square_file(sq)-chess.square_file(move.to_square)
            dr=chess.square_rank(sq)-chess.square_rank(move.to_square)
            bf=chess.square_file(sq)+(1 if df>0 else -1 if df<0 else 0)
            br=chess.square_rank(sq)+(1 if dr>0 else -1 if dr<0 else 0)
            if 0<=bf<=7 and 0<=br<=7:
                behind=ba.piece_at(chess.square(bf,br))
                if behind and behind.color!=col:
                    return {"name":"Skewer","icon":"🗡","color":"#e74c3c","desc":f"{PIECE_NAME[front.piece_type]} must move"}
        return None
    def _disc(self,board,move,ba):
        col=board.turn
        for sq in chess.SQUARES:
            p=ba.piece_at(sq)
            if not p or p.color!=col or sq==move.to_square: continue
            if p.piece_type not in (chess.BISHOP,chess.ROOK,chess.QUEEN): continue
            for t in ba.attacks(sq)-board.attacks(sq):
                tgt=ba.piece_at(t)
                if tgt and tgt.color!=col and PIECE_VALUE.get(tgt.piece_type,0)>=3:
                    orig=board.piece_at(move.from_square); o=PIECE_NAME.get(orig.piece_type,"Piece") if orig else "Piece"
                    return {"name":"Discovered Attack","icon":"💥","color":"#e67e22","desc":f"Moving {o} reveals {PIECE_NAME[p.piece_type]}'s attack!"}
        return None

# ═══════════════════════════════════════════════════════════════════════════════
def sanitize_board_map(bmap):
    MAX={"K":1,"k":1,"Q":9,"q":9,"R":10,"r":10,"B":10,"b":10,"N":10,"n":10,"P":8,"p":8}
    tracker,clean,warn={},{},[]
    for sq in sorted(bmap.keys()):
        p=bmap[sq]
        if not p: clean[sq]=None; continue
        cnt=tracker.get(p,0)
        if cnt<MAX.get(p,1): tracker[p]=cnt+1; clean[sq]=p
        else: warn.append(f"Extra {p} at {sq} removed"); clean[sq]=None
    if tracker.get("K",0)==0: clean["e1"]="K"; warn.append("White King added at e1")
    if tracker.get("k",0)==0: clean["e8"]="k"; warn.append("Black King added at e8")
    return clean,warn

def _infer_castling(bmap):
    r=""
    if bmap.get("e1")=="K":
        if bmap.get("h1")=="R": r+="K"
        if bmap.get("a1")=="R": r+="Q"
    if bmap.get("e8")=="k":
        if bmap.get("h8")=="r": r+="k"
        if bmap.get("a8")=="r": r+="q"
    return r or "-"

def board_map_to_fen(bmap,active="w",ep="-",hm=0,fm=1):
    castling=_infer_castling(bmap); rows=[]
    for rank in range(8,0,-1):
        empty,row=0,""
        for f in "abcdefgh":
            p=bmap.get(f"{f}{rank}")
            if p:
                if empty: row+=str(empty); empty=0
                row+=p
            else: empty+=1
        if empty: row+=str(empty)
        rows.append(row)
    return f"{'/'.join(rows)} {active} {castling} {ep} {hm} {fm}"

# ═══════════════════════════════════════════════════════════════════════════════
#  BoardDetector  — THE KEY FIX
#
#  Board from White's side (normal):
#    screen row 0 (top)    = rank 8   → rank = 8 - r
#    screen col 0 (left)   = file a   → file = "abcdefgh"[c]
#
#  Board from Black's side (flipped, like the screenshot):
#    screen row 0 (top)    = rank 1   → rank = r + 1
#    screen col 0 (left)   = file h   → file = "hgfedcba"[c]
# ═══════════════════════════════════════════════════════════════════════════════
def _template_path(sym):
    d=TEMPLATE_DIR/f"{sym}.png"
    if d.exists(): return d
    prefix="w" if sym.isupper() else "b"
    return TEMPLATE_DIR/f"{prefix}_{sym.upper()}.png"

def generate_synthetic_templates(cell_size=60):
    TEMPLATE_DIR.mkdir(parents=True,exist_ok=True)
    s,h=cell_size,cell_size//2
    def base(color):
        img=np.zeros((s,s,4),dtype=np.uint8)
        fill=(255,255,255,230) if color=="white" else (30,30,30,230)
        outline=(40,40,40,255) if color=="white" else (200,200,200,255)
        return img,fill,outline
    def pawn(c):
        img,f,o=base(c);cx=h
        cv2.circle(img,(cx,s//4),s//6,f,-1);cv2.circle(img,(cx,s//4),s//6,o,1)
        cv2.rectangle(img,(cx-s//8,s//4),(cx+s//8,s*3//4),f,-1);cv2.rectangle(img,(cx-s//8,s//4),(cx+s//8,s*3//4),o,1)
        cv2.rectangle(img,(cx-s//5,s*3//4),(cx+s//5,s-4),f,-1);cv2.rectangle(img,(cx-s//5,s*3//4),(cx+s//5,s-4),o,1)
        return img
    def rook(c):
        img,f,o=base(c);cx=h
        pts=np.array([[cx-s//4,4],[cx-s//5,4],[cx-s//5,s//5],[cx-s//8,s//5],[cx-s//8,4],
                       [cx+s//8,4],[cx+s//8,s//5],[cx+s//5,s//5],[cx+s//5,4],[cx+s//4,4],
                       [cx+s//4,s*3//4],[cx-s//4,s*3//4]],np.int32)
        cv2.fillPoly(img,[pts],f);cv2.polylines(img,[pts],True,o,1)
        cv2.rectangle(img,(cx-s//4,s*3//4),(cx+s//4,s-4),f,-1);cv2.rectangle(img,(cx-s//4,s*3//4),(cx+s//4,s-4),o,1)
        return img
    def knight(c):
        img,f,o=base(c);cx=h
        pts=np.array([[cx-s//5,s-4],[cx+s//4,s-4],[cx+s//4,s//3],[cx+s//8,s//5],[cx-s//8,s//6],[cx-s//5,s//3]],np.int32)
        cv2.fillPoly(img,[pts],f);cv2.polylines(img,[pts],True,o,1)
        cv2.circle(img,(cx-s//10,s//5),s//8,f,-1);cv2.circle(img,(cx-s//10,s//5),s//8,o,1)
        return img
    def bishop(c):
        img,f,o=base(c);cx=h
        cv2.circle(img,(cx,s//4),s//6,f,-1);cv2.circle(img,(cx,s//4),s//6,o,1)
        pts=np.array([[cx,s//8],[cx+s//5,s*2//3],[cx-s//5,s*2//3]],np.int32)
        cv2.fillPoly(img,[pts],f);cv2.polylines(img,[pts],True,o,1)
        cv2.rectangle(img,(cx-s//4,s*2//3),(cx+s//4,s-4),f,-1);cv2.rectangle(img,(cx-s//4,s*2//3),(cx+s//4,s-4),o,1)
        return img
    def queen(c):
        img,f,o=base(c);cx=h
        crown=np.array([[cx-s//3,s//2],[cx-s//4,s//5],[cx,s//3],[cx+s//4,s//5],[cx+s//3,s//2]],np.int32)
        cv2.fillPoly(img,[crown],f);cv2.polylines(img,[crown],False,o,1)
        for px in [cx-s//3,cx-s//4,cx,cx+s//4,cx+s//3]:
            cv2.circle(img,(px,s//5),3,f,-1);cv2.circle(img,(px,s//5),3,o,1)
        cv2.ellipse(img,(cx,s*2//3),(s//3,s//6),0,0,360,f,-1);cv2.ellipse(img,(cx,s*2//3),(s//3,s//6),0,0,360,o,1)
        cv2.rectangle(img,(cx-s//3,s*3//4),(cx+s//3,s-4),f,-1);cv2.rectangle(img,(cx-s//3,s*3//4),(cx+s//3,s-4),o,1)
        return img
    def king(c):
        img,f,o=base(c);cx=h
        cv2.rectangle(img,(cx-2,4),(cx+2,s//5),f,-1);cv2.rectangle(img,(cx-2,4),(cx+2,s//5),o,1)
        cv2.rectangle(img,(cx-s//8,s//8),(cx+s//8,s//6),f,-1);cv2.rectangle(img,(cx-s//8,s//8),(cx+s//8,s//6),o,1)
        cv2.ellipse(img,(cx,s*5//12),(s//4,s//5),0,0,360,f,-1);cv2.ellipse(img,(cx,s*5//12),(s//4,s//5),0,0,360,o,1)
        cv2.rectangle(img,(cx-s//3,s*3//5),(cx+s//3,s-4),f,-1);cv2.rectangle(img,(cx-s//3,s*3//5),(cx+s//3,s-4),o,1)
        return img
    makers={"pawn":pawn,"rook":rook,"knight":knight,"bishop":bishop,"queen":queen,"king":king}
    for sym,(color,ptype) in PIECES.items():
        cv2.imwrite(str(TEMPLATE_DIR/f"{sym}.png"),makers[ptype](color))

def load_templates(cell_size):
    if not all(_template_path(s).exists() for s in PIECES): generate_synthetic_templates(cell_size)
    out={}
    for sym in PIECES:
        p=_template_path(sym)
        if p.exists():
            img=cv2.imread(str(p),cv2.IMREAD_UNCHANGED)
            if img is not None: out[sym]=cv2.resize(img,(cell_size,cell_size))
    return out

class BoardDetector:
    def __init__(self): self.cell_size=60; self.templates={}

    def detect(self, img, flipped=False):
        h,w=img.shape[:2]
        self.cell_size=min(h,w)//8
        self.templates=load_templates(self.cell_size)
        raw=self._split_and_id(img,h,w,flipped)
        return sanitize_board_map(raw)

    def _split_and_id(self, img, h, w, flipped):
        ch,cw=h//8,w//8; cells={}
        for r in range(8):
            for c in range(8):
                if flipped:
                    # Black-side view: rank 1 at top, file h at left
                    rank=r+1
                    file_c=FILES_FLIPPED[c]
                else:
                    # White-side view: rank 8 at top, file a at left
                    rank=8-r
                    file_c=FILES_NORMAL[c]
                sq=f"{file_c}{rank}"
                cell=img[r*ch:(r+1)*ch, c*cw:(c+1)*cw]
                cells[sq]=self._id(cell)
        return cells

    def _id(self,cell):
        gray=cv2.cvtColor(cell,cv2.COLOR_BGR2GRAY)
        if gray.std()<22: return None
        cr=cv2.resize(cell,(self.cell_size,self.cell_size))
        best_sym,best_score=None,0.0
        for sym,tmpl in self.templates.items():
            s=self._ncc(cr,tmpl)
            if s>best_score: best_score=s; best_sym=sym
        if best_score>=0.30: return best_sym
        h,w=gray.shape; cy,cx=h//2,w//2; my,mx=h//5,w//5
        center=gray[cy-my:cy+my,cx-mx:cx+mx]
        if center.size==0 or center.std()<15: return None
        m=float(center.mean())
        if m>160: return "P"
        if m<90: return "p"
        return None

    def _ncc(self,cell,tmpl):
        c3=cell[:,:,:3] if cell.shape[2]>=3 else cell
        gc=cv2.cvtColor(c3,cv2.COLOR_BGR2GRAY).astype(np.float32)
        if tmpl.shape[2]==4:
            gt=cv2.cvtColor(tmpl[:,:,:3],cv2.COLOR_BGR2GRAY).astype(np.float32)
            mask=(tmpl[:,:,3]>128).astype(np.float32)
        else:
            gt=cv2.cvtColor(tmpl[:,:,:3],cv2.COLOR_BGR2GRAY).astype(np.float32)
            mask=np.ones(gt.shape,np.float32)
        n=mask.sum()
        if n==0: return 0.0
        mc=(gc*mask).sum()/n; mt=(gt*mask).sum()/n
        dc=(gc-mc)*mask; dt=(gt-mt)*mask
        return float((dc*dt).sum()/(np.sqrt((dc**2).sum()*(dt**2).sum())+1e-9))

# ═══════════════════════════════════════════════════════════════════════════════
def capture_region(x,y,w,h):
    with mss.mss() as s:
        return cv2.cvtColor(np.array(s.grab({"left":x,"top":y,"width":w,"height":h})),cv2.COLOR_BGRA2BGR)
def take_full_screenshot():
    with mss.mss() as s:
        return cv2.cvtColor(np.array(s.grab(s.monitors[1])),cv2.COLOR_BGRA2BGR)

# ═══════════════════════════════════════════════════════════════════════════════
class DownloadDialog:
    def __init__(self,parent,include_syzygy4=True):
        self.result={}
        self.win=tk.Toplevel(parent); self.win.title("⬇ Downloading Engines & Models")
        self.win.geometry("580x480"); self.win.configure(bg="#1a1d23")
        self.win.resizable(False,False); self.win.grab_set()
        tk.Label(self.win,text="⬇ Downloading Engine Stack",bg="#1a1d23",fg="#00c98d",font=("Segoe UI",14,"bold")).pack(pady=(16,4))
        tk.Label(self.win,text="Stockfish 18  ·  Lc0/Maia-1900  ·  Syzygy 3+4pc\n(~80 MB — runs once)",bg="#1a1d23",fg="#7a8099",font=("Segoe UI",9)).pack()
        tk.Label(self.win,
            text="⚠ If Stockfish shows 'Unsupported 16-bit': delete engines/sf18_bmi2/ and re-run.",
            bg="#1a1d23",fg="#ff8800",font=("Segoe UI",8)).pack(padx=20)
        self.progress_var=tk.IntVar(value=0)
        ttk.Progressbar(self.win,variable=self.progress_var,maximum=100,length=520).pack(pady=10,padx=20)
        self.msg_var=tk.StringVar(value="Starting…")
        tk.Label(self.win,textvariable=self.msg_var,bg="#1a1d23",fg="#e8eaf0",font=("Segoe UI",9),wraplength=540).pack()
        self.log_area=scrolledtext.ScrolledText(self.win,height=12,width=70,bg="#12151c",fg="#88ccaa",font=("Courier New",8),relief="flat",state="disabled")
        self.log_area.pack(padx=20,pady=8,fill=tk.BOTH,expand=True)
        btn_row=tk.Frame(self.win,bg="#1a1d23"); btn_row.pack(pady=(0,12))
        self.btn_cancel=tk.Button(btn_row,text="✖ Cancel",command=self._do_cancel,bg="#c0392b",fg="white",font=("Segoe UI",9,"bold"),relief="flat",padx=14,pady=5)
        self.btn_cancel.pack(side=tk.LEFT,padx=6)
        self.btn_close=tk.Button(btn_row,text="✔ Close",command=self.win.destroy,bg="#00c98d",fg="#000",font=("Segoe UI",9,"bold"),relief="flat",padx=14,pady=5,state="disabled")
        self.btn_close.pack(side=tk.LEFT,padx=6)
        self._dm=DownloadManager(progress_cb=self._on_progress,log_cb=self._on_log)
        threading.Thread(target=self._worker,kwargs={"include_syzygy4":include_syzygy4},daemon=True).start()
    def _do_cancel(self): self._dm.cancel(); self.msg_var.set("Cancelling…")
    def _on_progress(self,pct,msg):
        self.win.after(0,lambda:self.progress_var.set(max(0,pct)))
        self.win.after(0,lambda:self.msg_var.set(msg))
    def _on_log(self,msg):
        def _do():
            self.log_area.config(state="normal"); self.log_area.insert(tk.END,msg+"\n")
            self.log_area.see(tk.END); self.log_area.config(state="disabled")
        self.win.after(0,_do)
    def _worker(self,include_syzygy4=True):
        try: self.result=self._dm.download_all(include_syzygy4=include_syzygy4)
        except Exception as e: self._on_log(f"❌ Fatal: {e}")
        finally: self.win.after(0,self._done)
    def _done(self):
        self.progress_var.set(100); self.msg_var.set("Download complete ✅")
        self.btn_cancel.config(state="disabled"); self.btn_close.config(state="normal")

# ═══════════════════════════════════════════════════════════════════════════════
C={"bg":"#1a1d23","panel":"#22262f","accent":"#00c98d","text":"#e8eaf0","muted":"#7a8099",
   "sq_light":"#b0bec5","sq_dark":"#455a64","gold":"#f6c90e","red":"#ff6b6b","orange":"#ff8800"}

class ChessAnalyzerApp:
    FONT_MONO=("Courier New",9); FONT_UI=("Segoe UI",10)

    def __init__(self,root):
        self.root=root
        self.root.title("♟ Chess Analyzer v2.2 — Multi-Engine Stack")
        self.root.configure(bg=C["bg"]); self.root.geometry("1200x880"); self.root.minsize(950,700)
        self.detector=BoardDetector(); self.tactician=TacticalAnalyzer()
        self.syzygy=SyzygyManager(); self.stack=MultiEngineStack(self.syzygy)
        self._eng_lock=threading.Lock()
        self.region=None; self.board_img=None; self.board_map={}; self.last_fen=None
        self.fen_var=tk.StringVar(value="—"); self.turn_var=tk.StringVar(value="white")
        self.depth_var=tk.IntVar(value=ENGINE_DEPTH); self.status_var=tk.StringVar(value="Initializing…")
        self.phase_var=tk.StringVar(value="—"); self.eng_var=tk.StringVar(value="—")
        self._build_ui(); self._init_engine_async()

    def _is_flipped(self): return self.turn_var.get()=="black"

    def _build_ui(self):
        top=tk.Frame(self.root,bg=C["bg"],pady=8); top.pack(fill=tk.X,padx=16)
        tk.Label(top,text="♟ Chess Analyzer v2.2",bg=C["bg"],fg=C["accent"],font=("Segoe UI",18,"bold")).pack(side=tk.LEFT)
        tk.Label(top,text="  SF18 + Lc0/Maia + Syzygy  |  Black-side corrected",bg=C["bg"],fg=C["muted"],font=("Segoe UI",10)).pack(side=tk.LEFT)
        sb=tk.Frame(self.root,bg=C["panel"],pady=5); sb.pack(fill=tk.X,padx=16)
        tk.Label(sb,textvariable=self.status_var,bg=C["panel"],fg=C["accent"],font=("Segoe UI",9)).pack(side=tk.LEFT,padx=8)
        tk.Label(sb,textvariable=self.eng_var,bg=C["panel"],fg=C["gold"],font=("Segoe UI",9,"bold")).pack(side=tk.RIGHT,padx=8)
        content=tk.Frame(self.root,bg=C["bg"]); content.pack(fill=tk.BOTH,expand=True,padx=16,pady=8)
        left=tk.Frame(content,bg=C["bg"]); left.pack(side=tk.LEFT,fill=tk.BOTH)
        self.board_canvas=tk.Canvas(left,width=480,height=480,bg=C["panel"],highlightthickness=1,highlightbackground=C["accent"])
        self.board_canvas.pack(pady=(0,6)); self._draw_empty_board(False)
        ctrl=tk.Frame(left,bg=C["bg"]); ctrl.pack(fill=tk.X)
        b={"bg":C["accent"],"fg":"#000","font":("Segoe UI",9,"bold"),"relief":"flat","cursor":"hand2","padx":10,"pady":5}
        tk.Button(ctrl,text="📷 Select Region",command=self._select_region,**b).pack(side=tk.LEFT,padx=3)
        tk.Button(ctrl,text="🔍 Analyze",command=self._analyze,**b).pack(side=tk.LEFT,padx=3)
        tk.Button(ctrl,text="♻ Re-capture",command=self._recapture,**b).pack(side=tk.LEFT,padx=3)
        tk.Button(ctrl,text="⬇ Download Engines",command=self._open_download_dialog,
                  bg="#4a90d9",fg="white",font=("Segoe UI",9,"bold"),relief="flat",cursor="hand2",padx=10,pady=5).pack(side=tk.LEFT,padx=3)
        self.btn_retry=tk.Button(ctrl,text="🔄 Retry",command=self._retry_engine,
                                  bg="#c0392b",fg="white",font=("Segoe UI",9,"bold"),relief="flat",cursor="hand2",padx=8,pady=5)
        self.btn_retry.pack(side=tk.LEFT,padx=3); self.btn_retry.pack_forget()
        srow=tk.Frame(left,bg=C["bg"],pady=4); srow.pack(fill=tk.X)
        tk.Label(srow,text="Turn:",bg=C["bg"],fg=C["text"],font=self.FONT_UI).pack(side=tk.LEFT,padx=4)
        tk.Radiobutton(srow,text="White ♔",variable=self.turn_var,value="white",
                       bg=C["bg"],fg=C["text"],selectcolor=C["panel"],activebackground=C["bg"],
                       font=self.FONT_UI,command=self._on_turn_change).pack(side=tk.LEFT,padx=3)
        tk.Radiobutton(srow,text="Black ♚",variable=self.turn_var,value="black",
                       bg=C["bg"],fg=C["gold"],selectcolor=C["panel"],activebackground=C["bg"],
                       font=self.FONT_UI,command=self._on_turn_change).pack(side=tk.LEFT,padx=3)
        self.flip_indicator=tk.Label(srow,text="",bg=C["bg"],fg=C["orange"],font=("Segoe UI",8,"italic"))
        self.flip_indicator.pack(side=tk.LEFT,padx=6)
        tk.Label(srow,text="Depth:",bg=C["bg"],fg=C["text"],font=self.FONT_UI).pack(side=tk.LEFT,padx=4)
        tk.Spinbox(srow,from_=10,to=30,textvariable=self.depth_var,width=4,
                   bg=C["panel"],fg=C["text"],font=self.FONT_UI,buttonbackground=C["panel"],relief="flat").pack(side=tk.LEFT)
        prow=tk.Frame(left,bg=C["bg"],pady=2); prow.pack(fill=tk.X)
        tk.Label(prow,text="Game Phase:",bg=C["bg"],fg=C["muted"],font=("Segoe UI",9)).pack(side=tk.LEFT,padx=4)
        self.phase_lbl=tk.Label(prow,textvariable=self.phase_var,bg=C["bg"],fg=C["gold"],font=("Segoe UI",9,"bold"))
        self.phase_lbl.pack(side=tk.LEFT)
        self.coord_label=tk.Label(left,text="a  b  c  d  e  f  g  h",bg=C["bg"],fg=C["muted"],font=("Courier New",9))
        self.coord_label.pack()
        ef=tk.Frame(content,bg=C["bg"],padx=6); ef.pack(side=tk.LEFT,fill=tk.Y)
        tk.Label(ef,text="Eval",bg=C["bg"],fg=C["muted"],font=("Segoe UI",8)).pack()
        self.eval_canvas=tk.Canvas(ef,width=28,height=480,bg=C["panel"],highlightthickness=0); self.eval_canvas.pack()
        self.eval_label=tk.Label(ef,text="0.00",bg=C["bg"],fg=C["text"],font=("Segoe UI",8)); self.eval_label.pack()
        self.eval_side=tk.Label(ef,text="",bg=C["bg"],fg=C["muted"],font=("Segoe UI",7)); self.eval_side.pack()
        tk.Label(ef,text="Lc0",bg=C["bg"],fg=C["muted"],font=("Segoe UI",7)).pack(pady=(8,0))
        self.lc0_label=tk.Label(ef,text="—",bg=C["bg"],fg="#88ccaa",font=("Segoe UI",8)); self.lc0_label.pack()
        self._draw_eval_bar(0,chess.WHITE)
        right=tk.Frame(content,bg=C["panel"],padx=12,pady=10); right.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True,padx=(6,0))
        self.notebook=ttk.Notebook(right); self.notebook.pack(fill=tk.BOTH,expand=True)
        style=ttk.Style()
        style.configure("TNotebook",background=C["panel"],borderwidth=0)
        style.configure("TNotebook.Tab",background=C["bg"],foreground=C["text"],padding=[10,4],font=("Segoe UI",9))
        style.map("TNotebook.Tab",background=[("selected",C["accent"])],foreground=[("selected","#000")])
        self.tab_moves=tk.Frame(self.notebook,bg=C["panel"]); self.notebook.add(self.tab_moves,text="🎯 Moves")
        ff=tk.Frame(self.tab_moves,bg=C["panel"]); ff.pack(fill=tk.X,pady=(4,6))
        tk.Label(ff,text="FEN:",bg=C["panel"],fg=C["muted"],font=self.FONT_UI).pack(anchor="w")
        tk.Entry(ff,textvariable=self.fen_var,font=("Courier New",8),bg="#2d3240",fg=C["text"],relief="flat",width=46).pack(fill=tk.X)
        self.moves_frame=tk.Frame(self.tab_moves,bg=C["panel"]); self.moves_frame.pack(fill=tk.X)
        self.tab_tactics=tk.Frame(self.notebook,bg=C["panel"]); self.notebook.add(self.tab_tactics,text="💡 Tactics")
        self.tactics_area=scrolledtext.ScrolledText(self.tab_tactics,height=22,width=44,
            bg="#12151c",fg=C["text"],font=("Segoe UI",10),relief="flat",state="disabled",wrap=tk.WORD)
        self.tactics_area.pack(fill=tk.BOTH,expand=True)
        for tag,cfg in [("header",{"foreground":C["accent"],"font":("Segoe UI",11,"bold")}),
                        ("tactic",{"foreground":C["gold"],"font":("Segoe UI",10,"bold")}),
                        ("desc",{"foreground":C["text"],"font":("Segoe UI",9)}),
                        ("var",{"foreground":"#88ccaa","font":("Courier New",9)}),
                        ("phase",{"foreground":C["orange"],"font":("Segoe UI",9,"bold")}),
                        ("info",{"foreground":"#88ccff","font":("Segoe UI",9,"italic")}),
                        ("sep",{"foreground":C["muted"]})]:
            self.tactics_area.tag_config(tag,**cfg)
        self.tab_log=tk.Frame(self.notebook,bg=C["panel"]); self.notebook.add(self.tab_log,text="📋 Log")
        self.log=scrolledtext.ScrolledText(self.tab_log,height=22,width=44,
            bg="#12151c",fg=C["text"],font=self.FONT_MONO,relief="flat",state="disabled")
        self.log.pack(fill=tk.BOTH,expand=True)
        self.root.protocol("WM_DELETE_WINDOW",self._on_close)

    def _on_turn_change(self):
        flipped=self._is_flipped()
        if flipped:
            self.flip_indicator.config(text="🔄 Black's view — h at left, rank 1 at top")
            self.coord_label.config(text="h  g  f  e  d  c  b  a")
        else:
            self.flip_indicator.config(text="")
            self.coord_label.config(text="a  b  c  d  e  f  g  h")
        if self.board_map:
            self._draw_board(self.board_map,flipped=flipped)

    def _sq_to_canvas(self,sq_name,flipped):
        f="abcdefgh".index(sq_name[0]); r=int(sq_name[1])-1
        if flipped:
            col=7-f; row=r      # h leftmost, rank 1 at top
        else:
            col=f; row=7-r      # a leftmost, rank 8 at top
        return col,row

    def _draw_empty_board(self,flipped=False):
        c=self.board_canvas; sq=60; c.delete("all")
        for r in range(8):
            for f in range(8):
                color=C["sq_light"] if (r+f)%2==0 else C["sq_dark"]
                c.create_rectangle(f*sq,r*sq,(f+1)*sq,(r+1)*sq,fill=color,outline="")
        for row in range(8):
            rank_num=row+1 if flipped else 8-row
            c.create_text(6,row*sq+sq//2,text=str(rank_num),fill=C["muted"],font=("Courier New",8))

    def _draw_board(self,bmap,hl_from=None,hl_to=None,arrow_move=None,flipped=False):
        c=self.board_canvas; sq=60; c.delete("all")
        glyphs={"K":"♔","Q":"♕","R":"♖","B":"♗","N":"♘","P":"♙","k":"♚","q":"♛","r":"♜","b":"♝","n":"♞","p":"♟"}
        for sn in [f"{f}{r}" for r in range(1,9) for f in "abcdefgh"]:
            col,row=self._sq_to_canvas(sn,flipped)
            bg=C["sq_light"] if (col+row)%2==0 else C["sq_dark"]
            if sn==hl_from: bg="#a8d8a8"
            if sn==hl_to: bg=C["gold"]
            c.create_rectangle(col*sq,row*sq,(col+1)*sq,(row+1)*sq,fill=bg,outline="")
        for row in range(8):
            rank_num=row+1 if flipped else 8-row
            c.create_text(6,row*sq+sq//2,text=str(rank_num),fill=C["muted"],font=("Courier New",8))
        for col in range(8):
            file_lbl=FILES_FLIPPED[col] if flipped else FILES_NORMAL[col]
            c.create_text(col*sq+sq//2,478,text=file_lbl,fill=C["muted"],font=("Courier New",8))
        if arrow_move and len(arrow_move)>=4:
            try:
                fc,fr=self._sq_to_canvas(arrow_move[:2],flipped)
                tc,tr=self._sq_to_canvas(arrow_move[2:4],flipped)
                c.create_line(fc*sq+sq//2,fr*sq+sq//2,tc*sq+sq//2,tr*sq+sq//2,
                              fill="#00c98d",width=4,arrow=tk.LAST,arrowshape=(14,16,6))
            except: pass
        for sn,piece in bmap.items():
            if piece and piece in glyphs:
                pc,pr=self._sq_to_canvas(sn,flipped)
                cx_=pc*sq+sq//2; cy_=pr*sq+sq//2
                col_="white" if piece.isupper() else "#111"
                c.create_text(cx_+1,cy_+1,text=glyphs[piece],font=("Arial",26),fill="#0006")
                c.create_text(cx_,cy_,text=glyphs[piece],font=("Arial",26),fill=col_)

    def _draw_eval_bar(self,score_cp_relative,turn):
        import math
        c=self.eval_canvas; c.delete("all"); h=480
        white_cp=score_cp_relative if turn==chess.WHITE else -score_cp_relative
        clamped=max(-10.0,min(10.0,white_cp/100))
        pct=0.5+0.5*(2/(1+math.exp(-clamped*0.4))-1); wh=int(h*pct)
        c.create_rectangle(0,0,28,wh,fill="#e8e8e8",outline="")
        c.create_rectangle(0,wh,28,h,fill="#222",outline="")
        c.create_line(0,h//2,28,h//2,fill="#444",width=1)
        self.eval_label.config(text=f"{white_cp/100:+.2f}" if abs(white_cp)<9900 else "M")
        if white_cp>50: self.eval_side.config(text="♔ better",fg="#ddd")
        elif white_cp<-50: self.eval_side.config(text="♚ better",fg="#888")
        else: self.eval_side.config(text="equal",fg=C["muted"])

    def _init_engine_async(self):
        def _go():
            with self._eng_lock:
                ok=self.stack.init(log_cb=self._log)
                if ok:
                    self._set_status("Engine ready ✅")
                    self.root.after(0,lambda:self.btn_retry.pack_forget())
                    self.root.after(0,lambda:self.eng_var.set(self.stack.status_text()))
                else:
                    self._set_status("⚠ Stockfish not found — click '⬇ Download Engines'")
                    self.root.after(0,lambda:self.btn_retry.pack(side=tk.LEFT,padx=3))
        threading.Thread(target=_go,daemon=True).start()

    def _retry_engine(self):
        self.stack.close(); self._log("🔄 Retrying…"); self._set_status("Reconnecting…")
        self._init_engine_async()

    def _open_download_dialog(self):
        dlg=DownloadDialog(self.root,include_syzygy4=True)
        self.root.wait_window(dlg.win)
        self._log("🔄 Re-initializing after download…")
        self.stack.close(); self._init_engine_async()

    def _select_region(self):
        self.root.withdraw(); self.root.update(); time.sleep(0.2)
        result=self._run_selector(); self.root.deiconify()
        if result:
            self.region=result; x,y,w,h=result
            self._log(f"📐 Region: ({x},{y}) {w}×{h}")
            self._set_status(f"Region set: {w}×{h} — Press Analyze")
            self._capture_and_preview()
        else: self._set_status("Cancelled.")

    def _run_selector(self):
        sc=take_full_screenshot(); hs,ws=sc.shape[:2]
        pil=Image.fromarray(cv2.cvtColor(sc,cv2.COLOR_BGR2RGB))
        result=[None]
        win=tk.Toplevel(self.root); win.attributes("-fullscreen",True,"-topmost",True); win.configure(bg="black")
        cv=tk.Canvas(win,cursor="crosshair",bg="black",highlightthickness=0); cv.pack(fill=tk.BOTH,expand=True)
        tki=ImageTk.PhotoImage(pil); cv.create_image(0,0,anchor="nw",image=tki)
        cv.create_text(ws//2,30,text="Drag around the chessboard  |  ESC=cancel",fill="white",font=("Helvetica",15,"bold"))
        st={"s":None,"r":None}
        def press(e): st["s"]=(e.x,e.y)
        def drag(e):
            if st["s"]:
                if st["r"]: cv.delete(st["r"])
                st["r"]=cv.create_rectangle(*st["s"],e.x,e.y,outline="#00FF88",width=2,dash=(6,3))
        def release(e):
            if st["s"]:
                x0,y0=st["s"]; rx,ry=min(x0,e.x),min(y0,e.y); rw,rh=abs(e.x-x0),abs(e.y-y0)
                if rw>30 and rh>30: result[0]=(rx,ry,rw,rh)
                win.destroy()
        cv.bind("<ButtonPress-1>",press); cv.bind("<B1-Motion>",drag)
        cv.bind("<ButtonRelease-1>",release); win.bind("<Escape>",lambda e:win.destroy())
        self.root.wait_window(win); return result[0]

    def _recapture(self):
        if not self.region: self._set_status("No region selected."); return
        self._capture_and_preview()

    def _capture_and_preview(self):
        if not self.region: return
        x,y,w,h=self.region; self.board_img=capture_region(x,y,w,h)
        prev=cv2.resize(self.board_img,(480,480))
        pil=Image.fromarray(cv2.cvtColor(prev,cv2.COLOR_BGR2RGB))
        self._prev_tk=ImageTk.PhotoImage(pil)
        self.board_canvas.delete("all")
        self.board_canvas.create_image(0,0,anchor="nw",image=self._prev_tk)
        flipped=self._is_flipped()
        self._log(f"📸 Board captured. {'(Black-side view)' if flipped else '(White-side view)'}")

    def _analyze(self):
        if not self.region: messagebox.showwarning("","Please select a region first."); return
        if not self.stack.is_ready(): messagebox.showwarning("","Engine not ready. Click '⬇ Download Engines'."); return
        self._set_status("Analyzing…"); self._log("─"*44)

        def _run():
            try:
                x,y,w,h=self.region; self.board_img=capture_region(x,y,w,h)
                self._log("🔍 Detecting pieces…")
                flipped=self._is_flipped(); is_black=flipped
                self.board_map,warnings=self.detector.detect(self.board_img,flipped=flipped)
                n=sum(1 for v in self.board_map.values() if v)
                self._log(f"   {n} pieces found  (flipped={flipped})")
                for w_ in warnings: self._log(f"   ⚠ {w_}")
                active="b" if is_black else "w"
                fen=board_map_to_fen(self.board_map,active)
                self._log(f"   FEN: {fen}")
                try: board=chess.Board(fen)
                except ValueError as e:
                    self._log(f"❌ Invalid FEN: {e}"); self._set_status("FEN error"); return
                phase=detect_phase(board); phase_lbl=PHASE_LABEL.get(phase,phase); phase_col=PHASE_COLOR.get(phase,C["text"])
                self._log(f"   Phase: {phase_lbl}")
                self.root.after(0,lambda:self.phase_var.set(phase_lbl))
                self.root.after(0,lambda:self.phase_lbl.config(fg=phase_col))
                self.last_fen=fen
                self.root.after(0,lambda:self.fen_var.set(fen))
                self.root.after(0,lambda:self._draw_board(self.board_map,flipped=flipped))
                depth=self.depth_var.get(); self._log(f"⚙ Analyzing (depth={depth})…")
                try: result=self.stack.analyse(fen,depth=depth,k=TOP_K_MOVES)
                except RuntimeError as e:
                    self._log(f"❌ {e}")
                    self.root.after(0,lambda:self.btn_retry.pack(side=tk.LEFT,padx=3))
                    self._set_status("Engine error"); return
                moves=result["moves"]; lc0_eval=result["lc0_eval"]
                engine_used=result["engine_used"]; turn=result["turn"]
                self._log(f"   Engine: {engine_used}")
                self.root.after(0,lambda:self.eng_var.set(engine_used))
                if lc0_eval is not None:
                    lc0_txt=f"{lc0_eval/100:+.2f}" if abs(lc0_eval)<9900 else "M"
                    self.root.after(0,lambda:self.lc0_label.config(text=lc0_txt))
                else:
                    self.root.after(0,lambda:self.lc0_label.config(text="—"))
                best_cp=moves[0].get("score_cp",0) if moves else 0
                self.root.after(0,lambda:self._draw_eval_bar(best_cp or 0,turn))
                self.root.after(0,lambda:self._display_moves(moves))
                tactic_results=[]
                for mv_info in moves:
                    uci=mv_info["move"]
                    if uci in ("—",""): tactic_results.append(None); continue
                    try:
                        move_obj=chess.Move.from_uci(uci); sc_cp=mv_info.get("score_cp",0) or 0
                        ta=self.tactician.analyse_move(board,move_obj,0.0,sc_cp/100)
                        tactic_results.append(ta)
                    except: tactic_results.append(None)
                self.root.after(0,lambda:self._display_tactics(moves,tactic_results,board,phase,lc0_eval,engine_used,turn))
                if moves and moves[0]["move"] not in ("—",""):
                    uci=moves[0]["move"]; fsq,tsq=uci[:2],uci[2:4]
                    self.root.after(0,lambda:self._draw_board(self.board_map,hl_from=fsq,hl_to=tsq,arrow_move=uci,flipped=flipped))
                    self._log(f"✅ Best: {moves[0]['san']}  ({moves[0]['score']})")
                side_str="Black ♚" if is_black else "White ♔"
                self._set_status(f"Done ✅  {side_str}  depth={depth}  {engine_used}")
            except Exception as e:
                import traceback; self._log(f"❌ {e}\n{traceback.format_exc()}"); self._set_status("Error — check log")

        threading.Thread(target=_run,daemon=True).start()

    def _display_moves(self,moves):
        for w_ in self.moves_frame.winfo_children(): w_.destroy()
        medals=["🥇","🥈","🥉"]
        for i,m in enumerate(moves):
            row=tk.Frame(self.moves_frame,bg="#2a3040",pady=5,padx=8); row.pack(fill=tk.X,pady=2)
            tk.Label(row,text=medals[i] if i<3 else f"#{i+1}",bg="#2a3040",fg=C["text"],font=("Segoe UI",13)).pack(side=tk.LEFT)
            tk.Label(row,text=f"  {m['san']}",bg="#2a3040",fg=C["text"],font=("Segoe UI",13,"bold")).pack(side=tk.LEFT)
            tk.Label(row,text=f"  ({m['move']})",bg="#2a3040",fg=C["muted"],font=("Segoe UI",9)).pack(side=tk.LEFT)
            if m.get("mate") is not None and m["mate"]!=0:
                ss=f"Mate {m['mate']}"; sc=C["accent"] if m["mate"]>0 else C["red"]
            else:
                ss=m["score"]
                try: sc=C["accent"] if float(ss.replace("+",""))>=0 else C["red"]
                except: sc=C["text"]
            tk.Label(row,text=ss,bg="#2a3040",fg=sc,font=("Segoe UI",11,"bold")).pack(side=tk.RIGHT)
            pv=m.get("pv",[])
            if pv: tk.Label(row,text="  ↪ "+" ".join(pv[:5]),bg="#2a3040",fg="#6699aa",font=("Courier New",8)).pack(anchor="w",pady=(0,2))

    def _display_tactics(self,moves,tactic_results,board,phase,lc0_eval,engine_used,turn):
        ta=self.tactics_area; ta.config(state="normal"); ta.delete("1.0",tk.END)
        phase_lbl=PHASE_LABEL.get(phase,phase); side_str="Black ♚" if turn==chess.BLACK else "White ♔"
        ta.insert(tk.END,f"Phase: {phase_lbl}\n","phase")
        ta.insert(tk.END,f"Engine: {engine_used}\n","info")
        ta.insert(tk.END,f"Turn: {side_str}  — scores from this side's perspective\n","info")
        if lc0_eval is not None:
            lc0_txt=f"{lc0_eval/100:+.2f}" if abs(lc0_eval)<9900 else "Mate"
            ta.insert(tk.END,f"🧠 Lc0/Maia strategic eval: {lc0_txt}\n","info")
        if self.syzygy.is_available() and phase in (GamePhase.ENDGAME,GamePhase.TABLEBASE):
            ta.insert(tk.END,f"📖 Syzygy ({self.syzygy.file_count()} files) active\n","info")
        ta.insert(tk.END,"═"*36+"\n","sep")
        medals=["🥇","🥈","🥉"]
        for i,(m,tr) in enumerate(zip(moves,tactic_results)):
            if m["move"] in ("—",""): continue
            medal=medals[i] if i<3 else f"#{i+1}"
            ta.insert(tk.END,f"\n{medal} {m['san']}  ({m['score']})\n","header")
            ta.insert(tk.END,"─"*36+"\n","sep")
            if tr:
                if tr["tactics"]:
                    for t_ in tr["tactics"]:
                        ta.insert(tk.END,f"{t_['icon']} {t_['name']}\n","tactic")
                        ta.insert(tk.END,f"   {t_['desc']}\n\n","desc")
                ta.insert(tk.END,tr["explanation"]+"\n","desc")
            pv=m.get("pv",[])
            if pv:
                ta.insert(tk.END,"\n↪ Suggested continuation:\n","desc")
                ta.insert(tk.END,"  "+" ".join(pv[:6])+"\n","var")
            ta.insert(tk.END,"\n","sep")
        if not any(m["move"] not in ("—","") for m in moves):
            ta.insert(tk.END,"Game over or no moves available.\n","desc")
        ta.config(state="disabled"); self.notebook.select(self.tab_tactics)

    def _log(self,msg):
        def _do():
            self.log.config(state="normal"); self.log.insert(tk.END,msg+"\n")
            self.log.see(tk.END); self.log.config(state="disabled")
        self.root.after(0,_do)

    def _set_status(self,msg): self.root.after(0,lambda:self.status_var.set(msg))
    def _on_close(self): self.stack.close(); self.root.destroy()

# ═══════════════════════════════════════════════════════════════════════════════
def main():
    root=tk.Tk()
    ChessAnalyzerApp(root)
    root.mainloop()

if __name__=="__main__":
    main()
