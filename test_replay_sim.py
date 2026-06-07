#!/usr/bin/env python3
"""Tests for replay_sim.parse_signal — scrapes a scanner stdout block into a signal dict, including the
machine-parseable 'SMC: zone=… aligned=… age=…' line used for the SMC bucket report. No chart/network.
    python3 test_replay_sim.py
"""
import sys
import replay_sim as R

_r = []
def check(n, c): _r.append((n, bool(c)))

_BASE = (
    ">> FAST SIGNAL: LONG [A+]  confidence 8/10 (high) [zone-bounce] | +3 HTF (60m OB demand) | SMC discount ✓aligned\n"
    "   SMC: zone={zone} aligned={aligned} age={age}\n"
    "   Entry 4327.7 | SL 4310.0 (18p · 0.10 lot ≈ $20) | TP1 4345.0 (+17p) | TP2 4360.0 (+32p)\n"
    "RSI=44  regime=UP  15m-ER=0.61  session=ON  nextR=4345.0\n"
)


def test_parse_core_fields():
    s = R.parse_signal(_BASE.format(zone="discount", aligned="True", age="0.3"))
    check("parse: side", s["side"] == "LONG")
    check("parse: grade", s["grade"] == "A+")
    check("parse: why", s["why"] == "zone-bounce")
    check("parse: entry/sl/tp1", s["entry"] == 4327.7 and s["sl"] == 4310.0 and s["tp1"] == 4345.0)
    check("parse: regime", s["regime"] == "UP")


def test_parse_smc_aligned():
    s = R.parse_signal(_BASE.format(zone="discount", aligned="True", age="0.3"))
    check("smc: zone=discount", s["smc_zone"] == "discount")
    check("smc: aligned=True", s["smc_aligned"] == "True")
    check("smc: age=0.3", s["smc_age"] == "0.3")


def test_parse_smc_misaligned():
    s = R.parse_signal(_BASE.format(zone="premium", aligned="False", age="1.2"))
    check("smc: zone=premium", s["smc_zone"] == "premium")
    check("smc: aligned=False", s["smc_aligned"] == "False")


def test_parse_smc_none():
    # equilibrium / no range / no snapshot -> aligned=None, age=None : must normalise to empty strings (no-SMC bucket)
    s = R.parse_signal(_BASE.format(zone="None", aligned="None", age="None"))
    check("smc: zone None -> empty", s["smc_zone"] == "")
    check("smc: aligned None -> empty", s["smc_aligned"] == "")
    check("smc: age None -> empty", s["smc_age"] == "")


def test_parse_no_smc_line():
    # a signal printed without the SMC line at all (e.g. smc_mtf off) -> empty SMC fields, no crash
    txt = ("\n".join(l for l in _BASE.format(zone="x", aligned="x", age="x").splitlines()
                      if not l.strip().startswith("SMC:")))
    s = R.parse_signal(txt)
    check("no SMC line: fields empty", s["smc_zone"] == "" and s["smc_aligned"] == "" and s["smc_age"] == "")
    check("no SMC line: core still parsed", s["side"] == "LONG" and s["entry"] == 4327.7)


def main():
    for fn in (test_parse_core_fields, test_parse_smc_aligned, test_parse_smc_misaligned,
               test_parse_smc_none, test_parse_no_smc_line):
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
