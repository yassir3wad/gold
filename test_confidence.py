#!/usr/bin/env python3
"""Tests for confidence.py — aggregate every confluence axis into a 0–10 confidence score (which survives
past the A+ grade ceiling) and map it to a position-size multiplier. Pure stdlib.
    python3 test_confidence.py
"""
import sys
import confidence as C

_r = []
def check(n, c): _r.append((n, bool(c)))


def test_score_full_stack():
    # A+ + max level stack + max SMC/TL + RSI div + with-trend + R:R>=2 + valid level -> caps at 10
    s = C.score("A+", conf=3, smc_tl=2, rsi_div=True, with_trend=True, rr=3.0, level_valid=True)
    check("full stack caps at 10", s == 10)


def test_score_bare_b():
    check("bare B in open space -> low", C.score("B (open space)") == 1)


def test_score_counter_trend_penalty():
    # A grade but counter-trend should score LESS than the same with-trend
    ct = C.score("A", with_trend=False)
    wt = C.score("A", with_trend=True)
    check("counter-trend scores below with-trend", ct < wt)
    check("counter-trend penalised (A=2, -1) -> 1", ct == 1)


def test_score_monotonic_in_confluence():
    check("more confluence -> higher score",
          C.score("A", conf=0, smc_tl=0) < C.score("A", conf=2, smc_tl=2))


def test_score_clamped():
    check("never below 0", C.score("C-into-zone", with_trend=False) >= 0)
    check("never above 10", C.score("A+", conf=9, smc_tl=9, rsi_div=True, with_trend=True, rr=5, level_valid=True) == 10)


def test_size_multiplier():
    check("mid confidence -> 1.0x", C.size_multiplier(5.0) == 1.0)
    check("max confidence -> hi (1.5x)", C.size_multiplier(10.0) == 1.5)
    check("zero confidence -> lo (0.75x)", C.size_multiplier(0.0) == 0.75)
    check("monotonic", C.size_multiplier(3) < C.size_multiplier(5) < C.size_multiplier(8))
    check("clamps out-of-range", C.size_multiplier(99) == 1.5 and C.size_multiplier(-5) == 0.75)


def test_label():
    check("label tiers", C.label(9) == "very-high" and C.label(6) == "high" and C.label(4) == "medium" and C.label(1) == "low")


def main():
    for fn in (test_score_full_stack, test_score_bare_b, test_score_counter_trend_penalty,
               test_score_monotonic_in_confluence, test_score_clamped, test_size_multiplier, test_label):
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
