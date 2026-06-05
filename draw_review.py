#!/usr/bin/env python3
"""Draw the structural context for a given date so it can be reviewed by eye:
  - D / 4h / 1h supply-demand origin-candle zones (boxes; demand green, supply red)
  - prior-3-day value areas (POC / VAH / VAL, labeled with the date)
Pins to a dedicated chart; nothing wired into the engine. For visual review before integration.
    python3 draw_review.py --date 2026-06-01 --chart eFMec2F9
"""
import argparse, subprocess, os, json, time
import zones_sd as Z

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
    ap.add_argument("--display-tf", default="15")
    a = ap.parse_args(); CH = a.chart
    GREEN = json.dumps({"backgroundColor": "rgba(0,200,80,0.12)", "color": "rgba(0,200,80,0.6)"})
    RED   = json.dumps({"backgroundColor": "rgba(230,60,60,0.12)", "color": "rgba(230,60,60,0.6)"})
    BLUE  = json.dumps({"linecolor": "rgba(70,130,220,0.8)", "linestyle": 2})
    GRAY  = json.dumps({"linecolor": "rgba(150,150,150,0.7)", "linestyle": 2})

    tv(CH, "symbol", "XAUUSD")
    tv(CH, "replay", "start", "--date", a.date); time.sleep(5)
    tv(CH, "draw", "clear")
    drawn = {"demand": 0, "supply": 0, "va": 0}

    for tf, n, lab in [("D", 40, "D"), ("240", 60, "4H"), ("60", 140, "1H")]:
        b = bars_tf(CH, tf, n)
        if not b:
            continue
        t1 = b[-1]["time"]
        for z in Z.find_zones(b, left=2, right=2, lookback=20):
            rect(CH, z["time"], z["lo"], t1, z["hi"], f"{lab} {z['kind']}", GREEN if z["kind"] == "demand" else RED)
            drawn[z["kind"]] += 1

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
