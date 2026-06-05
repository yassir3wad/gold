#!/usr/bin/env python3
"""Empirical decision-boundary analysis across scored backtest days.
For every surfaced signal: attach its real outcome (TP1 vs SL first within the horizon), then
report win-rate + net pips sliced by each feature — and crucially, the confusion matrix of the
CURRENT discipline (score_signals.verdict) vs the actual outcome. The cells that matter:
  - REJECT but WON  -> the anti-predictive leak we're trying to plug (left money on the table)
  - APPROVE but LOST -> false positives the discipline should have caught
This is the evidence base for the outcome-calibrated approval model.

    python3 boundary.py 2026-06-01 2026-06-02 2026-06-04
"""
import sys, json, datetime as dt
from collections import defaultdict
from backtest_multi_day import simulate_trade
from score_signals import verdict
import approval_model as am

PIP = 0.10
HORIZON = 15

def fnum(x, d=0.0):
    try: return float(x)
    except (TypeError, ValueError): return d

def load_day(date):
    sigs = json.load(open(f"/tmp/replay_sim_{date}.json"))
    bars = sorted(json.load(open(f"/tmp/bars_{date}.json")), key=lambda b: b["time"])
    day_dr = am.day_efficiency(bars, 6, 9)   # morning directional efficiency -> day-type context
    rows = []
    for s in sigs:
        fut = [b for b in bars if b["time"] > s["t"]][:HORIZON]
        o, exitp, _ = simulate_trade(s["side"], s["entry"], s["sl"], s["tp1"], fut, horizon=HORIZON)
        pips = (s["entry"] - exitp) / PIP if s["side"] == "SHORT" else (exitp - s["entry"]) / PIP
        rsi, er = fnum(s.get("rsi")), fnum(s.get("er"))
        reg = s.get("regime", "?")
        counter = (s["side"] == "LONG" and reg == "DOWN") or (s["side"] == "SHORT" and reg == "UP")
        rows.append({
            "date": date, "side": s["side"], "regime": reg, "why": s.get("why", "?"),
            "rsi": rsi, "er": er, "session": s.get("session", "?"),
            "counter": counter, "outcome": o, "pips": round(pips),
            "v": verdict(s), "won": o == "TP1", "lost": o == "SL", "day_dr": day_dr,
        })
    return rows

def wr(rows):
    tp = sum(1 for r in rows if r["won"]); sl = sum(1 for r in rows if r["lost"])
    net = sum(r["pips"] for r in rows)
    return tp, sl, (tp / (tp + sl) * 100 if tp + sl else 0), net

def slice_report(title, rows, keyfn):
    print(f"\n=== {title} ===")
    groups = defaultdict(list)
    for r in rows: groups[keyfn(r)].append(r)
    print(f"  {'value':22} {'n':>4} {'TP1':>4} {'SL':>4} {'win%':>6} {'net':>7}")
    for k in sorted(groups, key=lambda k: -wr(groups[k])[3]):
        tp, sl, w, net = wr(groups[k])
        print(f"  {str(k):22} {len(groups[k]):4} {tp:4} {sl:4} {w:5.0f}% {net:+7d}p")

def main():
    dates = sys.argv[1:] or ["2026-06-01", "2026-06-02", "2026-06-04"]
    rows = []
    for d in dates:
        try: rows += load_day(d)
        except FileNotFoundError: print(f"  (skip {d}: no data)")
    decided = [r for r in rows if r["outcome"] in ("TP1", "SL")]   # ignore timeouts for win-rate clarity
    print(f"\n{'#'*70}\n# boundary analysis · {len(dates)} days · {len(rows)} signals "
          f"({len(decided)} resolved TP1/SL, {len(rows)-len(decided)} timeout)\n{'#'*70}")

    fam = lambda r: r["why"].split()[0][:18]
    rsib = lambda r: ("rsi<30" if r["rsi"] < 30 else "rsi 30-45" if r["rsi"] < 45 else
                      "rsi 45-55" if r["rsi"] < 55 else "rsi 55-70" if r["rsi"] < 70 else "rsi>70")
    erb = lambda r: ("er<0.2" if r["er"] < 0.2 else "er 0.2-0.35" if r["er"] < 0.35 else
                     "er 0.35-0.5" if r["er"] < 0.5 else "er>0.5")
    dirn = lambda r: "counter-trend" if r["counter"] else "with-trend"

    slice_report("by day", decided, lambda r: r["date"])
    slice_report("by direction vs 30m regime", decided, dirn)
    slice_report("by setup family", decided, fam)
    slice_report("by RSI bucket", decided, rsib)
    slice_report("by 15m-ER bucket", decided, erb)
    slice_report("by session", decided, lambda r: r["session"])
    slice_report("counter-trend × RSI (the dip-buy cells)", [r for r in decided if r["counter"]], rsib)

    # the key confusion matrix: current discipline vs reality
    print(f"\n=== current discipline (verdict) vs actual outcome ===")
    cm = {("APPROVE", "won"): [], ("APPROVE", "lost"): [], ("REJECT", "won"): [], ("REJECT", "lost"): []}
    for r in decided:
        cm[(r["v"], "won" if r["won"] else "lost")].append(r)
    for v in ("APPROVE", "REJECT"):
        w, l = len(cm[(v, "won")]), len(cm[(v, "lost")])
        netw, netl = sum(x["pips"] for x in cm[(v, "won")]), sum(x["pips"] for x in cm[(v, "lost")])
        print(f"  {v:8}  won={w:3} ({netw:+5d}p)   lost={l:3} ({netl:+5d}p)   "
              f"win%={w/(w+l)*100 if w+l else 0:3.0f}")
    leak = cm[("REJECT", "won")]
    print(f"\n=== ANTI-PREDICTIVE LEAK: rejected but WON  (n={len(leak)}, "
          f"{sum(r['pips'] for r in leak):+d}p left on table) ===")
    for r in sorted(leak, key=lambda r: -r["pips"])[:20]:
        print(f"  {r['date']} {r['side']:5} {r['why'][:22]:22} rsi={r['rsi']:5.1f} er={r['er']:.2f} "
              f"{r['regime']:4} {'CTR' if r['counter'] else 'with':4} -> +{r['pips']}p")
    fp = cm[("APPROVE", "lost")]
    print(f"\n=== FALSE POSITIVES: approved but LOST  (n={len(fp)}, "
          f"{sum(r['pips'] for r in fp):+d}p) ===")
    for r in sorted(fp, key=lambda r: r["pips"])[:10]:
        print(f"  {r['date']} {r['side']:5} {r['why'][:22]:22} rsi={r['rsi']:5.1f} er={r['er']:.2f} "
              f"{r['regime']:4} -> {r['pips']}p")

if __name__ == "__main__":
    main()
