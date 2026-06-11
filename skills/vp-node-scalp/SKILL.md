---
name: vp-node-scalp
description: Gold scalp using a Volume Profile (POC/VAH/VAL + HVN/LVN/edges) as the sole framework — drives location, entry, no-trade filter, TP1 path (70–100p), TP2, and SL. Two models (Edge Reversal, LVN Continuation). Candle-close confirmation. Use "Volume Profile with Node Detection [LuxAlgo]" with Profile Lookback TRIMMED to ~40-60 (the only API-readable VP — node levels via pine_labels; trimming fixes its memory crash). Native VP has no level API (eyeball only). Ignores SBS/CRT/SMC/discretionary.
---

# Volume Profile Node Scalp [VP-only]

> **TOOL NOTE (2026-06, REVISED): use "Volume Profile with Node Detection [LuxAlgo]" — TRIMMED.** It's the VP we want
> because it's the **only one that's API-readable**: its node levels (HVN/LVN/POC) come back via
> `data_get_pine_labels{study_filter:"Node Detection"}` (e.g., 4515 / 4462 / 4335 / 4268). **Fix the crash by trimming its
> Profile Lookback to ~40–60** (`indicator_set_inputs {"in_25": 60}`) and saving the layout — at low lookback it renders,
> reads, and doesn't blow Pine memory. (Earlier it crashed only because it loaded at the default 360.)
> **Do NOT rely on the *native* "Periodic/Session Volume Profile"** for an automated read — it has **no data API for
> POC/VAH/VAL** (only Up/Down/Total), so its levels can only be eyeballed. Native = fine for a human glance; **Node-Detection
> (trimmed) = the machine-readable choice** for this skill.

**Single framework. The ONLY profile tool needed is the native Volume Profile** (+ Volume pane).
Do NOT require OFVWAP/VWAP, Liquidity Delta Profiler, SMC, OB/FVG, CRT, SBS, ATR, or any other confirmation. The
full scalp decision comes from: **VP nodes (HVN/LVN/POC), profile edges, price action at those levels, candle-close
confirmation, a clean path to TP1, and logical SL.** (OFVWAP is optional, only ever as a second opinion on 5m entry
timing — not part of the decision.)

PEPPERSTONE:XAUUSD only (real volume required — VP is blank on OANDA). **Pip:** 1.00 = 10 pips; 100p = $10; 70p = $7;
40p = $4.

---

## 1. The levels (what each node means)

- **POC** — highest-volume price. Main magnet, major decision point, **chop if price rotates around it.** Avoid new
  entries ON it. Use as a TP2 / mean-reversion target.
- **HVN (peak node)** — price acceptance / fair value / consolidation. **Stalls price → S/R.** Don't enter in the
  middle of an HVN. An HVN can **block TP1** (if it sits <70p ahead → reject/wait) or **be TP2**.
- **LVN (trough node)** — thin liquidity / rejection / **fast-move zone.** Preferred for quick 70–100p runs. Price
  rips through it on a strong close.
- **Profile edge (VAH/VAL / outer value)** — breakout, rejection, or reversal level. **Best entries are at edges,
  not the middle.** Longs after reclaiming a lower edge; shorts after losing an upper edge.

---

## 2. The two models (GPT's 4 collapse to these)

### A) EDGE REVERSAL (reversal back toward value) — covers Profile-Edge Reversal + POC Magnet + HVN Rejection
Price **tests/sweeps a profile edge or LVN extreme, then a candle CLOSES back inside** (rejection wick or strong
reclaim close).
- **LONG:** sweep lower edge / LVN low → close back above the edge → target POC/HVN above. SL **below the rejection low.**
- **SHORT:** sweep upper edge / LVN high → close back below the edge → target POC/HVN below. SL **above the rejection high.**
- Need: next HVN/POC not so close it blocks TP1 (≥70p of room). TP2 = POC or next HVN.
- **Reject if:** price closes beyond the edge and *accepts* there (no reclaim), or TP1 blocked <70p, or SL too wide.

### B) LVN CONTINUATION (breakout away from value) — the "run through the gap"
Price **closes through an edge/HVN/POC into thin volume (LVN)** with a strong displacement candle, clean space ahead.
- **LONG:** strong close above edge/HVN/POC into an LVN, clean 70–100p up, no HVN blocking. SL **below the breakout/retest low.**
- **SHORT:** strong close below edge/HVN/POC into an LVN, clean 70–100p down, no HVN blocking. SL **above the breakdown/retest high.**
- Enter on the **breakout close or a retest hold.** TP2 = next node boundary.
- **Reject if:** the breakout closes directly INTO another HVN, weak close, still inside congestion, or TP1 blocked <70p.

---

## 3. Entry confirmation (VP alone needs price-action proof)
**Valid:** strong candle CLOSE away from HVN/POC · breakout close into LVN · retest of an edge holds · rejection wick
at an edge · close back inside after an edge sweep · 2 candles holding outside/inside a level · clear displacement
away from value.
**Invalid:** wick only (no close) · weak doji in the value middle · choppy candles around POC · entry inside HVN
congestion · entry after the move already traveled most of TP1.

---

## 4. TP1 — dynamic 70–100p (never blindly force 100)
Pick by the **clean path to the next blocking node:**
- **70p / $7** — setup valid but the next node/level is close.
- **80p / $8** — moderate clean space.
- **90p / $9** — momentum + profile path support it.
- **100p / $10** — only when the path is clean and **no HVN/POC/edge blocks before target.**
- If a blocker sits **<70p ahead → WAIT/REJECT.** If it sits **70–100p ahead → set TP1 just before it** (still ≥70p).
- LONG TP1 = entry +$7…+$10. SHORT TP1 = entry −$7…−$10.

## 5. TP2 — optional, VP/structure only (never invented)
Next HVN · POC · profile extreme · opposite edge · next LVN boundary · major visible swing H/L · round-number liquidity.
No clear one → **TP1 only.**

## 6. SL + R
Logical placement only: LONG → below the rejection low / LVN low / retest low / edge. SHORT → above the mirror.
Target **1:2** vs the chosen TP1: TP1 70p→SL ≤$3.5 · 80p→≤$4 · 90p→≤$4.5 · 100p→≤$5. **Hard cap ≤$5 (50p).**
If the logical SL is wider than TP1 allows → **wait for a better entry / reduce / reject.** Never put SL in noise to force R.

## 7. Breakeven
Move SL to **BE after +40p / +$4.** Never widen after. (LONG entry 3350 → BE at 3354; SHORT 3350 → BE at 3346.)

---

## 8. No-trade filter (WAIT/REJECT)
Price inside a large HVN · rotating around POC · in the middle of value · between nodes with no clear edge · TP1
blocked <70p · no LVN/thin path · entry too late (move mostly done) · weak candle confirmation · SL too wide · TP2
guessed · no clear profile-based reason.

## 9. Decision order (run every checkpoint)
1. **Where is price?** HVN / LVN / POC / profile edge / between nodes / profile extreme.
2. **Trade location or not?** TRADE: edge, extreme, LVN edge, HVN edge. NO-TRADE: POC, HVN middle, value middle, unclear between nodes.
3. **Which model?** Edge Reversal / LVN Continuation / No-Trade.
4. **Candle confirmation?** breakout close / reclaim close / rejection close / retest hold / displacement.
5. **TP1 path clean for 70–100p?** (check for a blocking HVN/POC/edge before 70p).
6. **SL logical + R valid (≤$5)?**
7. **Decide.**

## 10. Execution workflow (MCP / replay)
- Backtest tab (`eFMec2F9`). Visible: **Volume Profile with Node Detection** + **Volume** only (hide the rest, incl. OFVWAP).
- Read nodes: `data_get_pine_labels {study_filter:"Node Detection"}` → node price levels; **screenshot** (`--region full`)
  for the histogram / POC / value-area / edges. Nodes **develop** as the session prints — re-read at each decision point.
- **15m = location/structure; 5m = time the confirming close + keep SL tight.** Decide on bars-up-to-cursor only.
- Log every checkpoint to `screenshots/gold-<day>-vp/DECISIONS.md`. Track entry/TP/SL **manually off OHLCV** (replay
  position field reads null). Always log **trade total time.**

---

## 11. Validation — Monday 2026-06-01 (VP-only) — [filled during the walk]
VP node map at open: `4595 · 4549 · 4507 · 4446 · 4366`; POC/heaviest ≈ 4520–4540; value bracketed ~4446–4549.
(Trades + confluence appended after the walk in `screenshots/gold-jun01-ofvwap/REWALK_VP.md`.)

## One-liner
**Trade the profile EDGES, never the middle. Edge sweep + close back inside = reversal to POC/HVN; strong close
through a level into an LVN = continuation. Candle CLOSE confirms. TP1 = clean 70–100p to the next blocking node,
TP2 = next node. BE +40p, SL ≤$5 and logical. POC/HVN-middle/between-nodes = WAIT.**
