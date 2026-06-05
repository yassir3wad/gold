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


def main():
    test_upsert_roundtrip()
    test_inplace_update()
    test_concurrent_appends()
    test_analyze_parity()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
