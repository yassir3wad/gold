#!/bin/bash
# bash shot.sh [SYMBOL]  — screenshot a specific pair's window (default = active chart)
cd ~/tradingview-mcp || exit 1
SYM="${1:-}"
if [ -n "$SYM" ]; then
  CHART=$(python3 -c "import json;print(json.load(open('instruments.json')).get('$SYM',{}).get('chart',''))" 2>/dev/null)
  [ -n "$CHART" ] && export TV_CHART="$CHART"
fi
exec node src/cli/index.js screenshot
