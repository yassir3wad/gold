#!/usr/bin/env python3
"""Tests for va_reject.py — the VWAP value-area rejection entry (docs/gold-vwap-strategy.md):
a setup fires only when price is VWAP-aligned, at a VALID prior VA level (held/flipped, not accepted),
shows a confirmed rejection, and the reward to the nearest VWAP/POC target gives R:R >= 1:2. Pure stdlib.
    python3 test_va_reject.py
"""
import sys
import va_reject as R

_r = []
def check(n, c): _r.append((n, bool(c)))
def bar(o, h, l, c): return {"open": o, "high": h, "low": l, "close": c}


# A clean LONG at prior VAL=4445: price reclaims VWAP (4447), bullish rejection off VAL, POC=4463 far enough
# above for R:R>=2 against a tight stop under the rejection wick.
LONG_BARS = [
    bar(4452, 4454, 4448, 4451),   # approaching from above
    bar(4451, 4452, 4443, 4449),   # REJECTION: wick below VAL 4445, close back above
    bar(4449, 4453, 4447, 4449),   # breaks rejection-candle high (4452) -> confirmed; last close 4449
]
VA = {"vah": 4479.0, "val": 4445.0, "poc": 4463.0}


def test_long_at_val():
    out = R.detect_va_reject(4449, 4447, VA, LONG_BARS, pip=0.1)
    check("LONG emitted", len(out) == 1 and out[0][0] == "LONG")
    check("why names VAL + va-reject", "VAL" in out[0][1] and "VA" in out[0][1].upper())
    check("entry = last close", out[0][2] == 4449)
    check("stop below the rejection wick (<= 4443)", out[0][3] <= 4443)


def test_skip_below_vwap():
    # same rejection but price is BELOW VWAP -> long bias not allowed -> no LONG
    out = R.detect_va_reject(4449, 4460, VA, LONG_BARS, pip=0.1)
    check("skip: price below VWAP -> no long", all(s[0] != "LONG" for s in out))


def test_skip_accepted_level():
    # VAL accepted through (two closes below + value below) -> level invalid -> no trade
    accepted = [
        bar(4448, 4449, 4440, 4443),   # close below VAL
        bar(4443, 4445, 4438, 4441),   # close below VAL (2 closes beyond + value below)
        bar(4441, 4444, 4439, 4442),
    ]
    out = R.detect_va_reject(4442, 4440, VA, accepted, pip=0.1)
    check("skip: accepted VAL -> no setup", out == [])


def test_skip_bad_rr():
    # POC target only ~3p above a wide stop -> R:R < 2 -> skip
    va = {"vah": 4479.0, "val": 4445.0, "poc": 4452.0}   # POC very close above entry
    out = R.detect_va_reject(4449, 4447, va, LONG_BARS, pip=0.1, rr_min=2.0)
    check("skip: R:R below 1:2 -> no setup", out == [])


def test_short_at_vah():
    # mirror: SHORT at prior VAH=4479, price below VWAP (4485), tight rejection wick, POC=4463 below for R:R>=2
    short_bars = [
        bar(4476, 4478, 4474, 4477),   # approaching from below
        bar(4477, 4482, 4476, 4477),   # REJECTION: wick above VAH 4479, close back below
        bar(4477, 4478, 4474, 4476),   # breaks rejection-candle low (4476) -> confirmed; last close 4476
    ]
    va = {"vah": 4479.0, "val": 4445.0, "poc": 4463.0}
    out = R.detect_va_reject(4476, 4485, va, short_bars, pip=0.1)
    check("SHORT emitted at VAH", len(out) == 1 and out[0][0] == "SHORT")
    check("short stop above the VAH/wick (> 4479)", out[0][3] > 4479)


def main():
    for fn in (test_long_at_val, test_skip_below_vwap, test_skip_accepted_level, test_skip_bad_rr, test_short_at_vah):
        try: fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False); print(f"  !! {fn.__name__}: {e}")
    p = sum(1 for _, ok in _r if ok); t = len(_r)
    for n, ok in _r:
        if not ok: print(f"  [FAIL] {n}")
    print(f"\n{'OK' if p == t else 'FAIL'} {p}/{t} checks passed")
    sys.exit(0 if p == t else 1)


if __name__ == "__main__":
    main()
