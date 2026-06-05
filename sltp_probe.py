#!/usr/bin/env python3
"""SL/TP geometry probe — attack the breakeven math directly.
For every surfaced signal we keep the entry + direction the engine chose, then on the SAME real future
bars we re-simulate alternative stop/target geometries to find what maximizes expectancy:
  (A) MFE/MAE distribution — how far price actually travels for/against us (the headroom that exists).
  (B) TP sweep — hold the engine's structure SL, move TP1 to R-multiples of it. (closer TP = higher hit
      rate, lower payoff; the EV/trade product is what matters.)
  (C) SL sweep — hold the engine's TP1, widen/tighten the SL. (wider = fewer premature stops, bigger loss.)
Expectancy is reported in pips/trade and in R, across all 9 backtest days.
    python3 sltp_probe.py
"""
import json
from backtest_multi_day import simulate_trade

PIP, HORIZON = 0.10, 15
DAYS = ["2026-05-25", "2026-05-26", "2026-05-27", "2026-05-28", "2026-05-29",
        "2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"]


def load():
    out = []
    for d in DAYS:
        sigs = json.load(open(f"/tmp/replay_sim_{d}.json"))
        bars = sorted(json.load(open(f"/tmp/bars_{d}.json")), key=lambda b: b["time"])
        for s in sigs:
            if not (s.get("entry") and s.get("sl") and s.get("tp1")):
                continue
            fut = [b for b in bars if b["time"] > s["t"]][:HORIZON]
            if len(fut) < 3:
                continue
            out.append({"side": s["side"], "entry": s["entry"], "sl": s["sl"], "tp1": s["tp1"], "fut": fut})
    return out


def pnl(sig, sl_price, tp_price):
    o, exitp, _ = simulate_trade(sig["side"], sig["entry"], sl_price, tp_price, sig["fut"], horizon=HORIZON)
    pips = (sig["entry"] - exitp) / PIP if sig["side"] == "SHORT" else (exitp - sig["entry"]) / PIP
    return o, pips


def excursions(sig):
    e = sig["entry"]
    if sig["side"] == "SHORT":
        mfe = max((e - b["low"]) for b in sig["fut"]) / PIP
        mae = max((b["high"] - e) for b in sig["fut"]) / PIP
    else:
        mfe = max((b["high"] - e) for b in sig["fut"]) / PIP
        mae = max((e - b["low"]) for b in sig["fut"]) / PIP
    return mfe, mae


def report(name, rows):
    n = len(rows)
    tp = sum(1 for o, _ in rows if o == "TP1"); sl = sum(1 for o, _ in rows if o == "SL")
    net = sum(p for _, p in rows); wr = tp / (tp + sl) * 100 if tp + sl else 0
    print(f"  {name:14} n={n:3} TP1={tp:3} SL={sl:3} win%={wr:3.0f}  net={net:+6.0f}p  EV={net/n:+5.1f}p/trade")


def main():
    sigs = load()
    print(f"### SL/TP geometry probe · {len(sigs)} signals · 9 days ###\n")

    # (A) excursion distribution + current geometry
    sl_d = [abs(s["entry"] - s["sl"]) / PIP for s in sigs]
    tp_d = [abs(s["tp1"] - s["entry"]) / PIP for s in sigs]
    mfes = [excursions(s)[0] for s in sigs]; maes = [excursions(s)[1] for s in sigs]
    med = lambda a: sorted(a)[len(a) // 2]
    print("=== (A) geometry + excursions (pips) ===")
    print(f"  engine SL dist : median {med(sl_d):4.0f}  (mean {sum(sl_d)/len(sl_d):4.0f})")
    print(f"  engine TP1 dist: median {med(tp_d):4.0f}  (mean {sum(tp_d)/len(tp_d):4.0f})")
    print(f"  current R:R    : median {med(tp_d)/med(sl_d):.2f}")
    print(f"  MFE (max favor): median {med(mfes):4.0f}  -> typical room toward target")
    print(f"  MAE (max adver): median {med(maes):4.0f}  -> typical heat against")
    # how many losers' MFE reached e.g. 0.5R / 0.75R before stopping (stops too tight?)
    base = report  # alias

    # (B) TP sweep: hold engine SL, move TP to R-multiples of the SL distance
    print("\n=== (B) TP sweep (engine structure SL held; TP = R x SL) ===")
    for rr in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
        rows = []
        for s in sigs:
            d = abs(s["entry"] - s["sl"])
            tp = s["entry"] - rr * d if s["side"] == "SHORT" else s["entry"] + rr * d
            rows.append(pnl(s, s["sl"], tp))
        report(f"TP={rr:.2f}R", rows)

    # (C) SL sweep: hold engine TP1, scale the SL distance
    print("\n=== (C) SL sweep (engine TP1 held; SL = mult x engine SL) ===")
    for m in (0.5, 0.75, 1.0, 1.5, 2.0, 3.0):
        rows = []
        for s in sigs:
            d = abs(s["entry"] - s["sl"]) * m
            sl = s["entry"] + d if s["side"] == "SHORT" else s["entry"] - d
            rows.append(pnl(s, sl, s["tp1"]))
        report(f"SL={m:.2f}x", rows)

    # (D) joint: best-looking combos
    print("\n=== (D) joint SL x TP grid (EV p/trade) ===")
    hdr = "SLx|TPr"
    print(f"  {hdr:>8}" + "".join(f"{rr:>7.2f}R" for rr in (0.75, 1.0, 1.5, 2.0)))
    for m in (0.75, 1.0, 1.5, 2.0):
        cells = []
        for rr in (0.75, 1.0, 1.5, 2.0):
            rows = []
            for s in sigs:
                d = abs(s["entry"] - s["sl"]) * m
                sl = s["entry"] + d if s["side"] == "SHORT" else s["entry"] - d
                tp = s["entry"] - rr * d if s["side"] == "SHORT" else s["entry"] + rr * d
                rows.append(pnl(s, sl, tp))
            cells.append(sum(p for _, p in rows) / len(rows))
        print(f"  {m:>7.2f}x" + "".join(f"{c:>+8.1f}" for c in cells))


if __name__ == "__main__":
    main()
