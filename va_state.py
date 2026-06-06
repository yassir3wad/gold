#!/usr/bin/env python3
"""Rules 6 & 7 of the value-area framework (docs/value-area-framework.md, docs/gold-va-strategy.md):
classify a prior-day VA level (VAH/VAL/POC) against the CURRENT session's bars into a Level State —
Untested / Rejected / Accepted / Flipped — using ONLY price/candle data. We have no footprint/delta/DOM,
so acceptance is judged from closes-beyond / value-beyond / time-beyond / POC-migration, and rejection
from the wick-back + close-back + break-of-rejection-candle pattern.

A level is "beyond" relative to VALUE: above VAH or below VAL (value-relative, independent of how price
approached). POC is a magnet, not a boundary, so for POC "beyond" is taken relative to the approach side.

    cnt, flags = acceptance(level, bars, kind, poc=None, bar_minutes=5)   # Rule 6 — invalidation
    rejected   = rejection(level, bars, kind)                            # Rule 7 — valid hold
    state      = level_state(level, bars, kind, poc=None, bar_minutes=5) # combined Level State

bars: chronological list of {"open","high","low","close"} (current session). Pure (testable).
"""

# fraction of the session beyond a level that counts as "value built there"
_VALUE_FRAC = 0.50
# minutes beyond a level that counts as acceptance (gold-va-strategy: >30 min)
_TIME_BEYOND_MIN = 30


def _origin_above(level, bars):
    """Which side did price approach from? Use the first bar's close vs the level."""
    return bool(bars) and bars[0]["close"] >= level


def _is_beyond(kind, close, level, origin_above):
    """Is a close 'beyond' the level (i.e. on the discovery side)?
    VAH beyond = above; VAL beyond = below; POC beyond = opposite the approach side."""
    if kind == "VAH":
        return close > level
    if kind == "VAL":
        return close < level
    # POC: beyond = away from where price came in
    return close < level if origin_above else close > level


def _touched(level, bars):
    return any(b["low"] <= level <= b["high"] for b in bars)


def acceptance(level, bars, kind, poc=None, bar_minutes=5):
    """Rule 6 — count how many invalidation criteria fire. Returns (count, flags).
    Criteria (price-derivable subset):
      closes_beyond  — >=2 candle closes beyond the level
      retest_beyond  — after a beyond-close, a later bar wicks back to the level but closes beyond again
      value_beyond   — >50% of bars close beyond (new value developing on the far side)
      poc_beyond     — the prior-day POC sits beyond the level (POC migrated through)
      time_beyond    — price spends >30 min beyond (bars-beyond * bar_minutes)
    A level is INVALID ("accepted") when >=2 of these hold."""
    oa = _origin_above(level, bars)
    beyond = [_is_beyond(kind, b["close"], level, oa) for b in bars]
    n_beyond = sum(beyond)

    closes_beyond = n_beyond >= 2
    value_beyond = bool(bars) and (n_beyond / len(bars)) > _VALUE_FRAC
    time_beyond = (n_beyond * bar_minutes) > _TIME_BEYOND_MIN
    poc_beyond = poc is not None and _is_beyond(kind, poc, level, oa)

    # retest-beyond: once beyond, price comes back to touch the level then closes beyond again
    retest_beyond = False
    seen_beyond = False
    for b, isb in zip(bars, beyond):
        if seen_beyond and b["low"] <= level <= b["high"] and isb:
            retest_beyond = True
            break
        if isb:
            seen_beyond = True

    flags = {"closes_beyond": closes_beyond, "retest_beyond": retest_beyond,
             "value_beyond": value_beyond, "poc_beyond": poc_beyond, "time_beyond": time_beyond}
    return sum(flags.values()), flags


def rejection(level, bars, kind):
    """Rule 7 — confirmed rejection (the level HELD, so it's a valid S/R).
    Bullish (level defended as support — VAL, or POC approached from above): a candle wicks BELOW the level
    and closes back ABOVE it, and the NEXT candle breaks that rejection candle's HIGH.
    Bearish (level defended as resistance — VAH, or POC approached from below): wick ABOVE, close back BELOW,
    next candle breaks the rejection candle's LOW. Returns True/False."""
    oa = _origin_above(level, bars)
    if kind == "VAL":
        bull = True
    elif kind == "VAH":
        bull = False
    else:  # POC — defended from whichever side price approached
        bull = oa
    for i in range(len(bars) - 1):
        b, nxt = bars[i], bars[i + 1]
        if bull:
            if b["low"] < level and b["close"] > level and nxt["high"] > b["high"]:
                return True
        else:
            if b["high"] > level and b["close"] < level and nxt["low"] < b["low"]:
                return True
    return False


def level_state(level, bars, kind, poc=None, bar_minutes=5):
    """Combined Level State. Returns {state, accepted_count, evidence}.
      Untested — price never reached the level.
      Accepted — >=2 acceptance criteria (Rule 6): invalid, don't trade first touch.
      Flipped  — accepted AND a retest from the far side held (level now S/R from the other side).
      Rejected — the level held (confirmed rejection), or (weak) price is touched but inconclusive and
                 currently sits on the origin side.
    When neither acceptance nor a confirmed rejection is clear but the level was touched, we fall back to
    current side (last close beyond -> Accepted, else Rejected) and mark confidence='weak'."""
    if not bars:
        return {"state": "Untested", "accepted_count": 0,
                "evidence": {"touched": False, "confidence": "n/a"}}
    oa = _origin_above(level, bars)
    touched = _touched(level, bars)
    cnt, flags = acceptance(level, bars, kind, poc=poc, bar_minutes=bar_minutes)
    rejected = rejection(level, bars, kind)
    accepted = cnt >= 2
    last_beyond = _is_beyond(kind, bars[-1]["close"], level, oa)

    if not touched and not last_beyond:
        state, conf = "Untested", "n/a"
    elif accepted and flags["retest_beyond"]:
        state, conf = "Flipped", "strong"
    elif accepted:
        state, conf = "Accepted", "strong"
    elif rejected:
        state, conf = "Rejected", "strong"
    else:
        # touched but inconclusive — lean on where price currently sits
        state, conf = ("Accepted", "weak") if last_beyond else ("Rejected", "weak")

    ev = {"touched": touched, "confidence": conf, "rejected": rejected,
          "retest_held": flags["retest_beyond"], "last_close_beyond": last_beyond, **flags}
    return {"state": state, "accepted_count": cnt, "evidence": ev}
