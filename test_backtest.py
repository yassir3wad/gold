#!/usr/bin/env python3
"""Tests for backtest_multi_day — the replay fetch, trade simulation, bootstrap Monte Carlo, metrics,
and walk-forward windowing. Pure stdlib; the replay fetch is tested with an injected fake `tv`.
    python3 test_backtest.py    (exit 0 = all pass)
"""
import sys, random, datetime as dt
import backtest_multi_day as bt

_results = []
def check(name, cond): _results.append((name, bool(cond)))
def approx(a, b, tol=1e-6): return a is not None and abs(a - b) <= tol
def _utc(y, mo, d, h=12): return dt.datetime(y, mo, d, h, tzinfo=dt.timezone.utc).timestamp()
def T(pips): return ("LONG", "A", "x", 0, 0, 0, ("TP1" if pips > 0 else "SL"), pips)  # trade tuple, pips at [7]


def test_bars_on_date():
    day = dt.date(2025, 6, 10)
    bars = [{"time": _utc(2025, 6, 9, 23), "high": 1, "low": 0},   # day before
            {"time": _utc(2025, 6, 10, 8), "high": 1, "low": 0},   # in
            {"time": _utc(2025, 6, 10, 20), "high": 1, "low": 0},  # in
            {"time": _utc(2025, 6, 11, 1), "high": 1, "low": 0},   # day after
            {"time": None}]                                         # junk
    out = bt.bars_on_date(bars, day)
    check("bars_on_date: keeps only the target date", len(out) == 2)
    check("bars_on_date: drops None time", all(b.get("time") for b in out))


def test_fetch_session_bars():
    day = dt.date(2025, 6, 10)
    calls = []
    canned = [{"time": _utc(2025, 6, 9, 22), "high": 1, "low": 0},
              {"time": _utc(2025, 6, 10, 12), "high": 1, "low": 0}]
    def fake_tv(*a):
        calls.append(a)
        return {"bars": canned} if a[0] == "ohlcv" else {}
    out = bt.fetch_session_bars(day, tv_fn=fake_tv, n=500, wait=0)
    cmds = [c[0] for c in calls]
    check("fetch: starts replay", ("replay", "start", "--date", "2025-06-11") in calls)   # cursor = day+1
    check("fetch: reads ohlcv", "ohlcv" in cmds)
    check("fetch: stops replay (cleanup)", ("replay", "stop") in calls)
    check("fetch: filtered to the date", len(out) == 1 and out[0]["time"] == _utc(2025, 6, 10, 12))

    # replay loads async: first ohlcv returns realtime (wrong-date) bars, then the target-date bars appear.
    # fetch_session_bars must POLL past the empty/wrong reads (this was the real 'Bars: 0' bug).
    seq = [[{"time": _utc(2025, 6, 11, 9), "high": 1, "low": 0}],   # realtime read -> filtered out
           [{"time": _utc(2025, 6, 11, 9), "high": 1, "low": 0}],   # still loading
           canned]                                                   # replay engaged -> 06-10 bar present
    box = {"i": 0}
    def loading_tv(*a):
        if a[0] != "ohlcv": return {}
        bars = seq[min(box["i"], len(seq) - 1)]; box["i"] += 1; return {"bars": bars}
    out2 = bt.fetch_session_bars(day, tv_fn=loading_tv, n=500, wait=0, retries=6)
    check("fetch: polls past async replay load", len(out2) == 1 and out2[0]["time"] == _utc(2025, 6, 10, 12))
    check("fetch: gives up after retries -> []", bt.fetch_session_bars(day, tv_fn=fake_tv if False else (lambda *a: {"bars": []} if a[0]=="ohlcv" else {}), n=500, wait=0, retries=3) == [])

    def boom_tv(*a):
        calls.append(a)
        if a[0] == "ohlcv": raise RuntimeError("network")
        return {}
    calls.clear()
    try: bt.fetch_session_bars(day, tv_fn=boom_tv, wait=0)
    except Exception: pass
    check("fetch: replay stop runs even on error", ("replay", "stop") in calls)


def test_simulate_trade():
    B = lambda h, l: {"high": float(h), "low": float(l), "close": float((h + l) / 2)}
    check("sim: LONG TP1", bt.simulate_trade("LONG", 100, 98, 103, [B(101, 99), B(104, 100)]) == ("TP1", 103, 2))
    check("sim: LONG SL",  bt.simulate_trade("LONG", 100, 98, 103, [B(101, 97)])[0] == "SL")
    check("sim: LONG tie -> SL", bt.simulate_trade("LONG", 100, 98, 103, [B(104, 97)])[0] == "SL")
    check("sim: SHORT TP1", bt.simulate_trade("SHORT", 100, 102, 97, [B(100, 96)])[0] == "TP1")
    to = bt.simulate_trade("LONG", 100, 98, 103, [B(101, 99), B(102, 99)])
    check("sim: timeout exits at last close", to[0] == "timeout" and approx(to[1], 100.5))
    check("sim: empty -> timeout, 0 bars", bt.simulate_trade("LONG", 100, 98, 103, []) == ("timeout", 100, 0))
    check("sim: respects horizon", bt.simulate_trade("LONG", 100, 98, 103, [B(101, 99)] * 5 + [B(104, 100)], horizon=3)[0] == "timeout")


def test_profit_factor():
    check("PF: 100/35", approx(bt.calculate_profit_factor([T(50), T(50), T(-35)]), 100 / 35))
    check("PF: no losses -> inf", bt.calculate_profit_factor([T(50)]) == float("inf"))


def test_max_drawdown():
    dd, pct = bt.calculate_max_drawdown([T(50), T(-35), T(-35), T(50)])  # equity 50,15,-20,30; peak 50; maxDD 70
    check("maxDD: pips", approx(dd, 70))
    check("maxDD: pct vs peak", approx(pct, 140.0))


def test_sharpe_not_annualized():
    s = bt.calculate_sharpe_ratio([T(10), T(20), T(30)])   # mean 20, std 10 -> 2.0 (NOT *sqrt(252))
    check("sharpe: mean/std per-trade", approx(s, 2.0))
    check("sharpe: NOT annualized", s < 3)   # sqrt(252)*2 ≈ 31.7 would fail this


def test_monte_carlo_bootstrap():
    random.seed(0)
    trades = [T(50)] * 6 + [T(-35)] * 4   # mixed
    mc = bt.monte_carlo_simulation(trades, 400)
    check("MC: has percentiles", all(k in mc['net_pips'] for k in ('p5', 'p50', 'p95')))
    check("MC: net P&L VARIES (bootstrap, not shuffle)", mc['net_pips']['p5'] < mc['net_pips']['p95'])
    check("MC: win rate varies too", mc['win_rate']['p5'] < mc['win_rate']['p95'])
    check("MC: percentiles ordered", mc['net_pips']['p5'] <= mc['net_pips']['p50'] <= mc['net_pips']['p95'])


def test_walk_forward_windows():
    w = bt.generate_walk_forward_windows(dt.date(2025, 1, 1), dt.date(2025, 1, 14), 5, 2)
    check("WF: two windows", len(w) == 2)
    check("WF: w1 train start", w[0][0] == dt.date(2025, 1, 1))
    check("WF: w1 test end", w[0][3] == dt.date(2025, 1, 7))
    check("WF: w2 test end", w[1][3] == dt.date(2025, 1, 12))
    check("WF: no window when range too small", bt.generate_walk_forward_windows(dt.date(2025, 1, 1), dt.date(2025, 1, 3), 5, 2) == [])


def test_ema_regime():
    check("regime: rising -> UP", bt.ema_regime([float(i) for i in range(250)]) == "UP")
    check("regime: falling -> DOWN", bt.ema_regime([float(250 - i) for i in range(250)]) == "DOWN")
    check("regime: too few -> flat", bt.ema_regime([1.0, 2.0]) == "flat")


def test_htf_room():
    R = [(4480, 4485, "R")]; Sz = [(4455, 4460, "S")]
    check("room: LONG to next R above", bt.htf_room("LONG", 4470, R, Sz) == 100)   # (4480-4470)/0.10
    check("room: SHORT to next S below", bt.htf_room("SHORT", 4470, R, Sz) == 100)  # (4470-4460)/0.10
    check("room: LONG open (no wall above)", bt.htf_room("LONG", 4490, R, Sz) is None)


def main():
    for fn in (test_bars_on_date, test_fetch_session_bars, test_simulate_trade, test_profit_factor,
               test_max_drawdown, test_sharpe_not_annualized, test_monte_carlo_bootstrap, test_walk_forward_windows,
               test_ema_regime, test_htf_room):
        try: fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False); print(f"  !! {fn.__name__}: {e}")
    passed = sum(1 for _, ok in _results if ok); total = len(_results)
    for n, ok in _results:
        if not ok: print(f"  [FAIL] {n}")
    print(f"\n{'✅' if passed == total else '❌'} {passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
