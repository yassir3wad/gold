#!/usr/bin/env python3
"""Does structural context actually find the high-edge scalps? Retro-tag every captured signal with its
channel/fib context (computed from the bars up to its timestamp, no look-ahead) and compare edge AFTER
the ~3p spread. If signals at a channel extreme / fib level clear the spread better than the average,
patterns are worth integrating; if not, they aren't.
    python3 pattern_edge.py
"""
import json
from backtest_multi_day import simulate_trade
import patterns as P

PIP, HOR, SPREAD = 0.10, 15, 3
DAYS = ["2026-05-25", "2026-05-26", "2026-05-27", "2026-05-28", "2026-05-29",
        "2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"]


def resample(bars, mins=15):
    out = []; bucket = mins * 60; cur = None
    for b in sorted(bars, key=lambda x: x["time"]):
        k = b["time"] - (b["time"] % bucket)
        if cur is None or cur["time"] != k:
            if cur: out.append(cur)
            cur = dict(time=k, open=b["open"], high=b["high"], low=b["low"], close=b["close"])
        else:
            cur["high"] = max(cur["high"], b["high"]); cur["low"] = min(cur["low"], b["low"]); cur["close"] = b["close"]
    if cur: out.append(cur)
    return out


def tag(s, bars1):
    hist = [b for b in bars1 if b["time"] <= s["t"]]
    b15 = resample(hist, 15)
    if len(b15) < 12:
        return None
    ch = P.detect_channel(b15, lookback=min(40, len(b15)))
    sw = P.active_swing(b15, lookback=min(40, len(b15)))
    side = s["side"]; entry = s["entry"]
    # with-channel at the right extreme: SHORT near top of a down-channel, LONG near bottom of an up-channel
    good_ch = bool(ch and ((ch["direction"] == "down" and side == "SHORT" and ch["pos"] > 0.65) or
                           (ch["direction"] == "up" and side == "LONG" and ch["pos"] < 0.35)))
    # fib proximity: entry within 8p of any fib level; golden-pocket containment
    fib_near = gp_in = False
    if sw:
        levels = list(P.fib_levels(sw["high"], sw["low"]).values())
        fib_near = min(abs(entry - L) for L in levels) / PIP <= 8
        gp = P.golden_pocket(sw["high"], sw["low"]); gp_in = gp[0] <= entry <= gp[1]
    return {"good_ch": good_ch, "fib_near": fib_near, "gp_in": gp_in}


def main():
    rows = []
    for d in DAYS:
        sigs = json.load(open(f"/tmp/replay_sim_{d}.json"))
        bars1 = sorted(json.load(open(f"/tmp/bars_{d}.json")), key=lambda b: b["time"])
        for s in sigs:
            if not (s.get("entry") and s.get("sl") and s.get("tp1")):
                continue
            fut = [b for b in bars1 if b["time"] > s["t"]][:HOR]
            o, exitp, _ = simulate_trade(s["side"], s["entry"], s["sl"], s["tp1"], fut, horizon=HOR)
            if o not in ("TP1", "SL"):
                continue
            t = tag(s, bars1)
            if t is None:
                continue
            pips = (s["entry"] - exitp) / PIP if s["side"] == "SHORT" else (exitp - s["entry"]) / PIP
            rows.append({**t, "won": o == "TP1", "pips": round(pips)})

    def rep(name, sel):
        g = [r for r in rows if sel(r)]
        if not g:
            print(f"  {name:34} n=  0"); return
        n = len(g); gross = sum(r["pips"] for r in g) / n; net = gross - SPREAD
        wr = sum(1 for r in g if r["won"]) / n * 100
        print(f"  {name:34} n={n:4} win%={wr:3.0f}  gross={gross:+5.1f}p  net(-{SPREAD})={net:+5.1f}p  {'CLEARS' if net>0 else ''}")

    print(f"### pattern-context edge · {len(rows)} signals · after {SPREAD}p spread ###\n")
    rep("ALL signals", lambda r: True)
    rep("at good channel location", lambda r: r["good_ch"])
    rep("near a fib level (<8p)", lambda r: r["fib_near"])
    rep("inside golden pocket", lambda r: r["gp_in"])
    rep("good channel + fib confluence", lambda r: r["good_ch"] and r["fib_near"])
    rep("good channel + golden pocket", lambda r: r["good_ch"] and r["gp_in"])
    rep("NONE of the above (no context)", lambda r: not (r["good_ch"] or r["fib_near"] or r["gp_in"]))


if __name__ == "__main__":
    main()
