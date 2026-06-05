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


def hline(chart, price, label, ov):
    tv(chart, "draw", "shape", "--type", "horizontal_line", "--price", f"{price}",
       "--text", f"{label} [{TAG}]", "--overrides", ov)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--chart", default="eFMec2F9")
    ap.add_argument("--display-tf", default="60")
    a = ap.parse_args(); CH = a.chart
    # KL = bright/solid, normal zone = faint. demand=green, supply=red.
    GREEN_KL = json.dumps({"backgroundColor": "rgba(0,210,90,0.28)", "color": "rgba(0,230,100,0.95)"})
    GREEN    = json.dumps({"backgroundColor": "rgba(0,200,80,0.08)", "color": "rgba(0,200,80,0.45)"})
    RED_KL   = json.dumps({"backgroundColor": "rgba(240,60,60,0.28)", "color": "rgba(255,70,70,0.95)"})
    RED      = json.dumps({"backgroundColor": "rgba(230,60,60,0.08)", "color": "rgba(230,60,60,0.45)"})
    BLUE  = json.dumps({"linecolor": "rgba(70,130,220,0.8)", "linestyle": 2})
    GRAY  = json.dumps({"linecolor": "rgba(150,150,150,0.7)", "linestyle": 2})

    SUP = json.dumps({"linecolor": "rgba(0,210,90,0.85)", "linestyle": 0, "linewidth": 2})   # support line (green)
    RES = json.dumps({"linecolor": "rgba(240,70,70,0.85)", "linestyle": 0, "linewidth": 2})   # resistance line (red)

    tv(CH, "symbol", "XAUUSD")
    tv(CH, "replay", "start", "--date", a.date); time.sleep(5)
    tv(CH, "draw", "clear")
    drawn = {"demand": 0, "supply": 0, "KL": 0, "support": 0, "resistance": 0, "va": 0}
    cur_price = None
    sr = []   # (price, kind 'H'/'L', tf-label) horizontal support/resistance LEVELS

    # --- buy/sell ZONES (demand/supply order-block boxes) ---
    for tf, n, lab in [("D", 40, "D"), ("240", 80, "4H"), ("60", 160, "1H")]:
        b = bars_tf(CH, tf, n)
        if not b:
            continue
        t1 = b[-1]["time"]; cur_price = b[-1]["close"]
        for z in Z.mark_key_levels(b, left=2, right=2, lookback=20):
            kl = z["key_level"]
            tag = f"{lab} {z['kind']}" + (f" KL {z['score']}" if kl else "")
            ov = (GREEN_KL if kl else GREEN) if z["kind"] == "demand" else (RED_KL if kl else RED)
            rect(CH, z["time"], z["lo"], t1, z["hi"], tag, ov)
            drawn[z["kind"]] += 1
            if kl: drawn["KL"] += 1
        for x in Z.sr_levels(b, lookback=20):
            sr.append((x["price"], x["role"], x["flipped"], lab))

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
            hline(CH, p, f"{role.capitalize()} {l}" + (" flip" if fl else ""), color)
            drawn[role] += 1
            if len(seen) >= 4:
                break
    if cur_price:
        draw_sr("support", SUP, True)
        draw_sr("resistance", RES, False)

    b30 = bars_tf(CH, "30", 400)
    if b30:
        for v in Z.prior_day_vas(b30, ref_ts=b30[-1]["time"], n=3):
            md = v["date"][5:]
            hline(CH, v["poc"], f"POC {md}", BLUE)
            hline(CH, v["vah"], f"VAH {md}", GRAY)
            hline(CH, v["val"], f"VAL {md}", GRAY)
            drawn["va"] += 3

    tv(CH, "timeframe", a.display_tf)
    print(f"drawn on {CH} @ {a.date}: {drawn}")


if __name__ == "__main__":
    main()
