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


SESSION_CLOSE_HOUR = 22   # the gold daily TPO session rolls over at ~22:00 UTC (verified)
READ_FROM_HOUR = 15       # start scanning late bars here (the day's last bar before the 22:00 close varies)


def fetch_va(symbol, date, chart=None, tv=None, render_wait=8.0):
    """Read ONE day's POC/VAH/VAL off the TPO indicator. The daily session ROLLS OVER at ~22:00 UTC, so a
    day's finalized value area is only on screen in the window JUST BEFORE 22:00 (≈21:00–21:59): there the
    session is complete (POC present) AND still the current session whose VAH/VAL/POC TEXT labels are drawn.
    After 22:00 the labels switch to the next (empty) session. So we replay to `date` and step the cursor
    into that 21:xx window, then read the labels. The date is known from the cursor WE set — no bar-index
    dating. Returns {poc, vah, val} (None if the indicator hadn't rendered). For va_store fallback.
    """
    tv = tv or _default_tv
    chart = chart or os.environ.get("TV_CHART", "")
    tv(chart, "timeframe", "30")
    target = dt.datetime.strptime(date, "%Y-%m-%d").date()

    def cursor_dt():
        cu = (tv(chart, "replay", "status") or {}).get("current_date")
        return dt.datetime.utcfromtimestamp(cu) if cu else None

    def rolled(t):   # past the day's ~22:00 session close (or into the next day)
        return t is None or t.date() > target or (t.date() == target and t.hour >= SESSION_CLOSE_HOUR)

    def read_va():
        labs = ((tv(chart, "data", "labels", "-f", TPO_FILTER, "-n", "600").get("studies", []) or [{}])[0]).get("labels", [])
        m = {}
        for l in labs:
            t = str(l.get("text", "")).strip()
            if t in ("VAH", "VAL", "POC") and t not in m:
                m[t] = l.get("price")
        return m if all(k in m for k in ("VAH", "VAL", "POC")) else None

    tv(chart, "replay", "start", "--date", date)
    time.sleep(3)
    # step up to the day's late "close window" (>= ~19:00) — the exact last bar before the 22:00 rollover
    # varies per day (gaps), so we don't target a fixed hour.
    for _ in range(70):
        t = cursor_dt()
        if t and (t.date() > target or (t.date() == target and t.hour >= READ_FROM_HOUR)):
            break
        tv(chart, "replay", "step")
    tid = next((s["id"] for s in (tv(chart, "state") or {}).get("studies", []) if "TPO" in (s.get("name") or "")), None)
    if tid:
        tv(chart, "indicator", "toggle", tid, "--visible", "true")
    # Scan every bar of the calendar day and KEEP THE LAST COMPLETE (POC-present) read = the day's finalized
    # value area. A weekday rolls over at ~22:00 (its post-22:00 reads are incomplete, so `best` stays at the
    # pre-22:00 close); a Friday's session runs to the weekend, so its last complete read is at ~23:59. Stop
    # when the cursor crosses into the next calendar day.
    best = {}
    for i in range(30):
        t = cursor_dt()
        if t and t.date() > target:
            break
        time.sleep(render_wait if i == 0 else 3.0)
        m = read_va()
        if m:
            best = m
        tv(chart, "replay", "step")
    if tid:
        tv(chart, "indicator", "toggle", tid, "--hidden")
    return {"poc": best.get("POC"), "vah": best.get("VAH"), "val": best.get("VAL")}

