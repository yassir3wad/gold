#!/usr/bin/env python3
"""On-demand pattern annotator: read the current chart's bars at its own timeframe, detect the
structural patterns, and draw them. Adapts to whatever symbol/TF the chart is on.

    python3 pattern_scan.py --chart 2jQrylrl              # detect + draw on that chart
    python3 pattern_scan.py --chart 2jQrylrl --dry-run    # just print what it would draw
    python3 pattern_scan.py --chart 2jQrylrl --clear      # remove our AUTO-PATTERN drawings
"""
import argparse, subprocess, os, json
import patterns as P
import draw_patterns as D

CLI = os.path.expanduser("~/tradingview-mcp/src/cli/index.js")
TVDIR = os.path.expanduser("~/tradingview-mcp")


def cli(chart, *args):
    env = dict(os.environ)
    if chart:
        env["TV_CHART"] = chart
    r = subprocess.run(["node", CLI, *args], cwd=TVDIR, capture_output=True, text=True, timeout=40, env=env)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chart", required=True)
    ap.add_argument("--n", type=int, default=120, help="bars to analyze")
    ap.add_argument("--lookback", type=int, default=60)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--clear", action="store_true")
    a = ap.parse_args()

    if a.clear:
        print("removed:", D.clear_patterns(chart=a.chart, dry_run=a.dry_run))
        return

    state = cli(a.chart, "chart", "get-state") or {}
    sym = state.get("symbol", "?"); tf = state.get("timeframe", "?")
    raw = cli(a.chart, "ohlcv", "-n", str(a.n)).get("bars", [])
    bars = sorted(({"time": b["time"], "open": b["open"], "high": b["high"],
                    "low": b["low"], "close": b["close"]} for b in raw), key=lambda x: x["time"])
    if len(bars) < 10:
        print(f"not enough bars ({len(bars)}) on {sym} {tf}"); return

    ch = P.detect_channel(bars, lookback=a.lookback)
    sw = P.active_swing(bars, lookback=a.lookback)
    d = P.detect_double(bars, left=3, right=3, tol=0.004)
    print(f"=== {sym} {tf} · {len(bars)} bars ===")
    if ch:
        print(f"  channel : {ch['direction']:5} slope={ch['slope']:+.3f}/bar  pos={ch['pos']:.2f} "
              f"(0=lower/buy, 1=upper/sell)  band={ch['band']:.1f}")
    if sw:
        gp = P.golden_pocket(sw['high'], sw['low'])
        print(f"  swing   : {sw['direction']} {sw['low']:.2f}->{sw['high']:.2f}  golden=[{gp[0]:.2f},{gp[1]:.2f}]")
    print(f"  double  : {d['kind'] + ' @ ' + format(d['neckline'], '.2f') if d else 'none'}")

    # redraw cleanly: clear our old annotations first, then draw current
    if not a.dry_run:
        D.clear_patterns(chart=a.chart)
    summary = D.draw_all(bars, lookback=a.lookback, chart=a.chart, dry_run=a.dry_run)
    print("  drawn:", summary)


if __name__ == "__main__":
    main()
