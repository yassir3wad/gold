#!/usr/bin/env python3
"""Tests for approval_model — the outcome-calibrated approval layer.
Pure stdlib. Pins featurization, the smoothed win-rate table, hierarchical backoff,
the decision rule (off-session hard veto + calibrated threshold), and JSON persistence.
    python3 test_approval_model.py   (exit 0 = all pass)
"""
import sys, os, json, tempfile, unittest
import approval_model as am

_results = []
def check(name, cond): _results.append((name, bool(cond)))
def approx(a, b, tol=1e-6): return a is not None and abs(a - b) <= tol

def row(why="CRT sweep+reclaim", side="LONG", regime="UP", rsi=50.0, session="ON", won=True):
    return {"why": why, "side": side, "regime": regime, "rsi": rsi, "session": session, "won": won}


def test_featurize():
    f = am.featurize(row(why="CRT sweep+reclaim", side="LONG", regime="UP", rsi=62.0, session="ON"))
    check("featurize: setup family = first token", f["family"] == "CRT")
    check("featurize: rsi 55-70 bucket", f["rsi"] == "55-70")
    check("featurize: LONG+UP = with-trend", f["align"] == "with")
    check("featurize: session passthrough", f["session"] == "ON")
    check("featurize: SHORT+UP = counter", am.featurize(row(side="SHORT", regime="UP"))["align"] == "counter")
    check("featurize: SHORT+DOWN = with", am.featurize(row(side="SHORT", regime="DOWN"))["align"] == "with")
    check("featurize: flat regime = flat", am.featurize(row(regime="flat"))["align"] == "flat")
    # rsi bucket boundaries
    check("featurize: rsi<30", am.featurize(row(rsi=29.9))["rsi"] == "<30")
    check("featurize: rsi 30-45", am.featurize(row(rsi=30.0))["rsi"] == "30-45")
    check("featurize: rsi 45-55", am.featurize(row(rsi=45.0))["rsi"] == "45-55")
    check("featurize: rsi>70", am.featurize(row(rsi=70.0))["rsi"] == ">70")
    # string rsi from the readout must be tolerated
    check("featurize: rsi as string", am.featurize(row(rsi="62.0"))["rsi"] == "55-70")


def test_score_laplace():
    # one fully-populated cell: 3 wins, 1 loss; Laplace alpha=1 -> (3+1)/(4+2) = 0.6667
    rows = [row(won=True)] * 3 + [row(won=False)]
    m = am.Model(alpha=1.0, min_support=4)
    m.train(rows)
    s = m.score(row())
    check("score: laplace on populated cell", approx(s["score"], 4 / 6))
    check("score: reports the tier used (full cell)", s["tier"] == "cell")
    check("score: reports support n", s["n"] == 4)


def test_backoff_to_family_then_global():
    # train family 'CRT' rich (mostly wins) but the SPECIFIC cell (rsi<30) unseen ->
    # an rsi<30 CRT query must back off to the CRT family marginal, not invent data.
    rows = [row(rsi=60.0, won=True)] * 8 + [row(rsi=60.0, won=False)] * 2   # CRT family: 8W/2L
    m = am.Model(alpha=1.0, min_support=5)
    m.train(rows)
    q = row(rsi=20.0)                       # CRT but rsi<30 -> cell unseen
    s = m.score(q)
    check("backoff: thin cell falls back to family", s["tier"] == "family")
    check("backoff: family rate ~ (8+1)/(10+2)", approx(s["score"], 9 / 12))
    # totally unseen family -> global prior
    s2 = m.score(row(why="moon-phase signal"))
    check("backoff: unknown family -> global tier", s2["tier"] == "global")
    check("backoff: global ~ overall win rate", 0.0 <= s2["score"] <= 1.0)


def test_decide_offsession_hard_veto():
    rows = [row(won=True)] * 20    # everything wins -> high score
    m = am.Model()
    m.train(rows)
    d = m.decide(row(session="off"))
    check("decide: off-session is a hard REJECT regardless of score", d["approve"] is False)
    check("decide: off-session reason given", any("off-session" in r for r in d["reasons"]))
    d2 = m.decide(row(session="ON"), threshold=0.5)
    check("decide: strong ON cell approves", d2["approve"] is True)


def test_decide_threshold():
    # momentum: mostly losers; CRT: mostly winners. Threshold should split them.
    rows = ([row(why="momentum impulse", won=False)] * 8 + [row(why="momentum impulse", won=True)] * 2 +
            [row(why="CRT sweep+reclaim", won=True)] * 8 + [row(why="CRT sweep+reclaim", won=False)] * 2)
    m = am.Model(alpha=1.0, min_support=5)
    m.train(rows)
    check("decide: momentum rejected at 0.5", m.decide(row(why="momentum impulse"), threshold=0.5)["approve"] is False)
    check("decide: CRT approved at 0.5", m.decide(row(why="CRT sweep+reclaim"), threshold=0.5)["approve"] is True)
    check("decide: score in reasons", "score" in m.decide(row())["reasons"][0] or any("score" in r for r in m.decide(row())["reasons"]))


def test_persistence_roundtrip():
    rows = [row(won=True)] * 6 + [row(won=False)] * 4
    m = am.Model(alpha=1.0, min_support=3)
    m.train(rows)
    before = m.score(row())["score"]
    fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd)
    try:
        m.save(path)
        m2 = am.Model.load(path)
        after = m2.score(row())["score"]
        check("persist: score identical after save/load", approx(before, after))
        check("persist: file is valid json", isinstance(json.load(open(path)), dict))
    finally:
        os.remove(path)


def test_day_efficiency():
    # straight-line uptrend over the morning window -> displacement ≈ range -> ~1.0 (directional)
    B = lambda t, c: {"time": t, "high": c + 0.5, "low": c - 0.5, "close": float(c)}
    base = 1_000_000  # 1970-ish, hour 0 UTC; window default covers all
    trend = [B(base + i * 60, 100 + i) for i in range(60)]
    dr = am.day_efficiency(trend, start_hour=0, end_hour=24)
    check("day_eff: straight trend -> disp/range near 1", dr is not None and dr > 0.9)
    # round-trip: up then back to start -> displacement ≈ 0 (choppy)
    chop = [B(base + i * 60, 100 + i) for i in range(30)] + [B(base + (30 + i) * 60, 130 - i) for i in range(30)]
    drc = am.day_efficiency(chop, start_hour=0, end_hour=24)
    check("day_eff: round-trip -> disp/range near 0", drc is not None and drc < 0.15)
    check("day_eff: too few bars -> None", am.day_efficiency([B(base, 100)], start_hour=0, end_hour=24) is None)


def test_featurize_dctx():
    check("dctx: directional when day_dr high", am.featurize(row() | {"day_dr": 0.7})["dctx"] == "directional")
    check("dctx: choppy when day_dr low", am.featurize(row() | {"day_dr": 0.2})["dctx"] == "choppy")
    check("dctx: unknown when absent", am.featurize(row())["dctx"] == "unknown")
    # adding dctx must not break grouping when it's constant across a cell
    rows = [row(won=True)] * 3 + [row(won=False)]
    m = am.Model(alpha=1.0, min_support=4).train(rows)
    check("dctx: constant dctx keeps one cell (n=4)", m.score(row())["n"] == 4)


def test_recovers_known_boundary():
    # the empirical truth from 3 backtest days: momentum loses, CRT/trendline win.
    # the model must rank CRT strictly above momentum after training on that shape.
    rows = ([row(why="momentum impulse", won=(i < 3)) for i in range(10)] +     # 3/10
            [row(why="CRT sweep+reclaim", won=(i < 7)) for i in range(10)])     # 7/10
    m = am.Model(alpha=1.0, min_support=5)
    m.train(rows)
    check("boundary: CRT scores strictly above momentum",
          m.score(row(why="CRT sweep+reclaim"))["score"] > m.score(row(why="momentum impulse"))["score"])


def main():
    for fn in (test_featurize, test_score_laplace, test_backoff_to_family_then_global,
               test_decide_offsession_hard_veto, test_decide_threshold,
               test_persistence_roundtrip, test_day_efficiency, test_featurize_dctx,
               test_recovers_known_boundary):
        try: fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False); print(f"  !! {fn.__name__}: {e}")
    passed = sum(1 for _, ok in _results if ok); total = len(_results)
    for n, ok in _results:
        if not ok: print(f"  [FAIL] {n}")
    print(f"\n{'✅' if passed == total else '❌'} {passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


class ApprovalModelUnitTests(unittest.TestCase):
    def _run_case(self, fn):
        global _results
        _results = []
        fn()
        failed = [name for name, ok in _results if not ok]
        self.assertEqual(failed, [])

    def test_featurize_case(self): self._run_case(test_featurize)
    def test_score_laplace_case(self): self._run_case(test_score_laplace)
    def test_backoff_to_family_then_global_case(self): self._run_case(test_backoff_to_family_then_global)
    def test_decide_offsession_hard_veto_case(self): self._run_case(test_decide_offsession_hard_veto)
    def test_decide_threshold_case(self): self._run_case(test_decide_threshold)
    def test_persistence_roundtrip_case(self): self._run_case(test_persistence_roundtrip)
    def test_day_efficiency_case(self): self._run_case(test_day_efficiency)
    def test_featurize_dctx_case(self): self._run_case(test_featurize_dctx)
    def test_recovers_known_boundary_case(self): self._run_case(test_recovers_known_boundary)


if __name__ == "__main__":
    main()
