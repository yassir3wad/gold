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
    # Session ranges read from the user's "Trading Sessions" indicator (its window + timezone inputs),
    # so they match the chart boxes exactly and stay DST-correct — no hardcoded UTC windows.
    # Falls back to UTC windows only if the indicator can't be read.
    import datetime as dt
    try: from zoneinfo import ZoneInfo
    except Exception: ZoneInfo = None
    tv('timeframe', '15'); sb = tv('ohlcv', '-n', '300').get('bars', []); tv('timeframe', '1')
    def srange(win, tzname):   # win 'HHMM-HHMM' in tzname -> (high, low, end_utc_hour) of the last completed session
        if not (ZoneInfo and sb): return (None, None, None)
        tz = ZoneInfo(tzname); a = int(win[:2])*60+int(win[2:4]); z = int(win[5:7])*60+int(win[7:])
        byd = {}
        for x in sb:
            lt = dt.datetime.fromtimestamp(x['time'], tz); m = lt.hour*60+lt.minute
            if a <= m < z: byd.setdefault(lt.date(), []).append(x)
        if not byd: return (None, None, None)
        now = dt.datetime.now(tz); days = sorted(byd); last = days[-1]
        if last == now.date() and (now.hour*60+now.minute) < z and len(days) >= 2: last = days[-2]
        s = byd[last]; end = dt.datetime.combine(last, dt.time(), tz) + dt.timedelta(minutes=z)
        return (round(max(x['high'] for x in s), 1), round(min(x['low'] for x in s), 1), end.astimezone(dt.timezone.utc).hour)
    sid = next((s['id'] for s in tv('state').get('studies', []) if 'Session' in s.get('name', '')), None)
    sess = {}
    if sid:
        vals = [i.get('value') for i in tv('indicator', 'get', sid).get('inputs', [])]
        for k, v in enumerate(vals):   # find 'HHMM-HHMM' windows, pair each with the next IANA tz, classify by region
            if isinstance(v, str) and len(v) == 9 and v[4] == '-' and v[:4].isdigit() and v[5:].isdigit():
                tz = next((vals[j] for j in range(k+1, min(k+3, len(vals))) if isinstance(vals[j], str) and '/' in vals[j]), None)
                reg = ('asia' if 'Asia' in (tz or '') else 'london' if 'Europe' in (tz or '') else 'ny' if 'America' in (tz or '') else None)
                if reg: sess[reg] = srange(v, tz)
    def fb(h1, h2):   # fallback: hardcoded UTC windows
        now = dt.datetime.utcnow(); day = now.date() if now.hour >= h2 else (now.date()-dt.timedelta(days=1))
        s = [x for x in sb if dt.datetime.utcfromtimestamp(x['time']).date() == day and h1 <= dt.datetime.utcfromtimestamp(x['time']).hour < h2]
        return (round(max(x['high'] for x in s), 1), round(min(x['low'] for x in s), 1), h2) if s else (None, None, None)
    asia_h, asia_l, asia_end = sess.get('asia') or fb(0, 7)
    london_h, london_l, london_end = sess.get('london') or fb(7, 16)
    ny_h, ny_l, ny_end = sess.get('ny') or fb(13, 22)
    out = {'ts': time.time(), 'price': price, 'pdh': pdh, 'pdl': pdl,
           'asia_h': asia_h, 'asia_l': asia_l, 'london_h': london_h, 'london_l': london_l, 'ny_h': ny_h, 'ny_l': ny_l,
           'asia_end': asia_end, 'london_end': london_end, 'ny_end': ny_end,
           'htf_r': [[z[0], z[1], z[2]] for z in R], 'htf_s': [[z[0], z[1], z[2]] for z in S]}
    json.dump(out, open(ZONES_FILE, 'w'), indent=1)
    print(f"wrote zones.json  asia={asia_h}/{asia_l}(end{asia_end}) london={london_h}/{london_l}(end{london_end}) ny={ny_h}/{ny_l}(end{ny_end})  src={'indicator' if sess else 'fallback-UTC'}")

if __name__ == "__main__":
    main()
