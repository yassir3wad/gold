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
HTF_R = [(4445,4450,"R 4447 (broken lvl/15m EMA50)"), (4460,4468,"R 4462-68 (1H+15m)"),
         (4473,4478,"R 4475 (1H EMA50/15m EMA200)"), (4495,4503,"KEY R 4500 (4H EMA50/1H EMA200/fib OTE)"),
         (4538,4545,"R 4541 (1H/4H lower high)")]
HTF_S = [(4424,4434,"S 4426-34 (1H+15m multi-touch)"), (4398,4406,"Support 4400 (4H+1H)"),
         (4351,4368,"BUY ZONE Daily EMA200")]
def near_htf(price, levels, tol=4):
    for lo, hi, lab in levels:
        if lo - tol <= price <= hi + tol: return (lo, hi, lab)
    return None

# --- v2 gold-specific reference levels (refresh ~daily) ---
PDH, PDL = 4496.7, 4426.4          # prior-day high / low
ASIA_H, ASIA_L = 4496.7, 4455.2    # Asian-session range
SESSION_UTC = set(range(7, 22))    # London+NY active hours (UTC); outside = quiet
NEWS_BLACKOUT = []                 # [(h1,m1,h2,m2),...] UTC windows to mute (manual)
CD_FILE = os.path.expanduser("~/.tv_fast_cd.json")
COOLDOWN_MIN = 8                   # no new signal for N minutes after one fires (anti-clustering)

def vwap(bars):
    num = sum(((x['high']+x['low']+x['close'])/3) * x.get('volume', 0) for x in bars)
    den = sum(x.get('volume', 0) for x in bars)
    return round(num/den, 2) if den else None

def in_session(ts):
    return _dt.datetime.utcfromtimestamp(ts).hour in SESSION_UTC

def in_news(ts):
    t = _dt.datetime.utcfromtimestamp(ts); m = t.hour*60 + t.minute
    return any(h1*60+m1 <= m <= h2*60+m2 for h1,m1,h2,m2 in NEWS_BLACKOUT)

# --- feature flags (toggle strategies/filters in flags.json, no code edits) ---
FLAGS_FILE = os.path.expanduser("~/tradingview-mcp/flags.json")
DEFAULT_FLAGS = {"trendline_break": True, "range_breakout": True, "double_top_bottom": True,
                 "momentum_impulse": True, "liquidity_sweep": True, "break_retest": True, "vwap": True,
                 "session_breakout": True, "extended_levels": True, "session_filter": True,
                 "news_filter": True, "volume_filter": True}
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
            oe = old["entry"]; pips = round((oe-entry)/PIP if old["side"] == "SHORT" else (entry-oe)/PIP)
            log_signal({"id": old["id"], "result": "superseded", "exit": round(entry, 1), "pips": pips})
    except Exception: pass
    try: json.dump({"active": True, "id": sid, "side": side, "entry": entry, "sl": sl,
                    "tp1": tp1, "tp2": tp2, "tp1_hit": False, "t0": time.time()}, open(TRADE_STATE, "w"))
    except Exception: pass

def check_active_trade(price):
    """Alert on TP1/TP2/SL; finalize the signals_log outcome (incl. 12-min timeout)."""
    try: t = json.load(open(TRADE_STATE))
    except Exception: return
    if not t.get("active"): return
    side, e, sl, tp1, tp2 = t["side"], t["entry"], t["sl"], t["tp1"], t["tp2"]
    sid = t.get("id"); PP = lambda x: round((e - x)/PIP if side == "SHORT" else (x - e)/PIP)
    label = None
    if side == "SHORT":
        if price >= sl: label, lvl, res = "❌ SL", sl, "SL"; t["active"] = False
        elif price <= tp2: label, lvl, res = "🎯 TP2 (+100p)", tp2, "TP2"; t["active"] = False
        elif price <= tp1 and not t.get("tp1_hit"): label, lvl, res = "✅ TP1 (+50p)", tp1, "TP1"; t["tp1_hit"] = True
    else:
        if price <= sl: label, lvl, res = "❌ SL", sl, "SL"; t["active"] = False
        elif price >= tp2: label, lvl, res = "🎯 TP2 (+100p)", tp2, "TP2"; t["active"] = False
        elif price >= tp1 and not t.get("tp1_hit"): label, lvl, res = "✅ TP1 (+50p)", tp1, "TP1"; t["tp1_hit"] = True
    if label:
        extra = "  → take partial, SL to breakeven." if "TP1" in label else "  → trade closed."
        _tg_text(f"{label} — GOLD {side} hit {lvl} (entry {e}, now {price}).{extra}")
        if sid: log_signal({"id": sid, "result": res, "exit": round(lvl, 1), "pips": PP(lvl)})
    elif time.time() - t.get("t0", time.time()) > 720:   # 12-min timeout
        res = "TP1" if t.get("tp1_hit") else "timeout"
        t["active"] = False
        if sid: log_signal({"id": sid, "result": res, "exit": round(price, 1), "pips": PP(price)})
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

    # --- v2: VWAP, round#, volume, session ---
    vw = vwap(b)
    r10 = round(price/10)*10; near_round = r10 if abs(r10-price) < 2 else None
    vol = last.get('volume', 0); avgvol = sum(x.get('volume', 0) for x in b[-20:])/20
    vol_ok = (vol > avgvol) if avgvol else True
    ts = last['time']; sess_ok = in_session(ts); news = in_news(ts)
    # extended level map: HTF zones + dynamic (VWAP / round# / prior-day H-L / Asian H-L) for grading
    dynR, dynS = list(HTF_R), list(HTF_S)
    if FL["extended_levels"]:
        for lvl, lab in [(PDH,"prior-day high"), (PDL,"prior-day low"), (ASIA_H,"Asian high"),
                         (ASIA_L,"Asian low"), (vw,"VWAP"), (near_round,f"round {near_round}")]:
            if lvl is None: continue
            (dynR if lvl >= price else dynS).append((lvl-2, lvl+2, lab))
    at_R = near_htf(price, dynR); at_S = near_htf(price, dynS)
    print(f"PRICE {price}  TF=1m  range10={rng10:.0f}p  atr={atr:.1f}p  lastBody={body_pips:.0f}p({'bull' if bull else 'bear'}) strong={strong} vol_ok={vol_ok}")
    print(f"resTL@{res_at}  supTL@{sup_at}  range15={range15:.0f}p tight={tight}  dblTop={dtop} dblBot={dbot}  VWAP={vw}  session={'ON' if sess_ok else 'off'}")
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
        if strong and not bull and last['high'] > sw_hi and last['close'] < sw_hi:
            setups.append(("SHORT", "liquidity-sweep reversal", last['close'], last['high']))
        if strong and bull and last['low'] < sw_lo and last['close'] > sw_lo:
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
    # 8) Asian-range / prior-day breakout
    for lv, lab in [(ASIA_H, "Asian-range"), (PDH, "prior-day-high")]:
        if strong and bull and last['open'] <= lv and last['close'] > lv:
            setups.append(("LONG", f"{lab} breakout", last['close'], lo15))
    for lv, lab in [(ASIA_L, "Asian-range"), (PDL, "prior-day-low")]:
        if strong and not bull and last['open'] >= lv and last['close'] < lv:
            setups.append(("SHORT", f"{lab} breakdown", last['close'], hi15))
    # volume filter: breakouts/breaks need above-avg volume; reversals (sweep/retest/VWAP) exempt
    if FL["volume_filter"] and not vol_ok:
        setups = [s for s in setups if any(w in s[1] for w in ("sweep", "retest", "VWAP"))]
    # feature-flag filter: drop any setup whose strategy is toggled off
    setups = [s for s in setups if FL.get(flag_for(s[1]) or "", True)]

    if not setups:
        htf = at_R or at_S
        if htf:
            print(f"\n>> HTF WATCH: price at {htf[2]} — good-trade location; a momentum trigger here = A+. Waiting.")
            sidehint = "SHORT" if at_R else "LONG"
            wmsg = (f"👀 GOLD — SETUP FORMING\nPrice at {htf[2]} (~{price}). Possible {sidehint}.\n"
                    f"Get ready — I'll send the CONFIRMED entry (with SL/TP) when a {sidehint.lower()} trigger fires.")
            if not DRY: notify_telegram(wmsg, f"watch|{htf[2]}")
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
    if FL["session_filter"] and not sess_ok and not grade.startswith("A+"):
        print(f"\n>> OFF-SESSION ({side} {grade}) — skipped (only A+ trades outside London/NY)."); return
    if vol_ok and "open space" in grade: grade = "B+vol"   # volume gives a low-grade setup a small boost
    if side == "LONG":
        sl_lvl = round(min(struct, entry - 30*PIP), 2)   # structure or 30p, whichever is further (cap risk sense below)
        sl_lvl = round(max(sl_lvl, entry - 35*PIP), 2)    # but never risk > 35p
        tp1 = round(entry + 50*PIP, 2); tp2 = round(entry + 100*PIP, 2)
    else:
        sl_lvl = round(max(struct, entry + 30*PIP), 2)
        sl_lvl = round(min(sl_lvl, entry + 35*PIP), 2)
        tp1 = round(entry - 50*PIP, 2); tp2 = round(entry - 100*PIP, 2)
    risk = abs(entry - sl_lvl) / PIP
    print(f"\n>> FAST SIGNAL: {side} [{grade}] [{why}]{htf_note}")
    print(f"   Entry {entry} | SL {sl_lvl} ({risk:.0f}p) | TP1 {tp1} (+50p) | TP2 {tp2} (+100p)")
    print(f"   RULE: exit if TP1 not hit within ~10 min (speed thesis failed).")
    if DRY:
        print("   [DRY RUN — no telegram/log/state]"); return
    alert_sound(3)   # audible alert
    msg = (f"🚨 GOLD — CONFIRMED {side} [{grade}]\n{why}{htf_note}\n\n"
           f"Entry: {entry}\n"
           f"SL: {sl_lvl} ({risk:.0f}p)\n"
           f"TP1: {tp1} (+50p)\n"
           f"TP2: {tp2} (+100p)\n\n"
           f"Rule: exit if TP1 not hit in ~10 min.")
    notify_telegram(msg, f"signal|{side}|{round(entry)}|{why}")
    sid = int(time.time())
    hz = near_htf(entry, HTF_R) or near_htf(entry, HTF_S)
    log_signal({"id": sid, "time": _dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "side": side, "grade": grade, "pattern": why, "entry": entry, "sl": sl_lvl, "tp1": tp1,
                "rng10": round(rng10), "body_p": round(body_pips), "htf": hz[2] if hz else "open",
                "result": "PENDING", "exit": "", "pips": ""})
    set_active_trade(side, entry, sl_lvl, tp1, tp2, sid)   # track for TP/SL + outcome logging
    try: json.dump({"t": time.time()}, open(CD_FILE, "w"))   # start cooldown
    except Exception: pass

if __name__ == "__main__":
    main()
