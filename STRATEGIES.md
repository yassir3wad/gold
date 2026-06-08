# XAUUSD Scalp System — Strategy Reference

Auto-monitor (`scalp_fast.py`) reads the **live chart** every 60s on the **5m execution timeframe**
(`BASE_TF`, was 1m), detects setups, grades them, and pushes alerts to Telegram. Conventions: **1 pip =
$0.10** (so 50 pips = a $5 move). 0.1 lot ≈ $1/pip.

---

## 1. Entry strategies — each toggleable in `flags.json`

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
| 10 | **Zone-bounce** 🛡️ | `zone_bounce` | Rejection candle that **pierces a structural S/R zone and reclaims it** (≥15p wick, `ZONE_WICK_P`) — **no "strong" candle or 2-bar pattern needed**, so it catches *gradual* bounces the momentum triggers miss. Only at real zones (not clingy EMA points); tight stop at the rejection wick. |
| 9 | **Session liquidity sweep** 🌊 | `session_sweep` | A session **raids the prior session's high/low** (resting stops) then reverses back inside — the Asian-range raid / *Judas swing*. Watches real session pools (Asian / London / NY H-L + prior-day H-L), **time-gated** to the genuinely-prior session (during London → Asian; overnight → NY). Strong wick beyond the pool + close ≥4p back inside. |
| 11 | **Key-level rejection** | `key_level_trades` | A classic **Key-Level (KL)** is a trade location, not only confluence. LONG at a KL buy/support zone or SHORT at a KL sell/resistance zone fires when the latest candle rejects the level directionally (≥15p wick by default). It still must pass hard-floor R:R/chop/session/review gates. |
| 13 | **VWAP value-area rejection** 📐 | `va_reject` | The VWAP-bias strategy (`docs/gold-vwap-strategy.md`) as a first-class trigger, not just AI context. **LONG:** price **above/reclaiming VWAP** + a confirmed **rejection** off a **valid** prior **VAL / POC** (held) or a **flipped VAH** (now support) + **R:R ≥ 1:2** to the nearest VWAP/POC target; stop below the rejection wick. **SHORT** mirrors (below VWAP; VAH/POC/flipped-VAL). Validity (held/flipped vs *accepted*) and the rejection pattern come from `va_state` (Rules 6/7). Reversal-class (exempt from volume/anti-chase). |
| 12 | **CRT — Candle Range Theory** 📦 | `crt` | The prior 15m block is the **"range candle"**; the last ~5 1m bars **sweep its high or low** (liquidity grab) and the last candle **closes back INSIDE** the range = manipulation + reversal (ICT/PO3 model). Sweep *below* low → LONG, sweep *above* high → SHORT. Stop just beyond the swept wick; target the **opposite end of the range** (opposite liquidity). Distinct from `liquidity_sweep` (which needs an HTF zone): CRT keys off the range-candle extreme and **only fires with ≥25p room to the opposite end** — a built-in R:R floor that fixes the "no-room into structure" misses. Reversal-class: exempt from volume filter & anti-chase, stays live in chop. |
| 14 | **Fib correction pullback** | `fib_pullback` | After a clear impulse leg, draw fib in the direction of the wave: **SHORT** top→bottom on a down wave; **LONG** bottom→top on an up wave. A setup fires only when price pulls back into the primary correction pocket **0.52–0.645** and prints a directional rejection wick (default ≥6p×VS). Stop goes beyond the rejection wick; existing adaptive TP/R:R/hard-floor logic decides whether it is tradeable. |

*\*"strong candle" = body > **1.6× the average body of the last 20 candles** (adaptive to volatility).*

---

## 2. Grading (A+ / A / B / C)

Each signal is graded by how it aligns with a **level map** (HTF zones + dynamic levels):

- **A+** — momentum trigger **at** an HTF level in the *favourable* direction: a SHORT **rejecting** resistance, or a LONG **bouncing** off support. The best setups.
- **A** — a **genuine break** *through* a level (candle closes beyond it): LONG closes above resistance / SHORT closes below support.
- **B** — momentum in **open space** (no nearby level). `B+vol` if volume confirms.
- **C-into-zone** — a LONG poking *into* resistance, or SHORT *into* support, **without** a real break → **SUPPRESSED** (not fired). *(This is the fix for the "short into support" loss.)*

**Confidence (0–10)** — the letter grade ceilings at A+, so a 5-factor monster and a bare A+ look identical. `confidence.py` aggregates **every** axis (grade + level-map confluence count + SMC/Auto-Trendline score + RSI divergence + with/counter-trend + R:R≥2 + a valid prior-VA Level State) into a 0–10 score, shown in the readout and alert (`confidence N/10 (very-high/high/medium/low)`). With `confidence_sizing` **on** (default OFF), it scales position size: high-confidence trades risk up to `CONF_SIZE_HI`×, low ones down to `CONF_SIZE_LO`× the base `RISK_USD`; off, sizing stays fixed-risk.

**Classic supply/demand + S/R zones** (`classic_zones`, default ON) — the origin-candle buy/sell zones, Key Levels, and support/resistance levels from `zones_sd.py` (the ones `draw_review` draws) are now a **first-class part of the level map**: `refresh_zones` builds them hourly via the shared `zones_sd.build_classic_zones` (4h+1h) and writes `sd_zones`/`sd_sr` to the zone file; `scalp_fast` merges **buy zone/support → `HTF_S`** and **sell zone/resistance → `HTF_R`**, so they flow through `at_R/at_S`, `conf_R/conf_S` and the target picker. A **Key-Level (KL)** classic zone in the trade direction at price is the **top-probability tier**: with `key_level_trades` ON, a directional KL rejection can create its own trade candidate; as confluence it adds a hard **+2** (→ A+), shown as `⭐KL`. Engine + drawing share one builder, so **what's drawn is exactly what's graded.** Spec: `docs/zones-and-confluence.md` §3.5 + `docs/sd-zone-algorithm-spec.md`.

**Fib pullback confluence** (`fib_pullback`, default ON) — when any setup fires while price is rejecting the active **0.52–0.645** correction pocket in the same direction, the fib context adds one confluence tier (**B→A**, **A→A+**) and the alert/readout includes the fib pocket plus the wave anchors. It is not a free pass: `C-into-zone`, poor R:R, dead chop, off-session, and family caps still apply.

**Level map** = the drawn HTF zones (`HTF_R` / `HTF_S`, now incl. the classic zones above) **plus** dynamic levels (when `extended_levels` on): **VWAP (+ bands), round numbers, prior-day H/L, Asian-range H/L**, and (when `ema_levels` on) **EMA 50 / 100 / 200**. VWAP and the EMAs are **read live from your chart indicators** (not computed); the scanner self-heals by re-adding any that get removed. EMAs are read at the chart's timeframe and labeled by length via a rank-match (the value used is always the chart's plotted value). **Proximity:** wide `HTF_R`/`HTF_S` zones count as "at level" within ±4 (`near_htf` tol); dynamic point-levels (VWAP/EMA/round/PDH/Asian) use a tight **±15 pip** halo (`DYN_TOL`) so a far-away VWAP no longer inflates a grade to A+.

---

## 3a. Previous Value Area framework — AI judgment (Rules 1–7)

When a signal sits **at/near a prior-day VAH / POC / VAL**, the AI review applies the value-area framework
(full rules: `docs/value-area-framework.md`). The engine prints the inputs the rules need, so the AI judges
rather than recomputes:
- `prevVA[open-vs-value]: …` — the **regime** (Rule 3–5): `discovery-UP` (price above the most-recent prevVAH),
  `discovery-DOWN` (below prevVAL), or `balanced` (inside prev value).
- `prevVA <MM-DD>: VAH x (above/below Np) | POC … | VAL …` — each prior level's side + pip distance
  (Rules 1/2/7).
- `regime=UP/DOWN/flat` (30m EMA stack) — the trend for Rules 1/2.

**Judgment directives:**
1. **With-trend (Rules 1/2):** in an **up** trend, take longs only at a **VAL/POC below** price or a **VAH acting
   as support**; in a **down** trend, shorts only at a **VAH/POC above** price or a **VAL acting as resistance**.
   Require a rejection/confirmation (rejection candle, BOS in the trade direction).
2. **Open-vs-value (Rules 3–5):** `discovery-UP` → favour longs on a **VAH pullback + rejection** (target POC →
   single prints → weekly VAH); `discovery-DOWN` → shorts at **VAL**; `balanced` → **fade extremes toward POC**,
   don't chase the center.
3. **Validity (Rule 6):** treat a prior VA as **invalid** (don't trade its first touch) if price has put **2+ closes
   beyond it** or is **developing new value beyond it** — judge from recent bars.
4. **Selection (Rule 7):** prefer the **nearest active** prevVAH above / prevVAL below; skip levels tested **>3×**,
   that lost their POC, or were traded clean through by a later session.

**Data we lack:** delta and footprint absorption aren't available — substitute **closes-beyond + rejection wicks**
as the acceptance/rejection proxy. Invalidation/test-counts (Rules 6/7) are eyeballed from recent bars for now
(coding per-level state tracking is a planned upgrade).

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
| **Volume/TPO profile** | `volume_profile` | **Current-day** POC + value-area (VAH/VAL): reads your **Kioseff TPO** on a brief 30m show/hide (cached; falls back to a computed 30m profile). **Prior-day** VAH/POC/VAL come from the **`va_store` DB** (`prior_day_vas()`) — a reliable, immutable cache harvested off the indicator (the live scrape returns orphaned-primitive residue, so we don't use it). Both added as confluence levels (`prevVAH`/`prevPOC`/`prevVAL`); the prior-day ones also drive the Value-Area framework below. |
| **Confluence** | `confluence` | When **≥2 levels stack** at price (e.g. VWAP+EMA+zone), the grade is strengthened (A→A+, B→A). Lone touches earn less. |
| **SMC confluence** | `smc_confluence` (**OFF**) | **Disabled — the LuxAlgo "SMC" read was full-history noise** (~430 BOS/CHoCH, ~85 EQH/EQL, 52 OB/FVG boxes spanning gold's entire range), so `near_level`/`in_box` matched on noise, not signal. The indicator is removed from the chart. **SMC concepts are still considered natively** from clean price: liquidity/stop-hunts via `liquidity_sweep`/`session_sweep`/`crt`, BOS via `break_retest`/`trendline_break`, supply/demand via `zone_bounce` + HTF/VA zones. |
| **Auto-Trendline confluence** | `auto_trendlines` | +1 when entry is near an **Auto Trendlines** level read across **4h/1h/15m** (`read_trendlines_mtf`, cached ~1h). A SEPARATE indicator from SMC — scored independently (not gated by SMC). **Mandatory:** the indicator must be on the chart or the scan **throws** (`assert_trendlines`); see `docs/trendlines.md`. |
| **Daily family caps** | `family_caps` | Caps **fired (alerted) trades per setup-family per day** (`FAMILY_CAPS`: trendline 3 · CRT 2 · zone-bounce 1 · momentum 1 · liquidity-sweep 1 · session-sweep 2 · fib-pullback 2 · key-level 2) — stops noisy families overproducing (counts today's PENDING/executed rows from the outcome DB). Only *reduces* trades. |
| **Observation gate** | `observation_gate` | Families in `OBSERVE_FAMILIES` (currently **momentum_impulse**) are still detected + **logged** for measurement but **not fired live**, until they prove cost-adjusted edge out of sample (review: momentum is negative net). AI-decide mode still sees them. |
| **Cooldown** | (const) | After any signal, **no new signal for 5 min** (`COOLDOWN_MIN`) — anti-clustering |
| **Heads-up cooldown** | (const) | After a 👀 heads-up, **no re-ping for 12 min** (`WATCH_CD_MIN`) unless price moves >15p to a genuinely new zone — stops flip-flop spam when price wiggles across overlapping levels (round#/zone/VWAP band) |

---

## 4. Trade levels (TP / SL)

- **Entry:** the trigger candle's close
- **SL:** just beyond the invalidating structure, **capped at 30–35 pips**
- **TP1:** entry ± **50 pips**  ·  **TP2:** entry ± **100 pips**  *(currently fixed; adaptive-TP is planned)*
- **Management rule:** take partial at TP1 → SL to breakeven → trail. **Exit if TP1 not hit within ~10 min.**
- **Pre-TP1 breakeven protection** (`BE_TRIGGER_P=35`, auto): once a trade runs **+35 pips favorable** (even before TP1), the tracker pulls the stop to **entry** and fires a `🛡️ stop to BREAKEVEN` Telegram alert (move your broker stop too). A reversal then scratches at **0** instead of the full SL, and logs as `BE` not `SL`. *Born from 06-04: a short ran +38p, never hit TP1, gave it all back to −30p.* Trigger sits above typical entry-noise pullbacks so it doesn't scratch winners early.
- **What to AVOID (06-04 lesson):** in **choppy / post-trend / reversing tape** (low 15m-ER, no clean trend), **skip counter-trend fades** even when well-located with good R:R — their hit-rate is poor (1W-2L day proved it; both losses were counter-trend fades in chop). The edge is **with-trend continuation** (pullback/bounce in a clean trend, the +77p type). In chop, demand extra confirmation (a held break-of-structure + retest, not the first rejection/reclaim candle) or stand aside.

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
| `scalp_fast.py` | The live **5m** scanner (this doc's logic). Run with `--dry` to test, `--draw` to plot trendlines |
| `scalp_scan.py` | Alternative 15m zone-rejection scanner (auto-derives S/R) |
| `flags.json` | Feature flags (true/false per strategy & filter) |
| `signals_log.csv` | Every signal + features + outcome (auto-learn dataset) |
| `journal_trade.py` | Per-trade folder: chart + per-TF notes + `trades/journal_log.csv` |
| `backtest_day.py` / `backtest_tp.py` | Replay over recent 1m / TP-target sweep |
| `telegram_config.json` | Bot token + chat_id (send-only) |
| `tg_monitor.sh` | start/stop/status the autonomous launchd monitor |
| `tpo.py` / `va_store.py` | Read prior-day VAH/POC/VAL + single-print zones off the Kioseff **TPO indicator**; immutable sqlite cache (`value_areas.db`) |
| `va_state.py` | Rules 6/7: classify a prior VA level vs current-session bars → **Level State** (Untested/Rejected/Accepted/Flipped) |
| `va_reject.py` | Entry #13: VWAP value-area rejection trigger (the `gold-vwap-strategy.md` setups) |
| `draw_overlay.py` | Live-chart overlay: prior VAH/VAL/POC (date + Level State) + SP zones + near-price SMC order blocks; loop-refreshed, id-tracked |
| `confidence.py` | 0–10 confidence score (aggregates grade + confluence + SMC/TL + RSI-div + trend + R:R + Level-State) → optional `confidence_sizing` risk multiplier. Full doc: `docs/confidence.md` |
| `docs/trendlines.md` | Auto Trendlines as multi-TF (4h/1h/15m) confluence — decoupled from SMC, mandatory (`assert_trendlines`) |
| `docs/signal-roadmap.md` | 100-signal taxonomy + crosswalk to our 13 strategies; roadmap/menu (not a build list). AI approval checklist + APPROVE/REJECT/WAIT merged into `--review` |
| `docs/signal-roadmap-detailed.md` | Detailed companion: per-signal execution + Python detection hints, Confluence Score Guide, AI Review JSON schema |
| `docs/value-area-system.md` | End-to-end map of the whole prior-day value-area subsystem (harvest → store → state → trade → draw) |
| `harvest_daily.py` | Self-dating, idempotent daily VA harvest of the most-recent closed session. Replay runs ONLY on the **dedicated backtest tab** (`TV_BACKTEST_CHART`, default `eabXWKAd`) — never the live chart — and pins the pair to PEPPERSTONE:XAUUSD + verifies it before reading. Refuses to store a read unless the replay cursor is confirmed on the target date (no silent mis-dating). |
| `reharvest_week.py` | One-off: force re-harvest a date range (used to backfill SP zones) |
| `docs/value-area-framework.md` / `docs/gold-vwap-strategy.md` | Rules 1–7 framework + the VWAP-bias execution spec the AI applies |
| `~/Library/LaunchAgents/com.yassir.goldscalper.plist` | Runs the scanner every 60s on the Mac |
| `~/Library/LaunchAgents/com.yassir.vaharvest.plist` | Runs `harvest_daily.py` after the 22:00 UTC session close (00:20–03:20 local, idempotent retries) |

---

## 8. Known limitations / planned

- **Auto-learn loop** — `signals_log.csv` collects the data; periodic win-rate/expectancy analysis + supervised tuning is the roadmap. **Collect ~20–30 real trades before tuning from outcomes.**
- **Zone-reclaim trigger** (`zone_reclaim`, **default OFF**) — built + backtested. A non-impulse dip-into-zone-then-reclaim trigger. Backtest finding: confirmation **inherently lags** — by the time a gradual bounce closes back out of the zone it's already ~80–110p extended, where **anti-chase blocks it** and the entry sits in the next resistance. So a *confirmed* reclaim can't catch the dip. **The real fix is an anticipatory zone-touch entry** (buy the A+ support touch with a tight stop, before confirmation) — a different risk model (more failed-bounce losses, but catches the move from the bottom). Pending user's call on confirmed-vs-anticipatory.
- **No news feed** → blackout is a manual time list.
- **Asian range** (`ASIA_H`/`ASIA_L`) still manual — set near London open.
- Multi-timeframe *screenshots* unreliable on this desktop build — journal uses one annotated chart + written per-TF notes.

*Strategy logic lives in `scalp_fast.py`; this doc summarizes it. Re-read after major changes.*
