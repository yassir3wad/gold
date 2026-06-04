#!/bin/bash
# AI-review loop: scan + hold confirmed trades for Claude's decision (one clean command for the allowlist)
cd ~/tradingview-mcp || exit 1
rm -f ~/.tv_fast.lock
exec python3 scalp_fast.py --review 2>&1
