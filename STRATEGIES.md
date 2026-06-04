# XAUUSD Scalp System — Strategy Reference

Auto-monitor (`scalp_fast.py`) reads the **live 1m chart** every 60s, detects setups, grades them,
and pushes alerts to Telegram. Conventions: **1 pip = $0.10** (so 50 pips = a $5 move). 0.1 lot ≈ $1/pip.

---

## 1. Entry strategies (8) — each toggleable in `flags.json`

| # | Strategy | Flag | Trigger (needs a "strong" momentum candle*) |
|---|----------|------|---------|
| 1 | **Trendline break** | `trendline_break` | Strong candle closes through a line drawn across the last 2 swing highs (LONG) / lows (SHORT) |
| 2 | **Range / triangle breakout** | `range_breakout` | Tight 15-bar range (<35p) + strong close beyond the range high/low |
| 3 | **Double top / bottom** | `double_top_bottom` | Two equal swing highs/lows + strong break of the neckline |
| 4 | **Momentum impulse** | `momentum_impulse` | 2 consecutive strong same-direction candles (continuation) |
| 5 | **Liquidity-sweep reversal** 🥇 | `liquidity_sweep` | Price spikes through a recent extreme **that sits at a real HTF zone**, then closes **≥4p back inside** (stop-hunt + reclaim). *Gold's signature.* |
| 6 | **Break-and-retest** | `break_retest` | A broken swing level is retested from the other side and rejected |
| 7 | **VWAP rejection / bounce** | `vwap` | Strong rejection at / bounce off VWAP. Reads TradingView's **session-anchored VWAP + bands** off the chart (falls back to a computed rolling VWAP if the indicator's removed). Upper/lower bands act as mean-reversion levels (tag upper → short bias, lower → long bias). |
| 8 | **Asian-range / prior-day breakout** | `session_breakout` | Strong close beyond the Asian-session range or prior-day high/low |

*\*"strong candle" = body > **1.6× the average body of the last 20 candles** (adaptive to volatility).*

---

## 2. Grading (A+ / A / B / C)

Each signal is graded by how it aligns with a **level map** (HTF zones + dynamic levels):

- **A+** — momentum trigger **at** an HTF level in the *favourable* direction: a SHORT **rejecting** resistance, or a LONG **bouncing** off support. The best setups.
- **A** — a **genuine break** *through* a level (candle closes beyond it): LONG closes above resistance / SHORT closes below support.
- **B** — momentum in **open space** (no nearby level). `B+vol` if volume confirms.
- **C-into-zone** — a LONG poking *into* resistance, or SHORT *into* support, **without** a real break → **SUPPRESSED** (not fired). *(This is the fix for the "short into support" loss.)*

**Level map** = the drawn HTF zones (`HTF_R` / `HTF_S`) **plus** dynamic levels (when `extended_levels` on): **VWAP (+ bands), round numbers, prior-day H/L, Asian-range H/L**, and (when `ema_levels` on) **EMA 50 / 100 / 200**. VWAP and the EMAs are **read live from your chart indicators** (not computed); the scanner self-heals by re-adding any that get removed. EMAs are read at the chart's timeframe and labeled by length via a rank-match (the value used is always the chart's plotted value). **Proximity:** wide `HTF_R`/`HTF_S` zones count as "at level" within ±4 (`near_htf` tol); dynamic point-levels (VWAP/EMA/round/PDH/Asian) use a tight **±15 pip** halo (`DYN_TOL`) so a far-away VWAP no longer inflates a grade to A+.

---

## 3. Filters & gates (quality control)

| Filter | Flag | What it does |
|--------|------|--------------|
| **Volatility gate** | (always) | No signals unless the last 10 bars span ≥ **40 pips** (skip dead tape) |
| **Session filter** | `session_filter` | Outside London+NY (UTC 07–21), **only A+** trades pass |
| **News blackout** | `news_filter` | Mutes during manual `NEWS_BLACKOUT` UTC windows (set around NFP/CPI/FOMC) |
| **Volume confirmation** | `volume_filter` | Breakouts/breaks need **above-average volume**; reversals (sweep/retest/VWAP) exempt |
| **Range filter** | `range_filter` | Detects 15m **chop** via Kaufman efficiency ratio (`CHOP_ER=0.30`; ~1=clean trend, ~0=chop, computed from 1m bars resampled to 15m — no TF switch). In chop it **suppresses breakout/momentum/trendline/double entries** (false breaks in a range); reversals (sweep/VWAP/retest) stay. Directly targets the whipsaw-in-a-box losses. |
| **Anti-chase** | `anti_chase` | Skips a **continuation** entry (momentum/breakout/trendline/double) if price already ran **>60p** (`MAX_CHASE_P`) off the 6-bar base — stops buying the top / selling the bottom of a vertical spike. Reversals (sweep/VWAP/retest) are exempt (they fade extension). |
| **RSI exhaustion** | `rsi_filter` | Reads the chart RSI; blocks continuation **longs at RSI>78** / **shorts at RSI<22** (`RSI_OB`/`RSI_OS`) — don't chase a blow-off. Also: RSI **divergence** at a level upgrades a reversal to A+. |
| **Trend regime** | `trend_regime` | Bias from the **30m EMA stack** (50>100>200=UP) — read during the cached 30m visit, so it's immune to 1m pullbacks (1m is execution-only). **Counter-trend trades require A+**; with-trend pullbacks boosted; **heads-ups only pre-alert in the trend direction**. |
| **Adaptive TP/SL** | `adaptive_tp` | TP caps **8p short of the next horizontal structure** (`TP_BUFFER_P`); trade is **skipped if <25p clean room** (`MIN_ROOM_P`) — no more aiming +50 into a wall. EMAs/VWAP don't count as walls (price flows through them). |
| **Volume/TPO profile** | `volume_profile` | Reads your **Kioseff TPO** POC + value-area (VAH/VAL) — it only renders on a high TF, so the scanner briefly flips to 30m, **shows** the TPO, reads its letter-rows, **hides** it, and restores 1m (cached 20m; `try/finally` guarantees the chart never stays on 30m). Falls back to a computed 30m volume profile if unread. Levels added as confluence. |
| **Confluence** | `confluence` | When **≥2 levels stack** at price (e.g. VWAP+EMA+zone), the grade is strengthened (A→A+, B→A). Lone touches earn less. |
| **Cooldown** | (const) | After any signal, **no new signal for 5 min** (`COOLDOWN_MIN`) — anti-clustering |
| **Heads-up cooldown** | (const) | After a 👀 heads-up, **no re-ping for 12 min** (`WATCH_CD_MIN`) unless price moves >15p to a genuinely new zone — stops flip-flop spam when price wiggles across overlapping levels (round#/zone/VWAP band) |

---

## 4. Trade levels (TP / SL)

- **Entry:** the trigger candle's close
- **SL:** just beyond the invalidating structure, **capped at 30–35 pips**
- **TP1:** entry ± **50 pips**  ·  **TP2:** entry ± **100 pips**  *(currently fixed; adaptive-TP is planned)*
- **Management rule:** take partial at TP1 → SL to breakeven → trail. **Exit if TP1 not hit within ~10 min.**

---

## 5. Alert flow (Telegram)

1. **👀 SETUP FORMING** — price reaches a key zone (heads-up, prepare)
2. **🚨 CONFIRMED [side] [grade]** — trigger fired → Entry / SL / TP1 / TP2 + chart photo
3. **✅ TP1** → take partial / SL to BE  ·  **🎯 TP2** (+100p)  ·  **❌ SL**  ·  **🟰 BE after TP1** (remainder stopped at breakeven)

> **Logging integrity:** once **TP1** is banked, the stop moves to breakeven and the recorded outcome can only become **TP1** or **TP2** — a later reversal can never overwrite a partial win with an `SL` loss in `signals_log.csv`. This keeps the auto-learn dataset honest.

---

## 6. Reference levels (refresh ~daily — top of `scalp_fast.py`)

`HTF_R` / `HTF_S` are now **auto-refreshed**: `refresh_zones.py` derives them from D/4H/1H/15m swing pivots + EMAs + PDH/PDL + round numbers, clusters them into multi-touch zones, and writes `zones.json`. The scanner loads `zones.json` and **rebuilds it automatically every ~6h** (`ZONES_TTL`), falling back to the hardcoded `HTF_R`/`HTF_S` only if no file exists. Zone labels show touch counts, e.g. `4459.8 (15m+1H+round, x6)`. You can still force a rebuild any time: `python3 refresh_zones.py`. `ASIA_H`/`ASIA_L`, `SESSION_UTC`, `NEWS_BLACKOUT` remain manual.

---

## 7. File map

| File | Purpose |
|------|---------|
| `scalp_fast.py` | The live 1m scanner (this doc's logic). Run with `--dry` to test, `--draw` to plot trendlines |
| `scalp_scan.py` | Alternative 15m zone-rejection scanner (auto-derives S/R) |
| `flags.json` | Feature flags (true/false per strategy & filter) |
| `signals_log.csv` | Every signal + features + outcome (auto-learn dataset) |
| `journal_trade.py` | Per-trade folder: chart + per-TF notes + `trades/journal_log.csv` |
| `backtest_day.py` / `backtest_tp.py` | Replay over recent 1m / TP-target sweep |
| `telegram_config.json` | Bot token + chat_id (send-only) |
| `tg_monitor.sh` | start/stop/status the autonomous launchd monitor |
| `~/Library/LaunchAgents/com.yassir.goldscalper.plist` | Runs the scanner every 60s on the Mac |

---

## 8. Known limitations / planned

- **Auto-learn loop** — `signals_log.csv` collects the data; periodic win-rate/expectancy analysis + supervised tuning is the roadmap. **Collect ~20–30 real trades before tuning from outcomes.**
- **Zone-reclaim trigger** (`zone_reclaim`, **default OFF**) — built + backtested. A non-impulse dip-into-zone-then-reclaim trigger. Backtest finding: confirmation **inherently lags** — by the time a gradual bounce closes back out of the zone it's already ~80–110p extended, where **anti-chase blocks it** and the entry sits in the next resistance. So a *confirmed* reclaim can't catch the dip. **The real fix is an anticipatory zone-touch entry** (buy the A+ support touch with a tight stop, before confirmation) — a different risk model (more failed-bounce losses, but catches the move from the bottom). Pending user's call on confirmed-vs-anticipatory.
- **No news feed** → blackout is a manual time list.
- **Asian range** (`ASIA_H`/`ASIA_L`) still manual — set near London open.
- Multi-timeframe *screenshots* unreliable on this desktop build — journal uses one annotated chart + written per-TF notes.

*Strategy logic lives in `scalp_fast.py`; this doc summarizes it. Re-read after major changes.*
