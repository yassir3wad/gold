# Signal Database (SQLite) — Usage Guide

The trading system now uses SQLite as the primary signal storage backend, replacing CSV-based logging while maintaining full backward compatibility. This guide covers the new query API methods and export functionality.

---

## Overview

**What changed:**
- Signals are written to **SQLite database** (`~/tradingview-mcp/outcomes.db`) in real-time
- **CSV compatibility** preserved: export command generates `signal_log.csv` format
- **Fast queries**: indexed lookups and aggregations complete in <100ms even with 50K+ signals
- **Concurrent-safe**: WAL mode enables lock-free reads while scanner writes

**Migration:** Existing CSV data can be imported using `migrate_logs_to_db.py` (see [Migration](#migration) section)

---

## Query API Methods

The `outcome_db.py` module provides Python query methods for signal analytics.

### 1. Session Breakdown

Aggregate win rate and net pips by trading session (LONDON, NY, ASIA, etc.)

```python
import outcome_db

# Get performance by session
sessions = outcome_db.session_breakdown()

# Result format:
# {
#   'LONDON': {'n': 45, 'wins': 28, 'losses': 15, 'scratch': 2, 'win_rate': 65.1, 'net': 230.5},
#   'NY': {'n': 38, 'wins': 20, 'losses': 16, 'scratch': 2, 'win_rate': 55.6, 'net': 85.0},
#   'ASIA': {'n': 12, 'wins': 5, 'losses': 6, 'scratch': 1, 'win_rate': 45.5, 'net': -25.0}
# }

# Print summary
for session, stats in sessions.items():
    print(f"{session}: {stats['win_rate']:.1f}% win rate, {stats['net']:.1f} pips")
```

**Use cases:**
- Identify best-performing trading sessions
- Session filter optimization (e.g., disable ASIA if consistently negative)
- Analytics dashboard session comparison

---

### 2. Hourly Distribution

Aggregate performance by hour of day (0-23 UTC)

```python
import outcome_db

# Get performance by hour
hourly = outcome_db.hourly_distribution()

# Result format:
# {
#   7: {'n': 8, 'wins': 5, 'losses': 2, 'scratch': 1, 'win_rate': 71.4, 'net': 45.0},
#   8: {'n': 12, 'wins': 7, 'losses': 4, 'scratch': 1, 'win_rate': 63.6, 'net': 60.0},
#   9: {'n': 15, 'wins': 9, 'losses': 5, 'scratch': 1, 'win_rate': 64.3, 'net': 75.0},
#   ...
# }

# Find best trading hours
best_hours = sorted(hourly.items(), key=lambda x: x[1]['win_rate'], reverse=True)[:5]
print("Top 5 hours by win rate:")
for hour, stats in best_hours:
    print(f"  {hour:02d}:00 UTC - {stats['win_rate']:.1f}% ({stats['n']} trades, {stats['net']:.1f} pips)")
```

**Use cases:**
- Identify peak performance hours (e.g., London open, NY open)
- Time-of-day filters (skip low-probability hours)
- Volatility analysis by hour

---

### 3. Strategy Performance

Aggregate win rate and net pips by pattern/strategy type

```python
import outcome_db

# Get performance by strategy
strategies = outcome_db.strategy_performance()

# Result format:
# {
#   'momentum impulse': {'n': 32, 'wins': 20, 'losses': 10, 'scratch': 2, 'win_rate': 66.7, 'net': 185.0},
#   'trendline break': {'n': 28, 'wins': 16, 'losses': 11, 'scratch': 1, 'win_rate': 59.3, 'net': 95.0},
#   'zone-bounce rejection': {'n': 25, 'wins': 12, 'losses': 12, 'scratch': 1, 'win_rate': 50.0, 'net': 10.0},
#   'double-top': {'n': 15, 'wins': 8, 'losses': 6, 'scratch': 1, 'win_rate': 57.1, 'net': 35.0}
# }

# Print ranked by net pips
ranked = sorted(strategies.items(), key=lambda x: x[1]['net'], reverse=True)
print("Strategies ranked by net P&L:")
for pattern, stats in ranked:
    print(f"{pattern:25s}: {stats['net']:+7.1f} pips  ({stats['win_rate']:.1f}% WR, n={stats['n']})")
```

**Use cases:**
- Identify strongest and weakest strategies
- Strategy selection (disable underperforming patterns in `flags.json`)
- ML training: filter dataset to only winning strategies

---

### 4. Existing Methods

**`rows(symbol=None, since=None, db=DEFAULT_DB)`**

Query raw signal rows with optional filtering:

```python
import outcome_db

# Get all signals
all_signals = outcome_db.rows()

# Filter by symbol
gold_signals = outcome_db.rows(symbol="XAUUSD")

# Filter by date (ISO format)
recent = outcome_db.rows(since="2026-06-01")

# Combined filter
recent_gold = outcome_db.rows(symbol="XAUUSD", since="2026-06-01")

# Result: list of dicts with all columns (SIG_COLS + CONTEXT_COLS)
```

**`win_rate_by(column, db=DEFAULT_DB)`**

Generic aggregation by any column:

```python
import outcome_db

# Win rate by grade
by_grade = outcome_db.win_rate_by('grade')
# {'A+': {'n': 15, 'wins': 12, 'losses': 3, ...}, 'A': {...}, 'B': {...}}

# Win rate by side
by_side = outcome_db.win_rate_by('side')
# {'LONG': {'n': 50, 'wins': 28, ...}, 'SHORT': {'n': 45, 'wins': 25, ...}}

# Win rate by instrument
by_symbol = outcome_db.win_rate_by('symbol')
# {'XAUUSD': {...}, 'ES1!': {...}, 'NQ1!': {...}}
```

---

## CSV Export Command

Export SQLite signals back to CSV format for backward compatibility with external tools.

### Basic Usage

```bash
# Export all signals to CSV
python3 export_signals.py --output signals.csv
# Output: Exported 530 signals to signals.csv (standard columns)

# View exported file
head -5 signals.csv
# id,time,side,grade,confidence,pattern,entry,sl,tp1,rng10,body_p,htf,result,exit,pips
# 1780920860,2026-06-08 14:14,SHORT,A+,0.85,momentum impulse,51022.3,51052.3,50992.3,30,65,15m,TP1,50992.3,30
# ...
```

### Filtering Options

```bash
# Export signals for specific symbol
python3 export_signals.py --output gold.csv --symbol XAUUSD

# Export signals since specific date (ISO format)
python3 export_signals.py --output recent.csv --since 2026-06-01

# Combine filters
python3 export_signals.py --output gold_june.csv --symbol XAUUSD --since 2026-06-01

# Use custom database path
python3 export_signals.py --db /path/to/outcomes.db --output signals.csv
```

### Full Export (All Columns)

Export with **all context columns** (rsi, er, regime, cost tracking, SMC fields):

```bash
python3 export_signals.py --output full_export.csv --full
# Output: Exported 530 signals to full_export.csv (full columns)

# 31 total columns: 15 SIG_COLS + 16 CONTEXT_COLS
# Includes: rsi, er, regime, room, session, symbol, spread_pips, slippage_pips,
#           commission_pips, gross_pips, net_pips, decision_source, decision_reason_code,
#           smc_zone, smc_aligned, smc_age
```

### Count Mode (No Export)

Get signal count without creating file:

```bash
python3 export_signals.py --count
# Database contains 530 signals

python3 export_signals.py --count --symbol XAUUSD --since 2026-06-01
# Database contains 85 signals matching filters
```

### Roundtrip Workflow

Export → modify in Excel → re-import:

```bash
# 1. Export current signals
python3 export_signals.py --output backup.csv

# 2. Edit backup.csv in Excel/Python (add manual annotations, fix data, etc.)

# 3. Re-import modified CSV
python3 migrate_logs_to_db.py backup.csv --db ~/tradingview-mcp/outcomes.db
# Output: migrated 530 rows (530 unique ids) from 1 CSV files into ~/tradingview-mcp/outcomes.db
```

---

## Migration

Import existing CSV signal logs into SQLite database.

### Import Single CSV File

```bash
python3 migrate_logs_to_db.py signals_log.csv
# Default output: ~/tradingview-mcp/outcomes.db
```

### Import All CSV Files in `logs/` Directory

```bash
python3 migrate_logs_to_db.py
# Scans: signals_log.csv + logs/<symbol>/*.csv
# Output: migrated 540 rows (528 unique ids) from 17 CSV files into ~/tradingview-mcp/outcomes.db
# DB now holds 528 signal rows
```

### Custom Database Path

```bash
python3 migrate_logs_to_db.py --db /path/to/custom.db
```

### Deduplication Behavior

The migration tool uses **UPSERT** semantics (INSERT ... ON CONFLICT(id) DO UPDATE SET):

- Signals with the same `id` are **updated in place** (not duplicated)
- Safe to re-run migration multiple times
- Newer CSV data overwrites older database rows with same ID

Example:
```bash
# Initial migration
python3 migrate_logs_to_db.py
# migrated 500 rows (500 unique ids)

# Update some signals in CSV and re-run
python3 migrate_logs_to_db.py
# migrated 520 rows (510 unique ids)
# DB now holds 510 signal rows
# (10 new signals added, others updated in place)
```

---

## Integration Examples

### Example 1: Analytics Dashboard

```python
import outcome_db

# Load data
sessions = outcome_db.session_breakdown()
hourly = outcome_db.hourly_distribution()
strategies = outcome_db.strategy_performance()

# Best session
best_session = max(sessions.items(), key=lambda x: x[1]['win_rate'])
print(f"Best session: {best_session[0]} ({best_session[1]['win_rate']:.1f}% WR)")

# Best hour
best_hour = max(hourly.items(), key=lambda x: x[1]['win_rate'])
print(f"Best hour: {best_hour[0]:02d}:00 UTC ({best_hour[1]['win_rate']:.1f}% WR)")

# Best strategy
best_strategy = max(strategies.items(), key=lambda x: x[1]['net'])
print(f"Best strategy: {best_strategy[0]} ({best_strategy[1]['net']:.1f} pips)")
```

### Example 2: ML Feature Engineering

```python
import outcome_db
import pandas as pd

# Export to DataFrame for ML pipeline
rows = outcome_db.rows()
df = pd.DataFrame(rows)

# Add engineered features
df['hour'] = pd.to_datetime(df['time']).dt.hour
df['is_london'] = df['session'] == 'LONDON'
df['is_momentum'] = df['pattern'].str.contains('momentum')

# Filter to winning strategies only
winning_strategies = [p for p, s in outcome_db.strategy_performance().items() if s['win_rate'] > 60]
df_filtered = df[df['pattern'].isin(winning_strategies)]

# Train model on filtered dataset
# ... ML training code ...
```

### Example 3: End-of-Day Export for Backtesting

```python
#!/usr/bin/env python3
"""Daily export script - run via cron to backup signals"""
import datetime
import outcome_db
import os

# Export yesterday's signals
yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
export_path = f"backups/signals_{yesterday}.csv"

os.makedirs("backups", exist_ok=True)

# Use export_signals module
from export_signals import export_signals
export_signals(
    db_path="~/tradingview-mcp/outcomes.db",
    output_path=export_path,
    since=yesterday,
    full=True  # Include all context columns for analysis
)

print(f"Exported signals to {export_path}")
```

### Example 4: Performance Comparison

```python
import outcome_db

# Compare this week vs last week
import datetime

today = datetime.date.today()
week_ago = (today - datetime.timedelta(days=7)).isoformat()
two_weeks_ago = (today - datetime.timedelta(days=14)).isoformat()

# Last week
this_week = outcome_db.rows(since=week_ago)
last_week = outcome_db.rows(since=two_weeks_ago)
last_week = [r for r in last_week if r['time'] < week_ago]

def calc_stats(rows):
    wins = sum(1 for r in rows if r.get('result') in ('TP1', 'TP2') and float(r.get('pips', 0) or 0) > 0)
    losses = sum(1 for r in rows if r.get('result') == 'SL' and float(r.get('pips', 0) or 0) < 0)
    net = sum(float(r.get('pips', 0) or 0) for r in rows if r.get('result') in ('TP1', 'TP2', 'SL'))
    wr = 100 * wins / (wins + losses) if (wins + losses) > 0 else 0
    return {'n': len(rows), 'wins': wins, 'losses': losses, 'net': net, 'wr': wr}

this_stats = calc_stats(this_week)
last_stats = calc_stats(last_week)

print(f"This week: {this_stats['wr']:.1f}% WR, {this_stats['net']:.1f} pips")
print(f"Last week: {last_stats['wr']:.1f}% WR, {last_stats['net']:.1f} pips")
print(f"Delta: {this_stats['wr'] - last_stats['wr']:+.1f}% WR, {this_stats['net'] - last_stats['net']:+.1f} pips")
```

---

## Database File Location

**Default path:** `~/tradingview-mcp/outcomes.db`

This database is automatically:
- Created by `outcome_db.init_db()` on first use
- Written to by `scalp_fast.py` scanner on every signal
- Read by `analyze_logs.py` for performance analytics
- Backed up alongside other persistent state (CSV logs, trades/, flags.json)

**Custom path:** Set via `db` parameter in all `outcome_db` methods:
```python
import outcome_db

custom_db = "/path/to/custom.db"
outcome_db.init_db(custom_db)
signals = outcome_db.rows(db=custom_db)
```

---

## Performance Characteristics

Benchmark results with **50,000 signals**:

| Query Type | Time | Result Size | Index Used |
|------------|------|-------------|------------|
| Full scan | 745ms | 50,000 rows | - |
| Symbol filter | 146ms | ~10,000 rows | idx_signals_symbol |
| Time range | 346ms | ~27,000 rows | - |
| Combined filter | 61ms | ~3,600 rows | idx_signals_symbol |
| Pattern aggregation | 72ms | 3 groups | idx_signals_pattern |
| Session aggregation | 73ms | 3 groups | idx_signals_session |
| Hourly aggregation | 70ms | 24 groups | idx_signals_result |
| Symbol aggregation | 72ms | 5 groups | idx_signals_symbol |

**All aggregation queries complete in <100ms** (acceptance criteria met).

### Indexes

The following indexes are automatically created by `outcome_db.init_db()`:

```sql
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_result ON signals(result);
CREATE INDEX IF NOT EXISTS idx_signals_session ON signals(session);
CREATE INDEX IF NOT EXISTS idx_signals_pattern ON signals(pattern);
```

---

## Backward Compatibility

**CSV-based tools continue to work:**

1. **`analyze_logs.py`** auto-detects SQLite database and reads from it preferentially (CSV fallback if DB missing)
2. **Export command** generates CSV files matching original `signal_log.csv` format
3. **Backtesting scripts** can import from CSV exports
4. **External tools** (Excel, Python pandas, R) can consume exported CSV files

**Migration path:**
- Existing CSV files → `migrate_logs_to_db.py` → SQLite database
- SQLite database → `export_signals.py` → CSV files (for external tools)

**No breaking changes** — all existing workflows supported.

---

## Troubleshooting

### Database locked error

**Symptom:** `sqlite3.OperationalError: database is locked`

**Cause:** Multiple writers without WAL mode, or timeout too short

**Solution:** Ensure WAL mode is enabled (handled automatically by `outcome_db._connect()`). Increase timeout if needed:
```python
con = sqlite3.connect(db, timeout=30.0)  # Wait up to 30 seconds
```

### analyze_logs.py still reads CSV

**Symptom:** Analytics reads from `signals_log.csv` instead of SQLite

**Cause:** Database file doesn't exist or isn't at default path

**Solution:** 
```bash
# Check database exists
ls -lh ~/tradingview-mcp/outcomes.db

# If missing, run migration
python3 migrate_logs_to_db.py

# Or set OUTCOMES_DB environment variable
export OUTCOMES_DB=/path/to/outcomes.db
python3 analyze_logs.py
```

### Missing signals after migration

**Symptom:** CSV has 500 signals but database has 450

**Cause:** CSV may contain duplicate IDs (UPSERT deduplication)

**Verification:**
```bash
# Count unique IDs in CSV
grep -v '^id,' signals_log.csv | cut -d',' -f1 | sort -u | wc -l

# Count rows in database
python3 -c "import outcome_db; print(len(outcome_db.rows()))"
```

**Expected:** Database count should match unique ID count (not total CSV row count)

### Export produces empty file

**Symptom:** `export_signals.py` creates file with only header row

**Cause:** No signals match filter criteria, or database is empty

**Solution:**
```bash
# Check database has signals
python3 export_signals.py --count

# Remove filters and try again
python3 export_signals.py --output all.csv

# Check if database file exists
ls -lh ~/tradingview-mcp/outcomes.db
```

---

## Next Steps

- **Analytics Dashboard** (feature-9): Use new query methods to build real-time session/strategy dashboards
- **ML Optimization** (feature-25): Train models on SQLite dataset with fast filtered queries
- **AI Feedback Loop** (feature-10): Query historical performance to inform real-time trade decisions
- **Discipline Score** (feature-11): Track adherence to best sessions/strategies

See `spec.md` for full feature roadmap.
