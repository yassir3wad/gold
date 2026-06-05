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


def test_find_demand_zone():
    # rising-then-dipping series with a clear swing low at i=5 on a GREEN, high-volume candle
    base = [C(110-i, 111-i, 109-i, 110-i, 10) for i in range(5)]          # falling into the low
    low_candle = C(104, 106, 103, 105.5, 100)                             # green, tall volume, the swing low
    rise = [C(106+i, 107+i, 105+i, 106+i, 10) for i in range(5)]          # rally away
    bars = base + [low_candle] + rise
    zones = Z.find_demand_zones(bars, left=2, right=2, lookback=12)
    check("find-demand: detects a zone at the green high-vol swing low",
          any(abs(z["lo"] - 103) < 1 and z["kind"] == "demand" for z in zones))
    # same structure but the swing-low candle is RED -> not a demand zone
    bars_red = base + [C(106, 106, 103, 104, 100)] + rise
    check("find-demand: red swing-low candle is NOT a demand zone",
          not Z.find_demand_zones(bars_red, left=2, right=2, lookback=12))


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


def main():
    for fn in (test_volume_fib, test_zone_geometry, test_find_demand_zone, test_value_area, test_prior_day_vas_cached):
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
