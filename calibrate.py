#!/usr/bin/env python3
"""Calibrate + validate the outcome-calibrated approval model against scored backtest days.
LEAVE-ONE-OUT: for each test day, train the win-rate table on the OTHER days only, then decide
every signal on the held-out day. Compares three policies on the held-out set:
  - trade-everything (baseline)
  - current discipline (score_signals.verdict)
  - calibrated model (Model.decide at the chosen threshold)
Reports count / win% / net pips for each, plus a threshold sweep. Honest out-of-sample test.

    python3 calibrate.py 2026-06-01 2026-06-02 2026-06-04 [--threshold 0.5] [--min-support 6] [--save model.json]
"""
import sys, argparse
from boundary import load_day
import approval_model as am


def policy_stats(rows, approved_flags):
    """net pips / win% / n over the signals where approved_flags[i] is True."""
    kept = [r for r, ok in zip(rows, approved_flags) if ok]
    tp = sum(1 for r in kept if r["won"]); sl = sum(1 for r in kept if r["lost"])
    net = sum(r["pips"] for r in kept)
    wr = tp / (tp + sl) * 100 if tp + sl else 0
    return len(kept), wr, net


def loo(days, threshold, min_support, alpha):
    per_day = {d: load_day(d) for d in days}
    agg = {"all": [], "disc": [], "model": []}     # collect held-out rows under each policy
    print(f"\n=== leave-one-out validation · threshold={threshold} · min_support={min_support} ===")
    print(f"  {'test day':12} {'policy':16} {'n':>4} {'win%':>6} {'net':>8}")
    for test in days:
        train_rows = [r for d in days if d != test for r in per_day[d]]
        m = am.Model(alpha=alpha, min_support=min_support).train(train_rows)
        test_rows = per_day[test]
        flags_all = [True] * len(test_rows)
        flags_disc = [r["v"] == "APPROVE" for r in test_rows]
        flags_model = [m.decide(r, threshold)["approve"] for r in test_rows]
        for tag, fl, key in (("trade-all", flags_all, "all"), ("discipline", flags_disc, "disc"),
                             ("model", flags_model, "model")):
            n, wr, net = policy_stats(test_rows, fl)
            print(f"  {test:12} {tag:16} {n:4} {wr:5.0f}% {net:+8d}p")
            agg[key] += [r for r, ok in zip(test_rows, fl) if ok]
        print()
    print(f"  {'TOTAL (OOS)':12} {'policy':16} {'n':>4} {'win%':>6} {'net':>8}")
    for tag, key in (("trade-all", "all"), ("discipline", "disc"), ("model", "model")):
        rows = agg[key]
        tp = sum(1 for r in rows if r["won"]); sl = sum(1 for r in rows if r["lost"])
        net = sum(r["pips"] for r in rows); wr = tp / (tp + sl) * 100 if tp + sl else 0
        print(f"  {'':12} {tag:16} {len(rows):4} {wr:5.0f}% {net:+8d}p")


def sweep(days, min_support, alpha):
    per_day = {d: load_day(d) for d in days}
    print(f"\n=== threshold sweep (LOO net pips, min_support={min_support}) ===")
    print(f"  {'thr':>5} {'n':>5} {'win%':>6} {'net':>8}")
    for thr in (0.35, 0.40, 0.45, 0.50, 0.55, 0.60):
        rows_kept = []
        for test in days:
            train_rows = [r for d in days if d != test for r in per_day[d]]
            m = am.Model(alpha=alpha, min_support=min_support).train(train_rows)
            rows_kept += [r for r in per_day[test] if m.decide(r, thr)["approve"]]
        tp = sum(1 for r in rows_kept if r["won"]); sl = sum(1 for r in rows_kept if r["lost"])
        net = sum(r["pips"] for r in rows_kept); wr = tp / (tp + sl) * 100 if tp + sl else 0
        print(f"  {thr:5.2f} {len(rows_kept):5} {wr:5.0f}% {net:+8d}p")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("days", nargs="*", default=["2026-06-01", "2026-06-02", "2026-06-04"])
    ap.add_argument("--threshold", type=float, default=0.50)
    ap.add_argument("--min-support", type=int, default=6)
    ap.add_argument("--alpha", type=float, default=1.0)
    ap.add_argument("--save", help="train on ALL days and save the table here")
    a = ap.parse_args()
    days = a.days or ["2026-06-01", "2026-06-02", "2026-06-04"]
    loo(days, a.threshold, a.min_support, a.alpha)
    sweep(days, a.min_support, a.alpha)
    if a.save:
        rows = [r for d in days for r in load_day(d)]
        am.Model(alpha=a.alpha, min_support=a.min_support).train(rows).save(a.save)
        print(f"\nsaved full-data table -> {a.save} ({len(rows)} signals)")


if __name__ == "__main__":
    main()
