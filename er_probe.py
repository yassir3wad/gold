#!/usr/bin/env python3
"""Test the hypothesis that the 3h Kaufman ER is the wrong frame for 1m scalps:
recompute a FAST ER (30/45/60 min) at each signal's timestamp from the day's 1m bars, then ask:
  (1) does fast-ER separate winners (TP1-first) from losers (SL-first) better than the stored 3h-ER?
  (2) when the 3h frame and the fast frame DISAGREE, who's right about the outcome?  (the "stale signal" test)
  (3) what do near-floor (low 3h-ER) signals actually do?  (the "hiding signals" test)
    python3 er_probe.py
"""
import json, datetime as dt
from collections import defaultdict
from backtest_multi_day import simulate_trade

PIP, HORIZON = 0.10, 15
DAYS = ["2026-05-25", "2026-05-26", "2026-05-27", "2026-05-28", "2026-05-29",
        "2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"]


def kaufman_er(closes):
    if len(closes) < 2:
        return None
    path = sum(abs(closes[i] - closes[i - 1]) for i in range(1, len(closes)))
    return abs(closes[-1] - closes[0]) / path if path else 0.0


def fast_er(bars_by_t, t, minutes):
    win = [bars_by_t[k]["close"] for k in sorted(bars_by_t) if t - minutes * 60 < k <= t]
    return kaufman_er(win)


def fnum(x, d=0.0):
    try: return float(x)
    except (TypeError, ValueError): return d


def load():
    rows = []
    for d in DAYS:
        sigs = json.load(open(f"/tmp/replay_sim_{d}.json"))
        bars = sorted(json.load(open(f"/tmp/bars_{d}.json")), key=lambda b: b["time"])
        bt = {b["time"]: b for b in bars}
        for s in sigs:
            fut = [b for b in bars if b["time"] > s["t"]][:HORIZON]
            o, exitp, _ = simulate_trade(s["side"], s["entry"], s["sl"], s["tp1"], fut, horizon=HORIZON)
            if o not in ("TP1", "SL"):
                continue
            pips = (s["entry"] - exitp) / PIP if s["side"] == "SHORT" else (exitp - s["entry"]) / PIP
            rows.append({"won": o == "TP1", "pips": round(pips), "er3h": fnum(s.get("er")),
                         "er30": fast_er(bt, s["t"], 30), "er45": fast_er(bt, s["t"], 45),
                         "er60": fast_er(bt, s["t"], 60), "why": s.get("why", "?")})
    return rows


def wr(rows):
    w = sum(1 for r in rows if r["won"]); net = sum(r["pips"] for r in rows)
    return len(rows), (w / len(rows) * 100 if rows else 0), net


def buckets(rows, key, edges):
    print(f"\n=== outcome by {key} ===")
    print(f"  {'bucket':10}{'n':>5}{'win%':>7}{'net':>8}")
    labels = [f"<{edges[0]}"] + [f"{edges[i]}-{edges[i+1]}" for i in range(len(edges) - 1)] + [f">{edges[-1]}"]
    grp = defaultdict(list)
    for r in rows:
        v = r[key]
        if v is None: continue
        b = labels[0]
        for i, e in enumerate(edges):
            if v >= e: b = labels[i + 1]
        grp[b].append(r)
    for lb in labels:
        if grp[lb]:
            n, w, net = wr(grp[lb]); print(f"  {lb:10}{n:>5}{w:>6.0f}%{net:>+8d}p")


def main():
    rows = [r for r in load() if r["er30"] is not None]
    print(f"### ER frame probe · {len(rows)} resolved signals across {len(DAYS)} days ###")
    buckets(rows, "er3h", [0.2, 0.35, 0.5])
    buckets(rows, "er30", [0.2, 0.35, 0.5])
    buckets(rows, "er45", [0.2, 0.35, 0.5])

    # (2) agreement cross-tab: trend if ER>=0.5
    print("\n=== 3h vs 30m agreement (trend = ER>=0.5) — the STALE-SIGNAL test ===")
    print(f"  {'3h':>6} {'30m':>6}{'n':>5}{'win%':>7}{'net':>8}")
    for a in (True, False):
        for b in (True, False):
            g = [r for r in rows if (r["er3h"] >= 0.5) == a and (r["er30"] >= 0.5) == b]
            if g:
                n, w, net = wr(g)
                print(f"  {'trend' if a else 'chop':>6} {'trend' if b else 'chop':>6}{n:>5}{w:>6.0f}%{net:>+8d}p")

    # (3) near-floor 3h-ER — the HIDING-SIGNALS test
    print("\n=== near/below the hard floor (3h-ER<0.20) — what fired signals there actually do ===")
    lo = [r for r in rows if r["er3h"] < 0.20]
    n, w, net = wr(lo); print(f"  3h-ER<0.20 (would be hard-skipped if breakout/momentum): n={n} win%={w:.0f} net={net:+d}p")
    lo30 = [r for r in lo if r["er30"] >= 0.35]
    n, w, net = wr(lo30); print(f"    ...of those, fast-30m-ER>=0.35 (fresh trend, stale 3h): n={n} win%={w:.0f} net={net:+d}p")

    # discrimination spread: top-vs-bottom-third win-rate gap per frame (bigger = more predictive)
    print("\n=== discrimination (win% spread, high-third minus low-third) — bigger = better frame ===")
    for k in ("er3h", "er30", "er45", "er60"):
        vals = sorted([r for r in rows if r[k] is not None], key=lambda r: r[k])
        third = len(vals) // 3
        if third:
            _, wl, _ = wr(vals[:third]); _, wh, _ = wr(vals[-third:])
            print(f"  {k:6}: low-third win%={wl:4.0f}  high-third win%={wh:4.0f}  spread={wh-wl:+5.0f}")


if __name__ == "__main__":
    main()
