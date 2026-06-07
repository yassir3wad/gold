# Signal Roadmap — Detailed Execution Reference

> **Companion to [`signal-roadmap.md`](signal-roadmap.md)** (the summary + crosswalk). This is the *detailed*
> appendix: per-signal setup/trigger/execution/invalidation + Python detection hints for the same 100 signals.
>
> **REFERENCE / MENU, not a build list.** Our bottleneck is *edge*, not signal coverage — we add new detectors
> rarely and only after validating what we have (the crosswalk in `signal-roadmap.md` shows implemented vs.
> candidate vs. skip). The adopted parts of this file: the **AI approval checklist** (live in `scalp_fast
> --review`), the **APPROVE/REJECT/WAIT decision format + AI Review JSON** (below), and the **Confluence Score
> Guide** penalties implemented in `confidence.py`.

## Evidence status

This manual labels many setups "Excellent" on textbook grounds. **Those labels are not evidence.** This file is a
reference menu, not a validated live allowlist. Every signal below carries an implicit evidence tag:

- **`validated`** — repo-backed cost-adjusted edge in *our* backtest/live logs.
- **`experimental`** — plausible, being tried here, not yet proven.
- **`rejected`** — disproven in our backtest/live logs.
- **`not-tested`** — default; no evidence either way. **The vast majority of the 100 signals are here.**

**An AI reviewer must NOT approve a setup just because this manual calls it "Excellent."** Only `validated`
families are eligible for normal live alerts. Everything else (`experimental`, `not-tested`) is
observation/experimental only, and `rejected` must not be alerted. The few families with current evidence
(per `PROJECT_REVIEW_IMPROVEMENTS.md`):

| Signal / family | Tag | Note |
|---|---|---|
| Resistance-trendline break | `validated` | Only family that clearly cleared the 3-pip spread in the June backtest; current core setup. |
| Highly-selective CRT | `validated` | Only with a clean room + valid value-area context (large clean target, no immediate wall). Generic/high-volume CRT is not validated. |
| Value-area rejection (`va_reject`) | `validated` | Only when level state is valid (and VWAP bias agrees). |
| Break-and-retest | `rejected` | Uniformly bad in the tested sample. |
| Generic momentum impulse | `rejected` | Negative after spread; observation/disabled for live alerts. |
| Morning day-efficiency gate | `rejected` | Coin-flip in backtest; do not use to gate the day. |

All other signals in this file default to **`not-tested`** until our own backtest/live logs say otherwise.

Purpose: this manual gives the Python signal engine and AI review agent a shared rulebook. Python detects
possible trade signals mechanically; the AI reviews context and approves only high-quality setups.

Important: this is not financial advice and does not guarantee profits. The rules are designed for systematic analysis, backtesting, and discretionary review.

## Recommended Architecture

1. **Data Layer**: OHLCV candles, session times, previous day high/low, previous day VAH/VAL/POC, VWAP and bands, swing highs/lows, ATR.
2. **Python Detection Layer**: detects raw signals from objective rules.
3. **Scoring Layer**: scores the signal using confluence and risk/reward.
4. **AI Review Layer**: approves, rejects, or waits based on market context.
5. **Execution Layer**: only executes approved signals with defined entry, stop, targets, and invalidation.

## Required Python Features

- Candle direction, body size, wick size.
- Swing high / swing low detection.
- BOS and CHOCH detection.
- ATR and volatility expansion/compression.
- Session windows: Asian, London, New York, NY lunch.
- Daily/weekly open, previous day high/low.
- Previous day Market Profile levels: VAH, VAL, POC.
- VWAP, VWAP upper/lower bands.
- Zone state tracking: new, untested, tested, mitigated, invalidated.

## Global Approval Rules

AI must reject a signal when any of these are true:

- Risk/reward is below 1:2.
- Entry is in the middle of value with no edge.
- Signal trades directly into a strong opposite level.
- Setup has no clear invalidation / stop loss.
- Level has already been accepted through.
- Market is chopping around VWAP.
- Setup is old, unclear, or over-tested.

AI may approve only when:

- There is a meaningful level.
- Structure confirms the direction.
- Entry, stop, and targets are clear.
- Risk/reward is acceptable.
- The session and volatility are appropriate.

## Standard AI Review JSON

```json
{
  "decision": "APPROVE | REJECT | WAIT",
  "market": "XAUUSD | EURUSD | GBPUSD | USDJPY | OTHER",
  "signal_name": "",
  "direction": "LONG | SHORT | NEUTRAL",
  "bias": "BULLISH | BEARISH | NEUTRAL",
  "entry": 0,
  "stop_loss": 0,
  "target_1": 0,
  "target_2": 0,
  "risk_reward": 0,
  "confidence": 0,
  "reason": ""
}
```

## Confluence Score Guide

Add points:

- +25 at KLZ / order block / breaker.
- +20 at VAH/VAL/POC.
- +20 at PDH/PDL or session high/low sweep.
- +15 at VWAP or VWAP band.
- +15 with BOS/CHOCH confirmation.
- +10 during London/NY active session.
- +10 if fresh/untested level.

Subtract points:

- -30 in middle of value.
- -25 level accepted through.
- -20 tested more than twice.
- -20 directly into strong opposite level.
- -20 VWAP chop.

Decision thresholds:

- 80-100: strong candidate.
- 65-79: wait for extra confirmation.
- Below 65: reject.


# Signal Index

| # | Signal | Category | Gold/XAUUSD | Forex Majors | Evidence | Best Use |
|---:|---|---|---|---|---|---|
| 1 | [KLZ Retest](#1-klz-retest) | Institutional / SMC | Excellent | Excellent | `not-tested` | Intraday |
| 2 | [Order Block Retest](#2-order-block-retest) | Institutional / SMC | Excellent | Excellent | `not-tested` | Intraday/Swing |
| 3 | [Breaker Block Retest](#3-breaker-block-retest) | Institutional / SMC | Excellent | Very Good | `not-tested` | Intraday |
| 4 | [Mitigation Block Retest](#4-mitigation-block-retest) | Institutional / SMC | Very Good | Very Good | `not-tested` | Intraday |
| 5 | [Fair Value Gap Fill](#5-fair-value-gap-fill) | Institutional / SMC | Excellent | Excellent | `not-tested` | Scalping/Intraday |
| 6 | [Liquidity Sweep](#6-liquidity-sweep) | Institutional / SMC | Excellent | Excellent | `not-tested` | Scalping |
| 7 | [Equal Highs Sweep](#7-equal-highs-sweep) | Institutional / SMC | Excellent | Excellent | `not-tested` | Scalping |
| 8 | [Equal Lows Sweep](#8-equal-lows-sweep) | Institutional / SMC | Excellent | Excellent | `not-tested` | Scalping |
| 9 | [Previous Day High Sweep](#9-previous-day-high-sweep) | Institutional / SMC | Excellent | Very Good | `not-tested` | Intraday |
| 10 | [Previous Day Low Sweep](#10-previous-day-low-sweep) | Institutional / SMC | Excellent | Very Good | `not-tested` | Intraday |
| 11 | [Session High Sweep](#11-session-high-sweep) | Institutional / SMC | Excellent | Very Good | `not-tested` | Scalping |
| 12 | [Session Low Sweep](#12-session-low-sweep) | Institutional / SMC | Excellent | Very Good | `not-tested` | Scalping |
| 13 | [Trendline Liquidity Sweep](#13-trendline-liquidity-sweep) | Institutional / SMC | Very Good | Very Good | `not-tested` | Scalping |
| 14 | [Stop Hunt Reversal](#14-stop-hunt-reversal) | Institutional / SMC | Excellent | Very Good | `not-tested` | Scalping |
| 15 | [Displacement Continuation](#15-displacement-continuation) | Institutional / SMC | Excellent | Excellent | `not-tested` | Intraday |
| 16 | [Previous VAH Rejection](#16-previous-vah-rejection) | Market Profile | Excellent | Good | `validated` | Intraday |
| 17 | [Previous VAL Rejection](#17-previous-val-rejection) | Market Profile | Excellent | Good | `validated` | Intraday |
| 18 | [VAH Flip Support](#18-vah-flip-support) | Market Profile | Excellent | Good | `not-tested` | Intraday |
| 19 | [VAL Flip Resistance](#19-val-flip-resistance) | Market Profile | Excellent | Good | `not-tested` | Intraday |
| 20 | [Failed Auction Above VAH](#20-failed-auction-above-vah) | Market Profile | Excellent | Good | `not-tested` | Intraday |
| 21 | [Failed Auction Below VAL](#21-failed-auction-below-val) | Market Profile | Excellent | Good | `not-tested` | Intraday |
| 22 | [POC Magnet Rotation](#22-poc-magnet-rotation) | Market Profile | Very Good | Good | `not-tested` | Range day |
| 23 | [Inside Value Rotation](#23-inside-value-rotation) | Market Profile | Good | Good | `not-tested` | Range day |
| 24 | [Outside Value Acceptance](#24-outside-value-acceptance) | Market Profile | Excellent | Good | `not-tested` | Trend day |
| 25 | [Poor High / Poor Low Repair](#25-poor-high-poor-low-repair) | Market Profile | Very Good | Medium | `not-tested` | Intraday |
| 26 | [Single Prints Fill](#26-single-prints-fill) | Market Profile | Very Good | Medium | `not-tested` | Intraday |
| 27 | [LVN Rejection](#27-lvn-rejection) | Market Profile | Very Good | Medium | `not-tested` | Intraday |
| 28 | [HVN Magnet](#28-hvn-magnet) | Market Profile | Good | Medium | `not-tested` | Range day |
| 29 | [VWAP Reclaim Long](#29-vwap-reclaim-long) | VWAP | Excellent | Very Good | `not-tested` | Intraday |
| 30 | [VWAP Rejection Short](#30-vwap-rejection-short) | VWAP | Excellent | Very Good | `not-tested` | Intraday |
| 31 | [VWAP Pullback Long](#31-vwap-pullback-long) | VWAP | Excellent | Very Good | `not-tested` | Scalping |
| 32 | [VWAP Pullback Short](#32-vwap-pullback-short) | VWAP | Excellent | Very Good | `not-tested` | Scalping |
| 33 | [VWAP Band 2 Reversal](#33-vwap-band-2-reversal) | VWAP | Very Good | Good | `not-tested` | Scalping |
| 34 | [VWAP Band Trend Ride](#34-vwap-band-trend-ride) | VWAP | Excellent | Good | `not-tested` | Trend day |
| 35 | [VWAP Chop Filter](#35-vwap-chop-filter) | VWAP | Excellent | Excellent | `not-tested` | Filter |
| 36 | [Anchored VWAP Retest](#36-anchored-vwap-retest) | VWAP | Excellent | Excellent | `not-tested` | Intraday/Swing |
| 37 | [Weekly VWAP Confluence](#37-weekly-vwap-confluence) | VWAP | Very Good | Very Good | `not-tested` | Swing |
| 38 | [VWAP + VAH/VAL Confluence](#38-vwap-vah-val-confluence) | VWAP | Excellent | Good | `not-tested` | Intraday |
| 39 | [Double Top](#39-double-top) | Classic Pattern | Very Good | Excellent | `not-tested` | Intraday/Swing |
| 40 | [Double Bottom](#40-double-bottom) | Classic Pattern | Very Good | Excellent | `not-tested` | Intraday/Swing |
| 41 | [Triple Top](#41-triple-top) | Classic Pattern | Good | Good | `not-tested` | Swing |
| 42 | [Triple Bottom](#42-triple-bottom) | Classic Pattern | Good | Good | `not-tested` | Swing |
| 43 | [Head and Shoulders](#43-head-and-shoulders) | Classic Pattern | Good | Very Good | `not-tested` | Intraday/Swing |
| 44 | [Inverse Head and Shoulders](#44-inverse-head-and-shoulders) | Classic Pattern | Good | Very Good | `not-tested` | Intraday/Swing |
| 45 | [Bull Flag](#45-bull-flag) | Classic Pattern | Excellent | Excellent | `not-tested` | Scalping/Intraday |
| 46 | [Bear Flag](#46-bear-flag) | Classic Pattern | Excellent | Excellent | `not-tested` | Scalping/Intraday |
| 47 | [Bullish Pennant](#47-bullish-pennant) | Classic Pattern | Very Good | Very Good | `not-tested` | Intraday |
| 48 | [Bearish Pennant](#48-bearish-pennant) | Classic Pattern | Very Good | Very Good | `not-tested` | Intraday |
| 49 | [Ascending Triangle](#49-ascending-triangle) | Classic Pattern | Good | Very Good | `not-tested` | Intraday |
| 50 | [Descending Triangle](#50-descending-triangle) | Classic Pattern | Good | Very Good | `not-tested` | Intraday |
| 51 | [Symmetrical Triangle](#51-symmetrical-triangle) | Classic Pattern | Medium | Good | `not-tested` | Intraday |
| 52 | [Rising Wedge](#52-rising-wedge) | Classic Pattern | Very Good | Very Good | `not-tested` | Intraday |
| 53 | [Falling Wedge](#53-falling-wedge) | Classic Pattern | Very Good | Very Good | `not-tested` | Intraday |
| 54 | [Rectangle Breakout](#54-rectangle-breakout) | Classic Pattern | Very Good | Excellent | `not-tested` | Intraday |
| 55 | [Rectangle Reversal](#55-rectangle-reversal) | Classic Pattern | Good | Excellent | `not-tested` | Range day |
| 56 | [Channel Bounce](#56-channel-bounce) | Classic Pattern | Good | Excellent | `not-tested` | Intraday |
| 57 | [Channel Breakout](#57-channel-breakout) | Classic Pattern | Very Good | Excellent | `not-tested` | Intraday |
| 58 | [Parabolic Exhaustion](#58-parabolic-exhaustion) | Classic Pattern | Excellent | Good | `not-tested` | Scalping |
| 59 | [Asian Range Breakout](#59-asian-range-breakout) | Session | Very Good | Excellent | `not-tested` | London/NY |
| 60 | [Asian Range Fakeout](#60-asian-range-fakeout) | Session | Excellent | Excellent | `not-tested` | London/NY |
| 61 | [London Open Sweep](#61-london-open-sweep) | Session | Very Good | Excellent | `not-tested` | Scalping |
| 62 | [London High Sweep in NY](#62-london-high-sweep-in-ny) | Session | Excellent | Very Good | `not-tested` | NY Session |
| 63 | [London Low Sweep in NY](#63-london-low-sweep-in-ny) | Session | Excellent | Very Good | `not-tested` | NY Session |
| 64 | [NY Open Manipulation](#64-ny-open-manipulation) | Session | Excellent | Very Good | `not-tested` | Scalping |
| 65 | [NY AM Continuation](#65-ny-am-continuation) | Session | Excellent | Very Good | `not-tested` | Intraday |
| 66 | [NY Lunch Chop Filter](#66-ny-lunch-chop-filter) | Session | Excellent | Excellent | `not-tested` | Filter |
| 67 | [London Close Reversal](#67-london-close-reversal) | Session | Good | Very Good | `not-tested` | Intraday |
| 68 | [Daily Open Retest](#68-daily-open-retest) | Session | Very Good | Very Good | `not-tested` | Intraday |
| 69 | [Weekly Open Retest](#69-weekly-open-retest) | Session | Very Good | Very Good | `not-tested` | Swing |
| 70 | [Killzone Liquidity Sweep](#70-killzone-liquidity-sweep) | Session | Excellent | Excellent | `not-tested` | Scalping |
| 71 | [Clean Breakout Retest](#71-clean-breakout-retest) | Breakout / Fakeout | Very Good | Excellent | `not-tested` | Intraday |
| 72 | [Failed Breakout](#72-failed-breakout) | Breakout / Fakeout | Excellent | Very Good | `not-tested` | Scalping |
| 73 | [Breakout Without Retest](#73-breakout-without-retest) | Breakout / Fakeout | Medium | Medium | `not-tested` | Trend day |
| 74 | [Compression Breakout](#74-compression-breakout) | Breakout / Fakeout | Excellent | Excellent | `not-tested` | Intraday |
| 75 | [False Break Above Range](#75-false-break-above-range) | Breakout / Fakeout | Excellent | Excellent | `not-tested` | Scalping |
| 76 | [False Break Below Range](#76-false-break-below-range) | Breakout / Fakeout | Excellent | Excellent | `not-tested` | Scalping |
| 77 | [Break and Retest of KLZ](#77-break-and-retest-of-klz) | Breakout / Fakeout | Excellent | Excellent | `rejected` | Intraday |
| 78 | [Failed Retest](#78-failed-retest) | Breakout / Fakeout | Very Good | Very Good | `not-tested` | Scalping |
| 79 | [Volatility Expansion Breakout](#79-volatility-expansion-breakout) | Breakout / Fakeout | Excellent | Very Good | `not-tested` | Intraday |
| 80 | [News Breakout Continuation](#80-news-breakout-continuation) | Breakout / Fakeout | Good | Medium | `not-tested` | News only |
| 81 | [Bullish Pin Bar](#81-bullish-pin-bar) | Price Action Candle | Good | Very Good | `not-tested` | Confirmation |
| 82 | [Bearish Pin Bar](#82-bearish-pin-bar) | Price Action Candle | Good | Very Good | `not-tested` | Confirmation |
| 83 | [Bullish Engulfing](#83-bullish-engulfing) | Price Action Candle | Very Good | Very Good | `not-tested` | Confirmation |
| 84 | [Bearish Engulfing](#84-bearish-engulfing) | Price Action Candle | Very Good | Very Good | `not-tested` | Confirmation |
| 85 | [Inside Bar Breakout](#85-inside-bar-breakout) | Price Action Candle | Good | Very Good | `not-tested` | Intraday |
| 86 | [Outside Bar Reversal](#86-outside-bar-reversal) | Price Action Candle | Excellent | Very Good | `not-tested` | Scalping |
| 87 | [Marubozu Continuation](#87-marubozu-continuation) | Price Action Candle | Very Good | Good | `not-tested` | Momentum |
| 88 | [Doji at Level](#88-doji-at-level) | Price Action Candle | Medium | Medium | `not-tested` | Warning |
| 89 | [Rejection Wick + BOS](#89-rejection-wick-bos) | Price Action Candle | Excellent | Excellent | `not-tested` | Entry trigger |
| 90 | [Three Candle Reversal](#90-three-candle-reversal) | Price Action Candle | Very Good | Very Good | `not-tested` | Entry trigger |
| 91 | [Bullish BOS](#91-bullish-bos) | Trend / Structure | Excellent | Excellent | `not-tested` | Structure |
| 92 | [Bearish BOS](#92-bearish-bos) | Trend / Structure | Excellent | Excellent | `not-tested` | Structure |
| 93 | [Bullish CHOCH](#93-bullish-choch) | Trend / Structure | Excellent | Excellent | `not-tested` | Reversal |
| 94 | [Bearish CHOCH](#94-bearish-choch) | Trend / Structure | Excellent | Excellent | `not-tested` | Reversal |
| 95 | [Higher High / Higher Low Trend](#95-higher-high-higher-low-trend) | Trend / Structure | Very Good | Excellent | `not-tested` | Intraday |
| 96 | [Lower Low / Lower High Trend](#96-lower-low-lower-high-trend) | Trend / Structure | Very Good | Excellent | `not-tested` | Intraday |
| 97 | [Pullback to Higher Low](#97-pullback-to-higher-low) | Trend / Structure | Very Good | Excellent | `not-tested` | Intraday |
| 98 | [Pullback to Lower High](#98-pullback-to-lower-high) | Trend / Structure | Very Good | Excellent | `not-tested` | Intraday |
| 99 | [Trend Exhaustion](#99-trend-exhaustion) | Trend / Structure | Excellent | Very Good | `not-tested` | Reversal |
| 100 | [Market Structure Shift](#100-market-structure-shift) | Trend / Structure | Excellent | Excellent | `not-tested` | Reversal |

# Detailed Execution Instructions

## 1. KLZ Retest

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Continuation or reversal from a Key Level Zone that previously caused displacement and BOS.

**Setup / Conditions:**
- Price returns to an untested/partially-tested bullish or bearish KLZ.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Zone is touched, rejection candle forms, then minor BOS in trade direction.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter on the break of the rejection candle or on retest of the minor BOS level.
- Stop Loss: Stop beyond the opposite side of the KLZ plus buffer.
- Targets: Target nearest liquidity: VWAP, POC, VAH/VAL, PDH/PDL, or 2R.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if zone is mitigated more than twice, invalidated by closes through zone, or price is in middle of value.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect last opposite candle/consolidation before displacement; require BOS and ATR-sized impulse.

## 2. Order Block Retest

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday/Swing

**Description:** Retest of the last opposite candle before a strong displacement move.

**Setup / Conditions:**
- Bullish OB: last down candle before bullish BOS. Bearish OB: last up candle before bearish BOS.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price enters OB and rejects, preferably with CHOCH/BOS on lower timeframe.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after rejection confirmation; conservative entry after lower-timeframe BOS retest.
- Stop Loss: Stop behind OB extreme.
- Targets: Target opposing liquidity or the next profile level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if OB was already fully traded through or if entry is directly into opposing VAH/VAL/PDH/PDL.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Find candle range before impulse; mark as zone; track tests and closes through zone.

## 3. Breaker Block Retest

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** A failed order block flips direction after structure breaks against it.

**Setup / Conditions:**
- Old bullish OB breaks down and becomes resistance, or old bearish OB breaks up and becomes support.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Retest of broken OB fails and BOS continues in new direction.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after retest rejection of breaker.
- Stop Loss: Stop beyond breaker zone.
- Targets: Target next swing low/high, VAL/VAH, or 2R/3R.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if no confirmed opposite BOS or retest happens far from the zone.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Identify OB, detect full break and opposite BOS, then wait for retest.

## 4. Mitigation Block Retest

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Price revisits origin of a displacement to rebalance or fill remaining institutional orders.

**Setup / Conditions:**
- Strong displacement left quickly from a small base.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price returns into base and rejects in original displacement direction.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after rejection candle or lower-timeframe BOS.
- Stop Loss: Stop beyond mitigation block.
- Targets: Target displacement high/low, FVG midpoint, or next liquidity pool.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if block has been revisited repeatedly or no displacement existed.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Mark bases before impulses; score higher when untested and aligned with HTF trend.

## 5. Fair Value Gap Fill

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping/Intraday

**Description:** Three-candle imbalance where price often returns before continuing.

**Setup / Conditions:**
- Bullish FVG: candle1 high < candle3 low. Bearish FVG: candle1 low > candle3 high.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price fills 50%-100% of FVG and rejects in expected direction.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after rejection from FVG midpoint/edge or after small BOS.
- Stop Loss: Stop beyond FVG far edge.
- Targets: Target FVG origin high/low, previous swing, or next profile level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if FVG is fully filled and price accepts through it.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Scan 3-candle windows; store gap bounds; track fill percentage.

## 6. Liquidity Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** Price takes an obvious high/low and rapidly reclaims it.

**Setup / Conditions:**
- Obvious swing high/low, equal highs/lows, session high/low, or PDH/PDL exists.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Break beyond liquidity, close back inside, then BOS opposite direction.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after reclaim candle break or BOS retest.
- Stop Loss: Stop beyond sweep wick.
- Targets: Target midpoint/range opposite side, VWAP, or POC.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if price accepts beyond swept level with multiple closes.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect wick outside level + close back inside + structure shift.

## 7. Equal Highs Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** Sweep above two or more similar highs, trapping breakout buyers.

**Setup / Conditions:**
- At least two highs within tolerance, separated by pullback.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price trades above equal highs, closes below, then bearish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter short after bearish BOS or retest of equal highs from below.
- Stop Loss: Stop above sweep high.
- Targets: Target equal-high neckline, VWAP/POC, then opposing low.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if second close holds above equal highs.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Cluster highs within tolerance; require wick sweep and bearish close.

## 8. Equal Lows Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** Sweep below two or more similar lows, trapping breakout sellers.

**Setup / Conditions:**
- At least two lows within tolerance, separated by bounce.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price trades below equal lows, closes above, then bullish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter long after bullish BOS or retest of equal lows from above.
- Stop Loss: Stop below sweep low.
- Targets: Target neckline, VWAP/POC, then opposing high.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if close acceptance below equal lows.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Cluster lows within tolerance; require wick sweep and bullish close.

## 9. Previous Day High Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Stop run above PDH followed by bearish reversal.

**Setup / Conditions:**
- Current session trades near previous day high.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price breaks PDH, closes back below, then bearish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter short after reclaim failure or bearish BOS retest.
- Stop Loss: Stop above sweep high.
- Targets: Target previous POC/VWAP/VAL or PDL if strong reversal.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if two closes above PDH or VAH acceptance supports breakout.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Compare current high vs PDH; require close below PDH and bearish structure shift.

## 10. Previous Day Low Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Stop run below PDL followed by bullish reversal.

**Setup / Conditions:**
- Current session trades near previous day low.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price breaks PDL, closes back above, then bullish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter long after reclaim or BOS retest.
- Stop Loss: Stop below sweep low.
- Targets: Target previous POC/VWAP/VAH or PDH if strong reversal.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if two closes below PDL or VAL acceptance supports breakdown.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Compare current low vs PDL; require close above PDL and bullish structure shift.

## 11. Session High Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Intraday high is swept and rejected.

**Setup / Conditions:**
- A clean session high is visible and price revisits it.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Wick above session high, close below, bearish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short after bearish trigger.
- Stop Loss: Stop above sweep wick.
- Targets: Target VWAP, POC, or session midpoint.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject during strong trend above VWAP walking upper band.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Track session high, detect sweep-and-reclaim failure.

## 12. Session Low Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Intraday low is swept and rejected.

**Setup / Conditions:**
- A clean session low is visible and price revisits it.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Wick below session low, close above, bullish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long after bullish trigger.
- Stop Loss: Stop below sweep wick.
- Targets: Target VWAP, POC, or session midpoint.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject during strong trend below VWAP walking lower band.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Track session low, detect sweep and reclaim.

## 13. Trendline Liquidity Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Retail trendline is broken to collect stops, then price reverses.

**Setup / Conditions:**
- At least 3 touches form a visible trendline.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- False break outside trendline, close back inside, then BOS opposite.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after re-entry + BOS.
- Stop Loss: Stop beyond false-break extreme.
- Targets: Target opposite trendline side, VWAP, or next swing.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if trendline break accepts and retests successfully.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Fit line through swing points; detect break, reclaim, and structure shift.

## 14. Stop Hunt Reversal

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Fast spike through a level followed by immediate reclaim.

**Setup / Conditions:**
- Price approaches obvious liquidity level during active session.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Large wick pierces level and candle closes back beyond level; next candle confirms.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter on confirmation candle break.
- Stop Loss: Stop beyond spike.
- Targets: Target 1R/2R, VWAP, or nearest profile level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if spike is news continuation with large follow-through.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect outsized wick > body and reclaim relative to key level.

## 15. Displacement Continuation

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Strong impulse signals institutional direction; trade shallow pullback.

**Setup / Conditions:**
- Impulse candle sequence creates BOS and displacement.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Pullback holds 38.2%-61.8% or OB/FVG, then continuation BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter on pullback rejection or continuation break.
- Stop Loss: Stop beyond pullback swing.
- Targets: Target measured move or next liquidity.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if pullback becomes deep and structure flips.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Measure impulse ATR multiple, retracement %, and continuation break.

## 16. Previous VAH Rejection

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** Previous value area high rejects price as resistance.

**Setup / Conditions:**
- Price approaches previous VAH from below or after failed break above.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Wick above VAH, close below, then bearish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short below rejection candle low or BOS retest.
- Stop Loss: Stop above rejection wick.
- Targets: Target POC then VAL.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if price accepts above VAH with two closes/retest hold.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Use prev VAH; detect wick/close relation and BOS.

## 17. Previous VAL Rejection

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** Previous value area low rejects price as support.

**Setup / Conditions:**
- Price approaches previous VAL from above or after failed break below.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Wick below VAL, close above, then bullish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long above rejection candle high or BOS retest.
- Stop Loss: Stop below rejection wick.
- Targets: Target POC then VAH.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if price accepts below VAL with two closes/retest hold.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Use prev VAL; detect wick/close relation and BOS.

## 18. VAH Flip Support

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** Previous VAH breaks and flips from resistance into support.

**Setup / Conditions:**
- Price closes above VAH and holds above it.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Retest of VAH holds; bullish BOS after retest.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long on retest rejection or BOS retest.
- Stop Loss: Stop below VAH/zone low.
- Targets: Target next resistance, session high, or upper VWAP band.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if price returns inside previous value and rotates to POC.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Require acceptance above VAH before treating it as support.

## 19. VAL Flip Resistance

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** Previous VAL breaks and flips from support into resistance.

**Setup / Conditions:**
- Price closes below VAL and holds below it.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Retest of VAL fails; bearish BOS after retest.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short on retest rejection or BOS retest.
- Stop Loss: Stop above VAL/zone high.
- Targets: Target next support, session low, or lower VWAP band.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if price returns inside previous value and rotates to POC.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Require acceptance below VAL before treating it as resistance.

## 20. Failed Auction Above VAH

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** Auction above value fails and returns inside value.

**Setup / Conditions:**
- Price breaks above VAH but cannot accept.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close back below VAH and bearish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short after close back inside or retest of VAH from below.
- Stop Loss: Stop above failed auction high.
- Targets: Target POC first, VAL second.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if price builds value above VAH.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect break outside value + close back inside within limited candles.

## 21. Failed Auction Below VAL

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** Auction below value fails and returns inside value.

**Setup / Conditions:**
- Price breaks below VAL but cannot accept.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close back above VAL and bullish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long after close back inside or retest of VAL from above.
- Stop Loss: Stop below failed auction low.
- Targets: Target POC first, VAH second.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if price builds value below VAL.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect break below value + close back inside quickly.

## 22. POC Magnet Rotation

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Good  
**Best Use:** Range day

**Description:** When inside value, price often rotates to POC.

**Setup / Conditions:**
- Open/current price inside previous value area; no trend acceptance.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Rejection from VAH/VAL or value edge aims toward POC.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter from value edge after rejection.
- Stop Loss: Stop beyond rejected edge.
- Targets: Target POC; optional runner to opposite edge.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject in strong trend day or outside value acceptance.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Classify inside value; target POC if range conditions.

## 23. Inside Value Rotation

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Good  
**Best Use:** Range day

**Description:** Trade value area extremes back toward center/opposite side.

**Setup / Conditions:**
- Open inside previous value and price remains balanced.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Buy VAL rejection or sell VAH rejection.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after rejection candle.
- Stop Loss: Stop outside value edge.
- Targets: Target POC then opposite VA edge.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if price accepts outside value.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect current price within VAL-VAH and repeated rotations.

## 24. Outside Value Acceptance

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Trend day

**Description:** Acceptance outside previous value indicates directional auction.

**Setup / Conditions:**
- Price opens or breaks outside VAH/VAL.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Two closes outside + retest holds.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Trade in direction of acceptance after retest.
- Stop Loss: Stop back inside value.
- Targets: Target next HTF level, PDH/PDL, or measured range.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if price quickly returns inside value.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Define acceptance with closes, time, and retest.

## 25. Poor High / Poor Low Repair

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Medium  
**Best Use:** Intraday

**Description:** Weak unfinished auction high/low often gets revisited.

**Setup / Conditions:**
- Prior profile has poor high/low or equal TPOs at extreme.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price moves toward and attacks the poor extreme.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter only with trend/acceptance toward the target; not blindly.
- Stop Loss: Stop behind most recent swing.
- Targets: Target the poor high/low repair level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if opposing KLZ/VA level blocks path.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Flag equal/flat profile extremes and monitor repair path.

## 26. Single Prints Fill

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Medium  
**Best Use:** Intraday

**Description:** Single prints indicate fast auction imbalance that may later fill.

**Setup / Conditions:**
- Previous session has single-print area.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price returns toward single prints; acceptance into zone.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter in direction of fill after acceptance, or fade after full fill + rejection.
- Stop Loss: Stop outside entry structure.
- Targets: Target midpoint/full fill or next value level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if no acceptance into single-print zone.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Store single print bounds; detect entry and fill percentage.

## 27. LVN Rejection

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Medium  
**Best Use:** Intraday

**Description:** Low Volume Node often rejects due to low acceptance.

**Setup / Conditions:**
- Price approaches LVN from either side.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Rejection candle and structure turn away from LVN.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after rejection confirmation.
- Stop Loss: Stop beyond LVN.
- Targets: Target nearest HVN/POC.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if price accepts through LVN.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Need volume profile nodes; detect local minima in volume distribution.

## 28. HVN Magnet

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Medium  
**Best Use:** Range day

**Description:** High Volume Node attracts price in balanced markets.

**Setup / Conditions:**
- Price is inside balance and HVN/POC nearby.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Directional move starts toward HVN after rejection from range edge.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter from edge; use HVN as target, not entry.
- Stop Loss: Stop beyond edge.
- Targets: Target HVN/POC.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject on trend days; HVNs can become chop zones.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect high-volume peaks and use as magnets during balance.

## 29. VWAP Reclaim Long

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Price reclaims VWAP after trading below it.

**Setup / Conditions:**
- Price was below VWAP, then closes above.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Retest of VWAP holds and bullish BOS forms.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long on VWAP retest rejection or BOS retest.
- Stop Loss: Stop below VWAP retest low.
- Targets: Target upper band, VAH, PDH, or 2R.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if price chops across VWAP repeatedly.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect previous below state, two closes above, retest hold.

## 30. VWAP Rejection Short

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Price loses VWAP and rejects it from below.

**Setup / Conditions:**
- Price was above VWAP, then closes below.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Retest of VWAP fails and bearish BOS forms.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short on VWAP rejection or BOS retest.
- Stop Loss: Stop above VWAP retest high.
- Targets: Target lower band, VAL, PDL, or 2R.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if price chops across VWAP repeatedly.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect previous above state, two closes below, retest fail.

## 31. VWAP Pullback Long

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Trend is above VWAP; pullback to VWAP provides continuation.

**Setup / Conditions:**
- VWAP slope flat/up; price above VWAP with bullish structure.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Pullback touches or nears VWAP and rejects.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long after rejection candle high break.
- Stop Loss: Stop below pullback low/VWAP.
- Targets: Target recent high then upper band.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if VWAP is flat and price is balanced inside value.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Track price above VWAP and pullback distance threshold.

## 32. VWAP Pullback Short

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Trend is below VWAP; pullback to VWAP provides continuation.

**Setup / Conditions:**
- VWAP slope flat/down; price below VWAP with bearish structure.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Pullback touches or nears VWAP and rejects.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short after rejection candle low break.
- Stop Loss: Stop above pullback high/VWAP.
- Targets: Target recent low then lower band.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if VWAP is flat and price is balanced.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Track price below VWAP and pullback to VWAP.

## 33. VWAP Band 2 Reversal

**Category:** VWAP  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Good  
**Best Use:** Scalping

**Description:** Price reaches extreme VWAP band and rejects.

**Setup / Conditions:**
- Price extends to upper/lower band 2 near key level.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Rejection wick + CHOCH/BOS back toward VWAP.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after structure shift; do not catch first touch blindly.
- Stop Loss: Stop beyond band extreme.
- Targets: Target band 1 then VWAP.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject during band-walk strong trend.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect touch of band2 + reversal candle + BOS.

## 34. VWAP Band Trend Ride

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Trend day

**Description:** Strong trend walks upper/lower VWAP band.

**Setup / Conditions:**
- Price holds above VWAP and near upper band, or below VWAP and near lower band.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Pullbacks hold band1/VWAP and continue.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter pullbacks, not extended candles.
- Stop Loss: Stop behind pullback swing.
- Targets: Target next liquidity or trailing structure.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject reversal signals while band-walk persists.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect persistent closes on one side and band proximity.

## 35. VWAP Chop Filter

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Filter

**Description:** Repeated VWAP crosses indicate no clean directional edge.

**Setup / Conditions:**
- Price crosses VWAP many times in short window.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- No trade; wait for acceptance away from VWAP.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Execution is WAIT only.
- Stop Loss: No stop; no trade.
- Targets: No target; filter.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Do not approve trend strategies during chop.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Count VWAP crosses over N candles; if > threshold, set neutral.

## 36. Anchored VWAP Retest

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday/Swing

**Description:** AVWAP from major swing/news acts as institutional average cost.

**Setup / Conditions:**
- Anchor from swing high/low, weekly open, daily open, London/NY open, or news impulse.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price retests AVWAP and rejects in trend direction.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after rejection + BOS.
- Stop Loss: Stop beyond AVWAP retest swing.
- Targets: Target next structure/liquidity.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if AVWAP has been crossed repeatedly.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Compute VWAP from anchor index; detect retest/rejection.

## 37. Weekly VWAP Confluence

**Category:** VWAP  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Swing

**Description:** Weekly VWAP aligns with a trade level.

**Setup / Conditions:**
- Signal occurs near weekly VWAP plus KLZ/VA/PDH/PDL.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Primary signal triggers while weekly VWAP supports direction.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Use as confluence, not standalone entry.
- Stop Loss: Use primary setup stop.
- Targets: Use primary setup target.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if weekly VWAP is opposing directly.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Calculate weekly session VWAP and proximity to signal.

## 38. VWAP + VAH/VAL Confluence

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** VWAP or band aligns with Market Profile VAH/VAL.

**Setup / Conditions:**
- Price reaches VAH/VAL while also at VWAP/band.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Rejection or flip setup triggers at confluence.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter using VAH/VAL trigger.
- Stop Loss: Stop beyond VA level and wick.
- Targets: Target POC/VWAP/opposite VA.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if both levels are already accepted through.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Check absolute distance between VA level and VWAP/band.

## 39. Double Top

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday/Swing

**Description:** Two similar highs fail at resistance and break neckline.

**Setup / Conditions:**
- Two swing highs within tolerance with pullback between.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close below neckline after second top.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short neckline break or retest.
- Stop Loss: Stop above second top.
- Targets: Target measured height or next support.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if second top strongly closes above first top.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Cluster two highs; neckline = intervening low.

## 40. Double Bottom

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday/Swing

**Description:** Two similar lows fail at support and break neckline.

**Setup / Conditions:**
- Two swing lows within tolerance with bounce between.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close above neckline after second bottom.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long neckline break or retest.
- Stop Loss: Stop below second bottom.
- Targets: Target measured height or next resistance.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if second bottom strongly closes below first bottom.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Cluster two lows; neckline = intervening high.

## 41. Triple Top

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Good  
**Best Use:** Swing

**Description:** Three failed tests of resistance.

**Setup / Conditions:**
- Three similar highs at same zone.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close below neckline/support after third high.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short on neckline break/retest.
- Stop Loss: Stop above third high.
- Targets: Target range height or next support.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if tests become ascending continuation.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect three swing highs within tolerance.

## 42. Triple Bottom

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Good  
**Best Use:** Swing

**Description:** Three failed tests of support.

**Setup / Conditions:**
- Three similar lows at same zone.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close above neckline/resistance after third low.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long on neckline break/retest.
- Stop Loss: Stop below third low.
- Targets: Target range height or next resistance.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if tests become descending continuation.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect three swing lows within tolerance.

## 43. Head and Shoulders

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday/Swing

**Description:** Reversal with left shoulder, higher head, lower right shoulder.

**Setup / Conditions:**
- Appears after bullish move near resistance.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close below neckline; retest fails.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short neckline retest or break if momentum strong.
- Stop Loss: Stop above right shoulder or head.
- Targets: Target measured head-to-neckline distance.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject in strong uptrend without neckline break.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Identify sequence high-low-higher high-low-lower high and neckline.

## 44. Inverse Head and Shoulders

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday/Swing

**Description:** Bullish reversal with left shoulder, lower head, higher right shoulder.

**Setup / Conditions:**
- Appears after bearish move near support.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close above neckline; retest holds.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long neckline retest or break if momentum strong.
- Stop Loss: Stop below right shoulder or head.
- Targets: Target measured head-to-neckline distance.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject in strong downtrend without neckline break.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Identify low-high-lower low-high-higher low and neckline.

## 45. Bull Flag

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping/Intraday

**Description:** Bullish impulse followed by shallow downward/sideways channel.

**Setup / Conditions:**
- Strong pole above VWAP or after bullish BOS.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close above flag resistance.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long breakout retest or close if small flag.
- Stop Loss: Stop below flag low.
- Targets: Target pole measured move or next liquidity.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if pullback retraces >61.8% or breaks structure.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect impulse ATR multiple + shallow corrective channel.

## 46. Bear Flag

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping/Intraday

**Description:** Bearish impulse followed by shallow upward/sideways channel.

**Setup / Conditions:**
- Strong pole below VWAP or after bearish BOS.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close below flag support.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short breakout retest or close if small flag.
- Stop Loss: Stop above flag high.
- Targets: Target pole measured move or next liquidity.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if pullback retraces >61.8% or flips structure.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect bearish impulse + shallow corrective channel.

## 47. Bullish Pennant

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Bullish impulse followed by contracting triangle.

**Setup / Conditions:**
- Strong bullish pole then lower highs/higher lows compression.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close above pennant resistance.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long breakout retest.
- Stop Loss: Stop below pennant low.
- Targets: Target pole projection.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if breakout into strong resistance.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect triangle contraction after impulse.

## 48. Bearish Pennant

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Bearish impulse followed by contracting triangle.

**Setup / Conditions:**
- Strong bearish pole then lower highs/higher lows compression.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close below pennant support.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short breakout retest.
- Stop Loss: Stop above pennant high.
- Targets: Target pole projection.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if breakdown into strong support.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect triangle contraction after bearish impulse.

## 49. Ascending Triangle

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Flat resistance and higher lows, often bullish.

**Setup / Conditions:**
- At least two similar highs and rising lows.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close above resistance and retest holds.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long after retest or confirmed close.
- Stop Loss: Stop below last higher low.
- Targets: Target triangle height.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if breakout directly into VAH/PDH/KLZ resistance.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect horizontal resistance and rising lows.

## 50. Descending Triangle

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Flat support and lower highs, often bearish.

**Setup / Conditions:**
- At least two similar lows and falling highs.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close below support and retest fails.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short after retest or confirmed close.
- Stop Loss: Stop above last lower high.
- Targets: Target triangle height.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if breakdown directly into VAL/PDL/KLZ support.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect horizontal support and falling highs.

## 51. Symmetrical Triangle

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Medium  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** Compression between lower highs and higher lows.

**Setup / Conditions:**
- Converging trendlines with reduced range.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Breakout close beyond either side.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Prefer retest entry after breakout.
- Stop Loss: Stop inside/behind opposite side.
- Targets: Target triangle height or next liquidity.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if breakout candle is too far from entry.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Fit converging lines on swing highs/lows.

## 52. Rising Wedge

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Price rises in narrowing channel; often bearish when broken.

**Setup / Conditions:**
- Higher highs/lows but range contracts and momentum weakens.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close below wedge support.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short breakdown retest.
- Stop Loss: Stop above last wedge high.
- Targets: Target wedge base or next support.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if wedge breaks upward with acceptance.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect rising converging support/resistance.

## 53. Falling Wedge

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Price falls in narrowing channel; often bullish when broken.

**Setup / Conditions:**
- Lower highs/lows but range contracts and momentum weakens.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close above wedge resistance.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long breakout retest.
- Stop Loss: Stop below last wedge low.
- Targets: Target wedge base or next resistance.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if wedge breaks downward with acceptance.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect falling converging support/resistance.

## 54. Rectangle Breakout

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Range breaks and retests support/resistance.

**Setup / Conditions:**
- Clear horizontal range with multiple touches.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close outside range and retest holds.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter retest of broken boundary.
- Stop Loss: Stop back inside range.
- Targets: Target range height projection.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if breakout is a wick only.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect range high/low and closes outside.

## 55. Rectangle Reversal

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Range day

**Description:** Trade from rectangle edges back to center/opposite side.

**Setup / Conditions:**
- Balanced range with stable support/resistance.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Rejection from range low/high.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Buy range low or sell range high after rejection.
- Stop Loss: Stop outside range.
- Targets: Target midpoint then opposite side.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if trend day or outside value acceptance.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Classify range and edge touches.

## 56. Channel Bounce

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Price respects parallel rising/falling channel.

**Setup / Conditions:**
- At least 2 touches each side or 3 total reliable touches.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Touch channel boundary and rejection in channel direction.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after rejection candle.
- Stop Loss: Stop outside channel.
- Targets: Target channel midline/opposite boundary.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if channel slope is too steep or boundary breaks.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Fit parallel regression or swing trendlines.

## 57. Channel Breakout

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Price breaks out of a channel and retests boundary.

**Setup / Conditions:**
- Established rising/falling channel.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close outside channel and retest holds from other side.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter retest continuation.
- Stop Loss: Stop back inside channel.
- Targets: Target measured channel width or next level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if breakout lacks close or retest.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect channel and boundary close/retest.

## 58. Parabolic Exhaustion

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Scalping

**Description:** Move accelerates unsustainably and reverses at level.

**Setup / Conditions:**
- Multiple candles expand in same direction far from VWAP.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Rejection at key level + CHOCH/BOS opposite.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after structure shift; never short/long just because extended.
- Stop Loss: Stop beyond extreme.
- Targets: Target VWAP/band1 or prior structure.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject during news continuation or clean band-walk.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect acceleration, ATR extension, and reversal trigger.

## 59. Asian Range Breakout

**Category:** Session  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** London/NY

**Description:** Breakout from Asian session high/low.

**Setup / Conditions:**
- Define Asian range before London/NY.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close outside Asian range and retest holds.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter retest continuation.
- Stop Loss: Stop back inside range.
- Targets: Target range projection or London/NY liquidity.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if breakout occurs during dead time or into HTF level.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Calculate session range; detect close/retest.

## 60. Asian Range Fakeout

**Category:** Session  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** London/NY

**Description:** Sweep Asian range then reverse.

**Setup / Conditions:**
- Asian high/low is clear.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Break range extreme, close back inside, BOS opposite.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after re-entry and BOS.
- Stop Loss: Stop beyond fakeout wick.
- Targets: Target range midpoint/opposite side.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if acceptance outside Asian range.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect range sweep and reclaim.

## 61. London Open Sweep

**Category:** Session  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** Liquidity sweep near London open.

**Setup / Conditions:**
- During London open window, price sweeps Asian high/low or prior micro liquidity.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Reclaim plus CHOCH/BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after structure shift.
- Stop Loss: Stop beyond sweep.
- Targets: Target VWAP, opposite Asian side, or session liquidity.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if no reclaim within limited candles.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Apply time filter and liquidity sweep logic.

## 62. London High Sweep in NY

**Category:** Session  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** NY Session

**Description:** NY sweeps London high and reverses.

**Setup / Conditions:**
- London high is established before NY.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- NY trades above London high, closes back below, bearish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short after reclaim failure.
- Stop Loss: Stop above NY sweep high.
- Targets: Target VWAP/POC/London midpoint/low.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if NY accepts above London high.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Track London session high; detect NY sweep.

## 63. London Low Sweep in NY

**Category:** Session  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** NY Session

**Description:** NY sweeps London low and reverses.

**Setup / Conditions:**
- London low established before NY.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- NY trades below London low, closes back above, bullish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long after reclaim.
- Stop Loss: Stop below NY sweep low.
- Targets: Target VWAP/POC/London midpoint/high.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if NY accepts below London low.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Track London session low; detect NY sweep.

## 64. NY Open Manipulation

**Category:** Session  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** First NY move traps traders then reverses.

**Setup / Conditions:**
- Within first 15-45 minutes after NY open.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Sharp move sweeps liquidity and fails; BOS opposite.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after NY manipulation reclaim and BOS.
- Stop Loss: Stop beyond manipulation extreme.
- Targets: Target VWAP, opening price, or opposite liquidity.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if move aligns with strong news continuation.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Use time window, speed/ATR spike, sweep, and BOS.

## 65. NY AM Continuation

**Category:** Session  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** After NY manipulation, trend continues in real direction.

**Setup / Conditions:**
- Manipulation completed and structure has shifted.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Pullback to VWAP/KLZ/FVG holds in new trend direction.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter on pullback rejection.
- Stop Loss: Stop beyond pullback swing.
- Targets: Target session expansion levels.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject in lunch chop or after target already hit.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect NY reversal then continuation pullback.

## 66. NY Lunch Chop Filter

**Category:** Session  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Filter

**Description:** Avoid low-quality midday chop.

**Setup / Conditions:**
- Time window during NY lunch and low ATR/range.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- No trade unless exceptional level confluence and breakout.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Execution is WAIT.
- Stop Loss: No stop.
- Targets: No target.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject most scalps.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Time + ATR compression + VWAP chop count.

## 67. London Close Reversal

**Category:** Session  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Flows reverse near London close.

**Setup / Conditions:**
- Near London close time and price extended from VWAP.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Liquidity sweep/exhaustion and opposite BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after reversal confirmation.
- Stop Loss: Stop beyond extreme.
- Targets: Target VWAP/session midpoint.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if US trend day remains strong.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Time window + extension + reversal trigger.

## 68. Daily Open Retest

**Category:** Session  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Daily open acts as intraday polarity.

**Setup / Conditions:**
- Price moves away from daily open then retests.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Daily open holds as support/resistance with BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after rejection in prevailing bias.
- Stop Loss: Stop beyond retest swing.
- Targets: Target session high/low or VWAP band.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if daily open is chopped through repeatedly.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Calculate daily open; track retests and crosses.

## 69. Weekly Open Retest

**Category:** Session  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Swing

**Description:** Weekly open acts as higher-timeframe polarity.

**Setup / Conditions:**
- Price revisits weekly open during week.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Reaction at weekly open aligns with HTF bias.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter on lower-timeframe trigger.
- Stop Loss: Stop beyond weekly-open reaction swing.
- Targets: Target weekly range expansion or next HTF level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if weekly open has no reaction and is crossed repeatedly.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Store weekly open and proximity.

## 70. Killzone Liquidity Sweep

**Category:** Session  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** Liquidity sweep during London or NY killzone.

**Setup / Conditions:**
- Within active killzone and near liquidity level.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Sweep + reclaim + BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after BOS/retest.
- Stop Loss: Stop beyond sweep.
- Targets: Target nearest liquidity/profile level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject outside killzone unless confluence is exceptional.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Combine time window with sweep detector.

## 71. Clean Breakout Retest

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Level breaks cleanly, then retest confirms.

**Setup / Conditions:**
- Strong level with consolidation below/above.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close beyond level, retest holds, continuation candle.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter retest.
- Stop Loss: Stop back through level.
- Targets: Target measured range or next level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if breakout is overextended into opposing level.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect close outside and retest hold.

## 72. Failed Breakout

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Breakout fails and reverses back through level.

**Setup / Conditions:**
- Price breaks obvious range/level.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close back inside and BOS opposite.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after failed breakout confirmation.
- Stop Loss: Stop beyond fakeout extreme.
- Targets: Target range midpoint/opposite side.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if volume/acceptance continues outside.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect wick or short-lived close outside + reclaim.

## 73. Breakout Without Retest

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Medium  
**Works with Forex Majors:** Medium  
**Best Use:** Trend day

**Description:** Momentum breakout continues without pullback.

**Setup / Conditions:**
- High volatility trend day and no nearby opposing level.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Strong close beyond level with displacement.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter only if risk small; otherwise wait for pullback.
- Stop Loss: Stop below breakout candle/structure.
- Targets: Target next liquidity; trail.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject on normal days; this is lower quality.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect large displacement and lack of retest.

## 74. Compression Breakout

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Tight range compression expands into momentum.

**Setup / Conditions:**
- ATR/range contracts before active session or news.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Breakout candle closes outside compression with expansion.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter retest or first pullback.
- Stop Loss: Stop inside compression.
- Targets: Target measured compression height multiple.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if breakout into major opposing KLZ/VA level.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect low ATR window and range breakout.

## 75. False Break Above Range

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** Range high break fails and returns inside.

**Setup / Conditions:**
- Defined range with clear high.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price breaks range high then closes back inside; bearish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short after re-entry/retest.
- Stop Loss: Stop above false-break high.
- Targets: Target midpoint/range low.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if two closes above range.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect range high sweep and close inside.

## 76. False Break Below Range

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** Range low break fails and returns inside.

**Setup / Conditions:**
- Defined range with clear low.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price breaks range low then closes back inside; bullish BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long after re-entry/retest.
- Stop Loss: Stop below false-break low.
- Targets: Target midpoint/range high.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if two closes below range.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect range low sweep and close inside.

## 77. Break and Retest of KLZ

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** A structural zone breaks and flips direction.

**Setup / Conditions:**
- KLZ is established and then broken with displacement.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Retest of broken KLZ holds as opposite polarity.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after retest rejection.
- Stop Loss: Stop through KLZ.
- Targets: Target next KLZ/VA/liquidity.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if no displacement through KLZ.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect KLZ invalidation followed by polarity retest.

## 78. Failed Retest

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Retest of broken level fails quickly and price reverses.

**Setup / Conditions:**
- A level was broken and market attempts retest.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Retest cannot hold; price snaps back through trigger level.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter in failure direction after snapback.
- Stop Loss: Stop beyond failed retest.
- Targets: Target opposite side of range or VWAP/POC.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if retest actually holds with multiple candles.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect retest attempt and failure candle.

## 79. Volatility Expansion Breakout

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** ATR expands after compression, starting directional move.

**Setup / Conditions:**
- Recent ATR percentile low, tight candles, clear boundary.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Breakout candle > ATR threshold and closes beyond boundary.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter first pullback/retest.
- Stop Loss: Stop inside compression.
- Targets: Target measured expansion or next liquidity.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if expansion occurs into immediate HTF level.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Compute ATR compression then expansion ratio.

## 80. News Breakout Continuation

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Medium  
**Best Use:** News only

**Description:** News impulse continues after first pullback.

**Setup / Conditions:**
- Scheduled high-impact news; initial spike has clear direction.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Pullback holds 38-50% and continuation BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after pullback continuation, not during first spike.
- Stop Loss: Stop beyond pullback swing.
- Targets: Target news range extension.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if spread/slippage high or whipsaw both sides.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Requires economic calendar flag; detect impulse and pullback.

## 81. Bullish Pin Bar

**Category:** Price Action Candle  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Confirmation

**Description:** Long lower wick shows rejection of lower prices.

**Setup / Conditions:**
- Pin bar forms at support/VAL/KLZ/PDL/lower VWAP band.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Next candle breaks pin high.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long on break of pin high.
- Stop Loss: Stop below pin low.
- Targets: Target next resistance or 2R.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if pin is in middle of nowhere.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect lower wick >= 2x body and close upper half.

## 82. Bearish Pin Bar

**Category:** Price Action Candle  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Confirmation

**Description:** Long upper wick shows rejection of higher prices.

**Setup / Conditions:**
- Pin bar forms at resistance/VAH/KLZ/PDH/upper VWAP band.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Next candle breaks pin low.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short on break of pin low.
- Stop Loss: Stop above pin high.
- Targets: Target next support or 2R.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if pin is in middle of nowhere.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect upper wick >= 2x body and close lower half.

## 83. Bullish Engulfing

**Category:** Price Action Candle  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Confirmation

**Description:** Bull candle engulfs prior bearish candle at support.

**Setup / Conditions:**
- Occurs at support or after sweep.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close above prior candle high/body.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long on close or retest of engulfing midpoint.
- Stop Loss: Stop below engulfing low.
- Targets: Target next resistance or 2R.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if engulfing is late after large rally.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Compare candle body/high-low to prior candle.

## 84. Bearish Engulfing

**Category:** Price Action Candle  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Confirmation

**Description:** Bear candle engulfs prior bullish candle at resistance.

**Setup / Conditions:**
- Occurs at resistance or after sweep.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close below prior candle low/body.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short on close or retest of engulfing midpoint.
- Stop Loss: Stop above engulfing high.
- Targets: Target next support or 2R.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if engulfing is late after large selloff.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Compare candle body/high-low to prior candle.

## 85. Inside Bar Breakout

**Category:** Price Action Candle  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Small candle inside previous candle range breaks directionally.

**Setup / Conditions:**
- Mother candle forms, inside bar contracts.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close beyond mother candle high/low.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter breakout or retest.
- Stop Loss: Stop opposite side of mother candle or inside bar.
- Targets: Target mother candle range projection.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject in choppy mid-value unless aligned with trend.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect candle high<prev high and low>prev low.

## 86. Outside Bar Reversal

**Category:** Price Action Candle  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Candle sweeps both sides and closes strongly one way.

**Setup / Conditions:**
- Forms at key level or after liquidity hunt.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Outside bar closes directional and next candle confirms.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter on break of outside bar close direction.
- Stop Loss: Stop beyond outside bar extreme.
- Targets: Target VWAP/POC or 2R.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if outside bar range makes stop too large.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect high>prev high and low<prev low plus strong close.

## 87. Marubozu Continuation

**Category:** Price Action Candle  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Good  
**Best Use:** Momentum

**Description:** Full-body candle shows strong directional control.

**Setup / Conditions:**
- After breakout or BOS, candle has tiny wicks.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Small pullback holds candle midpoint.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter continuation on midpoint retest or next break.
- Stop Loss: Stop behind candle midpoint/low-high.
- Targets: Target next liquidity.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if candle ends directly at major opposing level.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect body > 80% of range and breakout context.

## 88. Doji at Level

**Category:** Price Action Candle  
**Works with Gold/XAUUSD:** Medium  
**Works with Forex Majors:** Medium  
**Best Use:** Warning

**Description:** Indecision at a key level; not a trade alone.

**Setup / Conditions:**
- Doji forms at key level.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Wait for break of doji high/low in context direction.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter only after confirmation break.
- Stop Loss: Stop opposite doji extreme.
- Targets: Target next level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject standalone doji signals.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect body <= 20% of candle range.

## 89. Rejection Wick + BOS

**Category:** Price Action Candle  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Entry trigger

**Description:** Wick rejects level then structure breaks in opposite direction.

**Setup / Conditions:**
- At key level or liquidity sweep.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Rejection wick followed by BOS.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after BOS or retest.
- Stop Loss: Stop beyond wick.
- Targets: Target next liquidity/profile level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject without BOS.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Combine wick rule with swing break.

## 90. Three Candle Reversal

**Category:** Price Action Candle  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Entry trigger

**Description:** Exhaustion candle, reversal candle, confirmation candle.

**Setup / Conditions:**
- After extended move into key level.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Third candle confirms opposite direction.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter on third candle close or small pullback.
- Stop Loss: Stop beyond pattern extreme.
- Targets: Target VWAP/POC or 2R.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if not at level.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect 3-candle pattern with reversal close.

## 91. Bullish BOS

**Category:** Trend / Structure  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Structure

**Description:** Price breaks confirmed swing high.

**Setup / Conditions:**
- Swing high is established and price approaches it.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close above swing high.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Use as confirmation, not standalone entry; enter pullback after BOS.
- Stop Loss: Stop below pullback low.
- Targets: Target next swing/level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject wick-only break.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Swing detection + close above high.

## 92. Bearish BOS

**Category:** Trend / Structure  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Structure

**Description:** Price breaks confirmed swing low.

**Setup / Conditions:**
- Swing low is established and price approaches it.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Close below swing low.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Use as confirmation; enter pullback after BOS.
- Stop Loss: Stop above pullback high.
- Targets: Target next swing/level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject wick-only break.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Swing detection + close below low.

## 93. Bullish CHOCH

**Category:** Trend / Structure  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Reversal

**Description:** First bullish structure shift after bearish sequence.

**Setup / Conditions:**
- Market is making LL/LH.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price breaks most recent lower high.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after retest/FVG/OB following CHOCH.
- Stop Loss: Stop below CHOCH origin.
- Targets: Target next swing high/VAH/VWAP.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if no displacement after CHOCH.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect trend state then break of LH.

## 94. Bearish CHOCH

**Category:** Trend / Structure  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Reversal

**Description:** First bearish structure shift after bullish sequence.

**Setup / Conditions:**
- Market is making HH/HL.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price breaks most recent higher low.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after retest/FVG/OB following CHOCH.
- Stop Loss: Stop above CHOCH origin.
- Targets: Target next swing low/VAL/VWAP.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if no displacement after CHOCH.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect trend state then break of HL.

## 95. Higher High / Higher Low Trend

**Category:** Trend / Structure  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Bullish trend continuation structure.

**Setup / Conditions:**
- Sequence of HH and HL exists.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Pullback to HL zone rejects and breaks minor high.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long at HL confirmation.
- Stop Loss: Stop below HL.
- Targets: Target next HH/extension.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if HL breaks.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Track swing sequence classification.

## 96. Lower Low / Lower High Trend

**Category:** Trend / Structure  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Bearish trend continuation structure.

**Setup / Conditions:**
- Sequence of LL and LH exists.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Pullback to LH zone rejects and breaks minor low.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short at LH confirmation.
- Stop Loss: Stop above LH.
- Targets: Target next LL/extension.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if LH breaks.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Track swing sequence classification.

## 97. Pullback to Higher Low

**Category:** Trend / Structure  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Buy the higher low in a bullish trend.

**Setup / Conditions:**
- HTF or current trend bullish.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price pulls back into support/KLZ/VWAP and forms HL.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Long after break of pullback high.
- Stop Loss: Stop below HL.
- Targets: Target prior high then extension.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if pullback breaks prior HL.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect bullish trend and local HL formation.

## 98. Pullback to Lower High

**Category:** Trend / Structure  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Sell the lower high in a bearish trend.

**Setup / Conditions:**
- HTF or current trend bearish.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Price pulls back into resistance/KLZ/VWAP and forms LH.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Short after break of pullback low.
- Stop Loss: Stop above LH.
- Targets: Target prior low then extension.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if pullback breaks prior LH.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect bearish trend and local LH formation.

## 99. Trend Exhaustion

**Category:** Trend / Structure  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Reversal

**Description:** Trend makes new extreme but weak follow-through.

**Setup / Conditions:**
- Extended move into key level or VWAP band.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- New high/low fails; CHOCH occurs opposite.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter after CHOCH, not before.
- Stop Loss: Stop beyond exhaustion extreme.
- Targets: Target VWAP/POC or first opposing level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject in strong trend without CHOCH.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect new extreme with reduced candle body/range and reversal break.

## 100. Market Structure Shift

**Category:** Trend / Structure  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Reversal

**Description:** CHOCH plus displacement confirms shift in control.

**Setup / Conditions:**
- Existing trend is mature or at key level.
- Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.
**Trigger / Confirmation:**
- Opposite structure break with strong displacement.
- Prefer candle close confirmation over wick-only confirmation.
**Execution:**
- Entry: Enter pullback to FVG/OB after MSS.
- Stop Loss: Stop beyond MSS origin.
- Targets: Target next liquidity/profile level.
- Minimum risk/reward: 1:2 unless the signal is used only as a filter or partial target.
**Invalidation / Reject:**
- Reject if break is weak and immediately retraced.
- Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
**Python Detection Hint:**
- Detect CHOCH + impulse ATR multiple.


# Python Signal Object Template

```python
signal = {
    "name": "KLZ_RETEST_LONG",
    "direction": "LONG",
    "market": "XAUUSD",
    "timeframe": "M5",
    "entry_zone": [0, 0],
    "entry_trigger": "break_rejection_high",
    "stop_loss": 0,
    "targets": [0, 0],
    "risk_reward": 0,
    "context": {
        "structure": "bullish_bos",
        "vwap_position": "above",
        "profile_context": "near_prev_val",
        "session": "ny_open",
        "nearest_opposing_level": 0
    },
    "python_confidence": 0
}
```
