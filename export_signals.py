#!/usr/bin/env python3
"""Export signals from the SQLite outcomes database to CSV format.

Provides backward compatibility for external tools and backtesting scripts that expect CSV input.
The output format matches the original signal_log.csv schema (SIG_COLS), with optional context
columns when --full is specified.

USAGE:
    # Export all signals to CSV
    python3 export_signals.py --output signals.csv

    # Export signals for a specific symbol
    python3 export_signals.py --output gold.csv --symbol XAUUSD

    # Export signals since a specific date
    python3 export_signals.py --output recent.csv --since 2025-06-01

    # Export with full context columns (rsi, er, regime, etc.)
    python3 export_signals.py --output full.csv --full

    # Use custom database path
    python3 export_signals.py --db /path/to/outcomes.db --output signals.csv

CLI FLAGS:
    --output FILE.csv       Output CSV file path (required)
    --db PATH               Database file path (default: ~/tradingview-mcp/outcomes.db)
    --symbol SYM            Filter by symbol (e.g., XAUUSD, ES1!, NQ1!)
    --since YYYY-MM-DD      Filter signals at/after this date
    --full                  Include all context columns (rsi, er, regime, etc.)
    --count                 Print row count without exporting

OUTPUT FORMAT:
    Default columns (matches signal_log.csv schema):
        id, time, side, grade, confidence, pattern, entry, sl, tp1,
        rng10, body_p, htf, result, exit, pips

    Full mode (--full) adds context columns:
        rsi, er, regime, room, session, symbol,
        spread_pips, slippage_pips, commission_pips, gross_pips, net_pips,
        decision_source, decision_reason_code,
        smc_zone, smc_aligned, smc_age

NOTES:
    - Output is sorted newest-first (same as outcome_db.rows())
    - Empty/None values are exported as empty strings
    - All values are exported as text (matching CSV format)
"""
import sys, os, csv as _csv, argparse

import outcome_db


def export_signals(output_path, db=outcome_db.DEFAULT_DB, symbol=None, since=None, full=False):
    """Export signals from SQLite to CSV file.

    Returns (rows_exported, file_path).
    """
    # Fetch rows from database
    rows = outcome_db.rows(symbol=symbol, since=since, db=db)

    # Determine columns to export
    if full:
        cols = outcome_db.ALL_COLS
    else:
        cols = outcome_db.SIG_COLS

    # Write CSV
    try:
        with open(output_path, 'w', newline='') as f:
            writer = _csv.writer(f)

            # Write header
            writer.writerow(cols)

            # Write data rows
            written = 0
            for row in rows:
                values = [row.get(c, "") for c in cols]
                writer.writerow(values)
                written += 1

        if written == 0:
            print("No signals found matching filters; wrote header-only CSV", file=sys.stderr)
        return written, output_path

    except Exception as e:
        print(f"Error writing CSV: {e}", file=sys.stderr)
        raise


def count_signals(db=outcome_db.DEFAULT_DB, symbol=None, since=None):
    """Count signals matching filters without exporting.

    Returns (count, filters_description).
    """
    rows = outcome_db.rows(symbol=symbol, since=since, db=db)
    filters = []
    if symbol:
        filters.append(f"symbol={symbol}")
    if since:
        filters.append(f"since={since}")

    filters_desc = ", ".join(filters) if filters else "all signals"
    return len(rows), filters_desc


def main():
    parser = argparse.ArgumentParser(
        description="Export signals from SQLite outcomes database to CSV format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 export_signals.py --output signals.csv
  python3 export_signals.py --output gold.csv --symbol XAUUSD
  python3 export_signals.py --output recent.csv --since 2025-06-01
  python3 export_signals.py --output full.csv --full
  python3 export_signals.py --count --symbol XAUUSD
        """
    )

    parser.add_argument("--output", type=str, help="Output CSV file path (required unless --count)")
    parser.add_argument("--db", type=str, default=outcome_db.DEFAULT_DB,
                        help=f"Database file path (default: {outcome_db.DEFAULT_DB})")
    parser.add_argument("--symbol", type=str, help="Filter by symbol (e.g., XAUUSD, ES1!)")
    parser.add_argument("--since", type=str, help="Filter signals at/after date (YYYY-MM-DD)")
    parser.add_argument("--full", action="store_true",
                        help="Include all context columns (rsi, er, regime, etc.)")
    parser.add_argument("--count", action="store_true",
                        help="Print row count without exporting")

    args = parser.parse_args()

    # Expand database path
    db = os.path.expanduser(args.db)

    # Check database exists
    if not os.path.exists(db):
        print(f"Error: Database not found: {db}", file=sys.stderr)
        print(f"Run 'python3 outcome_db.py --init' to create it", file=sys.stderr)
        sys.exit(1)

    # Count mode
    if args.count:
        count, filters_desc = count_signals(db=db, symbol=args.symbol, since=args.since)
        print(f"{count} signals in {db} ({filters_desc})")
        sys.exit(0)

    # Export mode - require output path
    if not args.output:
        parser.error("--output is required (or use --count to just count rows)")

    # Export signals
    count, path = export_signals(
        args.output,
        db=db,
        symbol=args.symbol,
        since=args.since,
        full=args.full
    )

    # Report result
    filters = []
    if args.symbol:
        filters.append(f"symbol={args.symbol}")
    if args.since:
        filters.append(f"since={args.since}")

    filters_desc = f" ({', '.join(filters)})" if filters else ""
    cols_desc = "full" if args.full else "standard"

    print(f"Exported {count} signals{filters_desc} to {path} ({cols_desc} columns)")


if __name__ == "__main__":
    main()
