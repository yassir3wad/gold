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

Penalties (subtract for bad contexts — the roadmap's Confluence Score Guide, docs/signal-roadmap-detailed.md;
scaled from the guide's 0–100 deductions down to this 0–10 model, worst contexts weighted heavier):
  mid_value        in the middle of value (guide −30)             → −2
  accepted_through level accepted through, not rejected (−25)     → −2
  into_opposing    fired directly into a strong opposite level (−20) → −1
  over_tested      level tested more than twice (−20)             → −1
  vwap_chop        VWAP chop / no clean directional bias (−20)    → −1
All deductions are optional (default False) and the result stays clamped to [0, 10]. Most of these are already
hard filters upstream, so folding them here lets confidence reflect near-misses that slip through.
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


def score(grade, conf=0, smc_tl=0, rsi_div=False, with_trend=None, rr=None, level_valid=False,
          mid_value=False, accepted_through=False, over_tested=False, into_opposing=False, vwap_chop=False,
          smc_aligned=None):
    """0–10 confidence. `with_trend`: True (with trend), False (counter-trend), None (neutral/flat).
    `smc_aligned`: SOFT premium/discount alignment from the stored multi-TF SMC snapshot — True (LONG in
    discount / SHORT in premium) +1, False (wrong side of the range) -1, None (at equilibrium / no range) 0.
    Soft by design: it nudges confidence, never blocks a trade. The
    `mid_value`/`accepted_through`/`over_tested`/`into_opposing`/`vwap_chop` flags are penalties for bad
    contexts (all default False, so omitting them is identical to the additive-only scoring)."""
    s = _grade_pts(grade)
    s += min(max(conf, 0), 2)
    s += min(max(smc_tl, 0), 2)
    s += 1 if rsi_div else 0
    s += 1 if with_trend is True else (-1 if with_trend is False else 0)
    s += 1 if smc_aligned is True else (-1 if smc_aligned is False else 0)
    s += 1 if (rr is not None and rr >= 2) else 0
    s += 1 if level_valid else 0
    # Penalties — worst contexts (mid-value, accepted-through) weighted heavier.
    s -= 2 if mid_value else 0
    s -= 2 if accepted_through else 0
    s -= 1 if over_tested else 0
    s -= 1 if into_opposing else 0
    s -= 1 if vwap_chop else 0
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
