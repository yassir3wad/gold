#!/bin/bash
# bash approve.sh [SYMBOL] [note...]   (default XAUUSD)
cd ~/tradingview-mcp || exit 1
SYM="${1:-XAUUSD}"; shift 2>/dev/null
exec python3 scalp_fast.py --symbol "$SYM" --approve "$@"
