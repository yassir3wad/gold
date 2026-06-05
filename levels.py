#!/usr/bin/env python3
"""Traditional key-level layer (per the howtotrade 'Key Levels' book): horizontal levels whose strength =
the NUMBER OF CLEAN TOUCHES (more touches = stronger), plus round numbers, pivot points, and a confluence
scorer. This is the counterpart to the SMC order-block zones in zones_sd (which use freshness-decay).
The strongest setups = confluence: a fresh zone sitting AT a many-times-tested level / round number.
"""
import patterns as P


def round_levels(price, step, n=2):
    """Round-number key levels around price (psychological magnets), n on each side of the nearest."""
    base = round(price / step) * step
    return [round(base + k * step, 6) for k in range(-n, n + 1)]


def pivot_points(prev_high, prev_low, prev_close):
    """Classic floor-trader pivots from the previous session's H/L/C."""
    p = (prev_high + prev_low + prev_close) / 3
    rng = prev_high - prev_low
    return {"P": p, "R1": 2 * p - prev_low, "S1": 2 * p - prev_high,
            "R2": p + rng, "S2": p - rng}


def touch_count(bars, level, tol):
    """Distinct TOUCH events of a level: the bar's range reaches within tol of the level, counted once per
    approach (price must leave the tol band before another touch counts)."""
    cnt = 0; touching = False
    for b in bars:
        near = (b["low"] <= level + tol) and (b["high"] >= level - tol)
        if near and not touching:
            cnt += 1
        touching = near
    return cnt


def horizontal_levels(bars, left=3, right=3, tol=5.0, min_touches=2):
    """Cluster swing highs/lows into horizontal levels; strength = clean touches across the whole window.
    Returns [{price, touches}] sorted strongest-first (book: 'significance grows with touches not crossed')."""
    prices = sorted(p["price"] for p in P.pivots(bars, left, right))
    clusters = []
    for pr in prices:
        if clusters and pr - clusters[-1][-1] <= tol:
            clusters[-1].append(pr)
        else:
            clusters.append([pr])
    out = []
    for c in clusters:
        center = sum(c) / len(c)
        t = touch_count(bars, center, tol)
        if t >= min_touches:
            out.append({"price": round(center, 2), "touches": t})
    return sorted(out, key=lambda x: -x["touches"])


def confluence(price, items, tol):
    """How many key-level prices (from any layer) sit within tol of `price` — the multi-layer stack count."""
    return sum(1 for x in items if abs(x - price) <= tol)
