#!/usr/bin/env python3
"""SQLite outcomes/log layer for the gold scalper — an ACID, concurrent-safe store that
mirrors (and will eventually replace) the CSV auto-learn dataset.

Why: the 7-pair live loop + backtests all append/upsert signal rows. CSV is append-rewrite
(read-all → rewrite-all), which races under concurrent writers and loses rows. SQLite in WAL
mode gives lock-free concurrent appends + in-place UPSERT by `id` (the exact semantics the
scanner needs: a PENDING row is updated in place to TP1/SL/timeout/etc).

Schema = SIG_COLS (id,time,side,grade,pattern,entry,sl,tp1,rng10,body_p,htf,result,exit,pips)
PLUS context columns (rsi,er,regime,room,session,symbol). The CSV format is NOT changed — this
is a parallel sink. analyze_logs reads from here when the DB exists, else falls back to CSV.

Pure stdlib (sqlite3). No third-party deps. Safe to import from the scanner hot path.
"""
import os, sqlite3

DEFAULT_DB = os.path.expanduser("~/tradingview-mcp/outcomes.db")

# The CSV schema (kept identical to scalp_fast.SIG_COLS — do NOT reorder/rename).
SIG_COLS = ["id", "time", "side", "grade", "confidence", "pattern", "entry", "sl", "tp1",
            "rng10", "body_p", "htf", "result", "exit", "pips"]
# Extra context captured alongside each signal (informational; absent in legacy CSV rows).
# Cost/decision fields (PROJECT_REVIEW_IMPROVEMENTS.md Engineering #4): execution cost is recorded
# explicitly so downstream analysis ranks on NET (after spread/slippage/commission) and can never
# accidentally optimize gross edge. `decision_source` is auto/AI/manual; `decision_reason_code` is a
# structured code for the gate/reviewer rationale (not free text). All TEXT, like every other column.
CONTEXT_COLS = ["rsi", "er", "regime", "room", "session", "symbol",
                "spread_pips", "slippage_pips", "commission_pips", "gross_pips", "net_pips",
                "decision_source", "decision_reason_code",
                # SMC bucket fields: stored multi-TF snapshot's range position + alignment + snapshot age,
                # so replay/analysis can split net-of-cost by smc_aligned (True/False/None). All TEXT.
                "smc_zone", "smc_aligned", "smc_age"]
ALL_COLS = SIG_COLS + CONTEXT_COLS

# `exit` is a SQL keyword → must be quoted everywhere it appears as a column name.
def _q(col):
    return f'"{col}"'


def _connect(db=DEFAULT_DB):
    """Open the DB in WAL mode so concurrent scanners/backtests never block each other.
    timeout lets a writer wait out a brief lock instead of erroring (busy retry)."""
    d = os.path.dirname(db)
    if d:
        os.makedirs(d, exist_ok=True)
    con = sqlite3.connect(db, timeout=30.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA busy_timeout=30000")
    _ensure_schema(con)
    return con


def _ensure_schema(con):
    cols_sql = ",\n  ".join(
        [f'{_q("id")} TEXT PRIMARY KEY'] +
        [f"{_q(c)} TEXT" for c in ALL_COLS if c != "id"]
    )
    con.execute(f"CREATE TABLE IF NOT EXISTS signals (\n  {cols_sql}\n)")
    # migrate older DBs: add any ALL_COLS column missing from the existing table (e.g. `confidence`)
    existing = {r[1] for r in con.execute("PRAGMA table_info(signals)").fetchall()}
    for c in ALL_COLS:
        if c not in existing:
            con.execute(f"ALTER TABLE signals ADD COLUMN {_q(c)} TEXT")
    # Indexes for the common analyze_logs query paths.
    con.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(time)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol_time ON signals(symbol, time)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_signals_result ON signals(result)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_signals_session ON signals(session)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_signals_pattern ON signals(pattern)")
    con.commit()


def init_db(db=DEFAULT_DB):
    """Create the DB + schema if absent. Returns the path."""
    con = _connect(db)
    con.close()
    return db


def log_signal(row, db=DEFAULT_DB):
    """UPSERT a signal row by `id`. Mirrors scalp_fast.log_signal semantics: an initial PENDING
    row is later updated IN PLACE (same id) to TP1/SL/timeout/superseded/etc — never duplicated.

    Only the keys present in `row` are written/updated; columns not supplied are left untouched on
    update (so a partial result update like {id, result, exit, pips} preserves the original entry/
    side/context). Unknown keys are ignored. Every value is stored as TEXT to match the CSV store
    exactly (so analyze_logs' numeric coercion behaves identically over either source)."""
    if "id" not in row or row["id"] in (None, ""):
        raise ValueError("log_signal: row must have a non-empty 'id'")
    data = {k: ("" if v is None else str(v)) for k, v in row.items() if k in ALL_COLS}
    if data.get("symbol"):
        data["symbol"] = data["symbol"].upper()
    data["id"] = str(row["id"])
    cols = list(data.keys())
    placeholders = ", ".join("?" for _ in cols)
    col_list = ", ".join(_q(c) for c in cols)
    # On conflict, update every supplied column EXCEPT id (in-place update of the same signal).
    updates = ", ".join(f"{_q(c)}=excluded.{_q(c)}" for c in cols if c != "id")
    sql = f"INSERT INTO signals ({col_list}) VALUES ({placeholders})"
    if updates:
        sql += f" ON CONFLICT(id) DO UPDATE SET {updates}"
    else:
        sql += " ON CONFLICT(id) DO NOTHING"
    con = _connect(db)
    try:
        con.execute(sql, [data[c] for c in cols])
        con.commit()
    finally:
        con.close()


def rows(symbol=None, since=None, db=DEFAULT_DB):
    """Return signal rows as a list of plain dicts (one key per ALL_COLS), newest-time first.
    `symbol` filters by the symbol context column (case-insensitive). `since` (a 'YYYY-MM-DD ...'
    string compared lexically, which is correct for ISO timestamps) keeps rows at/after that time."""
    if not os.path.exists(db):
        return []
    where, params = [], []
    if symbol:
        where.append("symbol = ?")
        params.append(symbol.upper())
    if since:
        where.append('"time" >= ?')
        params.append(str(since))
    sql = "SELECT * FROM signals"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += ' ORDER BY "time" DESC'
    con = _connect(db)
    try:
        out = []
        for r in con.execute(sql, params).fetchall():
            d = {k: (r[k] if r[k] is not None else "") for k in r.keys()}
            out.append(d)
        return out
    finally:
        con.close()


def win_rate_by(dimension, db=DEFAULT_DB):
    """Aggregate executed-trade win rate + net pips grouped by `dimension` (a column name such as
    'pattern', 'grade', 'side', 'symbol', 'regime'). Win = net pips > 0. Only rows that represent a
    real executed trade (result in TP1/TP2/SL/timeout/superseded/BE) with a numeric `pips` count.
    Returns {group_value: {n, wins, losses, scratch, win_rate, net}}."""
    if dimension not in ALL_COLS:
        raise ValueError(f"win_rate_by: unknown dimension {dimension!r} (must be one of {ALL_COLS})")
    if not os.path.exists(db):
        return {}
    executed = ("TP1", "TP2", "SL", "timeout", "superseded", "BE")
    con = _connect(db)
    try:
        marks = ", ".join("?" for _ in executed)
        sql = (f"SELECT {_q(dimension)} AS grp, result, pips FROM signals "
               f"WHERE result IN ({marks})")
        agg = {}
        for r in con.execute(sql, list(executed)).fetchall():
            try:
                p = float(str(r["pips"]).replace(",", "").strip())
            except (TypeError, ValueError):
                continue   # non-numeric pips → not a counted outcome
            g = r["grp"] if r["grp"] not in (None, "") else "?"
            a = agg.setdefault(g, {"n": 0, "wins": 0, "losses": 0, "scratch": 0, "net": 0.0})
            a["n"] += 1
            a["net"] += p
            if p > 0:   a["wins"] += 1
            elif p < 0: a["losses"] += 1
            else:       a["scratch"] += 1
        for a in agg.values():
            a["win_rate"] = (100.0 * a["wins"] / a["n"]) if a["n"] else 0.0
            a["net"] = round(a["net"], 1)
        return agg
    finally:
        con.close()


def session_breakdown(db=DEFAULT_DB):
    """Aggregate executed-trade win rate + net pips grouped by trading session (LONDON, NEWYORK,
    ASIA, etc). Win = net pips > 0. Only rows that represent a real executed trade (result in
    TP1/TP2/SL/timeout/superseded/BE) with a numeric `pips` count.
    Returns {session_name: {n, wins, losses, scratch, win_rate, net}}."""
    return win_rate_by("session", db)


def strategy_performance(db=DEFAULT_DB):
    """Aggregate executed-trade win rate + net pips grouped by pattern/strategy. Win = net pips > 0.
    Only rows that represent a real executed trade (result in TP1/TP2/SL/timeout/superseded/BE) with a
    numeric `pips` count. Returns {pattern_name: {n, wins, losses, scratch, win_rate, net}}."""
    return win_rate_by("pattern", db)


def hourly_distribution(db=DEFAULT_DB):
    """Aggregate executed-trade win rate + net pips grouped by hour of day (0-23). Win = net pips > 0.
    Only rows that represent a real executed trade (result in TP1/TP2/SL/timeout/superseded/BE) with a
    numeric `pips` count. Returns {hour: {n, wins, losses, scratch, win_rate, net}}."""
    if not os.path.exists(db):
        return {}
    executed = ("TP1", "TP2", "SL", "timeout", "superseded", "BE")
    con = _connect(db)
    try:
        marks = ", ".join("?" for _ in executed)
        # Extract hour from time column (format: 'YYYY-MM-DD HH:MM') using substr(time, 12, 2)
        sql = (f"SELECT CAST(substr({_q('time')}, 12, 2) AS INTEGER) AS hour, result, pips FROM signals "
               f"WHERE result IN ({marks})")
        agg = {}
        for r in con.execute(sql, list(executed)).fetchall():
            try:
                p = float(str(r["pips"]).replace(",", "").strip())
            except (TypeError, ValueError):
                continue   # non-numeric pips → not a counted outcome
            h = r["hour"] if r["hour"] is not None else -1
            a = agg.setdefault(h, {"n": 0, "wins": 0, "losses": 0, "scratch": 0, "net": 0.0})
            a["n"] += 1
            a["net"] += p
            if p > 0:   a["wins"] += 1
            elif p < 0: a["losses"] += 1
            else:       a["scratch"] += 1
        for a in agg.values():
            a["win_rate"] = (100.0 * a["wins"] / a["n"]) if a["n"] else 0.0
            a["net"] = round(a["net"], 1)
        return agg
    finally:
        con.close()


if __name__ == "__main__":
    import sys, json
    db = DEFAULT_DB
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        print("initialized", init_db(db))
    else:
        rs = rows(db=db)
        print(f"{len(rs)} rows in {db}")
        if rs:
            print(json.dumps(rs[0], indent=2))
