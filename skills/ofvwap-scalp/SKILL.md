---
name: ofvwap-scalp
description: Gold scalping with TWO LuxAlgo tools — Order Flow VWAP Deviation (trigger + dynamic mean) + Volume Profile with Node Detection (static level map / targets). Band→reject→VWAP loop, 15m signal / 5m entry, ≤50p stop, TP1 70–100p, targets read off POC/VAH/VAL/HVN/LVN. Self-contained; ignores all prior strategies (SBS/CRT/SMC/discretionary-trade).
---

# Order Flow VWAP Deviation + Volume Profile — Scalp Strategy

**This is a clean-slate, two-indicator method.** The ONLY tools on the chart are:
1. **Order Flow VWAP Deviation [LuxAlgo]** — the **WHEN**: the trigger (band sweep/reject, VWAP gate, tint) + the dynamic mean.
2. **Volume Profile with Node Detection [LuxAlgo]** — the **WHERE**: static horizontal levels (POC / VAH / VAL / HVN / LVN)
   that say where price stalls, accelerates, and where the runner dies.
(+ the Volume pane.) Ignore every other strategy we have ever discussed (SBS, CRT, SMC, the discretionary-trade skill,
the coded scalp engine). Nothing here depends on them.

**Division of labor:** OFVWAP fires the signal; the Volume Profile grades its confluence and sets the targets. You do
NOT take more random trades — you take the same signals with better targets and a confluence filter (see §1B + §5).

---

## 1. The tool (what each part means)

Anchored, order-flow-weighted VWAP with deviation bands. From the LuxAlgo source:

- **Blue line = anchored VWAP** (volume-weighted fair value). Anchor = **Session** (resets each day → the
  gold vertical lines). This is the **magnet and the gate**.
- **Cloud = ±std-dev deviation bands** (Upper / Lower). The "rubber band" — how stretched price is from fair value.
- **Order-flow tint** = a delta proxy (close vs high/low of each bar) → which side dominated. The **circuit-breaker**
  that says fade vs don't-fade.
- **Gold verticals = session anchor resets** → VWAP + bands re-seed.
- **"Stops Triggered High/Low"** = stop-run flags: price piercing a stop zone on high volume → trend exhaustion /
  reversal imminent. **A+ signal when it fires** (note: on quiet gold sessions it may never fire — then read the
  sweep-and-reclaim structurally instead).

LuxAlgo built this for **liquidity sweeps + mean reversion**, so the method is **mean-reversion-first** with one
trend rule so we don't fight a runaway.

---

## 1B. The second tool — Volume Profile with Node Detection [LuxAlgo] (the level map)

Static, volume-based horizontal levels (needs real volume → PEPPERSTONE:XAUUSD). Plots:

- **POC** (Point of Control) — highest-volume price = strongest magnet / S/R. A second "fair value" alongside VWAP.
- **VAH / VAL** (Value Area High/Low) — the ~70%-volume range edges. Range-day fade boundaries (like the bands).
- **HVN** (High-Volume Nodes) — price **acceptance** → price **stalls/slows** there → S/R, runner dies here.
- **LVN** (Low-Volume Nodes) — price **rejection** / thin air → price **moves FAST through** → breakout accelerator.

**Settings:** Profile Lookback = session or current swing range; Value Area 70%. **Read via MCP:** `data_get_pine_lines` /
`data_get_pine_labels` filtered to the profile for POC/VAH/VAL + node levels (ignore the raw 250 profile rows).

**How it changes the trade (this is the whole point of adding it):**
- **Entry confluence (grading):** an OFVWAP signal is **upgraded** when it lands on a VP level —
  band sweep-reclaim **at an HVN/VAL**, VWAP-retest **at the POC**. Confluence = take it bigger / with more trust.
  No confluence = it's a lower-grade signal (smaller / skip in chop).
- **Targets become exact (replaces the eyeballed "scan" TP2):** **TP1 = nearest HVN/POC**, **TP2 = VAH/VAL or the next HVN.**
- **The LVN travel rule:** LVN between entry and target → expect a **fast** move (let the runner run). HVN between →
  expect a **stall** (bank TP1 there, don't hold).
- **Don't fight a thick fresh POC/HVN** — if your target sits just beyond a big HVN, cut the expectation.

---

## 2. The core loop (the read this method trades)

```
band tag → REJECT → travel to BLUE (VWAP) → blue is the GATE
        ├─ price rejects blue  → continues (back toward the other band)
        └─ price CLOSES through blue → flips (new direction)
```

- Below blue, rally into blue, **rejected → back down.** **Closes above blue → flips up** (blue becomes support).
- Tag **upper band + reject → snap to blue.** Tag **lower band + reject → snap to blue.**
- Blue is where price **always travels first** → blue = the guaranteed first objective.

| Where price is | Trigger | Trade | First objective |
|---|---|---|---|
| Upper band | rejection candle | SHORT | blue → then lower band |
| Lower band | rejection candle | LONG | blue → then upper band |
| Into blue from below | rejects blue | SHORT (continuation) | toward lower band |
| Into blue from below | **closes above** blue | LONG (flip) | toward upper band |

**The A+ version of a band reject is a SWEEP-AND-RECLAIM:** price pokes just *past* the band (grabs liquidity /
prints a marginal new extreme), then immediately reclaims it. That sweep is the highest-quality entry the tool gives.

---

## 3. Regime filter (run BEFORE any trade)

Read two cues off the **15m**:

- **Flat blue + price ping-ponging band↔band → RANGE.** Fade the bands back to blue. (Primary mode — what the tool is for.)
- **Sloping blue + price band-walking one side** (rides a band, pullbacks die *at* blue, not across) → **TREND.**
  Do NOT fade. Only trade **pullback-to-blue WITH the slope.**
- **Order-flow tint = the circuit-breaker:** only fade a band when the tint has **flipped against** the move.
  Tint still with the move at the band = band-walk, don't fade.

---

## 4. Timeframes — 15m signal / 5m entry (hybrid)

- **15m = signal/structure** (regime, band tag, rejection, blue gate) on **closed bars.** Don't let 5m generate signals.
- **5m = entry timing only.** Once 15m flags a band tag, drop to 5m to catch the actual rejection/reclaim candle.
  A 5m swing is tighter than the 15m one → the stop fits under the **5m wick** → keeps SL ≤50p while 15m gives the target.
- Realistic count: **1–3 clean setups/day.** Quiet/dead/chop sessions → 0 trades is correct.

---

## 5. Risk & targets (firm)

- **Stop ≤ 50 pips (5.0 pts)**, placed under/over the **5m rejection wick or the swept extreme.**
  **If a setup can't fit a ≤50p stop with the stop OUTSIDE the noise (beyond the swept low/high), SKIP it.**
  → In a range this forces entry **AT the band/floor**, never mid-range. That single rule is most of the edge.
- **TP1 = 70–100 pips, partial** → then move stop to **BE (a touch beyond entry, not exact — noise wicks exact BE).**
- **Final TP = read off the Volume Profile** (no more eyeballing): **TP1 = nearest HVN/POC, TP2 = VAH/VAL or next HVN.**
  LVN between = let it run; HVN between = bank TP1 there. On a **range day the runner often will NOT reach VWAP**
  (an HVN/POC caps it) — that's fine, the VP tells you so in advance. On a **trend day** let the runner ride the
  band-walk toward the next node and trail behind blue.
- One setup at a time. No third target. Partial + runner only.

---

## 6. Stand aside (no trade)

- **Anchor reset just printed** (gold vertical) → VWAP/bands re-seeding; wait for a fresh slope before classifying.
- **Bands tight / price glued to blue** → balance/chop, no stretch = no edge.
- **Band tag with NO rejection** (price closing on/through the band) = band-walk → not a fade; wait.
- **Already extended past a band with no reclaim** → don't chase; wait for the sweep-reclaim or a pullback-to-blue.
- **Mid-range** → no entry (stop can't sit outside the noise within 50p).

---

## 7. Pip convention
1.00 price = 10 pips = $1. **100 pips = $10 = 10.0 price points.** Gold runs 250–700+ pips/day.

## 8. Chart setup
- Symbol: **PEPPERSTONE:XAUUSD** — REQUIRED. The tool is volume/order-flow weighted; OANDA/bare XAUUSD has no
  volume and breaks it.
- Indicators visible: **Order Flow VWAP Deviation [LuxAlgo]** + **Volume Profile with Node Detection [LuxAlgo]** +
  **Volume** pane ONLY. Hide everything else for a clean read.
- OFVWAP: Anchor = Session, std-dev mult ≈ 2.0 (outer fade band). VP: Lookback = session/swing, Value Area 70%.

---

## 9. Execution / replay-walk workflow (MCP)

For a no-hindsight study or live monitoring:

1. Use the **backtest tab** (chart_id `eFMec2F9`) for replay — never the live gold tab (`eabXWKAd`).
2. `chart_get_state` → hide all studies except Order Flow VWAP Deviation + Volume (`indicator_toggle_visibility`).
3. `replay_start {date}` → dismiss any "Continue last replay?" modal with `ui_keyboard Escape`.
4. Step the day on **15m** (`replay_step`); read each bar with `data_get_study_values` (VWAP / Upper Band / Lower Band /
   Stops Triggered) + `data_get_ohlcv {summary:true}` (price, last 5 bars). Screenshot (`--region full`, axes visible)
   at decision points.
5. On a 15m band tag → `chart_set_timeframe 5` to time the entry; place the ≤50p stop under the 5m wick.
6. **Decide on bars-up-to-cursor only** (no hindsight). Log every checkpoint (WAIT/PREP/ENTER + why) to a
   `screenshots/gold-<day>-ofvwap/DECISIONS.md` table.
7. Track entry/TP1/runner/stop **manually off OHLCV** — replay's position field reads null; manage by reading bars.
8. **Always log trade total time** (entry timestamp → exit timestamp = duration).

---

## 10. Validation — Monday 2026-06-01 (no-hindsight, this method only)

Full log: `screenshots/gold-jun01-ofvwap/DECISIONS.md`.

- **Asian (00:00–07:00 UTC):** anchor reset → tight bands → dead drift; lower-band tags were band-walks/breaks
  (no reject). **Correctly 0 trades.**
- **London (07:00+):** a **4490–4506 chop** formed. A base-high break **faked out** (skipped). Then the A-grade
  signal: **lower-band SWEEP-AND-RECLAIM** — price swept **4489.32** (under the 4490 band), reclaimed hard
  (4491→4498), pullback **held 4494**.
- **TRADE #1 LONG @ 4498 (09:35 UTC):** SL 4493 (50p) · **TP1 4505 = +70p partial** → BE · runner trailed to
  4503, **stopped +50p** (4508 broke but rejected at 4511, VWAP 4517 never tagged on the range day).
  **≈ +60p blended WIN. ~55 min.**
- **NY (13:00):** a **-90p volume-expansion breakdown** (4538→4448) flipped the regime to TREND-DOWN. Price flushed
  ~2 std-devs below VWAP, then **reclaimed the stretched lower band** with higher-lows = the same sweep/hold→revert signal.
- **TRADE #2 LONG @ 4467 (14:45 UTC):** SL 4462 (50p) · **TP1 4474 = +70p partial** → BE · runner scratched BE
  (dead-cat bounce capped 4479, TP2 4485 never filled on the down-trend day). **≈ +70p WIN. ~30 min.**
- **FULL DAY: 2 trades, 2 wins, ≈ +130p.** Both were the SAME signal (band sweep/hold + reclaim → travel toward blue).
  Zero shorts (every short idea was a chase past the band or couldn't fit a ≤50p stop → correctly skipped). Asian +
  late-session = dead drift, correctly flat.
- **Lessons confirmed:** (a) the **≤50p stop** forces entry AT the band extreme (where the edge is), never mid-range;
  (b) **TP1 70–100p** was right both times — neither bounce reached VWAP, a fixed run-to-VWAP target would've round-tripped;
  (c) the user's loop read held exactly; (d) the "Stops Triggered" flag never fired (quiet gold) → read the sweep-reclaim
  **structurally**; (e) once a runner is at BE, **let the BE stop work** — manually closing #2's runner at BE left ~+150p
  on the table (price's low was 0.03 above BE, then resumed up).

---

## One-liner
**OFVWAP fires it, Volume Profile aims it. Range = fade the band back to blue when order-flow exhausts (best on a
sweep-and-reclaim AT an HVN/VAL); Trend = trade the VWAP pullback with the slope; reset lines = reset bias; bands
tight = stand aside. 15m signals, 5m times the entry, ≤50p stop at the extreme, TP1 70–100p at the nearest HVN/POC,
TP2 next node (LVN between = let it run, HVN between = bank it).**
