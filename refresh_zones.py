#!/usr/bin/env python3
"""Auto-derive HTF support/resistance zones from D/4H/1H/15m structure -> zones.json.
Clusters swing pivots + EMAs + PDH/PDL + round numbers into multi-touch zones. Read by
scalp_fast.py (which rebuilds this automatically when it goes stale). Run standalone any time:
    python3 refresh_zones.py
"""
import subprocess, json, os, time
TVDIR = os.path.expanduser("~/tradingview-mcp"); PIP = 0.10
ZONES_FILE = os.path.join(TVDIR, "zones.json")
MERGE = 2.0   # cluster levels within $2 (20p) into one zone

def tv(*a):
    r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=45)
    try: return json.loads(r.stdout)
    except Exception: return {}

def pivots(b, L=3, R=3):
    sh, sl = [], []
    for i in range(L, len(b)-R):
        if all(b[i]['high'] >= b[i-k]['high'] for k in range(1, L+1)) and all(b[i]['high'] >= b[i+k]['high'] for k in range(1, R+1)): sh.append(b[i]['high'])
        if all(b[i]['low'] <= b[i-k]['low'] for k in range(1, L+1)) and all(b[i]['low'] <= b[i+k]['low'] for k in range(1, R+1)): sl.append(b[i]['low'])
    return sh, sl

def main():
    price = tv('quote').get('last')
    if price is None: print("no price"); return
    cands = []   # (price, source-tag)
    pdh = pdl = None
    for tf, n, tag in [('D', 40, 'D'), ('240', 60, '4H'), ('60', 90, '1H'), ('15', 100, '15m')]:
        tv('timeframe', tf); b = tv('ohlcv', '-n', str(n)).get('bars', [])
        if not b: continue
        sh, sl = pivots(b)
        for p in sh[-6:]: cands.append((round(p, 1), tag))
        for p in sl[-6:]: cands.append((round(p, 1), tag))
        for s in tv('values').get('studies', []):
            if 'Moving Average' in s.get('name', ''):
                try: cands.append((round(float(s['values']['EMA'].replace(',', '')), 1), tag+'EMA'))
                except Exception: pass
        if tf == 'D' and len(b) >= 2:
            pdh, pdl = round(b[-2]['high'], 1), round(b[-2]['low'], 1)
            cands += [(pdh, 'PDH'), (pdl, 'PDL')]
    tv('timeframe', '1')
    base = round(price/10)*10
    for r in (base-20, base-10, base, base+10, base+20): cands.append((float(r), 'round'))
    # cluster nearby levels
    cands.sort()
    clusters = []
    for p, src in cands:
        if clusters and p - clusters[-1]['hi'] <= MERGE:
            c = clusters[-1]; c['hi'] = max(c['hi'], p); c['srcs'].append(src); c['ps'].append(p)
        else:
            clusters.append({'lo': p, 'hi': p, 'srcs': [src], 'ps': [p]})
    raw = []
    for c in clusters:
        if len(c['srcs']) >= 2 or any(s in ('PDH', 'PDL') for s in c['srcs']):   # multi-touch or prior-day extreme
            raw.append({'lo': round(c['lo']-2, 1), 'hi': round(c['hi']+2, 1), 'srcs': list(c['srcs']), 'ps': list(c['ps'])})
    # merge overlapping zones (same structure split across adjacent clusters) — avoids confluence inflation
    raw.sort(key=lambda z: z['lo']); merged = []
    for z in raw:
        if merged and z['lo'] <= merged[-1]['hi']:
            m = merged[-1]; m['hi'] = max(m['hi'], z['hi']); m['srcs'] += z['srcs']; m['ps'] += z['ps']
        else:
            merged.append(z)
    def fmt(z):
        mid = round(sum(z['ps'])/len(z['ps']), 1); srcs = sorted(set(z['srcs']))
        return (z['lo'], z['hi'], f"{mid} ({'+'.join(srcs[:4])}, x{len(z['srcs'])})", mid)
    zones = [fmt(z) for z in merged]
    R = sorted([z for z in zones if z[3] > price], key=lambda z: z[3])[:6]
    S = sorted([z for z in zones if z[3] < price], key=lambda z: -z[3])[:6]
    # Session ranges by UTC time — dynamic liquidity pools for the session-sweep strategy.
    # For each session window [h1,h2) use the LAST COMPLETED occurrence (today's if past h2, else yesterday's).
    import datetime as dt
    tv('timeframe', '15'); sb = tv('ohlcv', '-n', '200').get('bars', []); tv('timeframe', '1')
    now = dt.datetime.utcnow()
    def sess(h1, h2):   # Asian 00-07, London 07-16, NY 13-22 (UTC)
        day = now.date() if now.hour >= h2 else (now.date() - dt.timedelta(days=1))
        s = [x for x in sb if dt.datetime.utcfromtimestamp(x['time']).date() == day
             and h1 <= dt.datetime.utcfromtimestamp(x['time']).hour < h2]
        return (round(max(x['high'] for x in s), 1), round(min(x['low'] for x in s), 1)) if s else (None, None)
    asia_h, asia_l = sess(0, 7); london_h, london_l = sess(7, 16); ny_h, ny_l = sess(13, 22)
    out = {'ts': time.time(), 'price': price, 'pdh': pdh, 'pdl': pdl,
           'asia_h': asia_h, 'asia_l': asia_l, 'london_h': london_h, 'london_l': london_l, 'ny_h': ny_h, 'ny_l': ny_l,
           'htf_r': [[z[0], z[1], z[2]] for z in R], 'htf_s': [[z[0], z[1], z[2]] for z in S]}
    json.dump(out, open(ZONES_FILE, 'w'), indent=1)
    print(f"wrote zones.json  price={price}  R={len(R)} S={len(S)}  asia={asia_h}/{asia_l} london={london_h}/{london_l} ny={ny_h}/{ny_l}")

if __name__ == "__main__":
    main()
