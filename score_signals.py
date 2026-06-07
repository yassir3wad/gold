#!/usr/bin/env python3
"""Score replay-sim signals against the day's REAL bars: did TP1 or SL hit first (within the horizon)?
Splits by the AI verdict (approve/reject) and reports TP1/SL/timeout counts plus gross/cost/NET pips.
    python3 score_signals.py --date 2026-06-04 [--horizon 15]
"""
import argparse, json, datetime as dt
from collections import Counter
from backtest_multi_day import DEFAULT_SYMBOL, load_spread_pips, simulate_trade
PIP = 0.10
REV = ("CRT", "zone-bounce", "VWAP", "liquidity-sweep", "break-and-retest", "reclaim", "Asian-H liq")

def verdict(s, er_min=0.5):
    side, reg, why, on = s["side"], s["regime"], s["why"], (s["session"] == "ON")
    er = float(s["er"]) if s["er"] else 0.0
    rsi = float(s["rsi"]) if s["rsi"] else 50.0
    counter = (side == "LONG" and reg == "DOWN") or (side == "SHORT" and reg == "UP")
    R = []
    if not on: R.append("off-session")
    if er < er_min: R.append(f"ER<{er_min:.2f}")
    if counter: R.append("counter-trend")
    if side == "LONG" and rsi > 72: R.append("RSI-buy-top")
    if side == "SHORT" and rsi < 28: R.append("RSI-sell-bottom")
    return ("APPROVE" if not R else "REJECT")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True); ap.add_argument("--horizon", type=int, default=15)
    ap.add_argument("--er-min", type=float, default=0.5)
    ap.add_argument("--symbol", default=DEFAULT_SYMBOL, help="Symbol used for cost assumptions (default: XAUUSD)")
    ap.add_argument("--spread-pips", type=float, help="Override round-trip spread/cost in pips")
    a = ap.parse_args()
    spread_pips = a.spread_pips if a.spread_pips is not None else load_spread_pips(a.symbol)
    sigs = json.load(open(f"/tmp/replay_sim_{a.date}.json"))
    bars = sorted(json.load(open(f"/tmp/bars_{a.date}.json")), key=lambda b: b["time"])

    def outcome(s):
        fut = [b for b in bars if b["time"] > s["t"]][:a.horizon]
        o, exitp, _ = simulate_trade(s["side"], s["entry"], s["sl"], s["tp1"], fut, horizon=a.horizon)
        pips = (s["entry"] - exitp) / PIP if s["side"] == "SHORT" else (exitp - s["entry"]) / PIP
        return o, round(pips)

    buckets = {"APPROVE": [], "REJECT": []}
    for s in sigs:
        s["_v"] = verdict(s, a.er_min); s["_o"], s["_p"] = outcome(s)
        s["_np"] = round(s["_p"] - spread_pips)
        buckets[s["_v"]].append(s)

    def report(name, group):
        c = Counter(s["_o"] for s in group)
        gross = sum(s["_p"] for s in group)
        cost = spread_pips * len(group)
        net = sum(s["_np"] for s in group)
        tp, sl, to = c["TP1"], c["SL"], c["timeout"]
        wr = tp / (tp + sl) * 100 if (tp + sl) else 0
        print(f"  {name:9} n={len(group):3}  TP1={tp:3}  SL={sl:3}  timeout={to:3}  "
              f"TP1-vs-SL={wr:3.0f}%  gross={gross:+5d}p  cost=-{cost:4.0f}p  NET={net:+5d}p")

    print(f"=== outcomes, {a.date}, {a.horizon}-bar horizon (TP1 or SL first) ===")
    print(f"Cost assumption: {spread_pips:g}p/trade ({a.symbol.upper()})")
    report("APPROVED", buckets["APPROVE"]); report("REJECTED", buckets["REJECT"])
    report("ALL", sigs)
    print("\n=== approved signals — outcome ===")
    for s in sigs:
        if s["_v"] == "APPROVE":
            lt = dt.datetime.fromtimestamp(s["t"]).strftime("%H:%M")
            print(f"  {lt} {s['side']:5} {s['why']:22} @{s['entry']}  ->  "
                  f"{s['_o']:7} gross={s['_p']:+d}p NET={s['_np']:+d}p")

if __name__ == "__main__":
    main()
