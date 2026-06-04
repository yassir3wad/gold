#!/usr/bin/env python3
"""Forex Factory economic-calendar integration (the FairEconomy weekly JSON feed FF itself uses).
  python3 news.py brief        -> fetch the week, cache it, print + Telegram today's High/Medium events
  python3 news.py blackout SYM -> print 'BLACKOUT <event>' (exit 0) if now is within +/-BLACKOUT_MIN of a
                                  HIGH-impact event affecting SYM's currency, else 'clear' (exit 1).
                                  The scanner calls this to suppress new entries around red-folder news.
  python3 news.py result       -> for HIGH events that just released (last ~10m), print + Telegram the
                                  actual-vs-forecast surprise + the directional bias for affected pairs.
Caches news_week.json. Dates parsed to UTC. (Note: filters by *today UTC* — in a clock-shifted test env the
feed's real-world dates won't match, so 'today' may be empty; the logic is correct for live use.)"""
import json, os, sys, urllib.request, datetime as dt

TVDIR = os.path.expanduser("~/tradingview-mcp")
FEED = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE = os.path.join(TVDIR, "news_week.json")
BLACKOUT_MIN = 15           # +/- minutes around a High-impact event = no new entries
# currency -> symbols it moves (USD news moves everything; gold/indices are USD-sensitive)
AFFECTS = {"USD": ["XAUUSD", "NAS100", "US30", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
           "EUR": ["EURUSD"], "GBP": ["GBPUSD"], "JPY": ["USDJPY"], "AUD": ["AUDUSD"],
           "CNY": ["AUDUSD"], "CAD": [], "CHF": [], "NZD": []}

def _tg(msg):
    try:
        c = json.load(open(os.path.join(TVDIR, "telegram_config.json")))
        tok = c.get("bot_token") or c.get("token"); chat = str(c.get("chat_id"))
        import urllib.parse
        d = urllib.parse.urlencode({"chat_id": chat, "text": msg}).encode()
        urllib.request.urlopen("https://api.telegram.org/bot"+tok+"/sendMessage", data=d, timeout=20)
    except Exception as e: print("tg err:", e)

def _local(d):   # UTC-aware datetime -> the Mac's local timezone (what the user sees)
    return d.astimezone() if d else d
def _loclabel():
    h = dt.datetime.now().astimezone().utcoffset().total_seconds()/3600
    return f"UTC{h:+.0f}" if h == int(h) else f"UTC{h:+.1f}"

def _parse_dt(s):
    try: return dt.datetime.fromisoformat(s).astimezone(dt.timezone.utc)
    except Exception:
        try: return dt.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)
        except Exception: return None

def fetch():
    try:
        req = urllib.request.Request(FEED, headers={"User-Agent": "Mozilla/5.0"})
        raw = json.load(urllib.request.urlopen(req, timeout=25))
    except Exception as e:   # rate-limited / offline -> fall back to last good cache (don't crash the loop)
        print("feed fetch failed (" + str(e) + "), using cache")
        return _cached()
    ev = []
    for x in raw:
        d = _parse_dt(x.get("date", ""))
        ev.append({"t": d.isoformat() if d else None, "cur": x.get("country"), "impact": x.get("impact"),
                   "title": x.get("title"), "forecast": x.get("forecast"), "previous": x.get("previous"),
                   "actual": x.get("actual")})
    json.dump({"fetched": dt.datetime.utcnow().isoformat(), "events": ev}, open(CACHE, "w"))
    return ev

def _cached():
    try: return json.load(open(CACHE)).get("events", [])
    except Exception: return []

def _load():
    ev = _cached()
    return ev if ev else fetch()

def _today_hi_med(ev):
    today = dt.datetime.now().astimezone().date()   # the user's LOCAL today
    out = []
    for e in ev:
        d = _parse_dt(e["t"]) if e.get("t") else None
        if d and _local(d).date() == today and e.get("impact") in ("High", "Medium"):
            out.append((d, e))
    return sorted(out, key=lambda x: x[0])

def brief():
    ev = fetch()
    rows = _today_hi_med(ev)
    if not rows:
        print("No High/Medium events today."); return
    lines = [f"📰 Today's news ({_loclabel()}):"]
    for d, e in rows:
        imp = "🔴" if e["impact"] == "High" else "🟠"
        lines.append(f"{imp} {_local(d):%H:%M} {e['cur']} — {e['title']}  (F:{e.get('forecast') or '–'} P:{e.get('previous') or '–'})")
    msg = "\n".join(lines)
    print(msg); _tg(msg)

def is_blackout(sym, mins=BLACKOUT_MIN):
    """(True, label) if now is within +/-mins of a HIGH-impact event affecting sym's currency. Reads cache only
    (no fetch) — safe to call from the scanner hot path."""
    now = dt.datetime.now(dt.timezone.utc)
    for e in _cached():
        if e.get("impact") != "High": continue
        if sym not in AFFECTS.get(e.get("cur"), []): continue
        d = _parse_dt(e["t"]) if e.get("t") else None
        if d and abs((now - d).total_seconds()) <= mins*60:
            return True, f"{e['cur']} {e['title']} @ {_local(d):%H:%M} {_loclabel()}"
    return False, ""

def blackout(sym):
    bo, lbl = is_blackout(sym)
    if bo: print("BLACKOUT " + lbl); sys.exit(0)
    print("clear"); sys.exit(1)

def result():
    now = dt.datetime.now(dt.timezone.utc); ev = fetch()   # refetch to pull 'actual'
    for e in ev:
        if e.get("impact") != "High" or not e.get("actual"): continue
        d = _parse_dt(e["t"]) if e.get("t") else None
        if not d or not (0 <= (now - d).total_seconds() <= 600): continue   # released in last 10 min
        a, f = e.get("actual"), e.get("forecast")
        bias = ""
        try:
            an = float(str(a).replace("%", "").replace("K", "").replace("B", "").replace(",", ""))
            fn = float(str(f).replace("%", "").replace("K", "").replace("B", "").replace(",", ""))
            strong = an > fn
            bias = f" → {e['cur']} {'stronger' if strong else 'weaker'} than forecast"
        except Exception: pass
        syms = ", ".join(AFFECTS.get(e.get("cur"), []))
        msg = f"🗞️ {e['cur']} {e['title']}: actual {a} vs forecast {f}{bias}\nAffects: {syms}"
        print(msg); _tg(msg)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "brief"
    if cmd == "brief": brief()
    elif cmd == "blackout": blackout(sys.argv[2].upper() if len(sys.argv) > 2 else "XAUUSD")
    elif cmd == "result": result()
    else: print("usage: news.py brief|blackout SYM|result")
