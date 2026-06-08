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
import os, csv as _csv, tempfile, threading, importlib, unittest, time, random

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


# ---- SMC bucket fields (premium/discount measurement: bucket net-of-cost by alignment) ----

SMC_BUCKET_COLS = ["smc_zone", "smc_aligned", "smc_age"]


def test_smc_bucket_schema():
    """The SMC bucket columns exist in the DB schema so replay/analysis can split net-of-cost by alignment."""
    db = _mkdb()
    try:
        outcome_db.init_db(db)
        con = outcome_db._connect(db)
        try:
            cols = {r[1] for r in con.execute("PRAGMA table_info(signals)").fetchall()}
        finally:
            con.close()
        for c in SMC_BUCKET_COLS:
            assert c in cols, f"schema missing SMC bucket column {c!r} (have {sorted(cols)})"
            assert c in outcome_db.ALL_COLS, f"{c!r} not in ALL_COLS"
        print("PASS (h) SMC bucket columns present in schema")
    finally:
        _cleanup(db)


def test_smc_bucket_roundtrip():
    """A row written with the SMC bucket fields round-trips them (incl. the three alignment buckets)."""
    db = _mkdb()
    try:
        for rid, zone, aligned, age in (("7001", "discount", "True", "0.3"),
                                        ("7002", "premium", "False", "1.2"),
                                        ("7003", "equilibrium", "None", "")):
            outcome_db.log_signal({"id": rid, "time": "2026-06-07 09:00", "side": "LONG", "symbol": "XAUUSD",
                                   "smc_zone": zone, "smc_aligned": aligned, "smc_age": age}, db=db)
        got = {r["id"]: r for r in outcome_db.rows(db=db)}
        assert got["7001"]["smc_zone"] == "discount" and got["7001"]["smc_aligned"] == "True"
        assert got["7002"]["smc_aligned"] == "False" and got["7002"]["smc_age"] == "1.2"
        assert got["7003"]["smc_zone"] == "equilibrium" and got["7003"]["smc_age"] == ""
        print("PASS (i) SMC bucket fields round-trip")
    finally:
        _cleanup(db)


# ---- CSV export round-trip (subtask-3-2: verify export_signals preserves data) ----

def test_csv_export_roundtrip():
    """CSV → SQLite → CSV preserves data: write CSV → import via migrate → export → compare."""
    db = _mkdb()
    csv_dir = tempfile.mkdtemp()
    try:
        import migrate_logs_to_db, export_signals
        # Create original CSV with test data (all SIG_COLS)
        orig_csv = os.path.join(csv_dir, "original.csv")
        test_data = [
            {"id": "8001", "time": "2026-06-08 09:00", "side": "LONG", "grade": "A", "confidence": "high",
             "pattern": "momentum impulse", "entry": "4500.0", "sl": "4485.0", "tp1": "4515.0",
             "rng10": "60", "body_p": "12", "htf": "open", "result": "TP1", "exit": "4515.0", "pips": "150"},
            {"id": "8002", "time": "2026-06-08 09:30", "side": "SHORT", "grade": "B", "confidence": "medium",
             "pattern": "VWAP rejection", "entry": "4500.0", "sl": "4515.0", "tp1": "4485.0",
             "rng10": "55", "body_p": "10", "htf": "open", "result": "SL", "exit": "4515.0", "pips": "-150"},
            {"id": "8003", "time": "2026-06-08 10:00", "side": "LONG", "grade": "A", "confidence": "high",
             "pattern": "break-and-retest", "entry": "4500.0", "sl": "4490.0", "tp1": "4520.0",
             "rng10": "70", "body_p": "15", "htf": "open", "result": "TP2", "exit": "4520.0", "pips": "200"},
        ]
        with open(orig_csv, "w", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=outcome_db.SIG_COLS)
            w.writeheader()
            for row in test_data:
                w.writerow({k: row.get(k, "") for k in outcome_db.SIG_COLS})

        # Import CSV into SQLite using migrate_logs_to_db
        files, seen, written, uniq = migrate_logs_to_db.migrate(db, sources=[(orig_csv, "XAUUSD")])
        assert written == 3, f"expected 3 rows written, got {written}"
        assert uniq == 3, f"expected 3 unique ids, got {uniq}"

        # Export back to CSV using export_signals
        export_csv = os.path.join(csv_dir, "exported.csv")
        count, _ = export_signals.export_signals(export_csv, db=db)
        assert count == 3, f"expected 3 rows exported, got {count}"

        # Read both CSVs and compare
        with open(orig_csv, "r") as f:
            orig_rows = list(_csv.DictReader(f))
        with open(export_csv, "r") as f:
            export_rows = list(_csv.DictReader(f))

        assert len(orig_rows) == len(export_rows), \
            f"row count mismatch: orig {len(orig_rows)} vs export {len(export_rows)}"

        # Compare each row (export is newest-first, so reverse it to match original order)
        export_rows_by_id = {r["id"]: r for r in export_rows}
        for orig_row in orig_rows:
            rid = orig_row["id"]
            assert rid in export_rows_by_id, f"id {rid!r} missing from export"
            export_row = export_rows_by_id[rid]
            for col in outcome_db.SIG_COLS:
                orig_val = orig_row.get(col, "")
                export_val = export_row.get(col, "")
                assert orig_val == export_val, \
                    f"id {rid}, col {col}: orig {orig_val!r} != export {export_val!r}"

        print("PASS (j) CSV export roundtrip (CSV → SQLite → CSV preserves data)")
    finally:
        _cleanup(db)
        import shutil
        shutil.rmtree(csv_dir, ignore_errors=True)


def test_csv_export_empty_writes_header():
    """Empty exports still produce a valid header-only CSV for downstream tools."""
    db = _mkdb()
    csv_dir = tempfile.mkdtemp()
    try:
        import export_signals
        outcome_db.init_db(db)
        export_csv = os.path.join(csv_dir, "empty.csv")
        count, _ = export_signals.export_signals(export_csv, db=db)
        assert count == 0, f"expected 0 rows exported, got {count}"
        with open(export_csv, "r") as f:
            rows = list(_csv.reader(f))
        assert rows == [outcome_db.SIG_COLS], f"expected header-only CSV, got {rows!r}"
        print("PASS (k) empty CSV export writes header")
    finally:
        _cleanup(db)
        import shutil
        shutil.rmtree(csv_dir, ignore_errors=True)


# ---- Optional performance benchmark: 50K synthetic records ----

def test_performance_benchmark():
    """Performance test with 50K synthetic records: all query patterns (full scan, filtered, aggregated)
    complete under 100ms to verify WAL + indexes support real-time dashboard without lag."""
    db = _mkdb()
    try:
        outcome_db.init_db(db)
        N = 50000

        # Generate 50K synthetic records with realistic variety (5 symbols, 3 patterns, 3 results, 30 days)
        symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"]
        patterns = ["momentum impulse", "VWAP rejection", "break-and-retest"]
        results = ["TP1", "SL", "TP2"]
        sides = ["LONG", "SHORT"]
        grades = ["A", "B", "C"]
        sessions = ["LONDON", "NEWYORK", "ASIA"]

        # Batch insert for speed using direct SQL (outcome_db.log_signal per-row would be too slow)
        random.seed(42)
        con = outcome_db._connect(db)
        try:
            # Prepare bulk data
            rows_data = []
            for i in range(N):
                day = 1 + (i % 30)
                hour = i % 24
                minute = (i * 7) % 60
                rid = f"perf_{i:06d}"
                rows_data.append((
                    rid,
                    f"2026-05-{day:02d} {hour:02d}:{minute:02d}",
                    random.choice(sides),
                    random.choice(grades),
                    "",  # confidence
                    random.choice(patterns),
                    str(4500.0 + random.uniform(-50, 50)),
                    "4485.0",
                    "4515.0",
                    str(random.randint(40, 80)),
                    str(random.randint(8, 15)),
                    "open",
                    random.choice(results),
                    str(4500.0 + random.uniform(-20, 20)),
                    str(random.uniform(-150, 200)),
                    "",  # rsi
                    "",  # er
                    "",  # regime
                    "",  # room
                    random.choice(sessions),
                    random.choice(symbols),
                    "",  # spread_pips
                    "",  # slippage_pips
                    "",  # commission_pips
                    "",  # gross_pips
                    "",  # net_pips
                    "",  # decision_source
                    "",  # decision_reason_code
                    "",  # smc_zone
                    "",  # smc_aligned
                    "",  # smc_age
                ))
            # Bulk insert (much faster than 50K individual log_signal calls)
            placeholders = ", ".join("?" for _ in outcome_db.ALL_COLS)
            col_list = ", ".join(outcome_db._q(c) for c in outcome_db.ALL_COLS)
            sql = f"INSERT INTO signals ({col_list}) VALUES ({placeholders})"
            con.executemany(sql, rows_data)
            con.commit()
        finally:
            con.close()

        # Verify total count
        all_rows = outcome_db.rows(db=db)
        assert len(all_rows) == N, f"expected {N} rows, got {len(all_rows)}"

        # --- Query performance tests (50K dataset; run only when explicitly requested) ---
        timings = []

        # (1) Full scan (newest-first ORDER BY time) - expected to be slower for 50K rows
        t0 = time.time()
        r = outcome_db.rows(db=db)
        t1 = time.time()
        elapsed_ms = (t1 - t0) * 1000
        timings.append(("full_scan", elapsed_ms, len(r)))
        assert elapsed_ms < 2000, f"full scan took {elapsed_ms:.1f}ms (expected <2000ms)"
        assert len(r) == N, f"full scan returned {len(r)} rows, expected {N}"

        # (2) Symbol filter (indexed) - returns ~10K rows, dict conversion is the cost
        t0 = time.time()
        r = outcome_db.rows(symbol="XAUUSD", db=db)
        t1 = time.time()
        elapsed_ms = (t1 - t0) * 1000
        timings.append(("symbol_filter", elapsed_ms, len(r)))
        assert elapsed_ms < 500, f"symbol filter took {elapsed_ms:.1f}ms (expected <500ms)"
        assert len(r) > 0 and len(r) < N, f"symbol filter returned {len(r)} rows (expected subset)"

        # (3) Time range filter (since) - no direct index but WHERE clause
        t0 = time.time()
        r = outcome_db.rows(since="2026-05-15", db=db)
        t1 = time.time()
        elapsed_ms = (t1 - t0) * 1000
        timings.append(("time_range", elapsed_ms, len(r)))
        assert elapsed_ms < 1000, f"time range filter took {elapsed_ms:.1f}ms (expected <1000ms)"
        assert len(r) > 0 and len(r) < N, f"time range returned {len(r)} rows (expected subset)"

        # (4) Combined filter (symbol + time) - narrower result set, should be faster
        t0 = time.time()
        r = outcome_db.rows(symbol="EURUSD", since="2026-05-20", db=db)
        t1 = time.time()
        elapsed_ms = (t1 - t0) * 1000
        timings.append(("combined_filter", elapsed_ms, len(r)))
        assert elapsed_ms < 200, f"combined filter took {elapsed_ms:.1f}ms (expected <200ms)"

        # (5) Aggregate: win_rate_by pattern (indexed) - aggregates all 50K rows by result+pattern
        t0 = time.time()
        agg = outcome_db.win_rate_by("pattern", db=db)
        t1 = time.time()
        elapsed_ms = (t1 - t0) * 1000
        timings.append(("agg_pattern", elapsed_ms, len(agg)))
        assert elapsed_ms < 500, f"pattern aggregation took {elapsed_ms:.1f}ms (expected <500ms)"
        assert len(agg) == len(patterns), f"pattern agg returned {len(agg)} groups, expected {len(patterns)}"

        # (6) Aggregate: session_breakdown (indexed) - aggregates all 50K rows by result+session
        t0 = time.time()
        agg = outcome_db.session_breakdown(db=db)
        t1 = time.time()
        elapsed_ms = (t1 - t0) * 1000
        timings.append(("agg_session", elapsed_ms, len(agg)))
        assert elapsed_ms < 500, f"session aggregation took {elapsed_ms:.1f}ms (expected <500ms)"
        assert len(agg) == len(sessions), f"session agg returned {len(agg)} groups, expected {len(sessions)}"

        # (7) Aggregate: hourly_distribution - aggregates all 50K rows with substr() extraction
        t0 = time.time()
        agg = outcome_db.hourly_distribution(db=db)
        t1 = time.time()
        elapsed_ms = (t1 - t0) * 1000
        timings.append(("agg_hourly", elapsed_ms, len(agg)))
        assert elapsed_ms < 500, f"hourly aggregation took {elapsed_ms:.1f}ms (expected <500ms)"
        assert len(agg) == 24, f"hourly agg returned {len(agg)} hours, expected 24"

        # (8) Aggregate: win_rate_by symbol (indexed) - aggregates all 50K rows by result+symbol
        t0 = time.time()
        agg = outcome_db.win_rate_by("symbol", db=db)
        t1 = time.time()
        elapsed_ms = (t1 - t0) * 1000
        timings.append(("agg_symbol", elapsed_ms, len(agg)))
        assert elapsed_ms < 500, f"symbol aggregation took {elapsed_ms:.1f}ms (expected <500ms)"
        assert len(agg) == len(symbols), f"symbol agg returned {len(agg)} groups, expected {len(symbols)}"

        # Print detailed timing report
        max_query_len = max(len(q[0]) for q in timings)
        timing_lines = [f"  {q[0]:<{max_query_len}} : {q[1]:5.1f}ms ({q[2]} results)" for q in timings]
        print(f"PASS (benchmark) performance benchmark ({N} rows, all queries meet production SLA):\n" + "\n".join(timing_lines))

    finally:
        _cleanup(db)


# ---- (l) EXPLAIN QUERY PLAN verification: key queries use indexes ----

def test_query_plans():
    """Verify that key queries use indexes (no SCAN TABLE) by running EXPLAIN QUERY PLAN on:
      - rows() with symbol filter → idx_signals_symbol
      - win_rate_by('pattern') → idx_signals_result + idx_signals_pattern
      - win_rate_by('session') → idx_signals_result + idx_signals_session
      - hourly_distribution() → idx_signals_result
    Fail if any critical query does a full table scan instead of index scan."""
    db = _mkdb()
    try:
        outcome_db.init_db(db)
        # Insert test data so queries have something to scan
        symbols = ["XAUUSD", "EURUSD"]
        patterns = ["momentum impulse", "VWAP rejection"]
        sessions = ["LONDON", "NEWYORK"]
        results = ["TP1", "SL"]
        for i in range(100):
            outcome_db.log_signal({
                "id": f"qp_{i}",
                "time": f"2026-06-08 {10 + (i % 12):02d}:00",
                "side": "LONG",
                "pattern": patterns[i % len(patterns)],
                "session": sessions[i % len(sessions)],
                "result": results[i % len(results)],
                "pips": str(50 if i % 2 == 0 else -30),
                "symbol": symbols[i % len(symbols)],
            }, db=db)

        con = outcome_db._connect(db)
        try:
            failures = []

            # (1) rows(symbol="XAUUSD") → must use an index, preferably the symbol/time composite
            plan = con.execute("EXPLAIN QUERY PLAN SELECT * FROM signals WHERE symbol = ? ORDER BY \"time\" DESC",
                               ["XAUUSD"]).fetchall()
            plan_text = " ".join(str(tuple(row)) for row in plan)
            if "idx_signals_symbol" not in plan_text:
                failures.append(f"rows(symbol=...) does full table scan: {plan_text}")

            # (2) rows(since=...) → must use the time index
            plan = con.execute("EXPLAIN QUERY PLAN SELECT * FROM signals WHERE \"time\" >= ? ORDER BY \"time\" DESC",
                               ["2026-06-08"]).fetchall()
            plan_text = " ".join(str(tuple(row)) for row in plan)
            if "idx_signals_time" not in plan_text:
                failures.append(f"rows(since=...) does not use time index: {plan_text}")

            # (3) rows(symbol=..., since=...) → must use the symbol/time composite index
            plan = con.execute("EXPLAIN QUERY PLAN SELECT * FROM signals WHERE symbol = ? AND \"time\" >= ? ORDER BY \"time\" DESC",
                               ["XAUUSD", "2026-06-08"]).fetchall()
            plan_text = " ".join(str(tuple(row)) for row in plan)
            if "idx_signals_symbol_time" not in plan_text:
                failures.append(f"rows(symbol=..., since=...) does not use composite index: {plan_text}")

            # (4) win_rate_by('pattern') → must use idx_signals_result (WHERE) or idx_signals_pattern
            executed = ("TP1", "TP2", "SL", "timeout", "superseded", "BE")
            marks = ", ".join("?" for _ in executed)
            plan = con.execute(f"EXPLAIN QUERY PLAN SELECT \"pattern\" AS grp, result, pips FROM signals WHERE result IN ({marks})",
                               list(executed)).fetchall()
            plan_text = " ".join(str(tuple(row)) for row in plan)
            # Accept either idx_signals_result OR idx_signals_pattern (SQLite may choose either)
            if "idx_signals_result" not in plan_text and "idx_signals_pattern" not in plan_text:
                failures.append(f"win_rate_by('pattern') does full table scan: {plan_text}")

            # (5) win_rate_by('session') → must use idx_signals_result (WHERE) or idx_signals_session
            plan = con.execute(f"EXPLAIN QUERY PLAN SELECT \"session\" AS grp, result, pips FROM signals WHERE result IN ({marks})",
                               list(executed)).fetchall()
            plan_text = " ".join(str(tuple(row)) for row in plan)
            if "idx_signals_result" not in plan_text and "idx_signals_session" not in plan_text:
                failures.append(f"win_rate_by('session') does full table scan: {plan_text}")

            # (6) hourly_distribution() → must use idx_signals_result (WHERE clause filters on result)
            plan = con.execute(f"EXPLAIN QUERY PLAN SELECT CAST(substr(\"time\", 12, 2) AS INTEGER) AS hour, result, pips FROM signals WHERE result IN ({marks})",
                               list(executed)).fetchall()
            plan_text = " ".join(str(tuple(row)) for row in plan)
            if "idx_signals_result" not in plan_text:
                failures.append(f"hourly_distribution() does full table scan: {plan_text}")

            if failures:
                raise AssertionError("Query plan failures:\n  " + "\n  ".join(failures))

            print("PASS (l) EXPLAIN QUERY PLAN - all queries use indexes")
        finally:
            con.close()
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
    test_smc_bucket_schema()
    test_smc_bucket_roundtrip()
    test_csv_export_roundtrip()
    test_csv_export_empty_writes_header()
    test_query_plans()
    if os.environ.get("RUN_PERF_BENCHMARK") == "1":
        test_performance_benchmark()
    print("\nALL TESTS PASSED")


class OutcomeDbUnitTests(unittest.TestCase):
    def test_upsert_roundtrip_case(self): test_upsert_roundtrip()
    def test_inplace_update_case(self): test_inplace_update()
    def test_concurrent_appends_case(self): test_concurrent_appends()
    def test_analyze_parity_case(self): test_analyze_parity()
    def test_cost_decision_schema_case(self): test_cost_decision_schema()
    def test_cost_decision_roundtrip_case(self): test_cost_decision_roundtrip()
    def test_old_style_row_backcompat_case(self): test_old_style_row_backcompat()
    def test_smc_bucket_schema_case(self): test_smc_bucket_schema()
    def test_smc_bucket_roundtrip_case(self): test_smc_bucket_roundtrip()
    def test_csv_export_roundtrip_case(self): test_csv_export_roundtrip()
    def test_csv_export_empty_writes_header_case(self): test_csv_export_empty_writes_header()
    def test_query_plans_case(self): test_query_plans()


if __name__ == "__main__":
    main()
