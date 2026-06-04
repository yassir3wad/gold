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
| Rebuild + draw zones | `python3 refresh_zones.py --symbol <SYM>` · `draw_zones.py --symbol <SYM>` |
| Pin a pair (always review) | `echo '["XAUUSD"]' > ~/.tv_fast_pinned.json` (empty list = unpin) |
| Change $ risk / lot specs | edit `instruments.json` (`risk_usd`, `pip_value`, `lot_min/max/step`) |
| Re-map a window's chart-id | `node src/cli/index.js tab list` → set `chart` per symbol in `instruments.json` |

**Config** lives in `instruments.json` (per symbol: `pip`, `atr_ref`, `pip_value`, `risk_usd`, `lot_min/max/step`,
`chart`, `sessions`, `use_tpo`, optional `flags`). **Logs**: `logs/<sym>/<YYYY-MM-DD>.csv` (the auto-learn dataset).

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
