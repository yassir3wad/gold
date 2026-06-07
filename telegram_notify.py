#!/usr/bin/env python3
"""
Telegram notification module for zone scheduler and trading alerts.
Provides simple functions to send text messages and formatted alerts via Telegram Bot API.
"""
import subprocess
import json
import os
import sys

# Config file path - check current directory first for worktree compatibility, then home
CONFIG_FILE = "./telegram_config.json" if os.path.exists("./telegram_config.json") else os.path.expanduser("~/tradingview-mcp/telegram_config.json")

def _load_config():
    """Load Telegram bot token and chat_id from config file. Returns (token, chat_id) or (None, None) if unavailable."""
    try:
        cfg = json.load(open(CONFIG_FILE))
        return cfg.get("bot_token"), cfg.get("chat_id")
    except Exception:
        return None, None


def _telegram_ok(result):
    """Return True only when the Telegram API reports ok:true.
    Curl transport success alone is not enough; Telegram can return HTTP 200 with {"ok": false, ...}."""
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout or "{}")
    except Exception:
        return False
    return bool(payload.get("ok"))

def format_zone_summary(changes_by_symbol):
    """
    Format zone refresh changes into a human-readable summary for Telegram.

    Args:
        changes_by_symbol: Dict mapping symbol names to change stats
                          e.g., {'XAUUSD': {'added': 2, 'removed': 1, 'modified': 0, 'unchanged': 5}}

    Returns:
        Formatted string suitable for Telegram notification
    """
    if not changes_by_symbol:
        return "No instruments refreshed"

    lines = []
    total_changes = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}

    for symbol in sorted(changes_by_symbol.keys()):
        stats = changes_by_symbol[symbol]
        added = stats.get("added", 0)
        removed = stats.get("removed", 0)
        modified = stats.get("modified", 0)
        unchanged = stats.get("unchanged", 0)

        for k in total_changes:
            total_changes[k] += stats.get(k, 0)

        if added + removed + modified == 0:
            lines.append(f"{symbol}: no changes")
        else:
            change_parts = []
            if added: change_parts.append(f"+{added}")
            if removed: change_parts.append(f"-{removed}")
            if modified: change_parts.append(f"~{modified}")
            lines.append(f"{symbol}: {' '.join(change_parts)}")

    if len(changes_by_symbol) > 1:
        if total_changes["added"] + total_changes["removed"] + total_changes["modified"] > 0:
            total_parts = []
            if total_changes["added"]: total_parts.append(f"+{total_changes['added']}")
            if total_changes["removed"]: total_parts.append(f"-{total_changes['removed']}")
            if total_changes["modified"]: total_parts.append(f"~{total_changes['modified']}")
            lines.append(f"\nTotal: {' '.join(total_parts)}")
        else:
            lines.append("\nTotal: no changes detected")

    return "\n".join(lines)

def send_message(text, dry_run=False):
    """
    Send a text message to Telegram.

    Args:
        text: Message text to send
        dry_run: If True, print message instead of sending (for testing)

    Returns:
        True if sent successfully, False otherwise
    """
    if dry_run:
        print(f"[DRY RUN] Would send Telegram message:\n{text}")
        return True

    tok, cid = _load_config()
    if not tok or not cid:
        print(f"[WARNING] Telegram config not found at {CONFIG_FILE} - skipping notification", file=sys.stderr)
        return False

    try:
        result = subprocess.run(
            ["curl", "-s", f"https://api.telegram.org/bot{tok}/sendMessage",
             "-d", f"chat_id={cid}",
             "--data-urlencode", f"text={text}"],
            timeout=15,
            capture_output=True,
            text=True
        )
        return _telegram_ok(result)
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram message: {e}", file=sys.stderr)
        return False

def send_alert(title, message, dry_run=False):
    """
    Send a formatted alert to Telegram with title and message body.

    Args:
        title: Alert title (e.g., "🔄 Zones Refreshed")
        message: Alert message body (can be multi-line)
        dry_run: If True, print alert instead of sending (for testing)

    Returns:
        True if sent successfully, False otherwise
    """
    # Format with title in bold using Telegram markdown
    formatted_text = f"*{title}*\n\n{message}"

    if dry_run:
        print(f"[DRY RUN] Would send Telegram alert:")
        print(formatted_text)
        return True

    tok, cid = _load_config()
    if not tok or not cid:
        print(f"[WARNING] Telegram config not found at {CONFIG_FILE} - skipping notification", file=sys.stderr)
        return False

    try:
        result = subprocess.run(
            ["curl", "-s", f"https://api.telegram.org/bot{tok}/sendMessage",
             "-d", f"chat_id={cid}",
             "-d", "parse_mode=Markdown",
             "--data-urlencode", f"text={formatted_text}"],
            timeout=15,
            capture_output=True,
            text=True
        )
        return _telegram_ok(result)
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram alert: {e}", file=sys.stderr)
        return False

def send_photo(photo_path, caption="", dry_run=False):
    """
    Send a photo to Telegram with optional caption.

    Args:
        photo_path: Path to image file to send
        caption: Optional caption text
        dry_run: If True, print info instead of sending (for testing)

    Returns:
        True if sent successfully, False otherwise
    """
    if dry_run:
        print(f"[DRY RUN] Would send Telegram photo: {photo_path}")
        if caption:
            print(f"Caption: {caption}")
        return True

    if not os.path.exists(photo_path):
        print(f"[ERROR] Photo file not found: {photo_path}", file=sys.stderr)
        return False

    tok, cid = _load_config()
    if not tok or not cid:
        print(f"[WARNING] Telegram config not found at {CONFIG_FILE} - skipping notification", file=sys.stderr)
        return False

    try:
        cmd = ["curl", "-s",
               "-F", f"chat_id={cid}",
               "-F", f"photo=@{photo_path}"]
        if caption:
            cmd.extend(["-F", f"caption={caption}"])
        cmd.append(f"https://api.telegram.org/bot{tok}/sendPhoto")

        result = subprocess.run(cmd, timeout=25, capture_output=True, text=True)
        return _telegram_ok(result)
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram photo: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # Simple CLI test interface
    if len(sys.argv) < 2:
        print("Usage: python telegram_notify.py [--dry-run] <message>")
        print("       python telegram_notify.py --test")
        sys.exit(1)

    dry = "--dry-run" in sys.argv
    if "--test" in sys.argv:
        print("Testing Telegram notify module...")
        send_message("Test message from telegram_notify.py", dry_run=dry)
        send_alert("Test Alert", "This is a test alert message", dry_run=dry)
        print("Test complete!")
    else:
        msg = " ".join(arg for arg in sys.argv[1:] if arg != "--dry-run")
        send_message(msg, dry_run=dry)
