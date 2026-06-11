---
name: scalp-suite
description: Master scalp skill — the 4 LuxAlgo-based strategies tested 2026-06 (Order Flow VWAP Deviation · Volume Profile nodes · Peak Activity Range + Liquidity Delta Profiler · Swing Breakout Sequence). Universal rules (per-instrument TP/SL scaling for gold/EUR/GBP/AUD/NZD/JPY, BE, no-trade, candle-close) + a regime selector (trend→SBS, range→mean-reversion). SUPERSEDES skills/discretionary-trade. Folds in skills/ofvwap-scalp, vp-node-scalp, par-liqdelta-scalp.
---

# Scalp Suite — 4 indicator strategies (XAUUSD + FX)

**One framework, four strategies — checked IN SEQUENCE on the SAME chart.** At each decision point, cycle the indicators
**one at a time: show indicator → read its signal → hide → show next**. NEVER stack the heavy ones (VP-Node / PAR / LDP)
— two+ heavy profiles visible at once blows Pine memory and crashes (OFVWAP + SBS are light and may co-exist). This
sequence-toggle is also the **live workflow** (flip each indicator on/off on the one chart — no per-pair layouts needed).
All 4 are API-readable (OFVWAP `study_values` · SBS/PAR/LDP/VP-Node `pine_labels`/`boxes`) so each is read while solo-visible.
PEPPERSTONE feed (real volume). This **supersedes `skills/discretionary-trade`** (SBS/CRT/SMC). The per-strategy deep-dives live in `skills/ofvwap-scalp`,
`skills/vp-node-scalp`, `skills/par-liqdelta-scalp`; this file is the single operating reference.

---

## 0. REGIME SELECTOR (decide first)
- **Trend / directional day** (sloping bias, expansion) → **S4 Swing Breakout Sequence** is the edge (the Jun 1–5
  trend-heavy week: SBS led every symbol). Also S1 trend-pullbacks.
- **Range / round-trip / dip-buy day** (flat value, edges holding) → **mean-reversion**: S1 (band fades), S2 (VP edge
  fades), S3 (PAR rejection / liquidity sweep reversal).
- **Mid-range / chop / on the POC / between nodes** → **NO TRADE.**

---

## 1. UNIVERSAL RULES (all 4 strategies)

### Pip conventions
- **Gold (XAUUSD):** 1.00 price = **10 pips**; 100p = $10 = 10.0 pts. Runs 250–700 p/day.
- **FX:** 1 pip = 0.0001 (JPY pairs: 1 pip = 0.01). EUR/AUD/NZD ~40–110 p/day, GBP ~33–154, JPY ~42–72.

> ### 🚨 CRITICAL — POINTS ≠ PIPS on gold (10× trap — verified the hard way, Jun 2026)
> **Gold 1.00 point = 10 pips.** A VWAP↔band gap of e.g. **17.86 points = ~178 PIPS** (NOT 17 pips). When reading OFVWAP
> band/VWAP distances off price, **multiply the point-gap by 10 to get pips.** Mis-reading points as pips makes every setup
> look 1/10th its size → you wrongly skip TP1-sized trades as "too small." This single bug invalidated a full set of walks
> (Jun 1–3) where band→VWAP reverts of ~170–180 pips were called "+17p, sub-TP1, skip."
> **TAKE the signals:** on gold the **VWAP cross** (close above blue = long / below = short) and the **band reject/reclaim**
> (touch band → revert toward VWAP) are **~180-pip (VWAP↔band) to ~360-pip (band-to-band)** moves — they fire several times a
> day and CLEAR TP1 (70–100p). They are NOT rare and NOT sub-target. A "0-trade / over-filtered" day is almost always this
> error, not a genuine no-setup day. Sanity-check any "too small to trade" call by converting points→pips first.

### Per-instrument TP/SL/BE scaling (LOGIC is identical; only the numbers scale — never use gold's 70–100p on FX)
| Instrument | TF | SL | TP1 | TP2 | BE |
|---|---|---|---|---|---|
| GOLD | 5m/15m | ≤50p ($5) | 70–100p | structure | +40p / 1R |
| EURUSD | 15m / 5m | 7–12 / 4–7p | 15–25 (20) / 8–14 (10) | 25–45 / 15–25 | ~1R |
| GBPUSD | 15m / 5m | 10–18 / 6–10p | 20–35 (25–30) / 12–20 (15–20) | 35–70 / 20–35 | ~1R |
| AUDUSD/NZDUSD | 15m / 5m | 7–10 / 4–7p | 15–20 / 8–14 | 25–40 / 15–25 | ~1R |
| USDJPY | 15m / 5m | 10–15 / 6–9p | 20–30 / 12–18 | 30–60 / 20–35 | ~1R |

### Discipline (all)
- **TP1 = clean path to the next blocking level** (don't force the max). **TP1 blocked before the min → WAIT/REJECT.**
- **TP2 = structure only** (next node/zone/edge/swing); never invented. No TP3.
- **BE after ~+40p (gold) / ~1R (FX). Never widen after BE.**
- **SL must be LOGICAL** (beyond the swept extreme / edge / structure). **If the logical SL is wider than the target
  allows → SKIP** (or reduce / classify wider-intraday). **NEVER put the SL in the noise to force R** (this lost −50p
  on the Jun-1 verified walk).
- **Candle-CLOSE confirmation** (not wicks). 15m = location/structure; 5m = time the entry tighter.
- **No-trade:** mid-range, on POC, between nodes, fully-consumed zone, weak candle, move already mostly traveled.

---

## 2. THE FOUR STRATEGIES

### S1 — Order Flow VWAP Deviation [LuxAlgo]  (`ofvwap-scalp`)
Blue = anchored session VWAP (magnet + gate); cloud = ±std-dev bands; order-flow tint = delta proxy (fade circuit-
breaker); gold verticals = session resets; "Stops Triggered" = stop-run flag.
- **Loop:** band tag → reject → travel to VWAP → VWAP is the GATE (reject = continue; close-through = flip).
- **A-grade entry:** band **sweep-and-reclaim** (pierce + close back inside). RANGE = fade bands to VWAP; TREND =
  pullback-to-VWAP with slope. Tint must flip to fade. Pair targets off the VP nodes when available.
- ⚠ **VERIFIED (Jun-8 gold bar-by-bar): RUN OFVWAP ON 5m, NOT 15m.** On a trend day the pullback-to-VWAP and its
  rejection happen inside a *single 15m bar* → a 15m entry needs a >50p stop → it SKIPS its own signals. 5m fits the
  ≤50p stop and takes them (Jun 8: ~+280–400p on 5m vs ~0 on 15m, 3–4 trades). Use 15m only for the trend/regime read.

### S2 — Volume Profile with Node Detection [LuxAlgo] — TRIMMED  (`vp-node-scalp`)
POC (magnet/chop), HVN (acceptance/stall/S-R), LVN (thin/fast), VAH/VAL (edges).
- **2 models:** **Edge Reversal** (sweep edge/LVN, candle closes back inside → revert to POC/HVN); **LVN Continuation**
  (strong close through a level into thin volume → run). TP1 = nearest HVN/POC; LVN between = let it run, HVN between = bank it.
- ✅ **Read node levels via `data_get_pine_labels{study_filter:"Node Detection"}`** (HVN/LVN/POC). It's the ONLY
  API-readable VP. **Trim Profile Lookback to ~40–60 (`in_25`)** to stop the memory crash, then it renders + reads fine.
  (The *native* Periodic/Session VP has NO level API — eyeball only — so don't use it for the automated read.)

### S3 — Peak Activity Range + Liquidity Delta Profiler [LuxAlgo]  (`par-liqdelta-scalp`)
**PAR = LOCATION:** a volume-spike range — high/low + solid midpoint (fair value) + dashed POC + signals; modes
Breakout (close beyond edge) / Retest (open inside, close beyond); signals reset at the midpoint. **LDP = TRIGGER:**
BSL (swing highs) / SSL (swing lows) zones, 4 delta quadrants, **Health% = consumed liquidity**; signals **ABS**
(absorption), **EXH** (low-vol sweep), **DIV** (high-vol into edge, no close-out), **REJ** (opposite-delta close-back-in).
- **4 models:** PAR Breakout-Retest · PAR Rejection · Liquidity Sweep Reversal (SSL/BSL sweep + close back in + LDP
  ABS/EXH/DIV/REJ) · Liquidity Continuation Break. Trade only at range edges / liquidity zones; POC/range-middle = no-trade.

### S4 — Swing Breakout Sequence [LuxAlgo] (SBS)  — *trend-week leader; run on 5m AND 15m*
**Not classic BOS/CHoCH** — it detects a **5-point FAILED-breakout sequence** in a swing zone:
P1 breakout attempt → P2 pullback in → P3 second attempt (beyond P1) → P4 pullback (taps P2 liquidity) → **P5 reversal
(double top/bottom)**. Premise = **trapped traders** after two failed breakouts fuel the next (3rd) move.
- **Entry:** after the 5-point sequence completes at P5, trade the resolving breakout (reversal or continuation) on a
  confirming close. SL beyond P5/the zone extreme; TP per the scaling table. **Inputs:** Swing Length (bigger = larger
  swings), Internal Length, "P4 beyond P2", "Require equal H/L at P5".
- **15m was cleaner than 5m** (less chop) in testing — but verify per symbol.

---

## 3. EXECUTION WORKFLOW (MCP / replay)
- **Backtest tab** (`eFMec2F9`) for replay; never the live chart. **SEQUENCE-TOGGLE all 4 at each decision point:**
  `indicator_toggle_visibility` show #1 → read its data → hide → show #2 → read → hide → … Keep **only one heavy
  profile visible at a time** (VP-Node/PAR/LDP); OFVWAP+SBS are light and can share. Cycle only at decision points
  (price at a level/structure), not every bar — most bars are no-trade for all four.
- **VP-Node:** trim its lookback (`in_25`≈60) once so it doesn't crash; if replay/screenshots ever go stale/drop,
  **relaunch TradingView** (`tv_launch`) — that resets the replay engine + screenshot cache (confirmed fix).
- **SBS read:** `pine_labels` caps at 50 (oldest-first); to read the CURRENT sequence pull with **`max_labels`≈360** and
  filter to the live price range (no "max sequences" input exists; remove/re-add doesn't help).

### ⚙ VERIFIED-WALK CADENCE (do it this way — learned the hard way)
**Run verification in SMALL, FOCUSED sessions — ONE strategy-day at a time** (e.g. "verify SBS gold Jun 9, 5m+15m").
A fresh session = replay holds, screenshots clean, full context budget. **Do NOT attempt a multi-day, multi-strategy
verified walk in one marathon session** — the tooling frictions (replay drops, stale screenshots, label caps, toggle
overhead) compound and it breaks/garbles. Each session: relaunch TV → set ONE strategy's indicator(s) → replay_start the
day → walk bar-by-bar → write the verified result to the day's RESULTS file → done. Estimates/regime-reads can be broad;
**tick-verification must be bite-sized.**
- Read: `data_get_study_values` (OFVWAP/VP plots) · `data_get_pine_boxes`/`_lines`/`_labels` (PAR ranges, LDP zones/
  signals, SBS points — filter by study name) · `capture_screenshot --region full` for the visual.
- 15m = structure; drop to 5m to time entries. **Decide on bars-up-to-cursor only.** Track entry/TP/SL **manually off
  OHLCV** (replay position field reads null). Log every checkpoint + **trade total time**.
- **Efficient backtest:** to get a completed day's structure, jump the cursor past it (`replay_start` next day) or pull
  **Daily bars** — don't bar-by-bar a whole day just to read its shape.

### 🔑 RULE — ONE BAR AT A TIME through the active session (non-negotiable for a real scalp)
**A scalp read = step ONE bar at a time through the active session and react in the moment** — read each 15m close, drop
to 5m at the decision zone, place the entry + SL there, manage to TP1/BE — NOT glance at where price ended up hours later.
- **Batch-stepping (many `replay_step` at once) is ONLY for fast-forwarding the dead/overnight zone** to *reach* the session
  (e.g. open→London). The moment price approaches a setup or the session goes live, **drop to single-bar steps.**
- **Why:** big batches skip the precise bar where the trigger prints and the fill happens — you "see" the move only after
  it's over, which is a regime *survey*, not a scalp. A survey maps the day's shape; a scalp takes the trade. Don't confuse
  the two or report a survey as if it were a walked trade.
- At every decision zone: **step 1 bar → read OFVWAP/levels → is there a trigger? → if yes act, if no step 1 more.** Repeat.

### 🔑 RULE — MONITOR 15m / EXECUTE 5m, with the STRUCTURAL (wick) stop (verified Jun-3 ledger)
- **The signal AND the stop come from 15m; 5m only TIMES the entry.** Place the stop at the 15m structural level — **below
  the sweep wick (long) / above the rejection wick (short)** — NOT a tight 5m stop.
- **Why (proven Jun 3):** the identical band-reclaim long that got **whipsawed out on a tight 5m stop (−50p)** SURVIVED on
  15m, because the 15m wick-stop sits *under the 5m noise*. Tight 5m stops die in chop; the 15m wick-stop holds.
- **Reversion-trade TP = VWAP.** A band-reclaim long / band-fade short targets VWAP — **bank it into VWAP resistance**
  (~+55–60p was there on Jun 3), don't hold a counter-trend trade for a fixed +100. **BE at +40p** (proven: turned a −110p
  VWAP-rejection into a scratch).

### 🔑 RULE — CHOP-SHELF STAND-ASIDE (the filter between over-filtering and over-trading)
- **A tight low-volatility shelf (e.g. a ~15-pt/150-pip band that price oscillates in below/above VWAP) stops BOTH
  directions.** Taking every cross/band signal inside it = death by whipsaw (Jun-3 = −$40 doing exactly this).
- **No new trades INSIDE a recognized chop shelf.** Wait for a **15m candle CLOSE decisively OUTSIDE the shelf with
  momentum/volume**, then take that break **with-trend.** This is the middle ground: not "over-filter to zero" (Jun 1–2),
  not "take everything" (Jun-3 5m).
- **Regime first, always:** don't fight the day. On a down day, counter-trend band-reclaim LONGS keep losing (Jun-3: 5m −50,
  5m −47, 15m scratch) — the edge is **with-trend shorts** (sell VWAP rejections / lower-band breaks). Match direction to regime.

## 4. LESSONS BANKED (2026-06)
1. **Never stack the heavy profiles** (VP-Node/PAR/LDP) — they crash/bury. **Check strategies in SEQUENCE** on one chart
   (show→read→hide→next, one heavy one visible at a time). For the VP use the **Pine Node-Detection trimmed** (it's the only
   API-readable one) — NOT native (native has no level API). If replay/screenshots break, **relaunch (`tv_launch`)**.
2. **The ≤stop is the binding constraint** — when invalidation is wider than the target allows, **SKIP**, don't squeeze
   the stop into noise (that's what lost the one −50p trade).
3. **Big step-batches miss entries** — walk the active session **ONE bar at a time** / 5m to time fills (see §3 RULE).
   Batch-stepping is only to fast-forward dead/overnight zones to reach the session; never through live price.
4. **Scale targets per instrument** — gold ≠ FX; a 70–100p TP1 is unreachable on EUR (whole day's range). 20 EUR pips is big.
5. **Fixed-$ risk flips the pip ranking** — gold's wide stop = cheap pips ($0.40/pip @ $20 risk); tight-stop FX = expensive
   pips ($2–4) → FX converts fewer pips into more dollars. Account for stop size, not just pips.

## 5. VALIDATION — Week Jun 1–5 (gold + EUR + GBP + AUD + NZD + USDJPY)
Full table: `screenshots/week-jun01-05/RESULTS.md`. **Trend-heavy week (USD strength)** → **SBS-15m positive on all 6
symbols** and the clear leader; mean-reversion (S1/S2/S3) earned on range/dip days, struggled on trend grinds (flat on
NZD). At $20 risk/trade, SBS ≈ +$1,000 for the week across the basket. **Caveat:** only Gold/Jun-1/S3 (PAR+LDP, +70p)
is tick-verified; the rest = verified day-structure + heuristic estimate.

## One-liner
**Pick by regime: trend → SBS (5-point trapped-trader breakout); range/dip → mean-reversion (VWAP bands / VP edges /
PAR+LDP sweeps). One strategy's indicators on the chart at a time. Candle-close confirms. TP1 = clean path to the next
level (scaled per instrument), TP2 = next structure, BE ~1R, SL logical — SKIP if it won't fit. POC/mid-range = WAIT.**
