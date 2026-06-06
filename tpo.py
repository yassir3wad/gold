#!/usr/bin/env python3
"""Read the 'Realtime TPO Profile [Kioseff Trading]' indicator's value-area lines off the chart.
The indicator draws VA boundary lines (lime = col4) and a POC line (yellow = col2), anchored at each
session start (x1) and extended forward until price moves >5% away. We read those line objects
(data_get_pine_lines --verbose -> all_lines), group them by session-start x, and return per-session
{x, vah, val, poc}. Colors are matched by RGB (low 24 bits) so they're robust to the indicator's
transparency settings. Full algorithm + color map: tpo-indicator.md.
"""
import subprocess, os, json, time, datetime as dt
from collections import defaultdict

TVDIR = os.path.expanduser("~/tradingview-mcp")
TPO_FILTER = "TPO"
_VA_RGB = 0x76E600    # col4 lime — value-area boundary lines (VAH/VAL)
_POC_RGB = 0x3BEBFF   # col2 yellow — POC line


def _default_tv(chart, *a):
    env = dict(os.environ)
    if chart:
        env["TV_CHART"] = chart
    try:
        r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=40, env=env)
        return json.loads(r.stdout)
    except Exception:
        return {}


def _rgb(c):
    return (c & 0xFFFFFF) if isinstance(c, int) else None


def tpo_sessions(all_lines):
    """Group the TPO VA/POC line objects into per-session value areas. Pure (testable).
    VA lines (lime) come as a VAH/VAL pair per session-start x; the POC line (yellow) is one per session.
    Returns [{x, vah, val, poc}] sorted by x; a session is emitted when it has a VA pair OR a POC line."""
    g = defaultdict(lambda: {"va": [], "poc": None})
    for l in all_lines:
        if not l.get("horizontal"):     # skip the aqua session-separator verticals etc.
            continue
        rgb = _rgb(l.get("color")); y = l.get("y1"); x = l.get("x1")
        if y is None or x is None:
            continue
        if rgb == _VA_RGB:
            g[x]["va"].append(y)
        elif rgb == _POC_RGB:
            g[x]["poc"] = y
    out = []
    for x, d in g.items():
        va = sorted(d["va"])
        if len(va) >= 2:
            out.append({"x": x, "vah": max(va), "val": min(va), "poc": d["poc"]})
        elif d["poc"] is not None:
            out.append({"x": x, "vah": None, "val": None, "poc": d["poc"]})
    return sorted(out, key=lambda s: s["x"])


def read_tpo_lines(chart, tv=None, render_wait=4.0):
    """Resolve the TPO study id FRESH (it rotates), show it, read its line objects, hide it, and group
    into per-session value areas. Returns [{x, vah, val, poc}] (x = session-start bar index)."""
    tv = tv or _default_tv
    live = tv is None or tv is _default_tv
    studies = (tv(chart, "state") or {}).get("studies", [])
    tid = next((s["id"] for s in studies if "TPO" in (s.get("name") or "")), None)
    if not tid:
        return []
    tv(chart, "indicator", "toggle", tid, "--visible", "true")
    if live and render_wait:
        time.sleep(render_wait)
    studies = tv(chart, "data", "lines", "-f", TPO_FILTER, "--verbose").get("studies", [])
    al = studies[0].get("all_lines", []) if studies else []
    tv(chart, "indicator", "toggle", tid, "--hidden")   # store-and-hide
    return tpo_sessions(al)


def _next_day(date):
    return (dt.datetime.strptime(date, "%Y-%m-%d").date() + dt.timedelta(days=1)).isoformat()


def fetch_va(symbol, date, chart=None, tv=None, render_wait=8.0):
    """Read ONE day's POC/VAH/VAL off the TPO indicator by replaying to that day's CLOSE and reading the
    indicator's printed VAH/VAL/POC TEXT labels (the current/just-completed session's value area). We tag
    it with `date` — known from the cursor WE set — so there's no unreliable bar-index dating. Returns
    {poc, vah, val} (any may be None if the indicator hadn't finished rendering). For va_store fallback.

    Method (validated): cursor = start of next day => current session = `date`, just closed; its VAH/VAL/POC
    labels are stable. Retries a few times because the realtime TPO needs time to compute the full profile.
    """
    tv = tv or _default_tv
    chart = chart or os.environ.get("TV_CHART", "")
    tv(chart, "timeframe", "30")
    tv(chart, "replay", "start", "--date", _next_day(date))
    time.sleep(render_wait)
    tid = next((s["id"] for s in (tv(chart, "state") or {}).get("studies", []) if "TPO" in (s.get("name") or "")), None)
    if tid:
        tv(chart, "indicator", "toggle", tid, "--visible", "true")
    m = {}
    for attempt in range(4):
        time.sleep(render_wait if attempt == 0 else 4.0)
        labs = ((tv(chart, "data", "labels", "-f", TPO_FILTER, "-n", "600").get("studies", []) or [{}])[0]).get("labels", [])
        m = {}
        for l in labs:
            t = str(l.get("text", "")).strip()
            if t in ("VAH", "VAL", "POC") and t not in m:
                m[t] = l.get("price")
        if all(k in m for k in ("VAH", "VAL", "POC")):   # full value area rendered
            break
    if tid:
        tv(chart, "indicator", "toggle", tid, "--hidden")
    return {"poc": m.get("POC"), "vah": m.get("VAH"), "val": m.get("VAL")}

