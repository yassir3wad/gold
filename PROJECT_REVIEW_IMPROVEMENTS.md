# Project Review and Improvement Plan

Date: 2026-06-07

This review covers the TradingView MCP gold scalping project, with focus on strategy improvement, performance, trade quality, backtesting reliability, and operational risk. It is based on the current repo docs/code, `flags.json`, recent `analyze_logs.py` output, and the June 2026 backtest findings.

## Executive Summary

The system is already more advanced than a simple signal bot: it has live TradingView chart extraction, multi-strategy setup detection, HTF level confluence, TPO/value-area logic, Telegram alerts, SQLite outcome logging, replay backtests, and feature flags.

The biggest strategic finding is cost-adjusted edge. The backtest notes show the average raw signal is around breakeven before spread, then negative after realistic gold spread. That means the project should optimize for fewer, higher-quality trades, not more alerts or higher signal count.

Current live logs for the last 14 days show 18 executed trades across symbols, +154 gross pips and +101 pips after spread. XAUUSD is still positive after spread (+118 pips, +6.9 pips/trade), but the result is carried by a few large winners. The losing groups in the live sample are still `momentum impulse`, `zone-bounce rejection`, and `liquidity-sweep reversal`, which matches the earlier cost-aware warning that high-frequency setup families can look attractive gross but fail after cost.

## Second-Pass Findings

This second review adds three important findings.

First, the untracked `docs/signal-roadmap-detailed.md` is useful as a reference menu, and it already says it is not a build list. That warning is important and should stay. The remaining risk is that the 100-signal table labels many setups as "Excellent" for gold/forex without repo-backed evidence. That can still push an AI reviewer toward approving attractive textbook setups instead of the few setup families that have demonstrated cost-adjusted edge.

Second, `draw_overlay.py` had a practical throttle bug. `_recent()` reads `(chart + ":ts")` from `~/.tv_overlay_ids.json`, but `_save_ids()` previously saved only the drawn entity IDs. This is now fixed: `_save_ids()` persists the timestamp, `draw_overlay()` accepts an injectable `state_path`, and `test_draw_overlay.py` covers the throttle path.

Third, current all-symbol log analysis over the last 14 days shows 18 executed trades, +154 gross pips, +101 pips after spread, 39% gross win rate, 1.50 gross profit factor, 1.29 net profit factor, and +5.6 net pips/trade. XAUUSD remains positive, while one NAS100 trade is negative. The all-symbol sample still shows the same weak families: `zone-bounce rejection`, `momentum impulse`, and `liquidity-sweep reversal`.

## Status Tracker

Legend: `Done` = implemented in current files; `Partial` = started but still incomplete; `Pending` = not implemented; `Keep monitoring` = intentionally not changed yet.

| Item | Status | Evidence / next step |
|---|---|---|
| Fix overlay redraw throttling | Done | `draw_overlay._save_ids()` now writes `:ts`; `test_draw_overlay.py` checks `_recent()` with a temp state file. |
| Add overlay throttle tests | Done | `python3 test_draw_overlay.py` passes 17/17 checks. |
| Add spread assumptions per symbol | Done | `instruments.json` includes `spread_pips` for default and each instrument. |
| Report spread-adjusted expectancy | Done | `analyze_logs.py` now reports gross and after-spread net, Nexp, Nnet, and cost-aware setup ranking. |
| Track alert/reject/trade opportunity cost | Done | `analyze_logs.py` now prints per-day flow with alerts, rejects, and trades. |
| Mark approval model as disproven | Done | `approval_model.py` has a prominent negative-result banner and rewrites the in-sample comments. |
| Add confidence score beyond A+ grade | Done | `confidence.py` exists and `scalp_fast.py` emits confidence in signal/review output. |
| Add confidence penalties from roadmap guide | Done | `confidence.py` includes mid-value, accepted-through, over-tested, opposing-level, and VWAP-chop penalties. |
| Add AI approval checklist / APPROVE-REJECT-WAIT | Done | `scalp_fast.py --review` prints the checklist and asks for `APPROVE / REJECT / WAIT`. |
| Add cost/decision columns to outcome DB | Done | `outcome_db.py` includes spread/slippage/commission/gross/net and decision source/reason columns, with migration. |
| Keep 100-signal roadmap as reference, not build list | Partial | `docs/signal-roadmap.md` and `docs/signal-roadmap-detailed.md` clearly say roadmap/menu, not build list. Still needs per-signal evidence tags. |
| Evidence-tag every roadmap signal | Pending | Add `validated / experimental / rejected / not tested` tags to the roadmap tables. |
| Disable or observation-gate `momentum_impulse` | Pending | `flags.json` still has `"momentum_impulse": true`; live logs remain negative after spread for this family. |
| Add setup-family daily caps | Pending | No cap mechanism found; rejected/auto-skip volume remains high. |
| Tighten `zone_bounce` and `liquidity_sweep` | Partial | Existing gates/hard floor help, but both remain enabled and live logs remain negative after spread. |
| Keep `break_retest` disabled | Done | `flags.json` has `"break_retest": false`. |
| Split static vs live Node tests | Pending | `package.json` still runs CDP-dependent tests under `npm test`; no `test:static` / `test:live` split yet. |
| Convert import-time Python tests | Pending | Full unittest discovery still needs cleanup; targeted `python3 -m unittest test_outcome_db test_metrics test_approval_model` ran 0 tests because these scripts use custom runners. |
| Add spread/cost to backtest reports | Partial | `analyze_logs.py` is cost-aware; `backtest_multi_day.py` still mostly reports gross `net_pips`. |
| Split `scalp_fast.py` into modules | Pending | `scalp_fast.py` remains the large canonical scanner. Keep this low priority until behavior stabilizes. |

## Current Strengths

- `scalp_fast.py` is a single canonical live scanner, which keeps strategy drift under control.
- `flags.json` allows fast strategy/filter toggling without code edits.
- SQLite outcome logging in `outcome_db.py` is a strong upgrade over CSV-only logging and reduces concurrent write risk.
- The replay harness uses the real scanner instead of a separate reimplementation, reducing backtest/live mismatch.
- TPO/value-area work is now stateful through `va_store.py`, `va_state.py`, `harvest_daily.py`, and `reharvest_week.py`.
- The hard-floor gate in `scalp_fast.py` correctly targets structurally bad trades: negative R:R, dead chop, and counter-trend no-room cases.
- The strategy docs preserve negative results, especially the disproven approval model and day-type gate. This is good research discipline.

## Main Problems

### 0. The New 100-Signal Roadmap Can Reintroduce Overtrading

`docs/signal-roadmap-detailed.md` is useful as a pattern glossary and detailed appendix, but it should not become an execution allowlist. The project has already learned that "more valid-looking setups" is not the path to profitability. A roadmap that marks many categories as excellent can dilute the cost-aware discipline unless those labels are separated from project-validated edge.

Recommended action:

- Keep its current "reference/menu, not a build list" positioning.
- Add an evidence label to each signal: `validated`, `experimental`, `rejected`, or `not tested`.
- Do not let the AI approve a setup only because the manual labels it excellent.
- Keep the live allowlist small: core setups, selective CRT, and validated value-area rejection.
- Require every new signal family to pass spread-adjusted backtest and out-of-sample live review before it becomes eligible for live alerts.

### 1. The System Still Produces Too Many Low-Edge Families

`flags.json` currently leaves `momentum_impulse`, `zone_bounce`, `liquidity_sweep`, `vwap`, and `crt` enabled. The June backtest found only resistance-trendline breaks clearly cleared a 3-pip spread. The latest live log sample also shows:

| Setup | Recent result |
|---|---:|
| `CRT sweep+reclaim` | +111p, n=1 |
| `resistance-trendline break` | +100p, n=1 |
| `zone-bounce rejection` | -9p, n=4 |
| `momentum impulse` | -65p, n=5 |
| `liquidity-sweep reversal` | -70p, n=3 |

The profitable live sample is not broad-based. It is concentrated in a few large winners.

Recommended action:

- Treat `resistance-trendline break` as the current core setup.
- Keep `CRT` only when the review layer requires a large clean target, strong value-area context, and no immediate wall.
- Put `momentum_impulse` into observation or disable it for live alerts until a fresh out-of-sample sample proves it clears spread.
- Require stricter conditions for `zone_bounce` and `liquidity_sweep`: valid level state, confluence, clean room, and preferably with-trend or value-area regime support.

### 2. AI-Decide Mode Bypasses Most Blocking Filters

In `scalp_fast.py`, `ai_decide` is documented as bypassing all blocking filters except the hard floor. This is useful for surfacing context to an AI reviewer, but dangerous if the reviewer is not consistently applying a cost-aware standard.

Risk:

- The engine can surface signals that the hard filters would have blocked.
- The reviewer may approve visually attractive setups that are statistically low edge after spread.
- The system becomes dependent on subjective review quality instead of a measurable policy.

Recommended action:

- Keep the hard floor mandatory.
- Add an explicit cost-aware review checklist to every AI-reviewed signal:
  - expected clean room after spread
  - R:R to TP1 and TP2
  - setup-family historical expectancy
  - trade frequency budget for the day
  - whether this is a core setup or an exception
- Log the AI decision reason in structured fields, not only free text.

### 3. The Approval Model Is a Research Artifact, Not a Live Upgrade

`approval_model.py` still describes morning day efficiency as if it can gate the day early. The backtest findings later disproved this idea. This creates documentation/code-comment drift.

Recommended action:

- Add a clear warning at the top of `approval_model.py`: "Disproven out-of-sample; do not wire into live trading."
- Remove or reword comments that imply `day_efficiency()` is validated.
- Keep the module as a negative-result artifact unless a new dataset supports it.

### 4. Strategy Evaluation Should Be Cost-First

The older analysis focuses heavily on win rate, gross pips, and TP1-vs-SL. For gold scalping, the spread changes the conclusion. A high-frequency strategy with +0.4 gross pips per trade is losing after a 3-pip spread.

Recommended action:

- Make all analysis scripts report both gross and spread-adjusted results.
- Add a default cost assumption per symbol in `instruments.json`.
- Rank setup families by net expectancy after spread, not gross pips or win rate.
- Track opportunity cost: number of alerts, number of rejects, and number of actual trades per day.

### 5. Backtest and Live Samples Are Still Small

The backtest is 9 days and 537 signals, while recent executed live trades are only 17. This is useful but not enough to overfit precise thresholds.

Recommended action:

- Use rule changes only when they satisfy one of these:
  - strong logic plus out-of-sample confirmation
  - clear structural flaw, such as negative R:R
  - repeated loss family across backtest and live logs
- Target at least 30 executed trades per setup family before trusting live expectancy.
- Use walk-forward windows by week, not only pooled daily stats.

## Strategy Improvements

### Priority 1: Make Selectivity the Strategy

The engine should not aim to catch every move. It should aim to take the few trades with enough expected movement to beat spread and execution risk.

Suggested policy:

- Core live candidates:
  - resistance-trendline break with clean room
  - high-quality CRT only at meaningful liquidity/value-area context
  - value-area rejection only when level state is valid and VWAP bias agrees
- Exception candidates:
  - support-trendline break
  - Asian/session breakout with enough post-spread room
  - liquidity sweep only at a real HTF or prior VA level
- Avoid or observe:
  - generic momentum impulse
  - break-and-retest
  - low-confluence zone-bounce
  - VWAP-only rejection without value-area confirmation

### Priority 2: Add Setup-Family Budgets

Some setup types overproduce. Recent rejections show CRT and zone-bounce dominate rejected signals. Add daily caps so noisy families cannot keep asking for review.

Example:

| Family | Daily live cap | Notes |
|---|---:|---|
| resistance-trendline | 3 | core |
| CRT | 2 | only with clean room and valid context |
| zone-bounce | 1 | only A+ and valid level |
| momentum impulse | 0-1 | observation only |
| liquidity-sweep | 1 | only at real HTF/VA level |

### Priority 3: Improve CRT Selection, Not CRT Quantity

CRT is high volume and weak on average, but it can contain large winners. Do not disable it blindly. Instead require:

- sweep of a meaningful prior range/session/VA level, not just any rolling 15-bar block
- minimum TP2 room after spread
- no immediate opposing VAH/VAL/POC wall
- confirmation that the reclaim candle is not in the middle of value
- optional trend-day context, but do not rely on the disproven morning day gate

### Priority 4: Make Value-Area Rejection More Mechanical

`docs/gold-vwap-strategy.md` is clear: VAH/VAL are not automatic support/resistance. They require rejection and BOS.

Recommended engine improvements:

- Only allow VA rejection after `va_state` returns `Rejected` or `Flipped`, not merely `Untested`.
- Count tests per level and reduce confluence after repeated touches.
- Penalize signals near the middle of prior value.
- Log level role: `prevVAH`, `prevVAL`, `prevPOC`, `flipped_VAH`, `flipped_VAL`.

### Priority 5: Revisit Stop/Target Geometry

The system currently uses ATR-scaled TP/SL and adaptive walls. The backtest suggests SL/TP placement may matter more than many filters.

Recommended experiments:

- Compare current stop vs wick-based stop vs zone-far-edge stop.
- Test TP1 at 0.8R, 1.0R, 1.5R, and fixed 50p.
- Report net expectancy after spread for each setup family.
- Track maximum favorable excursion and maximum adverse excursion. This will show whether winners are being cut early or losers need earlier invalidation.

## Performance and Engineering Improvements

### 1. Split `scalp_fast.py`

`scalp_fast.py` is now large and mixes data fetching, signal detection, grading, trade management, logging, Telegram, overlays, and backtest hooks.

Suggested split:

- `scanner/context.py`: TradingView reads, indicators, current market context
- `scanner/setups.py`: setup detection functions
- `scanner/grading.py`: grade/confluence/risk evaluation
- `scanner/risk.py`: SL/TP, R:R, hard floor, sizing
- `scanner/state.py`: cooldown, active trade, pending review
- `scanner/output.py`: logs and Telegram

Keep behavior identical during the split. Do not refactor strategy rules and architecture at the same time.

### 2. Add Pure Unit Tests for Signal Decisions

The Node tests require TradingView for some suites, and Python `pytest` is not installed in this environment. Also, `python3 -m unittest discover` fails because `test_stale_zone.py` exits at import time.

Recommended action:

- Convert import-time script tests into normal test functions.
- Add pure tests for:
  - `hard_floor_skip`
  - `flag_for`
  - setup family classification
  - adaptive TP room calculations
  - VA level validity decisions
- Separate live TradingView integration tests from pure unit tests.

### 3. Make Test Commands Deterministic

Current verification result:

- `python3 analyze_logs.py --symbol XAUUSD --days 14` passed.
- `python3 analyze_logs.py --days 14` passed and showed 18 executed trades, +154 gross pips, +101 pips after spread, 1.50 gross PF, 1.29 net PF, and +5.6 net pips/trade.
- `python3 test_draw_overlay.py` passed with 17/17 checks, including overlay throttle state persistence.
- `python3 -m pytest -q` failed because `pytest` is not installed.
- `npm test` partially passed static Pine tests but failed live TradingView/CDP tests because TradingView is not connected on port 9222.
- `python3 -m unittest discover -p 'test*.py'` failed because `test_stale_zone.py` calls `sys.exit()` during import.

Recommended action:

- Add `npm run test:static` for tests that do not need TradingView.
- Add `npm run test:live` for CDP-dependent tests.
- Add a Python test runner script that runs only pure unit tests by default.
- Document required live-test preconditions.

### 4. Add Cost and Slippage to Outcome DB

Status: Done for schema support.

`outcome_db.py` now stores signal/result context plus cost and decision fields.

Completed fields:

- `spread_pips`
- `slippage_pips`
- `commission_pips`
- `gross_pips`
- `net_pips`
- `decision_source`: auto, AI, manual
- `decision_reason_code`

This will prevent future analysis from accidentally optimizing gross edge.

### 5. Fix Overlay Throttling

Status: Done.

`draw_overlay.py` now persists the timestamp used by `_recent()`, accepts an injectable state path for tests, and warns on empty draw results.

Completed action:

- Save `d[(chart or "_") + ":ts"] = time.time()` inside `_save_ids()`.
- Add a pure test that writes a temporary state file and verifies `_recent()` returns true after saving.
- Consider injecting the state path into the functions so tests do not touch the real `~/.tv_overlay_ids.json`.
- Log draw failures when `_tv()` returns an empty object, otherwise TradingView/CDP failures are silent.

## Operational Improvements

### 1. Create a Daily Review Workflow

After each trading day:

1. Run `python3 analyze_logs.py --symbol XAUUSD --days 1 --md`.
2. Review all executed trades by setup family.
3. Mark each trade as `A: followed plan`, `B: marginal`, or `C: should not repeat`.
4. Update a small denylist/allowlist policy only once per day, not during live trading.

### 2. Add a Weekly Strategy Scorecard

Track:

- net pips after spread
- executed trades
- rejected trades
- auto-skipped trades
- expectancy per setup
- expectancy per grade
- expectancy per hour/session
- biggest avoidable loss reason
- best missed trade reason

### 3. Protect Against Stale Assumptions

Several comments/docs mention ideas that were later disproven. Keep a single `NEGATIVE_RESULTS.md` or add a section to this file for:

- approval model was anti-calibrated out of sample
- morning day-efficiency gate was coin-flip
- ER is weak as a profit lever
- break-and-retest was uniformly bad in the tested sample

This prevents accidentally reviving rejected ideas.

## Recommended Next Changes

1. Add evidence tags to `docs/signal-roadmap-detailed.md` so the 100-signal roadmap cannot be mistaken for a validated live allowlist.
2. Disable or observation-gate `momentum_impulse` for live alerts until it proves cost-adjusted edge out of sample.
3. Add setup-family daily caps to reduce alert/reject volume.
4. Tighten `zone_bounce` and `liquidity_sweep` so they require valid HTF/value-area context, not just a visually plausible wick.
5. Add spread-adjusted metrics to `score_signals.py` and `backtest_multi_day.py`; `analyze_logs.py` is already done.
6. Split pure tests from TradingView-dependent integration tests in `package.json`.
7. Convert script-style Python tests to import-safe test functions.
8. Keep `break_retest` disabled and monitor `CRT` after spread with at least 20-30 more live examples.

## Bottom Line

The project should move from "detect many technical setups and let filters sort them" to "trade only setup families with enough expected movement to beat spread." The evidence points to a smaller, stricter strategy centered on clean trendline breaks, highly selective CRT, and mechanically validated value-area rejections.

Do not optimize for signal count or raw win rate. Optimize for net expectancy after spread, per setup family, with enough sample size to avoid overfitting.
