#!/usr/bin/env python3
"""Draw the structural context for a given date so it can be reviewed by eye:
  - D / 4h / 1h supply-demand origin-candle zones (boxes; demand green, supply red)
  - prior-3-day value areas (POC / VAH / VAL, labeled with the date)
Pins to a dedicated chart; nothing wired into the engine. For visual review before integration.
    python3 draw_review.py --date 2026-06-01 --chart eFMec2F9
"""
import argparse, subprocess, os, json, time
import zones_sd as Z
import patterns as P
import smc as SMC
import tpo as TPO

TVDIR = os.path.expanduser("~/tradingview-mcp")
TAG = "REVIEW"


def tv(chart, *a):
    env = dict(os.environ); env["TV_CHART"] = chart
    try:
        return json.loads(subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR,
                                          capture_output=True, text=True, timeout=45, env=env).stdout)
    except Exception:
        return {}


def bars_tf(chart, tf, n):
    tv(chart, "timeframe", tf)
    return tv(chart, "ohlcv", "-n", str(n)).get("bars", [])


def rect(chart, t0, lo, t1, hi, label, ov):
    tv(chart, "draw", "shape", "--type", "rectangle", "--price", f"{lo}", "--time", str(int(t0)),
       "--price2", f"{hi}", "--time2", str(int(t1)), "--overrides", ov)
    tv(chart, "draw", "shape", "--type", "text", "--price", f"{hi}", "--time", str(int(t1)),
       "--text", f"{label} [{TAG}]")


def hline(chart, price, label, ov, t):
    # horizontal_line REQUIRES a finite --time anchor (else "point.time NaN" → silent fail). The line is
    # still full-width; the time only anchors its handle/label. `t` = a recent (cursor) bar time.
    tv(chart, "draw", "shape", "--type", "horizontal_line", "--price", f"{price}", "--time", str(int(t)),
       "--text", (f"{label} [{TAG}]" if label else f"[{TAG}]"), "--overrides", ov)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)   # backtest date (replay). Omit for LIVE mode (draws on the live chart at 'now', no replay).
    ap.add_argument("--chart", default="eFMec2F9")
    ap.add_argument("--display-tf", default="60")
    ap.add_argument("--symbol", default="PEPPERSTONE:XAUUSD")   # PEPPERSTONE has real volume (OANDA gold doesn't) → value areas + TPO work
    ap.add_argument("--layers", default="zones,sr,va")   # comma-list of layers to draw: zones,sr,va. SMC is NOT drawn — the LuxAlgo indicator draws itself; SMC is consumed as stored JSON (refresh_zones --with-smc) + used in scalp (mtf_signal). Pass --layers zones,sr,va,smc only to debug-overlay SMC.
    a = ap.parse_args(); CH = a.chart
    LAYERS = {x.strip() for x in a.layers.split(",") if x.strip()}
    # KL = bright/solid, normal zone = faint. demand=green, supply=red.
    GREEN_KL = json.dumps({"backgroundColor": "rgba(0,210,90,0.28)", "color": "rgba(0,230,100,0.95)"})
    GREEN    = json.dumps({"backgroundColor": "rgba(0,200,80,0.08)", "color": "rgba(0,200,80,0.45)"})
    RED_KL   = json.dumps({"backgroundColor": "rgba(240,60,60,0.28)", "color": "rgba(255,70,70,0.95)"})
    RED      = json.dumps({"backgroundColor": "rgba(230,60,60,0.08)", "color": "rgba(230,60,60,0.45)"})
    BLUE  = json.dumps({"linecolor": "rgba(70,130,220,0.8)", "linestyle": 2})
    GRAY  = json.dumps({"linecolor": "rgba(150,150,150,0.7)", "linestyle": 2})
    POC_C = json.dumps({"linecolor": "rgba(240,220,40,0.95)", "linestyle": 0, "linewidth": 2})    # POC = yellow
    VAH_C = json.dumps({"linecolor": "rgba(70,130,240,0.95)", "linestyle": 0, "linewidth": 2})    # VAH = blue
    VAL_C = json.dumps({"linecolor": "rgba(180,90,240,0.95)", "linestyle": 0, "linewidth": 2})    # VAL = purple

    SUP = json.dumps({"linecolor": "rgba(0,210,90,0.85)", "linestyle": 0, "linewidth": 2})   # support line (green)
    RES = json.dumps({"linecolor": "rgba(240,70,70,0.85)", "linestyle": 0, "linewidth": 2})   # resistance line (red)
    PURP = json.dumps({"linecolor": "rgba(180,120,255,0.85)", "linestyle": 2})   # SMC structure / liquidity / swings
    ORNG = json.dumps({"linecolor": "rgba(255,170,60,0.85)", "linestyle": 1})    # Auto-Trendline (projected to now)

    tv(CH, "symbol", a.symbol)
    if a.date:                                              # backtest: date-faithful replay
        tv(CH, "replay", "start", "--date", a.date); time.sleep(5)
    else:                                                   # LIVE: draw at 'now' (ensure no replay overlay)
        tv(CH, "replay", "stop"); time.sleep(1)
    tv(CH, "draw", "clear")
    drawn = {"demand": 0, "supply": 0, "KL": 0, "support": 0, "resistance": 0, "va": 0, "smc": 0}
    log = {"date": a.date, "chart": CH, "price": None, "zones": [], "sr": [], "va": [], "smc": {}}
    cur_price = None
    anchor_t = None   # a recent (cursor) bar time — REQUIRED to anchor horizontal_line draws

    # --- CLASSIC zones via the SHARED builder (zones_sd.build_classic_zones) so DRAWN == TRADED: the engine
    # (refresh_zones → scalp_fast) grades against EXACTLY these same zones. Bar counts match refresh_zones. ---
    b4 = bars_tf(CH, "240", 80); b1 = bars_tf(CH, "60", 160)
    if b1:
        cur_price = b1[-1]["close"]; anchor_t = b1[-1]["time"]
    elif b4:
        cur_price = b4[-1]["close"]; anchor_t = b4[-1]["time"]
    classic = Z.build_classic_zones([("4H", b4), ("1H", b1)], cur_price) if cur_price else {"zones": [], "sr": []}

    if "zones" in LAYERS:
        for z in classic["zones"]:
            buy = z["role"] in ("buy zone", "support")
            kl = z["kl"]
            ov = (GREEN_KL if kl else GREEN) if buy else (RED_KL if kl else RED)
            flag = " (flip)" if z["flip"] else (f" KL {z['score']}" if kl else "")
            right_edge = (z["t1"] or anchor_t) + 50 * 4 * 3600   # extend boxes ~50 4h-bars into the empty right side
            rect(CH, z["time"] or anchor_t, z["lo"], right_edge, z["hi"], f"{z['tf']} {z['role']}{flag}", ov)
            log["zones"].append(z)
            drawn["demand" if buy else "supply"] += 1
            if kl: drawn["KL"] += 1

    if cur_price and "sr" in LAYERS:
        for s in classic["sr"]:
            color = SUP if s["role"] == "support" else RES
            hline(CH, s["price"], f"{s['role'].capitalize()} {s['tf']}" + (" flip" if s["flip"] else ""), color, anchor_t)
            log["sr"].append(s)
            drawn[s["role"]] += 1

    b30 = bars_tf(CH, "30", 400)   # 30m for the TPO indicator read
    va_t = anchor_t or (int(b30[-1]["time"]) if b30 else None)   # time anchor required by horizontal_line
    # --- value areas: READ from the TPO indicator (POC=yellow / VAH=blue / VAL=purple, no labels) ---
    # Live this is correct; in replay the indicator's lines are stale (don't track the cursor) — known caveat.
    if va_t and "va" in LAYERS:
        for s in TPO.read_tpo_lines(CH):
            for price, ov in [(s.get("poc"), POC_C), (s.get("vah"), VAH_C), (s.get("val"), VAL_C)]:
                if price is None:
                    continue
                hline(CH, price, "", ov, va_t)   # no descriptive label, per request
                drawn["va"] += 1
            log["va"].append(s)

    # --- SMC confluence layer (LuxAlgo) — read into the LOG as data only (not drawn); keep Auto Trendlines on ---
    if "smc" in LAYERS:
        try:
            tv(CH, "timeframe", a.display_tf)   # read SMC on the display TF (1h)
            sctx = SMC.read_chart_context(CH, dedup_tol=8)
            sm = sctx.get("smc", {})
            log["smc"] = {"present": sctx.get("present"), "boxes": sm.get("boxes", []),
                          "structure": sm.get("structure", []), "liquidity": sm.get("liquidity", []),
                          "swings": sm.get("swings", []), "trendlines": sctx.get("trendlines", [])}
            # SMC kept as DATA only (in the log → confluence / engine) — NOT drawn on the chart (it flooded it).
            # Keep the Auto Trendlines indicator VISIBLE (its diagonal lines) — read_chart_context hid it.
            tlid = next((s["id"] for s in (tv(CH, "state") or {}).get("studies", []) if "Auto Trendlines" in (s.get("name") or "")), None)
            if tlid:
                tv(CH, "indicator", "toggle", tlid, "--visible", "true"); drawn["smc"] += 1
        except Exception as e:
            log["smc"] = {"error": str(e)}

    log["price"] = cur_price
    _tag = a.date or "live"
    out = f"/tmp/review_{_tag}.json"; json.dump(log, open(out, "w"), indent=1)
    print(f"drawn on {CH} @ {_tag}: {drawn}\nlog: {out}")


if __name__ == "__main__":
    main()
