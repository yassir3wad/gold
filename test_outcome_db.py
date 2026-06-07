#!/usr/bin/env python3
"""Pure unit tests for the SQLite outcomes/log layer (outcome_db.py) + analyze_logs DB/CSV parity.

No chart, no network, no live state — every test uses a throwaway temp DB / temp dir and never
touches the real ~/tradingview-mcp/outcomes.db or the live logs.

    python3 test_outcome_db.py

Covers:
  (a) upsert round-trip          — insert a row, read it back intact
  (b) in-place update            — PENDING row updated by id to TP1 ⇒ exactly one row, result=TP1
  (c) concurrent-append safety   — N threads appending distinct ids ⇒ zero lost rows
  (d) analyze_logs parity        — same data via DB vs via CSV yields identical executed/rejected/net
"""
import os, csv as _csv, tempfile, threading, importlib

import outcome_db


def _mkdb():
    fd, path = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(path)
    return path


def _cleanup(path):
    for p in (path, path + "-wal", path + "-shm"):
        try: os.remove(p)
        except OSError: pass


def test_upsert_roundtrip():
    db = _mkdb()
    try:
        row = {"id": "1001", "time": "2026-06-05 10:00", "side": "LONG", "grade": "A",
               "pattern": "momentum impulse", "entry": "4500.0", "sl": "4485.0", "tp1": "4515.0",
               "rng10": "60", "body_p": "12", "htf": "open", "result": "PENDING", "exit": "",
               "pips": "", "rsi": "55", "er": "0.6", "regime": "UP", "room": "40",
               "session": "ON", "symbol": "XAUUSD"}
        outcome_db.log_signal(row, db=db)
        got = outcome_db.rows(db=db)
        assert len(got) == 1, f"expected 1 row, got {len(got)}"
        r = got[0]
        for k, v in row.items():
            assert r[k] == v, f"col {k}: expected {v!r}, got {r[k]!r}"
        # `exit` (SQL keyword) survives round-trip
        assert r["exit"] == "", f"exit col mismatch: {r['exit']!r}"
        print("PASS (a) upsert round-trip")
    finally:
        _cleanup(db)


def test_inplace_update():
    db = _mkdb()
    try:
        outcome_db.log_signal({"id": "2002", "time": "2026-06-05 11:00", "side": "SHORT",
                               "grade": "B", "pattern": "VWAP rejection", "entry": "4500.0",
                               "sl": "4515.0", "tp1": "4485.0", "result": "PENDING",
                               "symbol": "XAUUSD"}, db=db)
        # later: the SAME id is finalized to TP1 (partial-row update, like check_active_trade)
        outcome_db.log_signal({"id": "2002", "result": "TP1", "exit": "4485.0", "pips": "150"}, db=db)
        got = outcome_db.rows(db=db)
        assert len(got) == 1, f"in-place update created {len(got)} rows (expected 1)"
        r = got[0]
        assert r["result"] == "TP1", f"result not updated: {r['result']!r}"
        assert r["exit"] == "4485.0" and r["pips"] == "150", "result fields not updated"
        # untouched columns preserved from the original PENDING insert
        assert r["side"] == "SHORT" and r["entry"] == "4500.0" and r["pattern"] == "VWAP rejection", \
            "in-place update clobbered untouched columns"
        print("PASS (b) in-place PENDING->TP1 update")
    finally:
        _cleanup(db)


def test_concurrent_appends():
    db = _mkdb()
    try:
        outcome_db.init_db(db)
        N_THREADS, PER = 8, 200
        TOTAL = N_THREADS * PER

        def worker(base):
            for i in range(PER):
                rid = base * 100000 + i
                outcome_db.log_signal({"id": rid, "time": "2026-06-05 12:00", "side": "LONG",
                                       "result": "TP1", "pips": "50", "symbol": "XAUUSD"}, db=db)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(N_THREADS)]
        for t in threads: t.start()
        for t in threads: t.join()
        got = outcome_db.rows(db=db)
        assert len(got) == TOTAL, f"lost rows under concurrency: {len(got)}/{TOTAL}"
        ids = {r["id"] for r in got}
        assert len(ids) == TOTAL, f"duplicate/lost ids: {len(ids)} unique of {TOTAL}"
        print(f"PASS (c) concurrent appends ({N_THREADS} threads x {PER} = {TOTAL}, zero lost)")
    finally:
        _cleanup(db)


# ---- (d) parity: analyze_logs over the DB vs the same data in CSV ----

SAMPLE = [
    # executed wins/losses + a rejected + a pending (pending excluded from executed counts)
    {"id": "1", "time": "2026-06-05 09:00", "side": "LONG", "grade": "A", "pattern": "impulse",
     "entry": "4500", "sl": "4485", "tp1": "4515", "rng10": "60", "body_p": "12", "htf": "open",
     "result": "TP1", "exit": "4515", "pips": "150"},
    {"id": "2", "time": "2026-06-05 09:30", "side": "SHORT", "grade": "B", "pattern": "VWAP rejection",
     "entry": "4500", "sl": "4515", "tp1": "4485", "rng10": "55", "body_p": "10", "htf": "open",
     "result": "SL", "exit": "4515", "pips": "-150"},
    {"id": "3", "time": "2026-06-05 10:00", "side": "LONG", "grade": "A", "pattern": "break-and-retest",
     "entry": "4500", "sl": "4490", "tp1": "4520", "rng10": "70", "body_p": "15", "htf": "open",
     "result": "TP2", "exit": "4520", "pips": "200"},
    {"id": "4", "time": "2026-06-05 10:30", "side": "SHORT", "grade": "C", "pattern": "impulse",
     "entry": "4500", "sl": "4510", "tp1": "4490", "rng10": "40", "body_p": "8", "htf": "open",
     "result": "rejected", "exit": "", "pips": "neg R:R 0.40 (TP1 < 0.8xSL)"},
    {"id": "5", "time": "2026-06-05 11:00", "side": "LONG", "grade": "B", "pattern": "zone-bounce",
     "entry": "4500", "sl": "4488", "tp1": "4518", "rng10": "65", "body_p": "11", "htf": "open",
     "result": "PENDING", "exit": "", "pips": ""},
]


def _analyze_numbers(rows):
    import analyze_logs
    executed = [r for r in rows if r.get("result") in analyze_logs.EXECUTED
                and analyze_logs._num(r.get("pips")) is not None]
    rejected = [r for r in rows if r.get("result") == "rejected"]
    net = sum(analyze_logs._num(r["pips"]) for r in executed)
    return (len(executed), len(rejected), net)


def test_analyze_parity():
    db = _mkdb()
    tvdir = tempfile.mkdtemp()
    import analyze_logs
    orig_db, orig_tvdir = analyze_logs.OUTCOMES_DB, analyze_logs.TVDIR
    try:
        # --- DB side ---
        for r in SAMPLE:
            outcome_db.log_signal({**r, "symbol": "XAUUSD"}, db=db)
        analyze_logs.OUTCOMES_DB = db
        db_rows = analyze_logs.load_rows()
        db_nums = _analyze_numbers(db_rows)

        # --- CSV side (same data; point analyze_logs at the temp dir, no DB present) ---
        sym_dir = os.path.join(tvdir, "logs", "xauusd")
        os.makedirs(sym_dir, exist_ok=True)
        csv_path = os.path.join(sym_dir, "2026-06-05.csv")
        with open(csv_path, "w", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=outcome_db.SIG_COLS)
            w.writeheader()
            for r in SAMPLE:
                w.writerow({k: r.get(k, "") for k in outcome_db.SIG_COLS})
        analyze_logs.OUTCOMES_DB = os.path.join(tvdir, "outcomes.db")   # absent → CSV fallback
        analyze_logs.TVDIR = tvdir
        csv_rows = analyze_logs.load_rows()
        csv_nums = _analyze_numbers(csv_rows)

        assert db_nums == csv_nums, f"parity mismatch: DB {db_nums} vs CSV {csv_nums}"
        # sanity: 3 executed (TP1, SL, TP2), 1 rejected, net = 150 - 150 + 200 = 200
        assert db_nums == (3, 1, 200.0), f"unexpected analysis numbers: {db_nums}"
        print(f"PASS (d) analyze_logs DB/CSV parity (executed/rejected/net = {db_nums})")
    finally:
        analyze_logs.OUTCOMES_DB, analyze_logs.TVDIR = orig_db, orig_tvdir
        _cleanup(db)
        import shutil
        shutil.rmtree(tvdir, ignore_errors=True)


# ---- cost/decision fields (PROJECT_REVIEW_IMPROVEMENTS.md Engineering #4) ----

COST_DECISION_COLS = ["spread_pips", "slippage_pips", "commission_pips", "gross_pips", "net_pips",
                      "decision_source", "decision_reason_code"]


def test_cost_decision_schema():
    """The new cost/decision columns exist in the DB schema (so analysis can rank on NET, not gross)."""
    db = _mkdb()
    try:
        outcome_db.init_db(db)
        con = outcome_db._connect(db)
        try:
            cols = {r[1] for r in con.execute("PRAGMA table_info(signals)").fetchall()}
        finally:
            con.close()
        for c in COST_DECISION_COLS:
            assert c in cols, f"schema missing cost/decision column {c!r} (have {sorted(cols)})"
            assert c in outcome_db.ALL_COLS, f"{c!r} not in ALL_COLS"
        print("PASS (e) cost/decision columns present in schema")
    finally:
        _cleanup(db)


def test_cost_decision_roundtrip():
    """A row written with the cost/decision fields round-trips them back through the read path."""
    db = _mkdb()
    try:
        row = {"id": "5005", "time": "2026-06-05 13:00", "side": "LONG", "grade": "A",
               "pattern": "resistance-trendline break", "entry": "4500.0", "sl": "4485.0",
               "tp1": "4515.0", "result": "TP1", "exit": "4515.0", "pips": "150",
               "symbol": "XAUUSD",
               "spread_pips": "3.0", "slippage_pips": "0.5", "commission_pips": "0.2",
               "gross_pips": "150.0", "net_pips": "146.3",
               "decision_source": "AI", "decision_reason_code": "core_setup_room_ok"}
        outcome_db.log_signal(row, db=db)
        got = outcome_db.rows(db=db)
        assert len(got) == 1, f"expected 1 row, got {len(got)}"
        r = got[0]
        for k in COST_DECISION_COLS:
            assert r[k] == row[k], f"cost/decision col {k}: expected {row[k]!r}, got {r[k]!r}"
        print("PASS (f) cost/decision fields round-trip")
    finally:
        _cleanup(db)


def test_old_style_row_backcompat():
    """An OLD-style row with NONE of the new fields still inserts fine and reads back with the new
    columns present but empty (migration / back-compat must not break legacy writers)."""
    db = _mkdb()
    try:
        old_row = {"id": "6006", "time": "2026-06-05 14:00", "side": "SHORT", "grade": "B",
                   "pattern": "VWAP rejection", "entry": "4500.0", "sl": "4515.0", "tp1": "4485.0",
                   "rng10": "55", "body_p": "10", "htf": "open", "result": "PENDING", "exit": "",
                   "pips": "", "rsi": "45", "er": "0.5", "regime": "DOWN", "room": "30",
                   "session": "ON", "symbol": "XAUUSD"}
        outcome_db.log_signal(old_row, db=db)
        got = outcome_db.rows(db=db)
        assert len(got) == 1, f"old-style row failed to insert: got {len(got)} rows"
        r = got[0]
        # original fields preserved
        for k, v in old_row.items():
            assert r[k] == v, f"col {k}: expected {v!r}, got {r[k]!r}"
        # new cost/decision columns present but empty (not supplied → "")
        for c in COST_DECISION_COLS:
            assert r[c] == "", f"new col {c!r} on old-style row should be empty, got {r[c]!r}"
        print("PASS (g) old-style row (no new fields) inserts + back-compat")
    finally:
        _cleanup(db)


def main():
    test_upsert_roundtrip()
    test_inplace_update()
    test_concurrent_appends()
    test_analyze_parity()
    test_cost_decision_schema()
    test_cost_decision_roundtrip()
    test_old_style_row_backcompat()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
