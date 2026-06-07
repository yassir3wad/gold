#!/usr/bin/env python3
"""Read the LuxAlgo 'Smart Money Concepts' indicator off the chart and score a signal's confluence with it.
MANDATORY input (the indicator must be on every chart): order-block / FVG boxes, BOS/CHoCH structure, and
EQH/EQL liquidity. Each SMC element a signal aligns with is a '+' on the trade grade — on TOP of our own
zones (zones_sd). Date-faithful in replay (the indicator recomputes on the historical bars).
"""
import subprocess, os, json, time

TVDIR = os.path.expanduser("~/tradingview-mcp")
SMC_FILTER = "Smart Money"


def _default_tv(chart, *a):
    env = dict(os.environ)
    if chart:
        env["TV_CHART"] = chart
    try:
        r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=40, env=env)
        return json.loads(r.stdout)
    except Exception:
        return {}


# Label texts LuxAlgo draws (matched case-insensitively — the indicator emits mixed case e.g. 'CHoCH').
_STRUCTURE_TAGS = ("BOS", "CHOCH")                                  # break-of-structure lines
_LIQUIDITY_TAGS = ("EQH", "EQL")                                    # equal-highs/lows liquidity
_SWING_TAGS = ("STRONG HIGH", "WEAK HIGH", "STRONG LOW", "WEAK LOW")  # trailing strong/weak swing extremes (default-on)


def dedup_levels(items, tol=0.0):
    """Collapse labels whose prices cluster within `tol`. LuxAlgo's default Mode='Historical' keeps EVERY
    past BOS/CHoCH line, so many sit at ~the same level; this stops stale repeats from cluttering the list.
    Greedy: sort by price, keep the first of each cluster. Returns a filtered list (original dicts)."""
    out = []
    for it in sorted(items, key=lambda x: x.get("price", 0)):
        if not out or abs(it.get("price", 0) - out[-1].get("price", 0)) > tol:
            out.append(it)
    return out


def read_smc(chart, tv=None, dedup_tol=0.0, max_labels=600):
    """Pull the SMC boxes + labels. Returns {present, boxes:[{high,low}], structure:[{text,price}],
    liquidity:[{text,price}], swings:[{text,price}]}. `structure`=BOS/CHoCH, `liquidity`=EQH/EQL,
    `swings`=Strong/Weak High/Low (default-on trailing extremes — protected liquidity a scalp targets).
    Matching is case-insensitive; `structure` is deduped within `dedup_tol`. `present` is False when the
    indicator isn't on the chart (it's mandatory). `max_labels` lifts the reader's default 50-label cap —
    Historical mode emits 500+ labels, so the Strong/Weak swings get truncated away without this."""
    tv = tv or _default_tv
    # NOTE: the CLI flag is --filter (NOT --study-filter — that was silently ignored, so reads fell back to
    # study[0], which on charts with a "Trading Sessions" indicator returned ITS boxes/labels, not SMC's).
    bx = tv(chart, "data", "boxes", "--filter", SMC_FILTER).get("studies", [])
    lb = tv(chart, "data", "labels", "--filter", SMC_FILTER, "--max", str(max_labels)).get("studies", [])
    # Pick the study that actually IS the SMC indicator — the filter can still return >1 study and order is
    # not guaranteed, so never blindly take [0].
    def _pick(studies, key):
        for s in studies:
            if SMC_FILTER.upper() in (s.get("name", "") or "").upper():
                return s.get(key, [])
        return []
    boxes = _pick(bx, "zones")
    labels = _pick(lb, "labels")
    def _tag(l): return (l.get("text") or "").strip().upper()
    structure = dedup_levels([l for l in labels if _tag(l) in _STRUCTURE_TAGS], dedup_tol)
    liquidity = [l for l in labels if _tag(l) in _LIQUIDITY_TAGS]
    swings = [l for l in labels if _tag(l) in _SWING_TAGS]
    present = any(SMC_FILTER.upper() in (s.get("name", "") or "").upper() for s in (bx + lb))
    return {"present": present, "boxes": boxes, "structure": structure,
            "liquidity": liquidity, "swings": swings}


class SMCMissing(RuntimeError):
    """Raised when the LuxAlgo Smart Money Concepts indicator isn't on the chart (it's mandatory)."""


def assert_smc(chart, tv=None):
    """Validate the SMC indicator IS on the chart; raise SMCMissing if not. Call before reading/using SMC so
    a missing indicator fails LOUD instead of silently returning empty (which previously read as 'no SMC')."""
    studies = ((tv or _default_tv)(chart, "state") or {}).get("studies", [])
    if not _find_tid(studies, SMC_FILTER):
        raise SMCMissing(f"Smart Money Concepts (LuxAlgo) indicator is NOT on chart '{chart or 'default'}'. "
                         "Add it before trading/refresh — SMC data comes from the indicator.")


def value_zones(swings):
    """Premium / Equilibrium / Discount from the current swing range (Strong/Weak High/Low). The range is the
    span of swing prices; premium = upper half (sell zone), discount = lower half (buy zone). None if <2 swings.
    Returns {hi, lo, eq, premium:[eq,hi], discount:[lo,eq]}. Pure (testable)."""
    ps = [s.get("price") for s in (swings or []) if s.get("price") is not None]
    if len(ps) < 2:
        return None
    hi, lo = max(ps), min(ps); eq = round((hi + lo) / 2, 5)
    return {"hi": hi, "lo": lo, "eq": eq, "premium": [eq, hi], "discount": [lo, eq]}


def read_smc_mtf(chart, price, tfs=("240", "60", "15"), base_tf="5", band=200.0, tv=None, render_wait=3.0):
    """Read the SMC indicator across MULTIPLE timeframes (4h/1h/15m) and return a per-TF snapshot, filtered to
    within `band` price-units of `price` (the far full-history boxes/labels drop out; only near-price ones,
    which are stable, remain — swings are KEPT regardless since they define the range). Switches TF, restores
    `base_tf`, hides the indicator after. Raises SMCMissing if absent. tv injectable for tests (returns {}).
    Per-TF: {boxes:[{high,low,side}], structure, liquidity, swings, premium, discount, equilibrium}."""
    _tv = tv or _default_tv
    live = tv is None
    assert_smc(chart, tv=_tv)
    sid = _find_tid((_tv(chart, "state") or {}).get("studies", []), SMC_FILTER)
    _tv(chart, "indicator", "toggle", sid, "--visible", "true")
    out = {}
    for tf in tfs:
        _tv(chart, "timeframe", str(tf))
        if live and render_wait:
            time.sleep(render_wait)
        m = read_smc(chart, tv=tv)
        near = lambda xs: [{"text": x["text"], "price": round(x["price"], 5)} for x in xs
                           if x.get("price") is not None and abs(x["price"] - price) <= band]
        boxes = [{"high": round(b["high"], 5), "low": round(b["low"], 5),
                  "side": "demand" if b["high"] <= price else "supply" if b["low"] >= price else "straddle"}
                 for b in m["boxes"]
                 if b.get("high") is not None and b["high"] >= price - band and b["low"] <= price + band]
        vz = value_zones(m["swings"])
        out[str(tf)] = {"boxes": boxes, "structure": near(m["structure"]), "liquidity": near(m["liquidity"]),
                        "swings": [{"text": s["text"], "price": round(s["price"], 5)} for s in m["swings"]],
                        "premium": vz["premium"] if vz else None, "discount": vz["discount"] if vz else None,
                        "equilibrium": vz["eq"] if vz else None}
    _tv(chart, "indicator", "toggle", sid, "--hidden")
    _tv(chart, "timeframe", str(base_tf))
    return out


def mtf_signal(price, side, smc_block, tol, weights=(("240", 3), ("60", 2), ("15", 1))):
    """Consider the STORED multi-TF SMC snapshot (zones_xauusd.json 'smc' block) for a `side` trade at `price`.
    Pure (testable). Returns {score, reasons, zone, aligned}:
      - box confluence: + weight[tf] if price is in a box on the FAVOURABLE side (demand for LONG / supply for
        SHORT) on that TF — HTF weighted (4h>1h>15m).
      - swing confluence: + a smaller weight if price is near a Strong/Weak swing on that TF.
      - zone: premium / discount / equilibrium from the HIGHEST TF range present (eq band = ±tol).
      - aligned: True if the trade is on the right side of the range (LONG in discount / SHORT in premium)."""
    tf = (smc_block or {}).get("tf", {}) or {}
    score = 0; reasons = []
    want = "demand" if side == "LONG" else "supply"
    for tfk, w in weights:
        d = tf.get(tfk)
        if not d:
            continue
        if any(b.get("side") == want and (b["low"] - tol) <= price <= (b["high"] + tol) for b in d.get("boxes", [])):
            score += w; reasons.append(f"{tfk}m OB {want}")
        if any(abs(price - s.get("price", 0)) <= tol for s in d.get("swings", [])):
            score += max(1, w // 2); reasons.append(f"{tfk}m swing")
    zone = None; aligned = None
    for tfk, _ in weights:                               # premium/discount from the highest TF that has a range
        d = tf.get(tfk)
        if d and d.get("equilibrium") is not None:
            eq = d["equilibrium"]
            zone = "equilibrium" if abs(price - eq) <= tol else ("discount" if price < eq else "premium")
            aligned = (side == "LONG" and zone == "discount") or (side == "SHORT" and zone == "premium")
            break
    return {"score": score, "reasons": reasons, "zone": zone, "aligned": aligned}


TRENDLINE_FILTER = "Auto Trendlines"


# JS run in the chart page: reads the Auto Trendlines DIAGONAL lines from the chart model and projects each
# to the current bar, keeping only those within `band` of price (the line-reader can't extract diagonals,
# so we go straight to the primitives). Date-faithful: xnow = the replay cursor bar.
_TL_JS = r"""(function(){
  var chart=window.TradingViewApi._activeChartWidgetWV.value()._chartWidget;
  var bars=chart.model().mainSeries().bars(); var xnow=bars.lastIndex();
  var px=bars.valueAt(xnow); var price=px?px[4]:0;
  var sources=chart.model().model().dataSources(); var out=[];
  for(var si=0;si<sources.length;si++){var s=sources[si]; if(!s.metaInfo) continue;
    var m=s.metaInfo(); var name=m.description||m.shortDescription||'';
    if(name.indexOf('Auto Trendlines')===-1) continue;
    var g=s._graphics; if(!g||!g._primitivesCollection) continue;
    var outer=g._primitivesCollection.dwglines; if(!outer) continue;
    var inner=outer.get('lines'); if(!inner) continue;
    var coll=inner.get(false); if(!coll||!coll._primitivesDataById) continue;
    coll._primitivesDataById.forEach(function(v){
      if(v.y1!=null&&v.y2!=null&&v.y1!==v.y2&&v.x1!=null&&v.x2!=null&&v.x1!==v.x2){
        var val=v.y1+(v.y2-v.y1)*(xnow-v.x1)/(v.x2-v.x1);
        if(price>0&&Math.abs(val-price)<price*0.06) out.push(Math.round(val*100)/100);}});}
  out.sort(function(a,b){return a-b;}); return {price:price, levels:out};})()"""


def read_trendlines(chart, tv=None):
    """Auto Trendlines (TradingView indicator) — its DIAGONAL lines projected to the current bar, near price.
    Read via raw chart-model eval (the pine line-reader can't see diagonals). Returns a list of price levels;
    empty if the indicator isn't on the chart. tv injectable for tests (returns []) ."""
    if tv is not None:
        try:
            r = tv(chart, "ui", "eval", _TL_JS)
            return (r or {}).get("result", {}).get("levels", [])
        except Exception:
            return []
    env = dict(os.environ)
    if chart:
        env["TV_CHART"] = chart
    try:
        r = subprocess.run(["node", "src/cli/index.js", "ui", "eval", _TL_JS], cwd=TVDIR,
                           capture_output=True, text=True, timeout=40, env=env)
        return json.loads(r.stdout).get("result", {}).get("levels", [])
    except Exception:
        return []


class TrendlinesMissing(RuntimeError):
    """Raised when the Auto Trendlines indicator isn't enabled on the chart (it's mandatory)."""


def assert_trendlines(chart, tv=None):
    """Validate the Auto Trendlines indicator IS on the chart; raise TrendlinesMissing if not. Call before any
    charting/trading that relies on trendline confluence so a missing indicator fails LOUD, not silent-empty."""
    _tv = tv or _default_tv
    studies = (_tv(chart, "state") or {}).get("studies", [])
    if not _find_tid(studies, "Auto Trendlines"):
        raise TrendlinesMissing(
            f"Auto Trendlines indicator is NOT enabled on chart '{chart or 'default'}'. "
            "Add it to the chart before charting/trading — trendline confluence is mandatory.")


def read_trendlines_mtf(chart, tfs=("240", "60", "15"), base_tf="5", tv=None, render_wait=3.0, dedup_tol=1.0):
    """Read the Auto Trendlines indicator's projected levels across MULTIPLE timeframes (4h, 1h, 15m) and
    return them as one deduped list of price levels for confluence. The indicator recomputes per chart TF, so
    we switch TF, let it render, read, and restore the execution TF (`base_tf`). The indicator must be VISIBLE
    to read, so we show it for the sweep and hide it after. tv injectable for tests (returns [])."""
    _tv = tv or _default_tv
    live = tv is None
    studies = (_tv(chart, "state") or {}).get("studies", [])
    tl_id = _find_tid(studies, "Auto Trendlines")
    if not tl_id:                       # mandatory — fail loud, don't silently return []
        raise TrendlinesMissing(
            f"Auto Trendlines indicator is NOT enabled on chart '{chart or 'default'}'. Add it before trading.")
    _tv(chart, "indicator", "toggle", tl_id, "--visible", "true")
    levels = []
    for tf in tfs:
        _tv(chart, "timeframe", str(tf))
        lv = []
        for i in range(2):                          # retry once on empty (render lag after a TF switch)
            if live and render_wait:
                time.sleep(render_wait)
            lv = read_trendlines(chart, tv=tv)
            if lv:
                break
        levels += lv
    if tl_id:
        _tv(chart, "indicator", "toggle", tl_id, "--hidden")
    _tv(chart, "timeframe", str(base_tf))   # restore execution TF
    # dedup the float levels (near-duplicates across TFs collapse to one)
    out = []
    for p in sorted({round(x, 5) for x in levels if x is not None}):
        if not out or p - out[-1] > dedup_tol:
            out.append(p)
    return out


def read_htf_context(chart, smc_tfs=("240", "60"), tl_tf="240", base_tf="1", tv=None, render_wait=4.0):
    """Read the structural confluence on the higher TFs: SMC on each of `smc_tfs` (4h major + 1h scalp
    structure) and Auto Trendlines on `tl_tf` (4h). Restores the execution TF. Cached per scan by the engine.
    NOTE: the SMC indicator needs a few seconds to RENDER after a TF switch — we wait `render_wait` before
    reading, else it returns empty. Returns {smc_by_tf, trendlines, present}."""
    _tv = tv or _default_tv
    live = tv is None                              # only sleep for real reads (tests inject tv)
    smc_by_tf = {}
    for tf in smc_tfs:
        _tv(chart, "timeframe", str(tf))
        if live and render_wait:
            time.sleep(render_wait)
        smc_by_tf[str(tf)] = read_smc(chart, tv=tv)
    _tv(chart, "timeframe", str(tl_tf))
    if live and render_wait:
        time.sleep(render_wait)
    trendlines = read_trendlines(chart, tv=tv)
    _tv(chart, "timeframe", str(base_tf))   # restore execution TF (1m live / 5m backtest)
    return {"smc_by_tf": smc_by_tf, "trendlines": trendlines,
            "present": any(s.get("present") for s in smc_by_tf.values())}


def grade_confluence(price, side, ctx, tol):
    """Aggregate confluence across the HTF context: SMC alignment on each TF (4h, 1h) + Auto-Trendline once.
    Each '+' raises the trade grade on top of our own zones. Returns {score, reasons}."""
    score = 0; reasons = []
    for tf, smc in ctx.get("smc_by_tf", {}).items():
        r = confluence(price, side, smc, tol)   # SMC only (trendlines handled once below)
        if r["score"]:
            score += r["score"]; reasons += [f"{tf}m {x}" for x in r["reasons"]]
    if near_level(price, ctx.get("trendlines", []), tol):
        score += 1; reasons.append("Auto-Trendline 4h")
    return {"score": score, "reasons": reasons}


def _find_tid(studies, name_substr):
    return next((s.get("id") for s in studies if name_substr in (s.get("name") or "")), None)


def read_chart_context(chart, tv=None, manage_visibility=True, render_wait=4.0, dedup_tol=0.0,
                       attempts=3, retry_wait=2.0):
    """Option A: read SMC + Auto Trendlines on the CURRENT chart (NO TF switch, no extra tabs). Since Pine
    indicators must be VISIBLE to read, we SHOW them → wait to render → read → HIDE — so the chart stays
    clean (we draw our own zones from the stored data) and the indicators don't constantly re-render. Cached
    by the engine and refreshed ~hourly. Returns {smc, trendlines, present}.

    Render timing is flaky: right after a show the model can read EMPTY (e.g. 0 boxes) and then 100+ on a
    re-read. So we RETRY (up to `attempts`) until SMC has data, instead of silently under-scoring confluence."""
    _tv = tv or _default_tv
    live = tv is None
    smc_id = tl_id = None
    if manage_visibility:
        studies = (_tv(chart, "state") or {}).get("studies", [])
        smc_id = _find_tid(studies, "Smart Money"); tl_id = _find_tid(studies, "Auto Trendlines")
        for tid in (smc_id, tl_id):
            if tid: _tv(chart, "indicator", "toggle", tid, "--visible", "true")
    smc = {"present": False, "boxes": [], "structure": [], "liquidity": [], "swings": []}
    trendlines = []
    for i in range(max(1, attempts)):
        if live and render_wait:
            time.sleep(render_wait if i == 0 else retry_wait)   # first wait = render; later = re-render lag
        s = read_smc(chart, tv=tv, dedup_tol=dedup_tol)
        t = read_trendlines(chart, tv=tv)
        if t:
            trendlines = t
        if s.get("present") and (s.get("boxes") or s.get("structure")):
            smc = s
            break                                                # got data — stop retrying
        smc = s                                                  # keep the latest (may still be empty)
    if manage_visibility:
        for tid in (smc_id, tl_id):
            if tid: _tv(chart, "indicator", "toggle", tid, "--hidden")   # hide again — store-and-hide
    return {"smc": smc, "trendlines": trendlines, "present": smc.get("present", False)}


def in_box(price, boxes, pad=0.0):
    """The order-block / FVG box containing price (± pad), or None."""
    return next((b for b in boxes if b["low"] - pad <= price <= b["high"] + pad), None)


def filter_near(ctx, price, band):
    """Keep only the SMC elements within `band` of `price`. LuxAlgo's default Mode=Historical emits the
    indicator's ENTIRE history (200+ boxes, 500+ labels spanning the whole chart); for a scalp only the
    handful at the working price matter. Used to de-clutter drawing/logging (confluence already credits
    near-price only). Accepts a read_chart_context dict {smc, trendlines, ...}; returns a filtered copy."""
    if not price:
        return ctx
    sm = dict(ctx.get("smc", {}))
    sm["boxes"] = [b for b in sm.get("boxes", []) if b["low"] - band <= price <= b["high"] + band]
    for k in ("structure", "liquidity", "swings"):
        sm[k] = [x for x in sm.get(k, []) if abs(x.get("price", 0) - price) <= band]
    tls = [t for t in ctx.get("trendlines", []) if abs(t - price) <= band]
    return {**ctx, "smc": sm, "trendlines": tls}


def near_level(price, levels, tol):
    return any(abs(price - lv) <= tol for lv in levels)


def confluence(price, side, smc, tol, trendlines=None):
    """Confluence score added to the trade grade (on top of our own zones): +1 in an SMC order-block/FVG,
    +1 near a BOS/CHoCH, +1 near EQH/EQL liquidity, +1 near a Strong/Weak High/Low, +1 near an
    Auto-Trendline. Returns {score, reasons}."""
    score = 0; reasons = []
    if in_box(price, smc.get("boxes", [])):
        score += 1; reasons.append("SMC order-block/FVG")
    if near_level(price, [s["price"] for s in smc.get("structure", [])], tol):
        score += 1; reasons.append("SMC BOS/CHoCH")
    if near_level(price, [l["price"] for l in smc.get("liquidity", [])], tol):
        score += 1; reasons.append("SMC liquidity (EQH/EQL)")
    if near_level(price, [s["price"] for s in smc.get("swings", [])], tol):
        score += 1; reasons.append("SMC strong/weak H/L")
    if near_level(price, trendlines or smc.get("trendlines", []), tol):
        score += 1; reasons.append("Auto-Trendline")
    return {"score": score, "reasons": reasons}
