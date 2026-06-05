#!/usr/bin/env python3
"""Tests for levels.py — the TRADITIONAL key-level layer (horowtotrade book): horizontal levels with
touch-count strength (more clean touches = stronger), round numbers, pivot points, and confluence scoring.
Distinct from the SMC order-block zones (which use freshness-decay). Pure stdlib.
    python3 test_levels.py   (exit 0 = all pass)
"""
import sys
import levels as L

_r = []
def check(n, c): _r.append((n, bool(c)))
def approx(a, b, t=1e-6): return a is not None and abs(a - b) <= t
def C(h, l, t=0): return {"time": t, "open": (h + l) / 2, "high": float(h), "low": float(l), "close": (h + l) / 2}


def test_round_levels():
    r = L.round_levels(4537, step=50, n=2)
    check("round: includes nearest round 4550", any(approx(x, 4550) for x in r))
    check("round: spans below+above", min(r) < 4537 < max(r))


def test_pivot_points():
    p = L.pivot_points(110, 90, 100)   # H,L,C
    check("pivot: P = (H+L+C)/3", approx(p["P"], 100))
    check("pivot: R1 = 2P-L", approx(p["R1"], 110))
    check("pivot: S1 = 2P-H", approx(p["S1"], 90))
    check("pivot: R2 = P+(H-L)", approx(p["R2"], 120))
    check("pivot: S2 = P-(H-L)", approx(p["S2"], 80))


def test_touch_count():
    # price touches level 100 three separate times (leaves and returns)
    bars = [C(101, 99), C(105, 103), C(101, 99), C(106, 104), C(100.5, 98.5), C(107, 105)]
    check("touch: counts 3 distinct touches of 100", L.touch_count(bars, 100, tol=1.0) == 3)
    check("touch: a far level has 0 touches", L.touch_count(bars, 130, tol=1.0) == 0)


def test_horizontal_levels():
    # a resistance ~110 tapped 3x + a support ~100 tapped 2x, with min_touches=2
    bars = ([C(110, 108)] + [C(105, 100)] + [C(110.5, 107)] + [C(104, 100)] +
            [C(110, 106)] + [C(103, 100.2)])
    hl = L.horizontal_levels(bars, left=1, right=1, tol=2.0, min_touches=2)
    check("horizontal: finds a multi-touch level", len(hl) >= 1)
    check("horizontal: strongest is the most-touched", hl[0]["touches"] >= hl[-1]["touches"])
    check("horizontal: levels carry a touch count", all("touches" in x and "price" in x for x in hl))


def test_confluence():
    items = [4500, 4502, 4540, 4499.5]
    check("confluence: counts levels within tol of price", L.confluence(4500, items, tol=3) == 3)
    check("confluence: isolated price scores low", L.confluence(4540, items, tol=3) == 1)


def main():
    for fn in (test_round_levels, test_pivot_points, test_touch_count, test_horizontal_levels, test_confluence):
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
