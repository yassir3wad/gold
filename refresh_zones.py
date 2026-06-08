#!/usr/bin/env python3
"""Auto-derive HTF support/resistance zones from D/4H/1H/15m structure -> zones.json.
Clusters swing pivots + EMAs + PDH/PDL + round numbers into multi-touch zones. Read by
scalp_fast.py (which rebuilds this automatically when it goes stale). Run standalone any time:
    python3 refresh_zones.py
"""
import subprocess, json, os, time, sys, math
TVDIR = os.path.expanduser("~/tradingview-mcp")
sys.path.insert(0, TVDIR)
try: import smc as smcmod   # LuxAlgo SMC multi-TF read (stored snapshot for trade-check)
except Exception: smcmod = None
try: import zones_sd as zsd   # classic supply/demand + S/R zones (SAME computation draw_review draws → drawn==traded)
except Exception: zsd = None
IS_BACKTEST = ("--out" in sys.argv)   # the isolated date-faithful zone file = the true backtest signal; the replay chart normally has no SMC. NOTE: key on --out NOT --chart — a live refresh may pin a chart with --chart and must still capture SMC (or fail loud if it's missing), never silently skip.
WITH_SMC = ("--with-smc" in sys.argv)   # opt IN to date-faithful SMC capture during a backtest (replay chart must have the SMC indicator); read at the replay cursor so the swings/boxes are date-faithful.
SYMBOL = "XAUUSD"
if "--symbol" in sys.argv:
    try: SYMBOL = sys.argv[sys.argv.index("--symbol")+1].upper()
    except Exception: pass
_cfg = {}
try:
    _all = json.load(open(os.path.join(TVDIR, "instruments.json")))
    _cfg = {**_all.get("_default", {}), **_all.get(SYMBOL, {})}
except Exception: pass
PIP = _cfg.get("pip", 0.10)
if _cfg.get("chart"): os.environ["TV_CHART"] = str(_cfg["chart"])   # pin reads to this symbol's window
if "--chart" in sys.argv:
    try: os.environ["TV_CHART"] = sys.argv[sys.argv.index("--chart")+1]   # backtest: pin reads to the replay chart
    except Exception: pass
ZONES_FILE = os.path.join(TVDIR, f"zones_{SYMBOL.lower()}.json")
if "--out" in sys.argv:
    try: ZONES_FILE = os.path.expanduser(sys.argv[sys.argv.index("--out")+1])   # backtest: write the isolated date-faithful zone file (never the live one)
    except Exception: pass
MERGE = 12 * PIP   # max cluster SPAN (pip-scaled): levels within this window form one zone; bounded by cluster START so dense levels can't daisy-chain
PAD = 4 * PIP      # zone half-width padding around the clustered span (pip-scaled; tight so a zone has a precise edge to react to)
MAX_W = 25 * PIP   # hard ceiling on final zone width — if a merged zone exceeds this, recenter to mid ± MAX_W/2 (anti-blowup safety net)
DECIMALS = max(0, int(round(-math.log10(PIP)))) + 1   # price rounding precision per instrument (gold 2, EUR 5, US30 1, JPY 3)
FIB_PULLBACK_ZONE = (0.52, 0.645)
FIB_TFS = [('240', '4H', 120), ('60', '1H', 180), ('15', '15m', 220), ('5', '5m', 260)]
FIB_MIN_WAVE_P = 80

def tv(*a):
    r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=45)
    try: return json.loads(r.stdout)
    except Exception: return {}

def symbol_base(s):
    """Bare ticker from a TV symbol: 'PEPPERSTONE:XAUUSD' -> 'XAUUSD'. Pure."""
    return s.split(":")[-1].strip().upper() if s else ""

def symbol_matches(expected_tv, chart_symbol):
    """True iff the chart is ACTUALLY showing the expected instrument (base-ticker match). Guards against a
    flaky/timed-out symbol switch writing the wrong instrument's levels into a zone file (the 2026-06-08
    incident: a stalled switch left the chart on gold, so refresh_zones --symbol GBPUSD wrote GOLD zones into
    zones_gbpusd.json). Empty/None chart_symbol -> False (unreadable = refuse to write). Pure (testable)."""
    cb = symbol_base(chart_symbol)
    return bool(cb) and cb == symbol_base(expected_tv)

def pivots(b, L=3, R=3):
    sh, sl = [], []
    for i in range(L, len(b)-R):
        if all(b[i]['high'] >= b[i-k]['high'] for k in range(1, L+1)) and all(b[i]['high'] >= b[i+k]['high'] for k in range(1, R+1)): sh.append(b[i]['high'])
        if all(b[i]['low'] <= b[i-k]['low'] for k in range(1, L+1)) and all(b[i]['low'] <= b[i+k]['low'] for k in range(1, R+1)): sl.append(b[i]['low'])
    return sh, sl

def fib_golden_zone(bars, side, pip=PIP, decimals=DECIMALS, zone=FIB_PULLBACK_ZONE, min_wave_p=FIB_MIN_WAVE_P):
    """Return the latest wave's golden-zone context for drawing/stored analysis. No rejection required."""
    if len(bars) < 8 or side not in ("LONG", "SHORT"):
        return None
    hist = bars[:-1]
    if side == "SHORT":
        low_i, low_bar = min(enumerate(hist), key=lambda kv: kv[1]["low"])
        prior = hist[:low_i]
        if not prior:
            return None
        high_i, high_bar = max(enumerate(prior), key=lambda kv: kv[1]["high"])
        if low_i <= high_i:
            return None
        wave_hi, wave_lo = high_bar["high"], low_bar["low"]
        wave_start, wave_end = high_bar.get("time"), low_bar.get("time")
        z1, z2 = (wave_lo + r * (wave_hi - wave_lo) for r in zone)
    else:
        high_i, high_bar = max(enumerate(hist), key=lambda kv: kv[1]["high"])
        prior = hist[:high_i]
        if not prior:
            return None
        low_i, low_bar = min(enumerate(prior), key=lambda kv: kv[1]["low"])
        if high_i <= low_i:
            return None
        wave_hi, wave_lo = high_bar["high"], low_bar["low"]
        wave_start, wave_end = low_bar.get("time"), high_bar.get("time")
        z1, z2 = (wave_hi - r * (wave_hi - wave_lo) for r in zone)
    wave_p = (wave_hi - wave_lo) / pip
    if wave_p < min_wave_p:
        return None
    zlo, zhi = min(z1, z2), max(z1, z2)
    return {"side": side, "wave_hi": round(wave_hi, decimals), "wave_lo": round(wave_lo, decimals),
            "zone_lo": round(zlo, decimals), "zone_hi": round(zhi, decimals),
            "ratio": f"{zone[0]:.3g}-{zone[1]:.3g}", "wave_pips": round(wave_p),
            "wave_start": wave_start, "wave_end": wave_end}

def build_fib_zones(tf_bars, pip=PIP, decimals=DECIMALS):
    out = []
    for tf, label, _ in FIB_TFS:
        bars = tf_bars.get(tf) or []
        for side in ("LONG", "SHORT"):
            z = fib_golden_zone(bars, side, pip=pip, decimals=decimals)
            if z:
                z["tf"] = label
                out.append(z)
    return out

def main():
    q = tv('quote')
    price = q.get('last')
    if price is None: print("no price"); return
    # GUARD: verify the chart is actually on the requested instrument before reading/writing — a flaky/timed-out
    # symbol switch must NEVER contaminate a zone file with another instrument's levels (2026-06-08 gold→GBP/NAS).
    _expected = _cfg.get("tv", SYMBOL)
    _chart_sym = q.get('symbol')
    if not symbol_matches(_expected, _chart_sym):
        print(f">> ABORT refresh: chart shows '{_chart_sym}' but {SYMBOL} (expected {_expected}) was requested — "
              f"symbol switch failed/timed out. NOT writing {ZONES_FILE} (would write the wrong instrument's "
              f"levels). Existing file kept.")
        sys.exit(1)
    cands = []   # (price, source-tag)
    pdh = pdl = None
    tf_bars = {}
    for tf, n, tag in [('D', 40, 'D'), ('240', 120, '4H'), ('60', 180, '1H'), ('15', 220, '15m'), ('5', 260, '5m')]:
        tv('timeframe', tf); b = tv('ohlcv', '-n', str(n)).get('bars', [])
        if not b: continue
        tf_bars[tf] = b
        if tf == '5':
            continue
        sh, sl = pivots(b)
        for p in sh[-6:]: cands.append((round(p, DECIMALS), tag))
        for p in sl[-6:]: cands.append((round(p, DECIMALS), tag))
        # NOTE: EMAs intentionally excluded as zone sources — they drift across the lookback, smear levels,
        # and inflate confluence (the old "x56" blobs). EMAs remain the scanner's trend filter, not static zones.
        if tf == 'D' and len(b) >= 2:
            pdh, pdl = round(b[-2]['high'], DECIMALS), round(b[-2]['low'], DECIMALS)
            cands += [(pdh, 'PDH'), (pdl, 'PDL')]
    tv('timeframe', '1')
    fib_zones = build_fib_zones(tf_bars)
    rstep = 100 * PIP   # round-number increment, pip-scaled (gold $10, EURUSD 0.01, US30 100, JPY 1.00)
    base = round(price / rstep) * rstep
    for k in (-2, -1, 0, 1, 2): cands.append((round(base + k*rstep, 5), 'round'))
    # cluster nearby levels
    cands.sort()
    clusters = []
    for p, src in cands:
        if clusters and p - clusters[-1]['lo'] <= MERGE:   # bound by cluster START so span can't exceed MERGE (no daisy-chain)
            c = clusters[-1]; c['hi'] = max(c['hi'], p); c['srcs'].append(src); c['ps'].append(p)
        else:
            clusters.append({'lo': p, 'hi': p, 'srcs': [src], 'ps': [p]})
    raw = []
    for c in clusters:
        if len(c['srcs']) >= 2 or any(s in ('PDH', 'PDL') for s in c['srcs']):   # multi-touch or prior-day extreme
            raw.append({'lo': round(c['lo']-PAD, DECIMALS), 'hi': round(c['hi']+PAD, DECIMALS), 'srcs': list(c['srcs']), 'ps': list(c['ps'])})
    # merge overlapping zones (same structure split across adjacent clusters) — avoids confluence inflation
    raw.sort(key=lambda z: z['lo']); merged = []
    for z in raw:
        if merged and z['lo'] <= merged[-1]['hi']:
            m = merged[-1]; m['hi'] = max(m['hi'], z['hi']); m['srcs'] += z['srcs']; m['ps'] += z['ps']
        else:
            merged.append(z)
    def fmt(z):
        mid = round(sum(z['ps'])/len(z['ps']), DECIMALS); srcs = sorted(set(z['srcs']))
        lo, hi = z['lo'], z['hi']
        if hi - lo > MAX_W:   # safety net: never let a zone exceed MAX_W; recenter tightly on the confluence mid
            lo, hi = round(mid - MAX_W/2, DECIMALS), round(mid + MAX_W/2, DECIMALS)
        return (lo, hi, f"{mid} ({'+'.join(srcs[:4])}, x{len(z['srcs'])})", mid)
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
        return (round(max(x['high'] for x in s), DECIMALS), round(min(x['low'] for x in s), DECIMALS), end.astimezone(dt.timezone.utc).hour)
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
        return (round(max(x['high'] for x in s), DECIMALS), round(min(x['low'] for x in s), DECIMALS), h2) if s else (None, None, None)
    asia_h, asia_l, asia_end = sess.get('asia') or fb(0, 7)
    london_h, london_l, london_end = sess.get('london') or fb(7, 16)
    ny_h, ny_l, ny_end = sess.get('ny') or fb(13, 22)
    # --- multi-TF SMC snapshot (LuxAlgo) — stored so trade-check consumes a STABLE snapshot (zones file),
    # not a flaky per-tick live read. LIVE refresh only: the backtest replay chart has no SMC indicator. ---
    smc_block = {}; smc_failed = False
    if smcmod and (not IS_BACKTEST or WITH_SMC):
        try:
            tf_snap = smcmod.read_smc_mtf(os.environ.get("TV_CHART", ""), price, base_tf="1", band=2000 * PIP)   # near-price window pip-normalised (gold ±200, EURUSD ±0.02, …)
            if not tf_snap:
                raise RuntimeError("SMC MTF snapshot is empty")
            smc_block = {'ts': time.time(), 'price': price, 'tf': tf_snap}
            tfsum = {k: f"box{len(v['boxes'])}/sw{len(v['swings'])}" for k, v in tf_snap.items()}
            print(f"  SMC: {tfsum}")
        except smcmod.SMCMissing as e:
            print(f"!! SMC MISSING — {e}", file=sys.stderr); smc_failed = True
        except Exception as e:
            print(f"!! SMC read failed: {e}", file=sys.stderr); smc_failed = True
        tv('timeframe', '1')   # restore (read_smc_mtf restores base_tf, but be explicit for the session/zone convention)
    # --- CLASSIC zones (zones_sd) — origin-candle supply/demand boxes + S/R levels, the SAME computation
    # draw_review draws, so the engine GRADES AGAINST exactly what's drawn. 4h + 1h, bar counts match draw_review. ---
    classic = {"zones": [], "sr": []}
    if zsd:
        try:
            tv('timeframe', '240'); b4 = tv('ohlcv', '-n', '80').get('bars', [])
            tv('timeframe', '60');  b1 = tv('ohlcv', '-n', '160').get('bars', [])
            tv('timeframe', '1')
            cur = (b1[-1]['close'] if b1 else (b4[-1]['close'] if b4 else price))
            classic = zsd.build_classic_zones([("4H", b4), ("1H", b1)], cur)
            print(f"  classic: {len(classic['zones'])} zones ({sum(1 for z in classic['zones'] if z['kl'])} KL), {len(classic['sr'])} S/R levels")
        except Exception as e:
            print(f"!! classic zones failed: {e}", file=sys.stderr)
    out = {'ts': time.time(), 'price': price, 'pdh': pdh, 'pdl': pdl,
           'asia_h': asia_h, 'asia_l': asia_l, 'london_h': london_h, 'london_l': london_l, 'ny_h': ny_h, 'ny_l': ny_l,
           'asia_end': asia_end, 'london_end': london_end, 'ny_end': ny_end,
           'htf_r': [[z[0], z[1], z[2]] for z in R], 'htf_s': [[z[0], z[1], z[2]] for z in S],
           'fib_zones': fib_zones,
           'smc': smc_block, 'sd_zones': classic['zones'], 'sd_sr': classic['sr']}
    json.dump(out, open(ZONES_FILE, 'w'), indent=1)
    print(f"wrote zones.json  asia={asia_h}/{asia_l}(end{asia_end}) london={london_h}/{london_l}(end{london_end}) ny={ny_h}/{ny_l}(end{ny_end})  src={'indicator' if sess else 'fallback-UTC'}")
    if smc_failed:   # fail LOUD (visible in cron logs) — but zones were still written so the engine keeps running
        sys.exit(1)

if __name__ == "__main__":
    main()
