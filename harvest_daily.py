#!/usr/bin/env python3
"""Daily prior-day value-area harvest for the live engine. Self-dating + idempotent + safe to schedule:

- Determines the most-recent CLOSED gold session (weekday whose ~22:00 UTC TPO close has passed).
- If the va_store already has a COMPLETE row for it, does nothing (so it's safe to run repeatedly).
- Otherwise replays the chart to that date, reads POC/VAH/VAL + single-print zones off the TPO indicator,
  stores them, and RESTORES realtime (replay stop) before exiting.

Schedule it for the daily 22:00 UTC session-close rollover (an illiquid window when the live engine isn't
trading), so the brief replay never collides with a live setup. The script uses UTC internally, so the cron
time only needs to land safely AFTER 22:00 UTC — timezone/DST shifts don't break the date math.

    python3 harvest_daily.py            # harvest the most-recent closed session
    python3 harvest_daily.py 2026-06-04 # harvest a specific date (force)
"""
import sys, os, subprocess, datetime as dt
import tpo, va_store as vs

SYMBOL = "XAUUSD"
CLOSE_HOUR = 22   # daily TPO session close, UTC (see tpo.SESSION_CLOSE_HOUR)
# Replay runs ONLY on the dedicated backtest tab (last XAUUSD window), never the live chart. Override with
# TV_BACKTEST_CHART if the window id changes.
BACKTEST_CHART = os.environ.get("TV_BACKTEST_CHART", "eabXWKAd")
SCANNER_PLIST = os.path.expanduser("~/Library/LaunchAgents/com.yassir.goldscalper.plist")


def _scanner_loaded():
    r = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    return "com.yassir.goldscalper" in (r.stdout or "")


class _pause_scanner:
    """If the every-60s live scanner LaunchAgent is RUNNING, stop it for the duration of a harvest so its
    tick can't yank the chart out of replay mid-read, then resume it. Resumes only what was actually loaded
    (never spuriously starts a scanner that was intentionally off). Always resumes, even on error."""
    def __enter__(self):
        self.was_loaded = _scanner_loaded() and os.path.exists(SCANNER_PLIST)
        if self.was_loaded:
            subprocess.run(["launchctl", "unload", SCANNER_PLIST], capture_output=True)
        return self
    def __exit__(self, *exc):
        if self.was_loaded:
            subprocess.run(["launchctl", "load", SCANNER_PLIST], capture_output=True)
        return False


def most_recent_closed_session(now=None):
    """The latest weekday date whose 22:00 UTC session close has already passed."""
    now = now or dt.datetime.utcnow()
    d = now.date()
    # if today's session hasn't closed yet (before 22:00 UTC), step back to yesterday
    if now.hour < CLOSE_HOUR:
        d -= dt.timedelta(days=1)
    while d.weekday() >= 5:   # skip Sat/Sun back to Friday
        d -= dt.timedelta(days=1)
    return d.isoformat()


def harvest(date, force=False):
    if not force and vs._complete(vs.get(SYMBOL, date)):
        print(f"{date}  already complete — skip", flush=True)
        return True
    with _pause_scanner():
        try:
            va = tpo.fetch_va(SYMBOL, date, chart=BACKTEST_CHART)
        finally:
            tpo._default_tv(BACKTEST_CHART, "replay", "stop")   # restore realtime on the backtest tab
    if va and va.get("poc") and va.get("vah") and va.get("val"):
        vs.put(SYMBOL, date, va["poc"], va["vah"], va["val"], sp=va.get("sp"))
        print(f"{date}  POC={va['poc']} VAH={va['vah']} VAL={va['val']} SP={va.get('sp')}", flush=True)
        return True
    print(f"{date}  INCOMPLETE {va}", flush=True)
    return False


def main():
    if len(sys.argv) > 1:
        harvest(sys.argv[1], force=True)
    else:
        harvest(most_recent_closed_session())


if __name__ == "__main__":
    main()
