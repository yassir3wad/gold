# Negative Results

This file records ideas that looked plausible but failed project evidence. Do not revive these as live
trading gates or approval reasons unless a fresh, spread-adjusted out-of-sample study overturns the result.

## Disproven Or Rejected Ideas

| Idea | Status | Evidence | Policy |
|---|---|---|---|
| `approval_model.py` calibrated approval layer | Disproven | June 2026 replay/backtest work found the calibrated model anti-calibrated out of sample. | Keep as a research artifact only; do not wire into live approval. |
| Morning `day_efficiency()` gate | Rejected | Morning displacement/range was coin-flip as an early day-type predictor. | Do not use it to gate the trading day or override setup quality. |
| `break-and-retest` family | Rejected | Tested sample was uniformly bad; the roadmap marks break-and-retest as `rejected`. | Keep `break_retest` disabled unless a new cost-adjusted study proves otherwise. |
| Generic `momentum impulse` | Rejected / observation-only | Negative after spread and overproduced losses in the June review sample. | Keep behind `observation_gate`; do not fire live by default. |
| Weak ER-only filters | Weak / insufficient | ER frame probes showed ER is a weak outcome discriminator; faster ER did not create robust edge. | Use ER as context/chop protection only, not as a standalone profit lever or loosening reason. |

## Reconsideration Bar

Before any item above can return to live trading, require all of:

- A clearly specified new rule, not the old rejected rule under a new name.
- Spread/slippage-adjusted results, not gross pips.
- Out-of-sample replay using the canonical `replay_sim.py` + `score_signals.py` path.
- Live-forward evidence with enough sample size for the setup family.
- An update to this file explaining why the old negative result no longer applies.
