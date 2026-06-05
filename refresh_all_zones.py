#!/usr/bin/env python3
"""Refresh HTF zones for all instruments in instruments.json by calling refresh_zones.py
for each symbol. Run with --dry-run to preview without executing.
    python3 refresh_all_zones.py              # refresh all
    python3 refresh_all_zones.py --dry-run    # list what would be refreshed
    python3 refresh_all_zones.py --symbol XAUUSD  # refresh single symbol
"""
import subprocess, json, os, sys
TVDIR = os.path.expanduser("~/tradingview-mcp")
DRY_RUN = "--dry-run" in sys.argv
SINGLE_SYMBOL = None
if "--symbol" in sys.argv:
    idx = sys.argv.index("--symbol")
    if idx + 1 < len(sys.argv):
        SINGLE_SYMBOL = sys.argv[idx + 1]

def load_zones(symbol):
    """Load zones file for symbol, return None if not found"""
    try:
        with open(os.path.join(TVDIR, f"zones_{symbol.lower()}.json")) as f:
            return json.load(f)
    except:
        return None

def compare_zones(old_zones, new_zones):
    """Compare old and new zone files, return {added, removed, modified, unchanged}"""
    if not old_zones or not new_zones:
        return {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}
    old_r = {tuple(z[:2]): z[2] if len(z) > 2 else "" for z in old_zones.get("htf_r", [])}
    old_s = {tuple(z[:2]): z[2] if len(z) > 2 else "" for z in old_zones.get("htf_s", [])}
    new_r = {tuple(z[:2]): z[2] if len(z) > 2 else "" for z in new_zones.get("htf_r", [])}
    new_s = {tuple(z[:2]): z[2] if len(z) > 2 else "" for z in new_zones.get("htf_s", [])}
    old_all = {**old_r, **old_s}
    new_all = {**new_r, **new_s}
    old_keys = set(old_all.keys())
    new_keys = set(new_all.keys())
    added = len(new_keys - old_keys)
    removed = len(old_keys - new_keys)
    common = old_keys & new_keys
    modified = sum(1 for k in common if old_all[k] != new_all[k])
    unchanged = len(common) - modified
    return {"added": added, "removed": removed, "modified": modified, "unchanged": unchanged}

def main():
    try:
        instruments = json.load(open(os.path.join(TVDIR, "instruments.json")))
    except Exception as e:
        print(f"error reading instruments.json: {e}")
        return
    symbols = [k for k in instruments.keys() if not k.startswith("_")]
    if SINGLE_SYMBOL:
        if SINGLE_SYMBOL not in symbols:
            print(f"error: symbol {SINGLE_SYMBOL} not found in instruments.json")
            return
        symbols = [SINGLE_SYMBOL]
    if not symbols:
        print("no instruments found in instruments.json")
        return
    if DRY_RUN:
        print(f"would refresh {len(symbols)} instrument{'s' if len(symbols) != 1 else ''}:")
        for sym in symbols:
            desc = instruments[sym].get('desc', '')
            old_zones = load_zones(sym)
            status = "no changes" if old_zones else "new zones file"
            print(f"  {sym:8} — {desc} ({status})")
        return
    print(f"refreshing {len(symbols)} instrument{'s' if len(symbols) != 1 else ''}...")
    total_changes = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}
    for idx, sym in enumerate(symbols, 1):
        desc = instruments[sym].get('desc', '')
        print(f"\n[{idx}/{len(symbols)}] {sym} — {desc}")
        old_zones = load_zones(sym)
        try:
            result = subprocess.run(
                ["python3", os.path.join(TVDIR, "refresh_zones.py"), "--symbol", sym],
                cwd=TVDIR, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                new_zones = load_zones(sym)
                diff = compare_zones(old_zones, new_zones)
                for k in diff:
                    total_changes[k] += diff[k]
                if diff["added"] + diff["removed"] + diff["modified"] == 0:
                    print(f"  ✓ no changes")
                else:
                    change_parts = []
                    if diff["added"]: change_parts.append(f"+{diff['added']}")
                    if diff["removed"]: change_parts.append(f"-{diff['removed']}")
                    if diff["modified"]: change_parts.append(f"~{diff['modified']}")
                    print(f"  ✓ zones changed: {' '.join(change_parts)}")
            else:
                print(f"  ✗ failed (exit {result.returncode})")
                if result.stderr: print(f"     {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"  ✗ timeout after 60s")
        except Exception as e:
            print(f"  ✗ error: {e}")
    if len(symbols) > 1:
        print(f"\ncompleted refresh for {len(symbols)} instruments")
        if total_changes["added"] + total_changes["removed"] + total_changes["modified"] > 0:
            print(f"total changes: +{total_changes['added']} -{total_changes['removed']} ~{total_changes['modified']}")
        else:
            print("no changes detected")

if __name__ == "__main__":
    main()
