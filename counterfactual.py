#!/usr/bin/env python3
"""Counterfactual reject analysis — for the trades we REJECTED, what would have happened?

For each rejected signal (which logged its entry/SL/TP1), replay the bars that came after it and check
whether TP1 or SL would have hit first. Aggregates into "winners we passed on" vs "losers we dodged", so
you can see whether the discipline (and the hard floor) is net +EV or quietly over-rejecting.

Read-only: pulls OHLCV only, never mutates the chart or live state. Covers only rejects whose bars are
still in the chart buffer (recent ones) — older signals are reported as 'no data', not silently dropped.

    python3 counterfactual.py [--symbol XAUUSD] [--bars 500] [--window 15]
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.expanduser("~/tradingview-mcp"))
import analyze_logs as al
TVDIR = os.path.expanduser("~/tradingview-mcp")


def simulate_outcome(side, entry, sl, tp1, bars):
    """Which level is hit first over `bars` (chronological, after entry)? SL takes priority on a same-bar
    tie (conservative — the standard backtest assumption). Returns 'TP1' | 'SL' | 'none'. Pure/testable."""
    for b in bars:
        hi, lo = b["high"], b["low"]
        if side == "LONG":
            if lo <= sl:  return "SL"
            if hi >= tp1: return "TP1"
        else:
            if hi >= sl:  return "SL"
            if lo <= tp1: return "TP1"
    return "none"


def _bars_for(sym, cfg, n):
    env = dict(os.environ)
    if cfg.get("chart"): env["TV_CHART"] = str(cfg["chart"])
    try:
        r = subprocess.run(["node", "src/cli/index.js", "ohlcv", "-n", str(n)], cwd=TVDIR,
                           capture_output=True, text=True, timeout=45, env=env)
        return json.loads(r.stdout).get("bars", [])
    except Exception:
        return []


def _unix(time_str):
    try: return dt.datetime.strptime(time_str.strip(), "%Y-%m-%d %H:%M").astimezone().timestamp()
    except Exception: return None


def main():
    symbol, n, window = None, 500, 15
    for flag, conv in (("--symbol", str), ("--bars", int), ("--window", int)):
        if flag in sys.argv:
            try:
                v = conv(sys.argv[sys.argv.index(flag) + 1])
                if flag == "--symbol": symbol = v
                elif flag == "--bars": n = v
                else: window = v
            except Exception: pass

    try: instr = json.load(open(os.path.join(TVDIR, "instruments.json")))
    except Exception: instr = {}
    rows = al.load_rows(symbol)
    rejected = [r for r in rows if r.get("result") == "rejected"
                and al._num(r.get("entry")) and al._num(r.get("sl")) and al._num(r.get("tp1"))]

    by_sym = {}
    for r in rejected: by_sym.setdefault(r.get("sym", "XAUUSD"), []).append(r)

    res = {"TP1": 0, "SL": 0, "none": 0, "nodata": 0}
    won_pips = dodged_pips = 0.0
    by_reason = {}   # reason-bucket -> [tp1, sl]
    def bucket(note):
        n = note.lower()
        for b, keys in al.REJECT_BUCKETS.items():
            if any(k in n for k in keys): return b
        return "other"

    for sym, rs in by_sym.items():
        cfg = {**instr.get("_default", {}), **instr.get(sym, {})}
        pip = cfg.get("pip", 0.10)
        bars = _bars_for(sym, cfg, n)
        bmin = bars[0]["time"] if bars else None
        for r in rs:
            t = _unix(r.get("time"))
            if not bars or t is None or t < bmin:
                res["nodata"] += 1; continue
            after = [b for b in bars if b["time"] > t][:window]
            if not after:
                res["nodata"] += 1; continue
            side, entry, sl, tp1 = r.get("side"), al._num(r["entry"]), al._num(r["sl"]), al._num(r["tp1"])
            out = simulate_outcome(side, entry, sl, tp1, after)
            res[out] += 1
            bk = bucket(str(r.get("pips", "")))
            by_reason.setdefault(bk, [0, 0])
            if out == "TP1": won_pips += abs(tp1 - entry) / pip; by_reason[bk][0] += 1
            elif out == "SL": dodged_pips += abs(entry - sl) / pip; by_reason[bk][1] += 1

    simulated = res["TP1"] + res["SL"] + res["none"]
    print("=" * 70)
    print(f"  COUNTERFACTUAL REJECT ANALYSIS  ({simulated} simulated · {res['nodata']} no-data/too-old)")
    print("=" * 70)
    if not simulated:
        print("  No rejects within the available bar window — run again after the loop logs recent rejects,")
        print("  or increase --bars. (Bars must still be in the chart buffer to replay.)")
        return
    print(f"  Would have WON (hit TP1)   : {res['TP1']:>3}   (+{won_pips:.0f}p of winners we passed on)")
    print(f"  Would have LOST (hit SL)   : {res['SL']:>3}   (-{dodged_pips:.0f}p of losers we dodged)")
    print(f"  Neither within {window} bars   : {res['none']:>3}")
    net = dodged_pips - won_pips
    verdict = "✅ discipline is +EV (dodged more than it passed)" if net >= 0 else "⚠️ OVER-REJECTING (passed more winners than losers dodged)"
    print(f"\n  Net edge of rejecting: {net:+.0f}p   →  {verdict}")
    if by_reason:
        print("\n  By reject reason (would-win / would-lose):")
        for bk, (w, l) in sorted(by_reason.items(), key=lambda kv: -(kv[1][0] + kv[1][1])):
            flag = "  ← passing winners?" if w > l else ""
            print(f"    {bk:18} {w}W / {l}L{flag}")
    print("\n  Caveat: assumes entry at the logged price with logged SL/TP1; same-bar ties → SL (conservative);")
    print("  only rejects still in the bar buffer are covered.")


if __name__ == "__main__":
    main()
