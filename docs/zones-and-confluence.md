# Zones & Confluence — Structural Grading System (June 2026)

How a signal is graded: **a computed structural base (our zones) + a read confluence layer (LuxAlgo SMC +
Auto-Trendlines)**. More independent factors aligning at the entry price = higher grade (B → A → A+).

```
total grade = base (our zones: buy/sell zones, Key Levels, support/resistance, value areas)
            + confluence "+" (SMC order-blocks/structure/liquidity + Auto-Trendlines, read off the chart)
```

---

## 1. The base layer — our zones (`zones_sd.py`, computed from bars)

Pure-Python, computed from bars resampled to **4h + 1h** (no chart read → zero CDP load, fully
backtest-faithful). **Analysis TFs are 4h + 1h only — no daily-TF structure** (4h covers the higher-TF
structure for a scalp; daily zones/patterns are too distant to act on). Daily appears *only* as daily-derived
levels: **prior-day high/low (PDH/PDL)** and **prior-3-day value areas**. Four distinct sub-layers (do NOT
conflate — see [[zone-taxonomy]]):

### Buy / Sell ZONES (order-block boxes)
- A **buy zone** at a swing low, a **sell zone** at a swing high — **any color, any volume** (purely
  structural; volume/color belong to the support/resistance layer, not zones).
- Anchored to the swing that **CAUSED the move** (impulse-in + impulse-out), not a minor continuation swing;
  overlapping time-adjacent zones merge to the **extreme** (origin) swing.
- A **strong impulse candle** is itself a zone (its base) even without being a swing pivot.
- **Geometry:** low wick → body bottom (green→open, red→close); a small **indecision** candle uses the
  **whole candle** (high→low).
- **Polarity by position:** a zone below price acts as a buy zone, above price as a sell zone.
- **Invalidation:** a zone traversed both ways (price closed through ≥2×) is **consumed** → dropped.
- **Display:** boxes extend right (forward projection); a 1h zone fully covered by a 4h zone is dropped.

### Key Levels (the strongest zone tier)
- A zone that is **BOS-confirmed** AND has the **impulse → swing → impulse** structure (an opposite impulse
  wave into it + an impulse wave out). Scored (fresh = 1.0, decays per retest, dead after 3 reactions).
- **Fails on a WICK through the level** (not just a close).

### Support / Resistance LEVELS (horizontal lines — distinct from zones)
- **Support** = a big **green** high-volume candle; **resistance** = a big **red** high-volume candle.
- "High volume" = **fib-0.5 of the recent volume range** (this is the only place fib-0.5 lives — NOT on
  buy/sell zones).
- Must have a **small opposite-direction wick** AND a **rejection wick in its own direction** (no upper
  wick → can't be resistance; no lower wick → can't be support).
- **Polarity flip:** a broken support becomes resistance (and vice versa).
- A zone whose origin candle qualifies as a strong level candle is **labeled support/resistance** (not a
  generic buy/sell zone).

### Value areas
- Prior-3-day **POC / VAH / VAL** (volume profile), labeled by date. A closed day's profile is **fixed →
  cached** (computed once).

### Traditional key levels (`levels.py`)
- Horizontal levels with **touch-count strength** (more clean touches = stronger — the howtotrade book
  model), **round numbers**, **pivot points**. A `confluence()` scorer counts how many layers stack at a
  price. (Note the strength contrast: SMC/our zones = *fresh is strongest*; traditional levels = *more
  touches is strongest* — kept on separate layers.)

---

## 2. The confluence layer — LuxAlgo SMC + Auto-Trendlines (`smc.py`, read off the chart)

The **mandatory** "+" on top of the base. Read the actual indicators (not our approximation) — see
[[zone-taxonomy]] mapping. Each element a signal aligns with adds +1 to the grade:
- inside an **SMC order-block / FVG** box
- at an **SMC BOS / CHoCH** structure level
- at **SMC EQH / EQL** liquidity
- at an **SMC Strong / Weak High-Low** (the trailing strong/weak swing extremes — protected liquidity a
  scalp targets; a *Strong High* unbroken = counter-trend resistance, when taken the trend flips)
- on an **Auto-Trendline** (its diagonal lines projected to the current bar, read via chart-model eval)

≥2 confluences → bump the grade (B→A, A→A+). If the SMC indicator isn't on the chart → **WARN** (mandatory
input missing), grade not boosted.

### What the indicator actually draws (from the LuxAlgo source, `smc-indicator.txt`)
Default-on elements our reader sees: **5 internal order-block boxes** (no text), **BOS/CHoCH** lines+labels
(both internal-dashed and swing-solid), **EQH/EQL** (dotted), and **Strong/Weak High-Low** lines+labels.
FVG, Premium/Discount, and MTF levels are **off by default**. Key reading facts:
- Labels are matched **case-insensitively** (the indicator emits mixed case, e.g. `CHoCH`).
- Default **Mode = Historical** keeps *every* past BOS/CHoCH line → many stale labels at ~the same price.
  We **dedup** structure within the instrument tolerance (`SMC_TOL`) so repeats don't inflate the list.
- An **order block** = within the leg from the swing pivot to the break, the candle with the extreme
  high/low, boxed full **high→low**, extended right, **invalidated when price wicks through it** (default
  HIGHLOW mitigation). That wick-through kill **matches our own Key-Level rule** — independent confirmation.
  (LuxAlgo's box geometry differs from our body-bottom-by-color zones; ours is the base, theirs the "+".)

### Option A — read on the execution chart, store-and-hide (the chosen design)
Reading multi-TF SMC by **switching the chart's timeframe** every scan was slow (~140s) and hung the CDP
(the indicator takes a few seconds to render after a switch). Dedicated 4h/1h tabs were a headache and
don't sync with replay. **Chosen approach (Option A):**
- The indicators sit on the **execution / replay chart** (you add SMC to all charts; add Auto-Trendlines
  there too for its "+"). The engine reads them **on the current TF — no switching** (~0.4s).
- **Store-and-hide:** SHOW the indicators → wait to render → READ → **HIDE** them. The chart then shows
  only **our own clean drawings**, and the indicators don't constantly re-render. (Mirrors the existing TPO
  volume-profile read.) Indicator IDs are **discovered by name** each cycle (they change per session).
- The **HTF (4h/1h) structural layer is supplied by our computed zones**, so we don't need the indicators
  on a higher TF.

---

## 3. The HOURLY refresh (applies to BOTH execution and backtest)

**Everything structural is refreshed every hour: all zones, support/resistance, value areas, AND the SMC /
Auto-Trendline confluence — then re-drawn; the indicators stay hidden between refreshes.**

### Execution (cron)
- The SMC/trendline context is **cached** (`~/.tv_fast_<suffix>_smc.json`, TTL ~1h) so it's read at most
  ~once/hour, not every minute. On refresh: show → read → store → hide.
- Our zones are recomputed on the latest bars and **re-drawn** on the hour.
- Between refreshes the per-minute tick uses the **stored** zones/SMC for confluence — no chart reads, no
  re-render, no CDP load.

### Backtest (replay)
- **Date-faithful:** zones are recomputed from the **replay bars at the cursor**, and the SMC cache is
  **cleared at each step-refresh** (≈hourly of replay time) so the indicators are re-read at the cursor's
  date — not today's values.
- Same show → read → hide cycle, but only ~once per replay-hour (gentle on the CDP, not every step).

---

## 4. Modules
- `zones_sd.py` (+ `test_zones_sd.py`, 31 tests) — buy/sell zones, Key Levels, support/resistance, value areas
- `patterns.py` (+ tests, 20) — pivots, channel, fib, double-top/bottom
- `levels.py` (+ tests, 14) — traditional touch-count levels, round numbers, pivots, confluence
- `smc.py` (+ tests, 22) — read LuxAlgo SMC + Auto-Trendlines, store-and-hide, confluence scorer
- `draw_patterns.py`, `pattern_scan.py`, `draw_review.py` — chart drawing of all layers
- `scalp_fast.py` — confluence wired into the grade (flag `smc_confluence`, mandatory)

## 5. Status
- All modules built + tested (worktree `feature/5m-backtest`); live engine untouched.
- SMC + Auto-Trendlines confluence **wired into the grade** (Option A, store-and-hide).
- **Pending:** wire `zones_sd` in as the grade *base* (engine still grades off the older `refresh_zones`
  levels); run the one-day backtest (held by user).
- Connecting requires TradingView launched **with CDP** — see [[tradingview-cdp-launch]].
