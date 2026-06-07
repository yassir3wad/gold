#!/usr/bin/env python3
"""Draw a symbol's HTF zones (from zones_<sym>.json) onto its chart as shaded boxes + labels.
  python3 draw_zones.py --symbol XAUUSD
Green = support, red = resistance. Pins to the symbol's window via TV_CHART (so it draws on the right chart)."""
import subprocess, json, os, sys
TVDIR = os.path.expanduser("~/tradingview-mcp")
SYM = "XAUUSD"
TAG = "AUTO-ZONE"
if "--symbol" in sys.argv:
    try: SYM = sys.argv[sys.argv.index("--symbol")+1].upper()
    except Exception: pass
cfg = {}
try:
    allc = json.load(open(os.path.join(TVDIR, "instruments.json"))); cfg = {**allc.get("_default", {}), **allc.get(SYM, {})}
except Exception: pass
if cfg.get("chart"): os.environ["TV_CHART"] = str(cfg["chart"])

def tv(*a):
    r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=30)
    try: return json.loads(r.stdout)
    except Exception: return {}

def lab_of(raw, side):
    inner = raw.split("(")[-1].rstrip(")") if "(" in raw else side
    return ("🟥 R " if side == "R" else "🟩 S ") + inner.replace(", ", " ") + f" [{TAG}]"

def clear_zones(chart=None):
    env = dict(os.environ)
    if chart:
        env["TV_CHART"] = chart
    try:
        r = subprocess.run(["node", "src/cli/index.js", "draw", "list"], cwd=TVDIR, capture_output=True, text=True, timeout=30, env=env)
        items = json.loads(r.stdout).get("drawings", []) if r.stdout.strip() else []
        n = 0
        for it in items:
            if TAG in json.dumps(it):
                eid = it.get("id") or it.get("entity_id")
                if eid:
                    subprocess.run(["node", "src/cli/index.js", "draw", "remove", "--id", str(eid)],
                                   cwd=TVDIR, env=env, timeout=20)
                    n += 1
        return n
    except Exception as e:
        return {"error": str(e)}

def main():
    z = json.load(open(os.path.join(TVDIR, f"zones_{SYM.lower()}.json")))
    b = tv("ohlcv", "-n", "240").get("bars", [])
    if not b: print("no bars"); return
    t0 = b[0]["time"]; t1 = b[-1]["time"] + 3600*2; tl = b[int(len(b)*0.15)]["time"]
    clear_zones()
    def box(lo, hi, lab, col):
        tv("draw", "shape", "--type", "rectangle", "--price", str(hi), "--time", str(t0),
           "--price2", str(lo), "--time2", str(t1),
           "--overrides", json.dumps({"color": col, "backgroundColor": col, "transparency": 85, "linewidth": 1}))
        tv("draw", "shape", "--type", "text", "--price", str(round((lo+hi)/2, 5)), "--time", str(tl),
           "--text", lab, "--overrides", json.dumps({"color": col, "fontsize": 12, "bold": True}))
    n = 0
    for lo, hi, raw in z.get("htf_r", [])[:4]:
        box(lo, hi, lab_of(raw, "R"), "#ef5350"); n += 1
    for lo, hi, raw in z.get("htf_s", [])[:4]:
        box(lo, hi, lab_of(raw, "S"), "#26a69a"); n += 1
    print(f"drew {n} zones on {SYM} (price {z.get('price')})")

if __name__ == "__main__":
    main()
