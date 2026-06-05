# Structural Patterns — build + validation (June 2026, worktree `feature/patterns`)

**Ask:** add more patterns (double-top/bottom, flag, triangle, up/down channel, fib retracements, even
counter-trend) and **draw them on the chart**.

## What was built
- **`patterns.py`** — pure detectors on OHLC bars, 20 tests:
  - `detect_channel` — linear-regression channel → direction (up/down/range) + `pos` (where price sits in
    the band, 0=lower/buy, 1=upper/sell). Validated on real gold 15m: correctly classified the down-day
    (06-01, pos 0.88 = top of down-channel), the strong up-day (05-28, pos 0.21 = bottom), and the flat
    day (06-04 → range).
  - `fib_levels` / `golden_pocket` / `active_swing` — retracement levels off the dominant swing.
  - `detect_double` — double-top/bottom via pivots + neckline.
- **`draw_patterns.py`** + **`pattern_scan.py`** — render channel (parallel trend-lines), fib levels, and
  necklines onto the chart via the node CLI draw tools; tagged `[AUTO-PATTERN]` so `--clear` removes only
  our drawings. `pattern_scan.py --chart <id>` reads the active chart at its own TF and annotates.
  Dry-run verified; **live draw deferred** (the backtest chart was busy and the live XAUUSD chart id
  wasn't identifiable from the tab list — ready to fire when the chart is free).

## Already in the engine (surprise) — and why they fire 0×
`double-top break`, `double-bottom break`, and `range/triangle breakout` are **already implemented** and
flagged ON — but they fired **0×** in 9 backtest days. Reading the code (`scalp_fast.py:666–679`): it's
**not a bug, it's strict-by-design**:
- Double-top fires only on `dtop AND strong-bearish-candle AND close < lo15` — two equal highs *and* a
  strong bearish candle *and* a break of the **entire 15-bar low**, all in one bar. Rare on 1m.
- Triangle needs `range15 < 35p` (real compression) + strong candle breaking the 15-bar extreme.

The textbook trigger is a break of the **neckline** (the valley between peaks, which is *higher* than
`lo15`), which `patterns.detect_double` computes and which would fire earlier/more often. **But:** we have
*zero* edge data on these (they never fired), and the cost finding says more signals = more spread bleed
unless they clear ~3p. So loosening them to the neckline trigger is a hypothesis to **backtest first**,
not a change to ship. `flag` is not implemented (momentum-style continuation is our worst family — skip).
Channel and fib are genuinely new.

## Does pattern context actually find the high-edge trades? (`pattern_edge.py`)
Retro-tagged every captured signal with its channel/fib context (no look-ahead) and compared edge after
the ~3p spread:

| subset | n | win% | net after −3p |
|---|---|---|---|
| ALL | 417 | 42% | −2.9p |
| good channel location (alone) | 43 | 37% | −4.7p |
| near fib level (alone) | 71 | 41% | −7.3p |
| inside golden pocket (alone) | 51 | 33% | −7.6p |
| **channel + fib confluence** | **9** | **56%** | **+0.2p ✅** |
| **channel + golden pocket** | **4** | **50%** | **+1.0p ✅** |
| no context | 277 | 45% | −0.7p |

**Conclusion:** individually the patterns make edge *worse*; only **confluence** clears the spread, and
only on samples too small to trust (n=4–9). Directionally encouraging (structure-stacking = real edge),
statistically unproven. **Not integrated into the engine.** Re-run on the ~19-day set (collecting now) to
confirm/kill the confluence signal.

## Caveats / next
- Validation used **intraday** (15m) context; the user's vision was **HTF (daily) channels/fib** — a
  daily-context test may behave differently and is worth running.
- `active_swing` uses crude global min/max; pivot-anchored swings could sharpen fib relevance.
- The patterns are a solid **drawing/context tool** regardless — they visualize where price sits in
  structure, which is useful for the manual/AI review even if not yet a mechanical edge.

## Artifacts (worktree `feature/patterns`)
`patterns.py`, `test_patterns.py` (20 tests), `draw_patterns.py`, `pattern_scan.py`, `pattern_edge.py`,
this doc. Nothing merged to `main`; nothing wired into `scalp_fast.py`.
