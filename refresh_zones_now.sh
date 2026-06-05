#!/bin/bash
# Wrapper script for refresh_all_zones.py — refresh HTF zones for instruments
# Usage:
#   bash refresh_zones_now.sh              # refresh all instruments
#   bash refresh_zones_now.sh --dry-run    # preview without executing
#   bash refresh_zones_now.sh --symbol XAUUSD  # refresh single symbol
#   bash refresh_zones_now.sh --notify     # send Telegram notification after refresh
#   bash refresh_zones_now.sh --help       # show this help message

# Change to tradingview-mcp directory
cd ~/tradingview-mcp || exit 1

# Show help if requested
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  echo "refresh_zones_now.sh — Refresh HTF zones for all instruments"
  echo ""
  echo "Usage:"
  echo "  bash refresh_zones_now.sh              # refresh all instruments"
  echo "  bash refresh_zones_now.sh --dry-run    # preview without executing"
  echo "  bash refresh_zones_now.sh --symbol XAUUSD  # refresh single symbol"
  echo "  bash refresh_zones_now.sh --notify     # send Telegram notification after refresh"
  echo "  bash refresh_zones_now.sh --help       # show this help message"
  echo ""
  echo "Options:"
  echo "  --dry-run       List what would be refreshed without executing"
  echo "  --symbol SYM    Refresh only the specified symbol"
  echo "  --notify        Send Telegram notification after refresh"
  echo "  --help, -h      Show this help message"
  exit 0
fi

# Execute the Python script with all arguments passed through
exec python3 refresh_all_zones.py "$@"
