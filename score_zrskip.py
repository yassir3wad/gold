#!/usr/bin/env python3
"""Score the ZRSKIP measurement bucket — zone-rejection setups the pre-hold HARD FLOOR auto-skipped —
to find how many were genuine misses. Two block mechanisms: dead CHOP (gold case) and neg-R:R geometry
(GBP case: TP1 capped at the nearest micro-structure on tight-range FX). Splits WITH-trend vs COUNTER-trend
and reports count, MFE/MAE, TP1/SL/timeout, after-spread net. Does NOT change engine behavior.

Backtest source: /tmp/zrskip_<date>.json + /tmp/bars_<date>.json (written by replay_sim). Aggregates every
date that has BOTH files.
    python3 score_zrskip.py [--horizon 15] [--rr-min 1.2]
"""
import argparse, glob, json, os, re
from backtest_multi_day import DEFAULT_SYMBOL, load_spread_pips, simulate_trade
PIP = 0.10


def mfe_mae(side, entry, fut):
    if not fut:
        return 0.0, 0.0
    hi = max(b["high"] for b in fut); lo = min(b["low"] for b in fut)
    if side == "LONG":
        return (hi - entry) / PIP, (entry - lo) / PIP
    return (entry - lo) / PIP, (hi - entry) / PIP


def score_one(rec, bars, horizon):
    fut = [b for b in bars if b["time"] > rec["t"]][:horizon]
    o, exitp, _ = simulate_trade(rec["side"], rec["entry"], rec["sl"], rec["tp1"], fut, horizon=horizon)
    pips = (rec["entry"] - exitp) / PIP if rec["side"] == "SHORT" else (exitp - rec["entry"]) / PIP
    mfe, mae = mfe_mae(rec["side"], rec["entry"], fut)
    return {**rec, "_o": o, "_p": round(pips), "_mfe": round(mfe), "_mae": round(mae)}


def report(name, group, spread):
    n = len(group)
    if n == 0:
        print(f"  {name:24} n=  0"); return
    tp = sum(1 for s in group if s["_o"] == "TP1"); sl = sum(1 for s in group if s["_o"] == "SL")
    to = sum(1 for s in group if s["_o"] == "timeout")
    gross = sum(s["_p"] for s in group); net = gross - spread * n
    amfe = sum(s["_mfe"] for s in group) / n; amae = sum(s["_mae"] for s in group) / n
    nw = sum(1 for s in group if (s["_p"] - spread) > 0)
    print(f"  {name:24} n={n:3}  TP1={tp:2} SL={sl:2} to={to:2}  WR={nw/n*100:3.0f}%  "
          f"avgMFE=+{amfe:4.0f}p avgMAE=-{amae:4.0f}p  NET(after-spread)={net:+5d}p")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=15)
    ap.add_argument("--rr-min", type=float, default=1.2)
    ap.add_argument("--symbol", default=DEFAULT_SYMBOL)
    ap.add_argument("--spread-pips", type=float)
    a = ap.parse_args()
    spread = a.spread_pips if a.spread_pips is not None else load_spread_pips(a.symbol)

    recs = []
    for zf in sorted(glob.glob("/tmp/zrskip_*.json")):
        date = re.search(r"zrskip_(\d{4}-\d{2}-\d{2})\.json", zf).group(1)
        bf = f"/tmp/bars_{date}.json"
        if not os.path.exists(bf):
            continue
        bars = sorted(json.load(open(bf)), key=lambda b: b["time"])
        for rec in json.load(open(zf)):
            recs.append(score_one(rec, bars, a.horizon))

    if not recs:
        print("No ZRSKIP records with matching bars found in /tmp. Run replay_sim first."); return

    dates = sorted({re.search(r"zrskip_(\d{4}-\d{2}-\d{2})", f).group(1) for f in glob.glob('/tmp/zrskip_*.json')})
    print(f"=== ZRSKIP study: zone-rejections killed by the hard floor · {len(recs)} records · "
          f"{len(dates)} days · {a.horizon}-bar horizon ===")
    print(f"Cost: {spread:g}p/trade ({a.symbol.upper()}).  Q: do WITH-trend zone-rejections the floor kills have edge?\n")

    wt = [r for r in recs if r["with_trend"]]; ct = [r for r in recs if not r["with_trend"]]
    print("By direction (ALL block reasons):")
    report("with-trend", wt, spread); report("counter-trend", ct, spread)

    print("\nThe two candidate fixes, isolated (WITH-trend only):")
    chop_rr_ok = [r for r in wt if r["block"] == "chop" and (r.get("rr1") or 0) >= a.rr_min]
    report(f"chop-exempt R:R>={a.rr_min}", chop_rr_ok, spread)
    report("TP1-geometry (neg-R:R)", [r for r in wt if r["block"] in ("rr", "both")], spread)
    print(f"\nShip a fix only where its WITH-trend bucket is convincingly net-positive across the {len(dates)} days.")


if __name__ == "__main__":
    main()
