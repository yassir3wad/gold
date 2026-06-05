#!/usr/bin/env python3
"""Tests for zones_sd.py — supply/demand origin-candle zones + value-area levels.
Pure stdlib. Encodes the user's spec: demand = green swing-low candle with a tall (fib-0.5) volume bar,
zone = low-wick -> body open; supply = mirror; value area = POC/VAH/VAL volume profile (cached per closed day).
    python3 test_zones_sd.py   (exit 0 = all pass)
"""
import sys
import zones_sd as Z

_r = []
def check(n, c): _r.append((n, bool(c)))
def approx(a, b, t=1e-6): return a is not None and abs(a - b) <= t
def C(o, h, l, c, v, t=0): return {"time": t, "open": o, "high": h, "low": l, "close": c, "volume": v}


def test_volume_fib():
    bars = [C(1, 2, 0, 1, v) for v in (10, 10, 10, 10, 100)]
    check("vol-fib: tall last bar (vmax) passes 0.5", Z.volume_fib(bars, 4, lookback=5) is True)
    bars2 = [C(1, 2, 0, 1, v) for v in (10, 100, 10, 10, 30)]
    # window vmin=10 vmax=100 -> thr = 10 + .5*90 = 55; bar4 vol=30 < 55 -> fail
    check("vol-fib: short bar fails 0.5", Z.volume_fib(bars2, 4, lookback=5) is False)
    check("vol-fib: bar at the 0.5 midpoint passes", Z.volume_fib([C(1,2,0,1,0),C(1,2,0,1,100),C(1,2,0,1,50)], 2, lookback=3) is True)


def test_zone_geometry():
    green = C(100, 105, 98, 104, 50)     # bullish: body = [open 100, close 104]
    lo, hi = Z.demand_zone(green)
    check("demand: low-wick to body open", approx(lo, 98) and approx(hi, 100))
    red = C(104, 106, 100, 101, 50)      # bearish: body = [close 101, open 104]
    lo2, hi2 = Z.supply_zone(red)
    check("supply: body open to high-wick", approx(lo2, 104) and approx(hi2, 106))
    # RED swing-low candle -> zone to CLOSE (body bottom), not open
    red_low = C(110, 111, 100, 105, 50)  # bearish: body bottom = close 105
    lo3, hi3 = Z.demand_zone(red_low)
    check("demand: red swing-low -> low to CLOSE (body bottom)", approx(lo3, 100) and approx(hi3, 105))
    # small indecision candle -> whole candle is the zone (top to bottom)
    doji = C(100, 110, 90, 101, 50)      # body 1 of 20 range -> indecision
    lo4, hi4 = Z.demand_zone(doji)
    check("demand: indecision candle -> whole candle (low..high)", approx(lo4, 90) and approx(hi4, 110))


def test_find_demand_zone():
    # rising-then-dipping series with a clear swing low at i=5 on a GREEN, high-volume candle
    base = [C(110-i, 111-i, 109-i, 110-i, 10) for i in range(5)]          # falling into the low
    low_candle = C(104, 106, 103, 105.5, 100)                             # green, tall volume, the swing low
    rise = [C(106+i, 107+i, 105+i, 106+i, 10) for i in range(5)]          # rally away
    bars = base + [low_candle] + rise
    zones = Z.find_demand_zones(bars, left=2, right=2, lookback=12)
    check("find-demand: detects a buy zone at the green swing low",
          any(abs(z["lo"] - 103) < 1 and z["kind"] == "demand" for z in zones))
    # a RED swing-low candle ALSO gets a buy zone (color/volume don't matter for zones)
    bars_red = base + [C(106, 106, 103, 104, 100)] + rise
    check("find-demand: red swing-low is ALSO a buy zone", bool(Z.find_demand_zones(bars_red, left=2, right=2, lookback=12)))


def test_value_area():
    # volume piled at price 100 -> POC ~100; small wings -> VA brackets it
    bars = ([C(100, 100.5, 99.5, 100, 100)] * 10 +
            [C(102, 102.5, 101.5, 102, 5)] * 2 + [C(98, 98.5, 97.5, 98, 5)] * 2)
    poc, vah, val = Z.value_area(bars, bin_size=1.0)
    check("VA: POC at the high-volume price", approx(round(poc), 100))
    check("VA: VAH >= POC >= VAL", vah >= poc >= val)
    check("VA: value area is tight around POC", (vah - val) <= 6)


def test_prior_day_vas_cached():
    # two days of bars; prior-day VA computed once and cached by date
    import datetime as dt
    d1 = int(dt.datetime(2026, 6, 1, 12, tzinfo=dt.timezone.utc).timestamp())
    d2 = int(dt.datetime(2026, 6, 2, 12, tzinfo=dt.timezone.utc).timestamp())
    bars = [C(100, 101, 99, 100, 50, d1 + i*60) for i in range(20)] + [C(110, 111, 109, 110, 50, d2 + i*60) for i in range(20)]
    cache = {}
    vas = Z.prior_day_vas(bars, ref_ts=int(dt.datetime(2026, 6, 3, tzinfo=dt.timezone.utc).timestamp()), n=2, cache=cache)
    check("prior-VA: returns up to n prior days", len(vas) == 2)
    check("prior-VA: each has poc/vah/val + date label", all({"poc","vah","val","date"} <= set(v) for v in vas))
    check("prior-VA: closed days cached by date", len(cache) >= 2)


def test_key_level_bos_and_score():
    # rise to a swing high (112), decline to a GREEN high-volume swing low, then rally that BREAKS 112 -> BOS
    bars = [C(100,105,99,104,10), C(104,112,103,108,10), C(108,109,102,103,10),
            C(103,104,96,97,10),  C(97,101,94,100,100),  C(100,107,99,106,10), C(106,116,105,115,10)]
    z = Z.find_demand_zones(bars, left=1, right=1, lookback=7)
    check("KL: a demand zone exists at the green swing low", any(zz["i"] == 4 for zz in z))
    dz = next(zz for zz in z if zz["i"] == 4)
    check("KL: rally broke prior swing high -> BOS", Z.caused_bos(bars, 4, "demand") is True)
    s = Z.key_level_score(bars, dz)
    check("KL: fresh BOS-confirmed zone scores top (1.0)", approx(s, 1.0))
    # no-BOS variant: same low but the rally never reclaims 112 -> not a key level
    nb = bars[:5] + [C(100,106,99,105,10), C(105,108,104,107,10)]   # tops out at 108 < 112
    check("KL: no BOS -> score 0", approx(Z.key_level_score(nb, Z.find_demand_zones(nb, 1, 1, 7)[0]), 0.0))
    # broken variant: after the rally, a later candle CLOSES below the demand zone -> invalid
    bk = bars + [C(100,101,90,91,10)]   # i7 closes 91 < zone low 94 (i4 stays the swing low)
    check("KL: closed-through zone -> broken -> score 0", approx(Z.key_level_score(bk, dz), 0.0))
    # wick-through variant: a later candle WICKS below the zone (closes back above) -> KL failure
    wb = bars + [C(100, 101, 92, 98, 10)]   # low 92 < zone low 94 (wick), close 98 back above
    wz = next(z for z in Z.mark_key_levels(wb, left=1, right=1) if z["i"] == 4)
    check("KL: wick through the level = KL failure", wz["wick_broken"] and not wz["key_level"])


def test_key_level_decay():
    # fresh -> 1.0, decays per retest, dead at >=3 touches
    check("KL: score decays with touches", Z.kl_score_from(bos=True, broken=False, touches=0) == 1.0
          and Z.kl_score_from(bos=True, broken=False, touches=1) < 1.0
          and Z.kl_score_from(bos=True, broken=False, touches=3) == 0.0)
    check("KL: mark_key_levels tags zones with score+key_level flag",
          all({"score", "key_level", "bos", "touches"} <= set(zz)
              for zz in Z.mark_key_levels([C(100,105,99,104,10)]*3, left=1, right=1)))


def test_big_candle():
    pre = [C(100, 101, 99, 100.2, 10) for _ in range(2)]
    post = [C(100, 101, 99, 100.2, 10) for _ in range(2)]
    bars = pre + [C(100, 110, 99, 109, 100)] + post           # big green at index 2 (body 9, vol 100)
    check("big: large body + high volume passes", Z.big_candle(bars, 2, lookback=5) is True)
    check("big: small body fails (vs the big one in window)", Z.big_candle(bars, 4, lookback=5) is False)
    busy = [C(100, 101, 99, 100.2, 100) for _ in range(4)]   # high-volume neighbors for contrast
    low_vol = busy + [C(100, 110, 99, 109, 10)]              # big body but LOW volume vs neighbors
    check("big: big body but low volume fails", Z.big_candle(low_vol, 4, lookback=5) is False)


def test_sr_levels_and_flip():
    small = [C(100, 101, 99, 100.2, 10) for _ in range(4)]
    # big GREEN -> support at its open
    sg = small + [C(100, 110, 99, 109, 100)]
    s = Z.sr_levels(sg, lookback=5)
    check("SR: big green -> support at open", any(x["role"] == "support" and approx(x["price"], 100) for x in s))
    # big RED -> resistance at its open
    sr_ = small + [C(109, 110, 99, 100, 100)]
    r = Z.sr_levels(sr_, lookback=5)
    check("SR: big red -> resistance at open", any(x["role"] == "resistance" and approx(x["price"], 109) for x in r))
    # polarity flip: support, then a later candle CLOSES below it -> role becomes resistance
    flip = small + [C(100, 110, 99, 109, 100), C(99, 100, 90, 95, 10)]   # closes 95 < support 100
    f = Z.sr_levels(flip, lookback=6)
    sup = next(x for x in f if x["origin"] == "support")
    check("SR: broken support flips to resistance", sup["flipped"] is True and sup["role"] == "resistance")
    # a green big-volume candle with a LONG upper wick is NOT support (rejection against the level)
    longwick = small + [C(100, 130, 99, 109, 100)]   # upper wick 130->109 = 21 of 31 range -> disqualify
    check("SR: green with long upper wick is NOT support",
          not any(x["origin"] == "support" for x in Z.sr_levels(longwick, lookback=5)))
    # a green candle with NO lower wick cannot be support (no rejection tail in its direction)
    nolowwick = small + [C(100, 112, 100, 110, 100)]   # low == open -> no lower wick
    check("SR: green with no lower wick is NOT support",
          not any(x["origin"] == "support" for x in Z.sr_levels(nolowwick, lookback=5)))


def main():
    for fn in (test_volume_fib, test_zone_geometry, test_find_demand_zone, test_value_area, test_prior_day_vas_cached,
               test_key_level_bos_and_score, test_key_level_decay, test_big_candle, test_sr_levels_and_flip):
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
