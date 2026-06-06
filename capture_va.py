#!/usr/bin/env python3
"""Capture a TradingView chart image of a week's TPO value-area profiles, for AI (Claude Code) extraction.

The data API can't be scraped reliably (orphaned-primitive residue), but the chart RENDERS correctly — so
we screenshot it and let the vision-capable agent read the VAH/POC/VAL off the rendered profiles. Critical
fix: the desktop app does NOT repaint an occluded/background tab, so CDP returns a STALE frame; we ACTIVATE
the tab first (tab switch) so the canvas renders live, then capture.

Flow (fits the existing Claude-Code-as-AI pattern): a scheduled run calls this to set up + capture, then
Claude Code reads the image and writes per-day VAs into va_store (immutable cache). See
docs/value-area-framework.md and tpo-indicator.md.

    python3 capture_va.py --chart eFMec2F9 --symbol PEPPERSTONE:XAUUSD --week-end 2026-05-31 [--days 10]
"""
import argparse, subprocess, os, json, time, datetime as dt

TVDIR = os.path.expanduser("~/tradingview-mcp")


def tv(*a, chart=None):
    env = dict(os.environ)
    if chart:
        env["TV_CHART"] = chart
    try:
        r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=45, env=env)
        return json.loads(r.stdout)
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chart", default="eFMec2F9")          # the dedicated review chart (not a live pair chart)
    ap.add_argument("--symbol", default="PEPPERSTONE:XAUUSD")  # PEPPERSTONE has real volume (OANDA gold doesn't)
    ap.add_argument("--week-end", required=True)            # last day to show; replay cursor parks here (YYYY-MM-DD)
    ap.add_argument("--days", type=int, default=10)         # how many days of profiles to frame
    a = ap.parse_args()
    CH = a.chart

    # 1) ACTIVATE the tab so its canvas renders live (else the screenshot is a stale frame)
    tabs = tv("tab", "list").get("tabs", [])
    idx = next((t["index"] for t in tabs if t.get("chart_id") == CH), None)
    if idx is not None:
        tv("tab", "switch", "--index", str(idx))
        time.sleep(2)

    # 2) set symbol + 30m (the TPO session TF) and replay to the week end so the profiles are complete
    tv("symbol", a.symbol, chart=CH)
    tv("timeframe", "30", chart=CH)
    tv("replay", "start", "--date", (dt.datetime.strptime(a.week_end, "%Y-%m-%d").date() + dt.timedelta(days=1)).isoformat(), chart=CH)
    time.sleep(4)

    # 3) frame the week: from (week_end - days) to (week_end + 1), so all the daily profiles are in view
    end = dt.datetime.strptime(a.week_end, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    frm = int((end - dt.timedelta(days=a.days)).timestamp())
    to = int((end + dt.timedelta(days=1)).timestamp())
    tv("chart", "--from", str(frm), "--to", str(to), chart=CH)
    time.sleep(2)

    # 4) show the TPO indicator and capture the full window (axis included)
    tid = next((s["id"] for s in (tv("state", chart=CH) or {}).get("studies", []) if "TPO" in (s.get("name") or "")), None)
    if tid:
        tv("indicator", "toggle", tid, "--visible", "true", chart=CH)
    time.sleep(3)
    res = tv("screenshot", "--region", "full", chart=CH)
    print(json.dumps({"image": res.get("file_path"), "chart": CH, "symbol": a.symbol,
                      "week_end": a.week_end, "days": a.days}))


if __name__ == "__main__":
    main()
