---
name: scalp-suite
description: Simple router for the 4 TradingView scalp layouts: VWAP, Volume Profile, SBS, Peak Activity Range, Liquidity Delta Provider. Use one strategy/layout per run, with mechanical ENTER/WAIT/REJECT rules. Supersedes discretionary-trade for scalps.
---

# Scalp Suite

This is the operating router. Do **not** run all strategies at once. Pick one strategy, open its layout, and execute its checklist.

## Layouts

| Strategy | Layout | Use |
|---|---|---|
| `OFVWAP` | `VWAP` | VWAP/band sweep, reclaim, pullback, rejection |
| `VP_NODE` | `Volume Profile` | VP edge rejection or LVN continuation |
| `SBS` | `SBS` | Trend-day 5-point breakout sequence |
| `PAR_LDP` | `Peak Activity Range` then `Liquidity Delta Provider` | PAR location + LDP trigger |

Fallback only: if a layout is unavailable, show only the required indicator(s). Never stack heavy profile tools.

## One Decision Contract

Every decision must be one of:

```text
WAIT | ENTER | REJECT | MANAGE
```

Every trade must state:

```text
strategy, layout, regime, location, trigger, entry, SL, TP1, TP2, R:R_to_TP1, result
```

If any field is unknown, `WAIT`.

## Universal Rules

1. Use real-volume feed, preferably `PEPPERSTONE:XAUUSD` for gold.
2. One strategy per session. No mixed triggers.
3. Regime first:
   - `TREND`: prefer SBS or with-trend VWAP pullbacks.
   - `RANGE`: prefer OFVWAP band fades, VP edges, PAR/LDP sweeps.
   - `CHOP/DEAD`: no trade.
4. Trade only at a real location: band, VWAP, VP edge/node, PAR edge, BSL/SSL, SBS P5/sequence level.
5. Trigger must be a closed candle or confirmed indicator label/box. Wick alone is not enough.
6. SL must be beyond the real invalidation. Never put SL inside noise to force R:R.
7. TP1 must have clean space to the next blocking level. If blocked before minimum TP1, reject.
8. Verify fills with OHLCV, not screenshots.
9. Step one bar at a time during active trading. Batch-step only through dead time.
10. Do not use SMC/TPO/CRT/discretionary-trade rules in scalp-suite.

## Gold Scaling

Gold convention: `1.00 price = 10 pips`.

| Item | Gold Rule |
|---|---|
| Normal scalp SL | max `50p` / `5.0` price points |
| TP1 | `70-100p` if path is clean |
| TP2 | next structure only |
| BE | after TP1 partial or after +40p with minor structure cleared |

For FX, use the instrument scaling table only if explicitly running FX. Do not apply gold targets to EUR/GBP/etc.

## Strategy Router

### OFVWAP

Use `VWAP` layout.

Checklist:
1. 15m defines regime and VWAP slope.
2. 5m gives entry.
3. Valid long: lower band sweep/reclaim, or close back above VWAP after rejection.
4. Valid short: upper band sweep/reclaim, or VWAP rejection from below.
5. Reject if price is glued to VWAP, bands are tight, or stop cannot fit beyond sweep.

### VP_NODE

Use `Volume Profile` layout. **Indicator = native Session Volume Profile HD** (the LuxAlgo Node-Detection VP was removed —
it crashed/wouldn't render). Read POC/VAH/VAL/HVN/LVN **visually** (native VP has no data API).

Checklist:
1. Trade only VP edge, LVN edge, or clear HVN/POC rejection.
2. Valid edge reversal: sweep edge then close back inside.
3. Valid continuation: strong close through level into LVN/thin area.
4. Reject POC/HVN middle, value middle, or TP1 blocked before minimum.

### SBS

Use `SBS` layout.

Checklist:
1. Use only on trend/expansion days.
2. Wait for P1-P5 sequence completion.
3. Enter only after confirming breakout close or retest hold.
4. SL beyond P5. If P5 stop is too wide for a scalp, skip or reclassify as wider intraday.
5. Reject on range/chop days.
6. ⚠ Backtest read caveat: `data_get_pine_labels` returns ALL sequences including FUTURE-drawn ones (can't be cleanly filtered to "as of the replay cursor"), and the 50-label cap is by draw-order not time. So SBS is NOT reliably no-hindsight readable via the API in replay — confirm the live sequence visually (it is visible on-screen live). Use the P5 level as the trigger line and require a closed-candle break beyond it.

### PAR_LDP

Use `Peak Activity Range` layout first, then `Liquidity Delta Provider`.

Checklist:
1. PAR gives location: range high, range low, breakout/retest level.
2. LDP gives trigger: BSL/SSL sweep plus ABS/EXH/DIV/REJ or delta recovery.
3. Valid long: PAR low/SSL sweep, close back in, bullish LDP confirmation.
4. Valid short: PAR high/BSL sweep, close back in, bearish LDP confirmation.
5. Reject PAR middle/POC, consumed zone, missing LDP trigger, or blocked TP1.

## Backtest Contract

Backtest exactly one strategy and one day per session.

1. Open the correct layout.
2. Start replay on the target date.
3. Verify date, symbol, timeframe, and OHLCV spacing.
4. Walk active session one bar at a time.
5. Log every checkpoint as `WAIT/ENTER/REJECT/MANAGE`.
6. Track entry, SL, TP1, TP2 from OHLCV.
7. Stop after the day is complete.

No future candles. No forced trades. No mixed strategy logic.

## Backtest Layout & Toggle Discipline

**Use the `backtest` layout for all backtests.** It is the single chart that holds every strategy's indicator, and it is the
chart the MCP data API reads. (The MCP binds to one chart target and cannot be re-pointed via `tab_switch`/`layout_switch`, so
all backtest reads must come from this one layout. The separate per-strategy layouts are for live focus, one strategy per screen.)

### 🔑 HARD RULE — only ONE indicator visible at a time; hide before you show
Multiple heavy profiles rendering at once is what crashed the chart (VP-Node "memory limits exceeded"). So:

- **Before showing any indicator, FIRST hide the currently-visible one.** Never reveal a second indicator while another is
  still visible. One on screen at a time, always.
- Sequence at each decision point: `hide current → show next → read it → hide it → show next …`.
- This applies to every indicator on the `backtest` layout (treat all as exclusive — hide-before-show), which prevents the
  stacking crash that led to separating them in the first place.

### 🔑 READ PROTOCOL — visual-first; pull data only when it prices the trade
Default read = **`capture_screenshot` then view it** (zoom to the active swing for fine labels). Screenshots are cheap, current,
and avoid the no-hindsight/future-label problem.
- ⚠ **Settle delay:** after `indicator_toggle_visibility`, **wait ~2–3s before `capture_screenshot` (method `cdp`)** — capturing
  immediately grabs a stale/pre-render frame (the indicator hasn't drawn yet). With the delay, cdp frames are clean and current.
  (`method: "api"` does NOT return a file — only `cdp` gives a readable path. The profile indicators DO render fine; the earlier
  "doesn't render" was just capture-too-fast.) Only pull the DATA API when you need exact numbers to place/manage a trade,
and only the cheap reads:
- **Expensive / no-API → ALWAYS visual:** SBS labels (~hundreds), **PAR boxes (~hundreds)**, and the **Volume Profile**
  (now native **Session Volume Profile HD** — no data API at all). Read sequence / range / profile off the (zoomed) chart.
- **Cheap + precise → data, only when it matters:** OFVWAP `data_get_study_values` (VWAP/band levels for entry/SL) and the
  **current bar `data_get_ohlcv`** (exact price for fills/stops).
- Rule of thumb: **screenshot to SEE the setup (location, is-there-a-signal); data to PRICE it.** Eyeball is fine for "at the
  band? / sequence resolving?"; exact entry/SL/TP come from OHLCV + OFVWAP values.
