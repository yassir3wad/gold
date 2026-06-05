#!/usr/bin/env python3
"""
Multi-factor scalp scanner for XAUUSD.
Combines: market structure (swing H/L), RSI, order blocks, FVG/imbalance,
AUTO-DETECTED 1H/4H support&resistance (multi-touch, resampled from 15m),
FIBONACCI retracement of the latest HTF leg (OTE/golden zone), round numbers,
and an EMA trend filter. Reads the chart's ACTIVE 15m timeframe via the tv CLI.

Entries only AT an S/R or fib zone; RSI/FVG/OB/fib/round#/touches act as confluence.
A signal needs a rejection candle (on the CLOSED 15m bar) + 3 confluences, and must be
with-trend (EMA filter). Usage: python3 scalp_scan.py [bar_count]
"""
import subprocess, json, os, sys
from src.state_manager import StateManager

TVDIR = os.path.expanduser("~/tradingview-mcp")
ZONE_PAD = 3.0          # half-width of an S/R zone around a clustered level
CLUSTER_TOL = 4.0       # merge swing levels within this distance into one S/R
# Daily EMA200 (~4357) + 4H support: a sanctioned counter-trend BUY zone that bypasses the
# EMA trend filter (price reaching the Daily EMA200 is a high-quality long per the playbook).
# Daily EMA200 drifts ~$1-3/day — refresh this range periodically.
HTF_BUY = (4351.0, 4368.0)
DAILY_EMA200 = 4357.0   # while price is ABOVE this, the daily uptrend is intact -> pullback longs allowed

def tv(*args):
    r = subprocess.run(["node", "src/cli/index.js", *args], cwd=TVDIR,
                       capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}

def get_rsi():
    for s in tv("values").get("studies", []):
        if "Relative Strength" in s.get("name", ""):
            try: return float(s["values"].get("RSI"))
            except Exception: return None
    return None

def get_emas():
    out = []
    for s in tv("values").get("studies", []):
        if "Exponential" in s.get("name", ""):
            try: out.append(float(str(s["values"].get("EMA")).replace(",", "")))
            except Exception: pass
    return sorted(out)

def resample(bars, f):
    """Aggregate 15m bars into higher-TF bars (f=4 -> 1H, f=16 -> 4H), aligned to the most recent bar."""
    out = []
    start = len(bars) % f
    for i in range(start, len(bars), f):
        c = bars[i:i+f]
        if len(c) < f: break
        out.append({"open": c[0]["open"], "high": max(x["high"] for x in c),
                    "low": min(x["low"] for x in c), "close": c[-1]["close"]})
    return out

def pivots(bars, L=2, R=2):
    sh, sl = [], []
    for i in range(L, len(bars) - R):
        h, l = bars[i]["high"], bars[i]["low"]
        if all(h >= bars[i-k]["high"] for k in range(1, L+1)) and all(h >= bars[i+k]["high"] for k in range(1, R+1)):
            sh.append(h)
        if all(l <= bars[i-k]["low"] for k in range(1, L+1)) and all(l <= bars[i+k]["low"] for k in range(1, R+1)):
            sl.append(l)
    return sh, sl

def cluster_levels(prices):
    """Cluster nearby swing prices into S/R levels. Returns [(center, touches)] sorted."""
    if not prices: return []
    ps = sorted(prices)
    groups = [[ps[0]]]
    for p in ps[1:]:
        if p - groups[-1][-1] <= CLUSTER_TOL:
            groups[-1].append(p)
        else:
            groups.append([p])
    return [(round(sum(g)/len(g), 1), len(g)) for g in groups]

def build_sr(bars):
    """Auto S/R from 1H + 4H resampled swings. Returns list of dicts {center,lo,hi,touches,tf}."""
    h1, h4 = resample(bars, 4), resample(bars, 16)
    raw = []  # (price, tf)
    for tf, hb in (("1H", h1), ("4H", h4)):
        sh, sl = pivots(hb)
        for p in sh + sl:
            raw.append((p, tf))
    # cluster across both TFs; a level touched on both / multiple times = stronger
    if not raw: return []
    raw.sort()
    groups = [[raw[0]]]
    for item in raw[1:]:
        if item[0] - groups[-1][-1][0] <= CLUSTER_TOL:
            groups[-1].append(item)
        else:
            groups.append([item])
    zones = []
    for g in groups:
        center = round(sum(p for p, _ in g) / len(g), 1)
        tfs = sorted(set(tf for _, tf in g))
        zones.append({"center": center, "lo": center - ZONE_PAD, "hi": center + ZONE_PAD,
                      "touches": len(g), "tf": "+".join(tfs)})
    return zones

def fib_zone(bars, lookback=48):
    """Fib retracement of the most recent significant leg on 4H-resampled data."""
    h4 = resample(bars, 16)
    seg = h4[-lookback:] if len(h4) >= 6 else h4
    if len(seg) < 4: return None
    hi_i = max(range(len(seg)), key=lambda i: seg[i]["high"])
    lo_i = min(range(len(seg)), key=lambda i: seg[i]["low"])
    H, L = seg[hi_i]["high"], seg[lo_i]["low"]
    rng = H - L
    if rng < 5: return None
    ratios = (0.382, 0.5, 0.618, 0.705, 0.786)
    if lo_i > hi_i:   # low more recent -> down leg -> retrace UP (with-trend = SHORT into OTE)
        direction, side = "down", "SUPPLY"
        levels = {r: round(L + rng * r, 1) for r in ratios}
    else:             # up leg -> retrace DOWN (with-trend = LONG into OTE)
        direction, side = "up", "DEMAND"
        levels = {r: round(H - rng * r, 1) for r in ratios}
    ote = tuple(sorted((levels[0.618], levels[0.786])))
    return {"dir": direction, "side": side, "H": round(H,1), "L": round(L,1),
            "levels": levels, "ote": ote}

def fvgs(bars, price):
    out = []; n = len(bars)
    for i in range(2, n):
        a, c = bars[i-2], bars[i]
        if a["high"] < c["low"]:
            lo, hi = a["high"], c["low"]
            if not any(b["low"] <= lo for b in bars[i+1:]) and abs((lo+hi)/2 - price) < 25:
                out.append(("bull", round(lo,2), round(hi,2), n-1-i))
        if a["low"] > c["high"]:
            lo, hi = c["high"], a["low"]
            if not any(b["high"] >= hi for b in bars[i+1:]) and abs((lo+hi)/2 - price) < 25:
                out.append(("bear", round(lo,2), round(hi,2), n-1-i))
    return out[-4:]

def order_blocks(bars, price):
    out = []; n = len(bars)
    for i in range(1, n-1):
        b, nx = bars[i], bars[i+1]
        body, nbody = abs(b["close"]-b["open"]), abs(nx["close"]-nx["open"])
        if b["close"] < b["open"] and nx["close"] > b["high"] and nbody > body and abs((b["low"]+b["high"])/2 - price) < 25:
            out.append(("bull", round(b["low"],2), round(b["high"],2), n-1-i))
        if b["close"] > b["open"] and nx["close"] < b["low"] and nbody > body and abs((b["low"]+b["high"])/2 - price) < 25:
            out.append(("bear", round(b["low"],2), round(b["high"],2), n-1-i))
    return out[-4:]

def round_levels(price):
    base = round(price / 10) * 10
    return [base - 10, base - 5, base, base + 5, base + 10]

def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    tv("timeframe", "15")   # self-heal: this scanner operates on 15m (in case fast-mode left it on 1m)
    q = tv("quote"); price = q.get("last")
    if price is None: print("ERR: no quote"); return
    fetch = max(count, 480)                       # enough 15m bars to resample 1H/4H
    allbars = tv("ohlcv", "-n", str(fetch)).get("bars", [])
    if len(allbars) < 40: print("ERR: no bars"); return
    bars = allbars[-count:]
    last = bars[-2] if len(bars) >= 2 else bars[-1]   # last CLOSED bar
    rsi = get_rsi(); emas = get_emas()
    ema_min = min(emas) if emas else None
    ema_max = max(emas) if emas else None

    sr = build_sr(allbars)
    fib = fib_zone(allbars)
    fv = fvgs(bars, price); ob = order_blocks(bars, price)
    near_round = min(round_levels(price), key=lambda r: abs(r - price))

    # last closed candle character
    body = last["close"] - last["open"]
    uw = last["high"] - max(last["open"], last["close"])
    lw = min(last["open"], last["close"]) - last["low"]
    bull_rej = (lw > abs(body) and last["close"] > last["open"]) or (lw > 2*max(abs(body),0.01))
    bear_rej = (uw > abs(body) and last["close"] < last["open"]) or (uw > 2*max(abs(body),0.01))

    sup = sorted([z for z in sr if z["center"] > price], key=lambda z: z["center"])[:3]
    dem = sorted([z for z in sr if z["center"] <= price], key=lambda z: -z["center"])[:3]
    print(f"PRICE {price}  RSI={rsi}  EMA[{ema_min}-{ema_max}]")
    print("R (4H/1H): " + " | ".join(f"{z['center']}({z['tf']}x{z['touches']})" for z in sup))
    print("S (4H/1H): " + " | ".join(f"{z['center']}({z['tf']}x{z['touches']})" for z in dem))
    if fib:
        print(f"FIB {fib['dir']}-leg {fib['L']}->{fib['H']}: 0.5={fib['levels'][0.5]} 0.618={fib['levels'][0.618]} 0.705={fib['levels'][0.705]} 0.786={fib['levels'][0.786]} | OTE {fib['ote'][0]}-{fib['ote'][1]} ({fib['side']})")
    print(f"lastbar(closed) body{body:+.2f} uW{uw:.2f} lW{lw:.2f} bullRej={bull_rej} bearRej={bear_rej}")

    # which zone is price in? nearest S/R within pad, or fib OTE
    def in_zone(zones):
        for z in zones:
            if z["lo"] - 1 <= price <= z["hi"] + 1: return z
        return None
    in_sup = in_zone(sup); in_dem = in_zone(dem)
    in_htf_buy = HTF_BUY[0] - 1 <= price <= HTF_BUY[1] + 1
    in_ote = fib and fib["ote"][0] - 1 <= price <= fib["ote"][1] + 1
    near_fib = None
    if fib:
        for r, lv in fib["levels"].items():
            if abs(lv - price) < 2: near_fib = r; break

    # ---- verdict with de-dup ----
    state_manager = StateManager(namespace="scalp_scan")

    def load_state():
        watch_data = state_manager.get_watch_state("XAUUSD")
        return watch_data.get("key") if watch_data else None

    def save_state(k):
        if k is None:
            state_manager.save_watch_state("XAUUSD", {})
        else:
            state_manager.save_watch_state("XAUUSD", {"key": k})

    side = zone = None
    if in_dem or in_htf_buy or (in_ote and fib["side"] == "DEMAND"):
        if in_dem:
            z = in_dem
        elif in_htf_buy:
            z = {"center": round(sum(HTF_BUY)/2, 1), "touches": 3, "tf": "D-EMA200"}
        else:
            z = {"center": price, "touches": 0, "tf": "fib"}
        side, zone = "LONG", (round(z["center"]-ZONE_PAD,1), round(z["center"]+ZONE_PAD,1))
        conf = [f"S/R {z['center']} ({z.get('tf')}x{z.get('touches')})"] if in_dem else []
        if in_htf_buy: conf.append("Daily EMA200 HTF support (MAJOR buy)")
        if in_ote: conf.append(f"fib OTE {fib['ote'][0]}-{fib['ote'][1]}")
        if near_fib: conf.append(f"fib {near_fib}")
        if z.get("touches",0) >= 3: conf.append("multi-touch HTF")
        if rsi is not None and rsi < 35: conf.append(f"RSI oversold ({rsi})")
        if any(s=="bull" for s,_,_,_ in fv): conf.append("bullish FVG")
        if any(s=="bull" for s,_,_,_ in ob): conf.append("bullish OB")
        if abs(near_round - price) < 1.5: conf.append(f"round# {near_round}")
        if bull_rej: conf.append("bullish rejection")
        signal = bull_rej and len(conf) >= 3
        print(f"\n>> LONG confluence ({len(conf)}): " + " | ".join(conf))
        wait_msg = ">> WAIT: need bullish rejection + 3+ confluence"
    elif in_sup or (in_ote and fib["side"] == "SUPPLY"):
        z = in_sup or {"center": price, "touches": 0, "tf": "fib"}
        side, zone = "SHORT", (round(z["center"]-ZONE_PAD,1), round(z["center"]+ZONE_PAD,1))
        conf = [f"S/R {z['center']} ({z.get('tf')}x{z.get('touches')})"] if in_sup else []
        if in_ote: conf.append(f"fib OTE {fib['ote'][0]}-{fib['ote'][1]}")
        if near_fib: conf.append(f"fib {near_fib}")
        if z.get("touches",0) >= 3: conf.append("multi-touch HTF")
        if rsi is not None and rsi > 65: conf.append(f"RSI overbought ({rsi})")
        if any(s=="bear" for s,_,_,_ in fv): conf.append("bearish FVG")
        if any(s=="bear" for s,_,_,_ in ob): conf.append("bearish OB")
        if abs(near_round - price) < 1.5: conf.append(f"round# {near_round}")
        if bear_rej: conf.append("bearish rejection")
        signal = bear_rej and len(conf) >= 3
        print(f"\n>> SHORT confluence ({len(conf)}): " + " | ".join(conf))
        wait_msg = ">> WAIT: need bearish rejection + 3+ confluence"
    else:
        signal = False; save_state(None)
        ns = sup[0]["center"] if sup else "?"; nd = dem[0]["center"] if dem else "?"
        print(f"\n>> NO TRADE: mid-structure. Nearest R {ns}, S {nd}. Wait for a zone.")

    # EMA trend filter
    # Trend gating. Longs: with-trend (>= EMA cluster), Daily-EMA200 HTF buy, or PULLBACK
    # (counter to 1H/4H but still ABOVE the Daily EMA200 = daily uptrend intact). Block only
    # "falling-knife" longs (below the Daily EMA200 too). Shorts: with-trend only (below EMA cluster).
    long_label = ""; blocked = False
    if side == "LONG":
        counter = ema_min is not None and price < ema_min
        if in_htf_buy:
            long_label = " (Daily-EMA200 HTF buy)"
        elif counter and price > DAILY_EMA200:
            long_label = " (PULLBACK — counter 1H/4H but daily uptrend; tight stop, quick scalp)"
        elif counter:
            blocked = True   # below Daily EMA200 too = no higher-TF support
    elif side == "SHORT":
        if ema_max is not None and price > ema_max:
            blocked = True   # above EMA cluster = counter-trend short
    if side:
        if signal and blocked:
            print(f">> BLOCKED ({side} counter-trend): price {price} vs EMA {ema_min}-{ema_max}, DailyEMA200 {DAILY_EMA200} — skip")
        elif signal:
            key = f"{side}@{zone[0]}-{zone[1]}"
            if load_state() == key:
                print(f">> SIGNAL: {side}{long_label} (repeat — already alerted this zone-touch, suppress)")
            else:
                save_state(key); print(f">> SIGNAL: {side}{long_label}")
        else:
            print(wait_msg)

if __name__ == "__main__":
    main()
