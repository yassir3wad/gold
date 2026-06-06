# Operations — Multi-Pair Scalp System

How the system runs: what happens **every minute**, what happens **at day start / on a schedule**, and
the decision logic behind every signal. This is the live-trading runbook.

---

## 0. The big picture

7 instruments — **XAUUSD · GBPUSD · EURUSD · USDJPY · AUDUSD · NAS100 · US30** — each in its own
TradingView tab. Every tab is a separate CDP target, so each is read **in parallel** by pinning
`TV_CHART=<chart_id>` (mapped in `instruments.json`). One codebase scans any symbol via `--symbol`.

**Two scheduled loops drive everything:**

| Loop | Cadence | What it does |
|------|---------|--------------|
| **Orchestration** | every **1 min** | meta-scan all 7 → AI-review the hot/pinned/active pairs → hold confirmed trades for approval |
| **News** | every **15 min** | refetch the Forex Factory calendar (keeps the blackout current) + ping any just-released high-impact result |
| **News brief** | once each **morning** | Telegram "today's news" (high/medium events, local time) |

Nothing reaches your phone except **AI-approved trades** and their management updates (+ news). All times are
shown in **your local timezone** (currently UTC+2 / Amsterdam).

---

## 0b. Timeframes analysed — and how each is used

The scanner is **1m-native** (execution), but pulls context from higher timeframes. Importantly, the 15m and
30m reads come from **resampling the 1m bars in hand** or a **brief cached visit** — the chart is *not* constantly
flipped between timeframes.

| Timeframe | How it's obtained | What it drives |
|-----------|-------------------|----------------|
| **1m** — execution | the live chart (180 bars) each tick | Every **trigger & setup**, price action, the "strong candle" test, **RSI**, **EMA 50/100/200** (read at 1m → dynamic S/R + ema-levels), **VWAP + bands**, **ATR**, the 10-bar range, and entry/SL placement. This is where trades are taken. |
| **15m** — chop/range gate | **resampled from the 1m bars in hand — no TF switch** | The **15m efficiency ratio (ER)**: 1 = clean trend, 0 = chop. ER < 0.3 ⇒ "chop" ⇒ breakout/momentum setups are suppressed (reversals stay). Also the **CRT "range candle"** = the prior ~15-bar (≈15m) block whose high/low get swept. |
| **30m** — trend bias / regime | a **brief cached visit** (~20-min cache), then restores 1m | The **trend regime** from the 30m EMA stack (50>100>200 = UP, reverse = DOWN, else flat). Execution is 1m but **bias is 30m**, so it's immune to 1m pullbacks — *counter-trend trades (vs the 30m regime) need A+*. The same visit reads the **value-area** (VPOC / VAH / VAL — gold reads its TPO here; others compute it). |
| **D / 4H / 1H / 15m** — structure | `refresh_zones.py`, run separately (~every 6h or on demand) | The **HTF support/resistance zones** in `zones_<sym>.json`: swing pivots + EMAs + PDH/PDL + round numbers clustered into multi-touch bands, plus the chart's session H/L ranges. The scanner **reads** these each tick (it doesn't recompute them live). The drawn boxes come from here. |

**In one line:** **trade on 1m**, **gate chop on 15m**, **take trend bias from 30m**, **map structure from the
D/4H/1H/15m zones**. The 1m chart is execution-only; the higher TFs supply context — the readout each tick shows
all of it: `range10`/`atr`/`strong` (1m), `15m-ER` (15m), `regime`/`VPOC/VAH/VAL` (30m), `HTF @R/@S … nextR/nextS` (zones).

---

## 1. EVERY MINUTE — the orchestration tick

Driven by the per-minute cron → runs `bash orchestrate.sh` (= `orchestrate.py`). One tick:

### Step 1 — Meta-scan all 7 pairs  (`scan_pairs.score_pair`)
For each instrument, pinned to its own window, a **light read** (1m data + its zones + session — no TF flips):
- **Volatility** — `atr_base/ATR_REF` (the pair's ~2h ATR vs its normal). Best around 1.2×; dead (<0.5) or spiky (>2.5) score low.
- **Trend efficiency** — 15m Kaufman ER (1 = clean trend, 0 = chop). Toward 0.6 scores high.
- **Level proximity** — distance to the nearest zone, in ATR units (near a level = setup imminent).
- **Session fit** — is it this pair's active session right now? (London / NY / Asia from config.)

→ **Score = 30% volatility + 30% trend-efficiency + 20% level-proximity + 20% session.** Pairs ranked high→low.

### Step 2 — Decide which pairs to deep-review this tick
The review set = **top-scored pair** ∪ any pair scoring **≥55** ∪ **any pair with an active trade** (so TP/SL/BE
management is never dropped) ∪ **pinned pairs** (`~/.tv_fast_pinned.json`, e.g. gold "until further notice").

Only these pairs get the full scan — the quiet/chop pairs are skipped (efficient).

### Step 3 — AI-review each (`aireview.sh <SYM>` = `scalp_fast.py --symbol <SYM> --review`)
For each pair in the set, on its own window:
1. Read 1m bars, price, volume; compute ATR, 15m ER (chop), RSI, the EMA 50/100/200 stack, VWAP+bands; load its zones.
2. **30m regime** (cached ~20m) — UP/DOWN/flat from the 30m EMA stack (gold also reads its TPO value-area here).
3. **ATR-normalize** every threshold (wick, chase, room, TP/SL caps, BE trigger…) to the pair's volatility.
4. Run the **12 setups** (trendline break, range breakout, double top/bottom, momentum impulse, liquidity-sweep,
   break-retest, VWAP, session breakout, session-sweep, zone-reclaim, zone-bounce, **CRT**).
5. **Filters** (advisory under AI-decide; the AI does the final judging): chop/range, anti-chase, RSI exhaustion,
   counter-trend (needs A+), volume, adaptive-TP room, **news blackout** (±15 min around red-folder events on the
   pair's currency → mute).
6. **Grade** A+ / A / B / C. **Size the lot**: `lot = $RISK / (pip_value × stop_pips)`, rounded to the broker step, clamped to min/max.
7. **Outcome of the scan:**
   - A confirmed setup → **HELD** in `~/.tv_fast_<sym>_pending.json` (NOT sent — waits for AI approval).
   - An active trade → send its **TP1 / TP2 / SL / 🛡️BE** updates to Telegram, and pull the stop to breakeven once it runs +35p.
   - Nothing → just the readout.

### Step 4 — Orchestrator output
Prints: the **score table**, which pairs it reviewed (`focus` / `pinned` / `ACTIVE-TRADE`), and **`*** HELD — REVIEW ***`**
for any pair holding a confirmed trade, with the trade's details (side, grade, pattern, level, RSI, ER, room, lot).

### Step 5 — Claude reviews any HELD trade
For each held trade, the AI judges it against the discipline (below). If borderline, it screenshots the pair
(`shot.sh <SYM>`) and reads the chart. Then:
- **Good trade** → `approve.sh <SYM> "<reason>"` → fires the **CONFIRMED** alert to Telegram (entry/SL/lot/TP1/TP2 + chart), logs it, starts TP/SL tracking.
- **Weak trade** → `reject.sh <SYM> "<reason>"` → logged to the auto-learn dataset, **nothing sent**.

If nothing is held: one-line "focus pair + score + quiet 🔍".

**→ Your phone only ever sees AI-approved trades. No mechanical "setup forming" spam.**

---

## 2. AT DAY START / ON A SCHEDULE

### Morning — news brief
`python3 news.py brief` → pulls the week's Forex Factory calendar, filters **today's** High/Medium events, and
Telegrams them in your local time, e.g.:
> 📰 Today's news (UTC+2):
> 🔴 14:30 USD — Non-Farm Employment Change (F:85K P:115K)
> 🔴 20:00 GBP — BOE Gov Bailey Speaks

This tells you the day's landmines (avoid windows) and catalysts in advance.

### Every 15 min — news refresh + result
`python3 news.py result` → re-fetches the calendar (keeps the **blackout cache** current so the scanner mutes the
right windows) and, for any **high-impact** event that **just released**, Telegrams the surprise:
> 🗞️ USD Non-Farm Employment Change: actual 142K vs forecast 85K → USD stronger than forecast
> Affects: XAUUSD, NAS100, US30, EURUSD, GBPUSD, USDJPY, AUDUSD

### Zones
`zones_<sym>.json` rebuild automatically when stale (~6h), or on demand:
`python3 refresh_zones.py --symbol <SYM>` (derives D/4H/1H/15m pivots + EMAs + PDH/PDL + round numbers + the
chart's Trading Sessions ranges). Visualize them on the chart with `python3 draw_zones.py --symbol <SYM>`.

### HOURLY structural refresh + confluence (zones-and-confluence system)
**Every hour, ALL structural context is refreshed and re-drawn, and the indicators are hidden between
refreshes.** This is the `zones_sd` + `smc.py` grading layer (full detail: `docs/zones-and-confluence.md`):
- **Our zones** (buy/sell zones, Key Levels, support/resistance, value areas — computed on 4h+1h bars) are
  recomputed on the latest bars and **re-drawn on the hour**.
- **Confluence (mandatory)** — LuxAlgo **SMC** (order-blocks/structure/liquidity) + **Auto-Trendlines** are
  read off the **execution chart** via **store-and-hide** (show → render → read → hide), **cached ~1h**
  (`~/.tv_fast_<suffix>_smc.json`). The chart then shows only our clean drawings; the indicators don't
  re-render between refreshes. A signal at our zone that ALSO aligns with SMC OB / BOS-CHoCH / EQH-EQL / a
  trendline gets a grade **"+"** per alignment (≥2 → bump B→A→A+). SMC indicator absent ⇒ WARN.
- Between hourly refreshes the per-minute tick uses the **stored** zones/SMC — no chart reads, no CDP load.

---

## 3. The discipline (what passes vs gets rejected)

The AI approves a held trade only when it's **with-trend + has real room + a clean trigger**. It **rejects**:
- **Counter-trend fades** (LONG in a DOWN regime / SHORT in UP) unless genuinely A+ — and *never* in chop or thin off-session tape.
- **Overbought/oversold chasing** — buying RSI>70 blow-offs / selling RSI<30 capitulation lows.
- **No room into structure** — TP capped a few pips into the next wall (poor R:R).
- **Dead chop** — 15m ER < 0.3 (whipsaw-in-a-box).
- **Red-news windows** — muted automatically ±15 min.

Key lesson baked in: **the edge is the live/trending pair** (in-session, ER ≥ 0.4) — trade *that*, skip the 6 dead charts.

---

## 4. What reaches your phone (Telegram)

| Message | When |
|---------|------|
| 📰 Today's news brief | each morning |
| 🗞️ News result + bias | at each high-impact release |
| 🟢/🔴 **CONFIRMED** entry (entry · SL · **Lot** · TP1 · TP2 + chart) | only when **AI approves** a held trade |
| ✅ TP1 / 🎯 TP2 / ❌ SL / 🛡️ BE | as your live trade hits them |

You do **not** get: "setup forming" heads-ups, rejected trades, or anything mechanical.

---

## 5. Operator commands

| Action | Command |
|--------|---------|
| One orchestration tick (manual) | `bash ~/tradingview-mcp/orchestrate.sh` |
| Meta-scan only (rank pairs) | `python3 ~/tradingview-mcp/scan_pairs.py` |
| Review one pair | `bash ~/tradingview-mcp/aireview.sh <SYM>` |
| Approve / reject a held trade | `bash ~/tradingview-mcp/approve.sh <SYM> "reason"` · `reject.sh <SYM> "reason"` |
| Screenshot a pair | `bash ~/tradingview-mcp/shot.sh <SYM>` |
| News brief / result | `python3 ~/tradingview-mcp/news.py brief` · `news.py result` |
| **Performance review** (feedback loop) | `python3 analyze_logs.py [--symbol <SYM>] [--days N] [--md]` — see §8 |
| **Counterfactual reject check** (did we dodge losers or pass winners?) | `python3 counterfactual.py [--symbol <SYM>] [--bars N]` |
| **End-of-day digest** (W/L · net · floor skips → Telegram) | `python3 digest.py` (`--print` = no send) |
| **Morning pre-flight** (CDP · zones · news ready?) | `python3 preflight.py` |
| **Run the test suite** (before any code change) | `python3 test_trading.py` |
| Rebuild + draw zones | `python3 refresh_zones.py --symbol <SYM>` · `draw_zones.py --symbol <SYM>` |
| Pin a pair (always review) | `echo '["XAUUSD"]' > ~/.tv_fast_pinned.json` (empty list = unpin) |
| Change $ risk / lot specs | edit `instruments.json` (`risk_usd`, `pip_value`, `lot_min/max/step`) |
| Re-map a window's chart-id | `node src/cli/index.js tab list` → set `chart` per symbol in `instruments.json` |

**Config** lives in `instruments.json` (per symbol: `pip`, `atr_ref`, `pip_value`, `risk_usd`, `lot_min/max/step`,
`chart`, `sessions`, `use_tpo`, optional `flags`). **Logs**: `logs/<sym>/<YYYY-MM-DD>.csv` (the auto-learn dataset —
now also records `rejected` and `auto-skip` rows; review with `analyze_logs.py`, §8). **Feature flags**: `flags.json`
(e.g. `ai_decide` ON, `hard_floor` ON, `rsi_reset_gate` OFF — see §8).

---

## 6. Session → pair focus

- **Asia** (≈23:00–08:00) → USDJPY, AUDUSD (+ NZD)
- **London** (≈07:00–16:00) → GBPUSD, EURUSD, XAUUSD
- **NY / overlap** (≈13:00–22:00) → NAS100, US30, XAUUSD (London–NY overlap 13:00–16:00 is prime)

The meta-scanner already weights this — it surfaces the in-session, trending pair so you focus there.

---

## 7. Notes / caveats

- **Cron loops are session-only** — they stop when this Claude session closes. To restart: re-run the orchestration
  loop (per-minute) + the news loop (15-min). A durable cloud `/schedule` is the upgrade for survive-across-sessions.
- **Verify `pip_value` for NAS100 / US30 / USDJPY** with your broker before sizing those live (gold + EUR/GBP/AUD are correct).
- **Volume is tick-volume on FX** (activity proxy, not real volume); reversals are exempt from the volume filter anyway.
- **No auto-execution** — every trade is AI-reviewed and only sent as an alert; you place it. (MT5 auto-exec is parked.)
- **Pending / next**: news *catalyst* mode (trade the post-release reaction), durable cloud scheduling, MACD HTF-bias on indices (optional).

---

## 8. Performance review & safety rails

Tools to **measure the edge** and **cut the noise**, so tuning is data-driven instead of guesswork. (Added 2026-06-05.)

### `analyze_logs.py` — the feedback loop · *why: know what actually works*
Mines `logs/<sym>/*.csv` (+ legacy `signals_log.csv`) into **win-rate / profit-factor / expectancy** broken down by
**setup type, grade, side, and hour**, plus a **rejection-reason** and **auto-skip-reason** breakdown. This is how you
spot — with numbers, not vibes — that a setup is a net loser, that one side is bleeding, that the auto-grade isn't
predicting outcomes, or exactly what the hard floor is absorbing. Read-only; never touches live state, charts, or Telegram.
- `python3 analyze_logs.py` — full report, all pairs
- `python3 analyze_logs.py --symbol XAUUSD --days 1` — one pair, rolling 24h
- `python3 analyze_logs.py --md` — also write a dated snapshot to `logs/_analysis/` (diff it over time)
- **Win = net pips > 0** (the `pips` column is the source of truth); TP-hit rate is shown separately.

### Pre-hold HARD FLOOR — flag `hard_floor` (ON) · *why: stop burning review cycles on un-tradeable junk*
Before a setup can be **HELD for review**, the scanner auto-skips it when the **actual reward:risk is negative**
(TP1 < 0.8× the stop = no usable room) — the cramped / no-room chop-spam that otherwise gets hand-rejected every tick.
It applies **even in `ai_decide` mode** (the only gate that does — by design, since AI mode bypasses every other filter).
Each skip is logged as `result=auto-skip` (R:R in `exit`, reason in `pips`), de-duped ~10 min per thesis, so
`analyze_logs.py` shows exactly what it absorbed. You'll see `>> AUTO-SKIP (pre-hold floor): …` in the scan readout
where those rejects used to pile up.

### RSI-reset gate — flag `rsi_reset_gate` (**OFF** until validated) · *why: don't fade into a wrong-way extreme*
Optional gate that auto-skips a **reversal** taken at a wrong-way RSI extreme — a SHORT into deep oversold (≤25 =
selling the bottom) or a LONG into overbought (≥75 = buying the top) — telling you to wait for the reset. Reset-RSI
bounces (e.g. a long at RSI ~40) are left untouched. **Default OFF**: enable in `flags.json` only after `analyze_logs`
confirms the 25/75 thresholds wouldn't have clipped real winners.

### `counterfactual.py` — did our rejections cost us? · *why: audit the discipline with outcomes*
For every **rejected** signal (which logged its entry/SL/TP1), it replays the following bars and checks whether
**TP1 or SL would have hit first** — aggregating into *winners we passed on* vs *losers we dodged*, with a per-reason
breakdown and a net-EV verdict. This is how you confirm the discipline (and the hard floor) is **net +EV** rather
than quietly over-rejecting. Read-only (OHLCV only); covers recent rejects whose bars are still in the buffer (older
ones are honestly reported as "no data"). Run it daily — coverage sharpens as the loop logs recent rejects.

### Observability — `digest.py` / `preflight.py` · *why: see the day at a glance, start clean*
- **`python3 digest.py`** — end-of-day Telegram summary: trades, W/L, net pips, PF, best/worst setup, and **how many
  setups the floor auto-skipped** (so you see what it saved you from). `--print` builds it without sending.
- **`python3 preflight.py`** — one-glance readiness before the session: TradingView/CDP connected, HTF zones fresh
  per pair, news calendar loaded. Prints `READY` or `CHECK` + the exact fix command for anything stale.

### Tests — `test_trading.py` · *why: change the live engine safely*
115 checks over the hard floor, the RSI-reset gate, the auto-skip de-dup/logging, the core setup detectors
(`pivots`, `chop_15m`, `rsi_series`, `_calc_vp`, …), the counterfactual simulator, the digest, the pre-flight
helpers, and every `analyze_logs` helper. The engine is live (fresh process each tick), so **run `python3 test_trading.py` after ANY code change**
before the loop picks it up. Add a failing test first when fixing a bug or adding a rule.

---

## 9. Zone Scheduler — Automated HTF Zone Refresh

The **zone scheduler** keeps your higher-timeframe support/resistance zones fresh automatically. Stale zones (>6 hours old)
are the most common source of bad confluence grading — when `zones_<sym>.json` hasn't been refreshed in 8+ hours, the
system may flag confluence with obsolete levels, leading to false A+ grades on low-quality setups.

**The scheduler solves this:** zones auto-refresh **every 4 hours** (configurable), **at session opens** (London/NY), and
**on demand** (manual trigger). All refresh events send a Telegram summary of what changed.

---

### 8.1. What it does

The scheduler runs as a **background daemon** (systemd service or standalone) and:

1. **Interval refresh** — Every N hours (default: 4), refresh zones for all enabled instruments
2. **Session-based refresh** — Refresh zones 5 min after London open (08:05 UTC) and NY open (13:05 UTC)
3. **Stale zone monitoring** — Check zone file timestamps hourly; alert if any are >6h old
4. **Telegram notifications** — Send formatted alerts after each refresh with change summary (e.g., "XAUUSD: +2 -1 ~1")
5. **Health checks** — Startup health check + periodic checks to catch zones that go stale between refreshes

**Instruments managed:** Configured in `zone_scheduler_config.json` → `enabled_instruments` (default: XAUUSD, GBPUSD, EURUSD).
You can enable all 7 or just the pairs you trade.

---

### 8.2. Setup & Installation

#### Prerequisites
```bash
# Install APScheduler (required for zone_scheduler.py)
pip3 install apscheduler

# Ensure TradingView Desktop is running with CDP on port 9222
# The scheduler calls refresh_zones.py which reads the charts via MCP
```

#### Configuration

Edit `~/tradingview-mcp/zone_scheduler_config.json`:

```json
{
  "enabled": true,
  "enabled_instruments": ["XAUUSD", "GBPUSD", "EURUSD"],   // which pairs to refresh
  "refresh_interval_hours": 4,                              // how often to auto-refresh
  "stale_threshold_hours": 6,                               // warn if zones older than this
  "refresh_on_session_open": ["london", "ny"],              // trigger at session opens
  "session_times": {
    "london": "08:00",                                      // UTC time for session open
    "ny": "13:00"
  },
  "notifications": {
    "send_on_refresh": true,                                // Telegram alert on refresh
    "send_on_stale_warning": true                           // Telegram alert on stale zones
  }
}
```

**Important:** The scheduler applies a **5-minute offset** to session times (configurable), so London refresh triggers at
08:05 UTC, NY at 13:05 UTC. This gives the session time to establish initial ranges before zones are recalculated.

---

### 8.3. Running the Scheduler

#### Option A: Systemd Service (Recommended for production)

**Install as a system service** (survives reboots, auto-restarts on failure):

```bash
# 1. Edit service file to replace YOUR_USERNAME placeholder
cd ~/tradingview-mcp
sed -i "s/YOUR_USERNAME/$(whoami)/g" zone_scheduler.service

# 2. Install the service
sudo cp zone_scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable zone_scheduler
sudo systemctl start zone_scheduler

# 3. Verify it's running
sudo systemctl status zone_scheduler
```

**Service management commands:**
```bash
sudo systemctl start zone_scheduler      # Start
sudo systemctl stop zone_scheduler       # Stop
sudo systemctl restart zone_scheduler    # Restart (e.g., after config change)
sudo systemctl status zone_scheduler     # Check status
sudo systemctl is-active zone_scheduler  # Quick health check
```

**View logs:**
```bash
# Live systemd journal logs
sudo journalctl -u zone_scheduler -f

# Or application log file
tail -f ~/tradingview-mcp/logs/zone_scheduler.log
```

For full systemd setup details, see `ZONE_SCHEDULER_SYSTEMD_SETUP.md`.

#### Option B: Standalone Daemon (Manual start)

```bash
# Run in background (--daemon flag)
cd ~/tradingview-mcp
python3 zone_scheduler.py --daemon

# Run in foreground (debug mode, see live logs)
python3 zone_scheduler.py

# Run once and exit (useful for testing)
python3 zone_scheduler.py --once
```

**To stop:** `pkill -f zone_scheduler.py` or Ctrl+C (foreground mode).

---

### 8.4. Manual Refresh Commands

Sometimes you want to refresh zones **immediately** (e.g., after a major news event or when you add a new pair):

#### CLI Wrapper (Recommended)

```bash
# Refresh all enabled instruments
bash ~/tradingview-mcp/refresh_zones_now.sh

# Refresh specific symbol
bash ~/tradingview-mcp/refresh_zones_now.sh --symbol XAUUSD

# Dry-run (preview what would be refreshed without changing files)
bash ~/tradingview-mcp/refresh_zones_now.sh --dry-run

# Refresh + send Telegram notification
bash ~/tradingview-mcp/refresh_zones_now.sh --notify

# Combined: single symbol + notify
bash ~/tradingview-mcp/refresh_zones_now.sh --symbol GBPUSD --notify
```

#### Direct Python Script

```bash
# Refresh all
python3 ~/tradingview-mcp/refresh_all_zones.py

# Refresh with notification
python3 ~/tradingview-mcp/refresh_all_zones.py --notify

# Refresh single symbol
python3 ~/tradingview-mcp/refresh_all_zones.py --symbol NAS100 --notify
```

#### Telegram Bot Commands

If you have the Telegram bot handler running (`telegram_bot_handler.py`):

```
/refresh_zones              → Refresh all enabled instruments
/refresh_zones XAUUSD       → Refresh only XAUUSD
/help                       → Show available commands
```

**Start the bot:**
```bash
python3 ~/tradingview-mcp/telegram_bot_handler.py
```

The bot sends an immediate "🔄 Refreshing zones..." acknowledgment, triggers the refresh, and sends a detailed summary when complete.

---

### 8.5. Monitoring Zone Health

#### Check Zone Freshness

```bash
# Check all zone files, warn if >6h old (default threshold)
python3 ~/tradingview-mcp/check_zone_health.py

# Custom staleness threshold (e.g., warn if >2h old)
python3 ~/tradingview-mcp/check_zone_health.py --max-age 2
```

**Output example:**
```
Checking zone file health (max age: 6 hours)...

✓ XAUUSD: fresh (2.3 hours old) — last updated 2026-06-05 10:15:23
✓ GBPUSD: fresh (3.1 hours old) — last updated 2026-06-05 09:27:45
⚠ EURUSD: stale (8.7 hours old) — last updated 2026-06-05 04:02:10

Summary: 2 fresh, 1 stale, 0 missing
```

**Exit codes:** 0 = all fresh, 1 = stale or missing zones detected (useful for scripting/monitoring).

#### Integrated Health Check

The scheduler automatically:
- Runs a **startup health check** when it starts (sends Telegram alert if zones are stale)
- Runs **hourly health checks** while running (sends alert if zones go stale between refreshes)

You can also trigger a manual check:
```bash
python3 ~/tradingview-mcp/zone_scheduler.py --check-health
```

---

### 8.6. Logs & Debugging

All scheduler operations are logged to **`~/tradingview-mcp/logs/zone_scheduler.log`** with rotation (10MB max, 5 backups).

**View logs:**
```bash
# Tail live logs
tail -f ~/tradingview-mcp/logs/zone_scheduler.log

# View recent errors
grep ERROR ~/tradingview-mcp/logs/zone_scheduler.log | tail -20

# Check when last refresh happened
grep "Refreshing zones" ~/tradingview-mcp/logs/zone_scheduler.log | tail -5

# See zone change summaries
grep "zones changed" ~/tradingview-mcp/logs/zone_scheduler.log | tail -10
```

**Log format:** `[YYYY-MM-DD HH:MM:SS] LEVEL: message`

**Example log entries:**
```
[2026-06-05 08:05:12] INFO: Session refresh triggered: london
[2026-06-05 08:05:14] INFO: Refreshing zones for XAUUSD...
[2026-06-05 08:05:42] INFO: XAUUSD: zones changed: +2 -1 ~0
[2026-06-05 08:05:43] INFO: Telegram notification sent
[2026-06-05 12:00:00] INFO: Zone health check: 3 fresh, 0 stale, 0 missing
```

**Systemd journal logs** (if running as service):
```bash
# Live logs with timestamps
sudo journalctl -u zone_scheduler -f -o short-iso

# Last 100 lines
sudo journalctl -u zone_scheduler -n 100

# Errors only
sudo journalctl -u zone_scheduler -p err
```

---

### 8.7. Troubleshooting

#### Zones aren't refreshing

**Check scheduler is running:**
```bash
# Systemd service
sudo systemctl status zone_scheduler

# Standalone daemon
ps aux | grep zone_scheduler.py
```

**Check TradingView Desktop is running:**
```bash
# The scheduler calls refresh_zones.py which reads charts via MCP on port 9222
# Ensure TradingView Desktop is open with CDP enabled

# Test manual refresh
python3 ~/tradingview-mcp/refresh_zones.py --symbol XAUUSD
```

**Check logs for errors:**
```bash
tail -50 ~/tradingview-mcp/logs/zone_scheduler.log | grep ERROR
```

#### Stale zone warnings persist

If you keep getting stale zone warnings even though the scheduler is running:

1. **Check enabled_instruments** in `zone_scheduler_config.json` — are all the pairs you trade enabled?
2. **Check refresh_interval_hours** — if it's >6h, zones will go stale between refreshes (default is 4h, which is safe)
3. **Check TradingView is running** — if the app crashes or CDP disconnects, refresh_zones.py will fail silently
4. **Force a manual refresh** to reset zone timestamps:
   ```bash
   bash ~/tradingview-mcp/refresh_zones_now.sh --notify
   ```

#### Telegram notifications not sending

**Check telegram_config.json exists:**
```bash
ls -l ~/tradingview-mcp/telegram_config.json
```

**Test Telegram connectivity:**
```bash
python3 ~/tradingview-mcp/telegram_notify.py --test --dry-run
```

**Check notification settings in zone_scheduler_config.json:**
```json
"notifications": {
  "send_on_refresh": true,
  "send_on_stale_warning": true
}
```

#### Scheduler crashes or restarts frequently

**Check resource limits** (if running as systemd service):
```bash
sudo systemctl status zone_scheduler
# Look for "memory limit hit" or "CPU quota exceeded"
```

**Increase limits** in `zone_scheduler.service` if needed:
```ini
MemoryLimit=512M     # Increase if memory errors
CPUQuota=50%         # Increase if CPU throttling
```

**Check for Python errors:**
```bash
sudo journalctl -u zone_scheduler -p err -n 50
```

#### Configuration changes not taking effect

After editing `zone_scheduler_config.json`, **restart the scheduler**:

```bash
# Systemd service
sudo systemctl restart zone_scheduler

# Standalone daemon
pkill -f zone_scheduler.py && python3 ~/tradingview-mcp/zone_scheduler.py --daemon
```

---

### 8.8. Integration with Orchestration

The zone scheduler runs **independently** of the orchestration loop (`orchestrate.sh`). They work together:

- **Orchestration loop** (every 1 min) → scans pairs, triggers AI-reviewed trades, **reads zones from `zones_<sym>.json`**
- **Zone scheduler** (every 4h + session opens) → **writes fresh zones to `zones_<sym>.json`**

**Key points:**
- The orchestration loop **never refreshes zones itself** — it only reads them
- The zone scheduler **only refreshes zones** — it doesn't scan or trade
- They communicate via the zone files (`zones_xauusd.json`, etc.)
- This separation ensures **the scanner is fast** (no zone recalculation during scans) and **zones stay fresh** (scheduled background refresh)

**When zones are stale during a scan:** The scanner still uses the old zones (it doesn't know they're stale). This is why
the scheduler's health checks + alerts are critical — they catch staleness before it degrades trading decisions.

---

### 8.9. Quick Reference

| Task | Command |
|------|---------|
| **Start scheduler (systemd)** | `sudo systemctl start zone_scheduler` |
| **Stop scheduler (systemd)** | `sudo systemctl stop zone_scheduler` |
| **Check scheduler status** | `sudo systemctl status zone_scheduler` |
| **View logs (systemd)** | `sudo journalctl -u zone_scheduler -f` |
| **View logs (file)** | `tail -f ~/tradingview-mcp/logs/zone_scheduler.log` |
| **Manual refresh (all pairs)** | `bash ~/tradingview-mcp/refresh_zones_now.sh --notify` |
| **Manual refresh (one pair)** | `bash ~/tradingview-mcp/refresh_zones_now.sh --symbol XAUUSD --notify` |
| **Check zone health** | `python3 ~/tradingview-mcp/check_zone_health.py` |
| **Test configuration** | `python3 ~/tradingview-mcp/zone_scheduler.py --test-session-schedule` |
| **Run once and exit** | `python3 ~/tradingview-mcp/zone_scheduler.py --once` |
| **Dry-run refresh** | `bash ~/tradingview-mcp/refresh_zones_now.sh --dry-run` |

**Config files:**
- Zone scheduler config: `~/tradingview-mcp/zone_scheduler_config.json`
- Telegram config: `~/tradingview-mcp/telegram_config.json`
- Systemd service: `/etc/systemd/system/zone_scheduler.service`

**Documentation:**
- Full systemd setup guide: `~/tradingview-mcp/ZONE_SCHEDULER_SYSTEMD_SETUP.md`
- E2E test results: `~/tradingview-mcp/E2E_TEST_RESULTS.md`
