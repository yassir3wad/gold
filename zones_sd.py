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


def is_indecision(c, frac=0.33):
    """Small-body indecision candle (doji/spinning top): body < frac of the full range."""
    rng = c["high"] - c["low"]
    if rng <= 0:
        return True
    return abs(c["close"] - c["open"]) < frac * rng


def demand_zone(c):
    """Buy zone = low wick -> BODY BOTTOM (green->open, red->close). Indecision candle -> the WHOLE candle."""
    if is_indecision(c):
        return (c["low"], c["high"])
    return (c["low"], min(c["open"], c["close"]))


def supply_zone(c):
    """Sell zone = BODY TOP -> high wick. Indecision candle -> the WHOLE candle."""
    if is_indecision(c):
        return (c["low"], c["high"])
    return (max(c["open"], c["close"]), c["high"])


def _atr(bars, i, n=14):
    w = bars[max(0, i - n):i] or bars[:1]
    return sum(b["high"] - b["low"] for b in w) / len(w) if w else 0.0


def is_impulse_kl(bars, i, kind, look=5, mult=1.5):
    """Key-level structure: the swing has an OPPOSITE impulse wave INTO it and an impulse wave OUT of it
    (impulse -> swing -> impulse). demand low: strong drop in, strong rally out. supply high: mirror."""
    atr = _atr(bars, i)
    if atr <= 0:
        return False
    if kind == "demand":
        drop_in = max(b["high"] for b in bars[max(0, i - look):i + 1]) - bars[i]["low"]
        out = bars[i + 1:i + 1 + look]
        rally_out = (max(b["high"] for b in out) - bars[i]["low"]) if out else 0.0
        return drop_in > mult * atr and rally_out > mult * atr
    rise_in = bars[i]["high"] - min(b["low"] for b in bars[max(0, i - look):i + 1])
    out = bars[i + 1:i + 1 + look]
    drop_out = (bars[i]["high"] - min(b["low"] for b in out)) if out else 0.0
    return rise_in > mult * atr and drop_out > mult * atr


def find_demand_zones(bars, left=3, right=3, lookback=20, level=0.5):
    """A buy zone at a swing LOW that CAUSED the move (impulse in + impulse out), so it anchors to the origin
    swing, not a minor continuation swing. No volume/color gate (fib-0.5 volume belongs to the SUPPORT level)."""
    out = []
    for p in P.pivots(bars, left, right):
        if p["kind"] != "L" or not is_impulse_kl(bars, p["i"], "demand"):
            continue
        i = p["i"]; c = bars[i]
        lo, hi = demand_zone(c)
        if hi <= lo:
            hi = max(c["open"], c["close"])
        out.append({"kind": "demand", "lo": lo, "hi": hi, "i": i, "time": c.get("time")})
    return out


def find_supply_zones(bars, left=3, right=3, lookback=20, level=0.5):
    """A sell zone at a swing HIGH that CAUSED the move (impulse in + impulse out) — the origin, not a minor
    lower-high continuation."""
    out = []
    for p in P.pivots(bars, left, right):
        if p["kind"] != "H" or not is_impulse_kl(bars, p["i"], "supply"):
            continue
        i = p["i"]; c = bars[i]
        lo, hi = supply_zone(c)
        if lo >= hi:
            lo = min(c["open"], c["close"])
        out.append({"kind": "supply", "lo": lo, "hi": hi, "i": i, "time": c.get("time")})
    return out


def zone_crossings(bars, zone):
    """Times price has DECISIVELY crossed the zone (closed beyond it, alternating sides) since formation:
    0 = fresh; 1 = broken once (role flips); >=2 = traversed both ways = consumed/invalid."""
    lo, hi, i = zone["lo"], zone["hi"], zone["i"]
    side = None; crossings = 0
    for b in bars[i + 1:]:
        s = "above" if b["close"] > hi else "below" if b["close"] < lo else None
        if s is None:
            continue
        if side and s != side:
            crossings += 1
        side = s
    return crossings


def is_impulse_candle(bars, i, mult=1.5):
    """A single strong candle whose BODY is large vs ATR — it originates a move on its own."""
    atr = _atr(bars, i)
    return atr > 0 and abs(bars[i]["close"] - bars[i]["open"]) > mult * atr


def find_impulse_candle_zones(bars, mult=1.5):
    """A strong bullish impulse candle IS a buy zone (its base low->open); a strong bearish one a sell zone
    (open->high) — even when the candle isn't a swing pivot (the 'demand/supply candle' that launches a move)."""
    out = []
    for i, c in enumerate(bars):
        if not is_impulse_candle(bars, i, mult):
            continue
        if c["close"] > c["open"]:
            lo, hi = demand_zone(c); out.append({"kind": "demand", "lo": lo, "hi": hi, "i": i, "time": c.get("time")})
        elif c["close"] < c["open"]:
            lo, hi = supply_zone(c); out.append({"kind": "supply", "lo": lo, "hi": hi, "i": i, "time": c.get("time")})
    return out


def _merge_to_extreme(zones, kind, max_gap=4):
    """Merge same-kind zones that PRICE-OVERLAP and are TIME-ADJACENT (<= max_gap bars), keeping the EXTREME
    (highest supply / lowest demand) — so a cluster anchors to the origin swing (A), but a separate-day zone
    is NOT swallowed."""
    out = []
    for z in sorted(zones, key=lambda z: z["i"]):
        hit = next((o for o in out if z["lo"] <= o["hi"] and z["hi"] >= o["lo"] and abs(z["i"] - o["i"]) <= max_gap), None)
        if hit is None:
            out.append(z)
        elif (kind == "supply" and z["hi"] > hit["hi"]) or (kind == "demand" and z["lo"] < hit["lo"]):
            out[out.index(hit)] = z
    return out


def find_zones(bars, left=3, right=3, lookback=20, level=0.5):
    ic = find_impulse_candle_zones(bars)
    d = _merge_to_extreme(find_demand_zones(bars, left, right, lookback, level) + [z for z in ic if z["kind"] == "demand"], "demand")
    s = _merge_to_extreme(find_supply_zones(bars, left, right, lookback, level) + [z for z in ic if z["kind"] == "supply"], "supply")
    return d + s


def caused_bos(bars, i, kind, lookback=20):
    """Did the move AWAY from the origin candle break structure? demand: the rally took out the recent
    structure HIGH before the zone; supply: the drop took out the recent structure LOW. This is the
    'price reached it, didn't break, pulled back -> BOS' confirmation = the key-level signature."""
    after = bars[i + 1:]
    if not after:
        return False
    prior = bars[max(0, i - lookback):i]
    if not prior:
        return False
    if kind == "demand":
        return max(b["high"] for b in after) > max(b["high"] for b in prior)
    return min(b["low"] for b in after) < min(b["low"] for b in prior)


def touches(bars, zone):
    """How many times price RE-ENTERED the zone after it formed (retests consume its strength)."""
    lo, hi, i = zone["lo"], zone["hi"], zone["i"]
    cnt = 0; inside = True   # the origin candle itself is 'inside'
    for b in bars[i + 1:]:
        in_zone = b["low"] <= hi and b["high"] >= lo
        if in_zone and not inside:
            cnt += 1
        inside = in_zone
    return cnt


def is_broken(bars, zone):
    """A clean break = a candle CLOSES through the zone in the invalidating direction -> dead."""
    lo, hi, i = zone["lo"], zone["hi"], zone["i"]
    for b in bars[i + 1:]:
        if zone["kind"] == "demand" and b["close"] < lo:
            return True
        if zone["kind"] == "supply" and b["close"] > hi:
            return True
    return False


def wick_broken(bars, zone):
    """A KEY LEVEL fails if price pierces the zone's far edge with a WICK (even without closing through):
    demand -> any later low < zone low; supply -> any later high > zone high."""
    lo, hi, i = zone["lo"], zone["hi"], zone["i"]
    for b in bars[i + 1:]:
        if zone["kind"] == "demand" and b["low"] < lo:
            return True
        if zone["kind"] == "supply" and b["high"] > hi:
            return True
    return False


def kl_score_from(bos, broken, touches, max_touches=3):
    """Pure score: KEY LEVEL = BOS-confirmed, not broken, not exhausted. Fresh=1.0, decays 0.25 per retest,
    dead (0) once broken / not-a-KL / >= max_touches reactions."""
    if broken or not bos or touches >= max_touches:
        return 0.0
    return round(1.0 - 0.25 * touches, 2)


def key_level_score(bars, zone, max_touches=3):
    return kl_score_from(caused_bos(bars, zone["i"], zone["kind"]), is_broken(bars, zone),
                         touches(bars, zone), max_touches)


def mark_key_levels(bars, left=3, right=3, lookback=20, level=0.5, max_touches=3):
    """Find S/D zones and tag each with bos / touches / broken / score / key_level. Key levels (score>0)
    are the TOP-probability tier; sorted strongest first."""
    zones = find_zones(bars, left, right, lookback, level)
    for z in zones:
        z["bos"] = caused_bos(bars, z["i"], z["kind"])
        z["touches"] = touches(bars, z)
        z["broken"] = is_broken(bars, z)
        z["crossings"] = zone_crossings(bars, z)
        z["valid"] = z["crossings"] < 2            # traversed both ways (>=2) => consumed/invalid
        z["impulse"] = is_impulse_kl(bars, z["i"], z["kind"])   # opposite-impulse-in + impulse-out
        z["wick_broken"] = wick_broken(bars, z)                 # a wick through the level = KL failure
        kl_ok = z["bos"] and z["impulse"] and not z["wick_broken"]   # KL needs BOS + impulse + never wicked through
        z["score"] = kl_score_from(kl_ok, z["broken"], z["touches"], max_touches) if z["valid"] else 0.0
        z["key_level"] = z["score"] > 0
    return sorted(zones, key=lambda z: -z["score"])


def big_candle(bars, i, lookback=20, level=0.5):
    """A 'big' candle = large body AND high volume, both at/above the `level` fib of the recent range."""
    w = bars[max(0, i - lookback + 1):i + 1]
    bodies = [abs(b["close"] - b["open"]) for b in w]
    bmin, bmax = min(bodies), max(bodies)
    if bmax <= bmin:
        return False                    # no contrast -> not distinguishably 'big'
    body = abs(bars[i]["close"] - bars[i]["open"])
    big = body >= bmin + level * (bmax - bmin)
    return bool(big and volume_fib(bars, i, lookback, level))


def small_opposite_wick(c, frac=0.4):
    """A support (green) candle must have a SMALL upper wick; a resistance (red) candle a small lower wick.
    A long opposite-direction wick = rejection against the level -> disqualify."""
    rng = c["high"] - c["low"]
    if rng <= 0:
        return True
    if c["close"] > c["open"]:            # green -> opposite wick is the UPPER wick
        return (c["high"] - c["close"]) <= frac * rng
    return (c["close"] - c["low"]) <= frac * rng   # red -> opposite wick is the LOWER wick


def sr_levels(bars, lookback=20, level=0.5):
    """Support/resistance LEVELS from big high-volume candles (distinct from order-block zones):
      - big GREEN candle -> support at its open (launch base)
      - big RED candle   -> resistance at its open
    Polarity flip: once a later candle CLOSES through the level, it flips to the opposite role.
    Returns dicts {price, origin, role, flipped, i, time}."""
    out = []
    for i, c in enumerate(bars):
        if not big_candle(bars, i, lookback, level) or not small_opposite_wick(c):
            continue
        if c["close"] > c["open"]:
            origin, px = "support", c["open"]
        elif c["close"] < c["open"]:
            origin, px = "resistance", c["open"]
        else:
            continue
        flipped = False
        for b in bars[i + 1:]:
            if origin == "support" and b["close"] < px:
                flipped = True; break
            if origin == "resistance" and b["close"] > px:
                flipped = True; break
        role = ("resistance" if origin == "support" else "support") if flipped else origin
        out.append({"price": round(px, 2), "origin": origin, "role": role,
                    "flipped": flipped, "i": i, "time": c.get("time")})
    return out


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
