#!/usr/bin/env python3
"""Tests for va_state.py — Rules 6 & 7 of the value-area framework / gold-va-strategy: classify a prior-day
VA level (VAH/VAL/POC) against the CURRENT session's bars into Level State =
Untested / Rejected / Accepted / Flipped, using ONLY price/candle data (no footprint/delta — see
docs/gold-va-strategy.md). Pure stdlib.
    python3 test_va_state.py   (exit 0 = all pass)
"""
import sys
import va_state as V

_r = []
def check(n, c): _r.append((n, bool(c)))


def bar(o, h, l, c):
    return {"open": o, "high": h, "low": l, "close": c}


def test_untested():
    # VAH well above; price never reaches it
    bars = [bar(4450, 4455, 4445, 4452), bar(4452, 4458, 4448, 4454)]
    s = V.level_state(4500, bars, "VAH")
    check("untested: level never touched", s["state"] == "Untested")
    check("untested: touched flag false", s["evidence"]["touched"] is False)


def test_rejection_bullish_at_val():
    # VAL = support; wick below, close back above, next bar breaks rejection-candle high
    level = 4450
    bars = [
        bar(4460, 4462, 4456, 4458),   # above, approaching
        bar(4458, 4459, 4445, 4455),   # REJECTION: wick below 4450, close back above
        bar(4455, 4465, 4454, 4463),   # breaks rejection-candle high (4459) -> confirmed
    ]
    check("bullish rejection detected at VAL", V.rejection(level, bars, "VAL") is True)
    s = V.level_state(level, bars, "VAL")
    check("VAL held -> Rejected", s["state"] == "Rejected")


def test_rejection_bearish_at_vah():
    level = 4500
    bars = [
        bar(4490, 4495, 4488, 4492),   # below, approaching
        bar(4492, 4506, 4491, 4495),   # REJECTION: wick above 4500, close back below
        bar(4495, 4496, 4485, 4488),   # breaks rejection-candle low (4491) -> confirmed
    ]
    check("bearish rejection detected at VAH", V.rejection(level, bars, "VAH") is True)
    check("VAH held -> Rejected", V.level_state(level, bars, "VAH")["state"] == "Rejected")


def test_no_rejection_without_followthrough():
    # wick above + close back below, but next bar does NOT break the rejection low -> not confirmed
    level = 4500
    bars = [
        bar(4490, 4495, 4488, 4492),
        bar(4492, 4506, 4496, 4498),   # close back below, rejection low = 4496
        bar(4498, 4499, 4497, 4498),   # does not break 4496
    ]
    check("no confirmed rejection without break of rejection candle", V.rejection(level, bars, "VAH") is False)


def test_accepted_vah():
    # >=2 closes above + value built above -> Accepted (2 of the Rule-6 criteria)
    level = 4500
    bars = [
        bar(4498, 4503, 4497, 4502),   # close above
        bar(4502, 4509, 4501, 4507),   # close above
        bar(4507, 4512, 4505, 4510),   # close above
    ]
    cnt, flags = V.acceptance(level, bars, "VAH")
    check("acceptance: >=2 closes beyond", flags["closes_beyond"] is True)
    check("acceptance: value built beyond (>50%)", flags["value_beyond"] is True)
    check("acceptance: >=2 criteria", cnt >= 2)
    check("VAH accepted through -> Accepted", V.level_state(level, bars, "VAH")["state"] == "Accepted")


def test_accepted_poc_migration():
    # POC sits beyond the VAL (below it) -> POC-migration criterion fires
    level = 4450
    bars = [bar(4448, 4449, 4440, 4444), bar(4444, 4446, 4438, 4441)]  # 2 closes below
    cnt, flags = V.acceptance(level, bars, "VAL", poc=4435)
    check("acceptance: POC migrated beyond level", flags["poc_beyond"] is True)
    check("acceptance count with poc migration >=2", cnt >= 2)


def test_flipped_vah():
    # Accept above VAH, then retest from above holds (wick back to level, close stays above) -> Flipped
    level = 4500
    bars = [
        bar(4498, 4503, 4497, 4502),   # close above (accept)
        bar(4502, 4510, 4501, 4508),   # close above (accept) -> value above
        bar(4508, 4509, 4499, 4506),   # retest: wick to 4499 (<=level) but closes back above
        bar(4506, 4514, 4505, 4512),   # continues up
    ]
    s = V.level_state(level, bars, "VAH")
    check("VAH accepted + retest held -> Flipped", s["state"] == "Flipped")
    check("flip evidence: retest_held", s["evidence"]["retest_held"] is True)


def test_touched_inconclusive_weak():
    # one poke above, closes back below, no confirmed rejection, no acceptance -> weak Rejected (held side)
    level = 4500
    bars = [
        bar(4490, 4495, 4488, 4492),
        bar(4492, 4502, 4491, 4498),   # poke above, close back below
        bar(4498, 4499, 4496, 4497),   # no break, no follow-through
    ]
    s = V.level_state(level, bars, "VAH")
    check("touched-inconclusive, price held below -> Rejected (weak)", s["state"] == "Rejected")
    check("weak confidence flagged", s["evidence"]["confidence"] == "weak")


def test_thirty_minute_criterion():
    # spends > 30 min beyond (bar_minutes drives the time estimate)
    level = 4500
    bars = [bar(4500, 4505, 4499, 4503)] * 7   # 7 bars * 5 min = 35 min beyond
    cnt, flags = V.acceptance(level, bars, "VAH", bar_minutes=5)
    check("acceptance: >30 min beyond", flags["time_beyond"] is True)


def main():
    fns = [test_untested, test_rejection_bullish_at_val, test_rejection_bearish_at_vah,
           test_no_rejection_without_followthrough, test_accepted_vah, test_accepted_poc_migration,
           test_flipped_vah, test_touched_inconclusive_weak, test_thirty_minute_criterion]
    for fn in fns:
        try: fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False); print(f"  !! {fn.__name__}: {e}")
    p = sum(1 for _, ok in _r if ok); t = len(_r)
    for n, ok in _r:
        if not ok: print(f"  [FAIL] {n}")
    print(f"\n{'OK' if p == t else 'FAIL'} {p}/{t} checks passed")
    sys.exit(0 if p == t else 1)


if __name__ == "__main__":
    main()
