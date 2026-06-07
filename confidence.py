#!/usr/bin/env python3
"""Confidence scoring — aggregate EVERY confluence axis into one 0–10 score that survives past the A+ grade
ceiling, so a 5-factor monster reads stronger than a bare A+ (the letter grade can't show that). Optionally
maps to a position-size multiplier (conviction-based sizing). Pure (testable).

Axes (max 10 after clamp):
  grade        A+ → 3 · A → 2 · B → 1 · else 0
  conf         level-map stack at price (VWAP/VAL/EMA/round/PDH/…), capped at 2
  smc_tl       SMC order-block/structure + Auto-Trendline confluence score, capped at 2
  rsi_div      RSI divergence at the level → +1
  with_trend   with the 30m trend → +1 · counter-trend → −1 · neutral → 0
  rr           R:R ≥ 2 → +1
  level_valid  entry at a VALID prior-VA level (Rejected/Flipped, not Accepted) → +1
"""


def _grade_pts(grade):
    g = (grade or "").strip()
    if g.startswith("A+"):
        return 3
    if g.startswith("A"):
        return 2
    if g.startswith("B"):
        return 1
    return 0


def score(grade, conf=0, smc_tl=0, rsi_div=False, with_trend=None, rr=None, level_valid=False):
    """0–10 confidence. `with_trend`: True (with trend), False (counter-trend), None (neutral/flat)."""
    s = _grade_pts(grade)
    s += min(max(conf, 0), 2)
    s += min(max(smc_tl, 0), 2)
    s += 1 if rsi_div else 0
    s += 1 if with_trend is True else (-1 if with_trend is False else 0)
    s += 1 if (rr is not None and rr >= 2) else 0
    s += 1 if level_valid else 0
    return max(0, min(10, s))


def size_multiplier(conf_score, lo=0.75, hi=1.5, mid=5.0):
    """Map a 0–10 confidence to a position-size multiplier: `mid` → 1.0×, 10 → `hi`, 0 → `lo` (piecewise
    linear, clamped). Used only when confidence-sizing is enabled; otherwise sizing stays fixed-risk."""
    c = max(0.0, min(10.0, conf_score))
    if c >= mid:
        return round(1.0 + (hi - 1.0) * (c - mid) / (10.0 - mid), 3)
    return round(lo + (1.0 - lo) * c / mid, 3)


def label(conf_score):
    """Human tag for the readout/alert."""
    c = conf_score
    return "very-high" if c >= 8 else "high" if c >= 6 else "medium" if c >= 4 else "low"
