#!/usr/bin/env python3
"""One-shot import of the existing CSV auto-learn dataset into the SQLite outcomes DB.

Reads every logs/<sym>/<YYYY-MM-DD>.csv PLUS the legacy signals_log.csv (gold history), and
UPSERTs each row into outcomes.db keyed by id (so re-running is idempotent — no duplicates).
The per-pair directory name supplies the `symbol` context column; the legacy flat file is gold
(XAUUSD), matching analyze_logs.load_rows. Existing CSV files are left untouched.

    python3 migrate_logs_to_db.py            # import into ~/tradingview-mcp/outcomes.db
    python3 migrate_logs_to_db.py --db /tmp/x.db
"""
import os, sys, csv as _csv, glob

import outcome_db

TVDIR = os.path.expanduser("~/tradingview-mcp")


def _sources():
    """(path, symbol) for every CSV in the auto-learn dataset, oldest-first so newer rows win."""
    src = []
    for p in sorted(glob.glob(os.path.join(TVDIR, "logs", "*", "*.csv"))):
        sym = os.path.basename(os.path.dirname(p)).upper()
        src.append((p, sym))
    legacy = os.path.join(TVDIR, "signals_log.csv")
    if os.path.exists(legacy):
        src.append((legacy, "XAUUSD"))
    return src


def migrate(db=outcome_db.DEFAULT_DB, sources=None):
    """Import all CSV rows into the DB. Returns (files, rows_seen, rows_written)."""
    outcome_db.init_db(db)
    if sources is None:
        sources = _sources()
    files = rows_seen = rows_written = 0
    seen_ids = set()
    for path, sym in sources:
        try:
            recs = list(_csv.DictReader(open(path)))
        except Exception:
            continue
        files += 1
        for r in recs:
            rid = (r.get("id") or "").strip()
            if not rid:
                continue   # skip header-less / malformed rows with no id
            rows_seen += 1
            row = {k: r.get(k, "") for k in outcome_db.SIG_COLS}
            row["id"] = rid
            # tag symbol from the directory; preserve a symbol already embedded in the row if present
            row["symbol"] = (r.get("symbol") or sym).upper()
            for c in ("rsi", "er", "regime", "room", "session"):
                if r.get(c) not in (None, ""):
                    row[c] = r.get(c)
            try:
                outcome_db.log_signal(row, db=db)
                rows_written += 1
                seen_ids.add(rid)
            except Exception as e:
                print(f"  ! skipped {path} id={rid}: {e}", file=sys.stderr)
    return files, rows_seen, rows_written, len(seen_ids)


def main():
    db = outcome_db.DEFAULT_DB
    if "--db" in sys.argv:
        try: db = sys.argv[sys.argv.index("--db") + 1]
        except Exception: pass
    files, seen, written, uniq = migrate(db)
    total = len(outcome_db.rows(db=db))
    print(f"migrated {written} rows ({uniq} unique ids) from {files} CSV files into {db}")
    print(f"DB now holds {total} signal rows")


if __name__ == "__main__":
    main()
