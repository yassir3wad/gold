# Confidence scoring (0–10)

The letter grade ceilings at **A+** — so a setup with 5 stacked factors and a bare A+ look identical and
risk the same. `confidence.py` fixes that: it aggregates **every** confluence axis the engine already
computes into one **0–10 confidence score** that keeps rising past the A+ ceiling.

## What goes into the score
| Axis | Source | Points |
|---|---|---|
| Grade | the A+/A/B letter | A+ 3 · A 2 · B 1 · else 0 |
| Level-map confluence | `conf_S`/`conf_R` (VWAP/VAL/EMA/round#/PDH/… stacked at price) | up to 2 |
| SMC + Auto-Trendline | the independent HTF confluence score (`cf_score`) | up to 2 |
| RSI divergence | `rsi_divergence(b, side)` at the level | +1 |
| Trend alignment | 30m EMA stack vs trade side | with-trend +1 · counter-trend −1 · flat 0 |
| R:R | TP1-vs-stop ratio | ≥2 → +1 |
| Prior-VA Level State | a VAH/VAL/POC within `dyn_tolp` of entry that is **Rejected/Flipped** (not Accepted) | +1 |

Summed and clamped to **0–10**, then labeled: **very-high** (≥8) · **high** (≥6) · **medium** (≥4) · **low**.

## Where it shows
- **Readout:** `>> FAST SIGNAL: LONG [A+] confidence 8/10 (very-high) [why] …`
- **Telegram alert:** a `• Confidence: 8/10 (very-high)` line in the context block.
- **AI review (`--review`):** an explicit steer printed with the held trade — *"confidence N/10; ≥7 = strong
  conviction, lean approve if discipline holds; ≤3 = weak, only approve with a clear reason."* The score is
  also stored on the held trade (`confidence`, `conf_lbl`).

## Position sizing (opt-in)
Default sizing is **fixed-$-risk** (`lot = RISK_USD / stop_pips`). With the **`confidence_sizing`** flag
**on** (default **OFF** — live risk unchanged until you enable it), confidence scales the dollar risk:

```
size_multiplier:  confidence 0 → CONF_SIZE_LO (0.75×)
                  confidence 5 → 1.0×
                  confidence 10 → CONF_SIZE_HI (1.5×)   (piecewise-linear, clamped)
```

So high-conviction setups risk more, low ones less. The alert/readout tag the adjustment, e.g.
`($82 [conf-sized 1.35×])`. Turn it on by setting `"confidence_sizing": true` in `flags.json` — ideally
after watching a few signals' scores look sensible (and/or a backtest).

## Files & tests
`confidence.py` — `score(...)`, `size_multiplier(...)`, `label(...)` (all pure). Wired into `scalp_fast.py`
just before position sizing. Tests: `test_confidence.py` (13 checks).
