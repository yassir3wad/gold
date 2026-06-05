# Gold Scalper — Backtest & Approval-Model Findings (June 2026)

**Author:** Yassir Awad · **Date:** 2026-06-05
**Goal:** make the gold-scalp engine profitable and the AI review accurate (more winning trades/day).
**TL;DR:** The decisive finding (§10): the **average signal's gross edge (≈0p/trade) is far below the
gold spread (~3p)** — so high-frequency "trade-everything" scalping is *structurally* unprofitable; costs
dominate. **Selectivity is therefore mandatory, not optional** — the only path to profit is taking the
*few* setups whose per-trade edge clears the spread. Only **resistance-trendline breaks** do so robustly
(+7.5p gross → +4.5p net, n=35); the high-volume families (CRT, zone-bounce, momentum) are cost-negative.
This also explains why no filter beat trade-all in *gross* pips (wrong objective) and why selective manual
trading wins (it takes the big ones). Secondary findings: can't filter to profit on win-rate features
(calibrated model is anti-calibrated OOS); day-type dominates but isn't early-predictable; ER (any frame)
is weak; SL geometry tilts toward tighter stops (7/9 days) but the gross gain is also < spread.

---

## 1. Method — faithful replay backtest

To avoid logic drift, we drive the **real `scalp_fast.py`** over a TradingView replay tab candle-by-candle
(exactly like the live per-minute cron) rather than re-implementing the engine.

- `replay_sim.py` — steps a past day on a **dedicated** replay chart (`eFMec2F9`), runs the real scanner
  at each 1m step, captures every surfaced signal with its on-chart context (RSI, regime, 15m-ER, session,
  room). Isolated from the live loop via `TV_CHART_OVERRIDE` + `STATE_SUFFIX` (live charts untouched).
- `score_signals.py` — for each signal, simulates forward: did **TP1 or SL hit first** within a 15-bar
  horizon? Splits by the reconstructed discipline (`verdict()`), reports win% and net pips.
- `boundary.py` — feature→outcome boundary analysis + the anti-predictive leak / false-positive cells.
- `calibrate.py` — leave-one-out (LOO) validation + threshold sweep: model vs discipline vs trade-all.
- `er_probe.py` — recomputes fast ERs (30/45/60m) at each signal to test the "3h ER is too slow" thesis.
- `approval_model.py` — the outcome-calibrated approval model under test (see §4).

**Dataset:** 9 trading days, **537 signals (492 resolved TP1/SL)**, XAUUSD, window 06:00–23:00 UTC.

---

## 2. The dataset — day-type dominates everything

| Day | Type | net (all sigs) | n | win% (TP1-vs-SL) |
|-----|------|----------------|---|------|
| 2026-05-25 | TREND | +116p | 42 | 50 |
| 2026-05-26 | chop  | −73p  | 46 | 40 |
| 2026-05-27 | TREND | +7p   | 80 | 42 |
| 2026-05-28 | chop  | **−383p** | 91 | 33 |
| 2026-05-29 | TREND | +267p | 68 | 46 |
| 2026-06-01 | TREND | **+529p** | 65 | 50 |
| 2026-06-02 | chop  | −165p | 17 | 13 |
| 2026-06-03 | chop  | −93p  | 47 | 44 |
| 2026-06-04 | chop  | −123p | 81 | 41 |

**4 trend / 5 chop days. Trade-everything ≈ breakeven** (+82p all-signals incl. timeouts, −98p resolved-only).
The single +529 day is nearly cancelled by the single −383 day. **P&L is dominated by which day-type you
catch, not which signals you pick.** This recurs throughout every analysis below.

---

## 3. The current discipline is net-HARMFUL as a hard filter

`verdict()` reconstructs the rule-layer gates (off-session, ER floor, counter-trend veto, RSI-extreme veto).

| Policy (9d, resolved) | n | win% | net |
|---|---|---|---|
| trade everything | 492 | 42% | −98p |
| **discipline APPROVE** | 63 | 41% | **−196p** |

The filtered set is **worse** than trading everything, with no win-rate gain. The vetoes remove value.

> **Caveat (important):** `verdict()` is the *reconstructed rule-set*, not the live Claude review.
> The live system runs `ai_decide:true` — Claude's judgment is more nuanced than these hard rules, and
> a live-approved trade on 2026-06-05 hit **TP1+TP2 (+111p)**. So this indicts the **hard-coded gate
> layer**, not the live reviewer. The actionable read: the static vetoes are a poor pre-filter.

The **anti-predictive leak** (signals the rules rejected that actually won) was large in the 4-day window
(+2012p of rejected-but-won), concentrated in counter-trend dip-buy reclaims that the counter-trend veto
killed. Counter-trend was *not* a disqualifier in the data; the RSI-extreme veto was backwards (RSI
extremes won, mid-RSI 45–55 lost hardest).

---

## 4. The outcome-calibrated approval model — built, tested, and DISPROVEN

`approval_model.py`: a transparent stdlib win-rate table keyed on
`(setup-family, trend-alignment, RSI-bucket, session, day-context)` with hierarchical backoff
(cell → family → global) and Laplace smoothing. Off-session stays a hard veto; otherwise approve on
calibrated confidence ≥ threshold. **35 unit tests pass.** Degrades gracefully on unseen cells.

**Verdict: it does not work.** Leave-one-out (train on 8 days, score the 9th):

- At every threshold it **loses to trade-all**; the threshold sweep is **non-monotonic** (a red flag).
- **Reliability curve is anti-calibrated** — higher model score → *lower* actual win rate:

  | model score | n | actual win% | net |
  |---|---|---|---|
  | ~0.30 | 72 | 39% | −153p |
  | ~0.35 | 87 | 46% | +286p |
  | ~0.40 | 181 | 41% | −233p |
  | ~0.45 | 96 | 36% | −144p |

  Score ≥0.42 → **35% / −323p**; score <0.42 → **43% / +89p**. The model is *confidently wrong*.

**Why:** the per-signal features don't rank these scalps by win probability. Edge lives in day-type,
and day-type can't be learned from a per-signal table on 9 heterogeneous days. **Conclusion: do not wire
the model into the engine.** Kept as a research artifact + negative result.

### 4b. Morning day-type gate — also disproven
`day_efficiency()` = morning (06–09 UTC) displacement/range, intended to flag trend days early.
Across 9 days it's a **coin flip (5/8 at the 0.5 line)** and *misses real trend days* (05-29 +267p scored
0.284 → would skip; 06-03 −93p scored 0.528 → would trade). The clean 06-01 reading (0.672) was a
coincidence. **Morning directional efficiency does not predict day-type.**

---

## 5. The ER frame probe — "is 3h too slow for scalps?"

Hypothesis (well-reasoned): the 15m-ER spans ~3h (12 × 15m closes); for a 1m scalp with a ~10-min TP it
lags, passing **stale** signals (3h says trend, last 20m reversed) and possibly **hiding** fresh ones.

We recomputed faster Kaufman ERs (30/45/60m) at each signal time and tested discrimination + agreement.

**(a) Every ER frame is a weak outcome discriminator** (win% spread, high-third minus low-third):

| frame | low-third win% | high-third win% | spread |
|---|---|---|---|
| 3h (current) | 40 | 43 | **+3** |
| 30m | 39 | 45 | **+6** |
| 45m | 41 | 45 | +4 |
| 60m | 43 | 42 | −1 |

The 30-min ER is **marginally** more predictive than the 3h, but a 6-point spread is far too small to
build profit on. ER, in any frame, barely separates winners from losers.

**(b) Stale-signal test** (trend = ER≥0.5):

| 3h | 30m | n | win% | net |
|---|---|---|---|---|
| trend | trend | 8 | **62%** | +78p |
| trend | chop  | 138 | 41% | +19p |
| chop  | trend | 11 | **27%** | −78p |
| chop  | chop  | 335 | 42% | −117p |

Requiring **both frames to agree on "trend"** gives 62% — a real edge, but only **8 of 492 signals**.
It's a *precision* gate (kills stale "3h-trend / 20m-chop" longs like the US30 case), not a way to
surface more trades.

**(c) Hiding-signals test:** fired signals with 3h-ER<0.20 (floor-adjacent) actually **win modestly
(48% / +64p, n=25)** — so the hard floor may be slightly over-tight. *But* the signals a fast-ER OR-gate
would *add* (3h-chop + fast-trend) **lose (27% / −78p)**. Loosening ER to "unhide" signals would admit
losers.

**ER conclusion:** the 3h frame is indeed lagging, and 30m is slightly better — but **ER is not where the
profit lever is.** A 30m+3h *agreement* gate could improve precision (drop stale signals) at a steep
recall cost; it would *not* free up a lot of good signals (the freshly-trending-but-3h-chop ones lose).

---

## 6. THE robust per-signal lever — setup family

The one feature that separates winners from losers consistently across all 9 days:

| setup family | n | win% | net |
|---|---|---|---|
| resistance-trendline | 35 | 49% | **+264p** |
| CRT (sweep+reclaim) | 235 | 42% | +86p |
| support-trendline | 37 | 46% | +71p |
| liquidity-sweep | 5 | 60% | +21p |
| zone-bounce | 77 | 44% | −32p |
| VWAP | 13 | 31% | −40p |
| **break-and-retest** | 10 | **0%** | **−241p** |
| **momentum (impulse)** | 70 | 37% | **−269p** |

**Two families account for −510p of losses (momentum −269, break-and-retest −241).** Suppressing just
those two turns trade-all from −98p to **≈ +412p** over 9 days. Both are *categorical* (setup type), so
this is far more robust than a fragile continuous threshold.

**Per-day robustness (important nuance):**
- **break-and-retest** is **uniformly negative** — every day it fires it loses or breaks even (n=10 total,
  worst 06-03 −96p). Thin sample, but zero upside on any day. *Suppressing it is pure downside-removal.*
- **momentum-impulse** loses on **7 of 9 days** (−269p net) **but earns +85p on 05-25, a trend day**
  (8/14 W). It is *not* uniformly bad — it bleeds on chop days and pays on the right trend day. It's also
  the engine's namesake ("FAST momentum scalp scanner … 50–100 pip bursts"). *Suppressing it is net +EV
  over 9 days but sacrifices trend-day bursts* — a genuine trade-off, not a free win.

The engine already partially suppresses breakout/momentum below `CHOP_ER=0.30`, but momentum still fired
70× — the ER suppression isn't reaching them. Both families are gated by existing `flags.json` switches
(`momentum_impulse`, `break_retest`) via `flag_for()` at `scalp_fast.py:788` — suppression needs **no code
change**, only a flag flip.

---

## 7. Bottom line & next levers

1. **You cannot filter to profit with these context features** (ER/RSI/alignment/session/day-context).
   The calibrated model is anti-calibrated OOS; the day-gate is a coin flip; the discipline is net-harmful.
2. **Day-type dominates P&L** and is not predictable early from the features tried. Trade-all ≈ breakeven.
3. **Highest-confidence, lowest-risk lever: suppress the losing setup families** (momentum-impulse,
   break-and-retest). Big, robust, categorical, theory-consistent. ← acted on next (flagged, TDD).
4. **Second lever: SL/TP/R:R placement.** 42% TP1-vs-SL on ~1.4 R:R is breakeven by construction; small
   changes to where stops/targets sit move P&L more than any approval filter.
5. **ER:** optionally add a 30m ER as an *agreement* gate to kill stale signals (precision), accepting
   lower recall. Marginal; lower priority than #3/#4.
6. **Do NOT** ship the approval model or the morning day-gate to the live engine.

---

## 10. THE DECISIVE FINDING — per-trade edge vs spread (cost-aware)

Everything above measured **gross** pips. The moment you subtract the **gold spread (~3p/trade round-trip,
~$0.30)**, the picture inverts and clarifies (`sltp_probe.py` + per-family cost analysis):

- **Average signal: −0.2p/trade gross → −3.2p/trade after spread.** Trade-everything is deeply negative
  once costs are real. The earlier "trade-all ≈ breakeven" was a *gross*, cost-free illusion.
- **SL geometry:** tightening the stop to 0.75× structure is +1.2p/trade gross and beats current on 7/9
  days (robust) — but +1.2p is still **below the ~3p spread**. Geometry tuning alone can't save a
  high-frequency book; a **0.2-price-unit spread already flips it negative.**

**Per-family edge vs a 3p spread — only a few clear costs:**

| family | n | gross/trade | net/trade (−3p) | clears? |
|---|---|---|---|---|
| resistance-trendline | 35 | +7.5p | **+4.5p** | ✅ robust |
| Asian-range | 6 | +6.2p | +3.2p | ✅ thin |
| liquidity-sweep | 5 | +4.2p | +1.2p | ✅ thin |
| support-trendline | 37 | +1.9p | −1.1p | ✗ marginal |
| **CRT** | **235** | **+0.4p** | **−2.6p** | ✗ (highest volume!) |
| zone-bounce | 77 | −0.4p | −3.4p | ✗ |
| VWAP | 13 | −3.1p | −6.1p | ✗ |
| momentum | 70 | −3.8p | −6.8p | ✗ |
| break-and-retest | 10 | −24p | −27p | ✗ (suppressed) |

**The unifying conclusion — selectivity is the strategy, because the edge is thin vs cost:**

1. The per-trade edge is ~0–1p; the spread is ~3p. **You cannot win by trading often.** Profit requires
   taking *few* trades whose individual edge is large enough to clear the spread.
2. **The filter's true objective was never win-rate — it's per-trade edge size (pips after cost).** That's
   why the calibrated model (optimizing win probability on thin-edge signals) failed, and why no filter
   beat trade-all in gross pips.
3. **The robust profitable core is resistance-trendline breaks** (+4.5p/trade net, n=35). The high-volume
   families (CRT 235×, zone-bounce, momentum) are cost-negative *on average* — but **CRT is high-variance
   and contains the big winners** (the live 2026-06-05 +111p was a CRT sweep+reclaim). So CRT should not be
   suppressed wholesale; the job is to catch its big-edge instances, not trade all 235.
4. This is why **selective manual/AI-reviewed trading wins while the firehose loses** — and it tells the
   review exactly what to optimize for: *big clean moves that clear the spread*, concentrated in
   trendline-breaks / sweeps / trend-day CRT, not marginal win-rate on the chop-bound majority.

**Implications for the engine/review:**
- Favor (or weight up) **resistance/support-trendline breaks, liquidity sweeps**; treat the high-volume
  low-edge families as "need a *big* reason" rather than default-tradeable.
- The AI review should select for **expected pips after cost**, not probability of a small win.
- Reduce trade *count*; the math rewards fewer, larger-edge trades. (`break_retest` already off.)

## 8. Artifacts

**New modules (committed to `main`):**
- `approval_model.py` (+ `test_approval_model.py`, 35 tests) — calibrated approval (disproven, kept as ref)
- `boundary.py` — feature→outcome boundary analysis
- `calibrate.py` — LOO validation + threshold sweep
- `er_probe.py` — ER-frame discrimination test
- `replay_sim.py`, `score_signals.py`, `collect_bars.py` — the replay backtest harness (merged earlier)
- `outcome_db.py` (+ migration, tests) — SQLite outcomes/log layer (PR #8, merged)

**Data:** `/tmp/replay_sim_<date>.json` + `/tmp/bars_<date>.json` for 2026-05-25..29 and 06-01..04.

**Reproduce:**
```bash
python3 calibrate.py 2026-05-25 2026-05-26 2026-05-27 2026-05-28 2026-05-29 \
                     2026-06-01 2026-06-02 2026-06-03 2026-06-04
python3 er_probe.py
python3 boundary.py 2026-05-25 ... 2026-06-04
```

## 9. Open questions
- Does a wider set (more weeks, more trend days) reveal an *early* day-type signal we haven't found?
- Does suppressing momentum/break-and-retest hold out-of-sample on fresh days? (validate before/after live)
- What SL/TP geometry moves the 42% TP1-vs-SL win-rate above the breakeven line for a given R:R?
- PR #7 (Risk Engine) held — 4 gates non-functional (wrong log path, pip→USD ~100× off, case mismatch),
  default-on with a dead flag. Low priority; fix only after the above.
