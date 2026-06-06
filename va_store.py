#!/usr/bin/env python3
"""Persistent cache of prior-day value areas (POC/VAH/VAL) per symbol+date.

A CLOSED day's value area never changes, so we store it once and never recompute. On demand: look it up;
if it's missing (or was stored incomplete), fall back to a fetch function and store the result. The fetch
(fetch_va in tpo.py) reads the values off the TPO indicator by replaying to that day's close — see
docs/value-area-framework.md. Stdlib sqlite; the DB path is injectable for tests.
"""
import sqlite3, os, time, json

DB = os.path.expanduser("~/tradingview-mcp/value_areas.db")


def _conn(db=None):
    c = sqlite3.connect(db or DB)
    c.execute("CREATE TABLE IF NOT EXISTS value_areas("
              "symbol TEXT, date TEXT, poc REAL, vah REAL, val REAL, sp TEXT, ts REAL, "
              "PRIMARY KEY(symbol, date))")
    # migrate older DBs that predate the single-print column
    cols = [r[1] for r in c.execute("PRAGMA table_info(value_areas)").fetchall()]
    if "sp" not in cols:
        c.execute("ALTER TABLE value_areas ADD COLUMN sp TEXT")
    return c


def get(symbol, date, db=None):
    """Return {date, poc, vah, val, sp} for symbol+date, or None. `sp` is a list of single-print zones
    [[lo, hi], ...] (target levels per the value-area framework), or []."""
    c = _conn(db)
    r = c.execute("SELECT poc, vah, val, sp FROM value_areas WHERE symbol=? AND date=?", (symbol, date)).fetchone()
    c.close()
    if not r:
        return None
    return {"date": date, "poc": r[0], "vah": r[1], "val": r[2], "sp": json.loads(r[3]) if r[3] else []}


def put(symbol, date, poc, vah, val, sp=None, db=None):
    """Store (overwrite) a day's value area. `sp` = optional list of single-print zones [[lo, hi], ...]."""
    c = _conn(db)
    c.execute("INSERT OR REPLACE INTO value_areas(symbol, date, poc, vah, val, sp, ts) VALUES(?,?,?,?,?,?,?)",
              (symbol, date, poc, vah, val, json.dumps(sp) if sp else None, time.time()))
    c.commit(); c.close()


def _complete(v):
    return bool(v) and v.get("poc") is not None and v.get("vah") is not None and v.get("val") is not None


def get_or_fetch(symbol, date, fetch_fn, db=None):
    """Return the day's value area: from the DB if a COMPLETE row exists (immutable — never re-fetched);
    otherwise call fetch_fn(symbol, date) -> {poc, vah, val}, store it if complete, and return it.
    Returns None if the fetch couldn't produce a complete value area (so it'll be retried next time)."""
    cached = get(symbol, date, db)
    if _complete(cached):
        return cached
    fetched = fetch_fn(symbol, date)
    if _complete(fetched):
        put(symbol, date, fetched["poc"], fetched["vah"], fetched["val"], sp=fetched.get("sp"), db=db)
        return get(symbol, date, db)
    return None
