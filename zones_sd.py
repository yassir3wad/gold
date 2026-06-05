#!/usr/bin/env python3
"""Supply/demand origin-candle zones + value-area levels (for D / 4h / 1h structural context).

User's spec:
  - Demand (buy) zone: at a swing LOW, if the origin candle is GREEN with a tall volume bar
    (fib >= 0.5 of the recent volume range), draw the zone from the candle's LOW (wick) to its body OPEN.
  - Supply (sell) zone: mirror at a swing HIGH — RED candle, tall volume, body OPEN to the candle HIGH.
  - Value area: per-day POC / VAH / VAL volume profile; a closed day's profile is FIXED -> cache by date.

These are STRUCTURAL CONTEXT (where a high-edge scalp lives), drawable and feedable into the level map.
"""
import datetime as dt
import patterns as P


def is_green(c): return c["close"] > c["open"]
def is_red(c):   return c["close"] < c["open"]


def volume_fib(bars, i, lookback=20, level=0.5):
    """True if bar i's volume sits at/above the `level` fib of the volume range over the lookback window."""
    w = bars[max(0, i - lookback + 1):i + 1]
    vols = [b.get("volume", 0) for b in w]
    if not vols:
        return False
    vmin, vmax = min(vols), max(vols)
    thr = vmin + level * (vmax - vmin)
    return bars[i].get("volume", 0) >= thr


def demand_zone(c):
    """Green origin candle -> (low wick, body open). Body bottom of a green candle is its open."""
    return (c["low"], c["open"])


def supply_zone(c):
    """Red origin candle -> (body open, high wick). Body top of a red candle is its open."""
    return (c["open"], c["high"])


def find_demand_zones(bars, left=3, right=3, lookback=20, level=0.5):
    out = []
    for p in P.pivots(bars, left, right):
        if p["kind"] != "L":
            continue
        i = p["i"]; c = bars[i]
        if is_green(c) and volume_fib(bars, i, lookback, level):
            lo, hi = demand_zone(c)
            out.append({"kind": "demand", "lo": lo, "hi": hi, "i": i, "time": c.get("time")})
    return out


def find_supply_zones(bars, left=3, right=3, lookback=20, level=0.5):
    out = []
    for p in P.pivots(bars, left, right):
        if p["kind"] != "H":
            continue
        i = p["i"]; c = bars[i]
        if is_red(c) and volume_fib(bars, i, lookback, level):
            lo, hi = supply_zone(c)
            out.append({"kind": "supply", "lo": lo, "hi": hi, "i": i, "time": c.get("time")})
    return out


def find_zones(bars, left=3, right=3, lookback=20, level=0.5):
    return find_demand_zones(bars, left, right, lookback, level) + find_supply_zones(bars, left, right, lookback, level)


def value_area(bars, bin_size=1.0, va_pct=0.70):
    """Volume-by-price profile -> (POC, VAH, VAL). Volume assigned to each bar's typical price bin;
    value area grows from POC outward (greedier side first) until va_pct of volume is enclosed."""
    hist = {}
    for b in bars:
        tp = (b["high"] + b["low"] + b["close"]) / 3
        k = round(tp / bin_size) * bin_size
        hist[k] = hist.get(k, 0) + b.get("volume", 0)
    if not hist:
        return (0.0, 0.0, 0.0)
    total = sum(hist.values()) or 1
    prices = sorted(hist)
    poc = max(hist, key=lambda k: hist[k])
    lo_i = hi_i = prices.index(poc)
    acc = hist[poc]; target = va_pct * total
    while acc < target and (lo_i > 0 or hi_i < len(prices) - 1):
        below = hist[prices[lo_i - 1]] if lo_i > 0 else -1
        above = hist[prices[hi_i + 1]] if hi_i < len(prices) - 1 else -1
        if above >= below:
            hi_i += 1; acc += hist[prices[hi_i]]
        else:
            lo_i -= 1; acc += hist[prices[lo_i]]
    return (poc, prices[hi_i], prices[lo_i])


def prior_day_vas(bars, ref_ts, n=3, cache=None, bin_size=1.0):
    """Value areas for the last `n` CLOSED days before ref_ts. Closed-day profiles are fixed -> cached by date."""
    cache = cache if cache is not None else {}
    ref_date = dt.datetime.utcfromtimestamp(ref_ts).date()
    byday = {}
    for b in bars:
        d = dt.datetime.utcfromtimestamp(b["time"]).date()
        if d < ref_date:
            byday.setdefault(d, []).append(b)
    out = []
    for d in sorted(byday, reverse=True)[:n]:
        key = d.isoformat()
        if key not in cache:
            poc, vah, val = value_area(byday[d], bin_size)
            cache[key] = {"date": key, "poc": poc, "vah": vah, "val": val}
        out.append(cache[key])
    return out
