#!/bin/bash
# One hands-free multi-pair tick: meta-scan + AI-review the hot/active pairs, flag held trades.
cd ~/tradingview-mcp || exit 1
exec python3 orchestrate.py 2>&1
