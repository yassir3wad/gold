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
                                            {"text": "EQH", "price": 4525}, {"text": "EQL", "price": 4455},
                                            {"text": "Strong High", "price": 4530}, {"text": "Weak Low", "price": 4450}]}]}
        return {"studies": []}
    return tv


def test_read_smc():
    smc = S.read_smc("X", tv=fake_tv(None))
    check("read: present flag set", smc["present"] is True)
    check("read: 2 boxes", len(smc["boxes"]) == 2)
    check("read: structure = BOS+CHoCH only", sorted(s["text"] for s in smc["structure"]) == ["BOS", "CHoCH"])
    check("read: liquidity = EQH+EQL only", sorted(l["text"] for l in smc["liquidity"]) == ["EQH", "EQL"])
    check("read: swings = Strong/Weak High/Low (default-on liquidity)",
          sorted(s["text"] for s in smc["swings"]) == ["Strong High", "Weak Low"])
    empty = S.read_smc("X", tv=lambda c, *a: {"studies": []})
    check("read: missing indicator -> present False", empty["present"] is False)


def test_dedup_levels():
    items = [{"text": "BOS", "price": 4500}, {"text": "BOS", "price": 4501}, {"text": "CHoCH", "price": 4480}]
    out = S.dedup_levels(items, tol=2)
    check("dedup_levels: prices within tol collapse to one", len(out) == 2)
    out0 = S.dedup_levels([{"price": 4500}, {"price": 4500}, {"price": 4480}], tol=0)
    check("dedup_levels: exact duplicates collapse at tol 0", len(out0) == 2)


def test_read_smc_lifts_label_cap():
    seen = {}
    def tv(chart, *a):
        if "labels" in a:
            seen["a"] = a
            return {"studies": [{"name": "Smart Money Concepts [LuxAlgo]", "labels": []}]}
        if "boxes" in a:
            return {"studies": [{"name": "Smart Money Concepts [LuxAlgo]", "zones": []}]}
        return {"studies": []}
    S.read_smc("X", tv=tv)
    a = seen.get("a", ())
    check("read: labels read lifts the 50-label cap (--max passed, >=200)",
          "--max" in a and int(a[a.index("--max") + 1]) >= 200)


def test_filter_near():
    ctx = {"smc": {"boxes": [{"high": 4520, "low": 4505}, {"high": 5306, "low": 5300}],
                   "structure": [{"text": "BOS", "price": 4500}, {"text": "BOS", "price": 4870}],
                   "liquidity": [{"text": "EQL", "price": 4531}],
                   "swings": [{"text": "Strong High", "price": 4870}]},
           "trendlines": [4542, 4870], "present": True}
    out = S.filter_near(ctx, price=4539, band=50)
    check("filter_near: keeps the near box, drops the far one",
          len(out["smc"]["boxes"]) == 1 and out["smc"]["boxes"][0]["high"] == 4520)
    check("filter_near: drops far structure", [s["price"] for s in out["smc"]["structure"]] == [4500])
    check("filter_near: keeps near liquidity", len(out["smc"]["liquidity"]) == 1)
    check("filter_near: drops far swing", out["smc"]["swings"] == [])
    check("filter_near: filters trendlines to near price", out["trendlines"] == [4542])


def test_case_insensitive_and_dedup():
    def tv(chart, *a):
        if "boxes" in a:
            return {"studies": [{"name": "Smart Money Concepts [LuxAlgo]", "zones": []}]}
        if "labels" in a:
            return {"studies": [{"name": "Smart Money Concepts [LuxAlgo]", "labels": [
                {"text": "bos", "price": 4500}, {"text": "BOS", "price": 4501},   # case-variant + near-dup
                {"text": "choch", "price": 4480},
                {"text": "eql", "price": 4455}, {"text": "strong low", "price": 4450}]}]}
        return {"studies": []}
    smc = S.read_smc("X", tv=tv, dedup_tol=2)
    # 'bos'/'BOS' (near-dup) collapse to one, plus 'choch' -> 2 structure entries (case-insensitive match)
    check("ci+dedup: lowercase recognized & near-dups collapsed", len(smc["structure"]) == 2)
    check("ci: lowercase 'eql' -> liquidity", any(l["text"].upper() == "EQL" for l in smc["liquidity"]))
    check("ci: lowercase 'strong low' -> swing", any("low" in s["text"].lower() for s in smc["swings"]))


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
    # near the Strong High (4530) -> +1 strong/weak H/L liquidity
    r4 = S.confluence(4529, "LONG", smc, tol=3)
    check("confluence: near Strong/Weak H/L -> +1", any("strong/weak" in x.lower() for x in r4["reasons"]))


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
        calls.append(a)
        if a and a[0] == "state":
            return {"studies": [{"name": "Smart Money Concepts [LuxAlgo]", "id": "AJ1"},
                                {"name": "Auto Trendlines", "id": "TL1"}]}
        return fake_tv(None)(chart, *a)
    ctx = S.read_chart_context("X", tv=spy)
    check("chart-ctx: NO timeframe switch (Option A)", not any(a and a[0] == "timeframe" for a in calls))
    check("chart-ctx: returns smc + trendlines + present", set(ctx) == {"smc", "trendlines", "present"})
    check("chart-ctx: smc read on current chart", ctx["present"] is True and len(ctx["smc"]["boxes"]) == 2)
    # store-and-hide: shows then hides BOTH indicators
    toggles = [a for a in calls if a and a[0] == "indicator" and a[1] == "toggle"]
    shown = [a for a in toggles if "--visible" in a]; hidden = [a for a in toggles if "--hidden" in a]
    check("chart-ctx: shows both indicators to read", len(shown) == 2)
    check("chart-ctx: hides both after reading (store-and-hide)", len(hidden) == 2)


def test_grade_confluence():
    smc = S.read_smc("X", tv=fake_tv(None))
    ctx = {"smc_by_tf": {"240": smc, "60": smc}, "trendlines": [4510.0]}
    # price 4510 hits box + BOS on BOTH TFs + a trendline -> high aggregate score
    r = S.grade_confluence(4510, "LONG", ctx, tol=12)
    check("grade-conf: aggregates across TFs + trendline", r["score"] >= 5)
    check("grade-conf: tags the TF in reasons", any("240m" in x for x in r["reasons"]))


def main():
    for fn in (test_read_smc, test_read_smc_lifts_label_cap, test_filter_near, test_dedup_levels, test_case_insensitive_and_dedup, test_in_box, test_confluence, test_read_chart_context, test_htf_context, test_grade_confluence):
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
