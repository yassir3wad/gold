---
name: vp-node-scalp
description: Mechanical Volume Profile Node scalp checklist using the Volume Profile TradingView layout. Trades VP edge reversals or LVN continuations only. Gold SL max 50p, TP1 70-100p.
---

# VP Node Scalp

Use this strategy alone. Open the `Volume Profile` layout.

## Setup

- Feed: `PEPPERSTONE:XAUUSD` for gold.
- Layout: `Volume Profile`.
- Indicator: **Session Volume Profile HD (native TradingView).** Replaces "Volume Profile with Node Detection [LuxAlgo]",
  which crashed / wouldn't render or return labels. Native SVP HD always renders; read it **visually** (it has no data API for levels).
- Gold convention: `1.00 price = 10 pips`.

## Levels

- `POC`: magnet/chop. Avoid entries on it.
- `HVN`: acceptance/stall. Can be support/resistance or target.
- `LVN`: thin zone. Good for continuation if broken cleanly.
- `VAH/VAL/profile edge`: best reversal or breakout locations.

## Valid Models

### Edge Reversal

LONG:
1. Price sweeps lower edge/LVN low.
2. Candle closes back inside/above edge.
3. SL below sweep low.
4. TP1 to nearest HVN/POC/edge with clean path.

SHORT:
1. Price sweeps upper edge/LVN high.
2. Candle closes back inside/below edge.
3. SL above sweep high.
4. TP1 to nearest HVN/POC/edge with clean path.

### LVN Continuation

LONG:
1. Strong close above edge/HVN/POC into LVN/thin area.
2. Retest holds or close is strong enough.
3. SL below breakout/retest low.

SHORT: mirror.

## Risk

- Gold SL max `50p` / `5.0` price points.
- TP1 `70-100p` only if path is clear.
- TP2 next node/profile edge/structure only.

## Reject

- Price in POC/HVN middle.
- Value middle.
- Weak/doji close.
- TP1 blocked before `70p`.
- Logical SL wider than cap.
- Node data stale or unreadable.

## Reading (visual-first)

- **Read Session Volume Profile HD VISUALLY from a screenshot** — POC / VAH / VAL / HVN / LVN / value-area edges off the
  chart. Native VP has **no level data API**, so there is no label/box read — visual only. Cross-check exact entry/SL/TP
  prices against `data_get_ohlcv`. (The old LuxAlgo Node-Detection labels are gone — do not use them.)

## Backtest

One day, one strategy, one layout.

Log:

```text
time, location, model, trigger, decision, entry, SL, TP1, TP2, result, pips
```

Verify TP/SL with OHLCV only.
