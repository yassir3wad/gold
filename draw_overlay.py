#!/usr/bin/env python3
"""Draw the engine's value-area + SMC overlay on the chart so the level map is VISIBLE:
  - prior-day POC / VAH / VAL as horizontal lines, labeled with price + Level State (va_state)
  - single-print (SP) zones as boxes (target levels)
  - SMC order-block / FVG boxes near price (read from the LuxAlgo indicator), colored by side

`overlay_specs(...)` is the PURE decision of WHAT to draw (testable). `draw_overlay(...)` executes it and
tracks the entity ids it created in a state file so the next refresh removes ONLY our shapes — never the
user's own drawings (so it can run every loop tick on the live chart).
"""
import subprocess, os, json, time

TVDIR = os.path.expanduser("~/tradingview-mcp")
STATE = os.path.expanduser("~/.tv_overlay_ids.json")   # entity ids we drew (per chart) — refresh removes only these

# colors (match draw_review's value-area palette)
POC_C = "rgba(240,220,40,0.95)"    # yellow
VAH_C = "rgba(70,130,240,0.95)"    # blue
VAL_C = "rgba(180,90,240,0.95)"    # purple
SP_C  = "rgba(255,170,60,0.85)"    # orange
OB_DEMAND_C = "rgba(0,200,90,0.85)"   # green (bullish OB below price)
OB_SUPPLY_C = "rgba(240,70,70,0.85)"  # red (bearish OB above price)
OB_NEUTRAL_C = "rgba(150,150,150,0.8)"
# NOTE: Auto Trendlines are NOT drawn here — the TradingView indicator already draws them. We only READ
# them (multi-TF) for confluence; see smc.read_trendlines / scalp_fast.


def overlay_specs(price, va, va_states, sp_zones, smc_boxes, band, va_date=None):
    """Return a list of draw specs (pure). Each spec:
      {type:'hline', kind, price, label, color}              — a horizontal level
      {type:'rect',  kind, price(hi), price2(lo), label, color}  — a zone/box
    `va` = {vah,val,poc}; `va_states` = {'VAH':state,...}; `sp_zones` = [[lo,hi],...];
    `smc_boxes` = [{high,low},...]; `band` = price half-window around `price` for keeping OBs;
    `va_date` = the value area's date (YYYY-MM-DD) — labels show the DATE, not the price (price is on the axis)."""
    out = []
    md = (va_date or "")[5:] if va_date else ""   # MM-DD
    # prior-day value-area lines, labeled with the DATE + Level State
    for kind, color in (("POC", POC_C), ("VAH", VAH_C), ("VAL", VAL_C)):
        p = va.get(kind.lower()) if kind != "POC" else va.get("poc")
        if p is None:
            continue
        st = (va_states or {}).get(kind)
        lab = f"prev{kind}" + (f" {md}" if md else "") + (f" [{st}]" if st else "")
        out.append({"type": "hline", "kind": kind, "price": p, "label": lab, "color": color})
    # single-print zones (target levels)
    for lo, hi in (sp_zones or []):
        out.append({"type": "rect", "kind": "SP", "price": hi, "price2": lo, "label": "SP", "color": SP_C})
    # SMC order blocks near price, colored by side relative to price
    for bx in (smc_boxes or []):
        hi, lo = bx.get("high"), bx.get("low")
        if hi is None or lo is None:
            continue
        if hi < price - band or lo > price + band:   # entirely outside the near-price window
            continue
        if hi <= price:        # whole box below price -> demand
            kind, color = "OB-demand", OB_DEMAND_C
        elif lo >= price:      # whole box above price -> supply
            kind, color = "OB-supply", OB_SUPPLY_C
        else:                  # straddles price
            kind, color = "OB", OB_NEUTRAL_C
        out.append({"type": "rect", "kind": kind, "price": hi, "price2": lo, "label": "OB", "color": color})
    return out


def _tv(chart, *a):
    env = dict(os.environ)
    if chart:
        env["TV_CHART"] = chart
    try:
        r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=30, env=env)
        return json.loads(r.stdout) if r.stdout.strip() else {}
    except Exception:
        return {}


def _clear_ours(chart):
    """Remove only the entity ids we drew last time (recorded in STATE) — leaves the user's drawings."""
    try:
        ids = json.load(open(STATE)).get(chart or "_", [])
    except Exception:
        ids = []
    for eid in ids:
        _tv(chart, "draw", "remove", "--id", str(eid))


def _save_ids(chart, ids):
    try:
        d = json.load(open(STATE))
    except Exception:
        d = {}
    d[chart or "_"] = ids
    try:
        json.dump(d, open(STATE, "w"))
    except Exception:
        pass


def _recent(chart, min_interval):
    if min_interval <= 0:
        return False
    try:
        ts = json.load(open(STATE)).get((chart or "_") + ":ts", 0)
    except Exception:
        ts = 0
    return (time.time() - ts) < min_interval


def draw_overlay(chart, price, va, va_states, sp_zones, smc_boxes, band, t0=None, t1=None, min_interval=0, va_date=None):
    """Refresh the overlay on `chart`: remove our previous shapes, draw the current specs, record new ids.
    `t0`/`t1` = bar-time anchors (hlines/rects need a time); pass the visible range's start/end.
    `min_interval` (s) throttles redraws so the live loop doesn't flicker the chart every tick; returns -1
    when skipped for throttle."""
    if _recent(chart, min_interval):
        return -1
    _clear_ours(chart)
    specs = overlay_specs(price, va, va_states, sp_zones, smc_boxes, band, va_date=va_date)
    new_ids = []
    for s in specs:
        lab = s["label"]   # shapes are tracked by entity id (STATE), so no visible tag is needed
        if s["type"] == "hline":
            r = _tv(chart, "draw", "shape", "--type", "horizontal_line", "--price", f"{s['price']}",
                    "--time", str(int(t1 or t0 or 0)), "--text", lab,
                    "--overrides", json.dumps({"linecolor": s["color"], "linewidth": 2, "linestyle": 0}))
        else:
            r = _tv(chart, "draw", "shape", "--type", "rectangle", "--price", f"{s['price']}", "--time", str(int(t0 or 0)),
                    "--price2", f"{s['price2']}", "--time2", str(int(t1 or t0 or 0)), "--text", lab,
                    "--overrides", json.dumps({"color": s["color"], "backgroundColor": s["color"], "transparency": 88, "linewidth": 1}))
        eid = (r or {}).get("id") or (r or {}).get("entity_id")
        if eid:
            new_ids.append(eid)
    _save_ids(chart, new_ids)
    return len(new_ids)
