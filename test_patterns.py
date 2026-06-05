#!/usr/bin/env python3
"""Tests for patterns.py — channel / fib / double-top-bottom structural detectors.
Pure stdlib, synthetic bars with known structure. These patterns are meant as STRUCTURAL CONTEXT
(where a high-edge scalp lives), and each must be drawable + backtestable before going live.
    python3 test_patterns.py   (exit 0 = all pass)
"""
import sys
import patterns as P

_r = []
def check(n, c): _r.append((n, bool(c)))
def approx(a, b, t=1e-6): return a is not None and abs(a - b) <= t
def B(o, h, l, c, t=0): return {"time": t, "open": o, "high": h, "low": l, "close": c}


def test_pivots():
    # a clear peak at index 4, clear trough at index 9
    closes = [10, 11, 12, 13, 20, 13, 12, 11, 10, 3, 10, 11, 12]
    bars = [B(c, c + 1, c - 1, c, i) for i, c in enumerate(closes)]
    pv = P.pivots(bars, left=2, right=2)
    highs = [p for p in pv if p["kind"] == "H"]; lows = [p for p in pv if p["kind"] == "L"]
    check("pivots: finds the peak at i=4", any(p["i"] == 4 for p in highs))
    check("pivots: finds the trough at i=9", any(p["i"] == 9 for p in lows))
    check("pivots: ignores edges (no pivot at i=0)", all(p["i"] != 0 for p in pv))


def test_channel_up():
    # rising closes within a band -> up channel; last price near top -> pos ~1
    bars = [B(i, i + 2, i - 2, i, i) for i in range(60)]            # close == i, +/-2 band
    ch = P.detect_channel(bars, lookback=50)
    check("channel: rising -> up", ch and ch["direction"] == "up")
    check("channel: slope positive", ch and ch["slope"] > 0)
    check("channel: upper > lower at last bar", ch and ch["upper"] > ch["lower"])
    # a close sitting at the very top of the band
    bars2 = bars[:-1] + [B(59, 61, 57, 61, 59)]
    ch2 = P.detect_channel(bars2, lookback=50)
    check("channel: pos near top ~1", ch2 and ch2["pos"] > 0.8)


def test_channel_down_and_range():
    down = [B(60 - i, 62 - i, 58 - i, 60 - i, i) for i in range(60)]
    chd = P.detect_channel(down, lookback=50)
    check("channel: falling -> down", chd and chd["direction"] == "down")
    flat = [B(50, 52, 48, 50 + (i % 2), i) for i in range(60)]      # oscillating, ~no slope
    chf = P.detect_channel(flat, lookback=50)
    check("channel: flat -> range", chf and chf["direction"] == "range")


def test_fib_levels():
    f = P.fib_levels(100.0, 0.0)
    check("fib: 0.5 = 50", approx(f[0.5], 50.0))
    check("fib: 0.382 = 61.8", approx(f[0.382], 61.8))
    check("fib: 0.618 = 38.2", approx(f[0.618], 38.2))
    check("fib: 0.786 = 21.4", approx(f[0.786], 21.4))
    # golden pocket helper: 0.618-0.65 zone midpoint between 0.618 and 0.786 levels
    gp = P.golden_pocket(100.0, 0.0)
    check("fib: golden pocket spans 0.618..0.786 prices", gp[0] >= f[0.786] and gp[1] <= f[0.618])


def test_active_swing():
    # price runs up to a high at 50 then pulls back -> swing is (low0, high50), dir up
    closes = list(range(0, 50)) + [49, 47, 45, 44]
    bars = [B(c, c + 1, c - 1, c, i) for i, c in enumerate(closes)]
    sw = P.active_swing(bars, left=2, right=2)
    check("swing: detects an up-swing", sw and sw["direction"] == "up")
    check("swing: high >= low", sw and sw["high"] > sw["low"])


def test_double_top():
    # two ~equal peaks (~20) with a valley (~12) between -> double top, neckline at the valley
    closes = [10, 15, 20, 15, 12, 15, 20, 16, 12, 10]
    bars = [B(c, c + 0.5, c - 0.5, c, i) for i, c in enumerate(closes)]
    d = P.detect_double(bars, left=1, right=1, tol=0.05)
    check("double: detects double-top", d and d["kind"] == "double-top")
    check("double: neckline near the middle valley (~12)", d and 11 <= d["neckline"] <= 13)


def test_double_bottom():
    closes = [20, 15, 10, 15, 18, 15, 10, 14, 18, 20]
    bars = [B(c, c + 0.5, c - 0.5, c, i) for i, c in enumerate(closes)]
    d = P.detect_double(bars, left=1, right=1, tol=0.05)
    check("double: detects double-bottom", d and d["kind"] == "double-bottom")
    check("double: neckline near the middle peak (~18)", d and 17 <= d["neckline"] <= 19)


def main():
    for fn in (test_pivots, test_channel_up, test_channel_down_and_range, test_fib_levels,
               test_active_swing, test_double_top, test_double_bottom):
        try: fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False); print(f"  !! {fn.__name__}: {e}")
    p = sum(1 for _, ok in _r if ok); t = len(_r)
    for n, ok in _r:
        if not ok: print(f"  [FAIL] {n}")
    print(f"\n{'✅' if p == t else '❌'} {p}/{t} checks passed")
    sys.exit(0 if p == t else 1)


if __name__ == "__main__":
    main()
