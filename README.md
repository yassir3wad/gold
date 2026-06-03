# Gold (XAUUSD) Autonomous Scalp System

A momentum scalping assistant for **XAUUSD** built on top of [tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp).
It reads your **live TradingView Desktop** chart every minute, detects setups across 8 strategies,
grades them by higher-timeframe confluence, and pushes **Telegram alerts** — fully autonomous on your Mac.

> ⚠️ **Not financial advice.** It sends *alerts only* — it does **not** place trades. Practice on a **demo account** first. Scalping gold is high-risk.

---

## What it does

- **`scalp_fast.py`** — the live 1m scanner: trendline break, range/triangle breakout, double top/bottom,
  momentum impulse, **liquidity-sweep reversal**, break-and-retest, VWAP, Asian-range/prior-day breakout.
- **Grading** A+ / A / B (counter-zone pokes suppressed), using HTF zones + VWAP + round numbers + prior-day & Asian levels.
- **Filters:** volatility gate, London/NY session filter, news blackout, volume confirmation, 8-min cooldown.
- **Telegram alerts:** 👀 heads-up → 🚨 confirmed entry (Entry/SL/TP1/TP2 + chart) → ✅ TP1 / 🎯 TP2 / ❌ SL.
- **Logging & journaling:** every signal → `signals_log.csv`; per-trade folders via `journal_trade.py`.
- **Feature flags:** toggle any strategy/filter in `flags.json` (no code edits).

See **[STRATEGIES.md](STRATEGIES.md)** for the full algorithm reference.

---

## Setup

### 1. Install
```bash
git clone https://github.com/yassir3wad/gold && cd gold
npm install
```

### 2. Launch TradingView Desktop with the debug port (macOS)
```bash
pkill -f TradingView; open -a TradingView --args --remote-debugging-port=9222
```
Log in and open an **XAUUSD** chart. Verify: `curl -s http://localhost:9222/json/version`

### 3. Configure Telegram
Create a bot via [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token. Message your bot once.
Then copy the template and fill it in:
```bash
cp telegram_config.example.json telegram_config.json
# edit telegram_config.json: bot_token + chat_id
```
Get your `chat_id`: `curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates"` → read `chat.id`.

> `telegram_config.json` is gitignored — **never commit your token.**

### 4. (macOS) Run it autonomously
A `launchd` agent runs the scanner every 60s. Control it:
```bash
./tg_monitor.sh start    # begin (alerts to Telegram)
./tg_monitor.sh stop
./tg_monitor.sh status
```
The Mac must stay **awake** and **TradingView open** with the debug port.

Test the scanner by hand (no alerts/state): `python3 scalp_fast.py --dry`

---

## Tuning

- **`flags.json`** — `true`/`false` per strategy & filter (read fresh each run).
- **Reference levels** (top of `scalp_fast.py`): `HTF_R`/`HTF_S`, `PDH`/`PDL`, `ASIA_H`/`ASIA_L`, `NEWS_BLACKOUT`.
  These are hardcoded and **go stale** — refresh ~daily for the current structure.
- **`backtest_day.py`** / **`backtest_tp.py`** — replay over recent 1m data / sweep TP targets.

---

## Files

| File | Purpose |
|------|---------|
| `scalp_fast.py` | Live 1m momentum scanner (the brain) |
| `scalp_scan.py` | Alternative 15m zone-rejection scanner |
| `flags.json` | Feature flags |
| `signals_log.csv` | Every signal + features + outcome (auto-learn dataset) |
| `journal_trade.py` / `trades/` | Per-trade chart + notes journal |
| `STRATEGIES.md` | Full algorithm reference |
| `tg_monitor.sh` | start/stop/status the autonomous monitor |
| `src/` | tradingview-mcp engine (MIT — see LICENSE) |

---

## Credits & license

Built on [tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) (MIT, see `LICENSE`).
This project's additions are provided as-is for educational use. Trade at your own risk.
