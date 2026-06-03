#!/bin/bash
PLIST="$HOME/Library/LaunchAgents/com.yassir.goldscalper.plist"
case "$1" in
  start)  launchctl load "$PLIST" 2>/dev/null && echo "✅ monitor STARTED — runs every 60s, alerts to Telegram";;
  stop)   launchctl unload "$PLIST" 2>/dev/null && echo "🛑 monitor STOPPED";;
  status) launchctl list | grep goldscalper && echo "(running)" || echo "(not running)";;
  *) echo "usage: ./tg_monitor.sh start|stop|status";;
esac
