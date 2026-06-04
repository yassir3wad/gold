#!/bin/bash
# AI-review loop for one pair: bash aireview.sh [SYMBOL]   (default XAUUSD)
cd ~/tradingview-mcp || exit 1
SYM="${1:-XAUUSD}"
rm -f ~/.tv_fast_$(echo "$SYM" | tr 'A-Z' 'a-z').lock
exec python3 scalp_fast.py --symbol "$SYM" --review 2>&1
