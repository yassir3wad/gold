#!/usr/bin/env python3
"""Multi-day walk-forward backtesting framework.
Iterates over a date range, running single-day backtests for each day."""
import argparse, datetime as dt

def parse_date(s):
    """Parse YYYY-MM-DD string to date object."""
    try:
        return dt.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid date format '{s}': {e}")

def iter_days(start, end):
    """Yield each date from start to end (inclusive)."""
    current = start
    while current <= end:
        yield current
        current += dt.timedelta(days=1)

def main():
    parser = argparse.ArgumentParser(description="Multi-day walk-forward backtesting")
    parser.add_argument("--start-date", required=True, type=parse_date, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, type=parse_date, help="End date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Print dates without running backtests")
    args = parser.parse_args()

    if args.start_date > args.end_date:
        parser.error(f"start-date {args.start_date} is after end-date {args.end_date}")

    days = list(iter_days(args.start_date, args.end_date))
    print(f"Date range: {args.start_date} to {args.end_date} ({len(days)} days)")

    if args.dry_run:
        print("\nDry-run mode: iterating over dates...")
        for day in days:
            print(f"  {day}")
        print(f"\nTotal: {len(days)} days")
    else:
        print("\nBacktesting mode not yet implemented")
        for day in days:
            print(f"TODO: backtest {day}")

if __name__=="__main__":
    main()
