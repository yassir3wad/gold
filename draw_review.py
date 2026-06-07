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
    ap.add_argument("--date", required=True)
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
    tv(CH, "replay", "start", "--date", a.date); time.sleep(5)
    tv(CH, "draw", "clear")
    drawn = {"demand": 0, "supply": 0, "KL": 0, "support": 0, "resistance": 0, "va": 0, "smc": 0}
    log = {"date": a.date, "chart": CH, "price": None, "zones": [], "sr": [], "va": [], "smc": {}}
    cur_price = None
    anchor_t = None   # a recent (cursor) bar time — REQUIRED to anchor horizontal_line draws
    sr = []   # (price, kind 'H'/'L', tf-label) horizontal support/resistance LEVELS

    # --- buy/sell ZONES (4h + 1h) — collect all VALID, then prioritize + dedupe + cap ---
    zones = []
    for tf, n, lab in [("240", 80, "4H"), ("60", 160, "1H")]:
        b = bars_tf(CH, tf, n)
        if not b:
            continue
        t1 = b[-1]["time"]; cur_price = b[-1]["close"]; anchor_t = t1
        for z in Z.mark_key_levels(b, left=2, right=2, lookback=20):
            if z["valid"]:
                c = b[z["i"]]
                strong = (Z.big_candle(b, z["i"], 20) and Z.small_opposite_wick(c)
                          and Z.has_direction_wick(c) and Z.volume_fib(b, z["i"], 20))
                zones.append({**z, "t1": t1, "tf": lab, "strong_lvl": strong, "green": c["close"] > c["open"]})
        for x in Z.sr_levels(b, lookback=20):
            sr.append((x["price"], x["role"], x["flipped"], lab))

    # drop a lower-TF (1h) zone if a higher-TF (4h) zone fully covers it (100% containment)
    hi_tf = [z for z in zones if z["tf"] == "4H"]
    zones = [z for z in zones if not (z["tf"] == "1H" and
             any(h["lo"] <= z["lo"] and h["hi"] >= z["hi"] for h in hi_tf))]

    zmid = lambda z: (z["lo"] + z["hi"]) / 2
    # buy/sell zones don't care about volume/color — only KEY LEVEL (BOS) ranks them; then nearest to price
    zones.sort(key=lambda z: (0 if z["key_level"] else 1, abs(zmid(z) - cur_price)))
    seen = []; nbuy = nsell = 0
    for z in (zones if "zones" in LAYERS else []):
        mid = zmid(z)
        if any(abs(mid - q) < 15 for q in seen):
            continue
        # role by position; but if the origin candle is a STRONG level candle (big + volume + small wick),
        # it's a support/resistance ZONE (green->support, red->resistance), not a generic buy/sell zone.
        buy = z["hi"] < cur_price if (z["hi"] < cur_price or z["lo"] > cur_price) else (z["kind"] == "demand")
        if z.get("strong_lvl"):
            role = "support" if z["green"] else "resistance"
        else:
            role = "buy zone" if buy else "sell zone"
        if (buy and nbuy >= 5) or (not buy and nsell >= 5):
            continue
        flipped = (buy and z["kind"] == "supply") or (not buy and z["kind"] == "demand")
        # KL is a property of the buy/sell ZONE tier — NOT the support/resistance LINE tier. A zone whose
        # origin is a strong level candle is labeled support/resistance and must never carry a "KL" tag.
        kl = z["key_level"] and not flipped and not z.get("strong_lvl")
        flag = " (flip)" if flipped else (f" KL {z['score']}" if kl else "")
        ov = (GREEN_KL if kl else GREEN) if buy else (RED_KL if kl else RED)
        right_edge = z["t1"] + 50 * 4 * 3600   # extend boxes ~50 4h-bars into the empty right side
        rect(CH, z["time"], z["lo"], right_edge, z["hi"], f"{z['tf']} {role}{flag}", ov)
        log["zones"].append({"tf": z["tf"], "role": role, "lo": z["lo"], "hi": z["hi"], "mid": round(mid, 2),
                             "key_level": bool(kl), "score": z.get("score"), "flip": bool(flipped)})
        seen.append(mid); drawn["demand" if buy else "supply"] += 1
        if kl: drawn["KL"] += 1
        nbuy += buy; nsell += (not buy)

    # --- support / resistance LEVELS (big high-volume candle; role flips on break) ---
    # keep only the nearest few that are ACTIVE: support below price, resistance above price.
    def draw_sr(role, color, below):
        cand = sorted({(p, fl, l) for p, r, fl, l in sr if r == role and ((p < cur_price) == below)},
                      key=lambda x: abs(x[0] - cur_price))
        seen = []
        for p, fl, l in cand:
            if any(abs(p - q) < 15 for q in seen):
                continue
            seen.append(p)
            hline(CH, p, f"{role.capitalize()} {l}" + (" flip" if fl else ""), color, anchor_t)
            log["sr"].append({"role": role, "price": p, "tf": l, "flip": bool(fl)})
            drawn[role] += 1
            if len(seen) >= 4:
                break
    if cur_price and "sr" in LAYERS:
        draw_sr("support", SUP, True)
        draw_sr("resistance", RES, False)

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
    out = f"/tmp/review_{a.date}.json"; json.dump(log, open(out, "w"), indent=1)
    print(f"drawn on {CH} @ {a.date}: {drawn}\nlog: {out}")


if __name__ == "__main__":
    main()
