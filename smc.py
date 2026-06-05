#!/usr/bin/env python3
"""Read the LuxAlgo 'Smart Money Concepts' indicator off the chart and score a signal's confluence with it.
MANDATORY input (the indicator must be on every chart): order-block / FVG boxes, BOS/CHoCH structure, and
EQH/EQL liquidity. Each SMC element a signal aligns with is a '+' on the trade grade — on TOP of our own
zones (zones_sd). Date-faithful in replay (the indicator recomputes on the historical bars).
"""
import subprocess, os, json

TVDIR = os.path.expanduser("~/tradingview-mcp")
SMC_FILTER = "Smart Money"


def _default_tv(chart, *a):
    env = dict(os.environ)
    if chart:
        env["TV_CHART"] = chart
    try:
        r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=40, env=env)
        return json.loads(r.stdout)
    except Exception:
        return {}


def read_smc(chart, tv=None):
    """Pull the SMC boxes + labels. Returns {present, boxes:[{high,low}], structure:[{text,price}],
    liquidity:[{text,price}]}. `present` is False when the indicator isn't on the chart (it's mandatory)."""
    tv = tv or _default_tv
    bx = tv(chart, "data", "boxes", "--study-filter", SMC_FILTER).get("studies", [])
    lb = tv(chart, "data", "labels", "--study-filter", SMC_FILTER).get("studies", [])
    boxes = bx[0].get("zones", []) if bx else []
    labels = lb[0].get("labels", []) if lb else []
    structure = [l for l in labels if l.get("text") in ("BOS", "CHoCH")]
    liquidity = [l for l in labels if l.get("text") in ("EQH", "EQL")]
    return {"present": bool(bx), "boxes": boxes, "structure": structure, "liquidity": liquidity}


TRENDLINE_FILTER = "Auto Trendlines"


def read_trendlines(chart, tv=None):
    """Read the 'Auto Trendlines' indicator's line levels. NOTE: that indicator draws DIAGONAL lines, which
    the line-reader can't extract (returns 0 horizontal levels) — so this is empty in practice. Trendline
    confluence is computed from our own HTF trendlines instead (see patterns/htf_trendlines)."""
    tv = tv or _default_tv
    studies = tv(chart, "data", "lines", "--study-filter", TRENDLINE_FILTER).get("studies", [])
    s = next((x for x in studies if x.get("name") == "Auto Trendlines"), None)
    return list(s.get("horizontal_levels", [])) if s else []


def in_box(price, boxes, pad=0.0):
    """The order-block / FVG box containing price (± pad), or None."""
    return next((b for b in boxes if b["low"] - pad <= price <= b["high"] + pad), None)


def near_level(price, levels, tol):
    return any(abs(price - lv) <= tol for lv in levels)


def confluence(price, side, smc, tol, trendlines=None):
    """Confluence score added to the trade grade (on top of our own zones): +1 in an SMC order-block/FVG,
    +1 near a BOS/CHoCH, +1 near EQH/EQL liquidity, +1 near an Auto-Trendline. Returns {score, reasons}."""
    score = 0; reasons = []
    if in_box(price, smc.get("boxes", [])):
        score += 1; reasons.append("SMC order-block/FVG")
    if near_level(price, [s["price"] for s in smc.get("structure", [])], tol):
        score += 1; reasons.append("SMC BOS/CHoCH")
    if near_level(price, [l["price"] for l in smc.get("liquidity", [])], tol):
        score += 1; reasons.append("SMC liquidity (EQH/EQL)")
    if near_level(price, trendlines or smc.get("trendlines", []), tol):
        score += 1; reasons.append("Auto-Trendline")
    return {"score": score, "reasons": reasons}
