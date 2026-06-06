#!/usr/bin/env python3
"""VWAP value-area rejection entry (docs/gold-vwap-strategy.md) — entry strategy #13, flag `va_reject`.

The VWAP-bias setups, as a first-class trigger (not just AI context):
  LONG  — price above/reclaiming VWAP, at a VALID prior VAL/POC (held = bullish rejection) or a FLIPPED VAH
          (now support), with R:R >= 1:2 to the nearest VWAP/POC target above. Stop below the rejection wick.
  SHORT — mirror: below VWAP, at a VALID prior VAH/POC (bearish rejection) or a FLIPPED VAL (now resistance).

Validity (held / flipped vs accepted) and the rejection pattern come from va_state (Rules 6/7). "At the
level" is implied by the rejection wick crossing it, so there's no separate proximity gate. Pure (testable);
returns engine setup tuples (side, why, entry, stop).
"""
import va_state


def _nearest_beyond(entry, levels, above):
    """The closest level strictly above (above=True) / below the entry, or None."""
    cands = [l for l in levels if l is not None and (l > entry if above else l < entry)]
    if not cands:
        return None
    return min(cands, key=lambda l: abs(l - entry))


def detect_va_reject(price, vw, va, bars, pip=0.1, bar_minutes=1, rr_min=2.0, buf_p=0.5):
    """Return [(side, why, entry, stop)] for any valid VWAP value-area rejection, else []. `va` =
    {'vah','val','poc'} prior-day levels; `bars` = recent OHLC dicts (current session); `vw` = session VWAP."""
    if not bars or vw is None:
        return []
    vah, val, poc = va.get("vah"), va.get("val"), va.get("poc")
    entry = price
    lo2 = min(b["low"] for b in bars[-2:])
    hi2 = max(b["high"] for b in bars[-2:])
    out = []

    def rr_ok(target, stop):
        risk = abs(entry - stop)
        return target is not None and risk > 0 and (abs(target - entry) / risk) >= rr_min

    # ---- LONG: above/reclaiming VWAP, level held as support (or VAH flipped up) ----
    if price >= vw:
        long_lvls = []
        for lvl, kind in ((val, "VAL"), (poc, "POC")):
            if lvl is not None and va_state.rejection(lvl, bars, kind) \
                    and va_state.level_state(lvl, bars, kind, poc=poc, bar_minutes=bar_minutes)["state"] != "Accepted":
                long_lvls.append((lvl, kind))
        if vah is not None and va_state.level_state(vah, bars, "VAH", poc=poc, bar_minutes=bar_minutes)["state"] == "Flipped":
            long_lvls.append((vah, "flippedVAH"))
        if long_lvls:
            lvl, kind = min(long_lvls, key=lambda lk: abs(lk[0] - entry))  # the level price is interacting with
            stop = round(lo2 - buf_p * pip, 2)
            target = _nearest_beyond(entry, [vw, poc, vah], above=True)
            if stop < entry and rr_ok(target, stop):
                out.append(("LONG", f"prev {kind} rejection (VA/VWAP)", entry, stop))

    # ---- SHORT: below/rejecting VWAP, level held as resistance (or VAL flipped down) ----
    if price <= vw:
        short_lvls = []
        for lvl, kind in ((vah, "VAH"), (poc, "POC")):
            if lvl is not None and va_state.rejection(lvl, bars, kind) \
                    and va_state.level_state(lvl, bars, kind, poc=poc, bar_minutes=bar_minutes)["state"] != "Accepted":
                short_lvls.append((lvl, kind))
        if val is not None and va_state.level_state(val, bars, "VAL", poc=poc, bar_minutes=bar_minutes)["state"] == "Flipped":
            short_lvls.append((val, "flippedVAL"))
        if short_lvls:
            lvl, kind = min(short_lvls, key=lambda lk: abs(lk[0] - entry))
            stop = round(hi2 + buf_p * pip, 2)
            target = _nearest_beyond(entry, [vw, poc, val], above=False)
            if stop > entry and rr_ok(target, stop):
                out.append(("SHORT", f"prev {kind} rejection (VA/VWAP)", entry, stop))

    return out
