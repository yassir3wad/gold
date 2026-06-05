#!/usr/bin/env python3
"""Structural pattern detectors — channel, fibonacci, double-top/bottom — on OHLC bars.

These are STRUCTURAL CONTEXT, not 1m triggers. The backtest showed the per-trade edge (~1p) is below
the gold spread (~3p), so the way to profit is taking the FEW scalps that sit at high-edge locations:
the top/bottom of a channel, a fib retracement into a zone, a double-top neckline. This module finds
those locations so the engine/AI-review can weight an entry up (or only fire there). Each detector is
pure (bars in, structure out) and drawable (see draw_patterns.py).
"""


def _reg(ys):
    """Least-squares slope/intercept for y over x=0..n-1."""
    n = len(ys)
    if n < 2:
        return 0.0, (ys[0] if ys else 0.0)
    xm = (n - 1) / 2.0
    ym = sum(ys) / n
    num = sum((i - xm) * (ys[i] - ym) for i in range(n))
    den = sum((i - xm) ** 2 for i in range(n))
    slope = num / den if den else 0.0
    return slope, ym - slope * xm


def pivots(bars, left=3, right=3):
    """Swing highs/lows: bar i is a pivot-high if its high is the max in [i-left, i+right] (sym for low).
    Edges (first `left`, last `right`) are never pivots."""
    out = []
    for i in range(left, len(bars) - right):
        win = bars[i - left:i + right + 1]
        if bars[i]["high"] >= max(b["high"] for b in win):
            out.append({"i": i, "price": bars[i]["high"], "kind": "H"})
        if bars[i]["low"] <= min(b["low"] for b in win):
            out.append({"i": i, "price": bars[i]["low"], "kind": "L"})
    return out


def detect_channel(bars, lookback=60, dir_thresh=0.5):
    """Linear-regression channel over the last `lookback` bars.
    Returns {direction: up|down|range, slope, upper, lower, mid, pos} where upper/lower/mid are prices at
    the last bar and pos is where the last close sits in the band (0=lower, 1=upper). None if too few bars."""
    b = bars[-lookback:] if lookback else bars
    if len(b) < 5:
        return None
    closes = [x["close"] for x in b]
    slope, intercept = _reg(closes)
    n = len(b)
    reg = [intercept + slope * i for i in range(n)]
    up_off = max(b[i]["high"] - reg[i] for i in range(n))
    lo_off = max(reg[i] - b[i]["low"] for i in range(n))
    reg_last = reg[-1]
    upper, lower, mid = reg_last + up_off, reg_last - lo_off, reg_last
    band = upper - lower
    rise = slope * (n - 1)
    strength = rise / band if band else 0.0
    direction = "up" if strength > dir_thresh else "down" if strength < -dir_thresh else "range"
    last = b[-1]["close"]
    pos = (last - lower) / band if band else 0.5
    pos = max(0.0, min(1.0, pos))
    return {"direction": direction, "slope": slope, "upper": upper, "lower": lower,
            "mid": mid, "pos": pos, "band": band, "lookback": n}


FIB = (0.236, 0.382, 0.5, 0.618, 0.786)


def fib_levels(high, low):
    """Retracement price levels measured down from the high of the swing (high-low range)."""
    d = high - low
    return {l: high - d * l for l in FIB}


def golden_pocket(high, low):
    """The 0.618–0.786 price band (the high-reaction 'golden pocket'). Returns (low_price, high_price)."""
    f = fib_levels(high, low)
    return (min(f[0.618], f[0.786]), max(f[0.618], f[0.786]))


def active_swing(bars, left=3, right=3, lookback=None):
    """Most recent dominant swing over the window: the extreme high & low and the direction between them
    (up if the high printed after the low). Used to anchor fib levels."""
    b = bars[-lookback:] if lookback else bars
    if len(b) < 2:
        return None
    hi_i = max(range(len(b)), key=lambda i: b[i]["high"])
    lo_i = min(range(len(b)), key=lambda i: b[i]["low"])
    return {"high": b[hi_i]["high"], "low": b[lo_i]["low"],
            "direction": "up" if hi_i > lo_i else "down", "hi_i": hi_i, "lo_i": lo_i}


def detect_double(bars, left=3, right=3, tol=0.003):
    """Double-top / double-bottom: two recent same-type pivots within `tol` (relative) with an opposing
    pivot between them (the neckline). Returns {kind, level, neckline, peaks} or None. Top checked first."""
    pv = pivots(bars, left, right)
    highs = [p for p in pv if p["kind"] == "H"]
    lows = [p for p in pv if p["kind"] == "L"]
    if len(highs) >= 2:
        a, c = highs[-2], highs[-1]
        if abs(a["price"] - c["price"]) / max(a["price"], 1e-9) <= tol:
            mid = [l for l in lows if a["i"] < l["i"] < c["i"]]
            if mid:
                return {"kind": "double-top", "level": (a["price"] + c["price"]) / 2,
                        "neckline": min(mid, key=lambda l: l["price"])["price"], "peaks": [a["i"], c["i"]]}
    if len(lows) >= 2:
        a, c = lows[-2], lows[-1]
        if abs(a["price"] - c["price"]) / max(a["price"], 1e-9) <= tol:
            mid = [h for h in highs if a["i"] < h["i"] < c["i"]]
            if mid:
                return {"kind": "double-bottom", "level": (a["price"] + c["price"]) / 2,
                        "neckline": max(mid, key=lambda h: h["price"])["price"], "peaks": [a["i"], c["i"]]}
    return None
