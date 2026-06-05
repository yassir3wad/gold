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
  python zone_scheduler.py --check-health            # check zone file health and exit
  python zone_scheduler.py --help                    # show this help message
"""
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
import telegram_notify

# --- Configuration ---
DEFAULT_INTERVAL_HOURS = 4
# Try current directory first, then fall back to home directory
CONFIG_FILE = (
    "zone_scheduler_config.json" if os.path.exists("zone_scheduler_config.json")
    else os.path.expanduser("~/tradingview-mcp/zone_scheduler_config.json")
)
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
        "stale_threshold_hours": 6,
        "notifications_enabled": True
    }

    if not os.path.exists(CONFIG_FILE):
        logging.warning(f"Config file not found: {CONFIG_FILE}, using defaults")
        return defaults

    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        logging.info(f"Loaded config from {CONFIG_FILE}")
        # Merge with defaults for any missing keys
        merged = {**defaults, **config}
        # Honor the documented `notifications` object (BUG: code read a non-existent `notifications_enabled`,
        # so the config toggles were dead). Map the object's switches to the booleans the code uses.
        notif = merged.get("notifications", {})
        if isinstance(notif, dict):
            merged["notifications_enabled"] = notif.get("send_on_refresh", merged.get("notifications_enabled", True))
            merged["stale_notifications_enabled"] = notif.get("send_on_stale_warning", True)
        else:
            merged["stale_notifications_enabled"] = merged.get("notifications_enabled", True)
        return merged
    except Exception as e:
        logging.error(f"Error loading config {CONFIG_FILE}: {e}, using defaults")
        return defaults

# --- Session Timing ---
def get_session_times():
    """Calculate session open times in UTC.

    Returns dict with session timing info:
    {
        'london': {'open_utc': 7, 'close_utc': 16, 'tz': 'Europe/London'},
        'ny': {'open_utc': 13, 'close_utc': 22, 'tz': 'America/New_York'},
        'asia': {'open_utc': 0, 'close_utc': 7, 'tz': 'Asia/Tokyo'}
    }

    These are baseline UTC hours. Actual session boxes on chart may vary
    based on DST and the Trading Sessions indicator settings.
    Matches the fallback UTC windows used in refresh_zones.py.
    """
    return {
        'london': {
            'open_utc': 7,
            'close_utc': 16,
            'tz': 'Europe/London'
        },
        'ny': {
            'open_utc': 13,
            'close_utc': 22,
            'tz': 'America/New_York'
        },
        'asia': {
            'open_utc': 0,
            'close_utc': 7,
            'tz': 'Asia/Tokyo'
        }
    }

# --- Zone Refresh Job ---
def refresh_zones_job():
    """Execute zone refresh for all enabled instruments.
    This is the scheduled job that runs at intervals and session opens."""
    logging.info("Starting scheduled zone refresh cycle")

    try:
        config = load_config()
        instruments = config.get("enabled_instruments", [])
        notifications_enabled = config.get("notifications_enabled", True)

        if not instruments:
            logging.warning("No enabled instruments in config, skipping refresh")
            return

        logging.info(f"Refreshing zones for instruments: {', '.join(instruments)}")

        # Call refresh_all_zones.py for each enabled instrument
        tvdir = os.path.expanduser("~/tradingview-mcp")
        refresh_script = os.path.join(tvdir, "refresh_all_zones.py")
        changes_by_symbol = {}

        for symbol in instruments:
            logging.info(f"Refreshing zones for {symbol}")
            try:
                result = subprocess.run(
                    ["python3", refresh_script, "--symbol", symbol],
                    cwd=tvdir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if result.returncode == 0:
                    # Parse output to extract change statistics
                    if result.stdout:
                        for line in result.stdout.strip().split('\n'):
                            if line:
                                logging.debug(f"  {line}")
                            # Parse change line like "  ✓ zones changed: +2 -1 ~0"
                            if "zones changed:" in line:
                                changes_by_symbol[symbol] = _parse_changes_from_output(line)
                            elif "no changes" in line and symbol not in changes_by_symbol:
                                changes_by_symbol[symbol] = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}
                    logging.info(f"Successfully refreshed {symbol}")
                else:
                    logging.error(f"Failed to refresh {symbol} (exit {result.returncode})")
                    if result.stderr:
                        logging.error(f"  Error: {result.stderr.strip()}")

            except subprocess.TimeoutExpired:
                logging.error(f"Timeout refreshing {symbol} after 120s")
            except Exception as e:
                logging.error(f"Error refreshing {symbol}: {e}")

        logging.info("Zone refresh cycle completed successfully")

        # Send Telegram notification if enabled and we have changes
        if notifications_enabled and changes_by_symbol:
            summary = telegram_notify.format_zone_summary(changes_by_symbol)
            telegram_notify.send_alert("🔄 Zones Refreshed", summary, dry_run=False)
            logging.info("Telegram notification sent")

    except Exception as e:
        logging.error(f"Error during zone refresh: {e}", exc_info=True)

def _parse_changes_from_output(line):
    """Parse change statistics from refresh output line.
    Example: '  ✓ zones changed: +2 -1 ~0' -> {'added': 2, 'removed': 1, 'modified': 0}
    """
    changes = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}
    parts = line.split("zones changed:")
    if len(parts) < 2:
        return changes

    tokens = parts[1].strip().split()
    for token in tokens:
        if token.startswith('+'):
            changes["added"] = int(token[1:])
        elif token.startswith('-'):
            changes["removed"] = int(token[1:])
        elif token.startswith('~'):
            changes["modified"] = int(token[1:])

    return changes

# --- Zone Health Check ---
def check_zone_health(send_alert=False):
    """Check all zone files for staleness and optionally send alerts.

    Args:
        send_alert: If True, send Telegram alert for stale zones

    Returns:
        dict with health status: {
            'stale_count': int,
            'fresh_count': int,
            'missing_count': int,
            'stale_symbols': list of str
        }
    """
    config = load_config()
    instruments = config.get("enabled_instruments", [])
    stale_threshold_hours = config.get("stale_threshold_hours", 6)
    notifications_enabled = config.get("stale_notifications_enabled", True)   # stale alerts gated by send_on_stale_warning

    if not instruments:
        logging.warning("No enabled instruments in config, skipping health check")
        return {
            'stale_count': 0,
            'fresh_count': 0,
            'missing_count': 0,
            'stale_symbols': []
        }

    logging.info(f"Running zone health check (stale threshold: {stale_threshold_hours}h)")

    tvdir = os.path.expanduser("~/tradingview-mcp")
    current_time = time.time()
    max_age_seconds = stale_threshold_hours * 3600

    stale_count = 0
    fresh_count = 0
    missing_count = 0
    stale_symbols = []

    results = []

    for symbol in instruments:
        zone_file = os.path.join(tvdir, f"zones_{symbol.lower()}.json")

        if not os.path.exists(zone_file):
            missing_count += 1
            logging.warning(f"  ✗ {symbol}: zone file missing")
            results.append({
                "symbol": symbol,
                "status": "missing"
            })
            continue

        try:
            with open(zone_file, 'r') as f:
                zone_data = json.load(f)

            zone_ts = zone_data.get("ts")
            if zone_ts is None:
                logging.warning(f"  ✗ {symbol}: no timestamp field in zone file")
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
                stale_symbols.append(symbol)
                logging.warning(f"  ⚠ {symbol}: STALE ({age_hours:.1f}h old)")
                results.append({
                    "symbol": symbol,
                    "status": "stale",
                    "age_hours": round(age_hours, 1)
                })
            else:
                fresh_count += 1
                logging.info(f"  ✓ {symbol}: fresh ({age_hours:.1f}h old)")
                results.append({
                    "symbol": symbol,
                    "status": "fresh",
                    "age_hours": round(age_hours, 1)
                })

        except json.JSONDecodeError as e:
            logging.error(f"  ✗ {symbol}: invalid JSON - {e}")
            results.append({
                "symbol": symbol,
                "status": "error",
                "message": f"Invalid JSON: {e}"
            })
        except Exception as e:
            logging.error(f"  ✗ {symbol}: error - {e}")
            results.append({
                "symbol": symbol,
                "status": "error",
                "message": str(e)
            })

    # Log summary
    logging.info(f"Health check complete: {fresh_count} fresh, {stale_count} stale, {missing_count} missing")

    # Send alert if stale zones found and notifications enabled
    if send_alert and notifications_enabled and (stale_count > 0 or missing_count > 0):
        alert_lines = []

        if stale_count > 0:
            alert_lines.append(f"⚠ {stale_count} stale zone file(s) (>{stale_threshold_hours}h old):")
            for r in results:
                if r["status"] == "stale":
                    alert_lines.append(f"  • {r['symbol']}: {r['age_hours']}h old")

        if missing_count > 0:
            alert_lines.append(f"\n✗ {missing_count} missing zone file(s):")
            for r in results:
                if r["status"] == "missing":
                    alert_lines.append(f"  • {r['symbol']}")

        alert_lines.append("\nRun zone_scheduler.py to refresh zones")

        alert_message = "\n".join(alert_lines)
        telegram_notify.send_alert("⚠️ Stale Zones Detected", alert_message, dry_run=False)
        logging.info("Telegram alert sent for stale zones")

    return {
        'stale_count': stale_count,
        'fresh_count': fresh_count,
        'missing_count': missing_count,
        'stale_symbols': stale_symbols
    }

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
        Uses CronTrigger to schedule zone refreshes at configured session open times
        with optional offset (e.g., 5 min after London open)."""

        # Check if session refresh is enabled
        refresh_on_open = self.config.get("refresh_on_session_open", [])
        if not refresh_on_open:
            logging.info("No session-based refresh triggers configured")
            return

        session_times = self.config.get("session_times", {})
        offset_minutes = self.config.get("session_offset_minutes", 5)

        logging.info(f"Setting up session-based refresh triggers (offset: {offset_minutes} min)")

        for session in refresh_on_open:
            if session not in session_times:
                logging.warning(f"Session '{session}' not found in session_times config, skipping")
                continue

            time_str = session_times[session]
            try:
                # Parse time format "HH:MM"
                hour, minute = map(int, time_str.split(':'))

                # Apply offset
                total_minutes = hour * 60 + minute + offset_minutes
                trigger_hour = (total_minutes // 60) % 24
                trigger_minute = total_minutes % 60

                # Create CronTrigger for this session
                self.scheduler.add_job(
                    refresh_zones_job,
                    trigger=CronTrigger(hour=trigger_hour, minute=trigger_minute),
                    id=f'session_refresh_{session}',
                    name=f'{session.upper()} Session Refresh',
                    replace_existing=True
                )

                logging.info(f"  ✓ {session} session: {trigger_hour:02d}:{trigger_minute:02d} UTC")

            except ValueError as e:
                logging.error(f"Invalid time format for session '{session}': {time_str} - {e}")
            except Exception as e:
                logging.error(f"Error scheduling session '{session}': {e}")

    def start(self):
        """Start the scheduler daemon."""
        if not self.config.get("enabled", True):   # honor the documented master switch (BUG: was never read)
            logging.info("Zone scheduler is disabled in config ('enabled': false) — not starting.")
            return
        logging.info("=" * 60)
        logging.info("Zone Scheduler starting...")
        logging.info(f"Interval: {self.interval_hours} hours")
        logging.info(f"Config: {CONFIG_FILE}")
        logging.info(f"Enabled instruments: {', '.join(self.config.get('enabled_instruments', []))}")
        logging.info("=" * 60)

        # Run startup health check
        logging.info("Running startup health check...")
        health_status = check_zone_health(send_alert=True)

        # If stale zones detected on startup, offer to run immediate refresh
        if health_status['stale_count'] > 0:
            logging.warning(f"Found {health_status['stale_count']} stale zone(s) on startup")
            logging.info("Consider running immediate refresh with --once flag")

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
            last_health_check = time.time()
            health_check_interval = 3600  # Check health every hour

            while self.running:
                time.sleep(1)

                # Periodic health check (hourly)
                if time.time() - last_health_check >= health_check_interval:
                    logging.info("Running periodic health check...")
                    check_zone_health(send_alert=True)
                    last_health_check = time.time()

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

    parser.add_argument(
        '--test-session-schedule',
        action='store_true',
        help='Print session schedule configuration and exit (for testing)'
    )

    parser.add_argument(
        '--check-health',
        action='store_true',
        help='Run health check on zone files and exit (checks for stale zones)'
    )

    args = parser.parse_args()

    # Health check mode: run health check and exit (before importing dependencies)
    if args.check_health:
        setup_logging(verbose=args.verbose)
        logging.info("Running zone health check...")
        health_status = check_zone_health(send_alert=False)

        # Exit with error code if stale or missing zones found
        if health_status['stale_count'] > 0 or health_status['missing_count'] > 0:
            sys.exit(1)
        else:
            logging.info("✓ All zone files are healthy")
            sys.exit(0)

    # Test mode: print session schedule and exit (before importing dependencies)
    if args.test_session_schedule:
        config = load_config()
        refresh_on_open = config.get("refresh_on_session_open", [])
        session_times = config.get("session_times", {})
        offset_minutes = config.get("session_offset_minutes", 5)

        print("Session-based refresh schedule:")
        print(f"  Offset: {offset_minutes} minutes after session open")
        print()

        for session in refresh_on_open:
            if session in session_times:
                time_str = session_times[session]
                hour, minute = map(int, time_str.split(':'))
                total_minutes = hour * 60 + minute + offset_minutes
                trigger_hour = (total_minutes // 60) % 24
                trigger_minute = total_minutes % 60

                print(f"  {session}: {time_str} UTC → triggers at {trigger_hour:02d}:{trigger_minute:02d} UTC")

        sys.exit(0)

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
