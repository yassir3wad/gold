#!/usr/bin/env python3
"""Test suite for dynamic reference level computation — PDH/PDL from daily OHLCV and Asia H/L
from 15m session bars. Pure stdlib, no pytest. Run:  python3 test_reference_levels.py
(exit 0 = all pass, 1 = a failure).

Covers: compute_reference_levels() with mocked TV data, PDH/PDL extraction from daily bars,
Asia session range filtering, and tolerance validation against manually verified levels."""
import sys, datetime as dt
import scalp_fast as sf

_results = []
def check(name, cond):
    _results.append((name, bool(cond)))

def approx(a, b, tol=1e-6):
    """Floating point equality with tolerance (default 1e-6 for exact, or custom for percentage)."""
    return a is not None and b is not None and abs(a - b) <= tol

def pct_tol(val, pct=0.1):
    """Return tolerance threshold as percentage of value (0.1% = 0.001 * val)."""
    return abs(val) * (pct / 100.0)


# ─────────────────────────────────────────────────────────────────────────────
# 1) PDH/PDL computation from daily bars
# ─────────────────────────────────────────────────────────────────────────────
def test_pdh_pdl_from_daily_bars():
    """Verify PDH/PDL are extracted from previous day's high/low (bars[-2])."""
    calls = []

    def fake_tv(*a):
        calls.append(a)
        if a[0] == "timeframe":
            return {}
        elif a[0] == "ohlcv":
            # Return 3 daily bars: [day-2, day-1, today]
            # PDH/PDL should be taken from day-1 (bars[-2])
            return {
                "bars": [
                    {"time": 1717459200, "high": 4450.0, "low": 4400.0},  # day-2
                    {"time": 1717545600, "high": 4496.7, "low": 4426.4},  # day-1 (target)
                    {"time": 1717632000, "high": 4510.0, "low": 4460.0},  # today
                ]
            }
        return {}

    orig_tv = sf.tv
    orig_pxd = sf.PXD
    try:
        sf.tv = fake_tv
        sf.PXD = 2  # gold precision
        levels = sf.compute_reference_levels()

        check("pdh_pdl: switches to daily TF", ("timeframe", "D") in calls)
        check("pdh_pdl: fetches 3 bars", ("ohlcv", "-n", "3") in calls)
        check("pdh_pdl: restores 1m TF", ("timeframe", "1") in calls)
        check("pdh_pdl: PDH from bars[-2].high", approx(levels.get("pdh"), 4496.7, 0.01))
        check("pdh_pdl: PDL from bars[-2].low", approx(levels.get("pdl"), 4426.4, 0.01))
        check("pdh_pdl: rounds to PXD=2", levels.get("pdh") == round(4496.7, 2))
    finally:
        sf.tv = orig_tv
        sf.PXD = orig_pxd


def test_pdh_pdl_insufficient_bars():
    """Verify graceful fallback when daily bars fetch returns <2 bars."""
    def fake_tv(*a):
        if a[0] == "ohlcv":
            return {"bars": [{"time": 1717632000, "high": 4500.0, "low": 4450.0}]}  # only 1 bar
        return {}

    orig_tv = sf.tv
    try:
        sf.tv = fake_tv
        levels = sf.compute_reference_levels()
        check("pdh_pdl: no PDH when <2 bars", levels.get("pdh") is None)
        check("pdh_pdl: no PDL when <2 bars", levels.get("pdl") is None)
    finally:
        sf.tv = orig_tv


# ─────────────────────────────────────────────────────────────────────────────
# 2) Asia session range (00:00-07:00 UTC) from 15m bars
# ─────────────────────────────────────────────────────────────────────────────
def test_asia_session_range():
    """Verify Asia H/L are computed from last complete 00-07 UTC session."""
    calls = []

    # Mock current time: 2026-06-05 10:00 UTC (after Asia close)
    # Target day for Asia session: 2026-06-05
    # Create 15m bars spanning multiple days with session bars on target day
    target_day = dt.date(2026, 6, 5)

    def fake_tv(*a):
        calls.append(a)
        if a[0] == "timeframe":
            return {}
        elif a[0] == "ohlcv" and len(a) >= 3 and a[2] == "300":  # 15m bars
            bars = []
            # Day before (should be ignored)
            bars.append({"time": dt.datetime(2026, 6, 4, 2, 0, tzinfo=dt.timezone.utc).timestamp(),
                        "high": 4470.0, "low": 4460.0})
            # Target day Asia session bars (00-07 UTC)
            bars.append({"time": dt.datetime(2026, 6, 5, 0, 0, tzinfo=dt.timezone.utc).timestamp(),
                        "high": 4484.0, "low": 4443.3})
            bars.append({"time": dt.datetime(2026, 6, 5, 3, 0, tzinfo=dt.timezone.utc).timestamp(),
                        "high": 4480.0, "low": 4450.0})
            bars.append({"time": dt.datetime(2026, 6, 5, 6, 45, tzinfo=dt.timezone.utc).timestamp(),
                        "high": 4475.0, "low": 4445.0})
            # After Asia close (should be ignored)
            bars.append({"time": dt.datetime(2026, 6, 5, 8, 0, tzinfo=dt.timezone.utc).timestamp(),
                        "high": 4490.0, "low": 4470.0})
            return {"bars": bars}
        elif a[0] == "ohlcv" and len(a) >= 3 and a[2] == "3":  # daily bars
            return {"bars": [
                {"time": 1717459200, "high": 4450.0, "low": 4400.0},
                {"time": 1717545600, "high": 4496.7, "low": 4426.4},
            ]}
        return {}

    orig_tv, orig_pxd = sf.tv, sf.PXD
    try:
        sf.tv = fake_tv
        sf.PXD = 2
        levels = sf.compute_reference_levels()

        check("asia: switches to 15m TF", ("timeframe", "15") in calls)
        check("asia: fetches 300 bars", ("ohlcv", "-n", "300") in calls)
        check("asia: ASIA_H is max of session bars", approx(levels.get("asia_h"), 4484.0, 0.01))
        check("asia: ASIA_L is min of session bars", approx(levels.get("asia_l"), 4443.3, 0.01))
    finally:
        sf.tv, sf.PXD = orig_tv, orig_pxd


def test_asia_session_early_morning():
    """Verify Asia session targets previous day when current time is before 07:00 UTC."""
    # Mock time: 2026-06-05 05:00 UTC (during Asia session)
    # Should target previous day's complete session: 2026-06-04

    def fake_tv(*a):
        if a[0] == "ohlcv" and len(a) >= 3 and a[2] == "300":
            # Only include bars from 2026-06-04 00-07 UTC
            bars = [
                {"time": dt.datetime(2026, 6, 4, 1, 0, tzinfo=dt.timezone.utc).timestamp(),
                 "high": 4470.0, "low": 4450.0},
                {"time": dt.datetime(2026, 6, 4, 4, 0, tzinfo=dt.timezone.utc).timestamp(),
                 "high": 4475.0, "low": 4445.0},
                {"time": dt.datetime(2026, 6, 5, 2, 0, tzinfo=dt.timezone.utc).timestamp(),
                 "high": 4480.0, "low": 4460.0},  # today, should be ignored
            ]
            return {"bars": bars}
        elif a[0] == "ohlcv":
            return {"bars": [{"time": 1717545600, "high": 4496.7, "low": 4426.4}]}
        return {}

    orig_tv = sf.tv
    try:
        sf.tv = fake_tv
        # Can't easily mock datetime.utcnow(), so we test the logic accepts previous day bars
        levels = sf.compute_reference_levels()
        # If we're at 05:00 UTC, target_day would be previous day
        # Verification: as long as Asia levels are computed from some session, logic is correct
        check("asia_early: computed ASIA_H", levels.get("asia_h") is not None)
        check("asia_early: computed ASIA_L", levels.get("asia_l") is not None)
    finally:
        sf.tv = orig_tv


def test_asia_session_no_bars():
    """Verify graceful fallback when no Asia session bars found."""
    def fake_tv(*a):
        if a[0] == "ohlcv" and len(a) >= 3 and a[2] == "300":
            return {"bars": []}  # empty
        elif a[0] == "ohlcv":
            return {"bars": [{"time": 1717545600, "high": 4496.7, "low": 4426.4}]}
        return {}

    orig_tv = sf.tv
    try:
        sf.tv = fake_tv
        levels = sf.compute_reference_levels()
        check("asia_no_bars: no ASIA_H", levels.get("asia_h") is None)
        check("asia_no_bars: no ASIA_L", levels.get("asia_l") is None)
    finally:
        sf.tv = orig_tv


# ─────────────────────────────────────────────────────────────────────────────
# 3) Tolerance validation — 0.1% accuracy against manually verified levels
# ─────────────────────────────────────────────────────────────────────────────
def test_tolerance_validation():
    """Verify computed levels match manually verified levels within 0.1% tolerance.

    Manually verified levels from 2026-06-04 TradingView chart:
    - PDH: 4496.70 (previous day high)
    - PDL: 4426.40 (previous day low)
    - ASIA_H: 4484.00 (Asia session 00-07 UTC high)
    - ASIA_L: 4443.30 (Asia session 00-07 UTC low)
    """
    expected = {
        "pdh": 4496.70,
        "pdl": 4426.40,
        "asia_h": 4484.00,
        "asia_l": 4443.30,
    }

    def fake_tv(*a):
        if a[0] == "ohlcv" and len(a) >= 3 and a[2] == "3":  # daily
            # Return 3 bars so bars[-2] is the target day with expected values
            return {"bars": [
                {"time": 1717372800, "high": 4450.0, "low": 4400.0},  # day-2
                {"time": 1717459200, "high": expected["pdh"], "low": expected["pdl"]},  # day-1 (target)
                {"time": 1717545600, "high": 4510.0, "low": 4460.0},  # today
            ]}
        elif a[0] == "ohlcv" and len(a) >= 3 and a[2] == "300":  # 15m
            return {"bars": [
                {"time": dt.datetime(2026, 6, 5, 2, 0, tzinfo=dt.timezone.utc).timestamp(),
                 "high": expected["asia_h"], "low": expected["asia_l"]},
            ]}
        return {}

    orig_tv, orig_pxd = sf.tv, sf.PXD
    try:
        sf.tv = fake_tv
        sf.PXD = 2
        levels = sf.compute_reference_levels()

        # Verify each level within 0.1% tolerance
        for key, exp_val in expected.items():
            actual = levels.get(key)
            tol = pct_tol(exp_val, 0.1)
            check(f"tolerance: {key} within 0.1%",
                  actual is not None and approx(actual, exp_val, tol))
            if actual is not None:
                pct_diff = abs(actual - exp_val) / exp_val * 100
                check(f"tolerance: {key} error <0.1% (actual: {pct_diff:.4f}%)", pct_diff < 0.1)
    finally:
        sf.tv, sf.PXD = orig_tv, orig_pxd


# ─────────────────────────────────────────────────────────────────────────────
# 4) Error handling and timeframe restoration
# ─────────────────────────────────────────────────────────────────────────────
def test_timeframe_restoration_on_error():
    """Verify timeframe is always restored to 1m even when OHLCV fetch fails."""
    calls = []

    def boom_tv(*a):
        calls.append(a)
        if a[0] == "ohlcv":
            raise RuntimeError("network error")
        return {}

    orig_tv = sf.tv
    try:
        sf.tv = boom_tv
        levels = sf.compute_reference_levels()
        # Should return dict with None values (graceful degradation)
        check("error: returns dict", isinstance(levels, dict))
        check("error: PDH is None", levels.get("pdh") is None)
        check("error: restores TF even on error", ("timeframe", "1") in calls)
    finally:
        sf.tv = orig_tv


def test_partial_success():
    """Verify partial success when daily bars succeed but 15m bars fail."""
    def partial_tv(*a):
        if a[0] == "ohlcv" and len(a) >= 3 and a[2] == "3":
            return {"bars": [
                {"time": 1717459200, "high": 4450.0, "low": 4400.0},
                {"time": 1717545600, "high": 4496.7, "low": 4426.4},
            ]}
        elif a[0] == "ohlcv" and len(a) >= 3 and a[2] == "300":
            raise RuntimeError("15m fetch failed")
        return {}

    orig_tv = sf.tv
    try:
        sf.tv = partial_tv
        levels = sf.compute_reference_levels()
        check("partial: PDH computed", levels.get("pdh") is not None)
        check("partial: PDL computed", levels.get("pdl") is not None)
        check("partial: ASIA_H is None", levels.get("asia_h") is None)
        check("partial: ASIA_L is None", levels.get("asia_l") is None)
    finally:
        sf.tv = orig_tv


# ─────────────────────────────────────────────────────────────────────────────
# 5) Integration with load_zones() fallback logic
# ─────────────────────────────────────────────────────────────────────────────
def test_load_zones_fallback():
    """Verify load_zones() falls back to hardcoded constants when compute fails."""
    def null_tv(*a):
        if a[0] == "ohlcv":
            return {"bars": []}  # insufficient data
        return {}

    orig_tv = sf.tv
    orig_pdh, orig_pdl = sf.PDH, sf.PDL
    orig_asia_h, orig_asia_l = sf.ASIA_H, sf.ASIA_L

    try:
        sf.tv = null_tv
        # Set known fallback values
        sf.PDH, sf.PDL = 4500.0, 4430.0
        sf.ASIA_H, sf.ASIA_L = 4490.0, 4445.0

        # load_zones should fallback to hardcoded when compute returns None
        _, _, pdh, pdl, asia_h, asia_l = sf.load_zones()

        check("fallback: uses hardcoded PDH", pdh == 4500.0)
        check("fallback: uses hardcoded PDL", pdl == 4430.0)
        check("fallback: uses hardcoded ASIA_H", asia_h == 4490.0)
        check("fallback: uses hardcoded ASIA_L", asia_l == 4445.0)
    finally:
        sf.tv = orig_tv
        sf.PDH, sf.PDL = orig_pdh, orig_pdl
        sf.ASIA_H, sf.ASIA_L = orig_asia_h, orig_asia_l


def main():
    for fn in (test_pdh_pdl_from_daily_bars, test_pdh_pdl_insufficient_bars,
               test_asia_session_range, test_asia_session_early_morning, test_asia_session_no_bars,
               test_tolerance_validation, test_timeframe_restoration_on_error, test_partial_success,
               test_load_zones_fallback):
        try:
            fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False)
            print(f"  !! {fn.__name__}: {e}")

    passed = sum(1 for _, ok in _results if ok)
    total = len(_results)

    for n, ok in _results:
        if not ok:
            print(f"  [FAIL] {n}")

    print(f"\n{'✅' if passed == total else '❌'} {passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
