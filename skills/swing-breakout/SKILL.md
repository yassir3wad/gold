---
name: swing-breakout
description: Scalp using ONLY Swing Breakout Sequence [LuxAlgo] (SBS) — a 5-point FAILED-breakout / trapped-trader pattern. Trade the breakout that resolves after P5; SL just beyond P5 (not the full sequence); TP1 70–100p (gold, scaled per instrument). REGIME-DEPENDENT: strong edge on TREND days, liability on RANGE days (verified). 15m cleaner than 5m. Part of the scalp-suite.
---

# Swing Breakout Sequence [LuxAlgo] (SBS) — Scalp

**Single indicator: Swing Breakout Sequence [LuxAlgo].** PEPPERSTONE feed. This is one of the four `scalp-suite`
strategies — **the trend-day specialist.** Use it *only* when the regime is directional (see §Regime).

## 1. What it actually is (from source)
**Not classic BOS/CHoCH.** SBS marks a **5-point FAILED-breakout sequence** inside a swing zone:
- **P1** breakout attempt → **P2** pullback back into the zone → **P3** 2nd attempt (beyond P1) → **P4** pullback (taps
  P2 liquidity) → **P5** reversal structure (double top/bottom).
- Premise: after **two failed breakouts**, the **trapped traders** fuel the *next* (3rd) move. You trade that resolution.
- Plots **Swing High / Swing Low** + labeled points **1–5**.
- **Inputs:** `Swing Length` (bigger = larger swings, fewer sequences) · `Internal Length` · "P4 beyond P2" · "Show P5" ·
  "Require equal H/L at P5". (Defaults: Swing Length 5, Internal 2.)

## 2. Entry / stop / targets
- **Entry:** after the **5-point sequence completes at P5**, enter on the **confirming breakout close** beyond the
  sequence extreme (or a retest-hold). Reversal or continuation — trade the direction it resolves.
- **STOP — the P5 rule (critical):** SL **just beyond P5** (the reversal point), **NOT** the full sequence high/low.
  The full-sequence structural stop is huge (~400p on gold = ~8× the cap); the P5 stop is far tighter (~70–120p).
  **Gold ≤50p gate:** if even the P5 stop is >50p → **size down** (keep $-risk fixed) or take it as wider-intraday. Never
  widen to the structural extreme; never squeeze into noise.
- **Targets:** **TP1 70–100p (gold)**, scaled per instrument (see scalp-suite table: EUR 15/5p, GBP 25/15p, etc.).
  **TP2 = next swing / structure.** BE +40p (gold) / ~1R (FX). No TP3.

## 3. ⚠ REGIME — the most important rule (VERIFIED on real bars)
SBS is **strongly regime-dependent:**
- **TREND / expansion day → its edge.** Verified **gold Jun 8 (strong trend-down): SBS short caught +500p+.**
- **RANGE / chop day → a liability.** Verified **gold Jun 9 (range 4273–4351): SBS chops / no clean trade** — the
  breakout never resolves; signals revert inside the range.
- **→ Only deploy SBS when the day is directional.** On range days, stand aside / use mean-reversion (OFVWAP-5m / VP /
  PAR+LDP). This is *why* SBS led the trend-heavy estimate week — and why it would bleed in a range-heavy one.

## 4. Timeframe (5m vs 15m)
- **15m = cleaner** (less whipsaw) — the verified default.
- **5m = earlier entries + tighter stops on trends, but MORE chop on ranges** (more small failed sequences). Use 5m to
  *time* the entry on a confirmed trend day; avoid 5m SBS on chop. (5m tick-verification still pending — see §6.)

## 5. Reading it via MCP
- `data_get_pine_labels {study_filter:"Swing Breakout"}` → the sequences (labels 1–5 + Swing High/Low + prices).
- ⚠ **Label cap:** the API returns ~50 labels **oldest-first**, so the CURRENT sequence is excluded by default. To read
  the live sequence, pull **`max_labels`≈360+** (heavier on 5m) and filter to the live price range. (No "max sequences"
  input exists; remove/re-add doesn't help.)
- SBS is **light** (unlike the profile indicators) → it can co-exist with OFVWAP; never needs trimming.
- Standard suite hygiene: backtest tab `eFMec2F9`; if replay/screenshots break, **relaunch (`tv_launch`)**.

## 6. Validation status
- **15m: VERIFIED** — Jun 8 (trend) **+500p short** (P5 stop ~100p, sized down); Jun 9 (range) **chop/no-trade**. The
  regime-dependence is the confirmed headline.
- **5m: pending** — needs a focused session with budget for the `max_labels` dump (the read prerequisite). Structurally:
  earlier+tighter on trends, choppier on ranges. Logs: `screenshots/verified-gold-jun08-09/RESULTS.md`.

## One-liner
**SBS = the trend-day breakout. Trade the move that resolves after the 5-point (P1–P5) failed-breakout sequence; SL just
beyond P5 (size down if >50p); TP1 70–100p (scaled), TP2 next swing. ONLY on trend/expansion days — on range days it
chops, so stand aside. 15m cleaner; 5m earlier-but-choppier.**
