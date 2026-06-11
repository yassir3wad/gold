---
name: par-liqdelta-scalp
description: Mechanical Peak Activity Range + Liquidity Delta Provider scalp checklist. PAR gives location; LDP gives trigger. Trades PAR edge/liquidity sweeps only. Gold SL max 50p, TP1 70-100p.
---

# PAR + LDP Scalp

Use this strategy alone. Use two layouts in sequence:

1. `Peak Activity Range` for location.
2. `Liquidity Delta Provider` for trigger.

Do not stack heavy layouts unless explicitly needed and stable.

## Setup

- Feed: `PEPPERSTONE:XAUUSD` for gold.
- Location layout: `Peak Activity Range`.
- Trigger layout: `Liquidity Delta Provider`.
- Gold convention: `1.00 price = 10 pips`.

## PAR Location

Trade only:

- PAR high.
- PAR low.
- PAR breakout/retest edge.
- Clear liquidity zone near PAR edge.

No trade:

- PAR midpoint.
- PAR POC.
- Middle of range.

## LDP Trigger

Valid trigger needs one or more at the location:

- `ABS`: absorption.
- `EXH`: exhaustion.
- `DIV`: divergence.
- `REJ`: snapback rejection.
- BSL/SSL sweep with close back inside.
- Delta recovery in trade direction.

## Valid Models

### PAR Rejection

LONG:
1. Price tests/sweeps PAR low.
2. Candle closes back above PAR low.
3. LDP confirms SSL sweep or bullish ABS/EXH/DIV/REJ.

SHORT:
1. Price tests/sweeps PAR high.
2. Candle closes back below PAR high.
3. LDP confirms BSL sweep or bearish ABS/EXH/DIV/REJ.

### PAR Breakout Retest

LONG:
1. Candle closes above PAR high.
2. Retest holds above edge.
3. LDP does not show bearish absorption/rejection.

SHORT: mirror below PAR low.

## Risk

- Gold SL max `50p` / `5.0` price points.
- SL beyond sweep/retest extreme.
- TP1 `70-100p` if path is clear.
- TP2 next PAR edge, midpoint, liquidity zone, or visible structure only.

## Reject

- Price in PAR middle/POC.
- Missing LDP trigger.
- Wick only, no close confirmation.
- Zone fully consumed with no reaction.

## Reading (visual-first)

- **Read PAR ranges from a screenshot** — do NOT `data_get_pine_boxes` (it returns hundreds of boxes; context-killer). Read
  LDP signals (ABS/EXH/DIV/REJ) visually or via a small label read. Pull `data_get_ohlcv` only to price the trade.
- TP1 blocked before `70p`.
- Logical SL wider than cap.

## Backtest

One day, one strategy.

Workflow:

1. Read PAR location.
2. If price is not at PAR edge, `WAIT`.
3. Switch to LDP only at valid location.
4. Confirm trigger.
5. Enter/manage from OHLCV.

Log:

```text
time, PAR_location, LDP_trigger, decision, entry, SL, TP1, TP2, result, pips
```
