# XAUUSD / Forex AI Signal Execution Manual (Claude-Optimized)

**Purpose:** This manual provides a comprehensive framework for Claude, acting as an AI review agent, to analyze potential XAUUSD and Forex trading signals. The goal is to enable Claude to review market context, apply advanced trading methodologies, and approve only high-quality setups for execution. This document emphasizes a narrative-driven, analytical approach, moving beyond mere pattern recognition to contextual understanding.

**Important:** This is not financial advice and does not guarantee profits. The rules are designed for systematic analysis, backtesting, and discretionary review by an AI agent.

## Recommended Architecture (Claude-Centric)

1.  **Data Layer**: Comprehensive OHLCV candles, session times, previous day high/low, previous day VAH/VAL/POC, VWAP and bands, swing highs/lows, ATR, and other relevant market data. Claude will access this data for its analysis.
2.  **Signal Generation Layer**: An external system (or Claude itself, if prompted for pattern recognition) detects raw signals based on objective rules. This layer identifies potential setups without deep contextual analysis.
3.  **Claude AI Review Layer**: Claude analyzes the generated signals, considering market context, confluence, risk/reward, and overall market narrative. It uses its advanced reasoning capabilities to approve, reject, or wait for further confirmation.
4.  **Execution Layer**: Only signals approved by Claude, with clearly defined entry, stop, targets, and invalidation, are executed.

## Claude's Analytical Focus

Claude's review process should prioritize the following elements, moving beyond simple indicator-based detection:

-   **Market Structure**: Identification of Break of Structure (BOS) and Change of Character (CHOCH) to understand trend and potential reversals.
-   **Liquidity**: Recognition of liquidity pools (e.g., swing highs/lows, previous day's extremes, session highs/lows) and the dynamics of liquidity sweeps.
-   **Institutional Footprints**: Detection of Key Level Zones (KLZ), Order Blocks (OB), Breaker Blocks, Mitigation Blocks, and Fair Value Gaps (FVG) as areas of institutional interest.
-   **Volume Profile**: Understanding Value Area High (VAH), Value Area Low (VAL), Point of Control (POC), High Volume Nodes (HVN), and Low Volume Nodes (LVN) to gauge market acceptance and rejection.
-   **Session Dynamics**: Awareness of Asian, London, New York, and NY lunch sessions, and their typical behaviors (e.g., range expansion, manipulation).
-   **Volatility**: Assessment of Average True Range (ATR) and volatility expansion/compression to contextualize price movements.
-   **Risk Management**: Strict adherence to predefined risk/reward ratios and clear invalidation criteria.

## Global Approval Rules for Claude

Claude **MUST REJECT** a signal when any of these conditions are true:

-   **Risk/Reward**: The potential risk/reward ratio is below 1:2.
-   **Middle of Value**: Entry is within a balanced value area with no clear edge or directional bias.
-   **Opposing Levels**: The signal trades directly into a strong, unmitigated opposing key level.
-   **Unclear Invalidation**: The setup lacks a clear and logical stop loss or invalidation point.
-   **Level Acceptance**: The key level associated with the signal has already been accepted through (e.g., price has closed and retested beyond it).
-   **VWAP Chop**: The market is exhibiting choppy, non-directional movement around VWAP.
-   **Stale Setup**: The setup is old, unclear, or has been over-tested, indicating diminished potency.

Claude **MAY APPROVE** a signal only when:

-   **Meaningful Level**: The setup originates from or interacts with a significant key level (e.g., KLZ, OB, VAH/VAL, PDH/PDL).
-   **Structure Confirmation**: Market structure (BOS/CHOCH) clearly confirms the intended direction of the trade.
-   **Clear Parameters**: Entry, stop loss, and target levels are precisely defined and justifiable.
-   **Acceptable Risk/Reward**: The risk/reward ratio meets or exceeds the minimum threshold (e.g., 1:2).
-   **Appropriate Context**: The session, volatility, and overall market narrative align with the signal's premise.

## Standard AI Review JSON (Claude Output Schema)

Claude should output its decision and analysis in the following JSON format. This structured output ensures clarity and machine-readability for subsequent execution systems. Claude **MUST** provide a detailed `reasoning_chain_of_thought` explaining its decision process.

```json
{
  "decision": "APPROVE | REJECT | WAIT",
  "market": "XAUUSD | EURUSD | GBPUSD | USDJPY | OTHER",
  "signal_name": "[Name of the detected signal, e.g., KLZ Retest]",
  "direction": "LONG | SHORT | NEUTRAL",
  "bias": "BULLISH | BEARISH | NEUTRAL",
  "entry": {
    "price": 0.0,
    "type": "MARKET | LIMIT | STOP"
  },
  "stop_loss": 0.0,
  "target_1": 0.0,
  "target_2": 0.0,
  "risk_reward": 0.0,
  "confidence": "HIGH | MEDIUM | LOW",
  "reasoning_chain_of_thought": "[Detailed explanation of Claude's decision, referencing market context, confluence, and adherence to rules. This should be a narrative explanation, not just a list of points.]",
  "confluence_score_details": {
    "klz_ob_breaker": "+25 if at KLZ/OB/Breaker",
    "vah_val_poc": "+20 if at VAH/VAL/POC",
    "pdh_pdl_sweep": "+20 if at PDH/PDL or session high/low sweep",
    "vwap_band": "+15 if at VWAP or VWAP band",
    "bos_choch_confirmation": "+15 if BOS/CHOCH confirmation",
    "active_session": "+10 if during London/NY active session",
    "fresh_untested_level": "+10 if fresh/untested level",
    "middle_of_value": "-30 if in middle of value",
    "level_accepted_through": "-25 if level accepted through",
    "tested_more_than_twice": "-20 if tested more than twice",
    "direct_opposite_level": "-20 if directly into strong opposite level",
    "vwap_chop": "-20 if VWAP chop",
    "final_score": 0
  }
}
```

## Confluence Score Guide (for Claude's Internal Assessment)

Claude should use the following scoring system to quantify the strength of a signal. This score contributes to the `confidence` level in the JSON output and informs the `reasoning_chain_of_thought`.

**Add points for:**

-   **+25**: At Key Level Zone (KLZ), Order Block (OB), or Breaker Block.
-   **+20**: At Value Area High (VAH), Value Area Low (VAL), or Point of Control (POC).
-   **+20**: At Previous Day High (PDH), Previous Day Low (PDL), or after a significant session high/low sweep.
-   **+15**: At VWAP or a significant VWAP band (e.g., Band 1).
-   **+15**: With clear Break of Structure (BOS) or Change of Character (CHOCH) confirmation in the trade direction.
-   **+10**: During the London or New York active trading session.
-   **+10**: If the key level is fresh and largely untested.

**Subtract points for:**

-   **-30**: If the entry is in the middle of a balanced value area.
-   **-25**: If the key level has already been accepted through (e.g., multiple closes beyond it).
-   **-20**: If the level has been tested more than twice without a clear resolution.
-   **-20**: If the trade is directly against a strong, unmitigated opposing level.
-   **-20**: If the market is chopping around VWAP, indicating indecision.

**Decision Thresholds:**

-   **80-100**: Strong candidate. High confidence for approval.
-   **65-79**: Moderate candidate. Requires extra confirmation or a
    WAIT decision.
-   **Below 65**: Weak candidate. REJECT.

# Signal Index

| # | Signal | Category | Gold/XAUUSD | Forex Majors | Best Use |
|---:|---|---|---|---|---|
| 1 | [KLZ Retest](#1-klz-retest) | Institutional / SMC | Excellent | Excellent | Intraday |
| 2 | [Order Block Retest](#2-order-block-retest) | Institutional / SMC | Excellent | Excellent | Intraday/Swing |
| 3 | [Breaker Block Retest](#3-breaker-block-retest) | Institutional / SMC | Excellent | Very Good | Intraday |
| 4 | [Mitigation Block Retest](#4-mitigation-block-retest) | Institutional / SMC | Very Good | Very Good | Intraday |
| 5 | [Fair Value Gap Fill](#5-fair-value-gap-fill) | Institutional / SMC | Excellent | Excellent | Scalping/Intraday |
| 6 | [Liquidity Sweep](#6-liquidity-sweep) | Institutional / SMC | Excellent | Excellent | Scalping |
| 7 | [Equal Highs Sweep](#7-equal-highs-sweep) | Institutional / SMC | Excellent | Excellent | Scalping |
| 8 | [Equal Lows Sweep](#8-equal-lows-sweep) | Institutional / SMC | Excellent | Excellent | Scalping |
| 9 | [Previous Day High Sweep](#9-previous-day-high-sweep) | Institutional / SMC | Excellent | Very Good | Intraday |
| 10 | [Previous Day Low Sweep](#10-previous-day-low-sweep) | Institutional / SMC | Excellent | Very Good | Intraday |
| 11 | [Session High Sweep](#11-session-high-sweep) | Institutional / SMC | Excellent | Very Good | Scalping |
| 12 | [Session Low Sweep](#12-session-low-sweep) | Institutional / SMC | Excellent | Very Good | Scalping |
| 13 | [Trendline Liquidity Sweep](#13-trendline-liquidity-sweep) | Institutional / SMC | Very Good | Very Good | Scalping |
| 14 | [Stop Hunt Reversal](#14-stop-hunt-reversal) | Institutional / SMC | Excellent | Very Good | Scalping |
| 15 | [Displacement Continuation](#15-displacement-continuation) | Institutional / SMC | Excellent | Excellent | Intraday |
| 16 | [Previous VAH Rejection](#16-previous-vah-rejection) | Market Profile | Excellent | Good | Intraday |
| 17 | [Previous VAL Rejection](#17-previous-val-rejection) | Market Profile | Excellent | Good | Intraday |
| 18 | [VAH Flip Support](#18-vah-flip-support) | Market Profile | Excellent | Good | Intraday |
| 19 | [VAL Flip Resistance](#19-val-flip-resistance) | Market Profile | Excellent | Good | Intraday |
| 20 | [Failed Auction Above VAH](#20-failed-auction-above-vah) | Market Profile | Excellent | Good | Intraday |
| 21 | [Failed Auction Below VAL](#21-failed-auction-below-val) | Market Profile | Excellent | Good | Intraday |
| 22 | [POC Magnet Rotation](#22-poc-magnet-rotation) | Market Profile | Very Good | Good | Range day |
| 23 | [Inside Value Rotation](#23-inside-value-rotation) | Market Profile | Good | Good | Range day |
| 24 | [Outside Value Acceptance](#24-outside-value-acceptance) | Market Profile | Excellent | Good | Trend day |
| 25 | [Poor High / Poor Low Repair](#25-poor-high-poor-low-repair) | Market Profile | Very Good | Medium | Intraday |
| 26 | [Single Prints Fill](#26-single-prints-fill) | Market Profile | Very Good | Medium | Intraday |
| 27 | [LVN Rejection](#27-lvn-rejection) | Market Profile | Very Good | Medium | Intraday |
| 28 | [HVN Magnet](#28-hvn-magnet) | Market Profile | Good | Medium | Range day |
| 29 | [VWAP Reclaim Long](#29-vwap-reclaim-long) | VWAP | Excellent | Very Good | Intraday |
| 30 | [VWAP Rejection Short](#30-vwap-rejection-short) | VWAP | Excellent | Very Good | Intraday |
| 31 | [VWAP Pullback Long](#31-vwap-pullback-long) | VWAP | Excellent | Very Good | Scalping |
| 32 | [VWAP Pullback Short](#32-vwap-pullback-short) | VWAP | Excellent | Very Good | Scalping |
| 33 | [VWAP Band 2 Reversal](#33-vwap-band-2-reversal) | VWAP | Very Good | Good | Scalping |
| 34 | [VWAP Band Trend Ride](#34-vwap-band-trend-ride) | VWAP | Excellent | Good | Trend day |
| 35 | [VWAP Chop Filter](#35-vwap-chop-filter) | VWAP | Excellent | Excellent | Filter |
| 36 | [Anchored VWAP Retest](#36-anchored-vwap-retest) | VWAP | Excellent | Excellent | Intraday/Swing |
| 37 | [Weekly VWAP Confluence](#37-weekly-vwap-confluence) | VWAP | Very Good | Very Good | Swing |
| 38 | [VWAP + VAH/VAL Confluence](#38-vwap-vah-val-confluence) | VWAP | Excellent | Good | Intraday |
| 39 | [Double Top](#39-double-top) | Classic Pattern | Very Good | Excellent | Intraday/Swing |
| 40 | [Double Bottom](#40-double-bottom) | Classic Pattern | Very Good | Excellent | Intraday/Swing |
| 41 | [Triple Top](#41-triple-top) | Classic Pattern | Good | Good | Swing |
| 42 | [Triple Bottom](#42-triple-bottom) | Classic Pattern | Good | Good | Swing |
| 43 | [Head and Shoulders](#43-head-and-shoulders) | Classic Pattern | Good | Very Good | Intraday/Swing |
| 44 | [Inverse Head and Shoulders](#44-inverse-head-and-shoulders) | Classic Pattern | Good | Very Good | Intraday/Swing |
| 45 | [Bull Flag](#45-bull-flag) | Classic Pattern | Excellent | Excellent | Scalping/Intraday |
| 46 | [Bear Flag](#46-bear-flag) | Classic Pattern | Excellent | Excellent | Scalping/Intraday |
| 47 | [Bullish Pennant](#47-bullish-pennant) | Classic Pattern | Very Good | Very Good | Intraday |
| 48 | [Bearish Pennant](#48-bearish-pennant) | Classic Pattern | Very Good | Very Good | Intraday |
| 49 | [Ascending Triangle](#49-ascending-triangle) | Classic Pattern | Good | Very Good | Intraday |
| 50 | [Descending Triangle](#50-descending-triangle) | Classic Pattern | Good | Very Good | Intraday |
| 51 | [Symmetrical Triangle](#51-symmetrical-triangle) | Classic Pattern | Medium | Good | Intraday |
| 52 | [Rising Wedge](#52-rising-wedge) | Classic Pattern | Very Good | Very Good | Intraday |
| 53 | [Falling Wedge](#53-falling-wedge) | Classic Pattern | Very Good | Very Good | Intraday |
| 54 | [Rectangle Breakout](#54-rectangle-breakout) | Classic Pattern | Very Good | Excellent | Intraday |
| 55 | [Rectangle Reversal](#55-rectangle-reversal) | Classic Pattern | Good | Excellent | Range day |
| 56 | [Channel Bounce](#56-channel-bounce) | Classic Pattern | Good | Excellent | Intraday |
| 57 | [Channel Breakout](#57-channel-breakout) | Classic Pattern | Very Good | Excellent | Intraday |
| 58 | [Parabolic Exhaustion](#58-parabolic-exhaustion) | Classic Pattern | Excellent | Good | Scalping |
| 59 | [Asian Range Breakout](#59-asian-range-breakout) | Session | Very Good | Excellent | London/NY |
| 60 | [Asian Range Fakeout](#60-asian-range-fakeout) | Session | Excellent | Excellent | London/NY |
| 61 | [London Open Sweep](#61-london-open-sweep) | Session | Very Good | Excellent | Scalping |
| 62 | [London High Sweep in NY](#62-london-high-sweep-in-ny) | Session | Excellent | Very Good | NY Session |
| 63 | [London Low Sweep in NY](#63-london-low-sweep-in-ny) | Session | Excellent | Very Good | NY Session |
| 64 | [NY Open Manipulation](#64-ny-open-manipulation) | Session | Excellent | Very Good | Scalping |
| 65 | [NY AM Continuation](#65-ny-am-continuation) | Session | Excellent | Very Good | Intraday |
| 66 | [NY Lunch Chop Filter](#66-ny-lunch-chop-filter) | Session | Excellent | Excellent | Filter |
| 67 | [London Close Reversal](#67-london-close-reversal) | Session | Good | Very Good | Intraday |
| 68 | [Daily Open Retest](#68-daily-open-retest) | Session | Very Good | Very Good | Intraday |
| 69 | [Weekly Open Retest](#69-weekly-open-retest) | Session | Very Good | Very Good | Swing |
| 70 | [Killzone Liquidity Sweep](#70-killzone-liquidity-sweep) | Session | Excellent | Excellent | Scalping |
| 71 | [Clean Breakout Retest](#71-clean-breakout-retest) | Breakout / Fakeout | Very Good | Excellent | Intraday |
| 72 | [Failed Breakout](#72-failed-breakout) | Breakout / Fakeout | Excellent | Very Good | Scalping |
| 73 | [Breakout Without Retest](#73-breakout-without-retest) | Breakout / Fakeout | Medium | Medium | Trend day |
| 74 | [Compression Breakout](#74-compression-breakout) | Breakout / Fakeout | Excellent | Excellent | Intraday |
| 75 | [False Break Above Range](#75-false-break-above-range) | Breakout / Fakeout | Excellent | Excellent | Scalping |
| 76 | [False Break Below Range](#76-false-break-below-range) | Breakout / Fakeout | Excellent | Excellent | Scalping |
| 77 | [Break and Retest of KLZ](#77-break-and-retest-of-klz) | Breakout / Fakeout | Excellent | Excellent | Intraday |
| 78 | [Failed Retest](#78-failed-retest) | Breakout / Fakeout | Very Good | Very Good | Scalping |
| 79 | [Volatility Expansion Breakout](#79-volatility-expansion-breakout) | Breakout / Fakeout | Excellent | Very Good | Intraday |
| 80 | [News Breakout Continuation](#80-news-breakout-continuation) | Breakout / Fakeout | Good | Medium | News only |
| 81 | [Bullish Pin Bar](#81-bullish-pin-bar) | Price Action Candle | Good | Very Good | Confirmation |
| 82 | [Bearish Pin Bar](#82-bearish-pin-bar) | Price Action Candle | Good | Very Good | Confirmation |
| 83 | [Bullish Engulfing](#83-bullish-engulfing) | Price Action Candle | Very Good | Very Good | Confirmation |
| 84 | [Bearish Engulfing](#84-bearish-engulfing) | Price Action Candle | Very Good | Very Good | Confirmation |
| 85 | [Inside Bar Breakout](#85-inside-bar-breakout) | Price Action Candle | Good | Very Good | Intraday |
| 86 | [Outside Bar Reversal](#86-outside-bar-reversal) | Price Action Candle | Excellent | Very Good | Scalping |
| 87 | [Marubozu Continuation](#87-marubozu-continuation) | Price Action Candle | Very Good | Good | Momentum |
| 88 | [Doji at Level](#88-doji-at-level) | Price Action Candle | Medium | Medium | Warning |
| 89 | [Rejection Wick + BOS](#89-rejection-wick-bos) | Price Action Candle | Excellent | Excellent | Entry trigger |
| 90 | [Three Candle Reversal](#90-three-candle-reversal) | Price Action Candle | Very Good | Very Good | Entry trigger |
| 91 | [Bullish BOS](#91-bullish-bos) | Trend / Structure | Excellent | Excellent | Structure |
| 92 | [Bearish BOS](#92-bearish-bos) | Trend / Structure | Excellent | Excellent | Structure |
| 93 | [Bullish CHOCH](#93-bullish-choch) | Trend / Structure | Excellent | Excellent | Reversal |
| 94 | [Bearish CHOCH](#94-bearish-choch) | Trend / Structure | Excellent | Excellent | Reversal |
| 95 | [Higher High / Higher Low Trend](#95-higher-high-higher-low-trend) | Trend / Structure | Very Good | Excellent | Intraday |
| 96 | [Lower Low / Lower High Trend](#96-lower-low-lower-high-trend) | Trend / Structure | Very Good | Excellent | Intraday |
| 97 | [Pullback to Higher Low](#97-pullback-to-higher-low) | Trend / Structure | Very Good | Excellent | Intraday |
| 98 | [Pullback to Lower High](#98-pullback-to-lower-high) | Trend / Structure | Very Good | Excellent | Intraday |
| 99 | [Trend Exhaustion](#99-trend-exhaustion) | Trend / Structure | Excellent | Very Good | Reversal |
| 100 | [Market Structure Shift](#100-market-structure-shift) | Trend / Structure | Excellent | Excellent | Reversal |
| 101 | [Swing Breakout Sequence (SBS Alias)](#101-swing-breakout-sequence-sbs--alias) | Breakout / Liquidity / Swing Model | Excellent | Excellent | Scalping/Intraday |
| 102 | [Candle Range Theory (CRT) Model](#102-candle-range-theory-crt-model) | ICT-Derived / Liquidity / Range Model | Excellent | Excellent | Intraday/Scalping |

# Detailed Execution Instructions (Claude-Optimized)

## 1. KLZ Retest

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Continuation or reversal from a Key Level Zone (KLZ) that previously caused significant displacement and a Break of Structure (BOS). This indicates an area where institutional activity was dominant.

**Claude Analytical Focus:**
-   **Identify KLZ**: Locate a price zone where a strong, impulsive move originated, leading to a clear BOS.
-   **Contextualize Retest**: Observe price returning to this KLZ. Is it an untested or partially tested zone? Is it aligned with higher timeframe market structure or other meaningful levels?
-   **Confirm Rejection**: Look for clear signs of rejection from the KLZ, such as a strong wick or a reversal candle pattern. The subsequent price action should show a minor BOS in the intended trade direction.

**Setup / Conditions:**
-   Price returns to an untested/partially-tested bullish or bearish KLZ.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Zone is touched, a clear rejection candle forms, followed by a minor BOS in the trade direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the break of the rejection candle or on a retest of the minor BOS level.
-   **Stop Loss**: Place the stop loss beyond the opposite side of the KLZ, allowing for a small buffer.
-   **Targets**: Target nearest liquidity pools such as VWAP, POC, VAH/VAL, PDH/PDL, or aim for a minimum 2R (2 times risk) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the KLZ has been mitigated more than twice, indicating its strength is diminished.
-   Reject if price closes and accepts through the KLZ, invalidating the zone.
-   Reject if the entry is in the middle of a balanced value area, lacking clear edge.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 2. Order Block Retest

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday/Swing

**Description:** A retest of the last opposite-colored candle before a strong, impulsive displacement move. This candle represents an area where institutions placed significant orders.

**Claude Analytical Focus:**
-   **Identify Order Block (OB)**: Pinpoint the last bearish candle before a strong bullish move (for a bullish OB) or the last bullish candle before a strong bearish move (for a bearish OB). This OB should be associated with a clear displacement and BOS.
-   **Contextualize Retest**: Observe price returning to the OB. Is it a fresh, untested OB? Is it aligned with higher timeframe trend or other key levels?
-   **Confirm Rejection**: Look for price to interact with the OB and show signs of rejection, such as wicks into the block or reversal candle patterns, followed by a BOS in the direction of the original displacement.

**Setup / Conditions:**
-   Bullish OB: The last down candle before a bullish BOS. Bearish OB: The last up candle before a bearish BOS.
-   Price returns to the identified OB.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price touches the OB, forms a rejection candle, and then a minor BOS in the trade direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the break of the rejection candle or on a retest of the minor BOS level.
-   **Stop Loss**: Place the stop loss beyond the opposite side of the OB, allowing for a small buffer.
-   **Targets**: Target nearest liquidity pools, such as previous swing highs/lows, FVGs, or aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the OB is fully mitigated or price closes and accepts through it.
-   Reject if the OB has been tested multiple times without a strong reaction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 3. Breaker Block Retest

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** A retest of a price level that was previously an Order Block but was then broken through by a strong move, causing it to
flip its role (e.g., from support to resistance).

**Claude Analytical Focus:**
-   **Identify Breaker Block**: Locate a previous Order Block that failed to hold price and was broken with strong displacement. This broken OB now acts as a Breaker Block.
-   **Contextualize Retest**: Observe price returning to the Breaker Block. Is it a fresh retest? Does it align with the new trend direction established by the break?
-   **Confirm Rejection**: Look for price to interact with the Breaker Block and show signs of rejection in the new trend direction, followed by a minor BOS.

**Setup / Conditions:**
-   A previous OB is broken with strong displacement.
-   Price returns to retest the broken OB (now a Breaker Block).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price touches the Breaker Block, forms a rejection candle, and then a minor BOS in the trade direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the break of the rejection candle or on a retest of the minor BOS level.
-   **Stop Loss**: Place the stop loss beyond the opposite side of the Breaker Block, allowing for a small buffer.
-   **Targets**: Target nearest liquidity pools, such as previous swing highs/lows, FVGs, or aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price closes and accepts back through the Breaker Block, invalidating its new role.
-   Reject if the Breaker Block has been tested multiple times without a strong reaction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 4. Mitigation Block Retest

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** A retest of a price level that was previously a swing high or low that failed to break structure, and was subsequently broken. It acts similarly to a Breaker Block but originates from a failed swing rather than an Order Block.

**Claude Analytical Focus:**
-   **Identify Mitigation Block**: Locate a swing high/low that failed to create a new high/low (failed BOS) and was then broken with displacement. This broken swing level acts as a Mitigation Block.
-   **Contextualize Retest**: Observe price returning to the Mitigation Block. Is it a fresh retest? Does it align with the new trend direction established by the break?
-   **Confirm Rejection**: Look for price to interact with the Mitigation Block and show signs of rejection in the new trend direction, followed by a minor BOS.

**Setup / Conditions:**
-   A previous swing high/low that failed to break structure is broken with strong displacement.
-   Price returns to retest the broken swing level (now a Mitigation Block).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price touches the Mitigation Block, forms a rejection candle, and then a minor BOS in the trade direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the break of the rejection candle or on a retest of the minor BOS level.
-   **Stop Loss**: Place the stop loss beyond the opposite side of the Mitigation Block, allowing for a small buffer.
-   **Targets**: Target nearest liquidity pools, such as previous swing highs/lows, FVGs, or aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price closes and accepts back through the Mitigation Block, invalidating its new role.
-   Reject if the Mitigation Block has been tested multiple times without a strong reaction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 5. Fair Value Gap Fill

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping/Intraday

**Description:** A trade setup based on price returning to fill an imbalance or inefficiency in price delivery, known as a Fair Value Gap (FVG).

**Claude Analytical Focus:**
-   **Identify FVG**: Locate a three-candle sequence where the wicks of the first and third candles do not overlap, leaving a gap in price action. This indicates an imbalance.
-   **Contextualize Fill**: Observe price returning to the FVG. Is it a partial or full fill? Does the FVG align with other key levels like an OB or VWAP?
-   **Confirm Rejection**: Look for price to interact with the FVG and show signs of rejection, such as a strong wick or a reversal candle pattern, followed by a minor BOS in the direction of the original imbalance.

**Setup / Conditions:**
-   A clear FVG is identified following a strong displacement move.
-   Price returns to partially or fully fill the FVG.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price enters the FVG, forms a rejection candle, and then a minor BOS in the trade direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the break of the rejection candle or on a retest of the minor BOS level.
-   **Stop Loss**: Place the stop loss beyond the opposite side of the FVG or the swing point that created the FVG, allowing for a small buffer.
-   **Targets**: Target nearest liquidity pools, such as previous swing highs/lows, or aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price closes and accepts completely through the FVG, invalidating the imbalance.
-   Reject if the FVG has been filled multiple times without a strong reaction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

*(Note: For brevity, the remaining 95 signals follow the same structural format: Category, Works with, Best Use, Description, Claude Analytical Focus, Setup/Conditions, Trigger/Confirmation, Execution, and Invalidation/Reject. Claude should apply the same rigorous analytical focus to all signals, emphasizing market narrative, liquidity, and structure over simple pattern matching.)*

## References

[1] Inner Circle Trader (ICT) Methodologies and Smart Money Concepts (SMC)
[2] Market Profile and Volume-Weighted Average Price (VWAP) Techniques
[3] Best Practices for AI-Driven Trading Analysis and LLM Prompt Engineering

## 6. Liquidity Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** Price aggressively moves beyond a clear liquidity level (e.g., swing high/low, previous session extreme) to trigger stop losses or pending orders, then quickly reverses. This often indicates institutional manipulation before a true directional move.

**Claude Analytical Focus:**
-   **Identify Liquidity Pool**: Locate obvious swing highs/lows, previous day/session extremes, or equal highs/lows where stop losses or pending orders are likely to be clustered.
-   **Detect Sweep**: Observe a sharp, often quick, price movement that pierces through this liquidity level. The candle responsible for the sweep typically has a long wick extending beyond the level.
-   **Confirm Reversal**: Look for immediate rejection of the swept level. This is often characterized by the sweeping candle closing back within the previous range, followed by a strong candle in the opposite direction, and ideally a Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe.
-   **Contextualize**: Consider the time of day (e.g., session opens), news events, and higher timeframe bias. Sweeps during high-impact news or session opens are often more potent.

**Setup / Conditions:**
-   A clear, identifiable liquidity pool exists (e.g., previous swing high/low, equal highs/lows, session high/low).
-   Price aggressively pushes through this liquidity level.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price sweeps the liquidity level, and the candle closes back inside the previous range (or a significant portion of the wick is rejected).
-   A subsequent candle confirms the reversal, ideally with a minor BOS or CHOCH in the opposite direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the confirming candle closes, or on a retest of the swept level/BOS level.
-   **Stop Loss**: Place the stop loss beyond the extreme of the sweep (e.g., beyond the wick of the sweeping candle), allowing for a small buffer.
-   **Targets**: Target the opposite side of the range, the next significant liquidity pool, a Fair Value Gap (FVG) that needs filling, or aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price accepts beyond the swept liquidity level (e.g., multiple candles close and hold above/below it), indicating a true breakout rather than a sweep.
-   Reject if the reversal is weak or lacks a clear BOS/CHOCH confirmation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 7. Equal Highs Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** Price moves above a series of relatively equal highs (representing a clear liquidity pool) to trigger buy stops and then rapidly reverses, indicating a liquidity grab before a downward move.

**Claude Analytical Focus:**
-   **Identify Equal Highs**: Locate two or more swing highs that are at approximately the same price level, forming a visible resistance zone. This area represents a significant liquidity pool for buy-side stops.
-   **Detect Sweep**: Observe price aggressively pushing above these equal highs. The candle responsible for the sweep will typically have a prominent wick extending above the highs, but the body should ideally close back below the level.
-   **Confirm Reversal**: Look for immediate rejection of the swept highs. This is often characterized by the sweeping candle closing back within the previous range, followed by a strong bearish candle, and ideally a Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe, confirming the shift in momentum.
-   **Contextualize**: Consider the higher timeframe bias, session dynamics (e.g., London/NY open), and proximity to other key resistance levels (e.g., VAH, PDH, Order Blocks). A sweep of equal highs into a higher timeframe resistance level is a high-probability setup.

**Setup / Conditions:**
-   Two or more identifiable swing highs are at a similar price level, creating an 'equal highs' liquidity zone.
-   Price aggressively moves above these equal highs.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price sweeps the equal highs, and the candle closes back inside the previous range (or a significant portion of the wick is rejected).
-   A subsequent bearish candle confirms the reversal, ideally with a minor BOS or CHOCH in the opposite direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the confirming bearish candle closes, or on a retest of the swept level/BOS level.
-   **Stop Loss**: Place the stop loss beyond the extreme of the sweep (e.g., beyond the wick of the sweeping candle), allowing for a small buffer.
-   **Targets**: Target the opposite side of the range, the next significant liquidity pool (e.g., equal lows, FVG), or aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price accepts beyond the swept equal highs (e.g., multiple candles close and hold above it), indicating a true breakout rather than a sweep.
-   Reject if the reversal is weak or lacks a clear BOS/CHOCH confirmation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 8. Equal Lows Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** Price moves below a series of relatively equal lows (representing a clear liquidity pool) to trigger sell stops and then rapidly reverses, indicating a liquidity grab before an upward move.

**Claude Analytical Focus:**
-   **Identify Equal Lows**: Locate two or more swing lows that are at approximately the same price level, forming a visible support zone. This area represents a significant liquidity pool for sell-side stops.
-   **Detect Sweep**: Observe price aggressively pushing below these equal lows. The candle responsible for the sweep will typically have a prominent wick extending below the lows, but the body should ideally close back above the level.
-   **Confirm Reversal**: Look for immediate rejection of the swept lows. This is often characterized by the sweeping candle closing back within the previous range, followed by a strong bullish candle, and ideally a Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe, confirming the shift in momentum.
-   **Contextualize**: Consider the higher timeframe bias, session dynamics (e.g., London/NY open), and proximity to other key support levels (e.g., VAL, PDL, Order Blocks). A sweep of equal lows into a higher timeframe support level is a high-probability setup.

**Setup / Conditions:**
-   Two or more identifiable swing lows are at a similar price level, creating an 'equal lows' liquidity zone.
-   Price aggressively moves below these equal lows.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price sweeps the equal lows, and the candle closes back inside the previous range (or a significant portion of the wick is rejected).
-   A subsequent bullish candle confirms the reversal, ideally with a minor BOS or CHOCH in the opposite direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the confirming bullish candle closes, or on a retest of the swept level/BOS level.
-   **Stop Loss**: Place the stop loss beyond the extreme of the sweep (e.g., beyond the wick of the sweeping candle), allowing for a small buffer.
-   **Targets**: Target the opposite side of the range, the next significant liquidity pool (e.g., equal highs, FVG), or aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price accepts beyond the swept equal lows (e.g., multiple candles close and hold below it), indicating a true breakout rather than a sweep.
-   Reject if the reversal is weak or lacks a clear BOS/CHOCH confirmation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 9. Previous Day High Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Price moves above the Previous Day High (PDH) to collect liquidity (stop losses, breakout orders) and then reverses, indicating a potential shift in intraday direction.

**Claude Analytical Focus:**
-   **Identify PDH**: Clearly mark the high of the previous trading day. This is a significant liquidity magnet.
-   **Detect Sweep**: Observe price aggressively pushing above the PDH. The sweeping candle should ideally have a long wick above the PDH, with the body closing back below it.
-   **Confirm Reversal**: Look for immediate rejection of the PDH. This is often followed by a strong bearish candle and a Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe, confirming the bearish shift.
-   **Contextualize**: Consider the higher timeframe bias and the current session. A PDH sweep during the London or New York session, especially if it aligns with a higher timeframe resistance, is a high-probability setup.

**Setup / Conditions:**
-   The Previous Day High (PDH) is clearly defined.
-   Price trades above the PDH.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price sweeps the PDH, and the candle closes back below the PDH (or a significant portion of the wick is rejected).
-   A subsequent bearish candle confirms the reversal, ideally with a minor BOS or CHOCH in the opposite direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the confirming bearish candle closes, or on a retest of the swept PDH/BOS level.
-   **Stop Loss**: Place the stop loss beyond the extreme of the sweep (e.g., beyond the wick of the sweeping candle), allowing for a small buffer.
-   **Targets**: Target the Previous Day Low (PDL), VWAP, POC, or the next significant liquidity pool. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price accepts above the PDH (e.g., multiple candles close and hold above it), indicating a true breakout rather than a sweep.
-   Reject if the reversal is weak or lacks a clear BOS/CHOCH confirmation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 10. Previous Day Low Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Price moves below the Previous Day Low (PDL) to collect liquidity (stop losses, breakout orders) and then reverses, indicating a potential shift in intraday direction.

**Claude Analytical Focus:**
-   **Identify PDL**: Clearly mark the low of the previous trading day. This is a significant liquidity magnet.
-   **Detect Sweep**: Observe price aggressively pushing below the PDL. The sweeping candle should ideally have a long wick below the PDL, with the body closing back above it.
-   **Confirm Reversal**: Look for immediate rejection of the PDL. This is often followed by a strong bullish candle and a Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe, confirming the bullish shift.
-   **Contextualize**: Consider the higher timeframe bias and the current session. A PDL sweep during the London or New York session, especially if it aligns with a higher timeframe support, is a high-probability setup.

**Setup / Conditions:**
-   The Previous Day Low (PDL) is clearly defined.
-   Price trades below the PDL.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price sweeps the PDL, and the candle closes back above the PDL (or a significant portion of the wick is rejected).
-   A subsequent bullish candle confirms the reversal, ideally with a minor BOS or CHOCH in the opposite direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the confirming bullish candle closes, or on a retest of the swept PDL/BOS level.
-   **Stop Loss**: Place the stop loss beyond the extreme of the sweep (e.g., beyond the wick of the sweeping candle), allowing for a small buffer.
-   **Targets**: Target the Previous Day High (PDH), VWAP, POC, or the next significant liquidity pool. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price accepts below the PDL (e.g., multiple candles close and hold below it), indicating a true breakout rather than a sweep.
-   Reject if the reversal is weak or lacks a clear BOS/CHOCH confirmation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 11. Session High Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Price moves above the current session's high (e.g., Asian session high, London session high) to collect liquidity and then reverses, indicating a potential short-term reversal within the trading session.

**Claude Analytical Focus:**
-   **Identify Session High**: Clearly mark the high of the current trading session (e.g., Asian session, London session). This is a key intraday liquidity point.
-   **Detect Sweep**: Observe price aggressively pushing above the session high. The sweeping candle should ideally have a long wick above the session high, with the body closing back below it.
-   **Confirm Reversal**: Look for immediate rejection of the session high. This is often followed by a strong bearish candle and a Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe, confirming the bearish shift.
-   **Contextualize**: Consider the overall intraday bias and the proximity to higher timeframe resistance levels. A session high sweep that aligns with a daily or weekly resistance is a higher probability setup.

**Setup / Conditions:**
-   The current session high is clearly defined.
-   Price trades above the session high.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price sweeps the session high, and the candle closes back below the session high (or a significant portion of the wick is rejected).
-   A subsequent bearish candle confirms the reversal, ideally with a minor BOS or CHOCH in the opposite direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the confirming bearish candle closes, or on a retest of the swept session high/BOS level.
-   **Stop Loss**: Place the stop loss beyond the extreme of the sweep (e.g., beyond the wick of the sweeping candle), allowing for a small buffer.
-   **Targets**: Target the session low, VWAP, POC, or the next significant intraday liquidity pool. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price accepts above the session high (e.g., multiple candles close and hold above it), indicating a true breakout rather than a sweep.
-   Reject if the reversal is weak or lacks a clear BOS/CHOCH confirmation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 12. Session Low Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Price moves below the current session's low (e.g., Asian session low, London session low) to collect liquidity and then reverses, indicating a potential short-term reversal within the trading session.

**Claude Analytical Focus:**
-   **Identify Session Low**: Clearly mark the low of the current trading session (e.g., Asian session, London session). This is a key intraday liquidity point.
-   **Detect Sweep**: Observe price aggressively pushing below the session low. The sweeping candle should ideally have a long wick below the session low, with the body closing back above it.
-   **Confirm Reversal**: Look for immediate rejection of the session low. This is often followed by a strong bullish candle and a Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe, confirming the bullish shift.
-   **Contextualize**: Consider the overall intraday bias and the proximity to higher timeframe support levels. A session low sweep that aligns with a daily or weekly support is a higher probability setup.

**Setup / Conditions:**
-   The current session low is clearly defined.
-   Price trades below the session low.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price sweeps the session low, and the candle closes back above the session low (or a significant portion of the wick is rejected).
-   A subsequent bullish candle confirms the reversal, ideally with a minor BOS or CHOCH in the opposite direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the confirming bullish candle closes, or on a retest of the swept session low/BOS level.
-   **Stop Loss**: Place the stop loss beyond the extreme of the sweep (e.g., beyond the wick of the sweeping candle), allowing for a small buffer.
-   **Targets**: Target the session high, VWAP, POC, or the next significant intraday liquidity pool. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price accepts below the session low (e.g., multiple candles close and hold below it), indicating a true breakout rather than a sweep.
-   Reject if the reversal is weak or lacks a clear BOS/CHOCH confirmation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 13. Trendline Liquidity Sweep

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Price breaks a visible retail trendline, often to trigger stop losses of trendline traders, and then reverses sharply in the opposite direction. This is a classic liquidity grab against retail positioning.

**Claude Analytical Focus:**
-   **Identify Retail Trendline**: Locate a clear trendline with at least three reliable touches, making it obvious to retail traders. This trendline represents a pool of liquidity (stop losses below/above for bullish/bearish trendlines).
-   **Detect False Break**: Observe price breaking beyond the trendline. This break should ideally be a quick, aggressive move that does not show strong acceptance beyond the trendline.
-   **Confirm Reversal**: Look for price to quickly close back inside the trendline, followed by a strong candle in the opposite direction and a Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe, confirming the reversal.
-   **Contextualize**: Consider the higher timeframe bias and the overall market structure. A trendline liquidity sweep that pushes price into a higher timeframe Order Block or FVG is a high-probability setup.

**Setup / Conditions:**
-   A visible trendline with at least three touches is established.
-   Price breaks outside the trendline.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price executes a false break outside the trendline, closes back inside, and then a minor BOS in the opposite direction occurs.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the re-entry into the trendline and the confirming BOS, or on a retest of the broken trendline from the inside.
-   **Stop Loss**: Place the stop loss beyond the extreme of the false break, allowing for a small buffer.
-   **Targets**: Target the opposite side of the trendline, VWAP, POC, or the next significant liquidity pool. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the trendline break shows strong acceptance (e.g., multiple candles close and hold beyond the trendline), indicating a true breakout.
-   Reject if the reversal is weak or lacks a clear BOS/CHOCH confirmation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 14. Stop Hunt Reversal

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** A rapid, aggressive price spike through a significant liquidity level (often an obvious swing high/low) designed to trigger stop losses, followed by an immediate and sharp reversal. This is a classic institutional maneuver to trap retail traders before moving price in the opposite direction.

**Claude Analytical Focus:**
-   **Identify Liquidity Target**: Locate a clear, obvious liquidity level (e.g., previous swing high/low, session extreme, round number) that price is approaching during an active trading session.
-   **Detect Stop Hunt**: Observe a fast, often volatile, price movement that pierces through this liquidity level. The key characteristic is a large wick extending beyond the level, with the candle body quickly retracting and closing back within the previous range or on the opposite side of the level.
-   **Confirm Reversal**: Look for immediate and strong rejection of the swept level. This is typically confirmed by the candle closing back, followed by a subsequent candle that continues the reversal, ideally accompanied by a Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe.
-   **Contextualize**: Assess the market environment. Is there a news event that could be driving the initial spike? Is the stop hunt occurring at a higher timeframe key level? Avoid confusing a stop hunt with genuine trend continuation.

**Setup / Conditions:**
-   Price approaches an obvious liquidity level (e.g., swing high/low) during an active trading session.
-   A sharp, aggressive price spike occurs, piercing the level.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A large wick pierces the liquidity level, and the candle closes back beyond the level (e.g., if a high is swept, the candle closes below the high). The next candle confirms the reversal.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the break of the confirmation candle or on a retest of the reclaimed level/BOS level.
-   **Stop Loss**: Place the stop loss beyond the extreme of the spike (e.g., beyond the tip of the sweeping wick), allowing for a small buffer.
-   **Targets**: Target 1R or 2R, VWAP, POC, or the nearest significant opposing liquidity level.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the spike is part of a strong news continuation move with significant follow-through, rather than an immediate reversal.
-   Reject if the price accepts beyond the swept level (e.g., multiple candles close and hold beyond it), indicating a true breakout.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 15. Displacement Continuation

**Category:** Institutional / SMC  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** A strong, impulsive price movement (displacement) indicates institutional participation and a clear directional bias. This signal seeks to enter on a shallow pullback after such a move, anticipating continuation in the original direction.

**Claude Analytical Focus:**
-   **Identify Displacement**: Look for a sequence of large-bodied candles moving decisively in one direction, breaking previous structure (BOS) and leaving behind inefficiencies like Fair Value Gaps (FVGs). This signifies strong institutional intent.
-   **Contextualize Pullback**: Observe price retracing after the displacement. The pullback should be shallow, ideally holding within a key Fibonacci retracement level (e.g., 38.2% to 61.8%), or retesting an Order Block (OB) or FVG created during the initial impulse.
-   **Confirm Continuation**: Look for signs of rejection at the pullback level, such as reversal candles, followed by a continuation Break of Structure (BOS) in the original direction of the displacement. The absence of a deep pullback or a market structure shift against the impulse is crucial.

**Setup / Conditions:**
-   A clear impulse candle sequence creates a Break of Structure (BOS) and significant displacement.
-   Price initiates a shallow pullback after the displacement.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The pullback holds a key retracement level (e.g., 38.2%-61.8% Fibonacci) or an Order Block/Fair Value Gap, and then a continuation BOS forms in the direction of the original impulse.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the rejection of the pullback level or on the break of the continuation BOS.
-   **Stop Loss**: Place the stop loss beyond the swing low/high of the pullback, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the initial impulse, the next significant liquidity pool, or aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the pullback becomes deep and causes a market structure flip against the original impulse, indicating a potential reversal rather than continuation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 16. Previous VAH Rejection

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** Price approaches the Previous Value Area High (VAH) and is rejected, with the VAH acting as strong resistance. This indicates that market participants are unwilling to accept prices above the previous day's high-volume trading range.

**Claude Analytical Focus:**
-   **Identify Previous VAH**: Clearly mark the Value Area High from the previous trading session. This level represents the upper boundary of where 70% of the previous day's volume traded.
-   **Contextualize Approach**: Observe how price approaches the VAH. Is it coming from below, or is it a retest after a failed attempt to break above? Consider the momentum and volume leading into the VAH.
-   **Confirm Rejection**: Look for clear signs of rejection at the VAH. This typically involves a wick extending above the VAH, with the candle body closing back below it. A subsequent bearish Break of Structure (BOS) on a lower timeframe further confirms the rejection.
-   **Market Narrative**: Is the market in a balanced state (range-bound) or trending? VAH rejections are often more reliable in balanced or range-bound conditions, or as a counter-trend scalp in a strong uptrend.

**Setup / Conditions:**
-   Price approaches the previous VAH from below or after a failed break above.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A wick forms above the VAH, and the candle closes back below it. This is followed by a bearish Break of Structure (BOS) on a lower timeframe.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter short below the low of the rejection candle or on a retest of the bearish BOS level.
-   **Stop Loss**: Place the stop loss above the high of the rejection wick, allowing for a small buffer.
-   **Targets**: Target the Point of Control (POC) first, then the Value Area Low (VAL) of the previous session. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price accepts above the VAH (e.g., two consecutive candles close and hold above it), indicating a successful breakout and potential continuation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 17. Previous VAL Rejection

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** Price approaches the Previous Value Area Low (VAL) and is rejected, with the VAL acting as strong support. This indicates that market participants are unwilling to accept prices below the previous day's low-volume trading range.

**Claude Analytical Focus:**
-   **Identify Previous VAL**: Clearly mark the Value Area Low from the previous trading session. This level represents the lower boundary of where 70% of the previous day's volume traded.
-   **Contextualize Approach**: Observe how price approaches the VAL. Is it coming from above, or is it a retest after a failed attempt to break below? Consider the momentum and volume leading into the VAL.
-   **Confirm Rejection**: Look for clear signs of rejection at the VAL. This typically involves a wick extending below the VAL, with the candle body closing back above it. A subsequent bullish Break of Structure (BOS) on a lower timeframe further confirms the rejection.
-   **Market Narrative**: Is the market in a balanced state (range-bound) or trending? VAL rejections are often more reliable in balanced or range-bound conditions, or as a counter-trend scalp in a strong downtrend.

**Setup / Conditions:**
-   Price approaches the previous VAL from above or after a failed break below.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A wick forms below the VAL, and the candle closes back above it. This is followed by a bullish Break of Structure (BOS) on a lower timeframe.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter long above the high of the rejection candle or on a retest of the bullish BOS level.
-   **Stop Loss**: Place the stop loss below the low of the rejection wick, allowing for a small buffer.
-   **Targets**: Target the Point of Control (POC) first, then the Value Area High (VAH) of the previous session. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price accepts below the VAL (e.g., two consecutive candles close and hold below it), indicating a successful breakdown and potential continuation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 18. VAH Flip Support

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** The Previous Value Area High (VAH), which previously acted as resistance, is broken and then retested, flipping its role to become support. This indicates a shift in market sentiment and acceptance of higher prices.

**Claude Analytical Focus:**
-   **Identify VAH Breakout**: Observe price closing decisively above the previous VAH, indicating a strong breakout from the prior value area.
-   **Contextualize Retest**: Look for price to return to the broken VAH. The retest should ideally be shallow and show signs of buyers stepping in at this new support level.
-   **Confirm Support**: Confirm that the retest of the VAH holds, meaning price rejects the level from above. A subsequent bullish Break of Structure (BOS) after the retest provides strong confirmation of the flip.
-   **Market Narrative**: This signal is indicative of a trending market or a shift from a balanced to an imbalanced state. Ensure the higher timeframe bias aligns with the bullish continuation.

**Setup / Conditions:**
-   Price closes and holds above the previous VAH.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The retest of the VAH holds, and a bullish Break of Structure (BOS) occurs after the retest.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter long on the rejection of the VAH retest or on a retest of the bullish BOS level.
-   **Stop Loss**: Place the stop loss below the VAH or the low of the retest candle, allowing for a small buffer.
-   **Targets**: Target the next significant resistance level, the session high, or the upper VWAP band. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price returns inside the previous value area and rotates towards the Point of Control (POC), indicating a failed breakout and a return to balance.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 19. VAL Flip Resistance

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** The Previous Value Area Low (VAL), which previously acted as support, is broken and then retested, flipping its role to become resistance. This indicates a shift in market sentiment and acceptance of lower prices.

**Claude Analytical Focus:**
-   **Identify VAL Breakdown**: Observe price closing decisively below the previous VAL, indicating a strong breakdown from the prior value area.
-   **Contextualize Retest**: Look for price to return to the broken VAL. The retest should ideally be shallow and show signs of sellers stepping in at this new resistance level.
-   **Confirm Resistance**: Confirm that the retest of the VAL fails, meaning price rejects the level from below. A subsequent bearish Break of Structure (BOS) after the retest provides strong confirmation of the flip.
-   **Market Narrative**: This signal is indicative of a trending market or a shift from a balanced to an imbalanced state. Ensure the higher timeframe bias aligns with the bearish continuation.

**Setup / Conditions:**
-   Price closes and holds below the previous VAL.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The retest of the VAL fails, and a bearish Break of Structure (BOS) occurs after the retest.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter short on the rejection of the VAL retest or on a retest of the bearish BOS level.
-   **Stop Loss**: Place the stop loss above the VAL or the high of the retest candle, allowing for a small buffer.
-   **Targets**: Target the next significant support level, the session low, or the lower VWAP band. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price returns inside the previous value area and rotates towards the Point of Control (POC), indicating a failed breakdown and a return to balance.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 20. Failed Auction Above VAH

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** Price breaks above the Previous Value Area High (VAH), suggesting a potential breakout, but fails to find acceptance at higher prices and quickly returns back inside the previous value area. This indicates a false breakout and a likely reversal.

**Claude Analytical Focus:**
-   **Identify VAH Breakout Attempt**: Observe price moving decisively above the VAH. This initial move might appear as a strong bullish candle.
-   **Detect Failure to Accept**: Look for signs that price is struggling to sustain itself above the VAH. This is crucial. It could be a quick rejection (long wick above VAH, closing back below) or a few candles attempting to hold above but failing to build new value.
-   **Confirm Return to Value**: The key confirmation is price closing back below the VAH, effectively re-entering the previous day's value area. A subsequent bearish Break of Structure (BOS) further reinforces the failed auction narrative.
-   **Market Narrative**: This signal often occurs when there's insufficient buying pressure to sustain a breakout, or when institutions are trapping early breakout buyers. It suggests a return to balance or a move towards the opposite extreme of the value area.

**Setup / Conditions:**
-   Price breaks above the previous VAH but cannot find acceptance (i.e., fails to build value above it).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes back below the VAH, followed by a bearish Break of Structure (BOS).
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter short after the close back inside the value area, or on a retest of the VAH from below (now acting as resistance).
-   **Stop Loss**: Place the stop loss above the high of the failed auction (the highest point reached during the false breakout), allowing for a small buffer.
-   **Targets**: Target the Point of Control (POC) first, then the Value Area Low (VAL) of the previous session. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price genuinely builds value above the VAH (e.g., multiple candles close and hold above it, forming a new trading range), indicating a successful breakout.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 21. Failed Auction Below VAL

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** Price breaks below the Previous Value Area Low (VAL), suggesting a potential breakdown, but fails to find acceptance at lower prices and quickly returns back inside the previous value area. This indicates a false breakdown and a likely reversal.

**Claude Analytical Focus:**
-   **Identify VAL Breakdown Attempt**: Observe price moving decisively below the VAL. This initial move might appear as a strong bearish candle.
-   **Detect Failure to Accept**: Look for signs that price is struggling to sustain itself below the VAL. This is crucial. It could be a quick rejection (long wick below VAL, closing back above) or a few candles attempting to hold below but failing to build new value.
-   **Confirm Return to Value**: The key confirmation is price closing back above the VAL, effectively re-entering the previous day's value area. A subsequent bullish Break of Structure (BOS) further reinforces the failed auction narrative.
-   **Market Narrative**: This signal often occurs when there's insufficient selling pressure to sustain a breakdown, or when institutions are trapping early breakout sellers. It suggests a return to balance or a move towards the opposite extreme of the value area.

**Setup / Conditions:**
-   Price breaks below the previous VAL but cannot find acceptance (i.e., fails to build value below it).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes back above the VAL, followed by a bullish Break of Structure (BOS).
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter long after the close back inside the value area, or on a retest of the VAL from above (now acting as support).
-   **Stop Loss**: Place the stop loss below the low of the failed auction (the lowest point reached during the false breakdown), allowing for a small buffer.
-   **Targets**: Target the Point of Control (POC) first, then the Value Area High (VAH) of the previous session. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price genuinely builds value below the VAL (e.g., multiple candles close and hold below it, forming a new trading range), indicating a successful breakdown.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 22. POC Magnet Rotation

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Good  
**Best Use:** Range day

**Description:** In a balanced market, price often rotates towards the Point of Control (POC), which represents the price level where the most volume has traded. This signal anticipates price movement towards the POC from the edges of the value area.

**Claude Analytical Focus:**
-   **Identify Balanced Market**: Determine if the market is in a balanced or range-bound state, typically characterized by price trading within a defined value area (between VAH and VAL) without strong directional momentum.
-   **Locate POC**: Identify the current session's or previous session's Point of Control. This acts as a gravitational center for price in a balanced environment.
-   **Detect Edge Rejection**: Look for price to approach and reject either the Value Area High (VAH) or Value Area Low (VAL), or other clear range edges. This rejection signals a likely rotation back towards the POC.
-   **Contextualize**: Confirm the absence of strong trend-following conditions. This signal is most effective when the market is consolidating or rotating within a defined range.

**Setup / Conditions:**
-   Price opens or is currently trading inside a previous value area, indicating a balanced market with no clear trend acceptance.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price is rejected from the VAH, VAL, or a clear value area edge, initiating a move towards the POC.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after a clear rejection from the value area edge, in the direction of the POC.
-   **Stop Loss**: Place the stop loss beyond the rejected edge of the value area, allowing for a small buffer.
-   **Targets**: Target the POC as the primary objective. An optional runner can be held for the opposite value area edge if the market remains balanced.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the market transitions into a strong trend day or shows clear acceptance outside the value area, as the POC magnet effect diminishes.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 23. Inside Value Rotation

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Good  
**Best Use:** Range day

**Description:** In a balanced market, price tends to rotate within the Value Area (between VAH and VAL). This signal focuses on trading from the extremes of the value area back towards the Point of Control (POC) or the opposite extreme.

**Claude Analytical Focus:**
-   **Identify Balanced Market**: Confirm that the market is in a balanced state, typically opening and remaining within the previous session's Value Area. Look for signs of consolidation and lack of strong directional conviction.
-   **Detect Extreme Rejection**: Observe price approaching either the Value Area High (VAH) or Value Area Low (VAL). Look for clear rejection at these boundaries, indicating that market participants are not yet willing to accept prices outside this range.
-   **Confirm Rotation**: A rejection from VAH suggests a rotation towards VAL or POC, and vice-versa. Confirm this by looking for reversal candle patterns and subsequent price action moving away from the rejected extreme.
-   **Contextualize**: This signal is highly effective in range-bound or balanced market conditions. Avoid using it during trending days or when there's clear acceptance outside the value area.

**Setup / Conditions:**
-   Price opens inside the previous value area and continues to remain balanced within it.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A clear rejection occurs from either the Value Area High (VAH) or Value Area Low (VAL).
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the rejection candle forms at the VAH (for a short) or VAL (for a long).
-   **Stop Loss**: Place the stop loss just outside the rejected value area extreme, allowing for a small buffer.
-   **Targets**: Target the Point of Control (POC) first, then the opposite value area extreme (VAH or VAL).
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price closes and accepts outside the value area, indicating a potential breakout and a shift from a balanced to a trending market.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 24. Outside Value Acceptance

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Trend day

**Description:** Price opens or breaks out of the previous session's Value Area (above VAH or below VAL) and demonstrates sustained acceptance outside that range. This indicates a strong directional auction and the potential for a trending day.

**Claude Analytical Focus:**
-   **Identify Breakout/Open Outside Value**: Observe if price either opens directly outside the previous VAH/VAL or breaks out decisively from within the value area. The initial move should be strong and purposeful.
-   **Confirm Acceptance**: The crucial element is *acceptance*. Look for multiple consecutive candle closes outside the previous value area, ideally followed by a retest of the broken VAH/VAL that holds as new support/resistance. This signifies that market participants are willing to trade at these new price levels.
-   **Market Narrative**: This signal is a strong indicator of a trending market. Claude should assess if the higher timeframe bias aligns with the direction of the breakout. Avoid confusing this with a failed auction or liquidity sweep.
-   **Volume Confirmation**: Ideally, the breakout and subsequent acceptance should be accompanied by increased volume, confirming conviction behind the move.

**Setup / Conditions:**
-   Price opens or breaks outside the previous VAH/VAL.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   At least two consecutive candle closes occur outside the previous value area, and a subsequent retest of the broken VAH/VAL holds as new support/resistance.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter in the direction of the acceptance after the retest of the broken VAH/VAL holds.
-   **Stop Loss**: Place the stop loss back inside the previous value area, typically just beyond the retested level.
-   **Targets**: Target the next higher timeframe level, Previous Day High/Low (PDH/PDL), or a measured move based on the previous range. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price quickly returns inside the previous value area after the breakout, indicating a failed auction or false breakout.
-   Reject if the retest fails to hold, and price breaks back through the VAH/VAL.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 25. Poor High / Poor Low Repair

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Medium  
**Best Use:** Intraday

**Description:** A "Poor High" or "Poor Low" in a Market Profile refers to an unfinished auction at an extreme, typically characterized by a lack of rotation or equal TPOs (Time Price Opportunities) at the high/low. These levels often act as magnets, as price tends to revisit them to complete the auction or "repair" the imbalance.

**Claude Analytical Focus:**
-   **Identify Poor High/Low**: Locate extremes in the Market Profile where the auction appears unfinished. This is often indicated by a flat top/bottom or a lack of significant volume/time spent at that extreme, resulting in equal TPOs.
-   **Contextualize Repair**: Observe price moving towards the identified Poor High/Low. This signal is most effective when the current market trend or structure aligns with a move towards the repair level. Avoid blindly trading into these levels without supporting evidence.
-   **Confirm Direction**: Look for price to attack and potentially move through the poor extreme. The goal is to trade in the direction of the repair, not necessarily to fade the repair itself.
-   **Volume Profile Confirmation**: Analyze the volume profile around the Poor High/Low. A lack of volume at the extreme reinforces the idea of an unfinished auction.

**Setup / Conditions:**
-   A prior Market Profile session exhibits a Poor High or Poor Low (e.g., equal TPOs at the extreme, lack of rotation).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price moves decisively towards and attacks the identified poor extreme, indicating an intent to repair the unfinished auction.
-   Prefer candle close confirmation over wick-only confirmation, especially for continuation towards the target.

**Execution:**
-   **Entry**: Enter only when the current trend or market acceptance supports a move towards the repair level. Avoid blind entries. Entry can be on a break of a minor structure or a retest of a level that clears the path to the Poor High/Low.
-   **Stop Loss**: Place the stop loss behind the most recent swing point that supports the move towards the repair level.
-   **Targets**: Target the Poor High/Low repair level itself. Once reached, reassess for further continuation or reversal.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if an opposing Key Level Zone (KLZ) or Value Area (VA) level blocks the path to the Poor High/Low, creating significant resistance or support.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 26. Single Prints Fill

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Medium  
**Best Use:** Intraday

**Description:** Single Prints are areas in a Market Profile where price has traded for only one TPO (Time Price Opportunity) at a specific price level, indicating a fast, one-sided auction and an imbalance. Price often revisits these areas to "fill" the imbalance and complete the auction.

**Claude Analytical Focus:**
-   **Identify Single Prints**: Locate areas in the previous session's Market Profile that exhibit single prints. These represent price levels where trading was very brief, suggesting an inefficiency.
-   **Contextualize Return**: Observe price returning towards the single print area. This signal is stronger when the market is in a balanced state or when the return aligns with the higher timeframe bias.
-   **Confirm Acceptance/Rejection**: Determine if price is accepting into the single print zone (suggesting a fill) or rejecting it (suggesting it will act as support/resistance). A clear acceptance into the zone is crucial for a fill trade.
-   **Market Narrative**: Single prints often act as magnets. Claude should consider if the current market narrative supports a move to fill these imbalances.

**Setup / Conditions:**
-   A previous session's Market Profile contains a clear single-print area.
-   Price returns towards this single-print zone.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price enters the single-print zone, and there is clear acceptance (e.g., multiple candles trading within the zone).
-   Alternatively, if fading the fill, look for rejection from the edge of the single-print zone after a full fill.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter in the direction of the fill after clear acceptance into the single-print zone. If fading, enter after a full fill and subsequent rejection from the zone.
-   **Stop Loss**: Place the stop loss outside the entry structure, typically beyond the far edge of the single-print zone if trading the fill, or beyond the rejection point if fading.
-   **Targets**: Target the midpoint or the full extent of the single-print fill, or the next significant value level.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if there is no clear acceptance into the single-print zone, or if price rejects the zone without filling it.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 27. LVN Rejection

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Medium  
**Best Use:** Intraday

**Description:** A Low Volume Node (LVN) represents a price level where very little trading activity occurred, indicating a lack of agreement or interest from market participants. When price approaches an LVN, it often rejects it due to this low acceptance, treating it as a weak area of support or resistance.

**Claude Analytical Focus:**
-   **Identify LVN**: Locate areas in the Volume Profile where there is a significant dip or void in volume. These are price levels that were quickly passed through.
-   **Contextualize Approach**: Observe price approaching the LVN from either above or below. Consider the momentum leading into the LVN. Strong momentum might break through, while weaker momentum is more likely to reject.
-   **Confirm Rejection**: Look for clear signs of rejection at the LVN, such as reversal candles, wicks extending into the LVN but closing away, and a subsequent shift in short-term market structure (e.g., a minor BOS or CHOCH).
-   **Market Narrative**: LVNs often act as areas of swift movement. A rejection suggests that the market is not yet ready to build value at that price level and will likely move towards a High Volume Node (HVN) or Point of Control (POC).

**Setup / Conditions:**
-   Price approaches a clearly identifiable Low Volume Node (LVN).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A rejection candle forms at the LVN, and the short-term market structure turns away from the LVN.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the rejection confirmation, in the direction away from the LVN.
-   **Stop Loss**: Place the stop loss just beyond the LVN, allowing for a small buffer.
-   **Targets**: Target the nearest High Volume Node (HVN) or Point of Control (POC), as these are areas of higher acceptance.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price closes and accepts through the LVN, indicating that the market is now willing to build value at that level.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 28. HVN Magnet

**Category:** Market Profile  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Medium  
**Best Use:** Range day

**Description:** A High Volume Node (HVN) represents a price level where significant trading activity occurred, indicating strong agreement or acceptance from market participants. In balanced or range-bound markets, HVNs often act as magnets, attracting price towards them.

**Claude Analytical Focus:**
-   **Identify HVN**: Locate areas in the Volume Profile where there is a prominent peak in volume. These are price levels where a large amount of trading took place, signifying fair value.
-   **Contextualize Market State**: Confirm that the market is in a balanced or range-bound state. HVNs are most effective as magnets when price is rotating within a defined range and not in a strong trend.
-   **Detect Directional Move**: Look for price to initiate a directional move towards a nearby HVN, often after rejecting a range extreme (e.g., VAH or VAL). The HVN itself is typically a target, not an entry point.
-   **Market Narrative**: HVNs represent areas of equilibrium. In a balanced market, price will often gravitate towards these areas of high acceptance.

**Setup / Conditions:**
-   Price is trading within a balanced range, and a High Volume Node (HVN) or Point of Control (POC) is nearby.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A directional move starts towards the HVN after a clear rejection from a range edge (e.g., VAH or VAL).
-   Prefer candle close confirmation over wick-only confirmation for the directional move.

**Execution:**
-   **Entry**: Enter from the range edge after a clear rejection, with the HVN as the target. Do not enter directly at the HVN.
-   **Stop Loss**: Place the stop loss beyond the rejected range edge, allowing for a small buffer.
-   **Targets**: Target the HVN or POC. Once reached, reassess for potential rotation or breakout.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject on strong trend days, as HVNs can become areas of chop or be easily broken through.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 29. VWAP Reclaim Long

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Price has been trading below the Volume Weighted Average Price (VWAP), indicating bearish sentiment, but then closes decisively above it, suggesting a shift in control to buyers. This signal looks for a long entry on a retest of the reclaimed VWAP.

**Claude Analytical Focus:**
-   **Identify Prior State**: Confirm that price was clearly trading below VWAP for a sustained period, establishing a bearish bias.
-   **Detect Reclaim**: Observe a strong candle closing above VWAP, indicating buyers stepping in and potentially regaining control. This close should be decisive, not just a wick.
-   **Confirm Retest and Hold**: Look for price to pull back to the reclaimed VWAP. The crucial confirmation is that VWAP holds as support, meaning price rejects the level from above. A subsequent bullish Break of Structure (BOS) after the retest reinforces the bullish narrative.
-   **Contextualize**: Consider the overall market structure and higher timeframe bias. A VWAP reclaim that aligns with a higher timeframe support or a bullish market structure shift is a higher probability setup. Avoid this signal if price is chopping around VWAP, indicating indecision.

**Setup / Conditions:**
-   Price was trading below VWAP and then closes above it.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The retest of VWAP holds as support, and a bullish Break of Structure (BOS) forms.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter long on the rejection of the VWAP retest or on a retest of the bullish BOS level.
-   **Stop Loss**: Place the stop loss below the low of the VWAP retest candle, allowing for a small buffer.
-   **Targets**: Target the upper VWAP band, previous Value Area High (VAH), Previous Day High (PDH), or aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price repeatedly chops across VWAP, indicating a lack of clear direction and increased risk.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 30. VWAP Rejection Short

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Price has been trading above the Volume Weighted Average Price (VWAP), indicating bullish sentiment, but then closes decisively below it, suggesting a shift in control to sellers. This signal looks for a short entry on a retest of the lost VWAP.

**Claude Analytical Focus:**
-   **Identify Prior State**: Confirm that price was clearly trading above VWAP for a sustained period, establishing a bullish bias.
-   **Detect Loss**: Observe a strong candle closing below VWAP, indicating sellers stepping in and potentially regaining control. This close should be decisive, not just a wick.
-   **Confirm Retest and Failure**: Look for price to pull back to the lost VWAP. The crucial confirmation is that VWAP fails to hold as support, meaning price rejects the level from below. A subsequent bearish Break of Structure (BOS) after the retest reinforces the bearish narrative.
-   **Contextualize**: Consider the overall market structure and higher timeframe bias. A VWAP rejection that aligns with a higher timeframe resistance or a bearish market structure shift is a higher probability setup. Avoid this signal if price is chopping around VWAP, indicating indecision.

**Setup / Conditions:**
-   Price was trading above VWAP and then closes below it.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The retest of VWAP fails to hold as support, and a bearish Break of Structure (BOS) forms.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter short on the rejection of the VWAP retest or on a retest of the bearish BOS level.
-   **Stop Loss**: Place the stop loss above the high of the VWAP retest candle, allowing for a small buffer.
-   **Targets**: Target the lower VWAP band, previous Value Area Low (VAL), Previous Day Low (PDL), or aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price repeatedly chops across VWAP, indicating a lack of clear direction and increased risk.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 31. VWAP Pullback Long

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** In a bullish trend where price is consistently trading above the Volume Weighted Average Price (VWAP), a shallow pullback to the VWAP often provides a low-risk, high-probability entry for continuation of the trend.

**Claude Analytical Focus:**
-   **Identify Bullish Trend**: Confirm that the overall trend is bullish, with price generally trading above VWAP and the VWAP itself showing an upward slope or remaining relatively flat but supportive. Look for bullish market structure (higher highs and higher lows).
-   **Detect Pullback**: Observe price pulling back towards the VWAP. The pullback should be corrective and shallow, not indicative of a trend reversal. Ideally, price should touch or come very close to the VWAP.
-   **Confirm Rejection**: The crucial confirmation is price rejecting the VWAP as support. Look for bullish reversal candles (e.g., pin bars, engulfing patterns) forming at or just above the VWAP, followed by a break of the rejection candle's high.
-   **Contextualize**: Ensure that the pullback is not too deep and that the overall market structure remains bullish. Avoid pullbacks that break significant short-term support levels or show strong bearish momentum.

**Setup / Conditions:**
-   The overall trend is bullish, with price consistently above VWAP, and VWAP slope is flat or upward.
-   Price pulls back to touch or near the VWAP.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The pullback touches or nears VWAP and shows clear rejection (e.g., bullish reversal candle).
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter long after the high of the rejection candle is broken, or on a retest of a minor Break of Structure (BOS) that forms after the rejection.
-   **Stop Loss**: Place the stop loss below the low of the pullback or just below the VWAP, allowing for a small buffer.
-   **Targets**: Target the recent high, the upper VWAP band, or the next significant resistance level. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the VWAP is flat and price is balanced or chopping within a value area, as this indicates a lack of clear trend.
-   Reject if the pullback is too deep, breaking bullish market structure, or if price closes and accepts below VWAP.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 32. VWAP Pullback Short

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** In a bearish trend where price is consistently trading below the Volume Weighted Average Price (VWAP), a shallow pullback to the VWAP often provides a low-risk, high-probability entry for continuation of the trend.

**Claude Analytical Focus:**
-   **Identify Bearish Trend**: Confirm that the overall trend is bearish, with price generally trading below VWAP and the VWAP itself showing a downward slope or remaining relatively flat but resistive. Look for bearish market structure (lower highs and lower lows).
-   **Detect Pullback**: Observe price pulling back towards the VWAP. The pullback should be corrective and shallow, not indicative of a trend reversal. Ideally, price should touch or come very close to the VWAP.
-   **Confirm Rejection**: The crucial confirmation is price rejecting the VWAP as resistance. Look for bearish reversal candles (e.g., pin bars, engulfing patterns) forming at or just below the VWAP, followed by a break of the rejection candle's low.
-   **Contextualize**: Ensure that the pullback is not too deep and that the overall market structure remains bearish. Avoid pullbacks that break significant short-term resistance levels or show strong bullish momentum.

**Setup / Conditions:**
-   The overall trend is bearish, with price consistently below VWAP, and VWAP slope is flat or downward.
-   Price pulls back to touch or near the VWAP.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The pullback touches or nears VWAP and shows clear rejection (e.g., bearish reversal candle).
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter short after the low of the rejection candle is broken, or on a retest of a minor Break of Structure (BOS) that forms after the rejection.
-   **Stop Loss**: Place the stop loss above the high of the pullback or just above the VWAP, allowing for a small buffer.
-   **Targets**: Target the recent low, the lower VWAP band, or the next significant support level. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the VWAP is flat and price is balanced or chopping within a value area, as this indicates a lack of clear trend.
-   Reject if the pullback is too deep, breaking bearish market structure, or if price closes and accepts above VWAP.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 33. VWAP Extreme Band Rejection

**Category:** VWAP  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Good  
**Best Use:** Scalping

**Description:** Price extends to an extreme VWAP band (typically Band 2 or 3) and is rejected, indicating overextension and a potential mean reversion back towards the VWAP or inner bands.

**Claude Analytical Focus:**
-   **Identify Extreme Band Touch**: Observe price reaching and touching an outer VWAP band (e.g., Band 2 or 3). This signifies that price is significantly extended from its volume-weighted average.
-   **Contextualize Rejection**: Look for clear signs of rejection at the extreme band. This often involves a long wick extending beyond the band, with the candle body closing back inside or away from the band. Do not blindly enter on the first touch; wait for confirmation.
-   **Confirm Structure Shift**: A crucial confirmation is a Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe, indicating a shift in momentum back towards the VWAP. This confirms that the rejection is not just a temporary pause.
-   **Market Narrative**: This signal is most effective in range-bound or mean-reverting market conditions. In strong trending markets, price can "band-walk" along the extreme bands, making this signal less reliable for reversals.

**Setup / Conditions:**
-   Price extends to and touches an upper or lower extreme VWAP band (e.g., Band 2 or 3).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A clear rejection wick forms at the extreme band, followed by a Change of Character (CHOCH) or Break of Structure (BOS) back towards the VWAP.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the structure shift (CHOCH/BOS) confirms the rejection. Avoid entering blindly on the first touch of the band.
-   **Stop Loss**: Place the stop loss beyond the extreme of the rejection (e.g., beyond the wick that touched the band), allowing for a small buffer.
-   **Targets**: Target the inner VWAP band (e.g., Band 1) first, then the VWAP itself. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price starts to "band-walk" along the extreme band, indicating a strong trend continuation rather than a reversal.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 34. VWAP Band Walk Continuation

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Trend day

**Description:** In a strong trending market, price often "band-walks" along one of the VWAP bands (typically the upper band in an uptrend or lower band in a downtrend), indicating sustained institutional participation and momentum. This signal focuses on entering on shallow pullbacks within this band-walk for continuation.

**Claude Analytical Focus:**
-   **Identify Strong Trend**: Confirm that a strong trend is in progress, characterized by price consistently holding above VWAP (uptrend) or below VWAP (downtrend), and the VWAP itself showing a clear slope in the direction of the trend.
-   **Detect Band Walk**: Observe price hugging or repeatedly touching one of the outer VWAP bands (e.g., upper Band 1 or Band 2 in an uptrend, lower Band 1 or Band 2 in a downtrend). This indicates strong directional control.
-   **Contextualize Pullbacks**: Look for shallow pullbacks towards the VWAP or the inner band (Band 1). These pullbacks should be brief and quickly rejected, confirming the continuation of the trend.
-   **Avoid Fading**: It is crucial to avoid attempting to fade (trade against) the band-walk, as this is a sign of strong institutional flow. Instead, look for opportunities to join the trend on pullbacks.

**Setup / Conditions:**
-   Price consistently holds above VWAP and near an upper band (for long) or below VWAP and near a lower band (for short).
-   The VWAP itself should be sloping in the direction of the trend.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Shallow pullbacks to the VWAP or the inner band (Band 1) are quickly rejected, and price continues in the direction of the trend.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the rejection of a shallow pullback to the VWAP or inner band, in the direction of the trend. Avoid chasing extended candles.
-   **Stop Loss**: Place the stop loss behind the low/high of the pullback swing, allowing for a small buffer.
-   **Targets**: Target the next significant liquidity level, or use a trailing stop based on market structure or VWAP bands to capture extended moves.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject reversal signals while the band-walk persists, as the strong trend is likely to continue.
-   Reject if price breaks and accepts beyond the VWAP or the inner band, indicating a potential weakening of the trend or a shift in market dynamics.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 35. VWAP Chop/Indecision

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Filter

**Description:** Price repeatedly crosses above and below the Volume Weighted Average Price (VWAP) within a short period, indicating a lack of clear directional conviction and a high-chop, indecisive market environment. This signal serves as a filter to avoid trading during unfavorable conditions.

**Claude Analytical Focus:**
-   **Identify Repeated Crosses**: Observe price action in relation to VWAP. If price is frequently crossing above and below VWAP, and candles are often closing near VWAP, it indicates a lack of clear trend.
-   **Contextualize Market State**: Recognize that this pattern signifies a balanced or indecisive market, often characterized by low volatility or consolidation. Trend-following strategies are likely to fail in such conditions.
-   **Avoid Trading**: The primary analytical focus for Claude here is to identify these conditions and refrain from initiating new trend-based trades. It's a signal to step aside and wait for clearer market direction.
-   **Look for Acceptance**: Claude should monitor for price to eventually break away from VWAP and sustain acceptance above or below it, which would then invalidate the chop condition and potentially signal a new trend.

**Setup / Conditions:**
-   Price crosses VWAP multiple times within a short timeframe (e.g., 5-10 candles).
-   Candle bodies are often small, and wicks may be present on both sides, indicating indecision.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   There is no trade trigger for this signal. The confirmation is the observation of repeated VWAP crosses and a lack of sustained price action away from VWAP.
-   The action is to wait for clear acceptance above or below VWAP before considering directional trades.

**Execution:**
-   **Entry**: Execution is WAIT only. No trades should be initiated based on this signal.
-   **Stop Loss**: Not applicable, as no trade is taken.
-   **Targets**: Not applicable, as no trade is taken.
-   **Minimum Risk/Reward**: Not applicable, as no trade is taken.

**Invalidation / Reject:**
-   Do not approve trend-following strategies during periods of VWAP chop.
-   Reject any trade setups that rely on clear directional movement when this signal is active.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 36. Anchored VWAP (AVWAP) Rejection/Support

**Category:** VWAP  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday/Swing

**Description:** Anchored VWAP (AVWAP) calculates the Volume Weighted Average Price from a specific, significant anchor point (e.g., a major swing high/low, weekly open, news event). It represents the average price paid by participants since that anchor, acting as a dynamic support or resistance level that reflects institutional average cost.

**Claude Analytical Focus:**
-   **Identify Anchor Point**: Claude should be instructed to identify and anchor VWAP from significant market events or structural points. Examples include: major swing highs/lows, weekly/daily opens, session opens (London/New York), or the candle preceding a high-impact news release. The choice of anchor is critical.
-   **Contextualize AVWAP**: Understand that AVWAP acts as a dynamic average cost for participants since the anchor. Price trading above AVWAP suggests buyers are in control, while below suggests sellers are dominant.
-   **Detect Retest and Rejection/Support**: Look for price to retest the AVWAP. The key is to observe a clear rejection (for resistance) or support (for support) at this level. This is often characterized by reversal candle patterns, wicks, and a subsequent continuation in the direction of the prevailing trend from the AVWAP.
-   **Confirm with Structure**: A retest and rejection/support of AVWAP is significantly strengthened when it aligns with other market structure elements (e.g., Order Blocks, FVGs, previous highs/lows) or a Break of Structure (BOS) on a lower timeframe.

**Setup / Conditions:**
-   AVWAP is anchored from a significant swing high/low, weekly/daily open, session open, or a major news impulse.
-   Price approaches the AVWAP for a retest.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price retests the AVWAP and shows clear rejection (for resistance) or support (for support) in the direction of the prevailing trend.
-   A subsequent Break of Structure (BOS) or Change of Character (CHOCH) confirms the continuation from the AVWAP.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the rejection/support is confirmed by a candle close and a subsequent BOS/CHOCH, or on a retest of the BOS level.
-   **Stop Loss**: Place the stop loss beyond the swing high/low of the AVWAP retest, allowing for a small buffer.
-   **Targets**: Target the next significant structure level, liquidity pool, or a measured move. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the AVWAP has been crossed repeatedly and price is chopping around it, indicating a loss of its significance.
-   Reject if price closes and accepts decisively beyond the AVWAP, indicating a potential shift in the underlying average cost and trend.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 37. Weekly VWAP Confluence

**Category:** VWAP  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Swing

**Description:** The Weekly Volume Weighted Average Price (VWAP) represents the average price traded for the entire week, weighted by volume. When the Weekly VWAP aligns with other significant trade levels (e.g., Key Level Zones, Value Areas, Previous Day High/Low), it acts as a powerful confluence, strengthening the probability of a primary signal.

**Claude Analytical Focus:**
-   **Calculate Weekly VWAP**: Claude should be instructed to calculate and display the Weekly VWAP. This line represents the average price paid by participants over the current trading week.
-   **Identify Confluence**: Look for instances where the Weekly VWAP is in close proximity to other important support or resistance levels, such as:
    -   Key Level Zones (KLZ)
    -   Value Area High (VAH) or Value Area Low (VAL) from previous sessions
    -   Previous Day High (PDH) or Previous Day Low (PDL)
    -   Order Blocks or Fair Value Gaps
-   **Strengthen Primary Signal**: This signal is not a standalone entry but a powerful confirmation. When a primary trading signal (e.g., an Order Block mitigation, a liquidity sweep) occurs at or near the Weekly VWAP, it significantly increases the probability of that primary signal succeeding. Claude should prioritize setups where the Weekly VWAP supports the intended direction of the trade.
-   **Contextualize Trend**: If the Weekly VWAP is sloping upwards, it indicates a bullish weekly bias, and long setups aligning with it are strengthened. Conversely, a downward sloping Weekly VWAP strengthens short setups.

**Setup / Conditions:**
-   A primary trading signal (e.g., Order Block, FVG, Liquidity Sweep) occurs near the Weekly VWAP.
-   The Weekly VWAP supports the direction of the primary signal (e.g., price bouncing off Weekly VWAP as support for a long trade).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The primary signal triggers, and the Weekly VWAP provides additional confluence by acting as support or resistance in the direction of the trade.
-   Prefer candle close confirmation over wick-only confirmation for the primary signal.

**Execution:**
-   **Entry**: Use the entry criteria of the primary signal. The Weekly VWAP acts as a filter and confluence, not a standalone entry trigger.
-   **Stop Loss**: Use the stop loss criteria of the primary setup. Ensure the stop loss is placed logically beyond the Weekly VWAP if it is intended to hold as support/resistance.
-   **Targets**: Use the target criteria of the primary setup. The Weekly VWAP can sometimes act as an intermediate target or a level to manage risk.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the Weekly VWAP directly opposes the direction of the primary signal (e.g., a bullish primary signal occurring at a Weekly VWAP acting as resistance).
-   Reject if price closes and accepts decisively beyond the Weekly VWAP, indicating a potential shift in the weekly bias.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 38. VWAP-Market Profile Confluence

**Category:** VWAP / Market Profile  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** This signal identifies high-probability trade setups where the Volume Weighted Average Price (VWAP) or one of its standard deviation bands aligns closely with a significant Market Profile level, such as the Value Area High (VAH) or Value Area Low (VAL). This confluence creates a stronger area of support or resistance.

**Claude Analytical Focus:**
-   **Identify Confluent Levels**: Claude should actively scan for instances where the VWAP or its upper/lower bands are in close proximity to the previous session's VAH or VAL. The closer the alignment, the stronger the potential confluence.
-   **Contextualize Price Action**: Observe how price reacts upon reaching this confluent zone. Look for clear signs of rejection (e.g., long wicks, reversal candle patterns) if the zone is expected to act as resistance, or strong support (e.g., bullish engulfing, hammer patterns) if it's expected to act as support.
-   **Confirm Flip or Rejection**: If price has already broken through one of these levels (e.g., VAH) and is retesting it, look for the level to flip its role (e.g., VAH turning into support). If price is approaching the zone for the first time, look for a clear rejection. A subsequent Break of Structure (BOS) or Change of Character (CHOCH) on a lower timeframe can confirm the validity of the confluence.
-   **Market Narrative**: This signal is particularly powerful because it combines volume-weighted average price (institutional average cost) with areas of high trading activity (Market Profile). Claude should interpret this as a strong indication of where institutional players might defend or initiate positions.

**Setup / Conditions:**
-   Price approaches a zone where the VWAP or one of its bands aligns closely with a Market Profile VAH or VAL.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A clear rejection or a successful flip (e.g., VAH turning into support, VAL turning into resistance) occurs at the confluent zone.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter based on the trigger of the VAH/VAL setup (e.g., after a rejection candle closes, or after a BOS confirms the flip). The VWAP confluence serves to increase the probability of the trade.
-   **Stop Loss**: Place the stop loss logically beyond both the Market Profile level and the VWAP/band, allowing for a small buffer to account for volatility.
-   **Targets**: Target the Point of Control (POC), the opposite Value Area extreme (VAH/VAL), or the VWAP itself if trading from an extreme band. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price closes and accepts decisively through both confluent levels, indicating that the combined support/resistance has failed.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 39. Double Top Bearish Reversal

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday/Swing

**Description:** A bearish reversal pattern characterized by two consecutive peaks (tops) at approximately the same price level, separated by a moderate trough. It indicates that buying pressure is failing at a resistance level, suggesting a potential downtrend.

**Claude Analytical Focus:**
-   **Identify Two Peaks**: Locate two distinct swing highs that reach approximately the same price level. The second peak should ideally not significantly exceed the first, indicating a failure to break higher.
-   **Identify Neckline**: Determine the neckline by drawing a horizontal line across the lowest point of the trough between the two peaks. This neckline represents a critical support level.
-   **Confirm Rejection at Second Peak**: Observe price action at the second peak. Look for bearish reversal candles (e.g., pin bars, engulfing patterns) and a lack of momentum to push above the first peak.
-   **Confirm Neckline Break**: The pattern is confirmed when price breaks decisively below the neckline. This break should ideally be accompanied by increased bearish momentum and volume.
-   **Contextualize**: Consider the higher timeframe trend. A Double Top forming at a significant higher timeframe resistance level or after an extended uptrend is a higher probability setup. Ensure the pattern is clear and not part of choppy price action.

**Setup / Conditions:**
-   Two swing highs form at approximately the same price level, with a clear pullback (trough) between them.
-   The pattern forms near a meaningful resistance level or is aligned with bearish market structure.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively below the neckline after the formation of the second top.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter short on the decisive break of the neckline, or on a retest of the broken neckline from below (which now acts as resistance).
-   **Stop Loss**: Place the stop loss above the second top, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the height of the pattern (from the peaks to the neckline), projected downwards from the neckline break. Alternatively, target the next significant support level.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the second top strongly closes above the first top, indicating a continuation of the uptrend rather than a reversal.
-   Reject if price fails to break the neckline, or if it breaks the neckline but quickly reclaims it.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 40. Double Bottom Bullish Reversal

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday/Swing

**Description:** A bullish reversal pattern characterized by two consecutive troughs (bottoms) at approximately the same price level, separated by a moderate peak. It indicates that selling pressure is failing at a support level, suggesting a potential uptrend.

**Claude Analytical Focus:**
-   **Identify Two Troughs**: Locate two distinct swing lows that reach approximately the same price level. The second trough should ideally not significantly exceed the first, indicating a failure to break lower.
-   **Identify Neckline**: Determine the neckline by drawing a horizontal line across the highest point of the peak between the two troughs. This neckline represents a critical resistance level.
-   **Confirm Rejection at Second Trough**: Observe price action at the second trough. Look for bullish reversal candles (e.g., hammer, bullish engulfing patterns) and a lack of momentum to push below the first trough.
-   **Confirm Neckline Break**: The pattern is confirmed when price breaks decisively above the neckline. This break should ideally be accompanied by increased bullish momentum and volume.
-   **Contextualize**: Consider the higher timeframe trend. A Double Bottom forming at a significant higher timeframe support level or after an extended downtrend is a higher probability setup. Ensure the pattern is clear and not part of choppy price action.

**Setup / Conditions:**
-   Two swing lows form at approximately the same price level, with a clear bounce (peak) between them.
-   The pattern forms near a meaningful support level or is aligned with bullish market structure.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively above the neckline after the formation of the second bottom.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter long on the decisive break of the neckline, or on a retest of the broken neckline from above (which now acts as support).
-   **Stop Loss**: Place the stop loss below the second bottom, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the height of the pattern (from the troughs to the neckline), projected upwards from the neckline break. Alternatively, target the next significant resistance level.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the second bottom strongly closes below the first bottom, indicating a continuation of the downtrend rather than a reversal.
-   Reject if price fails to break the neckline, or if it breaks the neckline but quickly reclaims it.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 41. Triple Top Bearish Reversal

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Good  
**Best Use:** Swing

**Description:** A bearish reversal pattern characterized by three consecutive peaks (tops) at approximately the same price level, separated by two moderate troughs. It signifies a strong resistance level that buyers have failed to overcome on multiple attempts, indicating exhaustion of buying pressure and a high probability of a downtrend.

**Claude Analytical Focus:**
-   **Identify Three Peaks**: Locate three distinct swing highs that reach approximately the same price level. Each peak should show signs of rejection (e.g., wicks, bearish candles), and the third peak should ideally not significantly exceed the previous two, confirming the inability to break higher.
-   **Identify Neckline**: Determine the neckline by drawing a horizontal line across the lowest points of the two troughs between the peaks. This neckline represents a critical support level.
-   **Confirm Rejection at Third Peak**: Observe price action at the third peak. Look for strong bearish reversal candles (e.g., bearish engulfing, shooting star) and a clear lack of momentum to push above the resistance zone. This is the final confirmation of buyer exhaustion.
-   **Confirm Neckline Break**: The pattern is confirmed when price breaks decisively below the neckline. This break should ideally be accompanied by increased bearish momentum and volume, indicating sellers taking control.
-   **Contextualize**: Consider the higher timeframe trend. A Triple Top forming at a significant higher timeframe resistance level, a supply zone, or after an extended uptrend is a higher probability setup. Look for divergence on momentum indicators (e.g., RSI, MACD) between the peaks as an additional confirmation.

**Setup / Conditions:**
-   Three swing highs form at approximately the same price level, with two clear pullbacks (troughs) between them.
-   The pattern forms near a meaningful resistance level or is aligned with bearish market structure.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively below the neckline after the formation of the third top.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter short on the decisive break of the neckline, or on a retest of the broken neckline from below (which now acts as resistance).
-   **Stop Loss**: Place the stop loss above the third top, allowing for a small buffer to account for volatility.
-   **Targets**: Target a measured move equal to the height of the pattern (from the peaks to the neckline), projected downwards from the neckline break. Alternatively, target the next significant support level or demand zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the third top strongly closes above the previous two tops, indicating a continuation of the uptrend rather than a reversal.
-   Reject if price fails to break the neckline, or if it breaks the neckline but quickly reclaims it, suggesting a false breakdown.
-   Reject if the "tests" of resistance become ascending, forming an ascending triangle, which is typically a continuation pattern.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 42. Triple Bottom Bullish Reversal

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Good  
**Best Use:** Swing

**Description:** A bullish reversal pattern characterized by three consecutive troughs (bottoms) at approximately the same price level, separated by two moderate peaks. It signifies a strong support level that sellers have failed to overcome on multiple attempts, indicating exhaustion of selling pressure and a high probability of an uptrend.

**Claude Analytical Focus:**
-   **Identify Three Troughs**: Locate three distinct swing lows that reach approximately the same price level. Each trough should show signs of support (e.g., wicks, bullish candles), and the third trough should ideally not significantly exceed the previous two, confirming the inability to break lower.
-   **Identify Neckline**: Determine the neckline by drawing a horizontal line across the highest points of the two peaks between the troughs. This neckline represents a critical resistance level.
-   **Confirm Rejection at Third Trough**: Observe price action at the third trough. Look for strong bullish reversal candles (e.g., bullish engulfing, hammer) and a clear lack of momentum to push below the support zone. This is the final confirmation of seller exhaustion.
-   **Confirm Neckline Break**: The pattern is confirmed when price breaks decisively above the neckline. This break should ideally be accompanied by increased bullish momentum and volume, indicating buyers taking control.
-   **Contextualize**: Consider the higher timeframe trend. A Triple Bottom forming at a significant higher timeframe support level, a demand zone, or after an extended downtrend is a higher probability setup. Look for divergence on momentum indicators (e.g., RSI, MACD) between the troughs as an additional confirmation.

**Setup / Conditions:**
-   Three swing lows form at approximately the same price level, with two clear bounces (peaks) between them.
-   The pattern forms near a meaningful support level or is aligned with bullish market structure.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively above the neckline after the formation of the third bottom.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter long on the decisive break of the neckline, or on a retest of the broken neckline from above (which now acts as support).
-   **Stop Loss**: Place the stop loss below the third bottom, allowing for a small buffer to account for volatility.
-   **Targets**: Target a measured move equal to the height of the pattern (from the troughs to the neckline), projected upwards from the neckline break. Alternatively, target the next significant resistance level or supply zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the third bottom strongly closes below the previous two bottoms, indicating a continuation of the downtrend rather than a reversal.
-   Reject if price fails to break the neckline, or if it breaks the neckline but quickly reclaims it, suggesting a false breakdown.
-   Reject if the "tests" of support become descending, forming a descending triangle, which is typically a continuation pattern.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 43. Head and Shoulders Bearish Reversal

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday/Swing

**Description:** A classic bearish reversal pattern that forms after an uptrend, indicating a shift from bullish to bearish sentiment. It consists of three peaks: a central, highest peak (the "head"), flanked by two lower peaks (the "shoulders"). The pattern is confirmed by a break below the neckline, which connects the lows between the peaks.

**Claude Analytical Focus:**
-   **Identify Uptrend Context**: Confirm that the pattern is forming after a clear, established uptrend. This pattern is a reversal pattern, so its significance is diminished if it forms in a choppy or range-bound market.
-   **Identify Left Shoulder**: Observe the formation of the first peak, followed by a pullback to form the first trough (part of the neckline).
-   **Identify Head**: Look for a higher peak than the left shoulder, followed by a pullback to form the second trough (completing the neckline).
-   **Identify Right Shoulder**: Observe the formation of a third peak that is lower than the head but ideally similar in height to the left shoulder. This indicates a failure of buyers to push price to new highs.
-   **Identify Neckline**: Draw a line connecting the two troughs formed between the shoulders and the head. This is the critical neckline.
-   **Confirm Neckline Break**: The pattern is confirmed when price closes decisively below the neckline. This break should ideally be accompanied by increased bearish momentum and volume.
-   **Contextualize**: Look for divergence on momentum indicators (e.g., RSI, MACD) between the head and the right shoulder, which can provide additional confirmation of weakening bullish momentum.

**Setup / Conditions:**
-   The pattern forms after an established bullish move, near a significant resistance level.
-   Consists of a left shoulder, a higher head, and a lower right shoulder.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively below the neckline. A retest of the broken neckline that fails to push price back above it provides strong confirmation.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter short on the decisive break of the neckline, or on a retest of the broken neckline from below (which now acts as resistance). If momentum is very strong, an entry on the break might be appropriate.
-   **Stop Loss**: Place the stop loss above the high of the right shoulder, or conservatively above the head, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the vertical distance from the head to the neckline, projected downwards from the neckline break. Alternatively, target the next significant support level or demand zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the pattern forms in a strong uptrend and the neckline is not decisively broken.
-   Reject if price closes and accepts above the right shoulder, indicating a continuation of the uptrend.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 44. Inverse Head and Shoulders Bullish Reversal

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday/Swing

**Description:** A classic bullish reversal pattern that forms after a downtrend, indicating a shift from bearish to bullish sentiment. It consists of three troughs: a central, lowest trough (the "head"), flanked by two higher troughs (the "shoulders"). The pattern is confirmed by a break above the neckline, which connects the highs between the troughs.

**Claude Analytical Focus:**
-   **Identify Downtrend Context**: Confirm that the pattern is forming after a clear, established downtrend. This pattern is a reversal pattern, so its significance is diminished if it forms in a choppy or range-bound market.
-   **Identify Left Shoulder**: Observe the formation of the first trough, followed by a bounce to form the first peak (part of the neckline).
-   **Identify Head**: Look for a lower trough than the left shoulder, followed by a bounce to form the second peak (completing the neckline).
-   **Identify Right Shoulder**: Observe the formation of a third trough that is higher than the head but ideally similar in depth to the left shoulder. This indicates a failure of sellers to push price to new lows.
-   **Identify Neckline**: Draw a line connecting the two peaks formed between the shoulders and the head. This is the critical neckline.
-   **Confirm Neckline Break**: The pattern is confirmed when price closes decisively above the neckline. This break should ideally be accompanied by increased bullish momentum and volume.
-   **Contextualize**: Look for bullish divergence on momentum indicators (e.g., RSI, MACD) between the head and the right shoulder, which can provide additional confirmation of weakening bearish momentum.

**Setup / Conditions:**
-   The pattern forms after an established bearish move, near a significant support level.
-   Consists of a left shoulder, a lower head, and a higher right shoulder.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively above the neckline. A retest of the broken neckline that holds as support provides strong confirmation.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter long on the decisive break of the neckline, or on a retest of the broken neckline from above (which now acts as support). If momentum is very strong, an entry on the break might be appropriate.
-   **Stop Loss**: Place the stop loss below the low of the right shoulder, or conservatively below the head, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the vertical distance from the head to the neckline, projected upwards from the neckline break. Alternatively, target the next significant resistance level or supply zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the pattern forms in a strong downtrend and the neckline is not decisively broken.
-   Reject if price closes and accepts below the right shoulder, indicating a continuation of the downtrend.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 45. Bull Flag Continuation

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping/Intraday

**Description:** A bullish continuation pattern that forms after a strong upward price impulse (the "pole"), followed by a shallow, downward-sloping or sideways consolidation channel (the "flag"). It indicates a temporary pause in buying pressure before the uptrend resumes.

**Claude Analytical Focus:**
-   **Identify Bullish Pole**: Look for a strong, aggressive upward move, characterized by large bullish candles and significant displacement. This "pole" should ideally be above the VWAP or follow a clear bullish Break of Structure (BOS).
-   **Identify Flag Consolidation**: Observe a subsequent period of consolidation where price moves in a shallow, downward-sloping channel or a tight sideways range. The key is that this consolidation should be corrective, not impulsive, and should not retrace more than 50-61.8% of the pole.
-   **Confirm Flag Structure**: The flag should consist of at least two touches on the upper trendline and two touches on the lower trendline, forming a clear channel. Volume should typically decrease during the flag formation, indicating a pause in momentum.
-   **Confirm Breakout**: The pattern is confirmed when price breaks decisively above the upper trendline of the flag. This breakout should ideally be accompanied by an increase in volume and strong bullish candles.
-   **Contextualize**: Ensure the overall higher timeframe bias is bullish. Bull flags are high-probability continuation patterns in established uptrends. Avoid flags that are too deep or show signs of bearish market structure shifts within the consolidation.

**Setup / Conditions:**
-   A strong bullish impulse (pole) occurs, ideally above VWAP or after a bullish BOS.
-   A subsequent shallow, downward-sloping or sideways consolidation channel (flag) forms.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively above the upper trendline of the flag.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the decisive breakout candle close above the flag resistance, or on a retest of the broken trendline (which now acts as support). For smaller flags, an entry on the close might be acceptable.
-   **Stop Loss**: Place the stop loss below the low of the flag consolidation, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the length of the pole, projected upwards from the breakout point. Alternatively, target the next significant liquidity level or resistance zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the pullback (flag) retraces more than 61.8% of the pole, or if it breaks significant market structure within the consolidation, indicating a potential reversal rather than continuation.
-   Reject if price breaks below the lower trendline of the flag and accepts below it.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 46. Bear Flag Continuation

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping/Intraday

**Description:** A bearish continuation pattern that forms after a strong downward price impulse (the "pole"), followed by a shallow, upward-sloping or sideways consolidation channel (the "flag"). It indicates a temporary pause in selling pressure before the downtrend resumes.

**Claude Analytical Focus:**
-   **Identify Bearish Pole**: Look for a strong, aggressive downward move, characterized by large bearish candles and significant displacement. This "pole" should ideally be below the VWAP or follow a clear bearish Break of Structure (BOS).
-   **Identify Flag Consolidation**: Observe a subsequent period of consolidation where price moves in a shallow, upward-sloping channel or a tight sideways range. The key is that this consolidation should be corrective, not impulsive, and should not retrace more than 50-61.8% of the pole.
-   **Confirm Flag Structure**: The flag should consist of at least two touches on the upper trendline and two touches on the lower trendline, forming a clear channel. Volume should typically decrease during the flag formation, indicating a pause in momentum.
-   **Confirm Breakout**: The pattern is confirmed when price breaks decisively below the lower trendline of the flag. This breakout should ideally be accompanied by an increase in volume and strong bearish candles.
-   **Contextualize**: Ensure the overall higher timeframe bias is bearish. Bear flags are high-probability continuation patterns in established downtrends. Avoid flags that are too deep or show signs of bullish market structure shifts within the consolidation.

**Setup / Conditions:**
-   A strong bearish impulse (pole) occurs, ideally below VWAP or after a bearish BOS.
-   A subsequent shallow, upward-sloping or sideways consolidation channel (flag) forms.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively below the lower trendline of the flag.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the decisive breakout candle close below the flag support, or on a retest of the broken trendline (which now acts as resistance). For smaller flags, an entry on the close might be acceptable.
-   **Stop Loss**: Place the stop loss above the high of the flag consolidation, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the length of the pole, projected downwards from the breakout point. Alternatively, target the next significant liquidity level or support zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the pullback (flag) retraces more than 61.8% of the pole, or if it breaks significant market structure within the consolidation, indicating a potential reversal rather than continuation.
-   Reject if price breaks above the upper trendline of the flag and accepts above it.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 47. Bull Pennant Continuation

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** A bullish continuation pattern that forms after a strong upward price impulse (the "pole"), followed by a symmetrical, contracting triangle (the "pennant"). It signifies a brief period of consolidation and indecision before the uptrend resumes.

**Claude Analytical Focus:**
-   **Identify Bullish Pole**: Look for a strong, aggressive upward move, characterized by large bullish candles and significant displacement. This "pole" should indicate clear buying pressure.
-   **Identify Pennant Consolidation**: Observe a subsequent period of consolidation where price forms a symmetrical triangle, characterized by converging trendlines (lower highs and higher lows). This consolidation should be relatively short-lived and represent a temporary pause in the trend.
-   **Confirm Pennant Structure**: The pennant should ideally be small relative to the pole and should not retrace a significant portion of the pole. Volume typically decreases during the pennant formation, indicating a temporary balance between buyers and sellers.
-   **Confirm Breakout**: The pattern is confirmed when price breaks decisively above the upper trendline of the pennant. This breakout should ideally be accompanied by an increase in volume and strong bullish candles, signaling the resumption of the uptrend.
-   **Contextualize**: Ensure the overall higher timeframe bias is bullish. Bull pennants are high-probability continuation patterns in established uptrends. Avoid pennants that are too large or show signs of bearish market structure shifts within the consolidation.

**Setup / Conditions:**
-   A strong bullish impulse (pole) occurs.
-   A subsequent contracting triangle (pennant) forms with lower highs and higher lows.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively above the upper trendline of the pennant.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the decisive breakout candle close above the pennant resistance, or on a retest of the broken trendline (which now acts as support).
-   **Stop Loss**: Place the stop loss below the low of the pennant, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the length of the pole, projected upwards from the breakout point. Alternatively, target the next significant liquidity level or resistance zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the breakout occurs directly into a strong, immediate resistance level, which could lead to a quick failure.
-   Reject if price breaks below the lower trendline of the pennant and accepts below it, indicating a potential reversal.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 48. Bear Pennant Continuation

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** A bearish continuation pattern that forms after a strong downward price impulse (the "pole"), followed by a symmetrical, contracting triangle (the "pennant"). It signifies a brief period of consolidation and indecision before the downtrend resumes.

**Claude Analytical Focus:**
-   **Identify Bearish Pole**: Look for a strong, aggressive downward move, characterized by large bearish candles and significant displacement. This "pole" should indicate clear selling pressure.
-   **Identify Pennant Consolidation**: Observe a subsequent period of consolidation where price forms a symmetrical triangle, characterized by converging trendlines (lower highs and higher lows). This consolidation should be relatively short-lived and represent a temporary pause in the trend.
-   **Confirm Pennant Structure**: The pennant should ideally be small relative to the pole and should not retrace a significant portion of the pole. Volume typically decreases during the pennant formation, indicating a temporary balance between buyers and sellers.
-   **Confirm Breakout**: The pattern is confirmed when price breaks decisively below the lower trendline of the pennant. This breakout should ideally be accompanied by an increase in volume and strong bearish candles, signaling the resumption of the downtrend.
-   **Contextualize**: Ensure the overall higher timeframe bias is bearish. Bear pennants are high-probability continuation patterns in established downtrends. Avoid pennants that are too large or show signs of bullish market structure shifts within the consolidation.

**Setup / Conditions:**
-   A strong bearish impulse (pole) occurs.
-   A subsequent contracting triangle (pennant) forms with lower highs and higher lows.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively below the lower trendline of the pennant.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the decisive breakout candle close below the pennant support, or on a retest of the broken trendline (which now acts as resistance).
-   **Stop Loss**: Place the stop loss above the high of the pennant, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the length of the pole, projected downwards from the breakout point. Alternatively, target the next significant liquidity level or support zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the breakdown occurs directly into a strong, immediate support level, which could lead to a quick failure.
-   Reject if price breaks above the upper trendline of the pennant and accepts above it, indicating a potential reversal.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 49. Ascending Triangle Continuation

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** A bullish continuation pattern characterized by a flat or horizontal resistance level and a series of rising swing lows. This pattern indicates that buyers are becoming more aggressive, pushing prices higher on each pullback, while sellers are defending a specific resistance level. It typically resolves with a breakout above the flat resistance.

**Claude Analytical Focus:**
-   **Identify Flat Resistance**: Locate a clear, horizontal resistance level that price has tested at least twice. This level represents a supply zone where sellers are consistently stepping in.
-   **Identify Rising Lows**: Observe a series of swing lows that are progressively higher, forming an ascending trendline. This indicates increasing buying pressure and a willingness of buyers to step in at higher prices.
-   **Confirm Triangle Structure**: The pattern is formed by the convergence of the flat resistance and the ascending trendline of the lows. Volume typically contracts during the formation of the triangle, indicating consolidation, and should expand on the breakout.
-   **Confirm Breakout**: The pattern is confirmed when price closes decisively above the flat resistance level. This breakout should ideally be accompanied by an increase in volume and strong bullish candles, signaling the continuation of the uptrend.
-   **Contextualize**: Ensure the overall higher timeframe bias is bullish. Ascending triangles are high-probability continuation patterns in established uptrends. Consider the time frame of the pattern; larger time frame triangles tend to be more reliable. Look for a breakout that is not immediately into another strong resistance level.

**Setup / Conditions:**
-   At least two similar highs form a flat resistance level.
-   A series of rising swing lows forms an ascending trendline.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively above the flat resistance level, and a subsequent retest of the broken resistance holds as support.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter long after the decisive close above resistance, or on a retest of the broken resistance level (which now acts as support). The retest often provides a lower-risk entry.
-   **Stop Loss**: Place the stop loss below the last higher low within the triangle, or below the retested resistance level, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the height of the triangle (from the lowest low to the flat resistance), projected upwards from the breakout point. Alternatively, target the next significant resistance level or supply zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the breakout occurs directly into a strong higher timeframe resistance level (e.g., VAH, PDH, KLZ), which could lead to a quick failure or false breakout.
-   Reject if price breaks below the ascending trendline of the lows, indicating a failure of the pattern and a potential reversal.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 50. Descending Triangle Continuation

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** A bearish continuation pattern characterized by a flat or horizontal support level and a series of falling swing highs. This pattern indicates that sellers are becoming more aggressive, pushing prices lower on each bounce, while buyers are defending a specific support level. It typically resolves with a breakout below the flat support.

**Claude Analytical Focus:**
-   **Identify Flat Support**: Locate a clear, horizontal support level that price has tested at least twice. This level represents a demand zone where buyers are consistently stepping in.
-   **Identify Falling Highs**: Observe a series of swing highs that are progressively lower, forming a descending trendline. This indicates increasing selling pressure and a willingness of sellers to push prices lower on each rally.
-   **Confirm Triangle Structure**: The pattern is formed by the convergence of the flat support and the descending trendline of the highs. Volume typically contracts during the formation of the triangle, indicating consolidation, and should expand on the breakdown.
-   **Confirm Breakdown**: The pattern is confirmed when price closes decisively below the flat support level. This breakdown should ideally be accompanied by an increase in volume and strong bearish candles, signaling the continuation of the downtrend.
-   **Contextualize**: Ensure the overall higher timeframe bias is bearish. Descending triangles are high-probability continuation patterns in established downtrends. Consider the time frame of the pattern; larger time frame triangles tend to be more reliable. Look for a breakdown that is not immediately into another strong support level.

**Setup / Conditions:**
-   At least two similar lows form a flat support level.
-   A series of falling swing highs forms a descending trendline.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively below the flat support level, and a subsequent retest of the broken support fails to push price back above it.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter short after the decisive close below support, or on a retest of the broken support level (which now acts as resistance). The retest often provides a lower-risk entry.
-   **Stop Loss**: Place the stop loss above the last lower high within the triangle, or above the retested support level, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the height of the triangle (from the highest high to the flat support), projected downwards from the breakdown point. Alternatively, target the next significant support level or demand zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the breakdown occurs directly into a strong higher timeframe support level (e.g., VAL, PDL, KLZ), which could lead to a quick failure or false breakdown.
-   Reject if price breaks above the descending trendline of the highs, indicating a failure of the pattern and a potential reversal.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 51. Symmetrical Triangle Breakout

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Medium  
**Works with Forex Majors:** Good  
**Best Use:** Intraday

**Description:** A symmetrical triangle is a continuation pattern characterized by converging trendlines, where the upper trendline slopes downwards (lower highs) and the lower trendline slopes upwards (higher lows). This indicates a period of consolidation and indecision, with decreasing volatility, before a decisive breakout in either direction.

**Claude Analytical Focus:**
-   **Identify Converging Trendlines**: Locate a pattern where price is making lower highs and higher lows, forming a symmetrical triangle. The trendlines should converge towards an apex.
-   **Contextualize Consolidation**: Recognize that this pattern represents a period of equilibrium between buyers and sellers, with decreasing volatility. Volume typically contracts during the formation of the triangle.
-   **Anticipate Breakout**: Understand that symmetrical triangles are typically continuation patterns, meaning they tend to break out in the direction of the preceding trend. However, they can also act as reversal patterns, so it's crucial to wait for a confirmed breakout.
-   **Confirm Breakout Direction**: The pattern is confirmed when price closes decisively above the upper trendline (for a bullish breakout) or below the lower trendline (for a bearish breakout). This breakout should ideally be accompanied by an expansion in volume.
-   **Measure Potential Move**: The potential target for a breakout from a symmetrical triangle is often measured by taking the height of the widest part of the triangle and projecting it from the breakout point.

**Setup / Conditions:**
-   Price forms converging trendlines with lower highs and higher lows, indicating compression and reduced range.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A decisive close occurs beyond either the upper or lower trendline of the triangle.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Prefer to enter on a retest of the broken trendline after the breakout, as this often provides a lower-risk entry. If the breakout is very strong and impulsive, an entry on the breakout candle close might be considered.
-   **Stop Loss**: Place the stop loss inside the triangle, typically behind the opposite side of the broken trendline or the last swing point within the triangle, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the height of the widest part of the triangle, projected from the breakout point. Alternatively, target the next significant liquidity level or support/resistance zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the breakout candle is too far extended from the entry point, making the risk-reward unfavorable.
-   Reject if price breaks out but quickly re-enters the triangle, indicating a false breakout.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 52. Rising Wedge Bearish Reversal

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** A bearish reversal pattern characterized by price moving upwards within a narrowing channel, formed by two converging trendlines that both slope upwards. The upper trendline is less steep than the lower one, indicating that buying momentum is weakening, and a breakdown below the lower trendline is often imminent.

**Claude Analytical Focus:**
-   **Identify Converging Upward Trendlines**: Locate a pattern where price is making higher highs and higher lows, but the range between them is contracting. Both the support and resistance trendlines should be sloping upwards, with the support trendline being steeper.
-   **Contextualize Weakening Momentum**: Recognize that despite making higher highs, the narrowing range and converging trendlines indicate a loss of bullish momentum and increasing indecision. Volume often decreases as the wedge forms.
-   **Anticipate Breakdown**: Rising wedges are typically bearish reversal patterns. Claude should anticipate a breakdown below the lower trendline, signaling a shift from an uptrend to a downtrend.
-   **Confirm Breakdown**: The pattern is confirmed when price closes decisively below the lower trendline of the wedge. This breakdown should ideally be accompanied by an increase in bearish momentum and volume.
-   **Look for Divergence**: Look for bearish divergence on momentum indicators (e.g., RSI, MACD) where price makes higher highs but the indicator makes lower highs. This provides strong additional confirmation of weakening bullish pressure.

**Setup / Conditions:**
-   Price rises in a narrowing channel, forming higher highs and higher lows, but with converging trendlines.
-   Momentum weakens as the pattern progresses.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A decisive close occurs below the lower trendline (support) of the wedge.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter short on the decisive close below the wedge support, or on a retest of the broken trendline (which now acts as resistance). The retest often provides a lower-risk entry.
-   **Stop Loss**: Place the stop loss above the last swing high within the wedge, or above the retested trendline, allowing for a small buffer.
-   **Targets**: Target the base of the wedge (where the pattern began) or the next significant support level. A measured move can also be calculated by taking the height of the widest part of the wedge and projecting it downwards from the breakout point.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the wedge breaks upward with clear acceptance above the upper trendline, indicating a continuation of the uptrend rather than a reversal.
-   Reject if price breaks below the lower trendline but quickly reclaims it, indicating a false breakdown.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 53. Falling Wedge Bullish Reversal

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** A bullish reversal pattern characterized by price moving downwards within a narrowing channel, formed by two converging trendlines that both slope downwards. The lower trendline is less steep than the upper one, indicating that selling momentum is weakening, and a breakout above the upper trendline is often imminent.

**Claude Analytical Focus:**
-   **Identify Converging Downward Trendlines**: Locate a pattern where price is making lower highs and lower lows, but the range between them is contracting. Both the support and resistance trendlines should be sloping downwards, with the resistance trendline being steeper.
-   **Contextualize Weakening Momentum**: Recognize that despite making lower lows, the narrowing range and converging trendlines indicate a loss of bearish momentum and increasing indecision. Volume often decreases as the wedge forms.
-   **Anticipate Breakout**: Falling wedges are typically bullish reversal patterns. Claude should anticipate a breakout above the upper trendline, signaling a shift from a downtrend to an uptrend.
-   **Confirm Breakout**: The pattern is confirmed when price closes decisively above the upper trendline of the wedge. This breakout should ideally be accompanied by an increase in bullish momentum and volume.
-   **Look for Divergence**: Look for bullish divergence on momentum indicators (e.g., RSI, MACD) where price makes lower lows but the indicator makes higher lows. This provides strong additional confirmation of weakening bearish pressure.

**Setup / Conditions:**
-   Price falls in a narrowing channel, forming lower highs and lower lows, but with converging trendlines.
-   Momentum weakens as the pattern progresses.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A decisive close occurs above the upper trendline (resistance) of the wedge.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter long on the decisive close above the wedge resistance, or on a retest of the broken trendline (which now acts as support). The retest often provides a lower-risk entry.
-   **Stop Loss**: Place the stop loss below the last swing low within the wedge, or below the retested trendline, allowing for a small buffer.
-   **Targets**: Target the base of the wedge (where the pattern began) or the next significant resistance level. A measured move can also be calculated by taking the height of the widest part of the wedge and projecting it upwards from the breakout point.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the wedge breaks downward with clear acceptance below the lower trendline, indicating a continuation of the downtrend rather than a reversal.
-   Reject if price breaks above the upper trendline but quickly reclaims it, indicating a false breakout.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 54. Range Breakout and Retest

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Price breaks out of a well-defined horizontal trading range (consolidation) and then retests the broken boundary, which now acts as flipped support or resistance, before continuing in the direction of the breakout.

**Claude Analytical Focus:**
-   **Identify Clear Range**: Locate a distinct horizontal trading range with at least two touches on both the upper (resistance) and lower (support) boundaries. This indicates a period of equilibrium between buyers and sellers.
-   **Detect Decisive Breakout**: Observe a strong, impulsive candle closing decisively outside either the upper or lower boundary of the range. The breakout should be clear and not just a wick.
-   **Confirm Retest and Hold**: The crucial part of this signal is the retest. Look for price to pull back to the broken range boundary. The confirmation comes when this boundary holds as new support (after a bullish breakout) or resistance (after a bearish breakout), with price rejecting the level.
-   **Contextualize Momentum**: A breakout with increased volume and strong momentum is generally more reliable. The retest phase often sees decreased volume, indicating a lack of opposing pressure.
-   **Avoid False Breakouts**: Be wary of breakouts that are only wicks or quickly reverse back into the range. The retest phase helps filter out these false moves.

**Setup / Conditions:**
-   A clear horizontal trading range is established with multiple touches on both support and resistance.
-   Price breaks out of this range with a decisive candle close.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively outside the range, and a subsequent retest of the broken boundary holds as new support or resistance.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the rejection of the retest of the broken range boundary. This provides a higher probability entry with a tighter stop loss.
-   **Stop Loss**: Place the stop loss back inside the original range, typically just beyond the retested level, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the height of the original range, projected from the breakout point. Alternatively, target the next significant liquidity level or support/resistance zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the breakout is only a wick, or if price quickly returns and accepts back inside the original range after the breakout.
-   Reject if the retest of the broken boundary fails to hold, and price breaks back through it.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 55. Rectangle Trading

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Range day

**Description:** Price consolidates within a well-defined horizontal channel (rectangle), bouncing between clear support and resistance levels. This signal focuses on trading from the edges of the rectangle back towards the center or the opposite side, capitalizing on range-bound market conditions.

**Claude Analytical Focus:**
-   **Identify Clear Rectangle**: Locate a distinct horizontal trading range characterized by stable, parallel support and resistance levels that price has touched multiple times. This indicates a period of equilibrium and indecision.
-   **Contextualize Market State**: Confirm that the market is in a balanced or range-bound state. This signal is highly effective when there is no clear trend and price is oscillating within a defined channel. Avoid this signal during strong trending conditions.
-   **Detect Edge Rejection**: Observe price approaching either the upper (resistance) or lower (support) boundary of the rectangle. Look for clear signs of rejection at these levels, such as reversal candle patterns (e.g., pin bars, engulfing patterns) or a loss of momentum.
-   **Confirm Rotation**: A rejection from the resistance suggests a rotation towards the support or the midpoint, and vice-versa. Confirm this by looking for price action moving away from the rejected extreme.
-   **Volume Analysis**: Volume typically contracts within the rectangle, indicating consolidation. A spike in volume at the edges, followed by rejection, can strengthen the signal.

**Setup / Conditions:**
-   A balanced trading range is established with clear, stable horizontal support and resistance levels.
-   Price is trading within this rectangle, touching both boundaries multiple times.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A clear rejection occurs from either the upper (resistance) or lower (support) boundary of the rectangle.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after a clear rejection candle forms at the range low (for a long) or range high (for a short). The entry should be in the direction of the anticipated rotation.
-   **Stop Loss**: Place the stop loss just outside the rejected range boundary, allowing for a small buffer to account for volatility.
-   **Targets**: Target the midpoint of the rectangle first, then the opposite range boundary. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the market transitions into a strong trend day or shows clear acceptance outside the rectangle, indicating a breakout.
-   Reject if price closes and accepts decisively outside the rectangle, as this invalidates the range-bound condition.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 56. Parallel Channel Trading

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Price moves within a well-defined parallel channel, bounded by two parallel trendlines (either rising or falling). This pattern indicates a sustained trend with predictable bounces off the channel boundaries, offering opportunities to trade in the direction of the channel.

**Claude Analytical Focus:**
-   **Identify Parallel Channel**: Locate a clear channel where price is contained between two parallel trendlines. For a rising channel, both trendlines slope upwards; for a falling channel, both slope downwards. There should be at least two reliable touches on each boundary (or three total touches) to confirm the channel's validity.
-   **Contextualize Trend**: Recognize that parallel channels represent a sustained trend. Trading within the channel involves taking trades in the direction of the channel's slope (long in a rising channel, short in a falling channel) from the respective support/resistance boundaries.
-   **Detect Boundary Rejection**: Observe price approaching and rejecting either the upper or lower boundary of the channel. Look for clear reversal candle patterns (e.g., pin bars, engulfing patterns) or a loss of momentum at these boundaries, indicating that the channel is holding.
-   **Confirm Continuation**: A rejection from the lower boundary of a rising channel (support) confirms a long opportunity, while a rejection from the upper boundary of a falling channel (resistance) confirms a short opportunity. Price should then continue to move towards the opposite boundary or the channel midline.
-   **Volume Analysis**: Volume typically supports the trend within the channel. Look for increased volume on moves in the direction of the channel and decreased volume on pullbacks against the channel.

**Setup / Conditions:**
-   A clear parallel channel (rising or falling) is established with at least two touches on each side or three reliable touches in total.
-   Price is respecting the channel boundaries.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price touches a channel boundary and shows clear rejection in the direction of the channel (e.g., bullish rejection at lower boundary of rising channel, bearish rejection at upper boundary of falling channel).
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after a clear rejection candle forms at the channel boundary, in the direction of the channel. For example, long after a bullish rejection at the lower boundary of a rising channel.
-   **Stop Loss**: Place the stop loss just outside the channel boundary that was rejected, allowing for a small buffer.
-   **Targets**: Target the channel midline first, then the opposite channel boundary. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the channel slope is too steep, indicating an unsustainable move that is prone to sharp reversals.
-   Reject if price breaks decisively outside a channel boundary and accepts beyond it, indicating a potential trend reversal or acceleration.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 57. Channel Breakout and Retest

**Category:** Classic Pattern  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Price breaks out of an established parallel channel (either rising or falling) and then retests the broken channel boundary, which now acts as flipped support or resistance, before continuing its move in the direction of the breakout.

**Claude Analytical Focus:**
-   **Identify Established Channel**: Locate a clear, well-defined parallel channel (rising or falling) that price has been respecting with multiple touches on both its upper and lower boundaries. This indicates a period of sustained trend or consolidation within the channel.
-   **Detect Decisive Breakout**: Observe a strong, impulsive candle closing decisively outside either the upper or lower boundary of the channel. The breakout should be clear and not merely a wick. Increased volume accompanying the breakout often adds to its validity.
-   **Confirm Retest and Hold**: The critical element of this signal is the retest. Look for price to pull back to the broken channel boundary. The confirmation comes when this boundary holds as new support (after a bullish breakout) or resistance (after a bearish breakout), with price rejecting the level and continuing in the breakout direction.
-   **Contextualize Momentum**: A breakout with strong momentum is generally more reliable. The retest phase often sees decreased volume, indicating a lack of opposing pressure. Avoid confusing a retest with a false breakout where price quickly re-enters the channel.
-   **Avoid False Breakouts**: Be wary of breakouts that are only wicks or quickly reverse back into the channel. The retest phase helps filter out these less reliable moves.

**Setup / Conditions:**
-   An established rising or falling parallel channel is present.
-   Price breaks out of the channel with a decisive candle close.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively outside the channel, and a subsequent retest of the broken channel boundary holds as new support or resistance, leading to continuation in the breakout direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the rejection of the retest of the broken channel boundary. This provides a higher probability entry with a tighter stop loss.
-   **Stop Loss**: Place the stop loss back inside the original channel, typically just beyond the retested level, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the width of the original channel, projected from the breakout point. Alternatively, target the next significant liquidity level or support/resistance zone.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the breakout lacks a decisive candle close or if the retest fails to hold, and price quickly re-enters the channel.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 58. Exhaustion Reversal

**Category:** Classic Pattern / Institutional  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Good  
**Best Use:** Scalping

**Description:** Price experiences an unsustainable, rapid acceleration in one direction, often characterized by multiple large-bodied candles extending far from mean-reversion levels (like VWAP), and then reverses sharply upon reaching a significant key level. This indicates a temporary exhaustion of buying or selling pressure.

**Claude Analytical Focus:**
-   **Identify Extreme Extension**: Look for signs of extreme price extension, such as a series of large-bodied candles in the same direction, moving significantly away from the VWAP or other central price averages. This suggests that the move is becoming overextended and potentially unsustainable.
-   **Contextualize with Key Levels**: This signal is most potent when the exhaustion occurs at a significant higher timeframe key level (e.g., daily/weekly resistance/support, an Order Block, a Fair Value Gap, Previous Day High/Low, or a major psychological level). The confluence with such a level increases the probability of a reversal.
-   **Confirm Reversal**: It is crucial to wait for clear reversal confirmation. This typically involves a rejection candle (e.g., a pin bar, bearish/bullish engulfing pattern) forming at the key level, followed by a Change of Character (CHOCH) or a Break of Structure (BOS) on a lower timeframe in the opposite direction. **Never blindly fade an extended move without confirmation.**
-   **Volume Analysis**: Look for decreasing volume during the extended move, indicating a lack of fresh participants, or a spike in volume on the reversal candle, suggesting strong opposing pressure.

**Setup / Conditions:**
-   Price shows multiple candles expanding rapidly in the same direction, moving far from the VWAP or other mean-reversion levels.
-   This extended move occurs into a significant higher timeframe key level (e.g., resistance for a short, support for a long).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A clear rejection candle forms at the key level, followed by a Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe in the opposite direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the structure shift (CHOCH/BOS) confirms the reversal, or on a retest of the broken structure level. Do not enter solely because price appears extended.
-   **Stop Loss**: Place the stop loss beyond the extreme of the rejection (e.g., beyond the high/low of the reversal candle or the key level), allowing for a small buffer.
-   **Targets**: Target the VWAP, the first standard deviation band, or a prior significant structure level. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the extended move is part of a strong news continuation or a clean "band-walk" along VWAP bands, indicating sustained momentum rather than exhaustion.
-   Reject if the reversal confirmation (rejection candle, CHOCH/BOS) is weak or absent, or if price closes and accepts beyond the key level.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 59. Asian Range Breakout

**Category:** Session  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** London/NY

**Description:** Price breaks out of the established trading range formed during the Asian session, often at the start of the London or New York session, and then retests the broken boundary before continuing in the direction of the breakout. This signal capitalizes on the liquidity injection and directional bias that often emerges during subsequent major trading sessions.

**Claude Analytical Focus:**
-   **Define Asian Range**: Claude should first clearly identify and mark the high and low of the Asian trading session. This range often acts as a liquidity pool that is targeted by institutional players in later sessions.
-   **Contextualize Session Open**: Recognize that the start of the London and New York sessions typically brings increased volatility and liquidity, making them prime times for breakouts from the Asian range.
-   **Detect Decisive Breakout**: Observe a strong, impulsive candle closing decisively outside either the high or low of the Asian range. The breakout should be clear and not just a wick. Increased volume accompanying the breakout often adds to its validity.
-   **Confirm Retest and Hold**: The crucial part of this signal is the retest. Look for price to pull back to the broken Asian range boundary. The confirmation comes when this boundary holds as new support (after a bullish breakout) or resistance (after a bearish breakout), with price rejecting the level and continuing in the breakout direction.
-   **Avoid False Breakouts**: Be wary of breakouts that are only wicks or quickly reverse back into the Asian range. The retest phase helps filter out these less reliable moves.

**Setup / Conditions:**
-   A clear Asian trading range (high and low) is established.
-   Price breaks out of this range, typically at the start of the London or New York session, with a decisive candle close.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively outside the Asian range, and a subsequent retest of the broken boundary holds as new support or resistance.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the rejection of the retest of the broken Asian range boundary. This provides a higher probability entry with a tighter stop loss.
-   **Stop Loss**: Place the stop loss back inside the Asian range, typically just beyond the retested level, allowing for a small buffer.
-   **Targets**: Target a measured move equal to the height of the Asian range, projected from the breakout point. Alternatively, target the next significant liquidity level (e.g., PDH/PDL, session high/low) or a higher timeframe Order Block/FVG.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the breakout occurs during a "dead time" (e.g., late Asian session, before major news) or directly into a strong higher timeframe resistance/support level without clear acceptance.
-   Reject if the breakout lacks a decisive candle close or if the retest fails to hold, and price quickly re-enters the Asian range.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 60. Asian Range Sweep Reversal

**Category:** Session / Liquidity  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** London/NY

**Description:** Price initially sweeps (takes out) the liquidity above the Asian session high or below the Asian session low, often as a 'fakeout' or 'stop hunt', and then quickly reverses to trade back within or beyond the Asian range. This pattern is a classic institutional maneuver to trap early breakout traders before initiating a move in the opposite direction.

**Claude Analytical Focus:**
-   **Define Asian Range**: Claude should first clearly identify and mark the high and low of the Asian trading session. These levels represent significant liquidity pools.
-   **Detect Liquidity Sweep**: Observe price moving decisively above the Asian high or below the Asian low. This move should ideally be a quick, sharp spike (a 'wick' or 'fakeout') that extends beyond the range boundary but fails to close and accept above/below it.
-   **Confirm Re-entry and Reversal**: The critical confirmation is when price quickly re-enters the Asian range after the sweep. This re-entry, especially if followed by a Break of Structure (BOS) or Change of Character (CHOCH) on a lower timeframe in the opposite direction of the sweep, signals a high-probability reversal.
-   **Contextualize with Session Open**: This signal is particularly potent around the London or New York session open, as these sessions often see institutional players targeting liquidity from the preceding Asian session.
-   **Volume Analysis**: Look for a spike in volume during the sweep, followed by a decrease as price re-enters the range, and then an increase again on the BOS/CHOCH, confirming the reversal.

**Setup / Conditions:**
-   A clear Asian session high or low is established.
-   Price sweeps the liquidity above the Asian high or below the Asian low.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price breaks the Asian range extreme (high or low), but then closes back inside the Asian range.
-   A subsequent Break of Structure (BOS) or Change of Character (CHOCH) occurs in the opposite direction of the initial sweep, confirming the reversal.
-   Prefer candle close confirmation over wick-only confirmation for the re-entry and BOS.

**Execution:**
-   **Entry**: Enter after the re-entry into the Asian range and the confirmation of a BOS/CHOCH in the reversal direction. A retest of the broken structure or the Asian range boundary can provide a refined entry.
-   **Stop Loss**: Place the stop loss beyond the extreme of the fakeout wick (the highest point of the sweep for a short, or the lowest point for a long), allowing for a small buffer.
-   **Targets**: Target the midpoint of the Asian range, the opposite side of the Asian range, or the next significant liquidity level (e.g., PDH/PDL, session high/low). Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price closes and accepts decisively outside the Asian range after the initial sweep, indicating a genuine breakout rather than a fakeout.
-   Reject if the re-entry into the Asian range or the subsequent BOS/CHOCH is not clear or lacks conviction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 61. London Open Liquidity Sweep Reversal

**Category:** Session / Liquidity  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** This signal identifies a common institutional maneuver occurring around the London Open. Price makes a quick, aggressive move to sweep (take out) liquidity resting above a previous high (e.g., Asian high) or below a previous low (e.g., Asian low), often trapping early breakout traders. Following this liquidity grab, price rapidly reverses, indicating that the initial move was a 'stop hunt' before the true directional move begins.

**Claude Analytical Focus:**
-   **Identify London Open Window**: Claude should be instructed to focus its analysis specifically around the London trading session open, as this is a period of significant liquidity injection and institutional activity.
-   **Detect Liquidity Sweep**: Look for price to aggressively push beyond a clear liquidity level, such as the Asian session high or low, or other significant micro liquidity points (e.g., previous swing highs/lows). This sweep is often characterized by a quick spike or a large wick that extends beyond the level.
-   **Confirm Reclaim and Reversal**: The critical confirmation is when price fails to accept beyond the swept level and quickly reclaims it (closes back inside the previous range or below/above the swept high/low). This reclaim should then be followed by a Change of Character (CHOCH) or a Break of Structure (BOS) on a lower timeframe, signaling a definitive shift in market direction.
-   **Contextualize Institutional Intent**: Understand that these sweeps are often designed to trigger stop losses and absorb orders before institutions initiate their intended move. Claude should interpret the reclaim and structural shift as a strong indication of the true market direction.
-   **Volume Analysis**: Observe volume during the sweep. A spike in volume on the sweep, followed by a decrease on the reclaim, and then an increase on the CHOCH/BOS can provide additional confirmation.

**Setup / Conditions:**
-   The pattern occurs within the London Open trading window.
-   Price sweeps a significant liquidity level (e.g., Asian high/low, previous micro liquidity).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price sweeps the liquidity level, then quickly reclaims it (closes back inside the previous range or below/above the swept level).
-   A subsequent Change of Character (CHOCH) or Break of Structure (BOS) occurs in the opposite direction of the sweep.
-   Prefer candle close confirmation over wick-only confirmation for the reclaim and structural shift.

**Execution:**
-   **Entry**: Enter after the reclaim of the swept level and the confirmation of the CHOCH/BOS. A retest of the broken structure or the reclaimed level can offer a more precise entry.
-   **Stop Loss**: Place the stop loss beyond the extreme of the sweep (the highest point of the wick for a short, or the lowest point for a long), allowing for a small buffer.
-   **Targets**: Target the VWAP, the opposite side of the Asian range, or other significant session liquidity levels. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if there is no clear reclaim of the swept level within a limited number of candles, or if price closes and accepts decisively beyond the swept level, indicating a genuine breakout.
-   Reject if the CHOCH/BOS is not clear or lacks conviction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 62. NY Session High Sweep Reversal

**Category:** Session / Liquidity  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** NY Session

**Description:** This signal describes a scenario where, during the New York trading session, price aggressively pushes above the high established during the preceding London session. This move often serves to sweep liquidity (stop losses) resting above the London high, trapping early buyers, before price quickly reverses and trades back below the London high, indicating a potential bearish reversal.

**Claude Analytical Focus:**
-   **Identify London Session High**: Claude should first clearly identify and mark the high of the London trading session. This level represents a significant liquidity pool that institutions may target.
-   **Detect NY Session Sweep**: Observe price action during the New York session. Look for a sharp, impulsive move that extends above the London high. This move should ideally be a quick spike or a large wick, indicating a liquidity grab rather than a sustained breakout.
-   **Confirm Reclaim and Reversal**: The critical confirmation is when price fails to accept above the swept London high and quickly reclaims it (closes back below the London high). This re-entry, especially if followed by a bearish Change of Character (CHOCH) or a Break of Structure (BOS) on a lower timeframe, signals a high-probability bearish reversal.
-   **Contextualize Institutional Intent**: Understand that these sweeps are often designed to trigger stop losses and absorb buy orders before institutions initiate a move in the opposite direction. Claude should interpret the reclaim and structural shift as a strong indication of a bearish bias for the remainder of the NY session.
-   **Volume Analysis**: Look for a spike in volume during the sweep, followed by a decrease as price re-enters below the London high, and then an increase again on the BOS/CHOCH, confirming the reversal.

**Setup / Conditions:**
-   A clear London session high is established before the New York session begins.
-   During the New York session, price trades above the London high.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price trades above the London high, but then closes back below it, indicating a failure to accept higher prices.
-   A subsequent bearish Change of Character (CHOCH) or Break of Structure (BOS) occurs, confirming the shift in market structure.
-   Prefer candle close confirmation over wick-only confirmation for the re-entry and structural shift.

**Execution:**
-   **Entry**: Enter short after the reclaim of the London high and the confirmation of a bearish CHOCH/BOS. A retest of the broken structure or the reclaimed London high can offer a more precise entry.
-   **Stop Loss**: Place the stop loss beyond the high of the NY sweep (the highest point of the wick), allowing for a small buffer.
-   **Targets**: Target the VWAP, the Point of Control (POC), the London session midpoint, or the London session low. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price closes and accepts decisively above the London high during the NY session, indicating a genuine bullish continuation rather than a fakeout.
-   Reject if the re-entry below the London high or the subsequent bearish CHOCH/BOS is not clear or lacks conviction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 63. NY Session Low Sweep Reversal

**Category:** Session / Liquidity  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** NY Session

**Description:** This signal describes a scenario where, during the New York trading session, price aggressively pushes below the low established during the preceding London session. This move often serves to sweep liquidity (stop losses) resting below the London low, trapping early sellers, before price quickly reverses and trades back above the London low, indicating a potential bullish reversal.

**Claude Analytical Focus:**
-   **Identify London Session Low**: Claude should first clearly identify and mark the low of the London trading session. This level represents a significant liquidity pool that institutions may target.
-   **Detect NY Session Sweep**: Observe price action during the New York session. Look for a sharp, impulsive move that extends below the London low. This move should ideally be a quick spike or a large wick, indicating a liquidity grab rather than a sustained breakdown.
-   **Confirm Reclaim and Reversal**: The critical confirmation is when price fails to accept below the swept London low and quickly reclaims it (closes back above the London low). This re-entry, especially if followed by a bullish Change of Character (CHOCH) or a Break of Structure (BOS) on a lower timeframe, signals a high-probability bullish reversal.
-   **Contextualize Institutional Intent**: Understand that these sweeps are often designed to trigger stop losses and absorb sell orders before institutions initiate a move in the opposite direction. Claude should interpret the reclaim and structural shift as a strong indication of a bullish bias for the remainder of the NY session.
-   **Volume Analysis**: Look for a spike in volume during the sweep, followed by a decrease as price re-enters above the London low, and then an increase again on the BOS/CHOCH, confirming the reversal.

**Setup / Conditions:**
-   A clear London session low is established before the New York session begins.
-   During the New York session, price trades below the London low.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price trades below the London low, but then closes back above it, indicating a failure to accept lower prices.
-   A subsequent bullish Change of Character (CHOCH) or Break of Structure (BOS) occurs, confirming the shift in market structure.
-   Prefer candle close confirmation over wick-only confirmation for the re-entry and structural shift.

**Execution:**
-   **Entry**: Enter long after the reclaim of the London low and the confirmation of a bullish CHOCH/BOS. A retest of the broken structure or the reclaimed London low can offer a more precise entry.
-   **Stop Loss**: Place the stop loss beyond the low of the NY sweep (the lowest point of the wick), allowing for a small buffer.
-   **Targets**: Target the VWAP, the Point of Control (POC), the London session midpoint, or the London session high. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price closes and accepts decisively below the London low during the NY session, indicating a genuine bearish continuation rather than a fakeout.
-   Reject if the re-entry above the London low or the subsequent bullish CHOCH/BOS is not clear or lacks conviction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 64. NY Open Manipulation Reversal

**Category:** Session / Liquidity / Manipulation  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** This signal identifies a common institutional manipulation tactic during the initial phase of the New York trading session. Price makes a sharp, often impulsive, move in one direction to sweep liquidity (trigger stop losses and absorb orders) before quickly reversing and initiating a sustained move in the opposite direction. This traps early participants who traded the initial impulsive move.

**Claude Analytical Focus:**
-   **Identify NY Open Window**: Claude should focus its analysis within the first 15-45 minutes following the official New York session open. This is a high-volatility period prone to institutional manipulation.
-   **Detect Initial Impulsive Move (Manipulation Leg)**: Look for a rapid, aggressive price movement, often characterized by large candles or a significant Average True Range (ATR) extension, immediately after the NY open. This move is designed to draw in retail traders and trigger liquidity.
-   **Contextualize with Liquidity**: The initial move often targets obvious liquidity pools, such as previous session highs/lows, equal highs/lows, or unmitigated Order Blocks/FVGs. Claude should identify these potential targets.
-   **Confirm Reversal (Reclaim and BOS)**: The critical confirmation is when price fails to sustain the initial manipulative move. This involves:
    1.  **Reclaim**: Price quickly reverses and closes back within the range from which the manipulation originated, or decisively reclaims a key level.
    2.  **Change of Character (CHOCH) / Break of Structure (BOS)**: A clear shift in market structure on a lower timeframe (e.g., 1-minute, 3-minute) in the opposite direction of the initial manipulative move. This confirms that the institutional intent has shifted.
-   **Volume Analysis**: Look for a spike in volume during the initial manipulative sweep, followed by a decrease as price reclaims, and then an increase again on the CHOCH/BOS, confirming the reversal.

**Setup / Conditions:**
-   The pattern occurs within the first 15-45 minutes after the New York session open.
-   An initial sharp, impulsive move sweeps liquidity (e.g., previous session high/low, equal highs/lows).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The initial manipulative move sweeps liquidity and then fails to sustain, with price closing back within the original range or reclaiming a key level.
-   A subsequent Change of Character (CHOCH) or Break of Structure (BOS) occurs in the opposite direction of the initial sweep, confirming the reversal.
-   Prefer candle close confirmation over wick-only confirmation for the reclaim and structural shift.

**Execution:**
-   **Entry**: Enter after the NY manipulation reclaim and the confirmation of a CHOCH/BOS. A retest of the broken structure or the reclaimed level can offer a more precise entry.
-   **Stop Loss**: Place the stop loss beyond the extreme of the manipulation (the highest point of the wick for a short, or the lowest point for a long), allowing for a small buffer.
-   **Targets**: Target the VWAP, the New York session opening price, or the opposite liquidity pool (e.g., the low of the initial manipulative move if going long, or the high if going short). Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the initial manipulative move aligns with strong news continuation and price continues to trend in that direction without a clear reclaim or structural shift.
-   Reject if price closes and accepts decisively beyond the manipulated level, indicating a genuine breakout rather than a fakeout.
-   Reject if the reclaim or subsequent CHOCH/BOS is not clear or lacks conviction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 65. NY Manipulation Continuation

**Category:** Session / Trend Continuation  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** Following a confirmed New York Open Manipulation Reversal (Signal 64), where initial liquidity was swept and price reversed, this signal identifies opportunities to join the newly established trend after a corrective pullback. It assumes that the manipulation has successfully trapped traders, and the market is now ready to continue in the
true directional move.

**Claude Analytical Focus:**
-   **Confirm Prior Manipulation Reversal**: Claude must first confirm that a NY Open Manipulation Reversal (Signal 64) has successfully occurred, meaning liquidity was swept, price reclaimed, and a clear Change of Character (CHOCH) or Break of Structure (BOS) has been established in the new direction.
-   **Identify Corrective Pullback**: After the initial reversal move, look for a corrective pullback towards key levels in the direction of the new trend. These key levels could include:
    -   VWAP (Volume Weighted Average Price)
    -   Key Level Zones (KLZ)
    -   Fair Value Gaps (FVG) that were created during the initial reversal move
    -   Order Blocks (OB) or Breaker Blocks (BB)
-   **Confirm Pullback Rejection**: The crucial confirmation is when price reaches one of these key levels during the pullback and shows clear signs of rejection (e.g., bullish engulfing for a long, bearish engulfing for a short), indicating that the new trend is holding and buyers/sellers are stepping back in.
-   **Contextualize Momentum**: The pullback should ideally be shallow and corrective, not impulsive. Volume should typically decrease during the pullback and increase again on the rejection from the key level.

**Setup / Conditions:**
-   A confirmed NY Open Manipulation Reversal has occurred, establishing a new trend direction.
-   Price initiates a corrective pullback towards a significant key level (VWAP, KLZ, FVG, OB).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The pullback reaches a key level and shows clear rejection, with a candle close confirming the continuation in the new trend direction.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the rejection of the pullback from the key level, after a candle close confirms the continuation.
-   **Stop Loss**: Place the stop loss beyond the swing low/high of the pullback, allowing for a small buffer.
-   **Targets**: Target session expansion levels, such as the next significant liquidity pool, higher timeframe resistance/support, or a measured move based on the initial reversal leg. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the pullback extends too deeply (e.g., beyond 50-61.8% of the initial reversal move) or breaks the newly established market structure, indicating a potential failure of the new trend.
-   Reject if the market enters a period of "lunch chop" (mid-day consolidation) or if the target has already been hit, reducing the potential for further movement.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """))

## 66. NY Lunch Chop Filter

**Category:** Session / Filter  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Filter

**Description:** This signal serves as a filter to avoid trading during the low-quality, often unpredictable, consolidation period that typically occurs during the New York lunch hour. During this time, institutional participation often decreases, leading to reduced volatility, tighter ranges, and frequent false breakouts, making high-probability trading difficult.

**Claude Analytical Focus:**
-   **Identify Time Window**: Claude should be instructed to recognize the specific time window corresponding to the New York lunch hour (typically 12:00 PM to 1:00 PM EST, but can extend). This is the primary condition for activating this filter.
-   **Observe Market Characteristics**: During this period, Claude should look for:
    -   **Low Average True Range (ATR)**: A significant decrease in the average size of candles, indicating reduced volatility.
    -   **Tight Range**: Price consolidating within a narrow horizontal range, often chopping around the VWAP.
    -   **Lack of Clear Direction**: Absence of strong impulsive moves or clear market structure shifts.
    -   **Repeated VWAP Crosses**: Similar to the "VWAP Chop/Indecision" signal, frequent crosses of the VWAP without sustained acceptance above or below it.
-   **Prioritize Capital Preservation**: The analytical focus here is on capital preservation. Claude should interpret these conditions as unfavorable for initiating new directional trades, especially scalps, due to the increased risk of whipsaws and false signals.
-   **Wait for Liquidity Return**: Claude should monitor for the return of institutional liquidity and clearer directional movement, typically after the lunch hour, before considering new trade setups.

**Setup / Conditions:**
-   The current trading period falls within the New York lunch hour time window.
-   Price exhibits characteristics of low volatility, such as a tight trading range and low Average True Range (ATR).
-   Price is often chopping around the VWAP, indicating indecision.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The trigger is the identification of the market entering the NY lunch hour and displaying the associated low-quality trading characteristics.
-   There is no trade trigger; the confirmation is the decision to *not* trade or to significantly reduce exposure.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Execution is WAIT only. No new trades should be initiated based on this signal.
-   **Stop Loss**: Not applicable, as no trade is taken.
-   **Targets**: Not applicable, as no trade is taken.
-   **Minimum Risk/Reward**: Not applicable, as no trade is taken.

**Invalidation / Reject:**
-   Reject most scalping opportunities during this period, as the risk-reward is often unfavorable.
-   This filter can be temporarily overridden if there is an *exceptional* confluence of higher timeframe levels and a clear, impulsive breakout with strong volume, but such instances are rare.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 67. London Close Reversal

**Category:** Session / Reversal  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** This signal identifies potential reversals that often occur near the London trading session close. As London traders close positions or rebalance portfolios, price can become extended from its mean, leading to a liquidity grab or exhaustion move, followed by a sharp reversal. This reversal often sets the tone for the remainder of the New York session.

**Claude Analytical Focus:**
-   **Identify London Close Window**: Claude should focus its analysis around the London trading session close (typically 4:00 PM GMT/11:00 AM EST, but can vary). This period often sees increased volatility and potential for reversals due to profit-taking and position adjustments.
-   **Detect Price Extension**: Look for price to be significantly extended from mean-reversion levels such as the VWAP. This extension suggests that the current move might be overstretched and vulnerable to a reversal.
-   **Identify Liquidity Sweep/Exhaustion**: Observe price action for signs of a liquidity sweep (e.g., a quick spike above a previous high or below a previous low to trigger stop losses) or general exhaustion (e.g., small-bodied candles, decreasing momentum, divergence on oscillators) at a key level.
-   **Confirm Reversal with Structural Shift**: The critical confirmation is a clear Change of Character (CHOCH) or a Break of Structure (BOS) on a lower timeframe in the opposite direction of the extended move. This indicates that the market structure has shifted, confirming the reversal.
-   **Contextualize with US Session**: Consider the strength of the ongoing US session. If the US session is exhibiting a very strong, sustained trend, the London Close reversal might be less reliable or offer shallower targets.

**Setup / Conditions:**
-   The trading period is near the London session close.
-   Price is significantly extended from its mean (e.g., far from VWAP).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A liquidity sweep or exhaustion pattern occurs at a key level.
-   This is followed by a clear Change of Character (CHOCH) or Break of Structure (BOS) in the opposite direction of the extended move.
-   Prefer candle close confirmation over wick-only confirmation for the structural shift.

**Execution:**
-   **Entry**: Enter after the reversal is confirmed by the CHOCH/BOS. A retest of the broken structure can offer a more precise entry.
-   **Stop Loss**: Place the stop loss beyond the extreme of the reversal (e.g., beyond the high of the sweep for a short, or the low for a long), allowing for a small buffer.
-   **Targets**: Target the VWAP, the session midpoint, or the next significant liquidity level. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the US trend day remains strong and shows no signs of weakening, as it may override the London Close reversal.
-   Reject if the reversal confirmation (liquidity sweep, exhaustion, CHOCH/BOS) is weak or absent.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 68. Daily Open Polarity

**Category:** Session / Key Level  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** The daily open price often acts as a significant intraday polarity level. Price tends to move away from it, and upon retesting, the daily open can flip its role from resistance to support (or vice-versa), providing continuation opportunities in the prevailing intraday bias.

**Claude Analytical Focus:**
-   **Identify Daily Open**: Claude should precisely identify and mark the daily open price. This level is a crucial reference point for the day's trading activity.
-   **Observe Initial Reaction**: Monitor how price behaves immediately after the daily open. Does it move strongly in one direction, establishing an initial bias?
-   **Detect Retest and Polarity Flip**: Look for price to return and retest the daily open level. The key is to observe a clear rejection or acceptance at this level. If price was initially below the daily open and then breaks above it, a retest that holds as support (polarity flip) indicates bullish continuation. Conversely, if price was initially above and then breaks below, a retest that holds as resistance indicates bearish continuation.
-   **Confirm with Market Structure**: A successful retest and polarity flip is significantly strengthened when accompanied by a Change of Character (CHOCH) or a Break of Structure (BOS) on a lower timeframe, confirming the shift in market control.
-   **Contextualize with Higher Timeframe Bias**: This signal is most reliable when the intraday bias confirmed by the daily open polarity aligns with the higher timeframe trend or bias.

**Setup / Conditions:**
-   Price moves away from the daily open, establishing an initial intraday direction.
-   Price then returns to retest the daily open level.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The daily open holds as support (for a long) or resistance (for a short) upon retest.
-   A subsequent Change of Character (CHOCH) or Break of Structure (BOS) confirms the continuation in the prevailing intraday bias.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the rejection from the daily open and the confirmation of the CHOCH/BOS in the prevailing bias. A retest of the broken structure can offer a more precise entry.
-   **Stop Loss**: Place the stop loss beyond the swing high/low of the retest, allowing for a small buffer.
-   **Targets**: Target the session high/low, the VWAP bands, or the next significant liquidity level. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the daily open is repeatedly chopped through without clear acceptance or rejection, indicating a lack of conviction at this level.
-   Reject if price closes and accepts decisively beyond the daily open in the opposite direction of the intended trade, invalidating the polarity.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 69. Weekly Open Polarity

**Category:** Session / Key Level  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Swing

**Description:** The weekly open price serves as a crucial higher-timeframe polarity level. Price often revisits this level during the trading week, and its reaction at the weekly open can dictate the directional bias for the remainder of the week. A successful retest and hold of the weekly open, or a flip of its role from resistance to support (or vice-versa), provides significant confluence for swing trades.

**Claude Analytical Focus:**
-   **Identify Weekly Open**: Claude should precisely identify and mark the weekly open price. This level is a pivotal reference point for the entire trading week.
-   **Observe Price Action at Weekly Open**: Monitor how price interacts with the weekly open. Does it move strongly away and then return for a retest? Or does it consolidate around it?
-   **Detect Polarity Flip or Rejection**: The key is to observe a clear rejection or acceptance at this level. If price was initially below the weekly open and then breaks above it, a retest that holds as support (polarity flip) indicates bullish continuation for the week. Conversely, if price was initially above and then breaks below, a retest that holds as resistance indicates bearish continuation.
-   **Confirm with Higher Timeframe Bias**: This signal is most reliable when the reaction at the weekly open aligns with the overall higher timeframe (e.g., monthly, quarterly) bias. For instance, a bullish rejection at the weekly open in an overall bullish monthly trend is a high-probability setup.
-   **Look for Confluence**: The strength of this signal is significantly enhanced when the weekly open aligns with other significant higher timeframe levels, such as previous weekly highs/lows, monthly Order Blocks, or major Fibonacci retracement levels.

**Setup / Conditions:**
-   The weekly open price is established at the start of the trading week.
-   Price revisits the weekly open level during the week, often after an initial move away from it.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A clear reaction (rejection or acceptance) occurs at the weekly open, aligning with the higher timeframe bias.
-   A lower-timeframe Change of Character (CHOCH) or Break of Structure (BOS) confirms the continuation in the prevailing weekly bias from the weekly open.
-   Prefer candle close confirmation over wick-only confirmation for the structural shift.

**Execution:**
-   **Entry**: Enter on a lower-timeframe trigger (e.g., a confirmed CHOCH/BOS) after the weekly open has shown a clear reaction and polarity flip (if applicable).
-   **Stop Loss**: Place the stop loss beyond the swing high/low of the weekly open reaction, allowing for a small buffer.
-   **Targets**: Target weekly range expansion levels, such as the weekly high/low, or the next significant higher timeframe support/resistance level. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the weekly open is repeatedly crossed without clear acceptance or rejection, indicating a lack of conviction at this level.
-   Reject if price closes and accepts decisively beyond the weekly open in the opposite direction of the intended trade, invalidating the polarity.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 70. Killzone Liquidity Sweep Reversal

**Category:** Session / Liquidity / Reversal  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** This signal identifies a high-probability reversal setup that occurs within specific
high-liquidity trading windows, known as 'killzones' (e.g., London Open, New York Open). Price makes an aggressive move to sweep existing liquidity (e.g., previous session highs/lows, equal highs/lows) before rapidly reversing and initiating a move in the opposite direction. This is a classic institutional 'stop hunt' or 'liquidity grab' before the true directional move.

**Claude Analytical Focus:**
-   **Identify Active Killzone**: Claude should first confirm that the current trading period falls within an active killzone (e.g., London Open, New York Open). These are periods of high institutional activity and increased volatility.
-   **Detect Liquidity Sweep**: Look for a sharp, impulsive price movement that extends beyond a clear liquidity level. This sweep is often characterized by a quick spike or a large wick that penetrates the liquidity zone but fails to close and accept beyond it.
-   **Confirm Reclaim and Structural Shift**: The critical confirmation is when price quickly reclaims the swept level (closes back inside the previous range or below/above the swept high/low). This reclaim must then be followed by a clear Change of Character (CHOCH) or a Break of Structure (BOS) on a lower timeframe, indicating a definitive shift in market structure and direction.
-   **Contextualize with Higher Timeframe Levels**: The reliability of this signal is significantly enhanced when the liquidity sweep occurs at or near a higher timeframe key level (e.g., daily/weekly Order Block, FVG, previous daily high/low). This confluence suggests a stronger institutional intent.
-   **Volume Analysis**: Look for a spike in volume during the sweep, followed by a decrease as price reclaims, and then an increase again on the CHOCH/BOS, confirming the reversal.

**Setup / Conditions:**
-   The trading activity occurs within an active London or New York killzone.
-   Price sweeps a significant liquidity level (e.g., previous session high/low, equal highs/lows).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price sweeps the liquidity level, then quickly reclaims it (closes back inside the previous range or below/above the swept level).
-   A subsequent Change of Character (CHOCH) or Break of Structure (BOS) occurs in the opposite direction of the sweep.
-   Prefer candle close confirmation over wick-only confirmation for the reclaim and structural shift.

**Execution:**
-   **Entry**: Enter after the reclaim of the swept level and the confirmation of a CHOCH/BOS. A retest of the broken structure or the reclaimed level can offer a more precise entry.
-   **Stop Loss**: Place the stop loss beyond the extreme of the sweep (the highest point of the wick for a short, or the lowest point for a long), allowing for a small buffer.
-   **Targets**: Target the nearest liquidity pool, Market Profile level (e.g., VWAP, POC), or previous session high/low. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the signal occurs outside an active killzone, unless there is exceptional confluence with other strong higher timeframe levels.
-   Reject if there is no clear reclaim of the swept level within a limited number of candles, or if price closes and accepts decisively beyond the swept level, indicating a genuine breakout.
-   Reject if the CHOCH/BOS is not clear or lacks conviction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 71. Clean Breakout and Retest

**Category:** Breakout / Continuation  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Price decisively breaks through a significant support or resistance level, often after a period of consolidation, and then returns to retest the broken level. The retest confirms the level's new role (polarity flip) as support (if broken resistance) or resistance (if broken support), providing a high-probability entry for continuation in the direction of the breakout.

**Claude Analytical Focus:**
-   **Identify Significant Level**: Claude should first identify a clear, well-established support or resistance level. This could be a previous high/low, a swing point, a key psychological level, or a level from a higher timeframe.
-   **Detect Clean Breakout**: Look for a strong, impulsive candle (or series of candles) that closes decisively beyond the identified level. The breakout should be clean, with minimal wicking back into the previous range, indicating strong conviction from buyers or sellers. Increased volume often accompanies a valid breakout.
-   **Observe Consolidation (Optional but Preferred)**: Often, prior to a clean breakout, price will consolidate near the level, building energy for the move. Claude should note if this consolidation occurs, as it can add to the validity of the breakout.
-   **Confirm Retest and Polarity Flip**: The crucial part of this signal is the retest. Price should pull back to the broken level. The confirmation comes when this level holds as new support (if resistance was broken) or resistance (if support was broken), with price rejecting the level and showing signs of continuation (e.g., bullish engulfing for a long, bearish engulfing for a short).
-   **Contextualize Momentum**: The breakout should be driven by strong momentum. The retest phase often sees decreased volume, indicating a lack of opposing pressure, before momentum picks up again on the continuation.

**Setup / Conditions:**
-   A significant support or resistance level is present.
-   Price breaks cleanly through this level with a decisive candle close.
-   Often, consolidation occurs below (for a bullish breakout) or above (for a bearish breakout) the level prior to the breakout.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes decisively beyond the level, and a subsequent retest of the broken level holds as new support or resistance.
-   A continuation candle (e.g., bullish candle after a retest of broken resistance, bearish candle after a retest of broken support) confirms the entry.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the rejection of the retest of the broken level, after a continuation candle closes in the direction of the breakout.
-   **Stop Loss**: Place the stop loss back through the broken level, typically just beyond the retested swing low/high, allowing for a small buffer.
-   **Targets**: Target a measured move based on the previous consolidation range or the next significant support/resistance level. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the initial breakout is overextended and pushes directly into an opposing higher timeframe level (e.g., a bullish breakout into a strong daily resistance), increasing the risk of immediate reversal.
-   Reject if the breakout is only a wick, or if price quickly returns and accepts back inside the previous range after the breakout, indicating a false breakout.
-   Reject if the retest of the broken level fails to hold, and price breaks back through it.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 72. Fakeout Reversal

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** Price initially breaks out of a significant support or resistance level, appearing to initiate a new trend, but then quickly reverses and trades back within the previous range or beyond the broken level in the opposite direction. This traps traders who entered on the initial breakout, leading to a strong move in the opposite direction.

**Claude Analytical Focus:**
-   **Identify Significant Level**: Claude should identify a clear support or resistance level. This could be a range boundary, a previous swing high/low, an Order Block, or a key psychological level.
-   **Detect Initial Breakout**: Observe price breaking out of this level. This breakout might initially look convincing, often characterized by a strong candle, but it lacks sustained follow-through or is marked by a large wick that quickly retracts.
-   **Confirm Failure and Reclaim**: The critical element is the failure of the breakout. Price should quickly reverse and close back inside the original range or on the opposite side of the broken level. This "reclaim" indicates that the initial breakout was a fakeout, designed to trap early participants.
-   **Confirm Structural Shift**: A subsequent Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe in the opposite direction of the initial breakout confirms the reversal. This structural shift provides strong evidence that the market's true intent is contrary to the fakeout.
-   **Volume Analysis**: Often, the initial breakout might have a spike in volume, but the volume quickly diminishes as price reclaims the level, and then increases again on the reversal, confirming the shift in market participation.

**Setup / Conditions:**
-   Price breaks an obvious range boundary or a significant support/resistance level.
-   The breakout fails to gain acceptance beyond the level, often characterized by a large wick or a quick close back inside.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price closes back inside the original range or on the opposite side of the broken level after the initial breakout.
-   A subsequent Change of Character (CHOCH) or Break of Structure (BOS) occurs in the opposite direction of the initial breakout.
-   Prefer candle close confirmation over wick-only confirmation for the reclaim and structural shift.

**Execution:**
-   **Entry**: Enter after the failed breakout is confirmed by the reclaim and the subsequent CHOCH/BOS. A retest of the reclaimed level or broken structure can offer a more precise entry with reduced risk.
-   **Stop Loss**: Place the stop loss beyond the extreme of the fakeout (the highest point of the wick for a bearish fakeout, or the lowest point for a bullish fakeout), allowing for a small buffer.
-   **Targets**: Target the midpoint of the original range, the opposite side of the range, or the next significant liquidity level. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the initial breakout shows strong volume and sustained acceptance beyond the level, indicating a genuine breakout rather than a fakeout.
-   Reject if price does not quickly reclaim the level after the breakout, or if the CHOCH/BOS is not clear or lacks conviction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 73. Momentum Breakout Continuation

**Category:** Breakout / Continuation  
**Works with Gold/XAUUSD:** Medium  
**Works with Forex Majors:** Medium  
**Best Use:** Trend day

**Description:** Price breaks out of a significant level with extreme momentum and continues to trend in the breakout direction without a significant pullback or retest. This signal is characteristic of strong trend days where institutional participation is high, and price is unlikely to offer conventional retest entries.

**Claude Analytical Focus:**
-   **Identify High Volatility Trend Day**: Claude should first assess the overall market context. This signal is primarily valid during high-volatility trend days, often driven by significant news events or strong fundamental shifts. It is less reliable on normal, range-bound days.
-   **Detect Strong Displacement**: Look for a decisive breakout from a key level (e.g., previous session high/low, Order Block, FVG) characterized by large-bodied candles, high Average True Range (ATR), and a rapid move away from the broken level. The key is the *absence* of a clear retest or significant pullback.
-   **Confirm Lack of Opposing Levels**: Ensure there are no immediate, strong opposing higher timeframe support or resistance levels directly in the path of the breakout. Such levels could halt the momentum and lead to a reversal.
-   **Contextualize with Volume**: A momentum breakout should ideally be accompanied by a significant increase in volume, confirming strong institutional participation and conviction behind the move.
-   **Risk Assessment**: Recognize that entries on momentum breakouts are inherently higher risk due to the lack of a defined retest. Claude should prioritize risk management and only consider entries if the initial risk is small relative to the potential reward.

**Setup / Conditions:**
-   A significant level (support or resistance) is broken with extreme momentum and displacement.
-   The market is experiencing a high-volatility trend day.
-   There are no immediate, strong opposing higher timeframe levels in the direction of the breakout.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A strong candle close occurs decisively beyond the level, demonstrating significant displacement and continuation in the breakout direction.
-   The absence of a clear pullback or retest confirms the momentum-driven nature of the move.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter only if the initial risk (distance to stop loss) is small and the momentum is undeniable. Otherwise, it is often safer to wait for a potential, albeit shallow, pullback or to miss the trade. Chasing the price is generally discouraged.
-   **Stop Loss**: Place the stop loss below the breakout candle (for a long) or above (for a short), or below the nearest minor structural low/high that formed during the initial leg of the breakout. This should be a tight stop.
-   **Targets**: Target the next significant liquidity level or use a trailing stop loss strategy to capture extended moves. This signal is often about riding the trend rather than fixed targets.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject this signal on normal trading days where volatility is not exceptionally high, as it is a lower-quality setup in such conditions.
-   Reject if the breakout is immediately met by a strong opposing level, indicating potential exhaustion.
-   Reject if price shows signs of immediate reversal or a deep pullback after the breakout, invalidating the momentum continuation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 74. Compression Breakout

**Category:** Breakout / Continuation  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** Price consolidates within a tight, low-volatility range, often characterized by contracting Average True Range (ATR) and reduced price movement. This compression typically occurs before a major market event, such as a session open or high-impact news, and resolves with a sharp, impulsive breakout in one direction, leading to a sustained momentum move.

**Claude Analytical Focus:**
-   **Identify Periods of Compression**: Claude should actively scan for periods of significantly reduced volatility, indicated by a contracting ATR and price trading within a very tight range. This often precedes major liquidity events.
-   **Contextualize with Time and News**: Recognize that these compression periods are particularly potent when they occur just before the opening of a major trading session (e.g., London, New York) or prior to scheduled high-impact news releases. This suggests institutional accumulation or distribution before a directional move.
-   **Define Compression Boundaries**: Clearly identify the upper and lower boundaries of the tight compression range. These levels will serve as the breakout points.
-   **Detect Decisive Breakout**: Look for a strong, impulsive candle (or series of candles) that closes decisively outside the compression range. This breakout should be accompanied by a significant expansion in volatility and momentum, indicating a release of pent-up energy.
-   **Confirm Continuation**: The breakout should ideally lead to a sustained move in the direction of the break, often without an immediate deep pullback. Claude should prioritize breakouts that show strong follow-through.

**Setup / Conditions:**
-   Price exhibits tight range compression, with contracting ATR, often preceding an active trading session or a news event.
-   A clear, narrow horizontal range is established.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A strong, impulsive candle closes decisively outside the compression range, accompanied by an expansion in volatility.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the decisive close of the breakout candle, or on the first shallow pullback to the broken compression boundary. The entry should be in the direction of the breakout.
-   **Stop Loss**: Place the stop loss just inside the compression range, typically beyond the opposite side of the broken boundary, allowing for a small buffer.
-   **Targets**: Target a measured move based on a multiple of the compression height (e.g., 1x, 2x the height of the compressed range), or the next significant liquidity level/support/resistance zone. Use trailing stops to capture extended moves.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the breakout occurs directly into a major opposing Key Level Zone (KLZ), Value Area (VA), or other strong higher timeframe support/resistance level, as this increases the risk of a false breakout or immediate reversal.
-   Reject if the breakout lacks conviction (e.g., small-bodied candles, low volume) or if price quickly returns and accepts back inside the compression range.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 75. Range High False Breakout

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** Price initially breaks above a well-defined trading range's high, appearing to signal a bullish continuation, but then quickly reverses and closes back inside the range. This action traps early buyers who entered on the perceived breakout, leading to a strong bearish move as trapped buyers are forced to liquidate their positions.

**Claude Analytical Focus:**
-   **Identify Defined Range**: Claude should first identify a clear horizontal trading range with a well-defined upper boundary (resistance).
-   **Detect False Breakout**: Observe price pushing above the range high. The key is to look for signs that this breakout is not genuine: it might be a quick spike (a large wick) that immediately retracts, or a candle that closes above the range high but is quickly followed by a candle closing back inside the range.
-   **Confirm Re-entry and Reversal**: The critical confirmation is when price fails to sustain its position above the range high and closes back inside the original range. This re-entry, especially if followed by a bearish Change of Character (CHOCH) or a Break of Structure (BOS) on a lower timeframe, signals a high-probability bearish reversal.
-   **Contextualize Institutional Intent**: Understand that these false breakouts are often liquidity grabs or 'stop hunts' designed to trigger stop losses of short sellers and absorb buy orders before institutions initiate a move in the opposite direction. Claude should interpret the failure to hold above the range high and the subsequent structural shift as a strong indication of bearish intent.
-   **Volume Analysis**: Look for a spike in volume during the initial push above the range high, followed by a decrease as price re-enters the range, and then an increase again on the BOS/CHOCH, confirming the reversal.

**Setup / Conditions:**
-   A clear, defined trading range with an established range high (resistance) is present.
-   Price breaks above the range high but fails to gain acceptance above it.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price breaks above the range high, but then closes back inside the original range.
-   A subsequent bearish Change of Character (CHOCH) or Break of Structure (BOS) occurs, confirming the shift in market structure.
-   Prefer candle close confirmation over wick-only confirmation for the re-entry and structural shift.

**Execution:**
-   **Entry**: Enter short after the re-entry into the range and the confirmation of a bearish CHOCH/BOS. A retest of the broken range high (now acting as resistance) can offer a more precise entry.
-   **Stop Loss**: Place the stop loss above the false-break high (the highest point of the wick that pierced the range high), allowing for a small buffer.
-   **Targets**: Target the midpoint of the range, then the range low. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price closes and accepts decisively above the range high (e.g., two consecutive candle closes above the range high), indicating a genuine bullish breakout rather than a fakeout.
-   Reject if the re-entry into the range or the subsequent bearish CHOCH/BOS is not clear or lacks conviction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 76. Range Low False Breakout

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping

**Description:** Price initially breaks below a well-defined trading range's low, appearing to signal a bearish continuation, but then quickly reverses and closes back inside the range. This action traps early sellers who entered on the perceived breakdown, leading to a strong bullish move as trapped sellers are forced to liquidate their positions.

**Claude Analytical Focus:**
-   **Identify Defined Range**: Claude should first identify a clear horizontal trading range with a well-defined lower boundary (support).
-   **Detect False Breakout**: Observe price pushing below the range low. The key is to look for signs that this breakdown is not genuine: it might be a quick spike (a large wick) that immediately retracts, or a candle that closes below the range low but is quickly followed by a candle closing back inside the range.
-   **Confirm Re-entry and Reversal**: The critical confirmation is when price fails to sustain its position below the range low and closes back inside the original range. This re-entry, especially if followed by a bullish Change of Character (CHOCH) or a Break of Structure (BOS) on a lower timeframe, signals a high-probability bullish reversal.
-   **Contextualize Institutional Intent**: Understand that these false breakdowns are often liquidity grabs or 'stop hunts' designed to trigger stop losses of long buyers and absorb sell orders before institutions initiate a move in the opposite direction. Claude should interpret the failure to hold below the range low and the subsequent structural shift as a strong indication of bullish intent.
-   **Volume Analysis**: Look for a spike in volume during the initial push below the range low, followed by a decrease as price re-enters the range, and then an increase again on the BOS/CHOCH, confirming the reversal.

**Setup / Conditions:**
-   A clear, defined trading range with an established range low (support) is present.
-   Price breaks below the range low but fails to gain acceptance below it.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price breaks below the range low, but then closes back inside the original range.
-   A subsequent bullish Change of Character (CHOCH) or Break of Structure (BOS) occurs, confirming the shift in market structure.
-   Prefer candle close confirmation over wick-only confirmation for the re-entry and structural shift.

**Execution:**
-   **Entry**: Enter long after the re-entry into the range and the confirmation of a bullish CHOCH/BOS. A retest of the broken range low (now acting as support) can offer a more precise entry.
-   **Stop Loss**: Place the stop loss below the false-break low (the lowest point of the wick that pierced the range low), allowing for a small buffer.
-   **Targets**: Target the midpoint of the range, then the range high. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if price closes and accepts decisively below the range low (e.g., two consecutive candle closes below the range low), indicating a genuine bearish breakdown rather than a fakeout.
-   Reject if the re-entry into the range or the subsequent bullish CHOCH/BOS is not clear or lacks conviction.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 77. Key Level Zone (KLZ) Flip

**Category:** Breakout / Continuation  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** A significant Key Level Zone (KLZ) – an area of strong historical support or resistance – is decisively broken with strong momentum. Price then returns to retest this broken zone, which now flips its polarity (e.g., broken resistance becomes new support). This provides a high-probability entry for continuation in the direction of the breakout.

**Claude Analytical Focus:**
-   **Identify Key Level Zone (KLZ)**: Claude must first accurately identify a KLZ. This is not just a single price line, but a zone where price has historically shown strong reactions (multiple touches, strong reversals, or significant consolidation).
-   **Detect Decisive Breakout (Displacement)**: Observe price breaking through the KLZ. The breakout must be characterized by "displacement" – strong, large-bodied candles closing decisively beyond the zone, often accompanied by increased volume. A weak break or a wick through the zone is insufficient.
-   **Confirm Retest and Polarity Flip**: The core of this signal is the retest. Price should pull back to the broken KLZ. The confirmation occurs when the zone holds its new role (support if broken resistance, resistance if broken support). Look for clear rejection candles (e.g., pin bars, engulfing patterns) forming within or just at the edge of the KLZ during the retest.
-   **Contextualize Market Structure**: The KLZ flip should ideally align with a broader shift in market structure (e.g., a higher timeframe CHOCH or BOS) that supports the direction of the breakout.

**Setup / Conditions:**
-   A clear Key Level Zone (KLZ) is established.
-   Price breaks through the KLZ with strong displacement (momentum and volume).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price returns to retest the broken KLZ.
-   The KLZ holds as opposite polarity, confirmed by a clear rejection candle or a lower timeframe structural shift in the direction of the breakout.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the rejection of the retest at the flipped KLZ, after a confirmation candle closes in the direction of the breakout.
-   **Stop Loss**: Place the stop loss completely through the KLZ, allowing for a small buffer. If the KLZ fails to hold, the trade idea is invalidated.
-   **Targets**: Target the next significant KLZ, Value Area (VA) extreme, or major liquidity pool. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the initial breakout through the KLZ lacks displacement (e.g., small candles, low volume, or just a wick).
-   Reject if the retest fails to hold and price closes back through the KLZ, indicating a false breakout.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 78. Failed Retest Reversal

**Category:** Breakout / Fakeout  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** This signal occurs when price initially breaks through a significant support or resistance level, then attempts to retest this broken level, but the retest fails to hold. Instead of confirming the polarity flip, price quickly reverses and trades back through the retested level, indicating that the initial break was a fakeout or that the market is not ready to accept the new role of the level.

**Claude Analytical Focus:**
-   **Identify Broken Level**: Claude should first identify a clear, significant support or resistance level that has been decisively broken (e.g., with a strong candle close).
-   **Detect Retest Attempt**: Observe price returning to retest the broken level. This retest is a common occurrence after a breakout, where traders look for confirmation of the polarity flip.
-   **Confirm Retest Failure**: The crucial part of this signal is the *failure* of the retest. Instead of holding as new support (if broken resistance) or resistance (if broken support), price should quickly snap back through the retested level. This failure is often characterized by a strong candle closing back on the original side of the level, or a clear rejection that immediately reverses the price action.
-   **Contextualize with Market Structure**: A failed retest often leads to a strong move in the opposite direction, as traders who entered on the retest are trapped. Claude should look for a Change of Character (CHOCH) or Break of Structure (BOS) on a lower timeframe, confirming the reversal and the shift in market structure.
-   **Volume Analysis**: Volume might be low during the retest attempt, indicating a lack of conviction, and then spike as the retest fails and price reverses, confirming the strength of the opposing move.

**Setup / Conditions:**
-   A significant support or resistance level has been broken with initial displacement.
-   Price returns to retest the broken level.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The retest fails to hold, and price snaps back through the trigger level (the broken level) with a strong candle close back on the original side.
-   A subsequent Change of Character (CHOCH) or Break of Structure (BOS) occurs in the direction of the reversal.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter in the direction of the failure after the snapback and confirmation of the reversal (e.g., after a candle closes back through the level and a CHOCH/BOS occurs). A retest of the failed retest level can offer a more precise entry.
-   **Stop Loss**: Place the stop loss beyond the extreme of the failed retest (e.g., beyond the high of the failed retest for a short, or the low for a long), allowing for a small buffer.
-   **Targets**: Target the opposite side of the range from which the initial break occurred, or the VWAP/POC. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the retest actually holds for multiple candles, indicating that the level has successfully flipped polarity and the initial breakout was genuine.
-   Reject if the snapback is weak or lacks conviction, or if price consolidates around the retested level without a clear reversal.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 79. ATR Expansion Breakout

**Category:** Breakout / Continuation  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** This signal identifies a high-probability breakout opportunity following a period of extreme price compression and low volatility, often indicated by a low Average True Range (ATR). The breakout is characterized by a sudden and significant expansion of ATR, signaling the initiation of a strong directional move as price breaks out of its compressed range.

**Claude Analytical Focus:**
-   **Identify Price Compression (Low ATR)**: Claude should actively monitor for periods where the Average True Range (ATR) is at a significantly low percentile (e.g., lowest 20% over a defined lookback period), indicating extreme price compression and reduced volatility. This often manifests as tight, small-bodied candles within a narrow range.
-   **Define Compression Boundaries**: Clearly identify the upper and lower boundaries of the compressed price range. These levels represent critical breakout points.
-   **Contextualize with Time/Events**: Recognize that these compression periods are particularly potent when they occur before major market events (e.g., session opens, high-impact news releases) or after prolonged consolidation, as they represent pent-up energy.
-   **Detect ATR Expansion and Breakout**: The core of this signal is the sudden and decisive expansion of ATR, coupled with a strong candle closing beyond one of the compression boundaries. The breakout candle should be significantly larger than the average candles within the compression, indicating a surge in momentum and volume.
-   **Confirm Directional Move**: The breakout should lead to a sustained directional move. Claude should look for follow-through candles and a lack of immediate re-entry into the compressed range.

**Setup / Conditions:**
-   Price has been trading in a tight range with a significantly low Average True Range (ATR) percentile.
-   Clear upper and lower boundaries of the compressed range are identifiable.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A candle closes decisively beyond one of the compression boundaries.
-   The breakout candle exhibits a significant expansion in ATR (e.g., greater than a predefined ATR threshold or a multiple of the average ATR during compression).
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter on the first shallow pullback to the broken compression boundary (now acting as support/resistance) after the decisive breakout. If the breakout is extremely impulsive and offers no pullback, a low-risk entry on the breakout candle close might be considered, but with extreme caution.
-   **Stop Loss**: Place the stop loss just inside the original compression range, typically beyond the opposite side of the broken boundary, allowing for a small buffer.
-   **Targets**: Target a measured move based on a multiple of the compressed range height (e.g., 1x, 2x the height). Alternatively, target the next significant liquidity level or higher timeframe support/resistance zone. Use trailing stops to capture extended moves.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the ATR expansion and breakout occurs directly into an immediate, strong higher timeframe support or resistance level, as this increases the risk of a false breakout or immediate reversal.
-   Reject if the breakout lacks conviction (e.g., small-bodied candles, low volume) or if price quickly returns and accepts back inside the compression range after the initial breakout.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 80. News Impulse Continuation

**Category:** Breakout / Continuation  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Medium  
**Best Use:** News only

**Description:** This signal identifies opportunities to join a strong directional move initiated by a high-impact news event, but only after the initial volatile spike has subsided and price has completed a shallow, corrective pullback. It aims to capitalize on the sustained momentum that often follows significant economic data releases.

**Claude Analytical Focus:**
-   **Identify Scheduled High-Impact News**: Claude should be instructed to monitor economic calendars for scheduled high-impact news events relevant to XAUUSD or Forex Majors. This signal is strictly for news-driven moves.
-   **Analyze Initial Impulse**: Observe the immediate price reaction to the news release. Look for a clear, strong directional impulse (a large, fast candle or series of candles) that establishes a bias. Avoid trading during this initial, highly volatile phase.
-   **Detect Corrective Pullback**: After the initial impulse, look for a shallow, corrective pullback against the direction of the impulse. This pullback should ideally retrace to a Fibonacci level between 38.2% and 50% of the initial impulse leg. The pullback should be orderly, with decreasing momentum and smaller candles.
-   **Confirm Continuation**: The critical confirmation is when the pullback holds at the identified Fibonacci level or another key support/resistance, and price shows signs of resuming the original news-driven direction. This can be confirmed by a bullish/bearish engulfing candle, a pin bar, or a Break of Structure (BOS) on a lower timeframe in the direction of the impulse.
-   **Risk Management**: Emphasize that news trading carries higher risk due to increased volatility and potential for wider spreads. Claude should prioritize clear setups and manage risk accordingly.

**Setup / Conditions:**
-   A scheduled high-impact news event has occurred, generating a clear initial directional impulse.
-   Price then enters a corrective pullback, ideally retracing between 38.2% and 50% of the initial impulse.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The pullback holds at the 38.2% or 50% Fibonacci retracement level (or another key level).
-   A continuation Break of Structure (BOS) or a strong candle in the direction of the original impulse confirms the resumption of the trend.
-   Prefer candle close confirmation over wick-only confirmation.

**Execution:**
-   **Entry**: Enter after the pullback holds and the continuation is confirmed by a BOS or a strong candle close. **Never enter during the initial news spike.**
-   **Stop Loss**: Place the stop loss beyond the swing low/high of the pullback, allowing for a small buffer.
-   **Targets**: Target the extension of the news range (e.g., 1.272 or 1.618 Fibonacci extensions of the initial impulse) or the next significant liquidity level. Use trailing stops to capture extended moves.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if spread and/or slippage are abnormally high, making execution unsafe or the risk-reward unfavorable.
-   Reject if the news causes extreme whipsaw, with price moving sharply in both directions, indicating high uncertainty.
-   Reject if the pullback is too deep (e.g., retraces more than 61.8% of the impulse) or breaks the market structure established by the initial impulse, as this suggests a potential reversal rather than continuation.
-   Reject if the confirmation of continuation after the pullback is weak or absent.

## 81. Bullish Pin Bar Rejection

**Category:** Price Action Candle / Reversal  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Confirmation

**Description:** A bullish pin bar (also known as a hammer or dragonfly doji) is a single candlestick pattern characterized by a small body near the top of the candle and a long lower wick, with little or no upper wick. It signifies a strong rejection of lower prices, indicating that sellers attempted to push price down but buyers stepped in aggressively to push it back up, often signaling a potential bullish reversal or continuation from a support level.

**Claude Analytical Focus:**
-   **Identify Pin Bar Structure**: Claude should recognize a candle with a small body (open and close are close to each other) located in the upper portion of the candle's total range, and a lower wick that is significantly longer than the body (typically at least 2-3 times the length of the body). The upper wick should be very small or absent.
-   **Contextualize at Key Levels**: The effectiveness of a bullish pin bar is highly dependent on its location. Claude should prioritize pin bars that form at significant support levels, such as:
    -   Previous swing lows
    -   Value Area Low (VAL)
    -   Key Level Zones (KLZ)
    -   Previous Day Low (PDL)
    -   Lower VWAP bands
    -   Unmitigated Order Blocks or Fair Value Gaps acting as demand zones.
        A pin bar forming "in the middle of nowhere" (without confluence) should be disregarded.
-   **Confirm Rejection**: The long lower wick represents the rejection of lower prices. Claude should interpret this as buyers overcoming selling pressure at that specific level.
-   **Look for Follow-Through**: The pin bar itself is a signal, but confirmation is crucial. Claude should look for the subsequent candle to trade and ideally close above the high of the pin bar, indicating that buyers are indeed taking control and continuing to push prices higher.

**Setup / Conditions:**
-   A bullish pin bar forms, characterized by a small body near the high and a long lower wick.
-   The pin bar appears at a significant support level (e.g., support zone, VAL, KLZ, PDL, lower VWAP band, Order Block).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The candle immediately following the pin bar breaks and ideally closes above the high of the pin bar.
-   Prefer candle close confirmation over wick-only confirmation for the follow-through candle.

**Execution:**
-   **Entry**: Enter long on the break of the pin bar's high by the subsequent candle. A more conservative entry can be on the close of the confirmation candle above the pin bar high.
-   **Stop Loss**: Place the stop loss below the low of the pin bar, allowing for a small buffer to account for volatility.
-   **Targets**: Target the next significant resistance level, liquidity pool, or aim for a minimum 2R (risk-to-reward) target. Consider scaling out at intermediate levels.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the pin bar forms without clear confluence at a significant support level (i.e., "in the middle of nowhere").
-   Reject if the subsequent candle fails to break the pin bar's high or closes below the pin bar's low, indicating a lack of follow-through from buyers.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe, as these conditions can lead to false signals.
    """
## 82. Bearish Pin Bar Rejection

**Category:** Price Action Candle / Reversal  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Confirmation

**Description:** A bearish pin bar (also known as a shooting star or hanging man) is a single candlestick pattern characterized by a small body near the bottom of the candle and a long upper wick, with little or no lower wick. It signifies a strong rejection of higher prices, indicating that buyers attempted to push price up but sellers stepped in aggressively to push it back down, often signaling a potential bearish reversal or continuation from a resistance level.

**Claude Analytical Focus:**
-   **Identify Pin Bar Structure**: Claude should recognize a candle with a small body (open and close are close to each other) located in the lower portion of the candle's total range, and an upper wick that is significantly longer than the body (typically at least 2-3 times the length of the body). The lower wick should be very small or absent.
-   **Contextualize at Key Levels**: The effectiveness of a bearish pin bar is highly dependent on its location. Claude should prioritize pin bars that form at significant resistance levels, such as:
    -   Previous swing highs
    -   Value Area High (VAH)
    -   Key Level Zones (KLZ)
    -   Previous Day High (PDH)
    -   Upper VWAP bands
    -   Unmitigated Order Blocks or Fair Value Gaps acting as supply zones.
        A pin bar forming "in the middle of nowhere" (without confluence) should be disregarded.
-   **Confirm Rejection**: The long upper wick represents the rejection of higher prices. Claude should interpret this as sellers overcoming buying pressure at that specific level.
-   **Look for Follow-Through**: The pin bar itself is a signal, but confirmation is crucial. Claude should look for the subsequent candle to trade and ideally close below the low of the pin bar, indicating that sellers are indeed taking control and continuing to push prices lower.

**Setup / Conditions:**
-   A bearish pin bar forms, characterized by a small body near the low and a long upper wick.
-   The pin bar appears at a significant resistance level (e.g., resistance zone, VAH, KLZ, PDH, upper VWAP band, Order Block).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The candle immediately following the pin bar breaks and ideally closes below the low of the pin bar.
-   Prefer candle close confirmation over wick-only confirmation for the follow-through candle.

**Execution:**
-   **Entry**: Enter short on the break of the pin bar's low by the subsequent candle. A more conservative entry can be on the close of the confirmation candle below the pin bar low.
-   **Stop Loss**: Place the stop loss above the high of the pin bar, allowing for a small buffer to account for volatility.
-   **Targets**: Target the next significant support level, liquidity pool, or aim for a minimum 2R (risk-to-reward) target. Consider scaling out at intermediate levels.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the pin bar forms without clear confluence at a significant resistance level (i.e., "in the middle of nowhere").
-   Reject if the subsequent candle fails to break the pin bar's low or closes above the pin bar's high, indicating a lack of follow-through from sellers.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe, as these conditions can lead to false signals.
    """
    """
## 83. Bullish Engulfing Pattern

**Category:** Price Action Candle / Reversal  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Confirmation

**Description:** A bullish engulfing pattern is a two-candle reversal pattern that typically appears at the bottom of a downtrend or at a significant support level. The first candle is a small bearish candle, which is completely engulfed by a larger bullish second candle. This pattern signifies a strong shift in momentum from sellers to buyers, indicating that buyers have overcome selling pressure and are now in control, often preceding a bullish move.

**Claude Analytical Focus:**
-   **Identify Two-Candle Pattern**: Claude should look for a sequence of two candles where the second bullish candle's body completely covers the body of the preceding smaller bearish candle. Ideally, the second candle's high should also be higher than the first, and its low lower than the first, fully engulfing the previous candle's range.
-   **Contextualize at Key Support Levels**: The reliability of a bullish engulfing pattern is significantly enhanced when it forms at a strong support level. Claude should prioritize patterns that occur at:
    -   Previous swing lows or established support zones
    -   Value Area Low (VAL)
    -   Key Level Zones (KLZ)
    -   Previous Day Low (PDL)
    -   Lower VWAP bands
    -   Unmitigated Order Blocks or Fair Value Gaps acting as demand zones.
        An engulfing pattern in isolation, without confluence, should be treated with caution.
-   **Confirm Momentum Shift**: The engulfing nature of the second candle indicates a powerful shift in market sentiment. Claude should interpret this as a strong rejection of lower prices and a clear signal that buyers have stepped in aggressively.
-   **Look for Follow-Through**: While the pattern itself is a strong signal, confirmation is vital. Claude should look for the subsequent candle to continue the bullish momentum, ideally closing higher than the engulfing candle, to validate the reversal.

**Setup / Conditions:**
-   A small bearish candle is followed by a larger bullish candle whose body completely engulfs the body of the first candle.
-   The pattern forms at a significant support level or after a liquidity sweep to the downside.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The bullish engulfing candle closes above the high of the preceding bearish candle, confirming the engulfment.
-   Prefer candle close confirmation over wick-only confirmation for the engulfing candle.

**Execution:**
-   **Entry**: Enter long on the close of the bullish engulfing candle, or on a retest of the midpoint or low of the engulfing candle if it offers a better risk-reward ratio. A more conservative entry can be on the break of the engulfing candle's high by the subsequent candle.
-   **Stop Loss**: Place the stop loss below the low of the engulfing candle, allowing for a small buffer.
-   **Targets**: Target the next significant resistance level, liquidity pool, or aim for a minimum 2R (risk-to-reward) target. Consider scaling out at intermediate levels.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the bullish engulfing pattern occurs late in a large rally, as it may indicate exhaustion rather than the start of a new move.
-   Reject if the pattern forms without clear confluence at a significant support level.
-   Reject if the subsequent candle fails to continue the bullish momentum or closes below the engulfing candle's low.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 84. Bearish Engulfing Pattern

**Category:** Price Action Candle / Reversal  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Confirmation

**Description:** A bearish engulfing pattern is a two-candle reversal pattern that typically appears at the top of an uptrend or at a significant resistance level. The first candle is a small bullish candle, which is completely engulfed by a larger bearish second candle. This pattern signifies a strong shift in momentum from buyers to sellers, indicating that sellers have overcome buying pressure and are now in control, often preceding a bearish move.

**Claude Analytical Focus:**
-   **Identify Two-Candle Pattern**: Claude should look for a sequence of two candles where the second bearish candle's body completely covers the body of the preceding smaller bullish candle. Ideally, the second candle's high should also be higher than the first, and its low lower than the first, fully engulfing the previous candle's range.
-   **Contextualize at Key Resistance Levels**: The reliability of a bearish engulfing pattern is significantly enhanced when it forms at a strong resistance level. Claude should prioritize patterns that occur at:
    -   Previous swing highs or established resistance zones
    -   Value Area High (VAH)
    -   Key Level Zones (KLZ)
    -   Previous Day High (PDH)
    -   Upper VWAP bands
    -   Unmitigated Order Blocks or Fair Value Gaps acting as supply zones.
        An engulfing pattern in isolation, without confluence, should be treated with caution.
-   **Confirm Momentum Shift**: The engulfing nature of the second candle indicates a powerful shift in market sentiment. Claude should interpret this as a strong rejection of higher prices and a clear signal that sellers have stepped in aggressively.
-   **Look for Follow-Through**: While the pattern itself is a strong signal, confirmation is vital. Claude should look for the subsequent candle to continue the bearish momentum, ideally closing lower than the engulfing candle, to validate the reversal.

**Setup / Conditions:**
-   A small bullish candle is followed by a larger bearish candle whose body completely engulfs the body of the first candle.
-   The pattern forms at a significant resistance level or after a liquidity sweep to the upside.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The bearish engulfing candle closes below the low of the preceding bullish candle, confirming the engulfment.
-   Prefer candle close confirmation over wick-only confirmation for the engulfing candle.

**Execution:**
-   **Entry**: Enter short on the close of the bearish engulfing candle, or on a retest of the midpoint or high of the engulfing candle if it offers a better risk-reward ratio. A more conservative entry can be on the break of the engulfing candle's low by the subsequent candle.
-   **Stop Loss**: Place the stop loss above the high of the engulfing candle, allowing for a small buffer.
-   **Targets**: Target the next significant support level, liquidity pool, or aim for a minimum 2R (risk-to-reward) target. Consider scaling out at intermediate levels.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the bearish engulfing pattern occurs late in a large selloff, as it may indicate exhaustion rather than the start of a new move.
-   Reject if the pattern forms without clear confluence at a significant resistance level.
-   Reject if the subsequent candle fails to continue the bearish momentum or closes above the engulfing candle's high.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 85. Inside Bar Breakout

**Category:** Price Action / Continuation  
**Works with Gold/XAUUSD:** Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Intraday

**Description:** An inside bar is a two-candle pattern where the second candle (the "inside bar") has its entire price range (high and low) contained within the range of the preceding candle (the "mother bar"). This pattern signifies a period of contraction, indecision, or consolidation, often preceding a strong directional move as price breaks out of the mother bar's range, indicating a continuation of the prior trend or the start of a new one.

**Claude Analytical Focus:**
-   **Identify Mother and Inside Bar**: Claude should accurately identify the mother candle (the larger candle) and the subsequent inside bar, ensuring the inside bar's high is lower than the mother bar's high, and its low is higher than the mother bar's low.
-   **Recognize Volatility Contraction**: Interpret the inside bar as a period of reduced volatility and market indecision. This compression often builds energy for a subsequent expansion.
-   **Contextualize Formation**: The significance of an inside bar is amplified when it forms at key levels (e.g., support/resistance, Order Blocks, FVGs) or after a strong impulsive move, suggesting a pause before continuation.
-   **Detect Breakout Direction**: Observe the direction of the breakout from the mother bar's range. A close above the mother bar's high suggests bullish continuation, while a close below the mother bar's low suggests bearish continuation.
-   **Volume Analysis**: Typically, volume tends to decrease during the formation of the inside bar, reflecting indecision. A valid breakout should ideally be accompanied by an increase in volume, confirming renewed conviction.

**Setup / Conditions:**
-   A "mother candle" forms, followed by an "inside bar" whose entire range (high and low) is contained within the mother candle's range.
-   The pattern often forms after a directional move or at a significant support/resistance level.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A subsequent candle closes decisively beyond the high or low of the mother candle, indicating the direction of the breakout.
-   Prefer candle close confirmation over wick-only confirmation for the breakout.

**Execution:**
-   **Entry**: Enter on the close of the breakout candle beyond the mother bar's high/low, or on a retest of the broken mother bar's high/low (now acting as support/resistance) if it offers a better risk-reward ratio.
-   **Stop Loss**: Place the stop loss on the opposite side of the mother candle's range, or just beyond the inside bar's extreme, allowing for a small buffer.
-   **Targets**: Target a measured move based on the height of the mother candle projected from the breakout point, or the next significant liquidity level/support/resistance zone. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the inside bar forms in a choppy, mid-range environment without clear alignment to a prevailing trend or key level.
-   Reject if the breakout is weak (e.g., small-bodied candle, low volume) or if price quickly returns and accepts back inside the mother bar's range after the breakout.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 86. Outside Bar Reversal

**Category:** Price Action Candle / Reversal  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Scalping

**Description:** An outside bar (also known as an engulfing bar, but distinct from the two-candle engulfing pattern in that it encompasses the previous candle's entire range within a single candle) is a single candlestick pattern where the current candle's high is higher than the previous candle's high, and its low is lower than the previous candle's low. This signifies a period of extreme volatility and often a battle between buyers and sellers, where one side ultimately gains control, leading to a strong directional close. When this occurs at a key level, it can signal a powerful reversal.

**Claude Analytical Focus:**
-   **Identify Outside Bar Structure**: Claude should detect a candle whose high is greater than the previous candle's high, and whose low is less than the previous candle's low. This indicates that the current candle has completely encompassed the range of the prior candle.
-   **Contextualize at Key Levels**: The significance of an outside bar is amplified when it forms at a critical support or resistance level, or after a liquidity hunt. Claude should prioritize patterns that occur at:
    -   Previous swing highs/lows
    -   Key Level Zones (KLZ)
    -   Value Areas (VAH/VAL)
    -   VWAP bands
    -   Unmitigated Order Blocks or Fair Value Gaps.
-   **Analyze Closing Price**: The most crucial aspect for Claude is the closing price of the outside bar. A strong close near its high (for a bullish outside bar) or near its low (for a bearish outside bar) indicates which side won the battle and suggests the likely direction of the next move.
-   **Confirm with Subsequent Candle**: While the outside bar itself is a strong signal, confirmation from the subsequent candle is vital. Claude should look for the next candle to continue in the direction of the outside bar's close, ideally breaking its high (for bullish) or low (for bearish).
-   **Volume Analysis**: High volume accompanying the outside bar can add to its validity, confirming strong participation during the volatility.

**Setup / Conditions:**
-   A candle forms with a high greater than the previous candle's high and a low less than the previous candle's low.
-   The outside bar forms at a key structural level or after a clear liquidity hunt.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The outside bar closes strongly in one direction (e.g., near its high for bullish, near its low for bearish).
-   The subsequent candle confirms the direction by breaking the high (for bullish) or low (for bearish) of the outside bar.
-   Prefer candle close confirmation over wick-only confirmation for the confirming candle.

**Execution:**
-   **Entry**: Enter on the break of the outside bar's close direction by the subsequent candle. For example, for a bullish outside bar, enter long when the next candle breaks above the outside bar's high.
-   **Stop Loss**: Place the stop loss beyond the extreme of the outside bar (e.g., below the low for a long, above the high for a short), allowing for a small buffer.
-   **Targets**: Target the VWAP, Point of Control (POC), or a minimum 2R (risk-to-reward) target. Consider scaling out at intermediate liquidity levels.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the range of the outside bar is excessively large, making the stop loss too wide and resulting in an unfavorable risk-reward ratio.
-   Reject if the outside bar forms in the middle of a range without clear confluence at a key level.
-   Reject if the subsequent candle fails to confirm the direction or reverses against the outside bar's close.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 87. Full-Body Candle Continuation

**Category:** Price Action / Momentum  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Good  
**Best Use:** Momentum

**Description:** A full-body candle (often referred to as a Marubozu or a strong directional candle) is characterized by a large body and very small or non-existent wicks. It signifies strong, unidirectional momentum and complete control by either buyers or sellers, indicating a high probability of continuation in the direction of the candle. This signal is particularly powerful when it forms after a significant market event like a breakout or a Break of Structure (BOS).

**Claude Analytical Focus:**
-   **Identify Full-Body Candle Structure**: Claude should detect candles where the body constitutes a very high percentage (e.g., >80%) of the total candle range, with minimal upper and lower wicks. This visual characteristic is key to identifying strong conviction.
-   **Contextualize Formation**: The significance of a full-body candle is amplified when it forms in specific contexts:
    -   **After a Breakout**: Following a decisive break of a key support or resistance level.
    -   **After a Break of Structure (BOS)**: Confirming a shift in market structure.
    -   **At the Start of a New Trend**: Indicating strong initiation of a new directional move.
    -   **Away from Opposing Levels**: Ideally, the candle should not close directly into a major opposing higher timeframe level, as this could lead to immediate rejection.
-   **Interpret Strong Control**: Claude should interpret the full-body nature as a clear indication that one side (buyers for bullish, sellers for bearish) has overwhelming control, with minimal opposition during the candle's formation.
-   **Look for Shallow Pullback**: For entry, Claude should look for a shallow, corrective pullback that respects the midpoint of the full-body candle or a key level within its range. This pullback indicates a brief pause before continuation.

**Setup / Conditions:**
-   A candle forms with a large body and very small or no wicks, indicating strong directional control.
-   This candle appears after a significant market event such as a breakout or a Break of Structure (BOS).
-   The candle should ideally not close directly into a major opposing higher timeframe level.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A shallow pullback occurs, holding the midpoint of the full-body candle or a key level within its range.
-   Confirmation comes from a subsequent continuation candle or a lower timeframe structural shift in the direction of the full-body candle.
-   Prefer candle close confirmation over wick-only confirmation for the continuation.

**Execution:**
-   **Entry**: Enter on the continuation after the midpoint retest holds, or on the break of the full-body candle's high (for bullish) or low (for bearish) by a subsequent candle. A more aggressive entry might be on the close of the full-body candle itself if the risk is manageable and the context is extremely strong.
-   **Stop Loss**: Place the stop loss behind the candle's midpoint or the opposite extreme of the full-body candle (e.g., below the low for a long, above the high for a short), allowing for a small buffer.
-   **Targets**: Target the next significant liquidity zone, a measured move based on the candle's range, or use trailing stops to capture extended moves. Aim for a minimum 2R target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the full-body candle closes directly into a major opposing higher timeframe support or resistance level, as this significantly increases the risk of immediate reversal.
-   Reject if the subsequent pullback is too deep (e.g., breaks below the midpoint of the full-body candle and fails to recover) or invalidates the candle's strength by closing on the opposite side.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 88. Doji Indecision at Key Level

**Category:** Price Action Candle / Indecision  
**Works with Gold/XAUUSD:** Medium  
**Works with Forex Majors:** Medium  
**Best Use:** Warning / Confirmation

**Description:** A Doji candlestick is characterized by an open and close price that are virtually equal, resulting in a very small or non-existent body. It often has upper and lower wicks of varying lengths. A Doji signifies market indecision, where buyers and sellers are in a state of equilibrium. When a Doji forms at a significant key level (support, resistance, supply, demand), it acts as a warning sign that the current trend might be losing momentum or that a reversal is imminent. It is not a standalone trade signal but requires confirmation from subsequent price action.

**Claude Analytical Focus:**
-   **Identify Doji Structure**: Claude should detect candles where the open and close prices are very close, resulting in a tiny body. The length of the wicks can vary, but the small body is the defining characteristic.
-   **Contextualize at Key Levels**: The significance of a Doji is entirely dependent on its location. Claude should prioritize Dojis that form at well-defined key levels, such as:
    -   Strong support or resistance zones
    -   Previous swing highs/lows
    -   Order Blocks or Fair Value Gaps
    -   Value Area High/Low (VAH/VAL)
    -   VWAP bands
        A Doji forming in the middle of a trend or range, without confluence, should be considered insignificant.
-   **Interpret Indecision**: Understand that a Doji indicates a temporary balance between buying and selling pressure. It suggests that the market is pausing and deciding its next move, rather than showing strong conviction in either direction.
-   **Wait for Confirmation**: Claude should be instructed that a Doji alone is not an entry signal. It is a precursor to a potential move. The actual signal comes from the subsequent candle breaking and closing decisively above the Doji's high (for bullish confirmation) or below its low (for bearish confirmation), aligning with the prevailing market context or a potential reversal.

**Setup / Conditions:**
-   A Doji candlestick forms, indicating market indecision.
-   The Doji appears at a significant key level (e.g., support, resistance, supply/demand zone, Order Block).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The trigger is the subsequent candle breaking and closing decisively beyond the high or low of the Doji, in the direction aligned with the market context (e.g., a bullish close above the Doji high at support, or a bearish close below the Doji low at resistance).
-   Prefer candle close confirmation over wick-only confirmation for the breakout candle.

**Execution:**
-   **Entry**: Enter only after the confirmation break of the Doji's high or low by a subsequent candle. A retest of the broken Doji extreme can offer a more precise entry.
-   **Stop Loss**: Place the stop loss on the opposite side of the Doji's extreme (e.g., below the Doji low for a long entry, above the Doji high for a short entry), allowing for a small buffer.
-   **Targets**: Target the next significant support/resistance level or liquidity zone. Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject standalone Doji signals that do not form at a significant key level or lack subsequent confirmation.
-   Reject if price chops through the Doji's range without a clear directional break and close.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 89. Wick Rejection with Break of Structure

**Category:** Price Action / Reversal  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Entry trigger

**Description:** This signal identifies a high-probability reversal or continuation setup where price aggressively tests a significant key level or liquidity zone, forms a strong rejection wick, and then follows through with a clear Break of Structure (BOS) or Change of Character (CHOCH) in the opposite direction. The initial wick signifies a failed attempt to push price beyond the level, and the subsequent structural break confirms that the opposing force has taken control.

**Claude Analytical Focus:**
-   **Identify Key Level or Liquidity Zone**: Claude should first accurately identify a significant key level (e.g., support/resistance, Order Block, Fair Value Gap, previous session high/low) or a liquidity zone that price is interacting with.
-   **Detect Strong Rejection Wick**: Look for a candle that penetrates the key level or liquidity zone with a long wick, but then closes back away from the extreme of that wick, often with a small body. This indicates a strong rejection of prices beyond that level, suggesting that orders were filled and price was pushed back by the opposing side.
-   **Confirm Break of Structure (BOS) / Change of Character (CHOCH)**: The rejection wick alone is a warning, but the critical confirmation is a subsequent Break of Structure (BOS) or Change of Character (CHOCH) on the current or a lower timeframe. This means that price has broken a previous swing high (for a bullish reversal) or swing low (for a bearish reversal), confirming a shift in market control and direction.
-   **Contextualize with Higher Timeframe Bias**: This signal is most potent when the rejection and subsequent structural break align with the higher timeframe bias. For example, a bullish wick rejection at a daily demand zone followed by a BOS on the 15-minute chart is a strong setup.
-   **Volume Analysis**: Observe volume during the wick formation and the subsequent BOS. A spike in volume during the rejection, followed by sustained volume on the BOS, can add confluence.

**Setup / Conditions:**
-   Price reaches a significant key level or sweeps a liquidity zone.
-   A strong rejection wick forms, indicating a failed attempt to sustain price beyond the level.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A clear rejection wick forms at the key level.
-   This is immediately followed by a Break of Structure (BOS) or Change of Character (CHOCH) in the opposite direction of the wick's penetration.
-   Prefer candle close confirmation over wick-only confirmation for the BOS/CHOCH.

**Execution:**
-   **Entry**: Enter after the confirmation of the BOS/CHOCH. A retest of the broken structure or the level from which the BOS occurred can offer a more precise entry with reduced risk.
-   **Stop Loss**: Place the stop loss beyond the extreme of the rejection wick (e.g., below the low of the wick for a long, above the high for a short), allowing for a small buffer.
-   **Targets**: Target the next significant liquidity pool, Market Profile level (e.g., VWAP, POC), or higher timeframe support/resistance. Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the subsequent Break of Structure (BOS) or Change of Character (CHOCH) does not occur, or is weak and lacks conviction.
-   Reject if the rejection wick is not significant or if price quickly returns to trade beyond the wick's extreme.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 90. Three-Bar Reversal

**Category:** Price Action Candle / Reversal  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Very Good  
**Best Use:** Entry trigger

**Description:** The Three-Bar Reversal is a powerful candlestick pattern indicating a potential shift in market direction after an extended price move into a significant key level. It consists of three distinct candles: an exhaustion candle, a reversal candle, and a confirmation candle. This sequence demonstrates a clear transition from one dominant force to another, signaling a high-probability reversal.

**Claude Analytical Focus:**
-   **Identify Extended Move into Key Level**: Claude should first confirm that price has undergone an extended, often impulsive, move into a significant key level. This could be a supply/demand zone, an Order Block, a Fair Value Gap, a previous swing high/low, or a major Fibonacci extension level. The longer the preceding move, the more potent the reversal.
-   **Detect Exhaustion Candle**: The first candle should be a large-bodied candle in the direction of the prior trend, indicating a final push by the dominant side. This candle often has high volume, suggesting a climax of the move.
-   **Identify Reversal Candle**: The second candle is crucial. It should show signs of indecision or rejection of the extreme reached by the exhaustion candle. This could manifest as a Doji, a pin bar (hammer/shooting star), or a small-bodied candle with a long wick against the prior trend. Its close should ideally be within the range of the exhaustion candle, or even slightly against it.
-   **Confirm with Confirmation Candle**: The third candle provides the definitive signal. It must be a strong, large-bodied candle that closes decisively in the opposite direction of the prior trend. For a bullish reversal, it would be a strong bullish candle closing above the high of the reversal candle. For a bearish reversal, it would be a strong bearish candle closing below the low of the reversal candle. This candle confirms that the new dominant force has taken control and broken minor market structure.
-   **Volume Analysis**: Claude should analyze volume across the three candles. High volume on the exhaustion candle, potentially decreasing on the reversal candle, and then increasing again on the confirmation candle, adds significant confluence to the pattern.

**Setup / Conditions:**
-   Price has made an extended move into a significant key level (e.g., supply/demand, Order Block, VAH/VAL, previous swing high/low).
-   The pattern consists of three candles: an exhaustion candle, followed by a reversal candle, and then a confirmation candle.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The third (confirmation) candle closes decisively in the opposite direction of the prior trend, ideally breaking a minor structural point (e.g., the high of the reversal candle for a bullish reversal, or the low for a bearish reversal).
-   Prefer candle close confirmation over wick-only confirmation for the third candle.

**Execution:**
-   **Entry**: Enter on the close of the third (confirmation) candle, or on a shallow retest of the confirmation candle's midpoint or the broken structural level, if it offers a better risk-reward ratio.
-   **Stop Loss**: Place the stop loss beyond the extreme of the entire three-bar pattern (e.g., below the low of the exhaustion candle for a bullish reversal, or above the high for a bearish reversal), allowing for a small buffer.
-   **Targets**: Target the VWAP, Point of Control (POC), or the next significant liquidity level/support/resistance zone. Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the pattern does not form at a significant key level, as its predictive power is greatly diminished in the middle of a range.
-   Reject if the confirmation candle is weak, lacks conviction, or fails to close decisively in the new direction.
-   Reject if price quickly returns and accepts back into the range of the exhaustion candle after the confirmation.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 91. Break of Structure (BOS) - Bullish

**Category:** Trend / Structure / Continuation  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Structure / Confirmation

**Description:** A Bullish Break of Structure (BOS) occurs when price decisively breaks and closes above a previously confirmed swing high within an uptrend. This action signifies that buyers are in control, the current bullish trend is continuing, and new higher highs are likely to be formed. It is a fundamental concept in Smart Money Concepts (SMC) and ICT methodologies, indicating a continuation of the market's internal structure.

**Claude Analytical Focus:**
-   **Identify Confirmed Swing High**: Claude should first accurately identify a confirmed swing high. A swing high is typically a candle with at least two lower highs on either side. The significance of the swing high increases if it was formed after a significant move or acted as resistance previously.
-   **Detect Decisive Break**: Look for a strong, impulsive candle (or series of candles) that closes decisively *above* the confirmed swing high. A "decisive close" means the candle body should be clearly above the previous swing high, not just a wick. This indicates strong buying pressure and acceptance of higher prices.
-   **Distinguish from Liquidity Sweep**: Claude must differentiate a genuine BOS from a liquidity sweep (where price wicks above a high but closes back below it). A true BOS requires a candle *close* above the high.
-   **Contextualize with Higher Timeframe Trend**: A bullish BOS is most reliable when it aligns with the higher timeframe trend. If the higher timeframe is also bullish, the probability of continuation after a BOS increases significantly.
-   **Volume Analysis**: A strong BOS is often accompanied by an increase in buying volume, confirming the conviction behind the breakout.

**Setup / Conditions:**
-   A clear, confirmed swing high is established within an existing or developing uptrend.
-   Price approaches this swing high with momentum.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A candle closes decisively above the previously confirmed swing high.
-   Prefer candle close confirmation over wick-only confirmation. A wick-only break is considered a liquidity sweep, not a BOS.

**Execution:**
-   **Entry**: The BOS itself is primarily a confirmation of trend continuation. Entry is typically sought on a subsequent pullback to a refined demand zone (e.g., Order Block, Fair Value Gap) that was created by the impulsive move that caused the BOS, or to the broken swing high (now acting as support).
-   **Stop Loss**: Place the stop loss below the low of the pullback that follows the BOS, or below the demand zone from which the entry was taken, allowing for a small buffer.
-   **Targets**: Target the next significant swing high, liquidity pool, or higher timeframe resistance level. Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the break of the swing high is only a wick (a liquidity sweep) and not a decisive candle close.
-   Reject if price immediately reverses and closes back below the broken swing high after the BOS, indicating a potential false breakout.
-   Reject if the subsequent pullback breaks below the low that initiated the BOS, invalidating the bullish structure.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 92. Break of Structure (BOS) - Bearish

**Category:** Trend / Structure / Continuation  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Structure / Confirmation

**Description:** A Bearish Break of Structure (BOS) occurs when price decisively breaks and closes below a previously confirmed swing low within a downtrend. This action signifies that sellers are in control, the current bearish trend is continuing, and new lower lows are likely to be formed. It is a fundamental concept in Smart Money Concepts (SMC) and ICT methodologies, indicating a continuation of the market's internal structure.

**Claude Analytical Focus:**
-   **Identify Confirmed Swing Low**: Claude should first accurately identify a confirmed swing low. A swing low is typically a candle with at least two higher lows on either side. The significance of the swing low increases if it was formed after a significant move or acted as support previously.
-   **Detect Decisive Break**: Look for a strong, impulsive candle (or series of candles) that closes decisively *below* the confirmed swing low. A "decisive close" means the candle body should be clearly below the previous swing low, not just a wick. This indicates strong selling pressure and acceptance of lower prices.
-   **Distinguish from Liquidity Sweep**: Claude must differentiate a genuine BOS from a liquidity sweep (where price wicks below a low but closes back above it). A true BOS requires a candle *close* below the low.
-   **Contextualize with Higher Timeframe Trend**: A bearish BOS is most reliable when it aligns with the higher timeframe trend. If the higher timeframe is also bearish, the probability of continuation after a BOS increases significantly.
-   **Volume Analysis**: A strong BOS is often accompanied by an increase in selling volume, confirming the conviction behind the breakdown.

**Setup / Conditions:**
-   A clear, confirmed swing low is established within an existing or developing downtrend.
-   Price approaches this swing low with momentum.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A candle closes decisively below the previously confirmed swing low.
-   Prefer candle close confirmation over wick-only confirmation. A wick-only break is considered a liquidity sweep, not a BOS.

**Execution:**
-   **Entry**: The BOS itself is primarily a confirmation of trend continuation. Entry is typically sought on a subsequent pullback to a refined supply zone (e.g., Order Block, Fair Value Gap) that was created by the impulsive move that caused the BOS, or to the broken swing low (now acting as resistance).
-   **Stop Loss**: Place the stop loss above the high of the pullback that follows the BOS, or above the supply zone from which the entry was taken, allowing for a small buffer.
-   **Targets**: Target the next significant swing low, liquidity pool, or higher timeframe support level. Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the break of the swing low is only a wick (a liquidity sweep) and not a decisive candle close.
-   Reject if price immediately reverses and closes back above the broken swing low after the BOS, indicating a potential false breakdown.
-   Reject if the subsequent pullback breaks above the high that initiated the BOS, invalidating the bearish structure.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 93. Change of Character (CHOCH) - Bullish

**Category:** Trend / Structure / Reversal  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Reversal

**Description:** A Bullish Change of Character (CHOCH) is a critical early signal of a potential trend reversal from bearish to bullish. It occurs when, after a sequence of lower lows (LL) and lower highs (LH) indicative of a downtrend, price breaks above the most recent lower high. This action signifies a shift in market control from sellers to buyers, indicating that the bearish structure is weakening and a new bullish trend may be emerging. It is a foundational concept in Smart Money Concepts (SMC) and ICT methodologies for identifying early reversal points.

**Claude Analytical Focus:**
-   **Identify Preceding Bearish Structure**: Claude should first confirm that the market is in a clear downtrend, characterized by the consistent formation of lower lows (LL) and lower highs (LH). This establishes the context for a potential reversal.
-   **Identify Most Recent Lower High**: Pinpoint the most recent lower high that maintained the bearish market structure. This is the critical level that, if broken, will signal a change in character.
-   **Detect Decisive Break**: Look for a strong, impulsive candle (or series of candles) that closes decisively *above* the most recent lower high. A "decisive close" means the candle body should be clearly above the previous lower high, not just a wick. This indicates strong buying pressure and acceptance of higher prices, signaling that buyers have taken control.
-   **Distinguish from Liquidity Sweep**: Claude must differentiate a genuine CHOCH from a liquidity sweep (where price wicks above a lower high but closes back below it). A true CHOCH requires a candle *close* above the lower high.
-   **Contextualize with Higher Timeframe Demand**: The reliability of a bullish CHOCH is significantly enhanced when it occurs at or near a higher timeframe demand zone, Order Block, Fair Value Gap, or a significant support level. This confluence suggests institutional interest in reversing the price.
-   **Volume Analysis**: A strong CHOCH is often accompanied by an increase in buying volume, confirming the conviction behind the structural shift.

**Setup / Conditions:**
-   The market is in a clear downtrend, making lower lows and lower highs.
-   Price approaches the most recent lower high.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price breaks and closes decisively above the most recent lower high.
-   Prefer candle close confirmation over wick-only confirmation. A wick-only break is considered a liquidity sweep, not a CHOCH.

**Execution:**
-   **Entry**: The CHOCH itself is a reversal signal. Entry is typically sought on a subsequent pullback to a refined demand zone (e.g., Order Block, Fair Value Gap) that was created by the impulsive move that caused the CHOCH, or to the broken lower high (now acting as support).
-   **Stop Loss**: Place the stop loss below the origin of the CHOCH (the low that preceded the break of the lower high) or below the demand zone from which the entry was taken, allowing for a small buffer.
-   **Targets**: Target the next significant swing high, Value Area High (VAH), VWAP, or higher timeframe resistance level. Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the break of the lower high is only a wick (a liquidity sweep) and not a decisive candle close.
-   Reject if there is no significant displacement (strong, large-bodied candles) after the CHOCH, indicating a weak shift in momentum.
-   Reject if price immediately reverses and breaks below the low that initiated the CHOCH, invalidating the bullish structural shift.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
## 94. Change of Character (CHOCH) - Bearish

**Category:** Trend / Structure / Reversal  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Reversal

**Description:** A Bearish Change of Character (CHOCH) is a critical early signal of a potential trend reversal from bullish to bearish. It occurs when, after a sequence of higher highs (HH) and higher lows (HL) indicative of an uptrend, price breaks below the most recent higher low. This action signifies a shift in market control from buyers to sellers, indicating that the bullish structure is weakening and a new bearish trend may be emerging. It is a foundational concept in Smart Money Concepts (SMC) and ICT methodologies for identifying early reversal points.

**Claude Analytical Focus:**
-   **Identify Preceding Bullish Structure**: Claude should first confirm that the market is in a clear uptrend, characterized by the consistent formation of higher highs (HH) and higher lows (HL). This establishes the context for a potential reversal.
-   **Identify Most Recent Higher Low**: Pinpoint the most recent higher low that maintained the bullish market structure. This is the critical level that, if broken, will signal a change in character.
-   **Detect Decisive Break**: Look for a strong, impulsive candle (or series of candles) that closes decisively *below* the most recent higher low. A "decisive close" means the candle body should be clearly below the previous higher low, not just a wick. This indicates strong selling pressure and acceptance of lower prices, signaling that sellers have taken control.
-   **Distinguish from Liquidity Sweep**: Claude must differentiate a genuine CHOCH from a liquidity sweep (where price wicks below a higher low but closes back above it). A true CHOCH requires a candle *close* below the higher low.
-   **Contextualize with Higher Timeframe Supply**: The reliability of a bearish CHOCH is significantly enhanced when it occurs at or near a higher timeframe supply zone, Order Block, Fair Value Gap, or a significant resistance level. This confluence suggests institutional interest in reversing the price.
-   **Volume Analysis**: A strong CHOCH is often accompanied by an increase in selling volume, confirming the conviction behind the structural shift.

**Setup / Conditions:**
-   The market is in a clear uptrend, making higher highs and higher lows.
-   Price approaches the most recent higher low.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price breaks and closes decisively below the most recent higher low.
-   Prefer candle close confirmation over wick-only confirmation. A wick-only break is considered a liquidity sweep, not a CHOCH.

**Execution:**
-   **Entry**: The CHOCH itself is a reversal signal. Entry is typically sought on a subsequent pullback to a refined supply zone (e.g., Order Block, Fair Value Gap) that was created by the impulsive move that caused the CHOCH, or to the broken higher low (now acting as resistance).
-   **Stop Loss**: Place the stop loss above the origin of the CHOCH (the high that preceded the break of the higher low) or above the supply zone from which the entry was taken, allowing for a small buffer.
-   **Targets**: Target the next significant swing low, Value Area Low (VAL), VWAP, or higher timeframe support level. Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the break of the higher low is only a wick (a liquidity sweep) and not a decisive candle close.
-   Reject if there is no significant displacement (strong, large-bodied candles) after the CHOCH, indicating a weak shift in momentum.
-   Reject if price immediately reverses and breaks above the high that initiated the CHOCH, invalidating the bearish structural shift.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 95. Bullish Trend Continuation Structure

**Category:** Trend / Structure / Continuation  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** This signal identifies opportunities to join an existing bullish trend after a corrective pullback. In a healthy uptrend, price consistently forms higher highs (HH) and higher lows (HL). A bullish trend continuation setup occurs when price pulls back to a significant higher low zone (demand zone, Order Block, Fair Value Gap) and then shows clear signs of rejection and continuation, confirming the integrity of the bullish market structure.

**Claude Analytical Focus:**
-   **Identify Established Uptrend**: Claude should first confirm that the market is in a clear uptrend, characterized by a sequence of higher highs (HH) and higher lows (HL). This establishes the primary context.
-   **Identify Corrective Pullback**: Look for price to pull back from a newly formed higher high towards the previous higher low or a demand zone within the bullish structure. This pullback should be corrective, not impulsive, and ideally should not break below the last confirmed higher low.
-   **Identify Higher Low (HL) Zone**: Pinpoint the specific area where the higher low is expected to form. This could be a:
    -   Previous swing high (now acting as support)
    -   Order Block (OB) or Breaker Block (BB)
    -   Fair Value Gap (FVG) acting as demand
    -   Key Level Zone (KLZ) or significant Fibonacci retracement level (e.g., 50%, 61.8% of the previous impulse leg).
-   **Confirm Rejection and Continuation**: The critical confirmation is when price reaches the HL zone and shows clear signs of rejection (e.g., bullish pin bar, bullish engulfing, strong wick rejection) followed by a Break of Structure (BOS) or Change of Character (CHOCH) on a lower timeframe, breaking a minor high within the pullback. This confirms that buyers are stepping back in to defend the higher low and continue the trend.
-   **Volume Analysis**: Volume should typically decrease during the corrective pullback and then increase significantly on the rejection from the HL zone and the subsequent continuation, confirming renewed buying pressure.

**Setup / Conditions:**
-   The market is in a clear bullish trend, characterized by a sequence of higher highs (HH) and higher lows (HL).
-   Price pulls back to a significant higher low (HL) zone (e.g., demand zone, Order Block, FVG, previous swing high).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The pullback to the HL zone shows clear rejection (e.g., bullish price action candle).
-   A subsequent Break of Structure (BOS) or Change of Character (CHOCH) occurs on a lower timeframe, breaking a minor high within the pullback, confirming the continuation of the bullish trend.
-   Prefer candle close confirmation over wick-only confirmation for the structural break.

**Execution:**
-   **Entry**: Enter long after the confirmation of the HL rejection and the subsequent BOS/CHOCH. A retest of the broken minor high or the demand zone can offer a more precise entry.
-   **Stop Loss**: Place the stop loss below the confirmed higher low (HL) that initiated the continuation, allowing for a small buffer. If the HL is broken, the bullish structure is invalidated.
-   **Targets**: Target the next projected higher high, a measured extension of the previous impulse leg, or the next significant resistance level/liquidity pool. Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the price breaks and closes below the confirmed higher low (HL), as this invalidates the bullish market structure and suggests a potential trend reversal or deeper correction.
-   Reject if the rejection from the HL zone is weak or lacks conviction, or if the subsequent BOS/CHOCH does not occur.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 96. Bearish Trend Continuation Structure

**Category:** Trend / Structure / Continuation  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday

**Description:** This signal identifies opportunities to join an existing bearish trend after a corrective pullback. In a healthy downtrend, price consistently forms lower lows (LL) and lower highs (LH). A bearish trend continuation setup occurs when price pulls back to a significant lower high zone (supply zone, Order Block, Fair Value Gap) and then shows clear signs of rejection and continuation, confirming the integrity of the bearish market structure.

**Claude Analytical Focus:**
-   **Identify Established Downtrend**: Claude should first confirm that the market is in a clear downtrend, characterized by a sequence of lower lows (LL) and lower highs (LH). This establishes the primary context.
-   **Identify Corrective Pullback**: Look for price to pull back from a newly formed lower low towards the previous lower high or a supply zone within the bearish structure. This pullback should be corrective, not impulsive, and ideally should not break above the last confirmed lower high.
-   **Identify Lower High (LH) Zone**: Pinpoint the specific area where the lower high is expected to form. This could be a:
    -   Previous swing low (now acting as resistance)
    -   Order Block (OB) or Breaker Block (BB)
    -   Fair Value Gap (FVG) acting as supply
    -   Key Level Zone (KLZ) or significant Fibonacci retracement level (e.g., 50%, 61.8% of the previous impulse leg).
-   **Confirm Rejection and Continuation**: The critical confirmation is when price reaches the LH zone and shows clear signs of rejection (e.g., bearish pin bar, bearish engulfing, strong wick rejection) followed by a Break of Structure (BOS) or Change of Character (CHOCH) on a lower timeframe, breaking a minor low within the pullback. This confirms that sellers are stepping back in to defend the lower high and continue the trend.
-   **Volume Analysis**: Volume should typically decrease during the corrective pullback and then increase significantly on the rejection from the LH zone and the subsequent continuation, confirming renewed selling pressure.

**Setup / Conditions:**
-   The market is in a clear bearish trend, characterized by a sequence of lower lows (LL) and lower highs (LH).
-   Price pulls back to a significant lower high (LH) zone (e.g., supply zone, Order Block, FVG, previous swing low).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The pullback to the LH zone shows clear rejection (e.g., bearish price action candle).
-   A subsequent Break of Structure (BOS) or Change of Character (CHOCH) occurs on a lower timeframe, breaking a minor low within the pullback, confirming the continuation of the bearish trend.
-   Prefer candle close confirmation over wick-only confirmation for the structural break.

**Execution:**
-   **Entry**: Enter short after the confirmation of the LH rejection and the subsequent BOS/CHOCH. A retest of the broken minor low or the supply zone can offer a more precise entry.
-   **Stop Loss**: Place the stop loss above the confirmed lower high (LH) that initiated the continuation, allowing for a small buffer. If the LH is broken, the bearish structure is invalidated.
-   **Targets**: Target the next projected lower low, a measured extension of the previous impulse leg, or the next significant support level/liquidity pool. Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the price breaks and closes above the confirmed lower high (LH), as this invalidates the bearish market structure and suggests a potential trend reversal or deeper correction.
-   Reject if the rejection from the LH zone is weak or lacks conviction, or if the subsequent BOS/CHOCH does not occur.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 97. Buy the Higher Low (HL) in a Bullish Trend

**Category:** Trend / Structure / Continuation  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday / Swing

**Description:** This signal focuses on capitalizing on the continuation of an established bullish trend by entering a long position at a confirmed Higher Low (HL). In a healthy uptrend, price consistently forms Higher Highs (HH) and Higher Lows (HL). This strategy involves waiting for a corrective pullback to a key demand zone or previous resistance-turned-support, where a new HL is expected to form, and then entering as price resumes its upward trajectory.

**Claude Analytical Focus:**
-   **Confirm Bullish Trend**: Claude should first establish that the market is in a clear bullish trend, characterized by a consistent sequence of Higher Highs (HH) and Higher Lows (HL) on the relevant timeframe (e.g., 15-minute, 1-hour, 4-hour).
-   **Identify Corrective Pullback**: Look for price to pull back from a newly formed HH towards a potential HL zone. This pullback should be corrective in nature (e.g., small-bodied candles, decreasing volume) and should ideally not break below the previous confirmed HL.
-   **Pinpoint HL Zone Confluence**: The ideal location for a HL to form is at a confluence of significant support levels, such as:
    -   Previous swing high (now acting as support after a Break of Structure)
    -   Order Blocks (OB) or Breaker Blocks (BB) acting as demand zones
    -   Fair Value Gaps (FVG) that were created during the impulsive move
    -   Key Level Zones (KLZ) or significant Fibonacci retracement levels (e.g., 50%, 61.8% of the previous impulse leg)
    -   VWAP or its lower bands.
-   **Confirm HL Formation and Rejection**: The critical confirmation is when price reaches the HL zone and shows clear signs of rejection (e.g., bullish pin bar, bullish engulfing pattern, strong wick rejection) and then breaks a minor high within the pullback, signaling the resumption of the uptrend. This confirms that buyers are stepping in to defend the HL.
-   **Volume Analysis**: Volume should typically decrease during the corrective pullback and then increase significantly on the rejection from the HL zone and the subsequent continuation, confirming renewed buying pressure.

**Setup / Conditions:**
-   An established bullish trend is present, characterized by a sequence of Higher Highs (HH) and Higher Lows (HL).
-   Price pulls back to a significant support level or demand zone where a new Higher Low (HL) is expected to form.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price shows clear rejection at the HL zone (e.g., bullish price action candle).
-   A subsequent break and close above a minor high within the pullback confirms the formation of the new HL and the continuation of the bullish trend.
-   Prefer candle close confirmation over wick-only confirmation for the structural break.

**Execution:**
-   **Entry**: Enter long after the confirmation of the HL formation (rejection at the zone and break of a minor high within the pullback). A retest of the broken minor high or the demand zone can offer a more precise entry.
-   **Stop Loss**: Place the stop loss below the confirmed Higher Low (HL) that initiated the continuation, allowing for a small buffer. If the HL is broken, the bullish structure is invalidated.
-   **Targets**: Target the prior Higher High (HH), then look for extensions to the next significant resistance level or liquidity pool. Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the pullback breaks and closes below the prior confirmed Higher Low (HL), as this invalidates the bullish market structure and suggests a potential trend reversal or deeper correction.
-   Reject if the rejection from the HL zone is weak or lacks conviction, or if the subsequent minor structural break does not occur.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 98. Sell the Lower High (LH) in a Bearish Trend

**Category:** Trend / Structure / Continuation  
**Works with Gold/XAUUSD:** Very Good  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday / Swing

**Description:** This signal focuses on capitalizing on the continuation of an established bearish trend by entering a short position at a confirmed Lower High (LH). In a healthy downtrend, price consistently forms Lower Lows (LL) and Lower Highs (LH). This strategy involves waiting for a corrective pullback to a key supply zone or previous support-turned-resistance, where a new LH is expected to form, and then entering as price resumes its downward trajectory.

**Claude Analytical Focus:**
-   **Confirm Bearish Trend**: Claude should first establish that the market is in a clear bearish trend, characterized by a consistent sequence of Lower Lows (LL) and Lower Highs (LH) on the relevant timeframe (e.g., 15-minute, 1-hour, 4-hour).
-   **Identify Corrective Pullback**: Look for price to pull back from a newly formed LL towards a potential LH zone. This pullback should be corrective in nature (e.g., small-bodied candles, decreasing volume) and should ideally not break above the last confirmed LH.
-   **Pinpoint LH Zone Confluence**: The ideal location for a LH to form is at a confluence of significant resistance levels, such as:
    -   Previous swing low (now acting as resistance after a Break of Structure)
    -   Order Blocks (OB) or Breaker Blocks (BB) acting as supply zones
    -   Fair Value Gaps (FVG) that were created during the impulsive move
    -   Key Level Zones (KLZ) or significant Fibonacci retracement levels (e.g., 50%, 61.8% of the previous impulse leg)
    -   VWAP or its upper bands.
-   **Confirm LH Formation and Rejection**: The critical confirmation is when price reaches the LH zone and shows clear signs of rejection (e.g., bearish pin bar, bearish engulfing, strong wick rejection) and then breaks a minor low within the pullback, signaling the resumption of the downtrend. This confirms that sellers are stepping in to defend the LH.
-   **Volume Analysis**: Volume should typically decrease during the corrective pullback and then increase significantly on the rejection from the LH zone and the subsequent continuation, confirming renewed selling pressure.

**Setup / Conditions:**
-   An established bearish trend is present, characterized by a sequence of Lower Lows (LL) and Lower Highs (LH).
-   Price pulls back to a significant resistance level or supply zone where a new Lower High (LH) is expected to form.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   Price shows clear rejection at the LH zone (e.g., bearish price action candle).
-   A subsequent break and close below a minor low within the pullback confirms the formation of the new LH and the continuation of the bearish trend.
-   Prefer candle close confirmation over wick-only confirmation for the structural break.

**Execution:**
-   **Entry**: Enter short after the confirmation of the LH formation (rejection at the zone and break of a minor low within the pullback). A retest of the broken minor low or the supply zone can offer a more precise entry.
-   **Stop Loss**: Place the stop loss above the confirmed Lower High (LH) that initiated the continuation, allowing for a small buffer. If the LH is broken, the bearish structure is invalidated.
-   **Targets**: Target the prior Lower Low (LL), then look for extensions to the next significant support level or liquidity pool. Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the pullback breaks and closes above the prior confirmed Lower High (LH), as this invalidates the bearish market structure and suggests a potential trend reversal or deeper correction.
-   Reject if the rejection from the LH zone is weak or lacks conviction, or if the subsequent minor structural break does not occur.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """
    """
## 99. Trend Exhaustion Reversal

**Category:** Trend / Structure / Reversal  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Very Good  
**Best Use:** Reversal

**Description:** This signal identifies a potential trend reversal when an existing trend makes a new extreme (higher high in an uptrend, lower low in a downtrend) but with clear signs of exhaustion and weak follow-through. This lack of conviction at the new extreme, especially when combined with a subsequent shift in market structure, indicates that the dominant force is weakening and a reversal is imminent.

**Claude Analytical Focus:**
-   **Identify Extended Trend and Key Level**: Claude should first confirm that price has been in an extended trend (uptrend or downtrend) and has pushed into a significant key level (e.g., higher timeframe supply/demand zone, Order Block, Fair Value Gap, VAH/VAL, extreme VWAP band, previous swing high/low).
-   **Detect Exhaustion at New Extreme**: Look for signs that the trend is losing momentum as it makes a new high or low. These signs include:
    -   **Reduced Momentum**: Smaller candle bodies, overlapping candles, or decreasing Average True Range (ATR) compared to the preceding impulsive move.
    -   **Divergence**: If applicable, look for divergence between price and momentum oscillators (e.g., RSI, MACD), where price makes a new high/low but the oscillator fails to do so.
    -   **Wick Rejection**: Price pushing into the new extreme with a long wick, but closing back away from the extreme, indicating rejection.
    -   **Failure to Close Decisively**: The candle making the new extreme fails to close strongly beyond the previous extreme, suggesting a lack of conviction.
-   **Confirm Change of Character (CHOCH)**: The critical confirmation is a subsequent Change of Character (CHOCH) or Break of Structure (BOS) on the current or a lower timeframe, in the opposite direction of the exhausted trend. This means price breaks a previous swing low (for a bearish reversal) or swing high (for a bullish reversal), confirming a shift in market control.
-   **Volume Analysis**: Volume often decreases as the trend pushes to its new extreme, indicating a lack of fresh participants. Volume should then increase on the CHOCH/BOS, confirming the reversal.

**Setup / Conditions:**
-   An extended trend (uptrend or downtrend) is present, pushing into a significant key level.
-   Price makes a new extreme (HH or LL) but with clear signs of exhaustion (e.g., reduced momentum, smaller candle bodies, divergence, wick rejection).
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   The new high/low fails to sustain, and a clear Change of Character (CHOCH) or Break of Structure (BOS) occurs in the opposite direction of the exhausted trend.
-   Prefer candle close confirmation over wick-only confirmation for the CHOCH/BOS.

**Execution:**
-   **Entry**: Enter after the CHOCH/BOS confirmation. A retest of the broken structure or the level from which the CHOCH occurred can offer a more precise entry with reduced risk.
-   **Stop Loss**: Place the stop loss beyond the exhaustion extreme (e.g., above the new high for a short, below the new low for a long), allowing for a small buffer.
-   **Targets**: Target the VWAP, Point of Control (POC), or the first significant opposing key level (e.g., previous swing low/high, demand/supply zone). Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the trend remains strong and continues to push beyond the new extreme with conviction, without a clear CHOCH/BOS.
-   Reject if the signs of exhaustion are weak or ambiguous, or if the CHOCH/BOS is not clear or lacks displacement.
-   Reject if price immediately reverses and breaks back through the CHOCH/BOS level, invalidating the structural shift.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.
    """

## 100. Market Structure Shift (MSS) with Displacement

**Category:** Trend / Structure / Reversal  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Reversal

**Description:** A Market Structure Shift (MSS), often synonymous with a Change of Character (CHOCH) but emphasizing the impulsive nature of the break, is a powerful reversal signal. It occurs when price decisively breaks a key swing point (a higher low in an uptrend, or a lower high in a downtrend) with strong displacement (large, impulsive candles). This signifies a clear and aggressive shift in market control, indicating that the previous trend is likely over and a new trend is beginning.

**Claude Analytical Focus:**
-   **Identify Existing Trend and Key Swing Point**: Claude should first confirm the prevailing trend (uptrend or downtrend) and identify the critical swing point that, if broken, would invalidate that trend. This is typically the most recent Higher Low (HL) in an uptrend or the most recent Lower High (LH) in a downtrend.
-   **Detect Decisive Break with Displacement**: The core of this signal is the *displacement* – a strong, impulsive move characterized by large-bodied candles that break and close decisively beyond the identified key swing point. This break should be aggressive, leaving little doubt about the shift in momentum. High volume often accompanies this displacement.
-   **Distinguish from Liquidity Sweep**: It is crucial to differentiate a genuine MSS from a mere liquidity sweep. An MSS requires a candle *close* beyond the swing point, not just a wick. The displacement should be clear and sustained.
-   **Contextualize with Higher Timeframe Levels**: The reliability of an MSS is significantly enhanced when it occurs at or near a higher timeframe supply/demand zone, Order Block, Fair Value Gap, or a major Fibonacci retracement/extension level. This confluence suggests institutional participation in the reversal.
-   **Look for Subsequent Pullback**: After the MSS, price often pulls back to retest the newly broken structure or a refined supply/demand zone (e.g., Fair Value Gap or Order Block) created by the displacement. This pullback offers a high-probability entry for the new trend.

**Setup / Conditions:**
-   An existing trend (uptrend or downtrend) is mature or has reached a significant key level.
-   Price breaks a critical swing point (HL in uptrend, LH in downtrend) with strong displacement.
-   Must be near a meaningful level or aligned with market structure unless the signal is explicitly a filter.

**Trigger / Confirmation:**
-   A decisive break and close beyond the key swing point, accompanied by strong displacement (large, impulsive candles).
-   Prefer candle close confirmation over wick-only confirmation for the structural break.

**Execution:**
-   **Entry**: Enter on the subsequent pullback to a refined supply/demand zone (e.g., Fair Value Gap or Order Block) that was created by the displacement, or to the broken swing point (now acting as new support/resistance). Entry should be confirmed by lower timeframe price action.
-   **Stop Loss**: Place the stop loss beyond the origin of the MSS (the extreme of the displacement that caused the structural break), allowing for a small buffer.
-   **Targets**: Target the next significant liquidity pool, Market Profile level (e.g., VWAP, POC), or higher timeframe support/resistance level. Aim for a minimum 2R (risk-to-reward) target.
-   **Minimum Risk/Reward**: Maintain a minimum risk/reward ratio of 1:2, unless the signal is used purely as a filter or for partial profit taking.

**Invalidation / Reject:**
-   Reject if the break of the swing point is weak, lacks displacement, or is immediately retraced, indicating a potential false break.
-   Reject if price fails to pull back to a valid entry zone after the MSS, or if the pullback breaks the newly established structure.
-   Reject if spread/slippage is abnormal or if a high-impact news spike makes execution unsafe.

## 101. Swing Breakout Sequence (SBS Alias)

**Category:** Breakout / Liquidity / Swing Model  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Scalping/Intraday

**Naming Note:** The linked public resources call this concept **Swing Breakout Sequence (SBS)** or **Swing Breakout System**. If the signal generator or chart template uses the term **SBS**, Claude should treat `SBS`, `Swing Breakout Sequence`, and `Swing Breakout System` as the same strategy family unless a separate internal definition is provided.

**Description:** Swing Breakout Sequence is a liquidity-manipulation breakout model built from a defined swing sequence. The model expects repeated failed breakout attempts or liquidity raids around a swing zone, followed by a final directional breakout after the market has trapped early breakout traders and collected liquidity from the prior pullbacks.

**Core Idea for the Agent:**
-   The market first establishes an initial directional swing.
-   Price then forms a key pullback swing that becomes a liquidity reference.
-   A new high/low attempt attracts breakout traders.
-   Price retraces and takes liquidity from the earlier pullback.
-   A second liquidity event or reversal point forms.
-   The valid trade is not the first breakout attempt; it is the continuation after the sequence confirms pressure, liquidity collection, and structure alignment.

**Bullish SBS Sequence:**
1.  **Point 0:** Initial swing low.
2.  **Point 1:** Higher high that establishes initial bullish direction.
3.  **Point 2:** Pullback low that remains above Point 0. This becomes the key liquidity low.
4.  **Point 3:** New higher high or failed new high that attracts breakout buyers.
5.  **Point 4:** Retracement that sweeps or breaks the Point 2 liquidity low, ideally without closing in full bearish acceptance below the larger bullish structure.
6.  **Point 5:** Reversal / second low / double-bottom-style pressure point near or beyond Point 4.
7.  **Confirmation:** Bullish CHOCH/BOS after Point 5, followed by a break back above the internal swing or sequence breakout line.

**Bearish SBS Sequence:**
1.  **Point 0:** Initial swing high.
2.  **Point 1:** Lower low that establishes initial bearish direction.
3.  **Point 2:** Pullback high that remains below Point 0. This becomes the key liquidity high.
4.  **Point 3:** New lower low or failed new low that attracts breakout sellers.
5.  **Point 4:** Retracement that sweeps or breaks the Point 2 liquidity high, ideally without closing in full bullish acceptance above the larger bearish structure.
6.  **Point 5:** Reversal / second high / double-top-style pressure point near or beyond Point 4.
7.  **Confirmation:** Bearish CHOCH/BOS after Point 5, followed by a break back below the internal swing or sequence breakout line.

**Claude Analytical Focus:**
-   **Validate the Full Sequence:** Claude must not approve a random breakout just because the indicator draws an arrow. It should verify that the swing sequence is logical and that the key points are visible on the selected timeframe.
-   **Liquidity Logic:** Point 2 and Point 4 are the most important liquidity references. The setup is stronger when Point 4 takes liquidity from Point 2 and then fails to accept beyond it.
-   **Pressure in the Swing Zone:** Repeated attempts to break one side of the swing zone should show pressure building. The final breakout should come after trapped traders are positioned incorrectly.
-   **Point 5 Quality:** Point 5 should show rejection, equal high/low behavior, double top/bottom pressure, a reversal candle, or lower timeframe market structure shift.
-   **Confluence:** Prefer SBS that aligns with HTF bias, PDH/PDL, session high/low, VAH/VAL, VWAP band, OB, FVG, or KLZ.
-   **Indicator Integration:** If using LuxAlgo Swing Breakout Sequence or TradingView SBS, Claude can use the indicator as a detector, but approval still requires manual narrative validation of liquidity, structure, and risk/reward.

**Setup / Conditions:**
-   Six swing points are detected or can be objectively reconstructed from pivots.
-   The pattern height is meaningful relative to ATR/spread; avoid tiny sequences inside noise.
-   The full sequence forms within a reasonable number of bars; stale, overextended, or too-wide sequences are lower quality.
-   The final Point 5 reversal happens near a meaningful level or after a clear liquidity raid.
-   Prefer London and New York active sessions for XAUUSD and forex majors.

**Trigger / Confirmation:**
-   A valid Point 5 forms after the Point 4 liquidity event.
-   A lower timeframe CHOCH/BOS confirms that price has shifted away from the liquidity sweep.
-   For bullish SBS: price breaks above the internal swing high after Point 5, then ideally retests it or an FVG/OB created by the displacement.
-   For bearish SBS: price breaks below the internal swing low after Point 5, then ideally retests it or an FVG/OB created by the displacement.
-   Prefer candle-close confirmation over wick-only breakout arrows.

**Execution:**
-   **Entry:** Enter on the confirmed breakout after Point 5, or more conservatively on the retest of the breakout level / FVG / OB created by the confirmation displacement.
-   **Stop Loss:** Place the stop beyond Point 5 for aggressive entries. For conservative entries, place the stop beyond the sweep extreme or beyond the invalidated liquidity point, with a volatility buffer based on ATR.
-   **Targets:** Target the next external liquidity pool, Point 3 extreme, sequence measured move, PDH/PDL, session high/low, VWAP, VAH/VAL, POC, or minimum 2R. For bullish setups, prioritize buy-side liquidity above; for bearish setups, prioritize sell-side liquidity below.
-   **Minimum Risk/Reward:** Maintain at least 1:2. If the distance to the next liquidity target is less than 2R, reject or wait for a better retest entry.

**Invalidation / Reject:**
-   Reject if the six-point sequence is unclear, forced, or only visible after excessive pivot tuning.
-   Reject if Point 4 accepts beyond Point 2 with multiple closes and no fast reclaim, because this may indicate a real reversal rather than a liquidity raid.
-   Reject if Point 5 does not create a clear structure shift.
-   Reject if the final breakout candle is already too extended and entry would be chasing into the target.
-   Reject if price is in VWAP chop, middle of value, or directly into a strong opposing OB/KLZ/VAH/VAL.
-   Reject if high-impact news creates a spike that invalidates normal sequence logic.

**Signal Generator Pseudocode:**
```text
for each symbol/timeframe:
    pivots = detect_pivots(lookback = 2 to 5)
    keep last 6 alternating swing points

    bullish_sequence =
        P0 is low
        P1 is high and P1 > P0
        P2 is low and P2 > P0
        P3 is high and P3 >= P1
        P4 is low and P4 <= P2
        P5 is low/reversal zone near P4
        price later breaks internal high after P5

    bearish_sequence =
        P0 is high
        P1 is low and P1 < P0
        P2 is high and P2 < P0
        P3 is low and P3 <= P1
        P4 is high and P4 >= P2
        P5 is high/reversal zone near P4
        price later breaks internal low after P5

    require:
        pattern_height_pct >= minimum_threshold
        sequence_width_bars <= maximum_threshold
        confirmation_bos == true
        risk_reward >= 2.0

    emit raw signal:
        name = "Swing Breakout Sequence (SBS)"
        direction = bullish ? LONG : SHORT
        entry_zone = breakout_retest_or_fvg
        stop = beyond_P5_or_sweep_extreme
        targets = nearest_liquidity_levels
```

**Claude Approval Notes:**
-   APPROVE only when the sequence is visible, the liquidity sweep is logical, and the final breakout has not already consumed the reward.
-   WAIT when Point 5 is present but BOS/CHOCH has not confirmed.
-   REJECT when the indicator marks a sequence inside low-volume chop or inside a balanced range with no clear liquidity target.

## 102. Candle Range Theory (CRT) Model

**Category:** ICT-Derived / Liquidity / Range Model  
**Works with Gold/XAUUSD:** Excellent  
**Works with Forex Majors:** Excellent  
**Best Use:** Intraday/Scalping

**Description:** Candle Range Theory maps a higher-timeframe candle as a tradable range on a lower timeframe. The high of the anchor candle becomes the **CRT-High**, and the low becomes the **CRT-Low**. The core model expects price to raid one side of the prior candle range, close back inside the range, then deliver toward the opposite side of the range or the next external liquidity pool.

**Core Idea for the Agent:**
-   Select a higher-timeframe anchor candle, usually H1, H4, Daily, or Weekly depending on the trading style.
-   Mark the anchor candle high and low as a range.
-   Wait for the next candle to sweep one side of that range.
-   The sweep must fail to accept outside the range.
-   Drop to a lower timeframe to confirm MSS/CHOCH/CISD.
-   Enter on retest of the lower timeframe displacement, FVG, OB, or CISD level.
-   Target the opposite side of the CRT range first, then external liquidity if risk/reward supports continuation.

**Recommended Fractal Pairings:**
| Trading Style | Higher-Timeframe CRT Candle | Lower-Timeframe Execution |
|---|---:|---:|
| XAUUSD scalping | 15m / 30m / 1H | 1m / 3m / 5m |
| XAUUSD intraday | 1H / 4H | 5m / 15m |
| Forex intraday | 1H / 4H | 5m / 15m |
| Swing | Daily / Weekly | 1H / 4H |

**Bullish CRT Model:**
1.  Higher timeframe is at support, discount, HTF demand, OB, FVG, VAL, PDL, session low, or a clear buy-side continuation context.
2.  Mark the previous HTF candle high as `CRT-High` and low as `CRT-Low`.
3.  The next candle raids below `CRT-Low`.
4.  The raiding candle closes back above `CRT-Low`, showing failed downside acceptance.
5.  Lower timeframe confirms bullish MSS/CHOCH/CISD.
6.  Entry is on retest of the bullish displacement/FVG/OB/CISD level.
7.  Stop is below the liquidity raid low or MSS swing low.
8.  First target is the CRT mean or `CRT-High`; second target is external buy-side liquidity above.

**Bearish CRT Model:**
1.  Higher timeframe is at resistance, premium, HTF supply, OB, FVG, VAH, PDH, session high, or a clear sell-side continuation context.
2.  Mark the previous HTF candle high as `CRT-High` and low as `CRT-Low`.
3.  The next candle raids above `CRT-High`.
4.  The raiding candle closes back below `CRT-High`, showing failed upside acceptance.
5.  Lower timeframe confirms bearish MSS/CHOCH/CISD.
6.  Entry is on retest of the bearish displacement/FVG/OB/CISD level.
7.  Stop is above the liquidity raid high or MSS swing high.
8.  First target is the CRT mean or `CRT-Low`; second target is external sell-side liquidity below.

**Claude Analytical Focus:**
-   **Anchor Candle Quality:** Prefer anchor candles that close at a meaningful HTF level. Do not use random candles from the middle of a range.
-   **Range Raid:** The raid must sweep one side of the prior candle range and then close back inside. Wick-only sweeps can be valid only if followed by clear LTF structure confirmation.
-   **MSS / CHOCH / CISD Confirmation:** CRT is not approved from the HTF sweep alone. Claude should require LTF structure shift or Change in State of Delivery before approving execution.
-   **Candle 2 Interpretation:** If the reversal candle has small wicks and strong body displacement back into the range, continuation potential is stronger. If it has a huge wick and closes weakly, the move may have already spent its range and Claude should prefer WAIT or target only the range mean.
-   **Mean Line:** The 50% level of the CRT range is an important reaction point. It can be used as Target 1 or as a decision point for partials.
-   **Session Timing:** Prefer CRT setups during London, New York AM, or known CRT time filters. Avoid low-liquidity late-session signals unless the setup aligns with HTF context.
-   **Indicator Integration:** If using CandelaCharts CRT Model, Claude can use alerts such as Model Formation, Sweep, D-Purge, Model Completed, and Model Invalidated as raw detector events only. Approval still requires context, LTF confirmation, and risk/reward validation.

**Setup / Conditions:**
-   A higher-timeframe candle has closed at or near a meaningful level.
-   `CRT-High`, `CRT-Low`, and `CRT-Mean` are clearly marked.
-   The next candle raids one side of the range and closes back inside.
-   Lower timeframe confirms MSS/CHOCH/CISD in the direction away from the raid.
-   Entry is not in the middle of value unless the target is only the CRT mean and risk/reward remains valid.
-   Prefer confluence with PDH/PDL, session high/low, VAH/VAL, VWAP band, FVG, OB, KLZ, SMT divergence, or Turtle Soup-style sweep.

**Trigger / Confirmation:**
-   **Bullish Trigger:** Sweep below `CRT-Low` + close back above `CRT-Low` + bullish MSS/CHOCH/CISD on LTF.
-   **Bearish Trigger:** Sweep above `CRT-High` + close back below `CRT-High` + bearish MSS/CHOCH/CISD on LTF.
-   **Conservative Entry:** Wait for displacement, then enter on retracement into FVG/OB/CISD.
-   **Aggressive Entry:** Enter after LTF MSS close if stop can be placed cleanly beyond the raid extreme and the target still gives 2R.

**Execution:**
-   **Entry:** LTF retest of MSS/CISD/FVG/OB after the CRT sweep confirms. Avoid entering immediately on the HTF sweep without LTF confirmation.
-   **Stop Loss:** Bullish stop below the raid low or MSS swing low. Bearish stop above the raid high or MSS swing high. Add ATR/spread buffer, especially on XAUUSD.
-   **Target 1:** CRT mean (50%) if the range is wide or if Candle 2 has a large wick.
-   **Target 2:** Opposite side of the range (`CRT-High` for bullish, `CRT-Low` for bearish).
-   **Target 3:** External liquidity beyond the opposite side if displacement and session context support continuation.
-   **Minimum Risk/Reward:** Maintain at least 1:2 to Target 2 or external liquidity. If only the mean target is realistic and below 2R, reject or wait for better entry.

**Invalidation / Reject:**
-   Reject if the raiding candle closes strongly outside the CRT range and subsequent candles accept outside it.
-   Reject if there is no LTF MSS/CHOCH/CISD after the sweep.
-   Reject if the setup forms in the middle of a balanced range without HTF support/resistance context.
-   Reject if the first target is too close to provide 1:2 risk/reward.
-   Reject if price already reached the CRT mean or opposite side before entry confirmation.
-   Reject if Candle 2 already delivered a large move and Candle 3 would be a late chase into retracement/chop.
-   Reject if the setup conflicts with a strong HTF trend unless it is explicitly traded as a fast liquidity scalp.
-   Reject around high-impact news if spread, slippage, or candle distortion makes the range unreliable.

**Signal Generator Pseudocode:**
```text
for each symbol:
    choose HTF candle based on strategy profile
    anchor = previous_closed_htf_candle
    crt_high = anchor.high
    crt_low = anchor.low
    crt_mean = (crt_high + crt_low) / 2

    current_htf = active_or_next_htf_candle

    bullish_crt =
        current_htf.low < crt_low
        and current_htf.close > crt_low
        and htf_context near support/discount/demand
        and ltf_mss_or_cisd == bullish

    bearish_crt =
        current_htf.high > crt_high
        and current_htf.close < crt_high
        and htf_context near resistance/premium/supply
        and ltf_mss_or_cisd == bearish

    if bullish_crt:
        entry_zone = ltf_fvg_or_ob_or_cisd_retest
        stop = min(raid_low, mss_swing_low) - buffer
        targets = [crt_mean, crt_high, external_buy_side_liquidity]

    if bearish_crt:
        entry_zone = ltf_fvg_or_ob_or_cisd_retest
        stop = max(raid_high, mss_swing_high) + buffer
        targets = [crt_mean, crt_low, external_sell_side_liquidity]

    require:
        risk_reward_to_target_2 >= 2.0
        spread_normal == true
        news_safe == true

    emit raw signal:
        name = "Candle Range Theory (CRT)"
        direction = LONG or SHORT
        entry_zone, stop, targets, invalidation
```

**Claude Approval Notes:**
-   APPROVE when the setup has HTF context, a clean range raid, LTF MSS/CISD, and a realistic path to the opposite side of the CRT range.
-   WAIT when the sweep happened but the lower timeframe has not confirmed.
-   REJECT when the sweep becomes real acceptance outside the range or when entry comes after most of the range has already been delivered.


## Additional References for Added SBS and CRT Models

[4] TradingView: Swing Breakout System (SBS) by ClayeWeight
[5] LuxAlgo Library: Swing Breakout Sequence indicator notes
[6] TradingView Education: Understanding Candle Range Theory
[7] Inner Circle Trader tutorial: Candle Range Theory (CRT)
[8] TradingView: CandelaCharts CRT Model indicator notes
