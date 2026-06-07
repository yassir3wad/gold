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


def test_score_each_penalty_lowers():
    # Start from a mid-stack score with headroom so no penalty clamps to 0/10.
    base = C.score("A+", conf=2, smc_tl=2)  # 3+2+2 = 7
    check("base has headroom", 0 < base < 10)
    for kw in ("mid_value", "accepted_through", "over_tested", "into_opposing", "vwap_chop"):
        check(f"{kw} lowers score", C.score("A+", conf=2, smc_tl=2, **{kw: True}) < base)


def test_score_penalty_weights():
    base = C.score("A+", conf=2, smc_tl=2)  # 7
    check("mid_value -2", C.score("A+", conf=2, smc_tl=2, mid_value=True) == base - 2)
    check("accepted_through -2", C.score("A+", conf=2, smc_tl=2, accepted_through=True) == base - 2)
    check("over_tested -1", C.score("A+", conf=2, smc_tl=2, over_tested=True) == base - 1)
    check("into_opposing -1", C.score("A+", conf=2, smc_tl=2, into_opposing=True) == base - 1)
    check("vwap_chop -1", C.score("A+", conf=2, smc_tl=2, vwap_chop=True) == base - 1)


def test_score_penalties_stack():
    base = C.score("A+", conf=2, smc_tl=2)  # 7
    two = C.score("A+", conf=2, smc_tl=2, mid_value=True, over_tested=True)  # -2 -1
    check("two penalties stack", two == base - 3)
    check("stacked below single", two < C.score("A+", conf=2, smc_tl=2, mid_value=True))


def test_score_penalties_never_below_zero():
    # Every penalty on, weak base -> would be negative without the clamp.
    s = C.score("B", with_trend=False, mid_value=True, accepted_through=True,
                over_tested=True, into_opposing=True, vwap_chop=True)
    check("all penalties never below 0", s == 0)


def test_score_backward_compat():
    # Calling score() with only the original args must equal the pre-penalty behaviour:
    # additive axes only, then clamp to [0,10]. Recomputed here independently of the penalty code.
    def legacy(grade, conf=0, smc_tl=0, rsi_div=False, with_trend=None, rr=None, level_valid=False):
        s = C._grade_pts(grade)
        s += min(max(conf, 0), 2)
        s += min(max(smc_tl, 0), 2)
        s += 1 if rsi_div else 0
        s += 1 if with_trend is True else (-1 if with_trend is False else 0)
        s += 1 if (rr is not None and rr >= 2) else 0
        s += 1 if level_valid else 0
        return max(0, min(10, s))
    cases = [
        ("A+", 3, 2, True, True, 3.0, True),
        ("A", 2, 1, False, False, 1.0, False),
        ("B (open space)", 0, 0, False, None, None, False),
        ("C", 9, 9, True, False, 5, True),
        ("A", 0, 0, False, True, None, True),
    ]
    ok = True
    for g, cf, st, rd, wt, r, lv in cases:
        if C.score(g, conf=cf, smc_tl=st, rsi_div=rd, with_trend=wt, rr=r, level_valid=lv) != \
           legacy(g, conf=cf, smc_tl=st, rsi_div=rd, with_trend=wt, rr=r, level_valid=lv):
            ok = False
    check("original args identical to legacy scoring", ok)


def test_score_smc_aligned():
    # premium/discount alignment is a SOFT factor mirroring with_trend: +1 aligned, -1 misaligned, 0 neutral.
    base = C.score("A", conf=1, smc_tl=1)
    check("smc_aligned True adds +1", C.score("A", conf=1, smc_tl=1, smc_aligned=True) == base + 1)
    check("smc_aligned False subtracts 1", C.score("A", conf=1, smc_tl=1, smc_aligned=False) == base - 1)
    check("smc_aligned None is neutral (default)", C.score("A", conf=1, smc_tl=1, smc_aligned=None) == base)


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
               test_score_monotonic_in_confluence, test_score_clamped,
               test_score_each_penalty_lowers, test_score_penalty_weights, test_score_penalties_stack,
               test_score_penalties_never_below_zero, test_score_backward_compat,
               test_score_smc_aligned, test_size_multiplier, test_label):
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
