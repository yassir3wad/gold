#!/usr/bin/env python3
"""Tests for va_store.py — a sqlite cache of prior-day value areas (POC/VAH/VAL). Closed-day profiles are
immutable, so once a complete row is stored it's never re-fetched; a missing/incomplete date falls back to
a fetch function and stores the result. Pure stdlib; fetch is injected.
    python3 test_va_store.py   (exit 0 = all pass)
"""
import sys, os, tempfile
import va_store as V

_r = []
def check(n, c): _r.append((n, bool(c)))


def tmpdb():
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p); return p


def test_put_get_roundtrip():
    db = tmpdb()
    V.put("XAUUSD", "2026-05-29", 4514.96, 4567.58, 4509.12, db=db)
    r = V.get("XAUUSD", "2026-05-29", db=db)
    check("get returns the stored row", r and r["poc"] == 4514.96 and r["vah"] == 4567.58 and r["val"] == 4509.12)
    check("get unknown date -> None", V.get("XAUUSD", "2026-01-01", db=db) is None)
    check("get respects symbol", V.get("EURUSD", "2026-05-29", db=db) is None)


def test_get_or_fetch_misses_then_caches():
    db = tmpdb(); calls = []
    def fetch(sym, date):
        calls.append((sym, date)); return {"poc": 4455.0, "vah": 4490.0, "val": 4415.0}
    r1 = V.get_or_fetch("XAUUSD", "2026-05-27", fetch, db=db)
    check("miss -> fetch called once", calls == [("XAUUSD", "2026-05-27")])
    check("miss -> returns fetched value", r1 and r1["poc"] == 4455.0)
    r2 = V.get_or_fetch("XAUUSD", "2026-05-27", fetch, db=db)
    check("second call -> served from DB, fetch NOT called again (immutable)", len(calls) == 1 and r2["poc"] == 4455.0)


def test_incomplete_not_cached():
    db = tmpdb(); calls = []
    def fetch_bad(sym, date):
        calls.append(1); return {"poc": None, "vah": 4495.0, "val": 4491.0}   # POC didn't render -> incomplete
    r = V.get_or_fetch("XAUUSD", "2026-05-28", fetch_bad, db=db)
    check("incomplete fetch (no POC) -> not returned as valid", r is None)
    check("incomplete fetch -> nothing cached", V.get("XAUUSD", "2026-05-28", db=db) is None)
    # next time a good fetch succeeds and caches
    def fetch_ok(sym, date):
        calls.append(1); return {"poc": 4461.0, "vah": 4495.53, "val": 4491.58}
    r2 = V.get_or_fetch("XAUUSD", "2026-05-28", fetch_ok, db=db)
    check("retry with complete fetch -> cached", r2 and r2["poc"] == 4461.0 and V.get("XAUUSD", "2026-05-28", db=db))


def main():
    for fn in (test_put_get_roundtrip, test_get_or_fetch_misses_then_caches, test_incomplete_not_cached):
        try: fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False); print(f"  !! {fn.__name__}: {e}")
    p = sum(1 for _, ok in _r if ok); t = len(_r)
    for n, ok in _r:
        if not ok: print(f"  [FAIL] {n}")
    print(f"\n{'OK' if p == t else 'FAIL'} {p}/{t} checks passed")
    sys.exit(0 if p == t else 1)


if __name__ == "__main__":
    main()
