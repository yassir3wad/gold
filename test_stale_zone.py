#!/usr/bin/env python3
"""Test stale zone detection by temporarily modifying a zone file"""
import json
import time
import shutil
import subprocess
import sys

def main():
    # Backup original
    shutil.copy('zones_xauusd.json', 'zones_xauusd.json.backup')

    try:
        # Load and modify zone file to be 8 hours old
        with open('zones_xauusd.json', 'r') as f:
            zones = json.load(f)

        stale_ts = time.time() - (8 * 3600)  # 8 hours ago
        zones['ts'] = stale_ts

        with open('zones_xauusd.json', 'w') as f:
            json.dump(zones, f, indent=1)

        # Run health check with 6-hour threshold
        result = subprocess.run(['python3', 'check_zone_health.py', '--max-age', '6'],
                              capture_output=True, text=True)

        # Check if stale was detected
        if 'stale' in result.stdout.lower():
            print("✓ PASS: Stale zone detected correctly (8h old vs 6h threshold)")
            exit_code = 0
        else:
            print("✗ FAIL: Stale zone not detected")
            print("Output:", result.stdout)
            exit_code = 1

    finally:
        # Restore original
        shutil.move('zones_xauusd.json.backup', 'zones_xauusd.json')

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
