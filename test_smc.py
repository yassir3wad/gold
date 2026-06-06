#!/usr/bin/env python3
"""Tests for smc.py — reads the LuxAlgo Smart Money Concepts indicator off the chart (order-block/FVG boxes,
BOS/CHoCH structure, EQH/EQL liquidity) and scores a signal's confluence with it. MANDATORY input: a signal
gets a grade '+' for each SMC element it aligns with. Pure stdlib; the chart read is injected for testing.
    python3 test_smc.py   (exit 0 = all pass)
"""
import sys
import smc as S

_r = []
def check(n, c): _r.append((n, bool(c)))


def fake_tv(canned):
    def tv(chart, *a):
        if "boxes" in a:
            return {"studies": [{"name": "Smart Money Concepts [LuxAlgo]",
                                 "zones": [{"high": 4520, "low": 4505}, {"high": 4470, "low": 4460}]}]}
        if "labels" in a:
            return {"studies": [{"name": "Smart Money Concepts [LuxAlgo]",
                                 "labels": [{"text": "BOS", "price": 4500}, {"text": "CHoCH", "price": 4480},
                                            {"text": "EQH", "price": 4525}, {"text": "EQL", "price": 4455}]}]}
        return {"studies": []}
    return tv


def test_read_smc():
    smc = S.read_smc("X", tv=fake_tv(None))
    check("read: present flag set", smc["present"] is True)
    check("read: 2 boxes", len(smc["boxes"]) == 2)
    check("read: structure = BOS+CHoCH only", sorted(s["text"] for s in smc["structure"]) == ["BOS", "CHoCH"])
    check("read: liquidity = EQH+EQL only", sorted(l["text"] for l in smc["liquidity"]) == ["EQH", "EQL"])
    empty = S.read_smc("X", tv=lambda c, *a: {"studies": []})
    check("read: missing indicator -> present False", empty["present"] is False)


def test_in_box():
    boxes = [{"high": 4520, "low": 4505}, {"high": 4470, "low": 4460}]
    check("in_box: price inside a box", S.in_box(4510, boxes) is not None)
    check("in_box: price outside all", S.in_box(4490, boxes) is None)
    check("in_box: pad widens the box", S.in_box(4490, boxes, pad=20) is not None)


def test_confluence():
    smc = S.read_smc("X", tv=fake_tv(None))
    # price 4510 is inside box[0] AND near the BOS at 4500 (tol 12) -> 2 confluence points
    r = S.confluence(4510, "LONG", smc, tol=12)
    check("confluence: in-box + near-structure -> score >= 2", r["score"] >= 2)
    check("confluence: reasons name the elements", any("order-block" in x for x in r["reasons"]))
    # isolated price with nothing nearby -> 0
    r2 = S.confluence(4300, "LONG", smc, tol=2)
    check("confluence: isolated price -> 0", r2["score"] == 0)
    # Auto-Trendline alignment adds a point
    r3 = S.confluence(4300, "LONG", smc, tol=3, trendlines=[4301])
    check("confluence: near an Auto-Trendline -> +1", r3["score"] == 1 and "Auto-Trendline" in r3["reasons"])


def test_htf_context():
    calls = []
    def spy(chart, *a):
        calls.append(a)
        return fake_tv(None)(chart, *a)
    ctx = S.read_htf_context("X", smc_tfs=("240", "60"), tl_tf="240", base_tf="5", tv=spy)
    tf_calls = [a for a in calls if a and a[0] == "timeframe"]
    check("htf: reads 4h + 1h SMC then restores 5m",
          tf_calls == [("timeframe", "240"), ("timeframe", "60"), ("timeframe", "240"), ("timeframe", "5")])
    check("htf: smc per TF (4h + 1h)", set(ctx["smc_by_tf"]) == {"240", "60"})
    check("htf: present True", ctx["present"] is True)


def test_read_chart_context():
    calls = []
    def spy(chart, *a):
        calls.append(a); return fake_tv(None)(chart, *a)
    ctx = S.read_chart_context("X", tv=spy)
    check("chart-ctx: NO timeframe switch (Option A)", not any(a and a[0] == "timeframe" for a in calls))
    check("chart-ctx: returns smc + trendlines + present", set(ctx) == {"smc", "trendlines", "present"})
    check("chart-ctx: smc read on current chart", ctx["present"] is True and len(ctx["smc"]["boxes"]) == 2)


def test_grade_confluence():
    smc = S.read_smc("X", tv=fake_tv(None))
    ctx = {"smc_by_tf": {"240": smc, "60": smc}, "trendlines": [4510.0]}
    # price 4510 hits box + BOS on BOTH TFs + a trendline -> high aggregate score
    r = S.grade_confluence(4510, "LONG", ctx, tol=12)
    check("grade-conf: aggregates across TFs + trendline", r["score"] >= 5)
    check("grade-conf: tags the TF in reasons", any("240m" in x for x in r["reasons"]))


def main():
    for fn in (test_read_smc, test_in_box, test_confluence, test_read_chart_context, test_htf_context, test_grade_confluence):
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
