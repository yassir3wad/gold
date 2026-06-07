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

def stats(group, spread_pips):
    """Pure net-of-cost aggregate for a group of scored signals (each carrying _o, _p, _np).
    Returns counts + gross/cost/NET + win-rate, never dividing by zero on an empty group."""
    c = Counter(s["_o"] for s in group)
    n = len(group)
    nw = sum(1 for s in group if s["_np"] > 0)
    nl = sum(1 for s in group if s["_np"] < 0)
    ns = n - nw - nl
    tp, sl, to = c["TP1"], c["SL"], c["timeout"]
    return {"n": n, "tp": tp, "sl": sl, "to": to,
            "tp_wr": tp / (tp + sl) * 100 if (tp + sl) else 0,
            "net_wr": nw / n * 100 if n else 0,
            "gross": sum(s["_p"] for s in group),
            "cost": spread_pips * n,
            "net": sum(s["_np"] for s in group),
            "nw": nw, "nl": nl, "ns": ns}


def smc_bucket_key(s):
    """Bucket a signal by its stored-SMC premium/discount alignment: 'aligned' (LONG in discount /
    SHORT in premium), 'misaligned' (wrong side), or 'no-SMC' (equilibrium / no snapshot / not logged).
    Accepts bool or stringified values (CSV/DB store TEXT)."""
    a = s.get("smc_aligned")
    if a in (True, "True"): return "aligned"
    if a in (False, "False"): return "misaligned"
    return "no-SMC"


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
        st = stats(group, spread_pips)
        print(f"  {name:11} n={st['n']:3}  TP1={st['tp']:3}  SL={st['sl']:3}  timeout={st['to']:3}  "
              f"TP1-vs-SL={st['tp_wr']:3.0f}%  NetWR={st['net_wr']:3.0f}% ({st['nw']}W/{st['nl']}L/{st['ns']}=)  "
              f"gross={st['gross']:+5d}p  cost=-{st['cost']:4.0f}p  NET={st['net']:+5d}p")

    print(f"=== outcomes, {a.date}, {a.horizon}-bar horizon (TP1 or SL first) ===")
    print(f"Cost assumption: {spread_pips:g}p/trade ({a.symbol.upper()})")
    report("APPROVED", buckets["APPROVE"]); report("REJECTED", buckets["REJECT"])
    report("ALL", sigs)

    # --- SMC premium/discount measurement: net-of-cost split by alignment (the decision-grade view) ---
    smc_groups = {"aligned": [], "misaligned": [], "no-SMC": []}
    for s in sigs:
        smc_groups[smc_bucket_key(s)].append(s)
    ages = [float(s["smc_age"]) for s in sigs if str(s.get("smc_age", "")).strip() not in ("", "None")]
    n_smc = len(smc_groups["aligned"]) + len(smc_groups["misaligned"])
    print(f"\n=== SMC buckets (stored multi-TF premium/discount) ===")
    if n_smc == 0:
        print("  (no SMC alignment logged on these signals — the snapshot was inert/absent in this replay)")
    if ages:
        print(f"  snapshot age: min={min(ages):.1f}h  avg={sum(ages)/len(ages):.1f}h  max={max(ages):.1f}h  (n={len(ages)})")
    for name in ("aligned", "misaligned", "no-SMC"):
        report(name, smc_groups[name])
    print("\n=== approved signals — outcome ===")
    for s in sigs:
        if s["_v"] == "APPROVE":
            lt = dt.datetime.fromtimestamp(s["t"]).strftime("%H:%M")
            print(f"  {lt} {s['side']:5} {s['why']:22} @{s['entry']}  ->  "
                  f"{s['_o']:7} gross={s['_p']:+d}p NET={s['_np']:+d}p")

if __name__ == "__main__":
    main()
