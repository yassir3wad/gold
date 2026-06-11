---
name: discretionary-trade
description: Deprecated discretionary SMC/TPO workflow. Do not use for scalp-suite, OFVWAP, VP-Node, PAR/LDP, or SBS unless explicitly requested.
---

# Discretionary Trade

Deprecated for normal scalp work. Use `skills/scalp-suite` instead.

## Hard Boundary

Do **not** mix this workflow into:

- `scalp-suite`
- `ofvwap-scalp`
- `vp-node-scalp`
- `par-liqdelta-scalp`
- `swing-breakout`

SMC/TPO/CRT are not confirmations, vetoes, or triggers for the scalp strategies unless the user explicitly asks for this deprecated discretionary workflow.

## Use Only When Explicitly Requested

If the user asks for discretionary SMC/TPO trading, use this simplified loop:

1. Read 4H, 1H, 15m first.
2. Build level map from SMC order blocks, structure, VWAP/EMAs, and TPO value areas.
3. Classify regime: trend, range, chop/dead, reversal.
4. Trade only at meaningful levels.
5. Require candle close trigger.
6. Define entry, SL, TP1, TP2 before entry.
7. Reject if R:R is poor, stop is illogical, or price is mid-range.
8. Manage from OHLCV only.

## Output

```text
decision, regime, level, trigger, entry, SL, TP1, TP2, reason
```

If any field is unclear, `WAIT`.
