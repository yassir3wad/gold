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


def read_smc(chart, tv=None):
    """Pull the SMC boxes + labels. Returns {present, boxes:[{high,low}], structure:[{text,price}],
    liquidity:[{text,price}]}. `present` is False when the indicator isn't on the chart (it's mandatory)."""
    tv = tv or _default_tv
    bx = tv(chart, "data", "boxes", "--study-filter", SMC_FILTER).get("studies", [])
    lb = tv(chart, "data", "labels", "--study-filter", SMC_FILTER).get("studies", [])
    boxes = bx[0].get("zones", []) if bx else []
    labels = lb[0].get("labels", []) if lb else []
    structure = [l for l in labels if l.get("text") in ("BOS", "CHoCH")]
    liquidity = [l for l in labels if l.get("text") in ("EQH", "EQL")]
    return {"present": bool(bx), "boxes": boxes, "structure": structure, "liquidity": liquidity}


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


def in_box(price, boxes, pad=0.0):
    """The order-block / FVG box containing price (± pad), or None."""
    return next((b for b in boxes if b["low"] - pad <= price <= b["high"] + pad), None)


def near_level(price, levels, tol):
    return any(abs(price - lv) <= tol for lv in levels)


def confluence(price, side, smc, tol, trendlines=None):
    """Confluence score added to the trade grade (on top of our own zones): +1 in an SMC order-block/FVG,
    +1 near a BOS/CHoCH, +1 near EQH/EQL liquidity, +1 near an Auto-Trendline. Returns {score, reasons}."""
    score = 0; reasons = []
    if in_box(price, smc.get("boxes", [])):
        score += 1; reasons.append("SMC order-block/FVG")
    if near_level(price, [s["price"] for s in smc.get("structure", [])], tol):
        score += 1; reasons.append("SMC BOS/CHoCH")
    if near_level(price, [l["price"] for l in smc.get("liquidity", [])], tol):
        score += 1; reasons.append("SMC liquidity (EQH/EQL)")
    if near_level(price, trendlines or smc.get("trendlines", []), tol):
        score += 1; reasons.append("Auto-Trendline")
    return {"score": score, "reasons": reasons}
