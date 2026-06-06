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


_SP_X_TOL = 1   # SP labels sit at the VA anchor x (or +1 bar); residue from other sessions sits far away


def session_sp(labels):
    """From the TPO indicator's VERBOSE labels, return only the CURRENT session's single-print prices.
    The indicator draws exactly one VAH/VAL/POC label set (the current session) at a common bar `x`; that
    session's SP labels sit at the same x (±1 bar). During replay stepping, stale SP labels accumulate as
    orphaned-primitive residue at OTHER x's — we drop those by keeping only SP within `_SP_X_TOL` bars of
    the VA anchor. Returns a flat list of SP prices (group into zones with group_sp). Pure (testable)."""
    va_xs = [l.get("x") for l in labels
             if str(l.get("text", "")).strip() in ("VAH", "VAL", "POC") and l.get("x") is not None]
    if not va_xs:
        return []
    anchor = max(va_xs)   # the latest (rightmost) session = the one being harvested
    out = []
    for l in labels:
        if str(l.get("text", "")).strip() != "SP":
            continue
        x, p = l.get("x"), l.get("price")
        if x is not None and p is not None and abs(x - anchor) <= _SP_X_TOL:
            out.append(p)
    return out


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
CHART_SYMBOL = "PEPPERSTONE:XAUUSD"   # the pair the TPO harvest reads (set on the dedicated backtest tab)


def fetch_va(symbol, date, chart=None, tv=None, render_wait=8.0):
    """Read ONE day's POC/VAH/VAL off the TPO indicator. The daily session ROLLS OVER at ~22:00 UTC, so a
    day's finalized value area is only on screen in the window JUST BEFORE 22:00 (≈21:00–21:59): there the
    session is complete (POC present) AND still the current session whose VAH/VAL/POC TEXT labels are drawn.
    After 22:00 the labels switch to the next (empty) session. So we replay to `date` and step the cursor
    into that 21:xx window, then read the labels. The date is known from the cursor WE set — no bar-index
    dating. Returns {poc, vah, val} (None if the indicator hadn't rendered). For va_store fallback.

    Runs on the DEDICATED BACKTEST TAB (pass `chart` / TV_CHART = the backtest window id) so replay never
    touches the live chart. We pin the pair to PEPPERSTONE:XAUUSD and VERIFY it before trusting any read —
    if the tab isn't on XAUUSD we refuse (return incomplete) rather than harvest the wrong instrument.
    """
    tv = tv or _default_tv
    chart = chart or os.environ.get("TV_CHART", "")
    tv(chart, "symbol", CHART_SYMBOL)
    tv(chart, "timeframe", "30")
    sym = (tv(chart, "state") or {}).get("symbol") or ""
    if "XAUUSD" not in sym.upper():   # wrong pair on the tab -> don't harvest into the XAUUSD store
        return {"poc": None, "vah": None, "val": None, "sp": []}
    target = dt.datetime.strptime(date, "%Y-%m-%d").date()

    def cursor_dt():
        cu = (tv(chart, "replay", "status") or {}).get("current_date")
        return dt.datetime.utcfromtimestamp(cu) if cu else None

    def rolled(t):   # past the day's ~22:00 session close (or into the next day)
        return t is None or t.date() > target or (t.date() == target and t.hour >= SESSION_CLOSE_HOUR)

    def read_va():
        # VAH/VAL/POC: non-verbose read is reliable in replay (verbose returns empty when replaying a past
        # day — it only carries data for the latest/realtime session).
        nv = ((tv(chart, "data", "labels", "-f", TPO_FILTER, "-n", "600").get("studies", []) or [{}])[0]).get("labels", [])
        m = {}
        for l in nv:
            t = str(l.get("text", "")).strip()
            if t in ("VAH", "VAL", "POC") and t not in m:
                m[t] = l.get("price")
        if not all(k in m for k in ("VAH", "VAL", "POC")):
            return None
        # SP: needs the bar `x` to scope to the current session (SP labels accumulate replay residue at other
        # x's). x only comes from the verbose read, which only returns data for the latest session. So we
        # scope SP when verbose has data, and DROP SP otherwise (fail-safe — never store a neighbour's phantom
        # single prints into the live engine). Past-day backfills get no SP; the daily harvest of the
        # just-closed (latest) session gets clean, session-scoped SP.
        vb = ((tv(chart, "data", "labels", "-f", TPO_FILTER, "-n", "600", "--verbose").get("studies", []) or [{}])[0]).get("labels", [])
        m["SP"] = session_sp(vb) if vb else []
        return m

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
    # ONLY read while the cursor is CONFIRMED on the target date. Replay's current_date intermittently comes
    # back None (or replay fails to navigate); if we read then, we'd capture the realtime/latest session and
    # mislabel it as `date` (silent corruption). So: None cursor -> step & retry, never read; date < target ->
    # step forward; date == target -> read (keep last complete); date > target -> done. If we never confirm
    # the target date, `best` stays empty and we return an INCOMPLETE result (the caller won't store it).
    best = {}; confirmed = False; first = True
    for _ in range(40):
        t = cursor_dt()
        if t is None:                       # can't confirm where we are — don't trust any on-screen read
            tv(chart, "replay", "step"); time.sleep(2.0); continue
        if t.date() > target:
            break
        if t.date() < target:               # replay landed before the target day — advance
            tv(chart, "replay", "step"); continue
        time.sleep(render_wait if first else 3.0); first = False
        confirmed = True
        m = read_va()
        if m:
            best = m
        tv(chart, "replay", "step")
    if tid:
        tv(chart, "indicator", "toggle", tid, "--hidden")
    if not confirmed:                       # never reached the target date — refuse to return a mislabeled VA
        return {"poc": None, "vah": None, "val": None, "sp": []}
    return {"poc": best.get("POC"), "vah": best.get("VAH"), "val": best.get("VAL"),
            "sp": group_sp(best.get("SP", []))}


def group_sp(prices, max_gap=None):
    """Group single-print LEVELS into [lo, hi] zones: adjacent SP levels (within ~2.5 tick-spacings) belong
    to the same single-print zone. `max_gap` auto-derives from the tightest level spacing if not given.
    Pure (testable). Returns sorted [[lo, hi], ...]."""
    ps = sorted({round(p, 2) for p in prices if p is not None})
    if not ps:
        return []
    if max_gap is None:
        gaps = [ps[i + 1] - ps[i] for i in range(len(ps) - 1)]
        max_gap = (min(gaps) * 2.5) if gaps else 0.0
    zones = [[ps[0], ps[0]]]
    for p in ps[1:]:
        if p - zones[-1][1] <= max_gap:
            zones[-1][1] = p
        else:
            zones.append([p, p])
    return zones

