---
name: ofvwap-scalp
description: Mechanical OFVWAP scalp checklist using the VWAP TradingView layout. 15m regime, 5m trigger. Trades band/VWAP sweep, reclaim, pullback, or rejection. Gold SL max 50p, TP1 70-100p.
---

# OFVWAP Scalp

Use this strategy alone. Open the `VWAP` layout.

## Setup

- Feed: `PEPPERSTONE:XAUUSD` for gold.
- Layout: `VWAP`.
- Regime TF: `15m`.
- Entry TF: `5m`.
- Gold convention: `1.00 price = 10 pips`.

## Core Read

VWAP is the gate. Bands are stretch.

Valid patterns:

| Pattern | Direction | Trigger |
|---|---|---|
| Lower band sweep/reclaim | LONG | 5m closes back inside/above band after sweep |
| Upper band sweep/reclaim | SHORT | 5m closes back inside/below band after sweep |
| VWAP reclaim | LONG | 5m closes above VWAP and holds/retests |
| VWAP rejection | SHORT | 5m rejects VWAP from below and closes down |
| Trend pullback to VWAP | With trend | Pullback touches VWAP/band and rejects in trend direction |

## Regime

- `RANGE`: fade clean band sweeps back toward VWAP.
- `TREND`: trade with slope only; pullback to VWAP/band, then continuation.
- `CHOP`: no trade when price is glued to VWAP or bands are tight.

## Entry Rules

1. Price must be at VWAP or a band.
2. 5m candle must close as trigger. Wick alone is not enough.
3. Stop must sit beyond swept/rejection extreme.
4. Gold SL must be <= `50p` / `5.0` price points.
5. TP1 must have `70-100p` clean path, or use nearest real blocker if still >= `70p`.
6. TP2 is next structure/VWAP/band/node only.

## Reject

- Mid-range between VWAP and band.
- No 5m close confirmation.
- Band walk with no reclaim.
- Stop wider than allowed.
- TP1 blocked before `70p`.
- First candle after session reset unless a fresh regime is clear.

## Reading

- **`data_get_study_values` is the primary read here** — VWAP/band levels are tiny and exact, and you need them for entry/SL.
  This is the one strategy where the data read is the default (not a screenshot). Screenshot only for the visual picture.

## Manage

- Partial at TP1.
- Move to BE only after TP1 or +40p with minor structure cleared.
- Never widen SL.
- Runner exits at next structure or on close back through VWAP against trade.

## Backtest

One day, one strategy, one layout.

Log:

```text
time, regime, location, trigger, decision, entry, SL, TP1, TP2, result, pips
```

Verify TP/SL with OHLCV only.
