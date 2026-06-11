---
name: par-liqdelta-scalp
description: XAUUSD scalp using ONLY two LuxAlgo indicators — Peak Activity Range (location/structure) + Liquidity Delta Profiler (trigger/confirmation). BSL/SSL sweeps, ABS/EXH/DIV/REJ signals, candle-close confirmation, TP1 70–100p, analysis-based TP2, BE +40p, ≤$5 SL. 4 models. NEW/separate strategy track — distinct from ofvwap-scalp and vp-node-scalp. Ignores Volume-Profile/ATR/CRT/SBS/VWAP/OB/FVG unless visible in plain price action.
---

# XAUUSD Scalp — Peak Activity Range + Liquidity Delta Profiler [LuxAlgo]

**Two indicators only.** The full scalp decision comes from: **Peak Activity Range zones · Liquidity Delta Profiler
zones/signals · BSL/SSL liquidity sweeps · ABS/EXH/DIV/REJ signals · candle-close confirmation · clean path to TP1 ·
logical SL.** Do NOT require Volume Profile with Node Detection, ATR Exceedance, CRT, SBS, VWAP, OB, FVG, or any other
strategy unless it is clearly visible from normal price action.

**Setup:** both indicators must be loaded + VISIBLE on the chart. PEPPERSTONE:XAUUSD (real volume). Read zones via
`data_get_pine_boxes` / `data_get_pine_lines` / `data_get_pine_labels` (filter by study name) + `capture_screenshot`
for the visual; confirm signals (ABS/EXH/DIV/REJ, BSL/SSL) from the labels/screenshot.

## Pip convention
1.00 = 10 pips · 70 pips = $7 · 100 pips = $10 · 40 pips = $4.

---

## Indicator roles

### 1. Peak Activity Range [LuxAlgo] — LOCATION & STRUCTURE
**How it works (source):** VOLUME-detected (not volatility). A **pivot on volume** is found; once confirmed after
`Pivot Length` bars, the indicator retroactively draws a **range from that single high-volume candle**. So the "range"
is a **high-volume zone**, not a session range. Plots:
- Range **high / low** = the volume-spike candle's high/low.
- **Solid line = midpoint / average** of that candle = the **fair-value** level.
- **Dashed line = POC** (price with the most volume in the range).
- Volume-profile bars within the range + signal **triangles**.

**Built-in signal modes** (input `Signal Mode`): **Breakout** = bullish when price *closes above* range high / bearish when
*closes below* range low. **Retest** = bullish when a candle *opens below* range high but *closes above* it / bearish when
*opens above* range low but *closes below* it. **State logic:** price must return to the **solid midpoint line to reset**
a signal (prevents repeat false entries).

Use it to read **where price is**: at range **high / low** (tradeable edges), at **midpoint/POC** (chop, no-trade),
**breakout / retest / rejection** vs **middle-of-range**.

### 2. Liquidity Delta Profiler [LuxAlgo] — TRIGGER & CONFIRMATION
**How it works (source):** **BSL** zones form from confirmed **swing highs**, **SSL** from **swing lows** (clusters of
stops/breakout orders). Each zone is split into **4 horizontal quadrants** colored by **volume delta** (buy vs sell), with
**opacity = delta magnitude** → shows which slice aggressive buyers/sellers dominated. **Zone Health %** = cumulative
volume traded vs the zone's capacity; as liquidity is consumed it **approaches 0** (a near-0 / fully-consumed zone is spent
→ no reaction expected).

**Reversal signals (bubbles during a sweep) — exact defs:**
- **ABS (Absorption)** — aggressive market orders at the **extreme edge** are absorbed by large **opposite** limit orders.
- **EXH (Exhaustion)** — the sweep happens on **very low relative volume** → no follow-through.
- **DIV (Divergence)** — **high volume pushes into the edge** (FOMO) but price **fails to close outside** the level.
- **REJ (Snapback Rejection)** — the sweep candle shows **high delta OPPOSITE the sweep** and **closes back inside** the zone.

(The dashboard validates signals with `Eval Window` + `Hold Time` — a "win" = price reverses and stays profitable for N
consecutive bars, i.e. it favors **sustained** pressure, not temporary wicks.) Use LDP to judge whether a move is a **real
rejection, trap, continuation, or no-trade** — and confirm **delta support** in the trade's direction.

---

## TP rules (two TPs only — no TP3)

### TP1 — dynamic 70–100 pips
- **70p/$7** — valid but nearest range boundary / liquidity zone is close.
- **80p/$8** — moderate clean space.
- **90p/$9** — momentum + liquidity support continuation.
- **100p/$10** — only when the path is clean and no strong opposing range/liquidity zone blocks before target.
- LONG TP1 = entry +$7…+$10. SHORT TP1 = entry −$7…−$10.
- **Don't force 100.** If 100 is blocked but 70–80 is clean → take the clean TP1. **If TP1 blocked <70p → WAIT/REJECT.**

### TP2 — analysis-based (optional, never invented)
Opposite PAR edge · range high/low · range POC/midpoint · next BSL/SSL zone · next visible swing H/L · round-number
liquidity · major visible S/R. No clear one → **TP1 only.**

## Breakeven
Move SL to BE after **+40p / +$4**. (LONG 3350 → BE at 3354; SHORT 3350 → BE at 3346.) **Never widen after BE.**

---

## The 4 models

### 1. PAR Breakout Retest — price breaks a high-volume range and retests
**LONG:** close **above** PAR high · retest the high from above and **holds** · LDP supports bullish continuation (or no
bearish ABS) · bullish close after retest · clean 70–100p path · SL below retest low / back inside range · TP1 +$7…$10.
**SHORT:** mirror — close below PAR low · retest from below rejects · LDP supports bearish (or no bullish ABS) · bearish
close · SL above retest high / back inside range · TP1 −$7…$10.
**Reject if:** weak breakout candle · breaks then immediately returns inside · LDP shows ABS against the trade · TP1
blocked <70p · SL too wide.

### 2. PAR Rejection — price rejects from range high or low
**LONG:** price tests/sweeps PAR **low** · candle closes back **above** the range low · LDP shows **SSL sweep / ABS / EXH /
DIV / REJ / bullish delta recovery** · entry after reclaim candle or retest · SL below sweep/rejection low · TP1 +$7…$10 ·
TP2 = midpoint/POC/range high/next liquidity.
**SHORT:** mirror at PAR **high** · close back below · LDP shows **BSL sweep / ABS / EXH / DIV / REJ / bearish recovery** ·
SL above sweep/rejection high · TP1 −$7…$10.
**Reject if:** price in the middle of the range · no close back inside after sweep · LDP gives no REJ/ABS/EXH/DIV
evidence · TP1 blocked <70p · SL too wide.

### 3. Liquidity Sweep Reversal — price sweeps BSL/SSL and snaps back
**LONG:** sweeps **SSL** · candle closes back **above** the swept zone · LDP shows ABS/EXH/DIV/REJ/bullish recovery · sweep
near PAR low / below range / valid support · entry after bullish reclaim or retest · SL below sweep low · TP1 +$7…$10 ·
TP2 = midpoint/range high/BSL zone/structure.
**SHORT:** mirror — sweeps **BSL** · closes back below · LDP bearish · sweep near PAR high / above range / resistance · SL
above sweep high · TP1 −$7…$10.
**Reject if:** sweep continues with **acceptance** (not rejection) · candle only wicks, no close back · LDP signal missing ·
too close to the next opposing range/liquidity level · SL too wide.

### 4. Liquidity Continuation Break — price clears liquidity and continues (no reversal)
**LONG:** breaks **above** BSL or PAR high · **strong close** above the level · LDP shows **no** ABS/REJ against the move ·
retests the broken level and **holds** · clean 70–100p path · SL below retest low / broken level · TP1 +$7…$10.
**SHORT:** mirror — breaks below SSL or PAR low · strong close below · LDP no ABS/REJ against · retest rejects · SL above
retest high / broken level · TP1 −$7…$10.
**Reject if:** breakout into immediate opposite liquidity · LDP shows ABS/DIV/REJ against direction · retest fails · TP1
path <70p · price returns to range middle.

---

## No-trade zones (WAIT / REJECT)
Price in the **middle of PAR** · chopping around midpoint/POC · not near range high/low/BSL/SSL/a clear liquidity zone ·
LDP shows no sweep/ABS/EXH/DIV/REJ/delta support · price already moved most of the 70–100p target before entry · TP1
blocked <70p · SL too wide for valid R · weak candle confirmation · price keeps flipping above/below the same boundary ·
liquidity zone fully consumed with no reaction.

## Entry confirmation
**Valid:** strong close outside PAR · retest hold of range high/low · sweep + close back inside · rejection wick + strong
close · ABS/EXH/DIV/REJ from LDP · clear bullish/bearish delta recovery · two candles holding above/below the level.
**Invalid:** wick only (no close) · doji in range middle · choppy candles near midpoint · late entry after price already
moved too far · LDP signal against the trade.

## TP1 path validation (check before approving)
1. ≥70p of clean space to TP1? 2. Next PAR boundary before 70p? 3. Next BSL/SSL before 70p? 4. Entering congestion/range
middle before TP1? 5. Already traveled too far from the trigger? 6. TP1 reduced 100→70–90 by a blocking level?
**Rules:** blocker <70p → WAIT/REJECT · blocker 70–100p → set TP1 before/at it (still ≥70p) · clean to 100p → 100p TP1.

## Risk management
R vs selected TP1: TP1 70p→SL ≤$3.5 · 80p→≤$4 · 90p→≤$4.5 · 100p→≤$5. If the logical SL is wider than TP1 allows →
**wait for better entry / reduce / classify wider-intraday / reject.** **Never put SL in noise just to force R.**
SL logic: LONG → below sweep low / range low / retest low / liquidity zone. SHORT → above the mirror.

---

## Decision order (run every checkpoint)
1. **Where is price?** PAR high / PAR low / midpoint-POC / BSL / SSL / liquidity zone / range-middle(no-trade).
2. **Trade location?** Valid: range high/low, BSL, SSL, breakout-retest, sweep/reclaim. Invalid: range middle, midpoint chop, no liquidity nearby.
3. **Which model?** PAR Breakout Retest / PAR Rejection / Liquidity Sweep Reversal / Liquidity Continuation Break / No-Trade.
4. **LDP confirmation?** ABS / EXH / DIV / REJ / delta recovery / or no absorption against continuation.
5. **Candle confirmation?** breakout close / reclaim close / rejection close / retest hold / two-candle hold.
6. **TP1 path clean for 70–100p?**
7. **SL logical + R valid (≤$5)?**
8. **Final decision.**

## Final approval checklist
1. Price at a valid trade location? 2. Outside range-middle/POC chop? 3. Which model is active? 4. LDP confirmation
present? 5. Candle confirmation present? 6. TP1 between 70–100p? 7. Why that TP1? 8. Enough clean path to TP1? 9. SL
logical + outside invalidation? 10. R valid vs selected TP1? 11. Can SL move to BE after +40p/+$4? 12. TP2 based on real
PAR/liquidity/visible structure? 13. TP3 disabled?
**Any critical check fails → WAIT_FOR_BETTER_ENTRY or REJECT.** Only approve if PAR gives a valid location AND LDP
confirms the reaction.

## One-liner
**Peak Activity Range = WHERE (trade only at range high/low/edges, never the middle); Liquidity Delta Profiler = IS-IT-REAL
(BSL/SSL sweep + ABS/EXH/DIV/REJ or delta recovery). Candle CLOSE confirms. TP1 70–100p to the clean path, TP2 = next
PAR/liquidity level, BE +40p, SL ≤$5 and logical. Range-middle / no LDP signal / consumed zone = WAIT.**
