---
name: swing-breakout
description: Mechanical Swing Breakout Sequence scalp checklist using the SBS TradingView layout. Trend-day only. Trades confirmed resolution after P5. Skip range/chop.
---

# Swing Breakout Sequence Scalp

Use this strategy alone. Open the `SBS` layout.

## Setup

- Feed: `PEPPERSTONE:XAUUSD` for gold.
- Layout: `SBS`.
- Preferred TF: `15m`.
- Optional timing TF: `5m` only after trend is confirmed.
- Gold convention: `1.00 price = 10 pips`.

## Regime Gate

Use SBS only on:

- Trend day.
- Expansion day.
- Clear directional structure.

Reject SBS on:

- Range day.
- Chop shelf.
- Mid-value rotation.

## Pattern

SBS is a 5-point failed-breakout/trapped-trader sequence:

```text
P1 attempt -> P2 pullback -> P3 second attempt -> P4 pullback -> P5 reversal/resolution point
```

## Entry

Valid entry:

1. P1-P5 sequence is complete.
2. Candle closes in resolving direction.
3. Optional retest holds.
4. Entry is not late after target path is mostly traveled.

## Stop

- SL goes beyond P5/sequence invalidation.
- If P5 stop is too wide for scalp, skip or classify separately as wider intraday.
- Never use the full sequence extreme if it makes the scalp invalid.
- Never place SL inside noise to force R:R.

## Targets

- Gold TP1: `70-100p` if clean.
- TP2: next swing/structure only.
- BE after TP1 or after +40p with minor structure cleared.

## Reject

- No completed P5.
- No confirming close.
- Range/chop regime.
- TP1 blocked before minimum.
- Stop too wide.
- API labels stale/unreadable.

## Reading (visual-first)

- **Read SBS from a screenshot** (zoom to the active swing), NOT `data_get_pine_labels`: the label API returns hundreds of
  points including FUTURE-drawn sequences and caps by draw-order (not no-hindsight). Identify the live 5-point sequence and
  **P5 visually**, then watch price vs the P5 line via `data_get_ohlcv` for the closed-candle break. Pull data only to price the trade.

## Backtest

One day, one strategy, one layout.

Log:

```text
time, regime, sequence_state, trigger, decision, entry, SL, TP1, TP2, result, pips
```

Verify TP/SL with OHLCV only.
