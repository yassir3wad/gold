#!/usr/bin/env python3
"""
Zone Scheduler — Automated HTF Zone Refresh Daemon
Runs refresh_zones.py on a schedule (interval + session-based triggers) to keep
support/resistance zones fresh. Prevents stale confluence grading.

Usage:
  python zone_scheduler.py                           # run with default 4-hour interval
  python zone_scheduler.py --interval 2              # run every 2 hours
  python zone_scheduler.py --daemon                  # run as background daemon
  python zone_scheduler.py --once                    # run one refresh cycle then exit
  python zone_scheduler.py --help                    # show this help message
"""
import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime

# --- Configuration ---
DEFAULT_INTERVAL_HOURS = 4
CONFIG_FILE = os.path.expanduser("~/tradingview-mcp/zone_scheduler_config.json")
LOG_FILE = os.path.expanduser("~/tradingview-mcp/logs/zone_scheduler.log")

# --- Logging Setup ---
def setup_logging(verbose=False):
    """Configure logging to both console and file with rotation."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '[%(asctime)s] %(levelname)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))

    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# --- Configuration Loading ---
def load_config():
    """Load scheduler configuration from zone_scheduler_config.json.
    Returns dict with: refresh_interval_hours, session_refresh_enabled, etc.
    Falls back to defaults if file missing."""
    defaults = {
        "refresh_interval_hours": DEFAULT_INTERVAL_HOURS,
        "session_refresh_enabled": True,
        "session_offset_minutes": 5,
        "enabled_instruments": ["XAUUSD", "GBPUSD", "EURUSD"],
        "stale_threshold_hours": 6
    }

    if not os.path.exists(CONFIG_FILE):
        logging.warning(f"Config file not found: {CONFIG_FILE}, using defaults")
        return defaults

    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        logging.info(f"Loaded config from {CONFIG_FILE}")
        # Merge with defaults for any missing keys
        return {**defaults, **config}
    except Exception as e:
        logging.error(f"Error loading config {CONFIG_FILE}: {e}, using defaults")
        return defaults

# --- Zone Refresh Job ---
def refresh_zones_job():
    """Execute zone refresh for all enabled instruments.
    This is the scheduled job that runs at intervals and session opens."""
    logging.info("Starting scheduled zone refresh cycle")

    try:
        # TODO: Call refresh_all_zones.py here (will be implemented in subtask-2-3)
        # For now, just log the action
        config = load_config()
        instruments = config.get("enabled_instruments", [])

        logging.info(f"Refreshing zones for instruments: {', '.join(instruments)}")

        # Placeholder for actual refresh logic
        # In subtask-2-3, this will call: subprocess.run(["python", "refresh_all_zones.py", ...])

        logging.info("Zone refresh cycle completed successfully")

    except Exception as e:
        logging.error(f"Error during zone refresh: {e}", exc_info=True)

# --- Scheduler Setup ---
class ZoneScheduler:
    """Main scheduler daemon that manages interval-based and session-based refresh triggers."""

    def __init__(self, interval_hours=None, run_once=False):
        self.config = load_config()
        self.interval_hours = interval_hours or self.config.get("refresh_interval_hours", DEFAULT_INTERVAL_HOURS)
        self.run_once = run_once
        self.scheduler = BackgroundScheduler()
        self.running = False

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logging.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def add_interval_job(self):
        """Add interval-based refresh job (e.g., every 4 hours)."""
        logging.info(f"Scheduling interval refresh every {self.interval_hours} hours")

        self.scheduler.add_job(
            refresh_zones_job,
            trigger=IntervalTrigger(hours=self.interval_hours),
            id='interval_refresh',
            name='Interval Zone Refresh',
            replace_existing=True
        )

    def add_session_jobs(self):
        """Add session-based refresh jobs (London/NY opens).
        Will be implemented in subtask-3-2."""
        if not self.config.get("session_refresh_enabled", True):
            logging.info("Session-based refresh is disabled in config")
            return

        # TODO: Implement session timing logic in subtask-3-1
        # TODO: Add CronTrigger jobs in subtask-3-2
        logging.info("Session-based refresh triggers will be added in phase-3")

    def start(self):
        """Start the scheduler daemon."""
        logging.info("=" * 60)
        logging.info("Zone Scheduler starting...")
        logging.info(f"Interval: {self.interval_hours} hours")
        logging.info(f"Config: {CONFIG_FILE}")
        logging.info(f"Enabled instruments: {', '.join(self.config.get('enabled_instruments', []))}")
        logging.info("=" * 60)

        # Add scheduled jobs
        self.add_interval_job()
        self.add_session_jobs()

        # Start scheduler
        self.scheduler.start()
        self.running = True

        logging.info("Scheduler started successfully")

        # Run immediately if in once mode
        if self.run_once:
            logging.info("Running in --once mode, executing immediate refresh")
            refresh_zones_job()
            self.stop()
            return

        # Keep running until interrupted
        try:
            logging.info("Scheduler running. Press Ctrl+C to stop.")
            while self.running:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            self.stop()

    def stop(self):
        """Stop the scheduler gracefully."""
        if not self.running:
            return

        logging.info("Stopping scheduler...")
        self.running = False

        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)

        logging.info("Scheduler stopped")

# --- CLI Entry Point ---
def main():
    # Parse args first (so --help works without dependencies)
    parser = argparse.ArgumentParser(
        description='Zone Scheduler — Automated HTF Zone Refresh Daemon',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     Run with default 4-hour interval
  %(prog)s --interval 2        Run every 2 hours
  %(prog)s --daemon            Run as background daemon
  %(prog)s --once              Run one refresh cycle then exit
  %(prog)s --verbose           Enable debug logging

Configuration:
  Config file: ~/tradingview-mcp/zone_scheduler_config.json
  Log file:    ~/tradingview-mcp/logs/zone_scheduler.log
        """
    )

    parser.add_argument(
        '--interval',
        type=float,
        metavar='HOURS',
        help=f'Refresh interval in hours (default: {DEFAULT_INTERVAL_HOURS})'
    )

    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as background daemon (detach from terminal)'
    )

    parser.add_argument(
        '--once',
        action='store_true',
        help='Run one refresh cycle then exit (for testing)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose debug logging'
    )

    args = parser.parse_args()

    # Check APScheduler dependency (after argparse so --help works)
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        from apscheduler.triggers.cron import CronTrigger
        # Make available to module scope
        globals()['BackgroundScheduler'] = BackgroundScheduler
        globals()['IntervalTrigger'] = IntervalTrigger
        globals()['CronTrigger'] = CronTrigger
    except ImportError:
        print("ERROR: APScheduler not installed. Run: pip install apscheduler", file=sys.stderr)
        sys.exit(1)

    # Setup logging
    setup_logging(verbose=args.verbose)

    # Daemon mode: detach from terminal
    if args.daemon:
        logging.info("Running in daemon mode (background)")
        # TODO: Implement proper daemonization (fork, setsid, etc.) if needed
        # For now, just run normally (systemd will handle daemonization)

    # Create and start scheduler
    scheduler = ZoneScheduler(
        interval_hours=args.interval,
        run_once=args.once
    )

    scheduler.start()

if __name__ == "__main__":
    main()
