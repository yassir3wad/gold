#!/usr/bin/env python3
"""Refresh HTF zones for all instruments in instruments.json by calling refresh_zones.py
for each symbol. Run with --dry-run to preview without executing.
    python3 refresh_all_zones.py              # refresh all
    python3 refresh_all_zones.py --dry-run    # list what would be refreshed
"""
import subprocess, json, os, sys
TVDIR = os.path.expanduser("~/tradingview-mcp")
DRY_RUN = "--dry-run" in sys.argv

def main():
    try:
        instruments = json.load(open(os.path.join(TVDIR, "instruments.json")))
    except Exception as e:
        print(f"error reading instruments.json: {e}")
        return
    symbols = [k for k in instruments.keys() if not k.startswith("_")]
    if not symbols:
        print("no instruments found in instruments.json")
        return
    if DRY_RUN:
        print(f"would refresh {len(symbols)} instruments:")
        for sym in symbols:
            desc = instruments[sym].get('desc', '')
            print(f"  {sym:8} — {desc}")
        return
    print(f"refreshing {len(symbols)} instruments...")
    for idx, sym in enumerate(symbols, 1):
        desc = instruments[sym].get('desc', '')
        print(f"\n[{idx}/{len(symbols)}] {sym} — {desc}")
        try:
            result = subprocess.run(
                ["python3", os.path.join(TVDIR, "refresh_zones.py"), "--symbol", sym],
                cwd=TVDIR, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                print(f"  ✓ {result.stdout.strip()}")
            else:
                print(f"  ✗ failed (exit {result.returncode})")
                if result.stderr: print(f"     {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"  ✗ timeout after 60s")
        except Exception as e:
            print(f"  ✗ error: {e}")
    print(f"\ncompleted refresh for {len(symbols)} instruments")

if __name__ == "__main__":
    main()
