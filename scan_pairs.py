#!/usr/bin/env python3
"""Meta-scanner: rank every configured instrument by CURRENT tradeability so you focus on the live one
instead of staring at 7 charts. Light read per pair (1m data + its zones + session) from its own window
(TV_CHART) — no TF flips. Score = volatility(30%) + trend-efficiency(30%) + level-proximity(20%) + session(20%).
    python3 scan_pairs.py
"""
import subprocess, json, os, datetime as dt
TVDIR = os.path.expanduser("~/tradingview-mcp")
INSTR = json.load(open(os.path.join(TVDIR, "instruments.json")))

def tv(chart, *a):
    env = dict(os.environ); env["TV_CHART"] = str(chart)
    r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=30, env=env)
    try: return json.loads(r.stdout)
    except Exception: return {}

SESS = {"asia": (23, 8), "london": (7, 16), "ny": (13, 21)}   # approx UTC windows
def in_session(names):
    h = dt.datetime.utcnow().hour
    for n in (names or []):
        a, b = SESS.get(n, (0, 0))
        if (a <= h < b) if a < b else (h >= a or h < b): return n
    return None

def er15(bars):   # Kaufman efficiency ratio on ~15m closes resampled from 1m (1=trend, 0=chop)
    c = [bars[i]['close'] for i in range(len(bars)-1, -1, -15)][::-1]
    if len(c) < 5: return 1.0
    den = sum(abs(c[k]-c[k-1]) for k in range(1, len(c)))
    return abs(c[-1]-c[0]) / den if den else 0.0

def score_pair(sym, cfg):
    chart = cfg.get("chart")
    if not chart: return None
    pip = cfg.get("pip", 0.10); atr_ref = cfg.get("atr_ref", 30) or 30
    price = tv(chart, "quote").get("last")
    bars = tv(chart, "ohlcv", "-n", "120").get("bars", [])
    if price is None or len(bars) < 30: return None
    atr = sum(x['high']-x['low'] for x in bars[-14:]) / 14 / pip
    atr_base = sum(x['high']-x['low'] for x in bars) / len(bars) / pip
    vs = atr_base / atr_ref
    er = er15(bars)
    near_atr = 9.0
    try:
        z = json.load(open(os.path.join(TVDIR, f"zones_{sym.lower()}.json")))
        lv = [x for lo, hi, _ in z.get('htf_r', [])+z.get('htf_s', []) for x in (lo, hi)]
        if lv and atr: near_atr = min(abs(price-x) for x in lv) / pip / atr
    except Exception: pass
    sess = in_session(cfg.get("sessions"))
    s_vol = 100 * max(0, 1 - abs(min(vs, 3)-1.2)/1.5)   # best ~VS 1.2; penalize dead (<0.5) & spiky (>2.5)
    s_trend = 100 * min(1, er/0.6)                        # ER toward 0.6 = clean trend
    s_prox = 100 * max(0, 1 - near_atr/3)                 # within ~3 ATR of a key level
    s_sess = 100 if sess else 30
    score = round(0.30*s_vol + 0.30*s_trend + 0.20*s_prox + 0.20*s_sess)
    return {"sym": sym, "price": price, "vs": round(vs, 2), "atr": round(atr, 1),
            "er": round(er, 2), "near": round(near_atr, 1), "sess": sess or "—", "score": score}

def main():
    rows = []
    for sym, cfg in INSTR.items():
        if sym.startswith("_"): continue
        r = score_pair(sym, cfg)
        if r: rows.append(r)
    rows.sort(key=lambda r: -r["score"])
    print(f"\n=== Pair tradeability  {dt.datetime.utcnow():%Y-%m-%d %H:%M}Z ===")
    print(f"{'PAIR':8}{'SCORE':>6}{'VS':>6}{'ER':>6}{'lvl(ATR)':>9}{'session':>9}   price")
    for r in rows:
        print(f"{r['sym']:8}{r['score']:>6}{r['vs']:>6}{r['er']:>6}{r['near']:>9}{r['sess']:>9}   {r['price']}")
    if rows:
        t = rows[0]
        print(f"\n>> FOCUS: {t['sym']} (score {t['score']}) — "
              f"{'in '+t['sess'] if t['sess']!='—' else 'no active session'}, ER {t['er']} "
              f"({'trending' if t['er']>=0.4 else 'chop'}), VS {t['vs']}, {t['near']} ATR from a level.")
        hot = [r['sym'] for r in rows if r['score'] >= 60]
        print(f">> Worth watching (score≥60): {', '.join(hot) if hot else 'none — all quiet/chop right now'}")

if __name__ == "__main__":
    main()
