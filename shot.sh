#!/bin/bash
cd ~/tradingview-mcp || exit 1
exec node src/cli/index.js screenshot
