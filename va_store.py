#!/usr/bin/env python3
"""Persistent cache of prior-day value areas (POC/VAH/VAL) per symbol+date.

A CLOSED day's value area never changes, so we store it once and never recompute. On demand: look it up;
if it's missing (or was stored incomplete), fall back to a fetch function and store the result. The fetch
(fetch_va in tpo.py) reads the values off the TPO indicator by replaying to that day's close — see
docs/value-area-framework.md. Stdlib sqlite; the DB path is injectable for tests.
"""
import sqlite3, os, time

DB = os.path.expanduser("~/tradingview-mcp/value_areas.db")


def _conn(db=None):
    c = sqlite3.connect(db or DB)
    c.execute("CREATE TABLE IF NOT EXISTS value_areas("
              "symbol TEXT, date TEXT, poc REAL, vah REAL, val REAL, ts REAL, "
              "PRIMARY KEY(symbol, date))")
    return c


def get(symbol, date, db=None):
    """Return {date, poc, vah, val} for symbol+date, or None if not stored."""
    c = _conn(db)
    r = c.execute("SELECT poc, vah, val FROM value_areas WHERE symbol=? AND date=?", (symbol, date)).fetchone()
    c.close()
    return {"date": date, "poc": r[0], "vah": r[1], "val": r[2]} if r else None


def put(symbol, date, poc, vah, val, db=None):
    """Store (overwrite) a day's value area."""
    c = _conn(db)
    c.execute("INSERT OR REPLACE INTO value_areas(symbol, date, poc, vah, val, ts) VALUES(?,?,?,?,?,?)",
              (symbol, date, poc, vah, val, time.time()))
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
        put(symbol, date, fetched["poc"], fetched["vah"], fetched["val"], db)
        return {"date": date, "poc": fetched["poc"], "vah": fetched["vah"], "val": fetched["val"]}
    return None
