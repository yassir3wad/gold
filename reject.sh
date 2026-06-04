#!/bin/bash
cd ~/tradingview-mcp || exit 1
exec python3 scalp_fast.py --reject "$@"
