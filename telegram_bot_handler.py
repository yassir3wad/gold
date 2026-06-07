#!/usr/bin/env python3
"""
Telegram bot command handler for zone refresh operations.
Listens for /refresh_zones command and triggers zone refresh workflow.

Usage:
    python telegram_bot_handler.py              # Start bot in polling mode
    python telegram_bot_handler.py --dry-run    # Test mode (no actual refresh)
    python telegram_bot_handler.py --once       # Process one command and exit

Telegram commands:
    /refresh_zones              # Refresh all instruments
    /refresh_zones <SYMBOL>     # Refresh single instrument (e.g., /refresh_zones XAUUSD)
    /help                       # Show available commands
"""
import subprocess
import json
import os
import sys
import time

# Config file path - check current directory first for worktree compatibility, then home
CONFIG_FILE = "./telegram_config.json" if os.path.exists("./telegram_config.json") else os.path.expanduser("~/tradingview-mcp/telegram_config.json")

# Project directory for running refresh_all_zones.py
TVDIR = os.path.expanduser("~/tradingview-mcp")

# Poll interval in seconds
POLL_INTERVAL = 2

# Dry run mode flag
DRY_RUN = "--dry-run" in sys.argv
ONCE_MODE = "--once" in sys.argv

def _load_config():
    """Load Telegram bot token and chat_id from config file. Returns (token, chat_id) or (None, None) if unavailable."""
    try:
        cfg = json.load(open(CONFIG_FILE))
        return cfg.get("bot_token"), cfg.get("chat_id")
    except Exception as e:
        print(f"[ERROR] Failed to load config from {CONFIG_FILE}: {e}", file=sys.stderr)
        return None, None


def _telegram_ok(result):
    """Return True only when Telegram returns ok:true, not just when curl exits 0."""
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout or "{}")
    except Exception:
        return False
    return bool(payload.get("ok"))

def send_message(token, chat_id, text):
    """Send a text message to Telegram chat."""
    try:
        result = subprocess.run(
            ["curl", "-s", f"https://api.telegram.org/bot{token}/sendMessage",
             "-d", f"chat_id={chat_id}",
             "--data-urlencode", f"text={text}"],
            timeout=15,
            capture_output=True,
            text=True
        )
        return _telegram_ok(result)
    except Exception as e:
        print(f"[ERROR] Failed to send message: {e}", file=sys.stderr)
        return False

def get_updates(token, offset=None):
    """Poll for new updates from Telegram Bot API. Returns list of updates or None on error."""
    try:
        cmd = ["curl", "-s", f"https://api.telegram.org/bot{token}/getUpdates"]
        if offset:
            cmd.extend(["-d", f"offset={offset}"])
        cmd.extend(["-d", "timeout=30"])  # Long polling timeout

        result = subprocess.run(cmd, timeout=35, capture_output=True, text=True)

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        if data.get("ok"):
            return data.get("result", [])
        return None
    except Exception as e:
        print(f"[ERROR] Failed to get updates: {e}", file=sys.stderr)
        return None

def refresh_zones(symbol=None, dry_run=False):
    """
    Trigger zone refresh via refresh_all_zones.py.

    Args:
        symbol: Optional symbol to refresh (e.g., "XAUUSD"). If None, refresh all.
        dry_run: If True, run in dry-run mode

    Returns:
        Tuple of (success: bool, output: str)
    """
    cmd = ["python3", os.path.join(TVDIR, "refresh_all_zones.py"), "--notify"]
    if symbol:
        cmd.extend(["--symbol", symbol])
    if dry_run:
        cmd.append("--dry-run")

    try:
        result = subprocess.run(
            cmd,
            cwd=TVDIR,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for full refresh
        )

        output = result.stdout if result.stdout else result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Zone refresh timed out after 5 minutes"
    except Exception as e:
        return False, f"Error running zone refresh: {e}"

def handle_command(token, chat_id, message_text, username=""):
    """
    Process a command from Telegram and send response.

    Args:
        token: Bot token
        chat_id: Chat ID to respond to
        message_text: Command text (e.g., "/refresh_zones" or "/refresh_zones XAUUSD")
        username: Username of sender (for logging)
    """
    parts = message_text.strip().split()
    command = parts[0].lower()

    if command == "/help":
        help_text = """*Zone Refresh Bot Commands*

/refresh\\_zones — Refresh all instruments
/refresh\\_zones <SYMBOL> — Refresh single instrument
/help — Show this help message

Example:
/refresh\\_zones XAUUSD"""
        send_message(token, chat_id, help_text)
        print(f"[INFO] Sent help message to {username}")
        return

    if command == "/refresh_zones":
        symbol = parts[1].upper() if len(parts) > 1 else None

        # Send acknowledgment
        if symbol:
            ack_msg = f"🔄 Refreshing zones for {symbol}..."
        else:
            ack_msg = "🔄 Refreshing zones for all instruments..."

        send_message(token, chat_id, ack_msg)
        print(f"[INFO] Starting zone refresh for {symbol or 'all instruments'} (requested by {username})")

        # Trigger refresh
        success, output = refresh_zones(symbol=symbol, dry_run=DRY_RUN)

        # Send result (telegram_notify.py will send detailed alert via --notify flag)
        if success:
            if DRY_RUN:
                result_msg = f"✅ Dry run complete for {symbol or 'all instruments'}"
            else:
                result_msg = f"✅ Zone refresh complete for {symbol or 'all instruments'}"
            print(f"[INFO] Zone refresh successful")
        else:
            result_msg = f"❌ Zone refresh failed\n\nError: {output[:500]}"
            print(f"[ERROR] Zone refresh failed: {output}")

        send_message(token, chat_id, result_msg)
        return

    # Unknown command
    send_message(token, chat_id, f"Unknown command: {command}\n\nSend /help for available commands")
    print(f"[WARN] Unknown command from {username}: {command}")

def main():
    """Main bot loop - poll for commands and process them."""
    print("[INFO] Starting Telegram bot handler...")

    if DRY_RUN:
        print("[INFO] Running in DRY RUN mode - no actual zone refresh will occur")

    if ONCE_MODE:
        print("[INFO] Running in ONCE mode - will process one command and exit")

    token, chat_id = _load_config()
    if not token or not chat_id:
        print(f"[ERROR] Telegram config not found at {CONFIG_FILE}", file=sys.stderr)
        print(f"[ERROR] Please create {CONFIG_FILE} with bot_token and chat_id", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Bot configured with chat_id: {chat_id}")
    print(f"[INFO] Polling for commands... (Ctrl+C to stop)")

    offset = None

    try:
        while True:
            updates = get_updates(token, offset)

            if updates is None:
                # Error getting updates, wait and retry
                time.sleep(POLL_INTERVAL)
                continue

            for update in updates:
                # Update offset to mark this update as processed
                offset = update["update_id"] + 1

                # Check if this is a message
                if "message" not in update:
                    continue

                msg = update["message"]

                # Only process text messages
                if "text" not in msg:
                    continue

                # Only process messages from the configured chat
                if str(msg["chat"]["id"]) != str(chat_id):
                    print(f"[WARN] Ignoring message from unauthorized chat: {msg['chat']['id']}")
                    continue

                text = msg["text"]
                username = msg.get("from", {}).get("username", "unknown")

                # Check if this is a command
                if not text.startswith("/"):
                    continue

                print(f"[INFO] Received command from {username}: {text}")

                # Handle the command
                handle_command(token, chat_id, text, username)

                # If in once mode, exit after processing first command
                if ONCE_MODE:
                    print("[INFO] ONCE mode - exiting after processing command")
                    return

            # If no updates and in once mode, exit
            if ONCE_MODE and not updates:
                print("[INFO] ONCE mode - no commands to process, exiting")
                return

            # Brief sleep between polls (only used if no updates or short polling)
            if not updates:
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n[INFO] Bot stopped by user")
    except Exception as e:
        print(f"[ERROR] Bot crashed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)

    main()
