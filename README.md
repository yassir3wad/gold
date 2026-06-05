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

## Backtesting

A multi-day backtesting framework that replays **real historical 1m bars** (via the TradingView **replay engine**) to validate the momentum-scalp setups over past sessions.

> **Data source & limits:** bars are fetched per day via `replay start --date <D+1>` + `ohlcv` (capped at 500 bars ≈ the most recent ~8h of each day — the London–NY active window; full 24h isn't reachable in one fetch). It backtests the **momentum subset** of `scalp_fast` (trendline/range/double/impulse) with fixed 30–35/50–100 SL/TP — not the full 12-setup engine or its live gates, so treat it as a directional sanity check, not a faithful replica.
>
> ⚠️ **Replay mutates the chart.** Run backtests only when the **live loop is paused** (or pinned to a dedicated tab), or the scanner will read replay data.

### Quick Start

```bash
# Basic backtest over 15 days
python3 backtest_multi_day.py --start-date 2025-01-01 --end-date 2025-01-15

# Walk-forward optimization (rolling train/test windows)
python3 backtest_multi_day.py --start-date 2025-01-01 --end-date 2025-01-31 \
    --walk-forward --train-days 5 --test-days 2

# Monte Carlo simulation (test robustness by bootstrap-resampling trades)
python3 backtest_multi_day.py --start-date 2025-01-01 --end-date 2025-01-15 \
    --monte-carlo --iterations 1000

# Export results for analysis
python3 backtest_multi_day.py --start-date 2025-01-01 --end-date 2025-01-15 \
    --export trades.csv --report summary.txt
```

### Features

- **Sequential backtesting**: Test strategy over any date range using live TradingView 1m bar data
- **Walk-forward optimization**: Sliding train/test windows to simulate real-world forward testing
- **Monte Carlo simulation**: Bootstrap-resample trades (with replacement) 1000+ times to assess robustness and curve-fitting risk
- **Advanced metrics**: Profit factor, max drawdown, Sharpe ratio, confidence intervals
- **Export**: CSV trade log + text summary report for external analysis

### Walk-Forward Mode

Splits your date range into rolling windows:
1. **Train** on N days (e.g., 5)
2. **Test** on M days (e.g., 2)
3. Slide forward by M days and repeat

Reports both in-sample (training) and **out-of-sample (test)** metrics — focus on test results to avoid overfitting.

Example output:
```
WINDOW 1/12
Train: 2025-01-01 to 2025-01-05 (5 days)
  Signals: 23  |  Wins: 14  |  Losses: 6  |  Net: +320 pips
Test:  2025-01-06 to 2025-01-07 (2 days)
  Signals: 8   |  Wins: 5   |  Losses: 2  |  Net: +140 pips
```

### Monte Carlo Simulation

Bootstrap-resamples the trades (with replacement) to build a distribution of outcomes — a plain order-shuffle can't, since net P&L / win rate / PF / Sharpe are order-invariant. Reports 5th, 50th, and 95th percentile ranges:

```
MONTE CARLO SIMULATION (1000 iterations)
Confidence intervals (5th, 50th, 95th percentiles):
Net P&L:       -120 pips  |   +280 pips  |   +680 pips
Win rate:       48.5%     |    52.0%     |    55.5%
Max DD:         180 pips  |    240 pips  |    320 pips
Sharpe ratio:   0.85      |    1.20      |    1.55
```

If the 5th percentile is profitable and drawdown is acceptable, the strategy is robust.

### Filters

Use `--enable-filters` to apply the same filters as `scalp_fast.py`:
- **Session filter**: only London+NY hours (7-22 UTC)
- **Chop filter**: skip trades when market efficiency ratio < 0.30 (ranging)
- **News blackout**: skip manual blackout windows (edit `NEWS_BLACKOUT` in `backtest_multi_day.py`)

### Output Metrics

| Metric | Description |
|--------|-------------|
| **Signals** | Total trade setups detected |
| **Wins** | TP1 hits within 10-bar horizon |
| **Losses** | Stop loss hits |
| **Timeouts** | Neither TP1 nor SL hit within 10 bars (exit at market) |
| **Win rate** | Wins / (Wins + Losses), excluding timeouts |
| **Net pips** | Cumulative P&L |
| **Profit factor** | Gross profit / Gross loss |
| **Max drawdown** | Largest peak-to-valley equity decline (pips & %) |
| **Sharpe ratio** | Per-trade risk-adjusted return (mean/std of trade pips; NOT annualized) |

### Requirements

- **TradingView Desktop** running with CDP on port 9222
- **XAUUSD 1m chart** open in TradingView
- Python 3.7+ with `scalp_fast.py` in the same directory

### Tips

1. **Dry-run first**: Use `--dry-run` to preview dates before running
2. **Start small**: Test 5-7 days first to verify setup
3. **Use walk-forward**: Better than simple sequential for avoiding overfitting
4. **Check Monte Carlo**: If 5th percentile is negative, strategy may be fragile
5. **Export for analysis**: Use `--export trades.csv` to analyze patterns in Excel/Python

---

## Files

| File | Purpose |
|------|---------|
| `scalp_fast.py` | Live 1m momentum scanner (the brain) |
| `scalp_scan.py` | Alternative 15m zone-rejection scanner |
| `flags.json` | Feature flags (incl. `hard_floor` ON, `rsi_reset_gate` OFF) |
| `signals_log.csv` / `logs/<sym>/*.csv` | Every signal + features + outcome, incl. `rejected`/`auto-skip` rows (auto-learn dataset) |
| `analyze_logs.py` | **Performance feedback loop** — win-rate / PF / expectancy by setup·grade·side·hour + reject/auto-skip breakdown ([OPERATIONS.md §8](OPERATIONS.md)) |
| `counterfactual.py` | Reject audit — replays rejected signals to see if we dodged losers or passed winners |
| `digest.py` | End-of-day Telegram digest (W/L · net pips · floor auto-skips) |
| `preflight.py` | Morning readiness check (CDP · zones · news) |
| `test_trading.py` | Test suite (115 checks) — run before any code change |
| `journal_trade.py` / `trades/` | Per-trade chart + notes journal |
| `STRATEGIES.md` | Full algorithm reference |
| `OPERATIONS.md` | Live-trading runbook (loops, discipline, perf review & safety rails) |
| `tg_monitor.sh` | start/stop/status the autonomous monitor |
| `src/` | tradingview-mcp engine (MIT — see LICENSE) |

---

## Credits & license

Built on [tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) (MIT, see `LICENSE`).
This project's additions are provided as-is for educational use. Trade at your own risk.
