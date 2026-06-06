#!/usr/bin/env python3
"""One-off: re-harvest a date range's value areas from the TPO indicator, FORCE-overwriting the va_store
(the earlier harvest predated single-print reading, so SP zones are empty). Closed days are immutable, so
overwriting is safe. Restores realtime (replay stop) at the end. Run only when the market is closed so it
doesn't disturb the live chart.
    python3 reharvest_week.py 2026-06-01 2026-06-05
"""
import sys, datetime as dt
import tpo, va_store as vs

SYMBOL = "XAUUSD"


def daterange(a, b):
    d = dt.datetime.strptime(a, "%Y-%m-%d").date()
    end = dt.datetime.strptime(b, "%Y-%m-%d").date()
    while d <= end:
        if d.weekday() < 5:   # skip Sat/Sun (no session)
            yield d.isoformat()
        d += dt.timedelta(days=1)


def main():
    a, b = sys.argv[1], sys.argv[2]
    for date in daterange(a, b):
        try:
            va = tpo.fetch_va(SYMBOL, date)
        except Exception as e:
            print(f"{date}  FETCH-ERROR {e}", flush=True); continue
        if va and va.get("poc") and va.get("vah") and va.get("val"):
            vs.put(SYMBOL, date, va["poc"], va["vah"], va["val"], sp=va.get("sp"))
            print(f"{date}  POC={va['poc']} VAH={va['vah']} VAL={va['val']} SP={va.get('sp')}", flush=True)
        else:
            print(f"{date}  INCOMPLETE {va}", flush=True)
    # restore realtime so the live engine reads a normal chart
    tpo._default_tv("", "replay", "stop")
    print("done; replay stopped", flush=True)


if __name__ == "__main__":
    main()
