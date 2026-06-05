#!/usr/bin/env python3
"""Render detected structural patterns onto the TradingView chart via the node CLI draw tools.
Channel -> two parallel trend-lines; Fib -> horizontal lines + labels; Double-top/bottom -> neckline.
Every draw is tagged in its text so clear_patterns() can find and remove just our annotations.

    from draw_patterns import draw_all
    draw_all(bars, chart="2jQrylrl")        # detect + draw everything
    draw_all(bars, dry_run=True)            # print the CLI commands without drawing
"""
import subprocess, os, json
import patterns as P

CLI = os.path.expanduser("~/tradingview-mcp/src/cli/index.js")
TVDIR = os.path.expanduser("~/tradingview-mcp")
TAG = "AUTO-PATTERN"   # marker embedded in labels so we can clear only our drawings


def _draw(args, chart=None, dry_run=False):
    cmd = ["node", CLI, "draw", "shape"] + args
    if dry_run:
        print("  DRAW " + " ".join(str(a) for a in args))
        return None
    env = dict(os.environ)
    if chart:
        env["TV_CHART"] = chart
    try:
        r = subprocess.run(cmd, cwd=TVDIR, capture_output=True, text=True, timeout=30, env=env)
        out = json.loads(r.stdout) if r.stdout.strip() else {}
        return out.get("id") or out.get("entity_id") or out
    except Exception as e:
        return {"error": str(e)}


def _hline(price, label, chart=None, dry_run=False):
    return _draw(["-t", "horizontal_line", "-p", f"{price:.2f}",
                  "--text", f"{label} [{TAG}]"], chart, dry_run)


def _tline(t0, p0, t1, p1, chart=None, dry_run=False):
    return _draw(["-t", "trend_line", "-p", f"{p0:.2f}", "--time", str(int(t0)),
                  "--price2", f"{p1:.2f}", "--time2", str(int(t1))], chart, dry_run)


def draw_channel(bars, ch, chart=None, dry_run=False):
    """Two parallel trend-lines (upper + lower boundary) spanning the regression window."""
    if not ch:
        return []
    b = bars[-ch["lookback"]:]
    t0, t1 = b[0]["time"], b[-1]["time"]
    shift = ch["slope"] * (ch["lookback"] - 1)
    up1, lo1 = ch["upper"], ch["lower"]
    up0, lo0 = up1 - shift, lo1 - shift
    ids = [_tline(t0, up0, t1, up1, chart, dry_run), _tline(t0, lo0, t1, lo1, chart, dry_run)]
    ids.append(_hline(ch["mid"], f"{ch['direction']}-channel mid", chart, dry_run))
    return ids


def draw_fib(high, low, chart=None, dry_run=False):
    """Horizontal lines at each fib retracement + a golden-pocket marker."""
    ids = []
    for lvl, price in P.fib_levels(high, low).items():
        ids.append(_hline(price, f"fib {lvl}", chart, dry_run))
    gp = P.golden_pocket(high, low)
    ids.append(_hline((gp[0] + gp[1]) / 2, "golden pocket", chart, dry_run))
    return ids


def draw_double(d, chart=None, dry_run=False):
    if not d:
        return []
    return [_hline(d["neckline"], f"{d['kind']} neckline", chart, dry_run),
            _hline(d["level"], f"{d['kind']} level", chart, dry_run)]


def clear_patterns(chart=None, dry_run=False):
    """Remove only AUTO-PATTERN drawings (by listing and removing tagged ones)."""
    if dry_run:
        print("  CLEAR tagged drawings"); return
    env = dict(os.environ)
    if chart:
        env["TV_CHART"] = chart
    try:
        r = subprocess.run(["node", CLI, "draw", "list"], cwd=TVDIR, capture_output=True, text=True, timeout=30, env=env)
        items = json.loads(r.stdout).get("drawings", []) if r.stdout.strip() else []
        n = 0
        for it in items:
            if TAG in json.dumps(it):
                eid = it.get("id") or it.get("entity_id")
                if eid:
                    subprocess.run(["node", CLI, "draw", "remove", "--id", str(eid)], cwd=TVDIR, env=env, timeout=20)
                    n += 1
        return n
    except Exception as e:
        return {"error": str(e)}


def draw_all(bars, lookback=60, chart=None, dry_run=False):
    """Detect channel + fib(active swing) + double, draw them all. Returns a summary dict."""
    ch = P.detect_channel(bars, lookback=lookback)
    sw = P.active_swing(bars, lookback=lookback)
    d = P.detect_double(bars, left=3, right=3, tol=0.004)
    out = {"channel": ch and ch["direction"], "pos": ch and round(ch["pos"], 2),
           "swing": sw and sw["direction"], "double": d and d["kind"]}
    draw_channel(bars, ch, chart, dry_run)
    if sw:
        draw_fib(sw["high"], sw["low"], chart, dry_run)
    draw_double(d, chart, dry_run)
    return out
