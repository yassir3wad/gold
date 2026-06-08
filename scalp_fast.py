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
import subprocess, json, os, sys, time, csv as _csv, datetime as _dt, math
TVDIR = os.path.expanduser("~/tradingview-mcp")
try:
    sys.path.insert(0, TVDIR); import news as newsmod   # FF economic-calendar blackout (cache-only, no fetch in scanner)
except Exception: newsmod = None
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import smc as smcmod   # SMC + Auto-Trendlines confluence
except Exception: smcmod = None
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tpo as tpomod   # prior-day VAH/VAL/POC from the TPO indicator
except Exception: tpomod = None
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import va_store as vastore   # reliable prior-day value-area cache (DB)
except Exception: vastore = None
try:
    import va_state as vastate   # Rules 6/7: prior-VA Level State (Untested/Rejected/Accepted/Flipped)
except Exception: vastate = None
try:
    import va_reject as vareject   # entry #13: VWAP value-area rejection (docs/gold-vwap-strategy.md)
except Exception: vareject = None
try:
    import draw_overlay as dovr   # live-chart overlay: prior VA (+Level State) + SP + SMC order blocks
except Exception: dovr = None
try:
    import confidence as confmod   # 0-10 confidence score (aggregates all confluence) + opt-in size scaling
except Exception: confmod = None
PIP = 0.10
ZHALO_P = 40   # zone-proximity halo in PIPS (gold 40p = $4). near_htf/count_distinct_at use ZHALO_P*PIP so the halo is pip-normalised per instrument (was hardcoded 4 = 40 gold-pips).
PXD = 2              # price-rounding decimals (per-symbol, derived from PIP in init_symbol): gold 2, EURUSD 5, USDJPY 3, indices 1
MIN_TP = 50      # pips
TIGHT_RANGE_P = 35     # 15-bar range below this (×VS) = a "tight" consolidation (range-breakout trigger)
DT_EQ_P = 8            # two swing highs/lows within this (×VS) = equal = a double top/bottom
VOL_MIN_RANGE10 = 40   # last 10 bars must span >= this many pips (×VS) to allow a fast signal
ATR_REF = 30           # the VS=1 anchor (gold's 1m ATR, pips) for ATR-normalized sizing. All pip-tuned
                       # constants below are scaled by VS = atr_base/ATR_REF at runtime so the strategies
                       # self-fit any instrument, regime AND timeframe. On the 5m execution TF the bar ranges
                       # are ~1.8–2.2× wider, so VS auto-runs ~2 and the whole geometry (chase/room/SL/TP/
                       # vol-gate/tight/double-top) scales up to match 5m — no per-TF re-tuning needed.

# Higher-TF swing S/R map (matches the 1H/4H/Daily zones drawn on the chart). (lo, hi, label)
HTF_R = [(4459,4468,"R 4459-68 (15m+1H swing highs)"), (4470,4475,"R 4472 (15m EMA200 + 1H EMA50)"),
         (4483,4489,"R 4485-88 (1H EMA100 + 15m/1H highs)"), (4493,4501,"KEY R 4496-4500 (PDH + 4H/1H EMA200)"),
         (4511,4515,"R 4513 (1H high)"), (4538,4545,"R 4541 (1H/4H highs)")]
HTF_S = [(4446,4449,"S 4447 (15m EMA50 + 1H/4H lows)"), (4433,4439,"S 4433-39 (1H/15m swing lows)"),
         (4423,4427,"S 4424-26 (PDL + today-low multi-touch)"), (4398,4406,"S 4400 (4H swing low)"),
         (4375,4385,"BUY ZONE Daily EMA200 (~4380)"), (4360,4368,"S 4366 (4H/Daily low)")]
CLASSIC = {"zones": [], "sr": []}   # classic supply/demand boxes + S/R levels (zones_sd), loaded by load_zones() — the same zones draw_review draws (drawn==traded)
FIB_ZONES = []                      # hourly multi-TF golden zones (4H/1H/15m/5m), loaded from zones_<symbol>.json
def near_htf(price, levels, tol=None):
    if tol is None: tol = ZHALO_P * PIP   # pip-normalised zone halo (gold $4, EURUSD 0.004, …)
    for lo, hi, lab in levels:
        if lo - tol <= price <= hi + tol: return (lo, hi, lab)
    return None

# --- v2 gold-specific reference levels (refresh ~daily) ---
PDH, PDL = 4496.7, 4426.4          # prior-day high / low
ASIA_H, ASIA_L = 4484.0, 4443.3    # Asian-session range (06-04, complete 00-07 UTC)
SESSION_UTC = set(range(7, 22))    # London+NY active hours (UTC); outside = quiet
NEWS_BLACKOUT = []                 # [(h1,m1,h2,m2),...] UTC windows to mute (manual)
CD_FILE = os.path.expanduser("~/.tv_fast_cd.json")
COOLDOWN_MIN = 5                   # no new signal for N minutes after one fires (anti-clustering)
WATCH_CD_FILE = os.path.expanduser("~/.tv_fast_watch.json")
WATCH_CD_MIN = 12                  # heads-up cooldown: don't re-ping the same zone area for N min
WATCH_NEW_ZONE_P = 15              # ...unless price moved >this many pips to a genuinely new zone
CHASE_LOOKBACK = 6                 # bars used as the "base" for the anti-chase extension check
MAX_CHASE_P = 60                   # skip a continuation entry if price already ran >this many pips off the base
DYN_TOL = 15                       # "at level" halo for dynamic POINT levels (VWAP/EMA/round/PDH/Asian) in PIPS — ×PIP×VS, so ±15 pips on every pair (gold $1.5, EURUSD 0.0015)
OVERLAY_OB_BAND_P = 150            # live overlay: only draw SMC order blocks within this many pips of price
OVERLAY_MIN_INTERVAL = 300         # live overlay: redraw at most every N seconds (avoid per-tick chart flicker)
CONF_SIZE_LO, CONF_SIZE_HI = 0.75, 1.5   # confidence-sizing: risk multiplier at confidence 0 / 10 (only if confidence_sizing on)
TP_BUFFER_P = 8                    # adaptive TP stops this many pips short of the next structure (don't aim into the wall)
MIN_ROOM_P = 25                    # skip a trade if usable room to the next structure is below this (bad R:R)
BE_TRIGGER_P = 35                  # once a trade runs +this many pips favorable (pre-TP1), move stop to breakeven — protect the scratch (06-04: a short ran +38p, never hit TP1, gave it all back to -30p; BE turns that into 0). Set above typical entry-noise pullbacks so it doesn't scratch winners early.
RSI_OB, RSI_OS = 78, 22            # RSI exhaustion gates — block continuation longs >OB / shorts <OS (anti blow-off)
VP_TF, VP_BARS = "30", 48          # volume-profile basis: 30m bars x48 (~1 day) for VPOC / value-area levels
RECLAIM_MIN_P = 12                 # zone-reclaim: min net 3-bar move (pips) to confirm a grind-bounce off a zone
BASE_TF = int(os.environ.get("TV_BASE_TF", "5"))   # execution timeframe in minutes (5m default everywhere; backtests set TV_BASE_TF explicitly)
ER_STRIDE = max(1, 15 // BASE_TF)  # bars per 15m step (15 on 1m, 3 on 5m) so the ER stays a 15m-sampled read
SMC_TTL = 3600        # SMC/trendline HTF context refreshes slowly (4h); cached this long (live). Backtest clears the cache per replay step-refresh, so it stays date-faithful.
SMC_TOL = 80          # SMC proximity in PIPS (gold $8) — ×PIP makes it pair-correct (EURUSD 0.008)
CHOP_ER = 0.30                     # 15m efficiency-ratio below this = range/chop -> suppress breakout/momentum entries
RR_FLOOR     = 1.2                 # pre-hold HARD FLOOR (primary): TP1 must be >= this × the stop, else the trade
                                   # is structurally un-tradeable (sub-1.2 R:R is -EV at scalp win rates) and is
                                   # auto-skipped. Raised 0.8→1.2 (2026-06-08): the gold June 2-5 -135p loss was
                                   # driven entirely by 3 zone-bounce trades at R:R 0.83-1.06 that all hit SL.
                                   # BEFORE it can reach the held/review state — regardless of direction. This is
                                   # the dominant chop-spam signature ("neg R:R, TP1 +6p vs SL -18p"). A genuine
                                   # setup (positive R:R with room) never trips it. Applies EVEN under ai_decide.
HARD_CHOP_ER = 0.20                # PRIMARY floor: ER below this = truly dead tape (no trend lives here, a rejection
                                   # won't follow through). Auto-skipped regardless of room — the dominant gold-chop
                                   # spam signature. Real trending setups run ER 0.4-1.0, so this only kills dead tape.
HARD_ROOM_P  = 10                  # secondary floor: a THIN-room setup (<HARD_ROOM_P×VS) that is ALSO a
                                   # counter-trend fade (whipsaw-in-a-box) is skipped too.
ZONE_WICK_P = 15                   # zone-bounce: min rejection-wick (pips) for a candle to count as a zone defense
FIB_MIN_WAVE_P = 80                # fib pullback: minimum impulse leg before a correction is tradeable
FIB_TOUCH_P = 8                    # fib pullback: touch halo around the retracement pocket, in pips × VS
FIB_REJECT_P = 6                   # fib pullback: minimum rejection wick from the fib pocket, in pips × VS
FIB_PULLBACK_ZONE = (0.52, 0.645)  # user's chart template: primary correction pocket between 0.52 and 0.645
ZONES_FILE = os.path.expanduser("~/tradingview-mcp/zones.json")
ZONES_TTL = 6*3600                 # auto-rebuild HTF zones (refresh_zones.py) when older than this
ZONES_MAX_AGE = 18*3600            # ...but still use a stale file up to this old rather than fall back
SMC_SNAP_MAX_AGE = 6*3600          # stored multi-TF SMC snapshot: ignore for confluence if older than this (hourly cron tolerates a few missed cycles; a stale snapshot must contribute nothing, not mislead the grade)

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
            em[L] = round(order[rank], PXD)
    elif emas:                                            # fallback (extra/missing EMAs): absolute nearest
        for L in (50, 100, 200):
            ref = ema(L); em[L] = round(min(emas, key=lambda x: abs(x - ref)), PXD)
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
    at = lambda i: round(lo + (i+0.5)*w, PXD)   # PXD = per-symbol decimals (gold 2, EURUSD 5) — round(…,1) collapsed FX prices to 1.2
    return (at(poc), at(z), at(a))   # vpoc, vah (value-area high), val (value-area low)

def _tpo_levels():
    """Read the Kioseff TPO profile rows from its labels (each carries the TPO letters at that price).
    POC = price with the most letters; value area = the 70% band around it. (None,None,None) if empty."""
    rows = []
    for s in tv("data", "labels", "--filter", "TPO").get("studies", []):   # --filter (NOT --study-filter, which was ignored → mixed in other studies' labels)
        for lb in s.get("labels", []):
            p = lb.get("price"); cnt = len(str(lb.get("text", "")).replace(" ", ""))
            if p and cnt: rows.append((round(p, PXD), cnt))
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
    """One cached visit to VP_TF (30m) returns BOTH the TPO POC/value-area AND the HTF trend regime.
    The 1m chart is execution-only — trend bias is read from the 30m EMA stack up here (immune to 1m
    pullbacks). The Kioseff TPO only renders on a high TF, so we SHOW it, read it, HIDE it. try/finally
    guarantees the chart returns to 1m. Returns (vpoc, vah, val, regime). Cached VP_TTL."""
    try:
        c = json.load(open(VP_FILE))
        if time.time() - c.get("t", 0) < VP_TTL:
            return c.get("vpoc"), c.get("vah"), c.get("val"), c.get("regime", "flat")
    except Exception: pass
    tid = next((s["id"] for s in tv("state").get("studies", [])
                if "TPO" in s.get("name", "") or "Profile" in s.get("name", "")), None) if USE_TPO else None
    poc = vah = val = None; regime = "flat"
    try:
        tv("timeframe", VP_TF)
        if tid: tv("indicator", "toggle", tid, "--visible", "true"); time.sleep(4)   # show TPO to render on 30m
        if tid: poc, vah, val = _tpo_levels()
        bars = tv("ohlcv", "-n", str(VP_BARS)).get("bars", [])
        if poc is None: poc, vah, val = _calc_vp(bars)                    # fallback: computed profile
        if bars:                                                          # HTF regime from 30m EMA stack
            _, _, _, em_h, _ = read_chart_levels([x["close"] for x in bars])
            h5, h1, h2 = em_h.get(50), em_h.get(100), em_h.get(200)
            if h5 and h1 and h2:
                regime = "UP" if h5 > h1 > h2 else ("DOWN" if h5 < h1 < h2 else "flat")
    finally:
        if tid: tv("indicator", "toggle", tid, "--hidden")   # ALWAYS hide (even on error) — TPO stays off the chart
        tv("timeframe", str(BASE_TF))   # restore the execution TF (1m live, 5m backtest) — not hardcoded 1m
    try: json.dump({"t": time.time(), "vpoc": poc, "vah": vah, "val": val, "regime": regime}, open(VP_FILE, "w"))
    except Exception: pass
    return poc, vah, val, regime


def prior_day_vas(symbol, ref_ts, n=3):
    """Prior-day VAH/POC/VAL from the va_store DB (the reliable, immutable cache) — NOT the live indicator
    scrape (which returns orphaned-primitive residue). Walks back from the reference date and collects the
    last `n` CLOSED days that are cached, skipping gaps (weekends/holidays). Pure DB read, no chart I/O, so
    it's also date-faithful in the backtest (the cursor's date drives `ref_ts`). See docs/value-area-framework.md."""
    if not vastore:
        return []
    ref = _dt.datetime.utcfromtimestamp(ref_ts).date()
    out = []
    d = ref
    for _ in range(14):                 # look back up to 2 weeks to find n cached closed days
        if len(out) >= n:
            break
        d = d - _dt.timedelta(days=1)
        r = vastore.get(symbol, d.isoformat())
        if r:
            out.append(r)
    return out

def zones_fallback(symbol, htf_r, htf_s, pdh, pdl, asia_h, asia_l):
    """Fallback when no generated zone file is usable. The hardcoded HTF_R/HTF_S/PDH/... constants are
    GOLD levels — a valid fallback ONLY for XAUUSD. For any other symbol, returning them would grade e.g.
    EURUSD against gold prices, so fail SAFE with empty dynamic zones (no levels → no setups) instead of
    silently trading the wrong map. Pure (testable). [generated zone files are gitignored — codex]"""
    if symbol == "XAUUSD":
        return list(htf_r), list(htf_s), pdh, pdl, asia_h, asia_l
    return [], [], None, None, None, None

def load_zones():
    """Return (HTF_R, HTF_S, PDH, PDL) from auto-derived zones.json. Rebuilds it (refresh_zones.py)
    when stale (>ZONES_TTL); falls back via zones_fallback() if no usable file exists (gold-only constants,
    so non-XAU gets EMPTY zones, never gold levels). Each scan is a fresh process, so this re-applies every run."""
    z = None
    try:
        z = json.load(open(ZONES_FILE)); age = time.time() - z.get("ts", 0)
    except Exception:
        age = 1e12
    if age > ZONES_TTL:   # stale -> rebuild inline (only happens ~every 6h; switches TFs then restores 1m)
        try:
            subprocess.run(["python3", "refresh_zones.py", "--symbol", SYMBOL], cwd=TVDIR, capture_output=True, timeout=150)
            z = json.load(open(ZONES_FILE)); age = time.time() - z.get("ts", 0)
        except Exception: pass
    global CLASSIC, FIB_ZONES
    CLASSIC = {"zones": (z or {}).get("sd_zones", []) or [], "sr": (z or {}).get("sd_sr", []) or []}   # classic supply/demand + S/R (drawn==traded)
    FIB_ZONES = (z or {}).get("fib_zones", []) or []   # hourly golden-zone analysis (drawn + used as context)
    if z and z.get("htf_r") and age < ZONES_MAX_AGE:
        return ([tuple(x) for x in z["htf_r"]], [tuple(x) for x in z["htf_s"]],
                z.get("pdh") or PDH, z.get("pdl") or PDL, z.get("asia_h") or ASIA_H, z.get("asia_l") or ASIA_L)
    if SYMBOL != "XAUUSD":
        print(f">> WARN: no usable zones file for {SYMBOL} and refresh failed — running with EMPTY zones "
              f"(hardcoded fallback is GOLD-only; refusing to grade {SYMBOL} against gold levels).")
    return zones_fallback(SYMBOL, HTF_R, HTF_S, PDH, PDL, ASIA_H, ASIA_L)


def merge_classic_zones(htf_r, htf_s, classic):
    """Merge ALL classic sd_zones/sd_sr into the resistance/support level lists for confluence + targets, so
    what's DRAWN (draw_review) is exactly what's TRADED — overlapping zones are NOT dropped (dropping would
    hide a drawn zone from the engine). Double-counting is prevented at COUNT time (see count_distinct_at),
    not by discarding zones. buy zone/support → support side; sell zone/resistance → resistance side.
    Returns (R, S). Pure (testable)."""
    R = list(htf_r); S = list(htf_s)
    for zz in (classic or {}).get("zones", []):
        tup = (zz["lo"], zz["hi"], f"{zz['tf']} {zz['role']}{' KL' if zz['kl'] else ''}")
        (S if zz["role"] in ("buy zone", "support") else R).append(tup)
    for s in (classic or {}).get("sr", []):
        lo, hi = s.get("lo", s["price"]), s.get("hi", s["price"])   # S/R is the origin-candle band (a zone), not a bare price
        tup = (lo, hi, f"{s['tf']} {s['role']} (classic)")
        (S if s["role"] == "support" else R).append(tup)
    return R, S


def merge_smc_ob_zones(htf_r, htf_s, smc_block):
    """Merge stable stored SMC price objects into the resistance/support maps used by setup detection.
    Clear supply OBs, swing highs and EQH liquidity behave like resistance; clear demand OBs, swing lows
    and EQL liquidity behave like support. Straddle boxes are intentionally ignored because they sit
    around current/equilibrium price and are not directional. BOS/CHoCH structure labels are scoring-only:
    they are too dense/noisy in historical mode to become trigger zones safely. Returns (R, S). Pure."""
    R = list(htf_r); S = list(htf_s)
    tf_names = {"240": "4H", "60": "1H", "15": "15m"}
    for tfk, data in ((smc_block or {}).get("tf", {}) or {}).items():
        tf_lab = tf_names.get(str(tfk), f"{tfk}m")
        for b in data.get("boxes", []) or []:
            side = b.get("side")
            if side not in ("supply", "demand"):
                continue
            lo, hi = _num(b.get("low")), _num(b.get("high"))
            if lo is None or hi is None:
                continue
            if hi < lo:
                lo, hi = hi, lo
            tup = (lo, hi, f"{tf_lab} SMC {side} OB")
            (R if side == "supply" else S).append(tup)
        for sw in data.get("swings", []) or []:
            price = _num(sw.get("price"))
            text = str(sw.get("text", "swing")).strip() or "swing"
            low_text = text.lower()
            if price is None:
                continue
            if "high" in low_text:
                R.append((price, price, f"{tf_lab} SMC {text}"))
            elif "low" in low_text:
                S.append((price, price, f"{tf_lab} SMC {text}"))
        for liq in data.get("liquidity", []) or []:
            price = _num(liq.get("price"))
            text = str(liq.get("text", "")).upper()
            if price is None:
                continue
            if "EQH" in text:
                R.append((price, price, f"{tf_lab} SMC EQH liquidity"))
            elif "EQL" in text:
                S.append((price, price, f"{tf_lab} SMC EQL liquidity"))
    return R, S


def count_distinct_at(levels, price, edge=None):
    """Count DISTINCT price clusters in `levels` [(lo,hi,lab)…] that bracket `price` (within `edge`), merging
    overlapping/adjacent brackets so the SAME wall covered by several sources (e.g. an old HTF cluster + a
    coinciding classic zone) counts ONCE, not N times. This is where drawn-zone overlaps are de-duplicated
    for the confluence count, instead of dropping zones from the level map. `edge` defaults to the
    pip-normalised zone halo (ZHALO_P*PIP). Pure (testable)."""
    if edge is None: edge = ZHALO_P * PIP
    hit = sorted((lo, hi) for lo, hi, _ in levels if lo - edge <= price <= hi + edge)
    n = 0; cur_hi = None
    for lo, hi in hit:
        if cur_hi is None or lo > cur_hi + edge:
            n += 1; cur_hi = hi
        else:
            cur_hi = max(cur_hi, hi)
    return n


def cluster_walls(prices, tol):
    """Collapse a flat list of wall prices into DISTINCT obstacle clusters (merging points within `tol`),
    returning sorted (lo, hi) bounds per cluster. Used for nextR/nextS so a level map saturated with many
    near-duplicate SMC OB edges (one box contributes 2 points; 3 TFs pile up) doesn't read as a wall every
    few pips. The CALLER picks the near edge (cluster lo for resistance above, cluster hi for support below)
    so a zone price is currently INSIDE isn't counted as the next obstacle. Pure (testable)."""
    pts = sorted({p for p in prices if p is not None})
    if not pts:
        return []
    clusters = []; lo = hi = pts[0]
    for p in pts[1:]:
        if p - hi <= tol:
            hi = p
        else:
            clusters.append((lo, hi)); lo = hi = p
    clusters.append((lo, hi))
    return clusters


def next_wall(prices, price, side, tol, gap):
    """Nearest DISTINCT wall beyond `price` after clustering (next_wall replaces the raw min/max over every
    edge). side='R' → nearest cluster whose NEAR edge (lo) is > price+gap (resistance above); 'S' → nearest
    cluster whose near edge (hi) is < price-gap (support below). Returns the edge price or None. Pure."""
    cl = cluster_walls(prices, tol)
    if side == "R":
        cand = [lo for lo, _ in cl if lo > price + gap]
        return min(cand) if cand else None
    cand = [hi for _, hi in cl if hi < price - gap]
    return max(cand) if cand else None


def kl_upgrade(grade):
    """A Key-Level classic zone is the TOP-probability tier → upgrade a real setup (A or B) straight to A+
    (a bare B + KL must reach A+, not just A — the generic cf_score path only does B→A). Pure (testable)."""
    return "A+" if grade.startswith(("A", "B")) else grade


def classic_key_level_at(classic, side, price, tol):
    """Return the active classic Key-Level zone for `side` at `price`, if any.
    KL buy/support zones are LONG trade locations; KL sell/resistance zones are SHORT trade locations."""
    want = ("buy zone", "support") if side == "LONG" else ("sell zone", "resistance")
    for z in (classic or {}).get("zones", []) or []:
        if not z.get("kl") or z.get("role") not in want:
            continue
        lo, hi = _num(z.get("lo")), _num(z.get("hi"))
        if lo is None or hi is None:
            continue
        if hi < lo:
            lo, hi = hi, lo
        if lo - tol <= price <= hi + tol:
            return z
    return None


def key_level_rejection(last, zone, side, wick_p, pip):
    """True when the latest candle rejects a KL zone in the trade direction."""
    if not zone:
        return False
    lo, hi = _num(zone.get("lo")), _num(zone.get("hi"))
    if lo is None or hi is None:
        return False
    if hi < lo:
        lo, hi = hi, lo
    wick = wick_p * pip
    if side == "LONG":
        return (last["low"] <= hi and last["close"] >= lo
                and last["close"] > last["open"]
                and (last["close"] - last["low"]) >= wick)
    return (last["high"] >= lo and last["close"] <= hi
            and last["close"] < last["open"]
            and (last["high"] - last["close"]) >= wick)


def fib_pullback_signal(bars, side, pip, vs=1.0, pxd=2, lookback=80,
                        zone=FIB_PULLBACK_ZONE, min_wave_p=FIB_MIN_WAVE_P,
                        touch_p=FIB_TOUCH_P, reject_p=FIB_REJECT_P,
                        require_rejection=True):
    """Detect a correction pullback into the primary fib pocket of the latest impulse leg.
    SHORT: draw fib from wave top to wave bottom, then reject a pullback into 0.52-0.645.
    LONG: draw fib from wave bottom to wave top, then reject a pullback into 0.52-0.645.
    Returns context dict or None. Pure (testable)."""
    if len(bars) < 8 or side not in ("LONG", "SHORT"):
        return None
    win = bars[-lookback:] if len(bars) > lookback else bars[:]
    if len(win) < 8:
        return None
    last = win[-1]; hist = win[:-1]
    if side == "SHORT":
        low_i, low_bar = min(enumerate(hist), key=lambda kv: kv[1]["low"])
        prior = hist[:low_i]
        if not prior:
            return None
        high_i, high_bar = max(enumerate(prior), key=lambda kv: kv[1]["high"])
        wave_hi, wave_lo = high_bar["high"], low_bar["low"]
        if low_i <= high_i:
            return None
        wave_p = (wave_hi - wave_lo) / pip
        if wave_p < min_wave_p * vs:
            return None
        z1, z2 = (wave_lo + r * (wave_hi - wave_lo) for r in zone)
        zlo, zhi = min(z1, z2), max(z1, z2)
        pad, wick = touch_p * vs * pip, reject_p * vs * pip
        touched = last["high"] >= zlo - pad and last["low"] <= zhi + pad
        rejected = last["close"] < last["open"] and (last["high"] - last["close"]) >= wick
        if touched and (rejected or not require_rejection):
            return {"side": side, "wave_hi": round(wave_hi, pxd), "wave_lo": round(wave_lo, pxd),
                    "zone_lo": round(zlo, pxd), "zone_hi": round(zhi, pxd),
                    "ratio": f"{zone[0]:.3g}-{zone[1]:.3g}", "wave_pips": round(wave_p),
                    "touched": touched, "rejected": rejected}
        if not require_rejection:
            return {"side": side, "wave_hi": round(wave_hi, pxd), "wave_lo": round(wave_lo, pxd),
                    "zone_lo": round(zlo, pxd), "zone_hi": round(zhi, pxd),
                    "ratio": f"{zone[0]:.3g}-{zone[1]:.3g}", "wave_pips": round(wave_p),
                    "touched": touched, "rejected": rejected}
    else:
        high_i, high_bar = max(enumerate(hist), key=lambda kv: kv[1]["high"])
        prior = hist[:high_i]
        if not prior:
            return None
        low_i, low_bar = min(enumerate(prior), key=lambda kv: kv[1]["low"])
        wave_hi, wave_lo = high_bar["high"], low_bar["low"]
        if high_i <= low_i:
            return None
        wave_p = (wave_hi - wave_lo) / pip
        if wave_p < min_wave_p * vs:
            return None
        z1, z2 = (wave_hi - r * (wave_hi - wave_lo) for r in zone)
        zlo, zhi = min(z1, z2), max(z1, z2)
        pad, wick = touch_p * vs * pip, reject_p * vs * pip
        touched = last["low"] <= zhi + pad and last["high"] >= zlo - pad
        rejected = last["close"] > last["open"] and (last["close"] - last["low"]) >= wick
        if touched and (rejected or not require_rejection):
            return {"side": side, "wave_hi": round(wave_hi, pxd), "wave_lo": round(wave_lo, pxd),
                    "zone_lo": round(zlo, pxd), "zone_hi": round(zhi, pxd),
                    "ratio": f"{zone[0]:.3g}-{zone[1]:.3g}", "wave_pips": round(wave_p),
                    "touched": touched, "rejected": rejected}
        if not require_rejection:
            return {"side": side, "wave_hi": round(wave_hi, pxd), "wave_lo": round(wave_lo, pxd),
                    "zone_lo": round(zlo, pxd), "zone_hi": round(zhi, pxd),
                    "ratio": f"{zone[0]:.3g}-{zone[1]:.3g}", "wave_pips": round(wave_p),
                    "touched": touched, "rejected": rejected}
    return None


def fib_grade_boost(grade):
    """A valid fib correction pocket is +1 confluence tier, not a free pass for bad/counter-zone setups."""
    if grade.startswith("A") and not grade.startswith("A+"):
        return "A+"
    if grade.startswith("B"):
        return "A"
    return grade


_GRADE_TIERS = ["C", "B", "A", "A+"]   # ascending letter tiers
def downgrade_grade(grade, steps):
    """Lower the LETTER tier by `steps` (A+→A→B→C), floored at C. Used for the SOFT counter-trend penalty —
    counter-trend dents the grade, it is NOT a hard veto. Pure (testable). Drops any suffix (it described the
    original setup); downstream only checks the leading tier via startswith()."""
    idx = 3 if grade.startswith("A+") else 2 if grade.startswith("A") else 1 if grade.startswith("B") else 0
    return _GRADE_TIERS[max(0, idx - max(0, steps))]

def hard_floor_skip(side, regime, rsi, rr1, room, chop_er, VS):
    """Pre-hold HARD FLOOR predicate (applies EVEN under ai_decide — the only skip that does).
    Returns (skip: bool, reasons: list[str]).
      PRIMARY  — negative reward:risk: TP1 < RR_FLOOR × stop = no usable room, un-tradeable in any direction
                 (the dominant 'neg R:R, TP1 +6p vs SL -18p' chop-spam that gets hand-rejected every tick).
      PRIMARY  — dead chop: ER < HARD_CHOP_ER = no trend, a rejection/bounce won't follow through (the gold-4465
                 chop spam — same level, every tick, ER ~0.0-0.20). Skipped regardless of room/direction.
      SECONDARY — a THIN-room setup that is ALSO a counter-trend fade.
    Conservative: a genuine setup (positive R:R, real ER, room) trips none and still reaches review. Pure fn.
    NOTE: RSI is intentionally NOT used here — per directive it is informational only, never a gate."""
    reasons = []
    if rr1 is not None and rr1 < RR_FLOOR:
        reasons.append(f"neg R:R {rr1:.2f} (TP1 < {RR_FLOOR}×SL)")
    if chop_er is not None and chop_er < HARD_CHOP_ER:
        reasons.append(f"dead chop ER{chop_er} (<{HARD_CHOP_ER})")
    counter = (side == "LONG" and regime == "DOWN") or (side == "SHORT" and regime == "UP")
    if room is not None and room < HARD_ROOM_P * VS and counter:
        reasons.append(f"counter-{regime} no-room")
    return (bool(reasons), reasons)

ZONE_REJECTION_FAMILIES = ("zone-bounce", "zone-reclaim", "key-level")   # rejections AT a classic/SMC/KL supply-demand zone
def is_zone_rejection(why):
    return any(k in (why or "") for k in ZONE_REJECTION_FAMILIES)

def zrskip_record(why, flags, side, regime, er, rr1, entry, sl, tp1):
    """MEASUREMENT ONLY (does NOT change behavior): when a zone-rejection setup is auto-skipped by the
    pre-hold HARD FLOOR, return a bucket record so we can measure whether WITH-trend zone-rejections that
    the floor kills actually had edge. Two block mechanisms observed: dead CHOP (gold case) and neg R:R
    geometry (GBP case — TP1 capped at the nearest micro-structure on tight-range FX). `block` tags which.
    `with_trend` = side aligned with 30m regime. Returns None for non-zone-rejection families. Pure."""
    if not is_zone_rejection(why): return None
    chop   = any("dead chop" in (f or "") for f in (flags or []))
    neg_rr = any("neg R:R"   in (f or "") for f in (flags or []))
    block  = "both" if (chop and neg_rr) else "chop" if chop else "rr" if neg_rr else "other"
    with_trend = (side == "LONG" and regime == "UP") or (side == "SHORT" and regime == "DOWN")
    return {"family": why, "side": side, "regime": regime, "with_trend": with_trend, "block": block,
            "chop": chop, "neg_rr": neg_rr, "er": er, "rr1": rr1, "entry": entry, "sl": sl, "tp1": tp1}

def gate_trace(name):
    """Per-scan TERMINAL-gate trace for dry-replay funnel analysis (codex): every scan ends at exactly one
    gate (no_trigger / counter_trend / cramped / hard_floor_* / off_session / fast_signal / …). Emits a
    machine-parseable '>> GATE <name>' line ONLY when SKIP_TRACE env is set (replay_sim sets it) — silent
    live, so no behavior/log change. Returns name (testable). Makes 'why did trades vanish' measurable
    instead of the blind '0 surfaced'."""
    if os.environ.get("SKIP_TRACE"):
        print(f">> GATE {name}")
    return name

REVERSAL_KINDS = ("sweep", "retest", "VWAP", "reclaim", "bounce", "CRT", "key-level")   # fade / mean-reversion setups
def reversal_rsi_extreme(side, why, rsi, lo=25, hi=75):
    """#3 gate (pure): True if a REVERSAL setup is being taken at a WRONG-WAY RSI extreme — a SHORT into
    deep oversold (selling the bottom, rsi<=lo) or a LONG into overbought (buying the top, rsi>=hi).
    Reset-RSI bounces (e.g. a long at rsi 40) are NOT flagged; continuation setups aren't gated here."""
    if rsi is None: return False
    if not any(k in why for k in REVERSAL_KINDS): return False
    return (side == "LONG" and rsi >= hi) or (side == "SHORT" and rsi <= lo)

def valid_prior_va_near(level, prior_vas, bars, dyn_tolp, bar_minutes, state_mod=None):
    """True when `level` sits on a prior VA level that is still tradable.
    Accepted-through and weak/inconclusive states are intentionally not valid reversal context."""
    state_mod = state_mod or vastate
    if state_mod is None or not prior_vas or level is None:
        return False
    for p in prior_vas:
        for role, lvl in (("VAH", p.get("vah")), ("POC", p.get("poc")), ("VAL", p.get("val"))):
            if lvl is None or abs(lvl - level) > dyn_tolp:
                continue
            st = state_mod.level_state(lvl, bars, role, poc=p.get("poc"), bar_minutes=bar_minutes)
            if st["state"] in ("Rejected", "Flipped") and st["evidence"].get("confidence") != "weak":
                return True
    return False

def reversal_context_ok(side, probe_level, conf_s, conf_r, prior_vas, bars, dyn_tolp, bar_minutes, state_mod=None):
    """Quality floor for noisy reversal families: require either stacked local confluence
    or a valid prior-value-area level. This keeps generic wicks/sweeps out of live review."""
    conf = conf_s if side == "LONG" else conf_r
    return conf >= 2 or valid_prior_va_near(probe_level, prior_vas, bars, dyn_tolp, bar_minutes, state_mod=state_mod)

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
                 "anti_chase": True, "adaptive_tp": True, "rsi_filter": True, "trend_regime": True,  # rsi_filter ON by default (forex/indices); per-symbol override turns it OFF for gold (XAUUSD) — RSI informational only there
                 "confluence": True, "volume_profile": True, "zone_reclaim": False, "smc_confluence": False,
                 "smc_mtf": True,   # consider the STORED multi-TF SMC snapshot (zones file, hourly cron): HTF-weighted OB/swing confluence + soft premium/discount alignment. Stable read (not the flaky per-tick live read smc_confluence).
                 "smc_ob_zones": True,   # treat stable stored SMC price objects (clear OBs, swings, EQH/EQL) as real R/S zones for at_R/at_S, zone-bounce detection, confluence and target geometry. Straddle boxes remain scoring-only/no-trigger.
                 "classic_zones": True,   # consider the CLASSIC supply/demand + S/R zones (zones_sd, the ones draw_review draws) in confluence + grade; a KEY-LEVEL (KL) classic zone is the top-probability tier and boosts the grade.
                 "key_level_trades": True,   # KL classic zones are trade locations: a directional rejection at KL can create its own setup, not just add confluence.
                 "range_filter": True, "session_sweep": True, "zone_bounce": True, "session_filter": True,
                 "news_filter": True, "volume_filter": True, "crt": True, "ai_decide": False,
                 "fib_pullback": True,
                 "hard_floor": True, "rsi_reset_gate": False,   # rsi_reset_gate OFF until data validates thresholds
                 "wall_dedup": False,   # cluster near-duplicate wall edges before nextR/nextS (codex Option 2) — OFF live until the June 4-5 backtest confirms it cuts the cramped over-trigger without flooding

                 "family_caps": True, "observation_gate": True}   # daily per-family caps + observe-only families (review)
def load_flags():
    f = dict(DEFAULT_FLAGS)
    # FLAGS_FILE env override: the BACKTEST (replay_sim) points this at flags_backtest.json (ai_decide=false)
    # so the engine's own discipline is exercised in replay — WITHOUT editing the live flags.json the cron reads.
    path = os.environ.get("FLAGS_FILE", FLAGS_FILE)
    try: f.update(json.load(open(path)))
    except Exception: pass
    f.update(SYMBOL_FLAGS or {})   # per-symbol overrides from instruments.json (e.g. disable mean-reversion on indices)
    return f
PAT_FLAG = {"trendline": "trendline_break", "range/triangle": "range_breakout", "double": "double_top_bottom",
            "impulse": "momentum_impulse", "sweep": "liquidity_sweep", "retest": "break_retest",
            "VWAP": "vwap", "breakout": "session_breakout", "breakdown": "session_breakout",
            "reclaim": "zone_reclaim", "bounce": "zone_bounce", "CRT": "crt", "fib": "fib_pullback",
            "key-level": "key_level_trades"}
# Daily per-family caps on FIRED (alerted) trades — stop noisy families from overproducing (review Priority 2).
# Keyed by strategy flag; families not listed are uncapped. Only REDUCES trades (safe). Flag: family_caps.
FAMILY_CAPS = {"trendline_break": 3, "crt": 2, "zone_bounce": 1, "momentum_impulse": 1,
               "liquidity_sweep": 1, "session_sweep": 2, "break_retest": 1, "fib_pullback": 2,
               "key_level_trades": 2}
# Observation-only families: detected + LOGGED (for measurement) but NOT surfaced/fired live, until they
# prove cost-adjusted edge out of sample (review Next #3: momentum impulse is negative net). Flag: observation_gate.
OBSERVE_FAMILIES = {"momentum_impulse"}
def flag_for(why):
    for k, v in PAT_FLAG.items():
        if k in why: return v
    return None

def family_fired_today(symbol):
    """Count today's FIRED (alerted) trades per strategy-flag, from the outcome DB — for the daily family caps.
    Counts only rows that became real trades (PENDING/executed), not rejects/auto-skips. {} on any error."""
    try:
        import outcome_db
        today = _dt.datetime.now().astimezone().strftime("%Y-%m-%d")
        rows = outcome_db.rows(symbol=symbol, since=today)
    except Exception:
        return {}
    fired = ("PENDING", "TP1", "TP2", "SL", "BE", "timeout", "superseded")
    cnt = {}
    for r in rows:
        if r.get("result") in fired:
            fam = flag_for(r.get("pattern", "") or "")
            if fam:
                cnt[fam] = cnt.get(fam, 0) + 1
    return cnt

def alert_sound(n=3):
    """Audible alert on a fast signal (macOS afplay)."""
    for _ in range(n):
        try: subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], timeout=5)
        except Exception: pass

TG_CONF = os.path.expanduser("~/tradingview-mcp/telegram_config.json")
TG_STATE = os.path.expanduser("~/.tv_fast_tg.json")
TRADE_STATE = os.path.expanduser("~/.tv_fast_trade.json")
PENDING_FILE = os.path.expanduser("~/.tv_fast_pending.json")   # a confirmed trade held for AI review (--review)

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
SIG_COLS = ["id", "time", "side", "grade", "confidence", "pattern", "entry", "sl", "tp1", "rng10", "body_p", "htf", "result", "exit", "pips"]

SYMBOL = "XAUUSD"; TV_SYMBOL = "XAUUSD"; SESSIONS_OK = None; SYMBOL_FLAGS = {}
RISK_USD = 20.0      # fixed $ risk per trade → lot = RISK_USD / (PIP_VALUE × stop_pips)
PIP_VALUE = 10.0     # $ P/L per 1 pip per 1.0 lot (gold & USD-quoted forex ≈ 10; JPY/indices differ — set per symbol)
USE_TPO = False      # read the Kioseff TPO indicator for VPOC/value-area (gold only); others use the computed profile
LOT_MIN, LOT_MAX, LOT_STEP = 0.01, 100.0, 0.01   # broker volume constraints (per-instrument; sized lot is rounded to step + clamped)
INSTRUMENTS_FILE = os.path.expanduser("~/tradingview-mcp/instruments.json")
def init_symbol(sym):
    """Repoint every per-symbol global (PIP, ATR_REF, state files, zones, TV window) from instruments.json so the
    SAME code scans any instrument. Pins tv() to the symbol's window via TV_CHART. Default XAUUSD = unchanged."""
    global SYMBOL, TV_SYMBOL, SESSIONS_OK, SYMBOL_FLAGS, PIP, PXD, ATR_REF, RISK_USD, PIP_VALUE, USE_TPO
    global LOT_MIN, LOT_MAX, LOT_STEP
    global CD_FILE, WATCH_CD_FILE, VP_FILE, TG_STATE, TRADE_STATE, PENDING_FILE, ZONES_FILE
    SYMBOL = (sym or "XAUUSD").upper()
    cfg = {}
    try:
        allc = json.load(open(INSTRUMENTS_FILE)); cfg = {**allc.get("_default", {}), **allc.get(SYMBOL, {})}
    except Exception: pass
    PIP = cfg.get("pip", PIP); ATR_REF = cfg.get("atr_ref", ATR_REF)
    PXD = max(0, int(round(-math.log10(PIP)))) + 1   # price decimals from PIP (gold 2, EURUSD 5, USDJPY 3, indices 1)
    RISK_USD = cfg.get("risk_usd", RISK_USD); PIP_VALUE = cfg.get("pip_value", PIP_VALUE)
    USE_TPO = bool(cfg.get("use_tpo", False))
    LOT_MIN = cfg.get("lot_min", LOT_MIN); LOT_MAX = cfg.get("lot_max", LOT_MAX); LOT_STEP = cfg.get("lot_step", LOT_STEP)
    TV_SYMBOL = cfg.get("tv", SYMBOL); SESSIONS_OK = cfg.get("sessions"); SYMBOL_FLAGS = cfg.get("flags", {}) or {}
    if os.environ.get("TV_CHART_OVERRIDE"): os.environ["TV_CHART"] = os.environ["TV_CHART_OVERRIDE"]   # backtest: pin to a replay tab (loop never sets this)
    elif cfg.get("chart"): os.environ["TV_CHART"] = str(cfg["chart"])   # pin all tv() subprocess reads to this window
    s = os.environ.get("STATE_SUFFIX") or SYMBOL.lower()   # backtest isolates volatile state to its own namespace (loop never sets this)
    CD_FILE       = os.path.expanduser(f"~/.tv_fast_{s}_cd.json")
    WATCH_CD_FILE = os.path.expanduser(f"~/.tv_fast_{s}_watch.json")
    VP_FILE       = os.path.expanduser(f"~/.tv_fast_{s}_vp.json")
    TG_STATE      = os.path.expanduser(f"~/.tv_fast_{s}_tg.json")
    TRADE_STATE   = os.path.expanduser(f"~/.tv_fast_{s}_trade.json")
    PENDING_FILE  = os.path.expanduser(f"~/.tv_fast_{s}_pending.json")
    ZONES_FILE    = os.path.expanduser(f"~/tradingview-mcp/zones_{s}.json")   # live: zones_<sym>.json; backtest (STATE_SUFFIX set): isolated zones_<suffix>.json so date-faithful regeneration never touches live zones

def _log_path():
    """Per-pair-per-day log: logs/<symbol>/<YYYY-MM-DD>.csv (the auto-learn dataset, split by instrument & day)."""
    d = os.path.expanduser(f"~/tradingview-mcp/logs/{SYMBOL.lower()}")
    try: os.makedirs(d, exist_ok=True)
    except Exception: pass
    return os.path.join(d, _dt.datetime.now().astimezone().strftime("%Y-%m-%d") + ".csv")

def log_signal(row):
    """Upsert a row (by id) into today's per-symbol log. (A trade opened pre-midnight and finalized after
    lands in the new day's file as a fresh row — acceptable; intraday upserts stay intact.)"""
    path = _log_path()
    rows = []
    if os.path.exists(path):
        try: rows = list(_csv.DictReader(open(path)))
        except Exception: rows = []
    found = False
    for r in rows:
        if r.get("id") == str(row["id"]):
            r.update({k: str(v) for k, v in row.items()}); found = True
    if not found:
        rows.append({k: str(v) for k, v in row.items()})
    try:
        w = _csv.DictWriter(open(path, "w", newline=""), fieldnames=SIG_COLS); w.writeheader()
        for r in rows: w.writerow({k: r.get(k, "") for k in SIG_COLS})
    except Exception: pass
    try:   # dual-write: also UPSERT into the SQLite outcomes store (ACID/concurrent). CSV stays the
        import outcome_db   # source of truth/fallback — a DB failure must NEVER break the scanner.
        outcome_db.log_signal({**row, "symbol": SYMBOL})
    except Exception: pass

# Loiter-prone reversal-at-level families: they re-fire every tick as price oscillates around a (quasi-stable)
# VA/VWAP level, and the LOGGED entry is the drifting current price — so price-keyed dedup misses them and the
# log fills with near-identical rows (prev-VAL hit 48 rows in a day). Dedup these by side+family only (codex).
COARSE_DEDUP_FAMILIES = ("VAL rejection", "VA rejection", "VWAP rejection", "VWAP bounce")
def floor_skip_key(side, entry, why):
    """Thesis identity for de-duping auto-skip logging: same side + same ~price + same pattern. For the
    loiter-prone VA/VWAP-rejection families the drifting entry is dropped (side+family only) so oscillation
    near a level collapses to one row per dedup window instead of spamming."""
    if any(f in (why or "") for f in COARSE_DEDUP_FAMILIES):
        return f"{side}|{why}"
    return f"{side}|{round(entry)}|{why}"

def is_dup_skip(prev, key, now, window=600):
    """Pure dedup predicate: True if `key` matches the previously-logged skip within `window` seconds."""
    return bool(prev) and prev.get("key") == key and (now - prev.get("t", 0)) < window

FLOOR_SKIP_DEDUP_S = 3600   # an auto-skip thesis logs at most once per hour (chop re-fires the same un-tradeable setup every minute → log spam)

def log_floor_skip(side, why, entry, grade, rng10, body_p, htf, rr1, flags):
    """Record a pre-hold AUTO-SKIP (deduped by thesis ~1h) so analyze_logs can MEASURE what the hard floor
    absorbs. result='auto-skip'; the actual R:R goes in `exit`, the reason flags in `pips` (same convention
    as a 'rejected' row). Dedup tracks the timestamp of EVERY recent thesis-key (not just the last skip), so
    interleaved chop theses (CRT/zone-bounce/momentum cycling) each dedup independently — a recurring
    chop-thesis logs once/hour instead of every minute."""
    f = os.path.expanduser(f"~/.tv_fast_{SYMBOL.lower()}_skip.json")
    key = floor_skip_key(side, entry, why); now = time.time()
    try:
        recent = json.load(open(f))
        if not isinstance(recent, dict) or "key" in recent: recent = {}   # ignore the old single-prev format
    except Exception: recent = {}
    if now - recent.get(key, 0) < FLOOR_SKIP_DEDUP_S: return              # this thesis already logged within the window
    recent[key] = now
    recent = {k: t for k, t in recent.items() if now - t < FLOOR_SKIP_DEDUP_S}   # prune expired keys
    try: json.dump(recent, open(f, "w"))
    except Exception: pass
    log_signal({"id": int(time.time()), "time": _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
                "side": side, "grade": grade, "pattern": why, "entry": entry, "sl": "", "tp1": "",
                "rng10": round(rng10), "body_p": round(body_p), "htf": htf,
                "result": "auto-skip", "exit": round(rr1, 2) if rr1 is not None else "", "pips": "; ".join(flags)})

def set_active_trade(side, entry, sl, tp1, tp2, sid, be_trig=BE_TRIGGER_P):
    try:   # finalize any still-open prior trade that this new signal supersedes
        old = json.load(open(TRADE_STATE))
        if old.get("active") and old.get("id") and old.get("id") != sid:
            if old.get("tp1_hit"):   # already banked +50 — keep the win, don't downgrade to 'superseded'
                ot1 = old["tp1"]; tp = round((old["entry"]-ot1)/PIP if old["side"]=="SHORT" else (ot1-old["entry"])/PIP)
                log_signal({"id": old["id"], "result": "TP1", "exit": round(ot1, PXD), "pips": tp})
            else:
                oe = old["entry"]; pips = round((oe-entry)/PIP if old["side"] == "SHORT" else (entry-oe)/PIP)
                log_signal({"id": old["id"], "result": "superseded", "exit": round(entry, PXD), "pips": pips})
    except Exception: pass
    try: json.dump({"active": True, "id": sid, "side": side, "entry": entry, "sl": sl,
                    "tp1": tp1, "tp2": tp2, "tp1_hit": False, "be_trig": be_trig, "t0": time.time()}, open(TRADE_STATE, "w"))
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
    # Breakeven protection (pre-TP1): track max favorable excursion; once it runs +BE_TRIGGER_P, pull the stop to
    # entry so a reversal scratches at 0 instead of the full SL. (06-04 fix: a short ran +38p, never hit TP1, gave
    # it all back to -30p — this turns that into breakeven.) Fires a one-time alert so you move your broker stop too.
    fav = PP(price)
    if fav > t.get("mfe", -10**9): t["mfe"] = fav
    be_moved = t.get("be_moved", False)
    if not tp1_hit and not be_moved and t.get("mfe", 0) >= t.get("be_trig", BE_TRIGGER_P):
        sl = t["sl"] = e; t["be_moved"] = be_moved = True
        _tg_text(f"🛡️ {SYMBOL} {side} — stop to BREAKEVEN ({e}). Ran +{t['mfe']:.0f}p; protecting the scratch. Move your stop to entry.")
    hit_sl  = price >= sl  if side == "SHORT" else price <= sl
    hit_tp2 = price <= tp2 if side == "SHORT" else price >= tp2
    hit_tp1 = price <= tp1 if side == "SHORT" else price >= tp1
    label = None
    if hit_tp2:
        label, lvl, res = f"🎯 TP2 (+{PP(tp2):.0f}p)", tp2, "TP2"; t["active"] = False
    elif hit_sl:
        t["active"] = False
        if tp1_hit:   # remainder stopped at breakeven AFTER banking the partial — still a win, log as TP1
            label, lvl, res = "🟰 BE (after TP1)", tp1, "TP1"
        elif be_moved:   # pre-TP1 breakeven protection caught it — scratched at entry, no loss
            label, lvl, res = "🛡️ BE (protected)", e, "BE"
        else:
            label, lvl, res = "❌ SL", sl, "SL"
    elif hit_tp1 and not tp1_hit:
        label, lvl, res = f"✅ TP1 (+{PP(tp1):.0f}p)", tp1, "TP1"; t["tp1_hit"] = True; t["sl"] = e   # stop -> breakeven
    if label:
        if res == "BE":            extra = "  → scratched at breakeven, no loss (protected the +run)."
        elif res == "SL":          extra = "  → trade closed."
        elif "BE" in label:        extra = f"  → remainder out at breakeven ({e}); +{PP(tp1):.0f}p partial kept."
        elif res == "TP1":         extra = "  → take partial, SL to breakeven."
        else:                      extra = "  → trade closed."
        _tg_text(f"{label} — {SYMBOL} {side} hit {lvl} (entry {e}, now {price}).{extra}")
        if sid: log_signal({"id": sid, "result": res, "exit": round(lvl, PXD), "pips": PP(lvl)})
    elif time.time() - t.get("t0", time.time()) > 720:   # 12-min timeout
        t["active"] = False
        res, exit_px = ("TP1", tp1) if tp1_hit else ("timeout", price)   # tp1 already banked -> keep the win
        if sid: log_signal({"id": sid, "result": res, "exit": round(exit_px, PXD), "pips": PP(exit_px)})
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

def chop_15m(b):
    """Range/chop detector on the 15m TF (resampled from the 1m bars in hand — no TF switch).
    Kaufman efficiency ratio = |net move| / sum(|bar-to-bar moves|): ~1 = clean trend, ~0 = chop.
    Returns (is_chop, er)."""
    c = [b[i]['close'] for i in range(len(b)-1, -1, -ER_STRIDE)][::-1]   # 15m-sampled closes (TF-aware stride)
    c = c[-12:]                                                          # keep ~3h (12 x 15m) regardless of base TF
    if len(c) < 5: return (False, 1.0)
    denom = sum(abs(c[k]-c[k-1]) for k in range(1, len(c)))
    er = abs(c[-1]-c[0]) / denom if denom else 0.0
    return (er < CHOP_ER, round(er, 2))

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

def smc_context():
    """SMC + Auto-Trendlines confluence read on the CURRENT (execution/replay) chart — no TF switch (Option
    A). Cached to a file (TTL) to avoid re-reading every tick; the backtest clears this cache at its
    step-refresh so it stays date-faithful. The HTF layer comes from our own zones. Returns {} if missing."""
    if not smcmod:
        return {}
    s = os.environ.get("STATE_SUFFIX") or SYMBOL.lower()
    f = os.path.expanduser(f"~/.tv_fast_{s}_smc.json")
    try:
        c = json.load(open(f))
        if time.time() - c.get("t", 0) < SMC_TTL:
            return c.get("ctx", {})
    except Exception:
        pass
    try:
        chart = os.environ.get("TV_CHART", "")
        ctx = smcmod.read_chart_context(chart, dedup_tol=SMC_TOL * PIP)
        # Auto Trendlines as MULTI-TF confluence (4h/1h/15m) — the indicator recomputes per TF, so this
        # switches TF, reads, and restores BASE_TF. Cached (SMC_TTL), so the TF sweep only runs ~hourly.
        ctx["trendlines"] = smcmod.read_trendlines_mtf(chart, base_tf=str(BASE_TF))
        json.dump({"t": time.time(), "ctx": ctx}, open(f, "w"))
        return ctx
    except Exception:
        return {}

def stored_smc():
    """The STORED multi-TF SMC snapshot (zones_<sym>.json 'smc' block, refreshed by the hourly cron).
    Trade-check consumes THIS stable snapshot — not a fresh per-tick chart read (the live LuxAlgo read is
    flaky/unstable). Returns the smc block dict ({ts, price, tf:{...}}) or {} if absent/empty/STALE — a
    delayed or broken refresh must contribute nothing to scoring, never feed old SMC into the grade."""
    try:
        blk = json.load(open(ZONES_FILE)).get("smc") or {}
    except Exception:
        return {}
    if not blk:
        return {}
    age = time.time() - blk.get("ts", 0)
    if age > SMC_SNAP_MAX_AGE:
        print(f">> WARN: stored SMC snapshot is stale ({age/3600:.1f}h old > {SMC_SNAP_MAX_AGE//3600}h) — ignoring it for confluence.")
        return {}
    return blk

def main():
    draw = "--draw" in sys.argv
    DRY = "--dry" in sys.argv   # test mode: compute + print only, NO telegram/log/sound/state
    REVIEW = "--review" in sys.argv   # AI-review gate: hold confirmed trades for approval (TP/SL + heads-ups still go)
    FL = load_flags()
    AI = FL.get("ai_decide", False)   # AI-decides mode: bypasses soft quality filters, but still honors hard floor, observation gate, and family caps
    global HTF_R, HTF_S, PDH, PDL, ASIA_H, ASIA_L
    HTF_R, HTF_S, PDH, PDL, ASIA_H, ASIA_L = load_zones()   # auto-derived zones+session ranges (rebuilt ~6h); hardcoded = fallback
    SMC_STORED = stored_smc() if (FL.get("smc_mtf", True) or FL.get("smc_ob_zones", True)) else {}
    # CLASSIC supply/demand + S/R zones (zones_sd, the ones draw_review draws) join the confluence machinery:
    # buy zone/support → support side; sell zone/resistance → resistance side. So at_R/at_S/conf_R/conf_S and
    # the target picker grade against EXACTLY what's drawn (drawn == traded — overlapping zones are kept, not
    # dropped; conf_R/conf_S de-dup at COUNT time via count_distinct_at). (KL top-tier boost is in grading.)
    if FL.get("classic_zones", True):
        HTF_R, HTF_S = merge_classic_zones(HTF_R, HTF_S, CLASSIC)
    # STORED SMC order blocks from zones_<symbol>.json must also be first-class trade zones, not only
    # post-trigger confluence. This lets a clear supply/demand OB tap form a zone-bounce candidate.
    # Ambiguous straddle/equilibrium boxes are intentionally ignored by merge_smc_ob_zones().
    if FL.get("smc_ob_zones", True):
        HTF_R, HTF_S = merge_smc_ob_zones(HTF_R, HTF_S, SMC_STORED)
    tv("timeframe", str(BASE_TF))   # execution TF (1m live, 5m backtest) — load_zones/VP may have switched TF; restore before reading bars
    price = tv("quote").get("last")
    b = tv("ohlcv", "-n", "180").get("bars", [])
    if price is None or len(b) < 40:
        print("ERR: no data"); return
    # mandatory indicator: the Auto Trendlines must be enabled on the chart (multi-TF trendline confluence).
    # Fail LOUD if it's missing rather than silently scoring without it.
    if FL.get("auto_trendlines", True) and smcmod:
        smcmod.assert_trendlines(os.environ.get("TV_CHART", ""))
    n = len(b); last = b[-1]
    if not DRY: check_active_trade(price)   # alert TP1/TP2/SL on any live signalled trade
    # --- volatility gate ---
    rng10 = (max(x['high'] for x in b[-10:]) - min(x['low'] for x in b[-10:])) / PIP
    atr = sum(x['high'] - x['low'] for x in b[-14:]) / 14 / PIP
    # --- ATR-normalized sizing: scale the gold-tuned pip constants by a STABLE volatility factor so every
    # strategy self-fits the instrument, regime AND timeframe. atr_base = avg bar range over the last ≤120
    # EXECUTION-TF bars (instrument/TF character, not the noisy instant ATR) — on 5m that's ~10h and ~1.8–2.2×
    # the 1m value, so VS auto-scales the geometry up for 5m. VS=1 at gold's ~30p 1m ref. Clamped to avoid extremes. ---
    _nb = min(len(b), 120)
    atr_base = (sum(x['high'] - x['low'] for x in b[-_nb:]) / _nb / PIP) if _nb else atr
    VS = max(0.5, min(4.0, atr_base / ATR_REF))
    chase_p  = MAX_CHASE_P * VS           # anti-chase max extension
    wick_p   = ZONE_WICK_P * VS           # zone-bounce min rejection wick
    room_min = MIN_ROOM_P * VS            # min clean room to next structure (R:R floor)
    tp_buf   = TP_BUFFER_P * VS           # adaptive-TP buffer short of the wall
    be_trig  = round(BE_TRIGGER_P * VS)   # pre-TP1 breakeven trigger (stored per-trade for the tracker)
    dyn_tolp = DYN_TOL * PIP * VS         # dynamic-level "at level" halo (price units, pip-normalised)
    sl_lo_p, sl_hi_p = 30*VS, 35*VS       # SL cap band (pips)
    tp1_cap, tp2_cap = 50*VS, 100*VS      # TP target caps (pips)
    vol_min  = VOL_MIN_RANGE10 * VS       # volatility gate (10-bar range floor)
    buf_p, rcl_p = 2*VS, 4*VS             # break buffer / min reclaim-back-inside (pips)
    # --- momentum candle ---
    body = last['close'] - last['open']; body_pips = abs(body) / PIP
    avgbody = sum(abs(x['close'] - x['open']) for x in b[-20:]) / 20 / PIP
    strong = body_pips > 1.6 * max(avgbody, 0.5)
    bull = body > 0
    is_chop, chop_er = chop_15m(b)   # 15m range/chop detector (suppress breakout/momentum when ranging)
    sh, sl = pivots(b)
    # --- trendlines through last 2 swing highs / lows ---
    res_tl = line_through(sh[-2], sh[-1]) if len(sh) >= 2 else None
    sup_tl = line_through(sl[-2], sl[-1]) if len(sl) >= 2 else None
    res_at = round(proj(res_tl, n-1), PXD) if res_tl else None
    sup_at = round(proj(sup_tl, n-1), PXD) if sup_tl else None
    # --- consolidation range (last 15 bars) ---
    hi15 = max(x['high'] for x in b[-15:]); lo15 = min(x['low'] for x in b[-15:])
    range15 = (hi15 - lo15) / PIP
    tight = range15 < TIGHT_RANGE_P * VS               # VS-scaled so it self-fits the execution TF (5m bars are wider)
    # --- double top / bottom (last 3 swing highs/lows) ---
    dt_eq = DT_EQ_P * VS                                # "equal highs/lows" tolerance, VS-scaled
    dtop = len(sh) >= 2 and abs(sh[-1][1] - sh[-2][1]) / PIP < dt_eq
    dbot = len(sl) >= 2 and abs(sl[-1][1] - sl[-2][1]) / PIP < dt_eq

    # --- chart indicators: session VWAP (+bands), EMA 50/100/200, RSI — read not computed (self-heal) ---
    vw, vw_up, vw_lo, em, rsi = read_chart_levels([x['close'] for x in b])
    e50, e100, e200 = em.get(50), em.get(100), em.get(200)   # 1m EMAs — execution-level S/R only
    vpoc, vah, val, regime = volume_profile()              # current-day TPO POC/value-area + HTF regime, cached
    prior_vas = prior_day_vas(SYMBOL, last['time'])        # prior-day VAH/POC/VAL from the va_store DB (reliable, date-faithful)
    if not FL.get("volume_profile", True): vpoc = vah = val = None; prior_vas = []   # flag only suppresses the VP levels
    _rstep = 100*PIP; r10 = round(price/_rstep)*_rstep; near_round = round(r10, PXD) if abs(r10-price) < 20*PIP else None   # pip-scaled round number ($10 gold, 0.01 EUR, 1.00 JPY, 100 idx)
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
        ext += [(vpoc, "VPOC"), (vah, "value-area high"), (val, "value-area low")]   # current-day volume-profile levels
        for _pv in (prior_vas or []):   # prior-day value areas (from va_store DB) — see docs/value-area-framework.md
            _vah, _poc, _val = _pv.get("vah"), _pv.get("poc"), _pv.get("val")
            if None in (_vah, _poc, _val):
                ext += [(p, l) for p, l in ((_poc, "prevPOC"), (_vah, "prevVAH"), (_val, "prevVAL")) if p is not None]
                continue
            # when a boundary HUGS the POC (within ~1/3 of the VA width) it's effectively the same level —
            # merge so confluence counts it ONCE (a tight POC+VAH shouldn't read as two stacked levels).
            _mtol = max(dyn_tolp, 0.33 * (_vah - _val))
            _up, _lo = (_vah - _poc) <= _mtol, (_poc - _val) <= _mtol
            ext.append((_poc, "prevPOC" + ("/VAH" if _up else "") + ("/VAL" if _lo else "")))
            if not _up: ext.append((_vah, "prevVAH"))
            if not _lo: ext.append((_val, "prevVAL"))
        if not asian_now:   # only treat the Asian range as S/R AFTER the session completes
            ext += [(ASIA_H,"Asian high"), (ASIA_L,"Asian low")]
        for lvl, lab in ext:
            if lvl is None: continue
            (ptR if lvl >= price else ptS).append((lvl, lvl, lab))
    # HTF zones keep their intended wide tolerance; dynamic point-levels get the tight one
    at_R = near_htf(price, HTF_R) or near_htf(price, ptR, tol=dyn_tolp)
    at_S = near_htf(price, HTF_S) or near_htf(price, ptS, tol=dyn_tolp)
    # confluence: how many distinct levels sit right at price (used to strengthen/justify the grade)
    conf_R = count_distinct_at(HTF_R, price) + len([1 for p,_,_ in ptR if abs(p-price)<=dyn_tolp])   # distinct clusters → overlapping classic+HTF walls count ONCE
    conf_S = count_distinct_at(HTF_S, price) + len([1 for p,_,_ in ptS if abs(p-price)<=dyn_tolp])
    # next structure above / below entry (for adaptive TP) — horizontal walls only.
    # EMAs and VWAP are dynamic lines price flows THROUGH, so they don't cap a target.
    is_wall = lambda lab: not ("EMA" in lab or "VWAP" in lab)
    R_refs = [v for lo,hi,_ in HTF_R for v in (lo,hi)] + [p for p,_,lab in ptR if is_wall(lab)]
    S_refs = [v for lo,hi,_ in HTF_S for v in (lo,hi)] + [p for p,_,lab in ptS if is_wall(lab)]
    if FL.get("wall_dedup", False):
        # codex Option 2: cluster near-duplicate wall edges (SMC OB density saturates the map) and take each
        # cluster's NEAR edge — so a zone price is currently INSIDE stops reading as the next wall a few pips
        # away (the cramped-gate over-trigger). Flag-gated; default OFF leaves live geometry unchanged.
        _wtol = dyn_tolp
        nextR = next_wall(R_refs, price, "R", _wtol, 3*PIP)
        nextS = next_wall(S_refs, price, "S", _wtol, 3*PIP)
    else:
        nextR = min([r for r in R_refs if r > price + 3*PIP], default=None)
        nextS = max([s for s in S_refs if s < price - 3*PIP], default=None)

    print(f"\n[{_dt.datetime.now().astimezone():%Y-%m-%d %H:%M:%S %Z}]  PRICE {price}  TF={BASE_TF}m  VS={VS:.2f}  range10={rng10:.0f}p  atr={atr:.1f}p  lastBody={body_pips:.0f}p({'bull' if bull else 'bear'}) strong={strong} vol_ok={vol_ok}")
    print(f"resTL@{res_at}  supTL@{sup_at}  range15={range15:.0f}p tight={tight}  dblTop={dtop} dblBot={dbot}  VWAP={vw}{f' [{vw_lo}/{vw_up}]' if vw_up else ''}  EMA50/100/200={em.get(50)}/{em.get(100)}/{em.get(200)}  session={'ON' if sess_ok else 'off'}")
    print(f"RSI={rsi}  regime={regime}({VP_TF}m EMA stack)  15m-ER={chop_er}{' CHOP' if is_chop else ''}  VPOC/VAH/VAL={vpoc}/{vah}/{val}  confluence R{conf_R}/S{conf_S}  nextR={nextR} nextS={nextS}")
    if prior_vas:   # prior-day value areas + the inputs the AI needs to apply the framework (docs/value-area-framework.md)
        nv = prior_vas[0]   # most recent prior day = the primary reference (priority Rule)
        nvah, nval, npoc = nv.get("vah"), nv.get("val"), nv.get("poc")
        # Rules 3-5: where is price vs the most recent prior value area? -> discovery / balanced regime
        if nvah and price > nvah:   reg = f"discovery-UP (price>{nvah} prevVAH -> favor longs on VAH pullback+rejection)"
        elif nval and price < nval: reg = f"discovery-DOWN (price<{nval} prevVAL -> favor shorts on VAL pullback+rejection)"
        else:                       reg = f"balanced (inside {nval}-{nvah} -> fade extremes toward POC, don't chase center)"
        print(f"prevVA[open-vs-value]: {reg}")
        # each prior level relative to price (above/below + pip distance) for Rules 1/2/7 (with-trend + nearest-active)
        for p in prior_vas:
            md = (p.get("date") or "")[5:]
            parts = []
            for role, lvl in (("VAH", p.get("vah")), ("POC", p.get("poc")), ("VAL", p.get("val"))):
                if lvl is None: continue
                tag = f"{role} {lvl} ({'above' if lvl >= price else 'below'} {abs(lvl-price)/PIP:.0f}p)"
                # Rules 6/7 — Level State from current-session bars (Untested/Rejected/Accepted/Flipped).
                # Only meaningful for the most recent prior day's levels (priority Rule); older ones are context.
                if vastate is not None and p is prior_vas[0]:
                    st = vastate.level_state(lvl, b, role, poc=p.get("poc"), bar_minutes=BASE_TF)
                    cf = st["evidence"]["confidence"]
                    tag += f" [{st['state']}{'?' if cf == 'weak' else ''}]"
                parts.append(tag)
            if p.get("sp"):   # single-print zones = target levels (Rule 3/4 hierarchy: POC -> single prints -> ...)
                parts.append("SP[targets] " + ", ".join(f"{z[0]}-{z[1]}" for z in p["sp"]))
            print(f"  prevVA {md}: " + " | ".join(parts))
    print(f"HTF: {'@R '+at_R[2] if at_R else ''}{'@S '+at_S[2] if at_S else ''}{'(open space)' if not at_R and not at_S else ''}")

    if draw:
        if res_tl and len(sh) >= 2:
            tv("draw","shape","--type","trend_line","--price",str(sh[-2][1]),"--time",str(b[sh[-2][0]]['time']),
               "--price2",str(sh[-1][1]),"--time2",str(b[sh[-1][0]]['time']))
        if sup_tl and len(sl) >= 2:
            tv("draw","shape","--type","trend_line","--price",str(sl[-2][1]),"--time",str(b[sl[-2][0]]['time']),
               "--price2",str(sl[-1][1]),"--time2",str(b[sl[-1][0]]['time']))
        print("(trendlines drawn)")

    fib_overlay = FIB_ZONES if FL.get("fib_pullback", True) else []

    # --- live overlay: draw the value-area level map + SMC order blocks on the chart so it's VISIBLE.
    # Throttled (OVERLAY_MIN_INTERVAL) and id-tracked so it refreshes in the loop without flickering or
    # wiping your own drawings. Live only — skipped in --dry and in backtest (TV_CHART_OVERRIDE) runs.
    if (FL.get("draw_overlay", True) and dovr is not None and not DRY
            and not os.environ.get("TV_CHART_OVERRIDE") and (prior_vas or fib_overlay)):
        _ov = prior_vas[0] if prior_vas else {}
        _ova = {"vah": _ov.get("vah"), "val": _ov.get("val"), "poc": _ov.get("poc")}
        _ovst = {}
        if vastate is not None:
            for _k, _lvl in (("VAH", _ova["vah"]), ("VAL", _ova["val"]), ("POC", _ova["poc"])):
                if _lvl is not None:
                    _ovst[_k] = vastate.level_state(_lvl, b, _k, poc=_ova["poc"], bar_minutes=BASE_TF)["state"]
        # SMC OB boxes only if the (noisy, full-history) LuxAlgo read is explicitly enabled — off by default
        _boxes = (smc_context().get("smc", {}) or {}).get("boxes", []) if (smcmod and FL.get("smc_confluence", False)) else []
        _n = dovr.draw_overlay(os.environ.get("TV_CHART", ""), price, _ova, _ovst, _ov.get("sp"), _boxes,
                               band=OVERLAY_OB_BAND_P * PIP, t0=b[0]["time"], t1=last["time"],
                               min_interval=OVERLAY_MIN_INTERVAL, va_date=_ov.get("date"), fibs=fib_overlay)
        if _n >= 0:
            print(f"(overlay drawn: {_n} shapes)")

    # --- volatility gate ---
    if rng10 < vol_min and not AI:
        htf = at_R or at_S
        extra = f" — but price at {htf[2]}, watch for a burst there" if htf else ""
        print(f"\n>> TOO QUIET: last 10 1m bars only {rng10:.0f}p (<{vol_min:.0f}p). No fast scalp{extra}.")
        gate_trace("too_quiet"); return

    ff_bo, ff_lbl = (newsmod.is_blackout(SYMBOL) if newsmod else (False, ""))
    if FL["news_filter"] and (news or ff_bo):
        print(f"\n>> NEWS BLACKOUT — muted ({ff_lbl or 'manual window'})."); gate_trace("news"); return

    try: cd_t = json.load(open(CD_FILE)).get("t", 0)
    except Exception: cd_t = 0
    cd_left = COOLDOWN_MIN*60 - (time.time() - cd_t)
    if cd_left > 0 and not AI:
        print(f"\n>> COOLDOWN: {cd_left/60:.0f}m left since last signal — no new setups (anti-cluster)."); gate_trace("cooldown"); return

    fib_long = fib_pullback_signal(b, "LONG", PIP, VS, PXD) if FL.get("fib_pullback", True) else None
    fib_short = fib_pullback_signal(b, "SHORT", PIP, VS, PXD) if FL.get("fib_pullback", True) else None
    setups = []
    buf = buf_p * PIP  # break buffer (ATR-scaled)
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
        rcl = rcl_p * PIP   # must close >=rcl_p back INSIDE the swept level (genuine rejection, not a breakout run)
        if strong and not bull and last['high'] > sw_hi and last['close'] < sw_hi - rcl and near_htf(sw_hi, HTF_R):
            if reversal_context_ok("SHORT", sw_hi, conf_S, conf_R, prior_vas, b, dyn_tolp, BASE_TF):
                setups.append(("SHORT", "liquidity-sweep reversal", last['close'], last['high']))
            elif not DRY:
                log_floor_skip(
                    "SHORT", "liquidity-sweep reversal", last['close'], "strict-reversal",
                    round(rng10), round(body_pips), near_htf(sw_hi, HTF_R)[2], None,
                    ["strict reversal context: no stacked confluence or valid prior VA"],
                )
        if strong and bull and last['low'] < sw_lo and last['close'] > sw_lo + rcl and near_htf(sw_lo, HTF_S):
            if reversal_context_ok("LONG", sw_lo, conf_S, conf_R, prior_vas, b, dyn_tolp, BASE_TF):
                setups.append(("LONG", "liquidity-sweep reversal", last['close'], last['low']))
            elif not DRY:
                log_floor_skip(
                    "LONG", "liquidity-sweep reversal", last['close'], "strict-reversal",
                    round(rng10), round(body_pips), near_htf(sw_lo, HTF_S)[2], None,
                    ["strict reversal context: no stacked confluence or valid prior VA"],
                )
    # 6) Break-and-retest (broken swing level retested from the other side, rejected)
    if len(sh) >= 1:
        lv = sh[-1][1]
        if strong and bull and any(x['close'] > lv for x in b[-8:-1]) and last['low'] <= lv + 3*VS*PIP and last['close'] > lv:
            setups.append(("LONG", "break-and-retest", last['close'], lv - 3*VS*PIP))
    if len(sl) >= 1:
        lv = sl[-1][1]
        if strong and not bull and any(x['close'] < lv for x in b[-8:-1]) and last['high'] >= lv - 3*VS*PIP and last['close'] < lv:
            setups.append(("SHORT", "break-and-retest", last['close'], lv + 3*VS*PIP))
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
    # 9) Zone-reclaim — dip INTO a structural zone then close back OUT of it with net 3-bar momentum
    # (gradual bounce, no single strong candle). NOTE: confirmation lags — it tends to fire already
    # extended, where anti-chase blocks it. Default OFF; the real fix for catching the dip is an
    # anticipatory zone-touch entry (separate mode). Kept here, selective, for experimentation.
    if FL.get("zone_reclaim", False) and len(b) >= 6:
        cum3 = (last['close'] - b[-3]['open']) / PIP
        lo5 = min(x['low'] for x in b[-5:]); hi5 = max(x['high'] for x in b[-5:])
        for zlo, zhi, lab in HTF_S:
            if lo5 <= zhi and last['close'] > zhi + 5*PIP and bull and cum3 >= 20:
                setups.append(("LONG", "zone-reclaim bounce", last['close'], zlo)); break
        for zlo, zhi, lab in HTF_R:
            if hi5 >= zlo and last['close'] < zlo - 5*PIP and (not bull) and cum3 <= -20:
                setups.append(("SHORT", "zone-reclaim rejection", last['close'], zhi)); break
    # 10) Session liquidity sweep — a session raids the PRIOR session's high/low (resting stops) then
    # reverses back inside (Asian-range raid / Judas swing). Watches real session pools, not recent swings.
    if FL.get("session_sweep", True):
        try: _z = json.load(open(ZONES_FILE))
        except Exception: _z = {}
        h = _dt.datetime.utcfromtimestamp(ts).hour
        # only the genuinely-prior session's pool is live, gated by each session's real UTC end-hour
        # (from the indicator config, DST-correct): prior-day always; Asian/London once done; NY overnight.
        ae = _z.get("asia_end", 7); le = _z.get("london_end", 16); ne = _z.get("ny_end", 22)
        pools_hi = [(PDH, "PDH")]; pools_lo = [(PDL, "PDL")]
        if ae is not None and h >= ae:                pools_hi.append((ASIA_H, "Asian-H"));         pools_lo.append((ASIA_L, "Asian-L"))
        if le is not None and h >= le:                pools_hi.append((_z.get("london_h"), "London-H")); pools_lo.append((_z.get("london_l"), "London-L"))
        if ne is not None and (h >= ne or h < (ae or 7)): pools_hi.append((_z.get("ny_h"), "NY-H"));    pools_lo.append((_z.get("ny_l"), "NY-L"))
        for lvl, nm in pools_hi:   # raid buy-side liquidity above, reject -> SHORT
            if lvl and strong and not bull and last['high'] > lvl and last['close'] < lvl - rcl_p*PIP:
                setups.append(("SHORT", f"{nm} liq sweep", last['close'], last['high'])); break
        for lvl, nm in pools_lo:   # raid sell-side liquidity below, reclaim -> LONG
            if lvl and strong and bull and last['low'] < lvl and last['close'] > lvl + rcl_p*PIP:
                setups.append(("LONG", f"{nm} liq sweep", last['close'], last['low'])); break
    # 11) Key-Level rejection — KL zones are trade locations, not merely confluence. They still need a
    # directional rejection candle and still pass through hard-floor/R:R/session/review gates below.
    if FL.get("key_level_trades", True) and FL.get("classic_zones", True):
        _kl_long = classic_key_level_at(CLASSIC, "LONG", price, ZHALO_P * PIP)
        _kl_short = classic_key_level_at(CLASSIC, "SHORT", price, ZHALO_P * PIP)
        if key_level_rejection(last, _kl_long, "LONG", wick_p, PIP):
            setups.append(("LONG", "key-level rejection", last["close"], round(last["low"] - buf_p*PIP, PXD)))
        if key_level_rejection(last, _kl_short, "SHORT", wick_p, PIP):
            setups.append(("SHORT", "key-level rejection", last["close"], round(last["high"] + buf_p*PIP, PXD)))
    # 12) Zone-bounce — a REJECTION candle at a confluent zone (NO "strong" candle / 2-bar pattern needed).
    # Catches the gradual bounce/fade the impulse triggers miss: long lower-wick close-up at support, or
    # upper-wick close-down at resistance. Tight stop just beyond the zone. Gated to confluent (conf>=2) zones.
    if FL.get("zone_bounce", True):
        # LONG: wick dipped anywhere INTO the support band (floor OR upper edge of a wide zone) and closed back
        # above the floor with a real (>=ZONE_WICK_P) rejection wick. Widened 06-04 from floor-pierce-only so it
        # also catches upper-edge reclaims of wide zones (the ~4500 bounce inside 4486-4503 it used to miss).
        if (at_S and at_S[1] > at_S[0]
                and last['low'] <= at_S[1] and last['close'] >= at_S[0]  # wick into the band, close didn't lose the floor
                and (last['close'] - last['low']) >= wick_p*PIP and last['close'] > last['open']):
            if reversal_context_ok("LONG", last['low'], conf_S, conf_R, prior_vas, b, dyn_tolp, BASE_TF):
                setups.append(("LONG", "zone-bounce rejection", last['close'], round(last['low'] - buf_p*PIP, PXD)))
            elif not DRY:
                log_floor_skip(
                    "LONG", "zone-bounce rejection", last['close'], "strict-reversal",
                    round(rng10), round(body_pips), at_S[2], None,
                    ["strict reversal context: no stacked confluence or valid prior VA"],
                )
        if (at_R and at_R[1] > at_R[0]
                and last['high'] >= at_R[0] and last['close'] <= at_R[1]  # wick into the band, close didn't break the top
                and (last['high'] - last['close']) >= wick_p*PIP and last['close'] < last['open']):
            if reversal_context_ok("SHORT", last['high'], conf_S, conf_R, prior_vas, b, dyn_tolp, BASE_TF):
                setups.append(("SHORT", "zone-bounce rejection", last['close'], round(last['high'] + buf_p*PIP, PXD)))
            elif not DRY:
                log_floor_skip(
                    "SHORT", "zone-bounce rejection", last['close'], "strict-reversal",
                    round(rng10), round(body_pips), at_R[2], None,
                    ["strict reversal context: no stacked confluence or valid prior VA"],
                )
    # 13) Fib correction pullback — after a clear impulse leg, wait for price to pull back into the
    # primary correction pocket (0.52-0.645 on the user's chart template) and reject it. Directional:
    # SHORT draws top→bottom on a down wave; LONG draws bottom→top on an up wave.
    if FL.get("fib_pullback", True):
        if fib_long:
            setups.append(("LONG", f"fib pullback rejection {fib_long['ratio']}", last['close'], round(last['low'] - buf_p*PIP, PXD)))
        if fib_short:
            setups.append(("SHORT", f"fib pullback rejection {fib_short['ratio']}", last['close'], round(last['high'] + buf_p*PIP, PXD)))
    # CRT (Candle Range Theory): the prior 15m block = the "range candle"; the last few 1m bars SWEEP its
    # high/low (liquidity grab) and the last candle CLOSES BACK INSIDE the range = manipulation + reversal.
    # Distinct from liquidity_sweep (which needs an HTF zone): CRT's edge is the swept range-extreme + the
    # opposite range end as a defined target. Built-in room rule (>=25p to the opposite end) keeps R:R real.
    if FL.get("crt", True) and len(b) >= 25:
        rng = b[-20:-5]                                  # prior 15-bar block = the range candle (rolling 15m proxy)
        rhi = max(x['high'] for x in rng); rlo = min(x['low'] for x in rng)
        sw = b[-5:]                                      # last 5 bars = the sweep+reclaim window (recent, timely)
        swlo = min(x['low'] for x in sw); swhi = max(x['high'] for x in sw)
        # bullish CRT: swept >=3p below the range low, last candle reclaimed back inside (bullish close), room up
        if (swlo <= rlo - 3*VS*PIP and last['close'] > rlo and last['close'] > last['open']
                and (rhi - last['close']) >= room_min*PIP):
            setups.append(("LONG", "CRT sweep+reclaim", last['close'], round(swlo - buf_p*PIP, PXD)))
        # bearish CRT: swept >=3p above the range high, last candle reclaimed back inside (bearish close), room down
        if (swhi >= rhi + 3*VS*PIP and last['close'] < rhi and last['close'] < last['open']
                and (last['close'] - rlo) >= room_min*PIP):
            setups.append(("SHORT", "CRT sweep+reclaim", last['close'], round(swhi + buf_p*PIP, PXD)))
    # 13) VWAP value-area rejection (docs/gold-vwap-strategy.md): VWAP-aligned rejection off a VALID prior
    # VAL/POC/flipped-VAH (long) or VAH/POC/flipped-VAL (short), R:R>=1:2 to the nearest VWAP/POC target.
    # Reversal-class (the "VWAP" tag exempts it from the volume/anti-chase filters below).
    if FL.get("va_reject", True) and vareject is not None and vw and prior_vas:
        _pv = prior_vas[0]
        for s in vareject.detect_va_reject(price, vw, {"vah": _pv.get("vah"), "val": _pv.get("val"), "poc": _pv.get("poc")},
                                           b, pip=PIP, bar_minutes=BASE_TF):
            setups.append((s[0], s[1], s[2], round(s[3], PXD)))
    # volume filter: breakouts/breaks need above-avg volume; reversals/correction entries
    # (sweep/retest/VWAP/reclaim/bounce/CRT/fib/key-level) are exempt.
    if FL["volume_filter"] and not vol_ok and not AI:
        setups = [s for s in setups if any(w in s[1] for w in ("sweep", "retest", "VWAP", "reclaim", "bounce", "CRT", "fib", "key-level"))]
    # feature-flag filter: drop any setup whose strategy is toggled off
    setups = [s for s in setups if FL.get(flag_for(s[1]) or "", True)]

    # observation gate: families in OBSERVE_FAMILIES are detected + logged (measurable) but NOT fired/surfaced,
    # until they prove cost-adjusted edge out of sample. Applies even under ai_decide; set observation_gate=false
    # for an explicit research override.
    if FL.get("observation_gate", True) and setups:
        kept = []
        for s in setups:
            if flag_for(s[1]) in OBSERVE_FAMILIES:
                print(f">> OBSERVE-ONLY: {s[0]} [{s[1]}] — family under observation (negative net); logged, not fired.")
                if not DRY:
                    _htf = at_S if s[0] == "LONG" else at_R
                    log_floor_skip(s[0], s[1], s[2], "observe", round(rng10), round(body_pips), _htf[2] if _htf else "open", None, ["observation-only"])
            else:
                kept.append(s)
        setups = kept

    # range filter: in 15m chop, suppress BREAKOUT/CONTINUATION setups (false breaks in a range).
    # Reversals (sweep/VWAP/retest/reclaim) stay — fading the range is the right play when chopping.
    if FL.get("range_filter", True) and is_chop and setups and not AI:
        kept = []
        for s in setups:
            if any(k in s[1] for k in ("trendline", "breakout", "breakdown", "impulse", "double")):
                print(f">> SKIP RANGE: {s[0]} [{s[1]}] — 15m is chop (ER={chop_er}<{CHOP_ER}); breakouts fail in a range.")
            else:
                kept.append(s)
        setups = kept

    # anti-chase: don't enter a CONTINUATION setup after price has already run far off its base
    # (avoids buying the top / selling the bottom of a vertical spike). Reversals fade extension -> exempt.
    if FL.get("anti_chase", True) and setups and not AI:
        base_lo = min(x['low'] for x in b[-CHASE_LOOKBACK:]); base_hi = max(x['high'] for x in b[-CHASE_LOOKBACK:])
        ext_up = (price - base_lo)/PIP; ext_dn = (base_hi - price)/PIP
        def chasing(side, why):
            if not any(k in why for k in ("trendline", "breakout", "breakdown", "impulse", "double")):
                return False   # sweep / VWAP / retest are reversals — they trade the turn, exempt
            return ext_up > chase_p if side == "LONG" else ext_dn > chase_p
        kept = []
        for s in setups:
            if chasing(s[0], s[1]):
                run = ext_up if s[0] == "LONG" else ext_dn
                print(f">> SKIP CHASE: {s[0]} [{s[1]}] — price already ran {run:.0f}p off the {CHASE_LOOKBACK}-bar base (>{chase_p:.0f}p); too late, would be buying the top.")
            else:
                kept.append(s)
        setups = kept

    # RSI exhaustion gate: don't chase a continuation into an overbought/oversold blow-off (reversals exempt)
    if FL.get("rsi_filter", True) and rsi is not None and setups and not AI:
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
        # trend-aware heads-up side: in a trending regime, only warn WITH the trend (a counter-trend
        # heads-up needs an A+ confirmed trigger anyway, so don't pre-alert shorts in an uptrend).
        cands = ([("LONG", at_S)] if at_S else []) + ([("SHORT", at_R)] if at_R else [])
        if FL.get("trend_regime", True) and regime == "UP":   cands = [c for c in cands if c[0] != "SHORT"]
        if FL.get("trend_regime", True) and regime == "DOWN": cands = [c for c in cands if c[0] != "LONG"]
        if not cands and (at_R or at_S):
            print(f">> heads-up suppressed: price at {(at_R or at_S)[2]} but it's counter to the {regime} trend (A+ confirmation can still fire)."); gate_trace("watch_counter"); return
        if cands:
            sidehint, htf = cands[0]
            print(f"\n>> HTF WATCH: price at {htf[2]} — good-trade location; a {sidehint.lower()} trigger here = A+. Waiting.")
            # heads-up cooldown: don't spam as price wiggles across overlapping levels (round#, zone, VWAP band).
            # Only re-ping if WATCH_CD_MIN elapsed OR price moved to a genuinely new zone (>WATCH_NEW_ZONE_P away).
            try: w = json.load(open(WATCH_CD_FILE))
            except Exception: w = {}
            new_zone = abs(price - w.get("price", 0)) > WATCH_NEW_ZONE_P * VS and htf[2] != w.get("label")
            recent = (time.time() - w.get("t", 0)) < WATCH_CD_MIN*60
            if recent and not new_zone:
                print(f">> heads-up suppressed (within {WATCH_CD_MIN}m of last ping, same ~zone)."); gate_trace("watch_dedup"); return
            wa = "🟢⬆️" if sidehint == "LONG" else "🔴⬇️"
            wmsg = (f"{wa} 👀 {SYMBOL} — SETUP FORMING ({sidehint})\nPrice at {htf[2]} (~{price}).\n"
                    f"Get ready — I'll send the CONFIRMED entry (with SL/TP) when a {sidehint.lower()} trigger fires.")
            # In AI-review mode, DON'T auto-ping heads-ups to Telegram — they fire on every zone touch and
            # mostly never become trades (user: too many "forming" pings, no trade after). The readout still
            # prints "HTF WATCH" so Claude/AI can ping a heads-up ONLY when it judges the setup high-probability.
            # Only AI-approved CONFIRMED entries (+ TP/SL/BE) reach the phone. (Autonomous non-review mode still pings.)
            if not DRY and not REVIEW:
                notify_telegram(wmsg, f"watch|{htf[2]}")
                try: json.dump({"t": time.time(), "price": price, "label": htf[2]}, open(WATCH_CD_FILE, "w"))
                except Exception: pass
        else:
            print("\n>> NO FAST SETUP: volatility OK but no break/pattern/impulse trigger this bar.")
        gate_trace("no_trigger"); return

    # take the first (priority order above); build the trade
    side, why, entry, struct = setups[0]
    entry = round(entry, PXD)
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
    if grade == "C-into-zone" and not AI:
        print(f"\n>> SKIP: {side} into {'resistance' if side=='LONG' else 'support'} — counter-zone poke, not a real break (low quality)."); gate_trace("counter_zone_poke"); return

    is_rev = any(k in why for k in ("sweep", "VWAP", "retest"))
    # #4 confluence — multiple stacked levels at price strengthen the grade
    conf = conf_S if side == "LONG" else conf_R
    if FL.get("confluence", True) and conf >= 2:
        htf_note += f" | x{conf} confluence"
        if grade == "A": grade = "A+"
        elif grade.startswith("B"): grade = "A"
    fib_ctx = fib_long if side == "LONG" else fib_short
    if FL.get("fib_pullback", True) and fib_ctx:
        before = grade
        grade = fib_grade_boost(grade)
        htf_note += (f" | fib {fib_ctx['ratio']} pullback "
                     f"{fib_ctx['zone_lo']}-{fib_ctx['zone_hi']} "
                     f"(wave {fib_ctx['wave_lo']}-{fib_ctx['wave_hi']}, +{fib_ctx['wave_pips']}p)"
                     f"{' grade+1' if grade != before else ''}")
    # #2b RSI divergence at a level upgrades a reversal to A+
    if FL.get("rsi_filter", True) and is_rev and rsi is not None and rsi_divergence(b, side):
        htf_note += " | RSI divergence"; grade = "A+" if not grade.startswith("A+") else grade
    # #3 trend-regime — counter-trend needs A+; with-trend pullback gets a boost
    if FL.get("trend_regime", True) and regime != "flat":
        counter = (side == "LONG" and regime == "DOWN") or (side == "SHORT" and regime == "UP")
        with_trend = (side == "LONG" and regime == "UP") or (side == "SHORT" and regime == "DOWN")
        if counter and FL.get("counter_trend_soft", False):
            # SOFT counter-trend (flag, default OFF until backtest-validated): counter-trend dents the grade
            # (−1; −2 when ALSO chop/off-session), never a hard veto. Confidence already applies its own −1.
            _ctp = 2 if (is_chop or not sess_ok) else 1
            grade = downgrade_grade(grade, _ctp)
            htf_note += f" | counter-{regime} (grade −{_ctp})"
        elif counter and not grade.startswith("A+") and not AI:
            # LEGACY hard veto (default): only A+ counter-trend allowed (until counter_trend_soft is validated).
            print(f"\n>> SKIP COUNTER-TREND: {side} {grade} against {regime} EMA stack — only A+ counter-trend allowed."); gate_trace("counter_trend"); return
        elif counter:
            htf_note += f" | counter-{regime} (A+ only)"
        elif with_trend:
            htf_note += f" | with {regime} trend"
            if grade.startswith("B"): grade = "A"
    if FL["session_filter"] and not sess_ok and not grade.startswith("A+") and not AI:
        print(f"\n>> OFF-SESSION ({side} {grade}) — skipped (only A+ trades outside London/NY)."); gate_trace("off_session"); return
    if vol_ok and "open space" in grade: grade = "B+vol"   # volume gives a low-grade setup a small boost

    # --- HTF confluence — a '+' on top of our zones. SMC (LuxAlgo) and Auto-Trendlines are SEPARATE
    # indicators scored INDEPENDENTLY: a trendline touch counts even when the SMC indicator isn't present/read
    # (previously the trendline score was gated behind SMC presence, so it silently did nothing). ---
    cf_score = 0; cf_reasons = []   # SMC + Auto-Trendline confluence (hoisted for the confidence calc below)
    smc_zone = None; smc_aligned = None; smc_age = None   # stored multi-TF premium/discount — a SOFT confidence factor (smc_age = snapshot hours-old, logged for the bucket report)
    if (FL.get("smc_confluence", True) or FL.get("auto_trendlines", True) or FL.get("smc_mtf", True)) and smcmod:
        # the live chart read is only needed for the (flaky) per-tick SMC and the trendlines; skip it if neither is on.
        sctx = smc_context() if (FL.get("smc_confluence", True) or FL.get("auto_trendlines", True)) else {}
        if FL.get("smc_confluence", True):
            if not sctx.get("present"):
                print(">> WARN: LuxAlgo SMC indicator not on chart — SMC confluence missing.")
            else:
                c = smcmod.confluence(entry, side, sctx.get("smc", {}), SMC_TOL * PIP * VS)   # pure SMC (no trendlines)
                cf_score += c["score"]; cf_reasons += c["reasons"]
        if FL.get("auto_trendlines", True):                # Auto Trendlines — independent of SMC
            tls = sctx.get("trendlines", [])
            if tls and smcmod.near_level(entry, tls, SMC_TOL * PIP * VS):
                cf_score += 1; cf_reasons.append("Auto-Trendline")
        if FL.get("smc_mtf", True):                        # STORED multi-TF SMC snapshot (zones file, hourly cron) — stable
            _smcblk = SMC_STORED
            smc_age = round((time.time() - _smcblk["ts"]) / 3600, 2) if _smcblk.get("ts") else None
            sig = smcmod.mtf_signal(entry, side, _smcblk, SMC_TOL * PIP * VS)
            cf_score += sig["score"]; cf_reasons += sig["reasons"]
            smc_zone, smc_aligned = sig["zone"], sig["aligned"]
    # CLASSIC key-level zone — the TOP-probability tier (BOS + impulse + never wicked through). A KL S/D zone
    # in the trade direction at price is the strongest confluence we have, so it adds a hard +2 (→ A+). Runs
    # independently of SMC. (Plain non-KL classic zones already count via the at_R/at_S merge in main.)
    if FL.get("classic_zones", True):
        _want = ("buy zone", "support") if side == "LONG" else ("sell zone", "resistance")
        _klz = next((zz for zz in CLASSIC.get("zones", []) if zz.get("kl") and zz.get("role") in _want
                     and zz["lo"] - (SMC_TOL * PIP * VS) <= entry <= zz["hi"] + (SMC_TOL * PIP * VS)), None)
        if _klz:
            cf_score += 2; cf_reasons.append(f"KL {_klz['tf']} {_klz['role']}")
            htf_note += f" | ⭐KL {_klz['tf']} {_klz['role']}"
            grade = kl_upgrade(grade)   # KL = top tier → A+ directly (B+KL must reach A+, not just A)
    if cf_score:
        htf_note += f" | +{cf_score} HTF ({', '.join(cf_reasons[:3])})"
        if cf_score >= 2:                              # 2+ aligned HTF elements = a real grade boost
            grade = "A+" if grade.startswith("A") else ("A" if grade.startswith("B") else grade)
        elif grade.startswith("B"):                    # a single '+' nudges open-space up
            grade = "A"
    if smc_zone:                                       # surface the range position for the AI judge regardless of score
        htf_note += f" | SMC {smc_zone}{' ✓aligned' if smc_aligned else (' ✗misaligned' if smc_aligned is False else '')}"

    # --- #1 adaptive TP/SL: cap targets just short of the next structure; skip cramped trades ---
    # Zone-rejection stops sit BEYOND the rejection zone's far edge (+buffer) with a WIDER cap, so ordinary
    # movement *inside* the zone can't tag a VS-tight stop placed within it. (06-05 fix: the gold -21p loss
    # stopped at 4467 because the VS-capped stop sat inside the 4465-4477 resistance band instead of above it.)
    z_buf = 3 * VS                                          # buffer beyond the zone far edge (pips)
    if side == "LONG":
        zr = bool(at_S) and at_S[1] > at_S[0] and at_S[0] <= entry      # bouncing a real support band underfoot
        z_struct = min(struct, at_S[0] - z_buf*PIP) if zr else struct   # anchor below the band's LOW
        sl_hi_eff = (50*VS) if zr else sl_hi_p                          # wider ceiling so the stop clears the zone
        sl_lvl = round(max(min(z_struct, entry - sl_lo_p*PIP), entry - sl_hi_eff*PIP), PXD); wall = nextR
    else:
        zr = bool(at_R) and at_R[1] > at_R[0] and at_R[1] >= entry      # rejecting a real resistance band overhead
        z_struct = max(struct, at_R[1] + z_buf*PIP) if zr else struct   # anchor above the band's HIGH
        sl_hi_eff = (50*VS) if zr else sl_hi_p
        sl_lvl = round(min(max(z_struct, entry + sl_lo_p*PIP), entry + sl_hi_eff*PIP), PXD); wall = nextS
    if FL.get("adaptive_tp", True) and wall is not None:
        room = abs(wall - entry)/PIP - tp_buf
        if room < room_min and not AI:
            print(f"\n>> SKIP CRAMPED: {side} {grade} — only {room:.0f}p clean room to next structure {wall} (<{room_min:.0f}p R:R too poor)."); gate_trace("cramped"); return
        if room < room_min:   # AI mode: surface but flag the tight room
            print(f"   ⚠ CRAMPED: only {room:.0f}p clean room to next structure {wall} — poor R:R, judge carefully.")
        tp2_p = max(tp2_cap*0.2, min(tp2_cap, room)); tp1_p = min(tp1_cap, tp2_p*0.6)
    else:
        tp2_p, tp1_p = tp2_cap, tp1_cap
    if side == "LONG":
        tp1 = round(entry + tp1_p*PIP, PXD); tp2 = round(entry + tp2_p*PIP, PXD)
    else:
        tp1 = round(entry - tp1_p*PIP, PXD); tp2 = round(entry - tp2_p*PIP, PXD)
    risk = abs(entry - sl_lvl) / PIP
    # --- confidence: aggregate EVERY confluence axis into a 0-10 score that survives the A+ ceiling, so a
    # 5-factor monster reads stronger than a bare A+. Drives size ONLY when `confidence_sizing` is on. ---
    conf_now = conf_S if side == "LONG" else conf_R
    _wt = (side == "LONG" and regime == "UP") or (side == "SHORT" and regime == "DOWN")
    _ct = (side == "LONG" and regime == "DOWN") or (side == "SHORT" and regime == "UP")
    _trend = True if _wt else (False if _ct else None)
    _rsidiv = bool(rsi is not None and rsi_divergence(b, side))
    # level-validity + penalty context (Confluence Score Guide deductions, docs/signal-roadmap-detailed.md)
    _lvl_valid = False; _accepted = False; _mid_value = False
    if vastate is not None and prior_vas:
        _pv0 = prior_vas[0]; _vah0, _val0 = _pv0.get("vah"), _pv0.get("val")
        for _k, _lv in (("VAH", _vah0), ("VAL", _val0), ("POC", _pv0.get("poc"))):
            if _lv is None or abs(_lv - entry) > dyn_tolp:
                continue
            _st = vastate.level_state(_lv, b, _k, poc=_pv0.get("poc"), bar_minutes=BASE_TF)["state"]
            if _st in ("Rejected", "Flipped"): _lvl_valid = True
            elif _st == "Accepted": _accepted = True
        # mid-value: strictly inside prior value AND not at either edge (the chop the guide penalises)
        if _vah0 and _val0 and _val0 < entry < _vah0 and abs(entry - _vah0) > dyn_tolp and abs(entry - _val0) > dyn_tolp:
            _mid_value = True
    _opp = nextR if side == "LONG" else nextS                        # opposing structure before TP1?
    _into_opposing = _opp is not None and (abs(_opp - entry) / PIP) < tp1_p
    conf_score = confmod.score(grade, conf=conf_now, smc_tl=cf_score, rsi_div=_rsidiv, with_trend=_trend,
                               rr=(tp1_p / risk if risk > 0 else None), level_valid=_lvl_valid,
                               mid_value=_mid_value, accepted_through=_accepted,
                               into_opposing=_into_opposing, vwap_chop=bool(is_chop),
                               smc_aligned=smc_aligned) if confmod else None
    conf_lbl = confmod.label(conf_score) if confmod and conf_score is not None else ""
    # position sizing from fixed $ risk: lot = RISK_USD / ($/pip/lot × stop_pips), rounded to broker step + clamped
    risk_usd = RISK_USD
    if FL.get("confidence_sizing", False) and confmod and conf_score is not None:
        risk_usd = round(RISK_USD * confmod.size_multiplier(conf_score, lo=CONF_SIZE_LO, hi=CONF_SIZE_HI), 2)
    _raw = risk_usd / (PIP_VALUE * risk) if (risk > 0 and PIP_VALUE > 0) else LOT_MIN
    lot = round(round(_raw / LOT_STEP) * LOT_STEP, 4)
    lot = max(LOT_MIN, min(LOT_MAX, lot))
    # --- pre-hold HARD FLOOR: drop structurally un-tradeable signals (negative R:R / no room — the chop-spam
    # that gets hand-rejected every tick) BEFORE they reach the held/review state. Uses the ACTUAL R:R (TP1
    # vs stop), so it's direction-agnostic. One of the discipline gates that apply EVEN under ai_decide (with
    # observation_gate + family_caps); ai_decide only bypasses the SOFT quality filters. Conservative: a
    # genuine positive-R:R setup never trips it. ---
    if FL.get("hard_floor", True):
        _wall = nextR if side == "LONG" else nextS
        _room = round(abs(_wall - entry)/PIP) if _wall is not None else None
        _rr1  = (tp1_p / risk) if risk > 0 else None
        _skip, _flags = hard_floor_skip(side, regime, rsi, _rr1, _room, chop_er, VS)
        if _skip:
            print(f"\n>> AUTO-SKIP (pre-hold floor): {side} {grade} [{why}] — {', '.join(_flags)}. "
                  f"Not surfaced for review (un-tradeable).")
            # MEASUREMENT (no behavior change — still skipping): record zone-rejections killed by dead chop,
            # split by with-/counter-trend, to validate the proposed chop-exemption before shipping it.
            _zr = zrskip_record(why, _flags, side, regime, chop_er, _rr1, entry, sl_lvl, tp1)
            if _zr:
                _zr.update({"grade": grade, "t": ts, "sym": SYMBOL})
                print(f">> ZRSKIP {json.dumps(_zr)}")               # backtest (replay_sim) scrapes this
                if not DRY:
                    try:
                        with open(os.path.expanduser("~/tradingview-mcp/logs/zrskip.jsonl"), "a") as _zf:
                            _zf.write(json.dumps(_zr) + "\n")        # live accumulation (separate file, no CSV schema change)
                    except Exception: pass
            if not DRY:
                _htf = at_S if side == "LONG" else at_R
                log_floor_skip(side, why, entry, grade, rng10, body_pips, _htf[2] if _htf else "open", _rr1, _flags)
            gate_trace("hard_floor_" + ("chop" if any("dead chop" in f for f in _flags) else "rr" if any("neg R:R" in f for f in _flags) else "other")); return
    # #3 RSI-reset gate (OFF by default): skip a reversal taken at a wrong-way RSI extreme (selling the
    # bottom / buying the top) even with room — wait for the reset. Logged as auto-skip so it's measurable.
    if FL.get("rsi_reset_gate", False) and reversal_rsi_extreme(side, why, rsi):
        _rr1 = (tp1_p / risk) if risk > 0 else None
        _dir = "sell into oversold" if side == "SHORT" else "buy into overbought"
        _reason = f"RSI{rsi:.0f} reversal extreme ({_dir}) — wait for reset"
        print(f"\n>> AUTO-SKIP (rsi-reset gate): {side} {grade} [{why}] — {_reason}.")
        if not DRY:
            _htf = at_S if side == "LONG" else at_R
            log_floor_skip(side, why, entry, grade, rng10, body_pips, _htf[2] if _htf else "open", _rr1, [_reason])
        gate_trace("rsi_reset"); return
    # daily family cap: stop a noisy family from overproducing alerts/reviews. Applies even under ai_decide;
    # set family_caps=false for an explicit research override.
    if FL.get("family_caps", True):
        _fam = flag_for(why); _cap = FAMILY_CAPS.get(_fam)
        if _cap is not None:
            _n = family_fired_today(SYMBOL).get(_fam, 0)
            if _n >= _cap:
                print(f">> SKIP DAILY CAP: {side} [{why}] — {_fam} already fired {_n}/{_cap} today.")
                if not DRY:
                    _htf = at_S if side == "LONG" else at_R
                    log_floor_skip(side, why, entry, grade, rng10, body_pips, _htf[2] if _htf else "open", None, [f"daily cap {_n}/{_cap}"])
                gate_trace("family_cap"); return
    _cf = f"  confidence {conf_score}/10 ({conf_lbl})" if conf_score is not None else ""
    gate_trace("fast_signal")
    print(f"\n>> FAST SIGNAL: {side} [{grade}]{_cf} [{why}]{htf_note}")
    print(f"   SMC: zone={smc_zone} aligned={smc_aligned} age={smc_age}")   # machine-parseable (replay_sim scrapes this for the SMC bucket report)
    _szt = f" [conf-sized {risk_usd/RISK_USD:.2f}×]" if (FL.get('confidence_sizing', False) and risk_usd != RISK_USD) else ""
    print(f"   Entry {entry} | SL {sl_lvl} ({risk:.0f}p · {lot} lot ≈ ${risk_usd:.0f}{_szt}) | TP1 {tp1} (+{tp1_p:.0f}p) | TP2 {tp2} (+{tp2_p:.0f}p)")
    print(f"   RULE: exit if TP1 not hit within ~10 min (speed thesis failed).")
    arrow = "🟢⬆️" if side == "LONG" else "🔴⬇️"
    hz = at_R or at_S   # the actual extended level that drove the grade (incl. VWAP/round#/PDH/Asian)
    conf = conf_S if side == "LONG" else conf_R
    room_p = round(abs(wall - entry)/PIP) if wall else None
    bias = ("with-trend" if (side == "LONG" and regime == "UP") or (side == "SHORT" and regime == "DOWN")
            else "COUNTER-trend" if regime in ("UP", "DOWN") else "no clear trend")
    _cfline = f"\n• Confidence: {conf_score}/10 ({conf_lbl})" if conf_score is not None else ""
    ctx = (f"📊 {why} @ {hz[2] if hz else 'open space'}\n"
           f"• Trend: 30m {regime} ({bias})\n"
           f"• RSI {rsi:.0f} · 15m ER {chop_er}{' ⚠CHOP' if is_chop else ' (trending)'} · {conf}× confluence{_cfline}\n"
           f"• Room to next structure: {str(room_p)+'p' if room_p is not None else 'open'}"
           f"{' ⚠tight' if room_p is not None and room_p < room_min else ''}")
    msg = (f"{arrow} {SYMBOL} — CONFIRMED {side} [{grade}]\n\n"
           f"{ctx}\n\n"
           f"Entry: {entry}\n"
           f"SL: {sl_lvl} ({risk:.0f}p)\n"
           f"Lot: {lot}  (risk ≈ ${risk_usd:.0f}{_szt})\n"
           f"TP1: {tp1} (+{tp1_p:.0f}p)\n"
           f"TP2: {tp2} (+{tp2_p:.0f}p)\n\n"
           f"Rule: exit if TP1 not hit in ~10 min.")
    trade = {"side": side, "entry": entry, "sl": sl_lvl, "tp1": tp1, "tp2": tp2, "tp1_p": tp1_p, "tp2_p": tp2_p,
             "be_trig": be_trig, "lot": lot, "risk_usd": risk_usd,
             "grade": grade, "why": why, "htf_note": htf_note, "msg": msg, "rng10": round(rng10),
             "body_p": round(body_pips), "htf": hz[2] if hz else "open", "regime": regime, "rsi": rsi,
             "chop_er": chop_er, "conf": conf, "confidence": conf_score, "conf_lbl": conf_lbl, "room": room_p, "bias": bias,
             "smc_zone": smc_zone, "smc_aligned": smc_aligned, "smc_age": smc_age}
    if DRY:
        print("   [DRY RUN — no telegram/log/state]"); return
    if REVIEW:   # AI-review gate: hold the trade, don't send. (approve: --approve  ·  reject: --reject)
        try: json.dump({**trade, "t": time.time()}, open(PENDING_FILE, "w"))
        except Exception: pass
        if conf_score is not None:
            # explicit steer for the AI judge: confidence aggregates every confluence axis past the A+ ceiling
            print(f"   >> AI: confidence {conf_score}/10 ({conf_lbl}). ≥7 = strong conviction — lean APPROVE if the "
                  f"checklist holds. ≤3 = weak — only approve with a clear, specific reason; otherwise reject.")
        # AI approval checklist (from docs/signal-roadmap.md) — APPROVE only if ALL hold; else REJECT/WAIT:
        print("   >> AI APPROVAL CHECKLIST (all must hold):\n"
              "      1) at a real level (VAH/VAL/POC/VWAP/bands/PDH-PDL/session H-L/SMC zone) — not open space\n"
              "      2) structure aligned or shifted (BOS/CHoCH/HH-HL/LL-LH) in the trade direction\n"
              "      3) R:R ≥ 1:2 with a logical, not-too-wide stop\n"
              "      4) NOT mid-value / chopping around VWAP\n"
              "      5) no strong opposing level right before TP1\n"
              "      6) London/NY session (avoid Asian/NY-lunch unless clean breakout acceptance)\n"
              "      7) level is FRESH — not Accepted-through / over-tested (check prevVA Level State)\n"
              "      WAIT if a cleaner entry (retest/sweep-reclaim) is one candle away.")
        print("   >> AI DECISION: reply APPROVE / REJECT / WAIT + a one-line reason citing the checklist + "
              "confidence (WAIT = don't force it; let the pending expire if a cleaner entry is forming).")
        print("   ⏸ HELD FOR REVIEW — not sent to Telegram yet.")
        return
    _fire(trade)

def _fire(t, note="", source="auto"):
    """Send a confirmed trade to Telegram + log it + start TP/SL tracking + cooldown.
    `note` = Claude's one-line review reasoning, appended so the user sees WHY it was approved.
    `source` = decision_source for the log: 'AI' (review-approved) or 'auto' (autonomous fire)."""
    alert_sound(3)
    # Telegram photo caption hard-limits at 1024 chars; cap the review note so the send never fails.
    if note:
        budget = 1000 - len(t["msg"]) - len("\n\n🤖 Review: ")
        if budget < len(note):
            note = (note[:max(0, budget - 1)].rstrip() + "…") if budget > 1 else ""
    msg = t["msg"] + (f"\n\n🤖 Review: {note}" if note else "")
    notify_telegram(msg, f"signal|{t['side']}|{round(t['entry'])}|{t['why']}")
    sid = int(time.time())
    log_signal({"id": sid, "time": _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
                "side": t["side"], "grade": t["grade"], "confidence": t.get("confidence", ""), "pattern": t["why"],
                "entry": t["entry"], "sl": t["sl"], "tp1": t["tp1"], "rng10": t.get("rng10", ""),
                "body_p": t.get("body_p", ""), "htf": t.get("htf", "open"), "result": "PENDING", "exit": "", "pips": "",
                "smc_zone": t.get("smc_zone", ""), "smc_aligned": t.get("smc_aligned", ""), "smc_age": t.get("smc_age", ""),
                "decision_source": source, "decision_reason_code": f"{flag_for(t['why']) or t['why']}:{t.get('grade','')}:conf{t.get('confidence','')}"})
    set_active_trade(t["side"], t["entry"], t["sl"], t["tp1"], t["tp2"], sid, t.get("be_trig", BE_TRIGGER_P))
    try: json.dump({"t": time.time()}, open(CD_FILE, "w"))   # start cooldown
    except Exception: pass

def _read_pending():
    try: return json.load(open(PENDING_FILE))
    except Exception: return None

if __name__ == "__main__":
    # --symbol SYM picks the instrument (config + window + state/zones/logs); default XAUUSD = unchanged.
    if "--symbol" in sys.argv:
        try: init_symbol(sys.argv[sys.argv.index("--symbol")+1])
        except Exception: init_symbol("XAUUSD")
    else:
        init_symbol("XAUUSD")
    if "--approve" in sys.argv:   # send the held trade + start tracking. Optional note = Claude's reasoning.
        t = _read_pending()
        if t:
            note = " ".join(a for a in sys.argv[sys.argv.index("--approve")+1:] if not a.startswith("--"))
            _fire(t, note, source="AI")
            try: os.remove(PENDING_FILE)
            except Exception: pass
            print(f"✅ APPROVED & SENT: {t['side']} {t['grade']} @ {t['entry']}  (note: {note or '—'})")
        else: print("no pending trade to approve")
        sys.exit()
    if "--reject" in sys.argv:    # log the rejection (feeds the learn dataset), don't send
        t = _read_pending()
        if t:
            reason = next((a for a in sys.argv[sys.argv.index("--reject")+1:] if not a.startswith("--")), "")
            log_signal({"id": int(time.time()), "time": _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
                        "side": t["side"], "grade": t["grade"], "confidence": t.get("confidence", ""), "pattern": t["why"],
                        "entry": t["entry"], "sl": t["sl"], "tp1": t["tp1"], "rng10": t.get("rng10",""),
                        "body_p": t.get("body_p",""), "htf": t.get("htf","open"), "result": "rejected", "exit": "", "pips": reason,
                        "smc_zone": t.get("smc_zone", ""), "smc_aligned": t.get("smc_aligned", ""), "smc_age": t.get("smc_age", ""),
                        "decision_source": "AI", "decision_reason_code": (reason or "rejected")[:40]})
            try: os.remove(PENDING_FILE)
            except Exception: pass
            print(f"🚫 REJECTED & LOGGED: {t['side']} {t['grade']} @ {t['entry']}  ({reason})")
        else: print("no pending trade to reject")
        sys.exit()
    # single-instance lock (per-symbol: gold & GBPUSD scanners run concurrently, each locks only its own symbol)
    LOCK = os.path.expanduser(f"~/.tv_fast_{SYMBOL.lower()}.lock")
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
