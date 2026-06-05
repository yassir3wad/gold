#!/usr/bin/env python3
"""
Migration script for existing scanner deployments.

Scans for legacy ~/.tv_fast_* files and imports them into the consolidated StateManager.
Supports --dry-run and --backup flags for safe migration.

Usage:
    python3 scripts/migrate_state.py                    # Run migration
    python3 scripts/migrate_state.py --dry-run          # Preview migration without applying
    python3 scripts/migrate_state.py --backup           # Backup old files before migration
    python3 scripts/migrate_state.py --dry-run --backup # Preview with backup plan
"""
import argparse
import json
import os
import sys
import time
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add src to path for StateManager import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from state_manager import StateManager, DEFAULT_STATE_FILE

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Legacy file patterns
LEGACY_PATTERNS = [
    "~/.tv_fast_*_trade.json",    # Per-symbol trade state
    "~/.tv_fast_*_cd.json",       # Per-symbol cooldown
    "~/.tv_fast_*_skip.json",     # Per-symbol skip/watch state
    "~/.tv_fast_*_tg.json",       # Per-symbol telegram state
    "~/.tv_fast_*_vp.json",       # Per-symbol volume profile
    "~/.tv_fast_trade.json",      # Global trade state
    "~/.tv_fast_cd.json",         # Global cooldown
    "~/.tv_fast_watch.json",      # Global watch state
    "~/.tv_fast_tg.json",         # Global telegram state
    "~/.tv_fast_vp.json",         # Global volume profile
]

# Common symbol list for scanner
SYMBOLS = ["XAUUSD", "GBPUSD", "NAS100", "US30", "EURUSD", "USDJPY", "AUDUSD"]


def find_legacy_files() -> List[str]:
    """
    Find all legacy state files matching known patterns.

    Returns:
        List of absolute file paths
    """
    home = os.path.expanduser("~")
    files = []

    # Find all .tv_fast_* files
    for item in os.listdir(home):
        if item.startswith(".tv_fast_") and item.endswith(".json"):
            file_path = os.path.join(home, item)
            if os.path.isfile(file_path):
                files.append(file_path)

    return sorted(files)


def parse_legacy_filename(filename: str) -> Tuple[Optional[str], str]:
    """
    Parse legacy filename to extract symbol and state type.

    Args:
        filename: Legacy filename (e.g., '.tv_fast_xauusd_trade.json')

    Returns:
        Tuple of (symbol, kind) where symbol can be None for global files
        kind is one of: 'trade', 'cd', 'skip', 'tg', 'vp', 'watch'
    """
    basename = os.path.basename(filename)
    # Remove .tv_fast_ prefix and .json suffix
    name = basename.replace(".tv_fast_", "").replace(".json", "")

    # Check for per-symbol files (format: symbol_kind)
    parts = name.split("_")
    if len(parts) >= 2:
        # Last part is the kind, rest is symbol
        kind = parts[-1]
        symbol = "_".join(parts[:-1]).upper()
        return symbol, kind
    else:
        # Global file (format: kind)
        return None, name


def load_legacy_file(file_path: str) -> Optional[Dict]:
    """
    Load and validate legacy state file.

    Args:
        file_path: Path to legacy file

    Returns:
        Loaded JSON data or None if file is invalid/corrupted
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError as e:
        logger.warning(f"Corrupted JSON in {file_path}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Failed to load {file_path}: {e}")
        return None


def migrate_trade_state(state_manager: StateManager, symbol: str, data: Dict, dry_run: bool = False):
    """
    Migrate trade state to StateManager.

    Args:
        state_manager: StateManager instance
        symbol: Trading symbol
        data: Legacy trade data
        dry_run: If True, only log what would be done
    """
    if dry_run:
        logger.info(f"  [DRY-RUN] Would migrate trade state for {symbol}: {data}")
    else:
        state_manager.save_trade_state(symbol, data)
        logger.info(f"  Migrated trade state for {symbol}")


def migrate_cooldown(state_manager: StateManager, symbol: str, data: Dict, dry_run: bool = False):
    """
    Migrate cooldown to StateManager.

    Args:
        state_manager: StateManager instance
        symbol: Trading symbol
        data: Legacy cooldown data (format: {"t": timestamp})
        dry_run: If True, only log what would be done
    """
    if "t" not in data:
        logger.warning(f"  Skipping invalid cooldown for {symbol}: missing 't' field")
        return

    cooldown_timestamp = data["t"]
    if dry_run:
        logger.info(f"  [DRY-RUN] Would migrate cooldown for {symbol}: timestamp={cooldown_timestamp}")
    else:
        # Import cooldown directly into state
        state_manager._state["cooldowns"][symbol] = cooldown_timestamp
        state_manager._save_state()
        logger.info(f"  Migrated cooldown for {symbol}")


def migrate_watch_state(state_manager: StateManager, symbol: str, data: Dict, dry_run: bool = False):
    """
    Migrate watch/skip state to StateManager.

    Args:
        state_manager: StateManager instance
        symbol: Trading symbol
        data: Legacy watch data
        dry_run: If True, only log what would be done
    """
    if dry_run:
        logger.info(f"  [DRY-RUN] Would migrate watch state for {symbol}: {data}")
    else:
        state_manager.save_watch_state(symbol, data)
        logger.info(f"  Migrated watch state for {symbol}")


def backup_legacy_files(files: List[str], dry_run: bool = False) -> str:
    """
    Backup legacy files to timestamped directory.

    Args:
        files: List of files to backup
        dry_run: If True, only log what would be done

    Returns:
        Path to backup directory
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.expanduser(f"~/.tv_fast_backup_{timestamp}")

    if dry_run:
        logger.info(f"[DRY-RUN] Would create backup directory: {backup_dir}")
        for file_path in files:
            logger.info(f"  [DRY-RUN] Would backup: {os.path.basename(file_path)}")
    else:
        os.makedirs(backup_dir, exist_ok=True)
        for file_path in files:
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            logger.info(f"  Backed up: {os.path.basename(file_path)} -> {backup_dir}")
        logger.info(f"Backup created at: {backup_dir}")

    return backup_dir


def main():
    """Main migration script entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate legacy scanner state files to consolidated StateManager"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without applying changes"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup legacy files before migration"
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Scanner State Migration Tool")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("MODE: DRY-RUN (no changes will be applied)")
    else:
        logger.info("MODE: LIVE MIGRATION")

    # Find legacy files
    logger.info("\nScanning for legacy state files...")
    legacy_files = find_legacy_files()

    if not legacy_files:
        logger.info("No legacy state files found. Migration not needed.")
        logger.info("Checking if consolidated state already exists...")
        if os.path.exists(DEFAULT_STATE_FILE):
            logger.info(f"✓ Consolidated state file exists: {DEFAULT_STATE_FILE}")
        else:
            logger.info(f"✗ No state files found (neither legacy nor consolidated)")
        return

    logger.info(f"Found {len(legacy_files)} legacy state files:")
    for file_path in legacy_files:
        size = os.path.getsize(file_path)
        logger.info(f"  - {os.path.basename(file_path)} ({size} bytes)")

    # Backup if requested
    if args.backup:
        logger.info("\nCreating backup...")
        backup_legacy_files(legacy_files, dry_run=args.dry_run)

    # Initialize StateManager
    logger.info("\nInitializing StateManager...")
    state_manager = StateManager(namespace="scanner")

    # Migrate each file
    logger.info("\nMigrating state files...")
    migration_count = 0
    skip_count = 0

    for file_path in legacy_files:
        symbol, kind = parse_legacy_filename(file_path)
        logger.info(f"\nProcessing: {os.path.basename(file_path)} (symbol={symbol}, kind={kind})")

        # Load legacy data
        data = load_legacy_file(file_path)
        if data is None:
            skip_count += 1
            continue

        # Migrate based on kind
        if kind == "trade":
            if symbol:
                migrate_trade_state(state_manager, symbol, data, dry_run=args.dry_run)
                migration_count += 1
            else:
                # Global trade state - skip or handle specially
                logger.warning(f"  Skipping global trade state (use per-symbol files)")
                skip_count += 1

        elif kind == "cd":
            if symbol:
                migrate_cooldown(state_manager, symbol, data, dry_run=args.dry_run)
                migration_count += 1
            else:
                # Global cooldown - skip
                logger.warning(f"  Skipping global cooldown (use per-symbol files)")
                skip_count += 1

        elif kind in ["skip", "watch"]:
            if symbol:
                migrate_watch_state(state_manager, symbol, data, dry_run=args.dry_run)
                migration_count += 1
            else:
                # Global watch state
                logger.warning(f"  Skipping global watch state (use per-symbol files)")
                skip_count += 1

        elif kind in ["tg", "vp", "pending", "pinned"]:
            # These are not part of the core state schema - skip
            logger.info(f"  Skipping {kind} state (not part of core schema)")
            skip_count += 1

        else:
            logger.warning(f"  Unknown state kind: {kind}")
            skip_count += 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    logger.info(f"Total legacy files found: {len(legacy_files)}")
    logger.info(f"Successfully migrated: {migration_count}")
    logger.info(f"Skipped: {skip_count}")

    if args.dry_run:
        logger.info("\nThis was a DRY-RUN. No changes were applied.")
        logger.info("Run without --dry-run to perform actual migration.")
    else:
        logger.info(f"\nMigration complete!")
        logger.info(f"Consolidated state file: {DEFAULT_STATE_FILE}")
        logger.info("\nNext steps:")
        logger.info("1. Verify the consolidated state file looks correct")
        logger.info("2. Test scanner with new state")
        logger.info("3. Once confirmed working, you can safely delete legacy files")
        if args.backup:
            logger.info("4. Backup files are preserved for safety")


if __name__ == "__main__":
    main()
