#!/usr/bin/env python3
"""
FAST momentum scalp scanner for XAUUSD — targets ~50-100 pip bursts within ~10 min.
Reads the ACTIVE 1m chart. Detects, with a volatility gate (silent in dead tape):
  - Trendline break (support/resistance lines through recent swing pivots)
  - Range / triangle breakout (tight consolidation -> impulse out)
  - Double top / double bottom (neckline break)
  - Momentum impulse continuation
Outputs Entry / SL / TP1(+50) / TP2(+100).  1 pip = $0.10 (50 pips = $5 move).
Optionally draws the active trendlines:  python3 scalp_fast.py --draw
"""
import subprocess, json, os, sys, time, csv as _csv, datetime as _dt
TVDIR = os.path.expanduser("~/tradingview-mcp")
PIP = 0.10
MIN_TP = 50      # pips
VOL_MIN_RANGE10 = 40   # last 10 1m bars must span >= this many pips to allow a fast signal

# Higher-TF swing S/R map (matches the 1H/4H/Daily zones drawn on the chart). (lo, hi, label)
HTF_R = [(4459,4468,"R 4459-68 (15m+1H swing highs)"), (4470,4475,"R 4472 (15m EMA200 + 1H EMA50)"),
         (4483,4489,"R 4485-88 (1H EMA100 + 15m/1H highs)"), (4493,4501,"KEY R 4496-4500 (PDH + 4H/1H EMA200)"),
         (4511,4515,"R 4513 (1H high)"), (4538,4545,"R 4541 (1H/4H highs)")]
HTF_S = [(4446,4449,"S 4447 (15m EMA50 + 1H/4H lows)"), (4433,4439,"S 4433-39 (1H/15m swing lows)"),
         (4423,4427,"S 4424-26 (PDL + today-low multi-touch)"), (4398,4406,"S 4400 (4H swing low)"),
         (4375,4385,"BUY ZONE Daily EMA200 (~4380)"), (4360,4368,"S 4366 (4H/Daily low)")]
def near_htf(price, levels, tol=4):
    for lo, hi, lab in levels:
        if lo - tol <= price <= hi + tol: return (lo, hi, lab)
    return None

# --- v2 gold-specific reference levels (refresh ~daily) ---
PDH, PDL = 4496.7, 4426.4          # prior-day high / low
ASIA_H, ASIA_L = 4465.2, 4449.8    # Asian-session range (06-04, still forming at refresh — re-check near London open)
SESSION_UTC = set(range(7, 22))    # London+NY active hours (UTC); outside = quiet
NEWS_BLACKOUT = []                 # [(h1,m1,h2,m2),...] UTC windows to mute (manual)
CD_FILE = os.path.expanduser("~/.tv_fast_cd.json")
COOLDOWN_MIN = 5                   # no new signal for N minutes after one fires (anti-clustering)
WATCH_CD_FILE = os.path.expanduser("~/.tv_fast_watch.json")
WATCH_CD_MIN = 12                  # heads-up cooldown: don't re-ping the same zone area for N min
WATCH_NEW_ZONE_P = 15              # ...unless price moved >this many pips to a genuinely new zone
CHASE_LOOKBACK = 6                 # bars used as the "base" for the anti-chase extension check
MAX_CHASE_P = 60                   # skip a continuation entry if price already ran >this many pips off the base
DYN_TOL = 1.5                      # "at level" halo for dynamic POINT levels (VWAP/EMA/round/PDH/Asian) = ±15 pips
TP_BUFFER_P = 8                    # adaptive TP stops this many pips short of the next structure (don't aim into the wall)
MIN_ROOM_P = 25                    # skip a trade if usable room to the next structure is below this (bad R:R)
RSI_OB, RSI_OS = 78, 22            # RSI exhaustion gates — block continuation longs >OB / shorts <OS (anti blow-off)
VP_TF, VP_BARS = "30", 48          # volume-profile basis: 30m bars x48 (~1 day) for VPOC / value-area levels
ZONES_FILE = os.path.expanduser("~/tradingview-mcp/zones.json")
ZONES_TTL = 6*3600                 # auto-rebuild HTF zones (refresh_zones.py) when older than this
ZONES_MAX_AGE = 18*3600            # ...but still use a stale file up to this old rather than fall back

def _num(x):
    try: return float(str(x).replace(",", ""))
    except Exception: return None

def _heal_emas():
    """Ensure EMA 50/100/200 are all on the chart; add + set length for any that are missing."""
    present = []
    for s in tv("state").get("studies", []):
        if s.get("name") == "Moving Average Exponential":
            for inp in tv("indicator", "get", s["id"]).get("inputs", []):
                if inp.get("id") == "in_0":
                    try: present.append(int(inp["value"]))
                    except Exception: pass
    for L in (50, 100, 200):
        if L not in present:
            r = tv("indicator", "add", "Moving Average Exponential")
            nid = r.get("entity_id") or r.get("id")
            if nid: tv("indicator", "set", nid, "-i", json.dumps({"in_0": L}))

def read_chart_levels(closes):
    """One read of the data window -> session VWAP (+bands) and EMA 50/100/200, all taken from the
    chart's OWN indicators (not computed). Self-heals: re-adds any missing indicator. A quick internal
    EMA is used ONLY to label which plotted EMA line is which length (the VALUE used is the chart's)."""
    def parse(studies):
        vw = up = lo = rsi = None; emas = []
        for s in studies:
            n = s.get("name", ""); v = s.get("values", {})
            if "Volume Weighted" in n:
                vw, up, lo = _num(v.get("VWAP")), _num(v.get("Upper Band #1")), _num(v.get("Lower Band #1"))
            elif "Moving Average" in n:
                e = _num(v.get("EMA"))
                if e is not None: emas.append(e)
            elif "Relative Strength" in n:
                rsi = _num(v.get("RSI"))
        return vw, up, lo, emas, rsi
    vw, up, lo, emas, rsi = parse(tv("values").get("studies", []))
    if vw is None or len(emas) < 3 or rsi is None:        # self-heal then re-read
        if vw is None: tv("indicator", "add", "Volume Weighted Average Price")
        if len(emas) < 3: _heal_emas()
        if rsi is None: tv("indicator", "add", "Relative Strength Index")
        vw, up, lo, emas, rsi = parse(tv("values").get("studies", []))
    def ema(p):
        k = 2/(p+1); e = closes[0]
        for c in closes[1:]: e = c*k + e*(1-k)
        return e
    em = {50: None, 100: None, 200: None}
    if len(emas) == 3:
        # rank-match: chart EMAs and internal EMAs of the same series rank identically (shorter length
        # sits nearer recent price), so pairing by sorted rank is robust even though our EMA200 is
        # under-sampled from 180 bars — far safer than absolute-nearest in a tight cluster.
        order = sorted(emas)
        for rank, (_, L) in enumerate(sorted((ema(L), L) for L in (50, 100, 200))):
            em[L] = round(order[rank], 2)
    elif emas:                                            # fallback (extra/missing EMAs): absolute nearest
        for L in (50, 100, 200):
            ref = ema(L); em[L] = round(min(emas, key=lambda x: abs(x - ref)), 2)
    return vw, up, lo, em, rsi

VP_FILE = os.path.expanduser("~/.tv_fast_vp.json")
VP_TTL = 1200   # recompute the volume profile every 20 min (brief TF switch); cached in between

def _calc_vp(bars, bins=60):
    if len(bars) < 10: return (None, None, None)
    lo = min(x['low'] for x in bars); hi = max(x['high'] for x in bars)
    if hi <= lo: return (None, None, None)
    w = (hi - lo) / bins; vol = [0.0]*bins
    for x in bars:   # spread each bar's volume across the price bins it spans
        a = max(0, min(bins-1, int((x['low']-lo)/w))); z = max(0, min(bins-1, int((x['high']-lo)/w)))
        v = x.get('volume', 0) / (z-a+1)
        for i in range(a, z+1): vol[i] += v
    poc = max(range(bins), key=lambda i: vol[i])
    target = sum(vol)*0.70; a = z = poc; acc = vol[poc]
    while acc < target and (a > 0 or z < bins-1):   # grow value area toward the heavier side
        left = vol[a-1] if a > 0 else -1; right = vol[z+1] if z < bins-1 else -1
        if right >= left and z < bins-1: z += 1; acc += vol[z]
        elif a > 0: a -= 1; acc += vol[a]
        else: break
    at = lambda i: round(lo + (i+0.5)*w, 1)
    return (at(poc), at(z), at(a))   # vpoc, vah (value-area high), val (value-area low)

def _tpo_levels():
    """Read the Kioseff TPO profile rows from its labels (each carries the TPO letters at that price).
    POC = price with the most letters; value area = the 70% band around it. (None,None,None) if empty."""
    rows = []
    for s in tv("data", "labels", "--study-filter", "TPO").get("studies", []):
        for lb in s.get("labels", []):
            p = lb.get("price"); cnt = len(str(lb.get("text", "")).replace(" ", ""))
            if p and cnt: rows.append((round(p, 2), cnt))
    if not rows: return (None, None, None)
    rows.sort()
    idx = max(range(len(rows)), key=lambda i: rows[i][1])    # POC row
    target = sum(c for _, c in rows)*0.70; a = z = idx; acc = rows[idx][1]
    while acc < target and (a > 0 or z < len(rows)-1):
        left = rows[a-1][1] if a > 0 else -1; right = rows[z+1][1] if z < len(rows)-1 else -1
        if right >= left and z < len(rows)-1: z += 1; acc += rows[z][1]
        elif a > 0: a -= 1; acc += rows[a][1]
        else: break
    return (rows[idx][0], rows[z][0], rows[a][0])            # poc, vah, val

def volume_profile():
    """POC + value-area for confluence. The Kioseff TPO only renders on a high TF, so flip to VP_TF,
    SHOW the TPO, read it, HIDE it, restore 1m; fall back to a computed 30m volume profile if unread.
    Cached (VP_TTL). try/finally guarantees the chart is always restored to 1m (never stuck on 30m)."""
    try:
        c = json.load(open(VP_FILE))
        if time.time() - c.get("t", 0) < VP_TTL: return c.get("vpoc"), c.get("vah"), c.get("val")
    except Exception: pass
    tid = next((s["id"] for s in tv("state").get("studies", [])
                if "TPO" in s.get("name", "") or "Profile" in s.get("name", "")), None)
    poc = vah = val = None
    try:
        tv("timeframe", VP_TF)
        if tid: tv("indicator", "toggle", tid, "--show"); time.sleep(4)   # let the TPO render on 30m
        if tid: poc, vah, val = _tpo_levels()
        if poc is None:   # fallback: compute a volume profile from 30m bars
            poc, vah, val = _calc_vp(tv("ohlcv", "-n", str(VP_BARS)).get("bars", []))
        if tid: tv("indicator", "toggle", tid, "--hide")
    finally:
        tv("timeframe", "1")
    try: json.dump({"t": time.time(), "vpoc": poc, "vah": vah, "val": val}, open(VP_FILE, "w"))
    except Exception: pass
    return poc, vah, val

def load_zones():
    """Return (HTF_R, HTF_S, PDH, PDL) from auto-derived zones.json. Rebuilds it (refresh_zones.py)
    when stale (>ZONES_TTL); falls back to the hardcoded constants if no usable file exists.
    Each scan is a fresh process, so this re-applies every run."""
    z = None
    try:
        z = json.load(open(ZONES_FILE)); age = time.time() - z.get("ts", 0)
    except Exception:
        age = 1e12
    if age > ZONES_TTL:   # stale -> rebuild inline (only happens ~every 6h; switches TFs then restores 1m)
        try:
            subprocess.run(["python3", "refresh_zones.py"], cwd=TVDIR, capture_output=True, timeout=150)
            z = json.load(open(ZONES_FILE)); age = time.time() - z.get("ts", 0)
        except Exception: pass
    if z and z.get("htf_r") and age < ZONES_MAX_AGE:
        return ([tuple(x) for x in z["htf_r"]], [tuple(x) for x in z["htf_s"]],
                z.get("pdh") or PDH, z.get("pdl") or PDL)
    return list(HTF_R), list(HTF_S), PDH, PDL

def in_session(ts):
    return _dt.datetime.utcfromtimestamp(ts).hour in SESSION_UTC

def in_news(ts):
    t = _dt.datetime.utcfromtimestamp(ts); m = t.hour*60 + t.minute
    return any(h1*60+m1 <= m <= h2*60+m2 for h1,m1,h2,m2 in NEWS_BLACKOUT)

# --- feature flags (toggle strategies/filters in flags.json, no code edits) ---
FLAGS_FILE = os.path.expanduser("~/tradingview-mcp/flags.json")
DEFAULT_FLAGS = {"trendline_break": True, "range_breakout": True, "double_top_bottom": True,
                 "momentum_impulse": True, "liquidity_sweep": True, "break_retest": True, "vwap": True,
                 "session_breakout": True, "extended_levels": True, "ema_levels": True,
                 "anti_chase": True, "adaptive_tp": True, "rsi_filter": True, "trend_regime": True,
                 "confluence": True, "volume_profile": True,
                 "session_filter": True, "news_filter": True, "volume_filter": True}
def load_flags():
    f = dict(DEFAULT_FLAGS)
    try: f.update(json.load(open(FLAGS_FILE)))
    except Exception: pass
    return f
PAT_FLAG = {"trendline": "trendline_break", "range/triangle": "range_breakout", "double": "double_top_bottom",
            "impulse": "momentum_impulse", "sweep": "liquidity_sweep", "retest": "break_retest",
            "VWAP": "vwap", "breakout": "session_breakout", "breakdown": "session_breakout"}
def flag_for(why):
    for k, v in PAT_FLAG.items():
        if k in why: return v
    return None

def alert_sound(n=3):
    """Audible alert on a fast signal (macOS afplay)."""
    for _ in range(n):
        try: subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], timeout=5)
        except Exception: pass

TG_CONF = os.path.expanduser("~/tradingview-mcp/telegram_config.json")
TG_STATE = os.path.expanduser("~/.tv_fast_tg.json")
TRADE_STATE = os.path.expanduser("~/.tv_fast_trade.json")

def _tg_text(text):
    """Plain text Telegram send (no dedup, no photo) — for trade-management events."""
    try:
        cfg = json.load(open(TG_CONF)); tok, cid = cfg.get("bot_token"), cfg.get("chat_id")
        if tok and cid:
            subprocess.run(["curl", "-s", f"https://api.telegram.org/bot{tok}/sendMessage",
                            "-d", f"chat_id={cid}", "--data-urlencode", f"text={text}"], timeout=15)
    except Exception:
        pass

SIGNALS_LOG = os.path.expanduser("~/tradingview-mcp/signals_log.csv")
SIG_COLS = ["id", "time", "side", "grade", "pattern", "entry", "sl", "tp1", "rng10", "body_p", "htf", "result", "exit", "pips"]

def log_signal(row):
    """Upsert a row (by id) into signals_log.csv — the auto-learn dataset."""
    rows = []
    if os.path.exists(SIGNALS_LOG):
        try: rows = list(_csv.DictReader(open(SIGNALS_LOG)))
        except Exception: rows = []
    found = False
    for r in rows:
        if r.get("id") == str(row["id"]):
            r.update({k: str(v) for k, v in row.items()}); found = True
    if not found:
        rows.append({k: str(v) for k, v in row.items()})
    try:
        w = _csv.DictWriter(open(SIGNALS_LOG, "w", newline=""), fieldnames=SIG_COLS); w.writeheader()
        for r in rows: w.writerow({k: r.get(k, "") for k in SIG_COLS})
    except Exception: pass

def set_active_trade(side, entry, sl, tp1, tp2, sid):
    try:   # finalize any still-open prior trade that this new signal supersedes
        old = json.load(open(TRADE_STATE))
        if old.get("active") and old.get("id") and old.get("id") != sid:
            if old.get("tp1_hit"):   # already banked +50 — keep the win, don't downgrade to 'superseded'
                ot1 = old["tp1"]; tp = round((old["entry"]-ot1)/PIP if old["side"]=="SHORT" else (ot1-old["entry"])/PIP)
                log_signal({"id": old["id"], "result": "TP1", "exit": round(ot1, 1), "pips": tp})
            else:
                oe = old["entry"]; pips = round((oe-entry)/PIP if old["side"] == "SHORT" else (entry-oe)/PIP)
                log_signal({"id": old["id"], "result": "superseded", "exit": round(entry, 1), "pips": pips})
    except Exception: pass
    try: json.dump({"active": True, "id": sid, "side": side, "entry": entry, "sl": sl,
                    "tp1": tp1, "tp2": tp2, "tp1_hit": False, "t0": time.time()}, open(TRADE_STATE, "w"))
    except Exception: pass

def check_active_trade(price):
    """Alert on TP1/TP2/SL; finalize the signals_log outcome (incl. 12-min timeout).
    Once TP1 is banked the stop moves to breakeven and the logged result can only be TP1/TP2 —
    a later reversal can never overwrite a partial win with an 'SL' loss."""
    try: t = json.load(open(TRADE_STATE))
    except Exception: return
    if not t.get("active"): return
    side, e, sl, tp1, tp2 = t["side"], t["entry"], t["sl"], t["tp1"], t["tp2"]
    sid = t.get("id"); tp1_hit = t.get("tp1_hit"); PP = lambda x: round((e - x)/PIP if side == "SHORT" else (x - e)/PIP)
    hit_sl  = price >= sl  if side == "SHORT" else price <= sl
    hit_tp2 = price <= tp2 if side == "SHORT" else price >= tp2
    hit_tp1 = price <= tp1 if side == "SHORT" else price >= tp1
    label = None
    if hit_tp2:
        label, lvl, res = "🎯 TP2 (+100p)", tp2, "TP2"; t["active"] = False
    elif hit_sl:
        t["active"] = False
        if tp1_hit:   # remainder stopped at breakeven AFTER banking the +50 partial — still a win, log as TP1
            label, lvl, res = "🟰 BE (after TP1)", tp1, "TP1"
        else:
            label, lvl, res = "❌ SL", sl, "SL"
    elif hit_tp1 and not tp1_hit:
        label, lvl, res = "✅ TP1 (+50p)", tp1, "TP1"; t["tp1_hit"] = True; t["sl"] = e   # stop -> breakeven
    if label:
        if res == "SL":            extra = "  → trade closed."
        elif "BE" in label:        extra = f"  → remainder out at breakeven ({e}); +50p partial kept."
        elif res == "TP1":         extra = "  → take partial, SL to breakeven."
        else:                      extra = "  → trade closed."
        _tg_text(f"{label} — GOLD {side} hit {lvl} (entry {e}, now {price}).{extra}")
        if sid: log_signal({"id": sid, "result": res, "exit": round(lvl, 1), "pips": PP(lvl)})
    elif time.time() - t.get("t0", time.time()) > 720:   # 12-min timeout
        t["active"] = False
        res, exit_px = ("TP1", tp1) if tp1_hit else ("timeout", price)   # tp1 already banked -> keep the win
        if sid: log_signal({"id": sid, "result": res, "exit": round(exit_px, 1), "pips": PP(exit_px)})
    try: json.dump(t, open(TRADE_STATE, "w"))
    except Exception: pass

def notify_telegram(caption, dedup_key):
    """Send the signal + chart photo to Telegram. De-dups so the same signal doesn't spam each bar."""
    try:
        cfg = json.load(open(TG_CONF)); tok, cid = cfg.get("bot_token"), cfg.get("chat_id")
    except Exception:
        return
    if not tok or not cid:
        return
    try:
        if json.load(open(TG_STATE)).get("key") == dedup_key:
            return
    except Exception:
        pass
    try: json.dump({"key": dedup_key}, open(TG_STATE, "w"))
    except Exception: pass
    shot = tv("screenshot").get("file_path")
    try:
        if shot and os.path.exists(shot):
            subprocess.run(["curl", "-s", "-F", f"chat_id={cid}", "-F", f"photo=@{shot}",
                            "-F", f"caption={caption}", f"https://api.telegram.org/bot{tok}/sendPhoto"], timeout=25)
        else:
            subprocess.run(["curl", "-s", f"https://api.telegram.org/bot{tok}/sendMessage",
                            "-d", f"chat_id={cid}", "--data-urlencode", f"text={caption}"], timeout=15)
    except Exception:
        pass

def tv(*a):
    r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=30)
    try: return json.loads(r.stdout)
    except Exception: return {}

def pivots(b, L=3, R=3):
    sh, sl = [], []
    for i in range(L, len(b) - R):
        if all(b[i]['high'] >= b[i-k]['high'] for k in range(1, L+1)) and all(b[i]['high'] >= b[i+k]['high'] for k in range(1, R+1)):
            sh.append((i, b[i]['high']))
        if all(b[i]['low'] <= b[i-k]['low'] for k in range(1, L+1)) and all(b[i]['low'] <= b[i+k]['low'] for k in range(1, R+1)):
            sl.append((i, b[i]['low']))
    return sh, sl

def rsi_series(closes, n=14):
    """Wilder RSI aligned to `closes` (None during warmup). Used only to detect divergence —
    the live RSI value for the exhaustion gate is read from the chart indicator."""
    N = len(closes); out = [None]*N
    if N < n+1: return out
    gains = [max(closes[i]-closes[i-1], 0.0) for i in range(1, N)]
    losses = [max(closes[i-1]-closes[i], 0.0) for i in range(1, N)]
    ag = sum(gains[:n])/n; al = sum(losses[:n])/n
    out[n] = 100 - 100/(1 + (ag/al if al else 999))
    for i in range(n+1, N):
        ag = (ag*(n-1)+gains[i-1])/n; al = (al*(n-1)+losses[i-1])/n
        out[i] = 100 - 100/(1 + (ag/al if al else 999))
    return out

def rsi_divergence(b, side):
    """Bullish div (LONG): price lower-low but RSI higher-low at the last 2 swing lows. Mirror for SHORT."""
    rs = rsi_series([x['close'] for x in b]); sh, sl = pivots(b)
    if side == "LONG" and len(sl) >= 2:
        (i1, p1), (i2, p2) = sl[-2], sl[-1]
        return bool(rs[i1] and rs[i2] and p2 < p1 and rs[i2] > rs[i1])
    if side == "SHORT" and len(sh) >= 2:
        (i1, p1), (i2, p2) = sh[-2], sh[-1]
        return bool(rs[i1] and rs[i2] and p2 > p1 and rs[i2] < rs[i1])
    return False

def line_through(p1, p2):
    (x1, y1), (x2, y2) = p1, p2
    if x2 == x1: return None
    m = (y2 - y1) / (x2 - x1)
    return m, y1 - m * x1

def proj(line, x): return line[0] * x + line[1]

def main():
    draw = "--draw" in sys.argv
    DRY = "--dry" in sys.argv   # test mode: compute + print only, NO telegram/log/sound/state
    FL = load_flags()
    global HTF_R, HTF_S, PDH, PDL
    HTF_R, HTF_S, PDH, PDL = load_zones()   # auto-derived zones (rebuilt every ~6h) override the hardcoded fallback
    tv("timeframe", "1")
    price = tv("quote").get("last")
    b = tv("ohlcv", "-n", "180").get("bars", [])
    if price is None or len(b) < 40:
        print("ERR: no data"); return
    n = len(b); last = b[-1]
    if not DRY: check_active_trade(price)   # alert TP1/TP2/SL on any live signalled trade
    # --- volatility gate ---
    rng10 = (max(x['high'] for x in b[-10:]) - min(x['low'] for x in b[-10:])) / PIP
    atr = sum(x['high'] - x['low'] for x in b[-14:]) / 14 / PIP
    # --- momentum candle ---
    body = last['close'] - last['open']; body_pips = abs(body) / PIP
    avgbody = sum(abs(x['close'] - x['open']) for x in b[-20:]) / 20 / PIP
    strong = body_pips > 1.6 * max(avgbody, 0.5)
    bull = body > 0
    sh, sl = pivots(b)
    # --- trendlines through last 2 swing highs / lows ---
    res_tl = line_through(sh[-2], sh[-1]) if len(sh) >= 2 else None
    sup_tl = line_through(sl[-2], sl[-1]) if len(sl) >= 2 else None
    res_at = round(proj(res_tl, n-1), 2) if res_tl else None
    sup_at = round(proj(sup_tl, n-1), 2) if sup_tl else None
    # --- consolidation range (last 15 bars) ---
    hi15 = max(x['high'] for x in b[-15:]); lo15 = min(x['low'] for x in b[-15:])
    range15 = (hi15 - lo15) / PIP
    tight = range15 < 35
    # --- double top / bottom (last 3 swing highs/lows) ---
    dtop = len(sh) >= 2 and abs(sh[-1][1] - sh[-2][1]) / PIP < 8
    dbot = len(sl) >= 2 and abs(sl[-1][1] - sl[-2][1]) / PIP < 8

    # --- chart indicators: session VWAP (+bands), EMA 50/100/200, RSI — read not computed (self-heal) ---
    vw, vw_up, vw_lo, em, rsi = read_chart_levels([x['close'] for x in b])
    e50, e100, e200 = em.get(50), em.get(100), em.get(200)
    up_stack = bool(e50 and e100 and e200 and e50 > e100 > e200)   # EMA stack = uptrend regime
    dn_stack = bool(e50 and e100 and e200 and e50 < e100 < e200)   # EMA stack = downtrend regime
    regime = "UP" if up_stack else ("DOWN" if dn_stack else "flat")
    vpoc, vah, val = volume_profile() if FL.get("volume_profile", True) else (None, None, None)
    r10 = round(price/10)*10; near_round = r10 if abs(r10-price) < 2 else None
    vol = last.get('volume', 0); avgvol = sum(x.get('volume', 0) for x in b[-20:])/20
    vol_ok = (vol > avgvol) if avgvol else True
    ts = last['time']; sess_ok = in_session(ts); news = in_news(ts)
    asian_now = not sess_ok   # overnight/Asian window (off London-NY) — Asian range still forming, don't use it as a level
    # level map: wide HTF zones (tol=4) + dynamic POINT levels (VWAP/EMA/round#/PDH/Asian, tight DYN_TOL)
    ptR, ptS = [], []   # dynamic point levels — kept separate so they get a tight halo, not the zone width
    if FL["extended_levels"]:
        ext = [(PDH,"prior-day high"), (PDL,"prior-day low"), (vw,"VWAP"), (near_round,f"round {near_round}")]
        if vw_up: ext.append((vw_up, "VWAP upper band"))   # mean-reversion: tag of upper band favors shorts
        if vw_lo: ext.append((vw_lo, "VWAP lower band"))   # tag of lower band favors longs
        if FL.get("ema_levels", True):                     # EMA 50/100/200 as dynamic S/R (read off chart)
            ext += [(e50, "EMA50"), (e100, "EMA100"), (e200, "EMA200")]
        ext += [(vpoc, "VPOC"), (vah, "value-area high"), (val, "value-area low")]   # volume-profile levels
        if not asian_now:   # only treat the Asian range as S/R AFTER the session completes
            ext += [(ASIA_H,"Asian high"), (ASIA_L,"Asian low")]
        for lvl, lab in ext:
            if lvl is None: continue
            (ptR if lvl >= price else ptS).append((lvl, lvl, lab))
    # HTF zones keep their intended wide tolerance; dynamic point-levels get the tight one
    at_R = near_htf(price, HTF_R) or near_htf(price, ptR, tol=DYN_TOL)
    at_S = near_htf(price, HTF_S) or near_htf(price, ptS, tol=DYN_TOL)
    # confluence: how many distinct levels sit right at price (used to strengthen/justify the grade)
    conf_R = len([1 for lo,hi,_ in HTF_R if lo-4<=price<=hi+4] + [1 for p,_,_ in ptR if abs(p-price)<=DYN_TOL])
    conf_S = len([1 for lo,hi,_ in HTF_S if lo-4<=price<=hi+4] + [1 for p,_,_ in ptS if abs(p-price)<=DYN_TOL])
    # next structure above / below entry (for adaptive TP) — horizontal walls only.
    # EMAs and VWAP are dynamic lines price flows THROUGH, so they don't cap a target.
    is_wall = lambda lab: not ("EMA" in lab or "VWAP" in lab)
    R_refs = [v for lo,hi,_ in HTF_R for v in (lo,hi)] + [p for p,_,lab in ptR if is_wall(lab)]
    S_refs = [v for lo,hi,_ in HTF_S for v in (lo,hi)] + [p for p,_,lab in ptS if is_wall(lab)]
    nextR = min([r for r in R_refs if r > price + 3*PIP], default=None)
    nextS = max([s for s in S_refs if s < price - 3*PIP], default=None)
    print(f"\n[{_dt.datetime.utcnow():%Y-%m-%d %H:%M:%S}Z]  PRICE {price}  TF=1m  range10={rng10:.0f}p  atr={atr:.1f}p  lastBody={body_pips:.0f}p({'bull' if bull else 'bear'}) strong={strong} vol_ok={vol_ok}")
    print(f"resTL@{res_at}  supTL@{sup_at}  range15={range15:.0f}p tight={tight}  dblTop={dtop} dblBot={dbot}  VWAP={vw}{f' [{vw_lo}/{vw_up}]' if vw_up else ''}  EMA50/100/200={em.get(50)}/{em.get(100)}/{em.get(200)}  session={'ON' if sess_ok else 'off'}")
    print(f"RSI={rsi}  regime={regime}(EMA stack)  VPOC/VAH/VAL={vpoc}/{vah}/{val}  confluence R{conf_R}/S{conf_S}  nextR={nextR} nextS={nextS}")
    print(f"HTF: {'@R '+at_R[2] if at_R else ''}{'@S '+at_S[2] if at_S else ''}{'(open space)' if not at_R and not at_S else ''}")

    if draw:
        if res_tl and len(sh) >= 2:
            tv("draw","shape","--type","trend_line","--price",str(sh[-2][1]),"--time",str(b[sh[-2][0]]['time']),
               "--price2",str(sh[-1][1]),"--time2",str(b[sh[-1][0]]['time']))
        if sup_tl and len(sl) >= 2:
            tv("draw","shape","--type","trend_line","--price",str(sl[-2][1]),"--time",str(b[sl[-2][0]]['time']),
               "--price2",str(sl[-1][1]),"--time2",str(b[sl[-1][0]]['time']))
        print("(trendlines drawn)")

    # --- volatility gate ---
    if rng10 < VOL_MIN_RANGE10:
        htf = at_R or at_S
        extra = f" — but price at {htf[2]}, watch for a burst there" if htf else ""
        print(f"\n>> TOO QUIET: last 10 1m bars only {rng10:.0f}p (<{VOL_MIN_RANGE10}p). No fast scalp{extra}.")
        return

    if FL["news_filter"] and news:
        print("\n>> NEWS BLACKOUT — muted (manual window)."); return

    try: cd_t = json.load(open(CD_FILE)).get("t", 0)
    except Exception: cd_t = 0
    cd_left = COOLDOWN_MIN*60 - (time.time() - cd_t)
    if cd_left > 0:
        print(f"\n>> COOLDOWN: {cd_left/60:.0f}m left since last signal — no new setups (anti-cluster)."); return

    setups = []
    buf = 2 * PIP  # break buffer
    # 1) Trendline break (with strong momentum candle)
    if res_at and strong and bull and last['close'] > res_at + buf and last['open'] <= res_at + buf:
        setups.append(("LONG", "resistance-trendline break", last['close'], lo15))
    if sup_at and strong and (not bull) and last['close'] < sup_at - buf and last['open'] >= sup_at - buf:
        setups.append(("SHORT", "support-trendline break", last['close'], hi15))
    # 2) Range / triangle breakout
    if tight and strong and bull and last['close'] > hi15:
        setups.append(("LONG", "range/triangle breakout", last['close'], lo15))
    if tight and strong and (not bull) and last['close'] < lo15:
        setups.append(("SHORT", "range/triangle breakout", last['close'], hi15))
    # 3) Double bottom (break above the intervening high) / double top
    if dbot and strong and bull and last['close'] > hi15:
        setups.append(("LONG", "double-bottom break", last['close'], min(sl[-1][1], sl[-2][1])))
    if dtop and strong and (not bull) and last['close'] < lo15:
        setups.append(("SHORT", "double-top break", last['close'], max(sh[-1][1], sh[-2][1])))
    # 4) Momentum impulse (2 strong same-dir closes)
    p2 = b[-2]
    p2body = (p2['close'] - p2['open']) / PIP
    if strong and bull and p2body > 1.0 * max(avgbody, 0.5):
        setups.append(("LONG", "momentum impulse", last['close'], min(last['low'], p2['low'])))
    if strong and (not bull) and p2body < -1.0 * max(avgbody, 0.5):
        setups.append(("SHORT", "momentum impulse", last['close'], max(last['high'], p2['high'])))
    # 5) Liquidity-sweep reversal (gold's signature: spike through a recent extreme, then reclaim)
    look = b[-22:-2] if len(b) >= 24 else b[:-2]
    if look:
        sw_hi = max(x['high'] for x in look); sw_lo = min(x['low'] for x in look)
        rcl = 4 * PIP   # must close >=4p back INSIDE the swept level (genuine rejection, not a breakout run)
        if strong and not bull and last['high'] > sw_hi and last['close'] < sw_hi - rcl and near_htf(sw_hi, HTF_R):
            setups.append(("SHORT", "liquidity-sweep reversal", last['close'], last['high']))
        if strong and bull and last['low'] < sw_lo and last['close'] > sw_lo + rcl and near_htf(sw_lo, HTF_S):
            setups.append(("LONG", "liquidity-sweep reversal", last['close'], last['low']))
    # 6) Break-and-retest (broken swing level retested from the other side, rejected)
    if len(sh) >= 1:
        lv = sh[-1][1]
        if strong and bull and any(x['close'] > lv for x in b[-8:-1]) and last['low'] <= lv + 3*PIP and last['close'] > lv:
            setups.append(("LONG", "break-and-retest", last['close'], lv - 3*PIP))
    if len(sl) >= 1:
        lv = sl[-1][1]
        if strong and not bull and any(x['close'] < lv for x in b[-8:-1]) and last['high'] >= lv - 3*PIP and last['close'] < lv:
            setups.append(("SHORT", "break-and-retest", last['close'], lv + 3*PIP))
    # 7) VWAP rejection / bounce
    if vw:
        if strong and not bull and last['high'] >= vw and last['close'] < vw:
            setups.append(("SHORT", "VWAP rejection", last['close'], last['high']))
        if strong and bull and last['low'] <= vw and last['close'] > vw:
            setups.append(("LONG", "VWAP bounce", last['close'], last['low']))
    # 8) Asian-range / prior-day breakout (Asian range only valid AFTER the session, not while forming)
    up_lv = [(PDH, "prior-day-high")] + ([(ASIA_H, "Asian-range")] if not asian_now else [])
    dn_lv = [(PDL, "prior-day-low")] + ([(ASIA_L, "Asian-range")] if not asian_now else [])
    for lv, lab in up_lv:
        if strong and bull and last['open'] <= lv and last['close'] > lv:
            setups.append(("LONG", f"{lab} breakout", last['close'], lo15))
    for lv, lab in dn_lv:
        if strong and not bull and last['open'] >= lv and last['close'] < lv:
            setups.append(("SHORT", f"{lab} breakdown", last['close'], hi15))
    # volume filter: breakouts/breaks need above-avg volume; reversals (sweep/retest/VWAP) exempt
    if FL["volume_filter"] and not vol_ok:
        setups = [s for s in setups if any(w in s[1] for w in ("sweep", "retest", "VWAP"))]
    # feature-flag filter: drop any setup whose strategy is toggled off
    setups = [s for s in setups if FL.get(flag_for(s[1]) or "", True)]

    # anti-chase: don't enter a CONTINUATION setup after price has already run far off its base
    # (avoids buying the top / selling the bottom of a vertical spike). Reversals fade extension -> exempt.
    if FL.get("anti_chase", True) and setups:
        base_lo = min(x['low'] for x in b[-CHASE_LOOKBACK:]); base_hi = max(x['high'] for x in b[-CHASE_LOOKBACK:])
        ext_up = (price - base_lo)/PIP; ext_dn = (base_hi - price)/PIP
        def chasing(side, why):
            if not any(k in why for k in ("trendline", "breakout", "breakdown", "impulse", "double")):
                return False   # sweep / VWAP / retest are reversals — they trade the turn, exempt
            return ext_up > MAX_CHASE_P if side == "LONG" else ext_dn > MAX_CHASE_P
        kept = []
        for s in setups:
            if chasing(s[0], s[1]):
                run = ext_up if s[0] == "LONG" else ext_dn
                print(f">> SKIP CHASE: {s[0]} [{s[1]}] — price already ran {run:.0f}p off the {CHASE_LOOKBACK}-bar base (>{MAX_CHASE_P}p); too late, would be buying the top.")
            else:
                kept.append(s)
        setups = kept

    # RSI exhaustion gate: don't chase a continuation into an overbought/oversold blow-off (reversals exempt)
    if FL.get("rsi_filter", True) and rsi is not None and setups:
        kept = []
        for s in setups:
            cont = any(k in s[1] for k in ("trendline", "breakout", "breakdown", "impulse", "double"))
            if cont and s[0] == "LONG" and rsi > RSI_OB:
                print(f">> SKIP RSI: LONG [{s[1]}] blocked — RSI {rsi:.0f} > {RSI_OB} (overbought blow-off).")
            elif cont and s[0] == "SHORT" and rsi < RSI_OS:
                print(f">> SKIP RSI: SHORT [{s[1]}] blocked — RSI {rsi:.0f} < {RSI_OS} (oversold capitulation).")
            else:
                kept.append(s)
        setups = kept

    if not setups:
        htf = at_R or at_S
        if htf:
            print(f"\n>> HTF WATCH: price at {htf[2]} — good-trade location; a momentum trigger here = A+. Waiting.")
            sidehint = "SHORT" if at_R else "LONG"
            # heads-up cooldown: don't spam as price wiggles across overlapping levels (round#, zone, VWAP band).
            # Only re-ping if WATCH_CD_MIN elapsed OR price moved to a genuinely new zone (>WATCH_NEW_ZONE_P away).
            try: w = json.load(open(WATCH_CD_FILE))
            except Exception: w = {}
            new_zone = abs(price - w.get("price", 0)) > WATCH_NEW_ZONE_P and htf[2] != w.get("label")
            recent = (time.time() - w.get("t", 0)) < WATCH_CD_MIN*60
            if recent and not new_zone:
                print(f">> heads-up suppressed (within {WATCH_CD_MIN}m of last ping, same ~zone)."); return
            wa = "🟢⬆️" if sidehint == "LONG" else "🔴⬇️"
            wmsg = (f"{wa} 👀 GOLD — SETUP FORMING ({sidehint})\nPrice at {htf[2]} (~{price}).\n"
                    f"Get ready — I'll send the CONFIRMED entry (with SL/TP) when a {sidehint.lower()} trigger fires.")
            if not DRY:
                notify_telegram(wmsg, f"watch|{htf[2]}")
                try: json.dump({"t": time.time(), "price": price, "label": htf[2]}, open(WATCH_CD_FILE, "w"))
                except Exception: pass
        else:
            print("\n>> NO FAST SETUP: volatility OK but no break/pattern/impulse trigger this bar.")
        return

    # take the first (priority order above); build the trade
    side, why, entry, struct = setups[0]
    entry = round(entry, 2)
    # grade by alignment with the higher-TF map
    htf_note = ""; grade = "B (open space)"
    if side == "LONG":
        if at_S: htf_note = f" | A+ bounce at HTF support [{at_S[2]}]"; grade = "A+"
        elif at_R:
            if last['close'] > at_R[1]: htf_note = f" | A break above HTF resistance [{at_R[2]}]"; grade = "A"
            else: htf_note = f" | LONG into HTF resistance [{at_R[2]}]"; grade = "C-into-zone"
    else:
        if at_R: htf_note = f" | A+ rejection at HTF resistance [{at_R[2]}]"; grade = "A+"
        elif at_S:
            if last['close'] < at_S[0]: htf_note = f" | A break below HTF support [{at_S[2]}]"; grade = "A"
            else: htf_note = f" | SHORT into HTF support [{at_S[2]}]"; grade = "C-into-zone"
    if grade == "C-into-zone":
        print(f"\n>> SKIP: {side} into {'resistance' if side=='LONG' else 'support'} — counter-zone poke, not a real break (low quality)."); return

    is_rev = any(k in why for k in ("sweep", "VWAP", "retest"))
    # #4 confluence — multiple stacked levels at price strengthen the grade
    conf = conf_S if side == "LONG" else conf_R
    if FL.get("confluence", True) and conf >= 2:
        htf_note += f" | x{conf} confluence"
        if grade == "A": grade = "A+"
        elif grade.startswith("B"): grade = "A"
    # #2b RSI divergence at a level upgrades a reversal to A+
    if FL.get("rsi_filter", True) and is_rev and rsi is not None and rsi_divergence(b, side):
        htf_note += " | RSI divergence"; grade = "A+" if not grade.startswith("A+") else grade
    # #3 trend-regime — counter-trend needs A+; with-trend pullback gets a boost
    if FL.get("trend_regime", True) and regime != "flat":
        counter = (side == "LONG" and regime == "DOWN") or (side == "SHORT" and regime == "UP")
        with_trend = (side == "LONG" and regime == "UP") or (side == "SHORT" and regime == "DOWN")
        if counter and not grade.startswith("A+"):
            print(f"\n>> SKIP COUNTER-TREND: {side} {grade} against {regime} EMA stack — only A+ counter-trend allowed."); return
        if counter: htf_note += f" | counter-{regime} (A+ only)"
        elif with_trend:
            htf_note += f" | with {regime} trend"
            if grade.startswith("B"): grade = "A"
    if FL["session_filter"] and not sess_ok and not grade.startswith("A+"):
        print(f"\n>> OFF-SESSION ({side} {grade}) — skipped (only A+ trades outside London/NY)."); return
    if vol_ok and "open space" in grade: grade = "B+vol"   # volume gives a low-grade setup a small boost

    # --- #1 adaptive TP/SL: cap targets just short of the next structure; skip cramped trades ---
    if side == "LONG":
        sl_lvl = round(max(min(struct, entry - 30*PIP), entry - 35*PIP), 2); wall = nextR
    else:
        sl_lvl = round(min(max(struct, entry + 30*PIP), entry + 35*PIP), 2); wall = nextS
    if FL.get("adaptive_tp", True) and wall is not None:
        room = abs(wall - entry)/PIP - TP_BUFFER_P
        if room < MIN_ROOM_P:
            print(f"\n>> SKIP CRAMPED: {side} {grade} — only {room:.0f}p clean room to next structure {wall} (<{MIN_ROOM_P}p R:R too poor)."); return
        tp2_p = min(100, room); tp1_p = min(50, tp2_p*0.6)
    else:
        tp2_p, tp1_p = 100, 50
    if side == "LONG":
        tp1 = round(entry + tp1_p*PIP, 2); tp2 = round(entry + tp2_p*PIP, 2)
    else:
        tp1 = round(entry - tp1_p*PIP, 2); tp2 = round(entry - tp2_p*PIP, 2)
    risk = abs(entry - sl_lvl) / PIP
    print(f"\n>> FAST SIGNAL: {side} [{grade}] [{why}]{htf_note}")
    print(f"   Entry {entry} | SL {sl_lvl} ({risk:.0f}p) | TP1 {tp1} (+{tp1_p:.0f}p) | TP2 {tp2} (+{tp2_p:.0f}p)")
    print(f"   RULE: exit if TP1 not hit within ~10 min (speed thesis failed).")
    if DRY:
        print("   [DRY RUN — no telegram/log/state]"); return
    alert_sound(3)   # audible alert
    arrow = "🟢⬆️" if side == "LONG" else "🔴⬇️"
    msg = (f"{arrow} GOLD — CONFIRMED {side} [{grade}]\n{why}{htf_note}\n\n"
           f"Entry: {entry}\n"
           f"SL: {sl_lvl} ({risk:.0f}p)\n"
           f"TP1: {tp1} (+{tp1_p:.0f}p)\n"
           f"TP2: {tp2} (+{tp2_p:.0f}p)\n\n"
           f"Rule: exit if TP1 not hit in ~10 min.")
    notify_telegram(msg, f"signal|{side}|{round(entry)}|{why}")
    sid = int(time.time())
    hz = at_R or at_S   # the actual extended level that drove the grade (incl. VWAP/round#/PDH/Asian)
    log_signal({"id": sid, "time": _dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "side": side, "grade": grade, "pattern": why, "entry": entry, "sl": sl_lvl, "tp1": tp1,
                "rng10": round(rng10), "body_p": round(body_pips), "htf": hz[2] if hz else "open",
                "result": "PENDING", "exit": "", "pips": ""})
    set_active_trade(side, entry, sl_lvl, tp1, tp2, sid)   # track for TP/SL + outcome logging
    try: json.dump({"t": time.time()}, open(CD_FILE, "w"))   # start cooldown
    except Exception: pass

if __name__ == "__main__":
    # single-instance lock: never let two scans overlap and fight over the chart timeframe
    LOCK = os.path.expanduser("~/.tv_fast.lock")
    if os.path.exists(LOCK):
        try:
            if time.time() - os.path.getmtime(LOCK) < 50:
                print("skip: another scan is active"); sys.exit()
        except Exception: pass
    try:
        open(LOCK, "w").close(); main()
    finally:
        try: os.remove(LOCK)
        except Exception: pass
