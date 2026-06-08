#!/usr/bin/env python3
"""Compare smc_ob_zones ON vs OFF (codex's 'treat stored SMC levels as trade zones' commit) from the
A/B replay outputs (/tmp/ab_<pair>_<off|on>_<date>_{sig,zr,bars}.json). Answers codex's questions:
  (2) how many EXTRA candidates appear with SMC zones on (esp. GBP/XAU),
  (3) do the extra candidates REACH REVIEW (surfaced signals) or get BLOCKED (zrskip, by chop/R:R).
Scores surfaced signals + the blocked zone-rejections against the day's real bars. No engine interaction.
    python3 ab_smc.py
"""
import glob, json, os, re
from collections import defaultdict
from backtest_multi_day import simulate_trade
PIP = 0.10
SPREAD = {"XAUUSD": 3.0, "GBPUSD": 1.5}


def net_of(sigs, bars, spread):
    tot = 0
    for s in sigs:
        fut = [b for b in bars if b["time"] > s["t"]][:15]
        o, exitp, _ = simulate_trade(s["side"], s["entry"], s["sl"], s["tp1"], fut, horizon=15)
        p = (s["entry"] - exitp) / PIP if s["side"] == "SHORT" else (exitp - s["entry"]) / PIP
        tot += round(p) - spread
    return round(tot)


def load(pair, flag, date, kind):
    p = f"/tmp/ab_{pair}_{flag}_{date}_{kind}.json"
    try: return json.load(open(p))
    except Exception: return []


def main():
    pairs = sorted({m.group(1) for f in glob.glob("/tmp/ab_*_sig.json")
                    if (m := re.match(r"/tmp/ab_([A-Z0-9]+)_", f))})
    dates = sorted({re.search(r"_(\d{4}-\d{2}-\d{2})_sig", f).group(1) for f in glob.glob("/tmp/ab_*_sig.json")})
    if not pairs:
        print("No A/B outputs in /tmp (ab_<pair>_<flag>_<date>_*.json). Run the A/B first."); return
    print(f"=== smc_ob_zones A/B · pairs {pairs} · {len(dates)} days {dates} ===\n")

    for pair in pairs:
        spread = SPREAD.get(pair, 2.0)
        agg = {}
        for flag in ("off", "on"):
            sig_n = zr_n = zr_chop = zr_rr = 0; sig_net = 0; zr_wt = 0
            for d in dates:
                bars = sorted(load(pair, flag, d, "bars"), key=lambda b: b["time"])
                sigs = load(pair, flag, d, "sig"); zrs = load(pair, flag, d, "zr")
                sig_n += len(sigs); sig_net += net_of(sigs, bars, spread) if bars else 0
                for z in zrs:
                    zr_n += 1
                    if z.get("block") in ("chop", "both"): zr_chop += 1
                    if z.get("block") in ("rr", "both"):   zr_rr += 1
                    if z.get("with_trend"): zr_wt += 1
            agg[flag] = dict(sig_n=sig_n, sig_net=sig_net, zr_n=zr_n, zr_chop=zr_chop, zr_rr=zr_rr, zr_wt=zr_wt)

        o, n = agg["off"], agg["on"]
        print(f"--- {pair} (spread {spread}p) ---")
        print(f"  surfaced (reach review): off={o['sig_n']:2}  on={n['sig_n']:2}  Δ=+{n['sig_n']-o['sig_n']}   "
              f"net: off={o['sig_net']:+d}p  on={n['sig_net']:+d}p")
        print(f"  zone-rejections BLOCKED: off={o['zr_n']:2}  on={n['zr_n']:2}  Δ=+{n['zr_n']-o['zr_n']}   "
              f"(on: {n['zr_chop']} chop · {n['zr_rr']} negR:R · {n['zr_wt']} with-trend)")
        extra = (n['sig_n'] - o['sig_n']) + (n['zr_n'] - o['zr_n'])
        print(f"  => smc_ob_zones added ~{extra} extra zone candidates; "
              f"{n['sig_n']-o['sig_n']} reached review, {n['zr_n']-o['zr_n']} blocked by the floor.\n")


if __name__ == "__main__":
    main()
