#!/usr/bin/env python3
"""Check zone file freshness and warn if stale (>6 hours old by default).
Reads zone files (zones_*.json) and compares their timestamps to the current time.
Usage:
    python3 check_zone_health.py                 # default 6 hour threshold
    python3 check_zone_health.py --max-age 4     # custom 4 hour threshold
"""
import json, os, sys, time
from datetime import datetime, timedelta

TVDIR = os.path.expanduser("~/tradingview-mcp")

# Default max age in hours before a zone is considered stale
MAX_AGE_HOURS = 6

# Parse command line arguments
if "--max-age" in sys.argv:
    try:
        MAX_AGE_HOURS = float(sys.argv[sys.argv.index("--max-age") + 1])
    except (IndexError, ValueError):
        print("Error: --max-age requires a numeric value")
        sys.exit(1)

def check_zone_health():
    """Check all zone files and report their freshness."""
    # Load instruments configuration
    instruments = []
    try:
        inst_data = json.load(open(os.path.join(TVDIR, "instruments.json")))
        instruments = [k for k in inst_data.keys() if not k.startswith("_")]
    except Exception as e:
        print(f"Error loading instruments.json: {e}")
        sys.exit(1)

    if not instruments:
        print("No instruments found in instruments.json")
        sys.exit(1)

    current_time = time.time()
    max_age_seconds = MAX_AGE_HOURS * 3600
    stale_count = 0
    fresh_count = 0
    missing_count = 0

    results = []

    for symbol in instruments:
        zone_file = os.path.join(TVDIR, f"zones_{symbol.lower()}.json")

        if not os.path.exists(zone_file):
            missing_count += 1
            results.append({
                "symbol": symbol,
                "status": "missing",
                "file": zone_file
            })
            continue

        try:
            with open(zone_file, 'r') as f:
                zone_data = json.load(f)

            zone_ts = zone_data.get("ts")
            if zone_ts is None:
                results.append({
                    "symbol": symbol,
                    "status": "error",
                    "message": "No timestamp field"
                })
                continue

            age_seconds = current_time - zone_ts
            age_hours = age_seconds / 3600

            if age_seconds > max_age_seconds:
                stale_count += 1
                status = "stale"
            else:
                fresh_count += 1
                status = "fresh"

            zone_time = datetime.fromtimestamp(zone_ts)

            results.append({
                "symbol": symbol,
                "status": status,
                "age_hours": round(age_hours, 1),
                "last_update": zone_time.strftime("%Y-%m-%d %H:%M:%S"),
                "file": zone_file
            })

        except json.JSONDecodeError as e:
            results.append({
                "symbol": symbol,
                "status": "error",
                "message": f"Invalid JSON: {e}"
            })
        except Exception as e:
            results.append({
                "symbol": symbol,
                "status": "error",
                "message": str(e)
            })

    # Print results
    print(f"Zone Health Check (max age: {MAX_AGE_HOURS}h)")
    print("=" * 70)

    for r in results:
        symbol = r["symbol"]
        status = r["status"]

        if status == "fresh":
            print(f"✓ {symbol:7s} - fresh ({r['age_hours']}h old, updated {r['last_update']})")
        elif status == "stale":
            print(f"⚠ {symbol:7s} - STALE ({r['age_hours']}h old, updated {r['last_update']})")
        elif status == "missing":
            print(f"✗ {symbol:7s} - MISSING (file not found)")
        elif status == "error":
            print(f"✗ {symbol:7s} - ERROR ({r.get('message', 'unknown')})")

    print("=" * 70)
    print(f"Summary: {fresh_count} fresh, {stale_count} stale, {missing_count} missing")

    if stale_count > 0:
        print(f"\n⚠ WARNING: {stale_count} zone file(s) are stale (>{MAX_AGE_HOURS}h old)")
        print("Run refresh_zones.py or zone_scheduler.py to update zones")
        sys.exit(1)
    elif missing_count > 0:
        print(f"\n⚠ WARNING: {missing_count} zone file(s) are missing")
        sys.exit(1)
    else:
        print("\n✓ All zone files are fresh")
        sys.exit(0)

if __name__ == "__main__":
    check_zone_health()
