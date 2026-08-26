# Graph Report - chess-vision-ai  (2026-08-26)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 228 nodes · 464 edges · 16 communities (11 shown, 5 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 17 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6d1f9d13`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14

## God Nodes (most connected - your core abstractions)
1. `ChessAnalyzerApp` - 26 edges
2. `MultiEngineStack` - 21 edges
3. `DownloadManager` - 15 edges
4. `TrainerApp` - 12 edges
5. `SyzygyManager` - 11 edges
6. `TacticalAnalyzer` - 11 edges
7. `DownloadDialog` - 10 edges
8. `SingleEngine` - 10 edges
9. `BoardDetector` - 10 edges
10. `GamePhase` - 9 edges

## Surprising Connections (you probably didn't know these)
- `test_few_pieces_but_above_syzygy_threshold_is_endgame()` --uses--> `GamePhase`  [INFERRED]
  tests/test_phase.py → chess_vision_ai/phase.py
- `test_kr_vs_k_is_tablebase()` --uses--> `GamePhase`  [INFERRED]
  tests/test_phase.py → chess_vision_ai/phase.py
- `test_middlegame_between_thresholds()` --uses--> `GamePhase`  [INFERRED]
  tests/test_phase.py → chess_vision_ai/phase.py
- `test_starting_position_is_opening()` --uses--> `GamePhase`  [INFERRED]
  tests/test_phase.py → chess_vision_ai/phase.py
- `main()` --calls--> `ChessAnalyzerApp`  [EXTRACTED]
  main.py → chess_vision_ai/ui/analyzer_app.py

## Import Cycles
- None detected.

## Communities (16 total, 5 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.11
Nodes (26): Central configuration: paths, constants and download URLs. Nothing in this…, Downloads and unpacks Stockfish, Lc0, the Maia network and Syzygy tablebases.…, Orchestrates Stockfish + Lc0/Maia + Syzygy and returns a single…, Chess Vision AI — screenshot-driven multi-engine chess analyzer. This package…, attach_ui_handler(), _CallbackHandler, get_logger(), Path (+18 more)

### Community 2 - "Community 2"
Cohesion: 0.17
Nodes (8): capture_region(), ndarray, Screen-capture helpers, isolated so they can be mocked in tests., take_full_screenshot(), Tk, Template Calibration Tool — wizard that walks the user through clicking each of…, TrainerApp, main()

### Community 3 - "Community 3"
Cohesion: 0.16
Nodes (7): MultiEngineStack, Board, AnalysisResult, MoveInfo, A single candidate move returned by the engine stack., Backwards-compatible dict view (legacy UI code expects dicts)., Full result of analysing one FEN with the multi-engine stack.

### Community 4 - "Community 4"
Cohesion: 0.25
Nodes (6): DownloadError, DownloadManager, Path, Exception, LogCB, ProgressCB

### Community 5 - "Community 5"
Cohesion: 0.16
Nodes (10): find_lc0(), find_stockfish(), Board, UCI engine process wrapper + discovery of local Stockfish/Lc0 binaries., A UCI engine process that transparently restarts itself if it dies., SingleEngine, _test_engine(), Limit (+2 more)

### Community 6 - "Community 6"
Cohesion: 0.20
Nodes (10): DetectionResult, Result of reading piece positions off a captured board image., generate_synthetic_templates(), load_templates(), Synthetic piece-template generation and loading. If the user never runs the…, _template_path(), BoardDetector, ndarray (+2 more)

### Community 7 - "Community 7"
Cohesion: 0.22
Nodes (14): board_map_to_fen(), infer_castling(), Pure functions for turning a detected board map into a valid FEN. Nothing here…, Drop physically-impossible extra pieces and guarantee both kings exist. Returns…, Infer castling rights from piece positions (king/rook still home)., Serialize a ``{"e4": "P", ...}`` map into a full FEN string., sanitize_board_map(), test_board_map_to_fen_starting_position_is_valid() (+6 more)

### Community 8 - "Community 8"
Cohesion: 0.30
Nodes (8): Typed data structures shared across the app. Using dataclasses instead of ad-…, TacticInfo, TacticResult, Board, Rule-based tactical motif detection: forks, pins, skewers, discovered attacks,…, ``score_before``/``score_after`` are pawns, relative to the mover., TacticalAnalyzer, Move

### Community 9 - "Community 9"
Cohesion: 0.27
Nodes (10): _encode_image(), is_available(), _orientation_hint(), _parse_response(), ndarray, Optional Vision-LLM fallback for piece detection. Design goal: keep LLM usage…, True if the optional dependency and an API key are both present., Thin wrapper around an OpenAI-compatible vision chat completion call. (+2 more)

### Community 10 - "Community 10"
Cohesion: 0.36
Nodes (8): _tactic_names(), test_checkmate_detected(), test_discovered_attack_when_blocker_moves_away(), test_knight_fork_on_king_and_rook(), test_material_gain_on_favorable_capture(), test_promotion_detected(), test_rook_pin_against_king(), test_rook_skewer_through_queen_to_rook()

## Knowledge Gaps
- **1 isolated node(s):** `chess-vision-ai`
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ChessAnalyzerApp` connect `Community 1` to `Community 0`, `Community 11`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Why does `MultiEngineStack` connect `Community 3` to `Community 0`, `Community 1`, `Community 12`, `Community 5`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Why does `DownloadManager` connect `Community 4` to `Community 0`, `Community 11`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `MultiEngineStack` (e.g. with `SingleEngine` and `AnalysisResult`) actually correct?**
  _`MultiEngineStack` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `chess-vision-ai` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.10668563300142248 - nodes in this community are weakly interconnected._