#!/usr/bin/env python3
"""Collect a full day's 1m bars off the replay tab (step forward, pull overlapping ohlcv windows, merge
by timestamp). Used to score signal outcomes (TP1 vs SL). Pins to the backtest chart; live loop untouched.
    python3 collect_bars.py --date 2026-06-04 --chart eFMec2F9
"""
import argparse, subprocess, os, json, time, datetime as dt
TVDIR = os.path.expanduser("~/tradingview-mcp")
try:   # use the live engine's configured gold symbol (PEPPERSTONE:XAUUSD), not bare XAUUSD→OANDA
    TV_SYMBOL = json.load(open(os.path.join(TVDIR, "instruments.json"))).get("XAUUSD", {}).get("tv", "XAUUSD")
except Exception:
    TV_SYMBOL = "XAUUSD"

def tv(chart, *a):
    env = dict(os.environ); env["TV_CHART"] = chart
    try:
        r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=40, env=env)
        return json.loads(r.stdout)
    except Exception:
        return {}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True); ap.add_argument("--chart", required=True)
    ap.add_argument("--batch", type=int, default=50); ap.add_argument("--max-steps", type=int, default=1700)
    a = ap.parse_args(); CH = a.chart
    target = dt.datetime.strptime(a.date, "%Y-%m-%d").date()
    tv(CH, "symbol", TV_SYMBOL); tv(CH, "timeframe", "1")
    tv(CH, "replay", "start", "--date", a.date); time.sleep(5)
    bars = {}; steps = 0; out = f"/tmp/bars_{a.date}.json"
    while steps < a.max_steps:
        done = False
        for b in tv(CH, "ohlcv", "-n", str(a.batch + 12)).get("bars", []):
            d = dt.datetime.utcfromtimestamp(b["time"]).date()
            if d == target: bars[b["time"]] = b
            elif d > target: done = True
        if done and bars:
            break
        for _ in range(a.batch):
            tv(CH, "replay", "step"); steps += 1
        if steps % 200 == 0:
            json.dump(sorted(bars.values(), key=lambda x: x["time"]), open(out, "w"))
            print(f"  {steps} steps · {len(bars)} bars collected", flush=True)
    tv(CH, "replay", "stop")
    ordered = sorted(bars.values(), key=lambda x: x["time"])
    json.dump(ordered, open(out, "w"))
    span = (f"{dt.datetime.utcfromtimestamp(ordered[0]['time']):%H:%M}-{dt.datetime.utcfromtimestamp(ordered[-1]['time']):%H:%M} UTC"
            if ordered else "none")
    print(f"\n=== {len(ordered)} bars for {a.date} ({span}) saved {out} ===")

if __name__ == "__main__":
    main()
