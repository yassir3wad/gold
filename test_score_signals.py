#!/usr/bin/env python3
"""Tests for score_signals.py pure helpers — the net-of-cost aggregate (`stats`) and the SMC
alignment bucketing (`smc_bucket_key`) used by the SMC measurement report. No chart/network.
    python3 test_score_signals.py
"""
import sys
import score_signals as S

_r = []
def check(n, c): _r.append((n, bool(c)))


def test_stats():
    # 3 trades: a +120 net win, a -150 net loss, a 0 (timeout breakeven-ish)
    group = [{"_o": "TP1", "_p": 150, "_np": 120},
             {"_o": "SL", "_p": -150, "_np": -180},
             {"_o": "timeout", "_p": 0, "_np": 0}]
    st = S.stats(group, spread_pips=30)
    check("stats: n", st["n"] == 3)
    check("stats: TP1/SL/timeout counts", st["tp"] == 1 and st["sl"] == 1 and st["to"] == 1)
    check("stats: gross sums _p", st["gross"] == 0)            # 150 - 150 + 0
    check("stats: net sums _np", st["net"] == -60)             # 120 - 180 + 0
    check("stats: cost = spread × n", st["cost"] == 90)
    check("stats: win/loss/scratch", st["nw"] == 1 and st["nl"] == 1 and st["ns"] == 1)
    check("stats: TP1-vs-SL wr", round(st["tp_wr"]) == 50)     # 1/(1+1)
    check("stats: net wr", round(st["net_wr"]) == 33)          # 1/3
    # empty group must not divide by zero
    e = S.stats([], spread_pips=30)
    check("stats: empty -> zeroed, no div0", e["n"] == 0 and e["net"] == 0 and e["tp_wr"] == 0 and e["net_wr"] == 0)


def test_smc_bucket_key():
    check("aligned: bool True", S.smc_bucket_key({"smc_aligned": True}) == "aligned")
    check("aligned: str 'True'", S.smc_bucket_key({"smc_aligned": "True"}) == "aligned")
    check("misaligned: bool False", S.smc_bucket_key({"smc_aligned": False}) == "misaligned")
    check("misaligned: str 'False'", S.smc_bucket_key({"smc_aligned": "False"}) == "misaligned")
    check("no-SMC: None", S.smc_bucket_key({"smc_aligned": None}) == "no-SMC")
    check("no-SMC: empty string", S.smc_bucket_key({"smc_aligned": ""}) == "no-SMC")
    check("no-SMC: missing key", S.smc_bucket_key({}) == "no-SMC")
    check("no-SMC: 'None' string", S.smc_bucket_key({"smc_aligned": "None"}) == "no-SMC")


def main():
    for fn in (test_stats, test_smc_bucket_key):
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
