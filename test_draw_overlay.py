#!/usr/bin/env python3
"""Tests for draw_overlay.overlay_specs — the pure decision of WHAT to draw on the chart: prior-day
VAH/VAL/POC lines (labeled with Level State), SP zones, and SMC order-block boxes near price (colored by
side). Pure stdlib.  python3 test_draw_overlay.py
"""
import sys
import draw_overlay as D

_r = []
def check(n, c): _r.append((n, bool(c)))


VA = {"vah": 4479.0, "val": 4445.0, "poc": 4463.0}
STATES = {"VAH": "Rejected", "VAL": "Flipped", "POC": "Untested"}
SP = [[4422.0, 4428.0]]
BOXES = [
    {"high": 4452.0, "low": 4448.0},   # below price -> demand, within band
    {"high": 4490.0, "low": 4486.0},   # above price -> supply, within band
    {"high": 4600.0, "low": 4595.0},   # far above -> dropped (outside band)
]


TRENDLINES = [4458.0, 4170.0]   # one near price (drawn), one far (still drawn — read already filters near)


def specs():
    return D.overlay_specs(4460.0, VA, STATES, SP, BOXES, band=35.0, va_date="2026-06-05", trendlines=TRENDLINES)


def test_va_lines():
    s = specs()
    by = {x["kind"]: x for x in s if x["type"] == "hline"}
    check("POC line present", "POC" in by and by["POC"]["price"] == 4463.0)
    check("VAH line present", "VAH" in by and by["VAH"]["price"] == 4479.0)
    check("VAL line present", "VAL" in by and by["VAL"]["price"] == 4445.0)
    check("labels carry the Level State", "Rejected" in by["VAH"]["label"] and "Flipped" in by["VAL"]["label"])
    check("labels show the DATE not the price", "06-05" in by["POC"]["label"] and "4463" not in by["POC"]["label"])
    check("POC/VAH/VAL distinct colors", len({by["POC"]["color"], by["VAH"]["color"], by["VAL"]["color"]}) == 3)


def test_sp_zone():
    s = [x for x in specs() if x["kind"] == "SP"]
    check("one SP rect", len(s) == 1 and s[0]["type"] == "rect")
    check("SP rect spans the zone", s[0]["price"] == 4428.0 and s[0]["price2"] == 4422.0)


def test_order_blocks_near_price_only():
    obs = [x for x in specs() if x["kind"].startswith("OB")]
    check("2 OB boxes within band (far one dropped)", len(obs) == 2)
    kinds = sorted(x["kind"] for x in obs)
    check("one demand (below) + one supply (above)", kinds == ["OB-demand", "OB-supply"])
    demand = next(x for x in obs if x["kind"] == "OB-demand")
    supply = next(x for x in obs if x["kind"] == "OB-supply")
    check("demand box is the one below price", demand["price"] == 4452.0 and demand["price2"] == 4448.0)
    check("demand vs supply different colors", demand["color"] != supply["color"])


def test_trendlines():
    tl = [x for x in specs() if x["kind"] == "TL"]
    check("a TL hline per trendline", len(tl) == 2 and all(x["type"] == "hline" for x in tl))
    check("TL lines at the trendline prices", sorted(x["price"] for x in tl) == [4170.0, 4458.0])
    check("TL distinct color from VA lines", tl[0]["color"] not in (D.POC_C, D.VAH_C, D.VAL_C))


def test_no_va_no_lines():
    s = D.overlay_specs(4460.0, {"vah": None, "val": None, "poc": None}, {}, [], BOXES, band=35.0)
    check("no VA -> no VA hlines, still draws nearby OBs", all(x["kind"] not in ("POC","VAH","VAL") for x in s) and any(x["kind"].startswith("OB") for x in s))


def main():
    for fn in (test_va_lines, test_sp_zone, test_order_blocks_near_price_only, test_trendlines, test_no_va_no_lines):
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
