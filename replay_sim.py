#!/usr/bin/env python3
"""Replay simulation — step a past day candle-by-candle on a DEDICATED replay tab and run the REAL
`scalp_fast` scanner at each step (exactly like the live per-minute cron), collecting every surfaced
signal with its real on-chart context (RSI, regime, ER...). Full fidelity: the chart's own indicators
are read at each historical bar.

Isolation (so the LIVE loop is never touched):
  - pins the scanner to a backtest chart via TV_CHART_OVERRIDE (the loop never sets this)
  - isolates volatile state via STATE_SUFFIX (separate VP cache/cooldown; zones stay read-only-shared)

HOURLY structural refresh (date-faithful): every regime-refresh window (~1h of replay time) this clears the
30m-regime cache AND the SMC/Auto-Trendline cache (~/.tv_fast_<suffix>_smc.json) so the scanner re-reads
zones + the SMC/trendline confluence from the bars AT THE REPLAY CURSOR — i.e. the values that existed on
that date, not today's. Zones are recomputed on the replay bars; SMC/trendlines use the same store-and-hide
read as live (show → render → read → hide), only ~once per replay-hour (gentle on the CDP). Full detail:
docs/zones-and-confluence.md.

    python3 replay_sim.py --date 2026-06-04 --chart eFMec2F9 --start-hour 6 --end-hour 22
"""
import argparse, subprocess, os, json, re, time, datetime as dt
TVDIR = os.path.expanduser("~/tradingview-mcp")        # node CLI runs here (node_modules lives in main tree)
SCRIPTDIR = os.path.dirname(os.path.abspath(__file__)) # run THIS checkout's engine (worktree) by absolute path
SUFFIX = "xauusd_bt"
BASE_TF = "5"                                                   # execution timeframe (minutes); set from --tf in main
ZONEFILE = os.path.expanduser(f"~/tradingview-mcp/zones_{SUFFIX}.json")   # isolated, date-faithful zone file (never the live one)

def tv(chart, *a):
    env = dict(os.environ); env["TV_CHART"] = chart
    try:
        r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=40, env=env)
        return json.loads(r.stdout)
    except Exception:
        return {}

def regen_zones(chart):
    """Rebuild the isolated zone file from the replay chart (date-faithful) and redraw it on the chart."""
    try:
        subprocess.run(["python3", os.path.join(SCRIPTDIR, "refresh_zones.py"), "--symbol", "XAUUSD", "--chart", chart, "--out", ZONEFILE],
                       cwd=TVDIR, capture_output=True, text=True, timeout=150)
    except Exception:
        pass
    tv(chart, "timeframe", BASE_TF)   # refresh_zones switches TF (and leaves it on 1m) — restore the 5m execution TF
    draw_zones(chart)

def draw_zones(chart):
    """Draw the current zone file as labeled horizontal lines (clears prior drawings on this backtest chart first)."""
    try:
        z = json.load(open(ZONEFILE))
    except Exception:
        return
    tv(chart, "draw", "clear")                                  # backtest chart is ours — safe to clear+redraw
    lines = []
    for entry in z.get("htf_r", []) + z.get("htf_s", []):       # HTF S/R zones -> mid-line
        if len(entry) >= 2:
            lo, hi = entry[0], entry[1]; lab = entry[2] if len(entry) > 2 else "zone"
            lines.append(((lo + hi) / 2, lab))
    for key, lab in [("pdh", "PDH"), ("pdl", "PDL"), ("asia_h", "Asia H"), ("asia_l", "Asia L")]:
        v = z.get(key)
        if v:
            lines.append((v, lab))
    for price, lab in lines:
        tv(chart, "draw", "shape", "--type", "horizontal_line", "--price", f"{price}", "--text", f"{lab} [BT-ZONE]")

def cursor_unix(chart):
    return tv(chart, "replay", "status").get("current_date")

def run_scanner(chart):
    env = dict(os.environ); env["TV_CHART_OVERRIDE"] = chart; env["STATE_SUFFIX"] = SUFFIX; env["TV_BASE_TF"] = BASE_TF
    try:
        r = subprocess.run(["python3", os.path.join(SCRIPTDIR, "scalp_fast.py"), "--symbol", "XAUUSD", "--dry"],
                           cwd=TVDIR, capture_output=True, text=True, timeout=90, env=env)
        return r.stdout
    except Exception:
        return ""

def parse_signal(out):
    m = re.search(r">> FAST SIGNAL: (\w+) \[(.*?)\] \[(.*?)\]", out)
    if not m:
        return None
    e = re.search(r"Entry ([\d.]+) \| SL ([\d.]+).*?TP1 ([\d.]+)", out)
    g = lambda p, d=None: (re.search(p, out).group(1) if re.search(p, out) else d)
    return {"side": m.group(1), "grade": m.group(2), "why": m.group(3),
            "entry": float(e.group(1)) if e else None, "sl": float(e.group(2)) if e else None,
            "tp1": float(e.group(3)) if e else None,
            "rsi": g(r"RSI=([\d.]+)"), "regime": g(r"regime=(\w+)"), "er": g(r"15m-ER=([\d.]+)"),
            "session": g(r"session=(\w+)"), "room": g(r"nextR=([\d.None]+)")}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--chart", required=True)
    ap.add_argument("--start-hour", type=int, default=0)   # UTC
    ap.add_argument("--end-hour", type=int, default=24)    # UTC
    ap.add_argument("--regime-refresh", type=int, default=15)  # clear VP/regime cache every N analyzed steps
    ap.add_argument("--max-steps", type=int, default=1600)
    ap.add_argument("--tf", default="5")                       # execution timeframe (minutes) — 5m, no more 1m
    a = ap.parse_args()
    global BASE_TF; BASE_TF = a.tf
    CH = a.chart
    target = dt.datetime.strptime(a.date, "%Y-%m-%d").date()
    vpfile = os.path.expanduser(f"~/.tv_fast_{SUFFIX}_vp.json")
    zone_every = max(1, 60 // int(a.tf))                       # regenerate + redraw zones every ~1h of replay time

    tv(CH, "symbol", "XAUUSD"); tv(CH, "timeframe", a.tf)
    tv(CH, "replay", "start", "--date", a.date); time.sleep(5)
    regen_zones(CH)                                            # initial date-faithful zones for this day, drawn on chart
    print(f"replay sim: {a.date}  window {a.start_hour:02d}:00-{a.end_hour:02d}:00 UTC  chart {CH}  TF={a.tf}m  zones/{zone_every} steps\n")

    out = f"/tmp/replay_sim_{a.date}.json"; barfile = f"/tmp/bars_{a.date}.json"
    signals = []; allbars = {}; analyzed = 0; last_key = None; last_step = -99
    for step in range(a.max_steps):
        cu = cursor_unix(CH)
        if cu:
            t = dt.datetime.utcfromtimestamp(cu)
            if t.date() > target:
                break                                   # past the day -> done
            if t.date() < target or not (a.start_hour <= t.hour < a.end_hour):
                tv(CH, "replay", "step"); continue      # outside the analyzed window -> just advance
        if a.regime_refresh and analyzed % a.regime_refresh == 0:
            try: os.remove(vpfile)                       # force a fresh 30m-regime read at the current cursor
            except Exception: pass
            try: os.remove(os.path.expanduser(f"~/.tv_fast_{SUFFIX}_smc.json"))   # date-faithful SMC/TL re-read at the cursor
            except Exception: pass
        if analyzed and analyzed % zone_every == 0:      # ~hourly: rebuild date-faithful zones at the current cursor + redraw
            regen_zones(CH)
        analyzed += 1
        for b in tv(CH, "ohlcv", "-n", "3").get("bars", []):   # capture real bars for outcome scoring (one pass)
            allbars[b["time"]] = b
        sig = parse_signal(run_scanner(CH))
        if sig and sig["entry"]:
            key = f"{sig['side']}|{round(sig['entry'])}|{sig['why']}"
            if key != last_key or step - last_step > 5:   # dedup the same thesis repeating across bars
                sig["t"] = cu; signals.append(sig); last_key = key; last_step = step
                lt = dt.datetime.fromtimestamp(cu).strftime("%H:%M")
                print(f"[{lt}] {sig['side']:5} {sig['why']:22} @{sig['entry']} SL {sig['sl']} TP1 {sig['tp1']} | "
                      f"RSI {sig['rsi']} ER {sig['er']} {sig['regime']} sess={sig['session']}", flush=True)
                json.dump(signals, open(out, "w"))   # incremental save (long run survives a crash)
        tv(CH, "replay", "step")

    tv(CH, "replay", "stop")
    json.dump(signals, open(out, "w"))
    json.dump(sorted(allbars.values(), key=lambda x: x["time"]), open(barfile, "w"))   # bars for scoring
    print(f"\n=== {len(signals)} distinct signals · {analyzed} candles analyzed · saved {out} ===")

if __name__ == "__main__":
    main()
