#!/usr/bin/env python3
"""Refresh HTF zones for all instruments in instruments.json by calling refresh_zones.py
for each symbol. Run with --dry-run to preview without executing.
    python3 refresh_all_zones.py              # refresh all
    python3 refresh_all_zones.py --dry-run    # list what would be refreshed
    python3 refresh_all_zones.py --symbol XAUUSD  # refresh single symbol
    python3 refresh_all_zones.py --notify     # send Telegram notification after refresh
"""
import subprocess, json, os, sys, logging
from logging.handlers import RotatingFileHandler
import telegram_notify

# --- Logging Setup ---
LOG_FILE = os.path.expanduser("~/tradingview-mcp/logs/zone_scheduler.log")

def setup_logging():
    """Configure logging to both console and file with rotation."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    log_format = '[%(asctime)s] %(levelname)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))

    # File handler with rotation (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

TVDIR = os.path.expanduser("~/tradingview-mcp")
DRY_RUN = "--dry-run" in sys.argv
NOTIFY = "--notify" in sys.argv
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
    setup_logging()

    try:
        instruments = json.load(open(os.path.join(TVDIR, "instruments.json")))
    except Exception as e:
        logging.error(f"error reading instruments.json: {e}")
        return
    symbols = [k for k in instruments.keys() if not k.startswith("_")]
    if SINGLE_SYMBOL:
        if SINGLE_SYMBOL not in symbols:
            logging.error(f"symbol {SINGLE_SYMBOL} not found in instruments.json")
            return
        symbols = [SINGLE_SYMBOL]
    if not symbols:
        logging.warning("no instruments found in instruments.json")
        return
    if DRY_RUN:
        logging.info(f"would refresh {len(symbols)} instrument{'s' if len(symbols) != 1 else ''}:")
        for sym in symbols:
            desc = instruments[sym].get('desc', '')
            old_zones = load_zones(sym)
            status = "no changes" if old_zones else "new zones file"
            logging.info(f"  {sym:8} — {desc} ({status})")
        if NOTIFY:
            # In dry-run mode with notify, show what notification would be sent
            telegram_notify.send_alert("🔄 Zones Refreshed", "Dry run mode - no actual refresh", dry_run=True)
        return
    logging.info(f"refreshing {len(symbols)} instrument{'s' if len(symbols) != 1 else ''}...")
    total_changes = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}
    changes_by_symbol = {}
    for idx, sym in enumerate(symbols, 1):
        desc = instruments[sym].get('desc', '')
        logging.info(f"[{idx}/{len(symbols)}] {sym} — {desc}")
        old_zones = load_zones(sym)
        try:
            result = subprocess.run(
                ["python3", os.path.join(TVDIR, "refresh_zones.py"), "--symbol", sym],
                cwd=TVDIR, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                new_zones = load_zones(sym)
                diff = compare_zones(old_zones, new_zones)
                changes_by_symbol[sym] = diff
                for k in diff:
                    total_changes[k] += diff[k]
                if diff["added"] + diff["removed"] + diff["modified"] == 0:
                    logging.info(f"  ✓ no changes")
                else:
                    change_parts = []
                    if diff["added"]: change_parts.append(f"+{diff['added']}")
                    if diff["removed"]: change_parts.append(f"-{diff['removed']}")
                    if diff["modified"]: change_parts.append(f"~{diff['modified']}")
                    logging.info(f"  ✓ zones changed: {' '.join(change_parts)}")
            else:
                logging.error(f"  ✗ failed (exit {result.returncode})")
                if result.stderr: logging.error(f"     {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            logging.error(f"  ✗ timeout after 60s")
        except Exception as e:
            logging.error(f"  ✗ error: {e}")
    if len(symbols) > 1:
        logging.info(f"completed refresh for {len(symbols)} instruments")
        if total_changes["added"] + total_changes["removed"] + total_changes["modified"] > 0:
            logging.info(f"total changes: +{total_changes['added']} -{total_changes['removed']} ~{total_changes['modified']}")
        else:
            logging.info("no changes detected")

    # Send Telegram notification if requested
    if NOTIFY and changes_by_symbol:
        summary = telegram_notify.format_zone_summary(changes_by_symbol)
        telegram_notify.send_alert("🔄 Zones Refreshed", summary, dry_run=False)

if __name__ == "__main__":
    main()
