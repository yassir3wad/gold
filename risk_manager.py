#!/usr/bin/env python3
"""
Risk management module for scanner signal flow.
Enforces position limits, max daily loss, max concurrent signals per instrument,
and cross-pair correlation checks. When limits are breached, blocks new alerts
and notifies the trader via Telegram.
"""
import json
import os
import sys
import csv
import datetime

# Config file path - check current directory first for worktree compatibility, then home
FLAGS_FILE = "./flags.json" if os.path.exists("./flags.json") else os.path.expanduser("~/tradingview-mcp/flags.json")
SIGNALS_LOG = "./signals_log.csv" if os.path.exists("./signals_log.csv") else os.path.expanduser("~/tradingview-mcp/signals_log.csv")

class RiskManager:
    """
    Risk management controller for trading signals.

    Tracks daily P&L, open positions, and enforces configurable risk limits:
    - Max daily loss threshold
    - Max concurrent positions per instrument
    - Max total open positions
    - Correlation checks across currency pairs
    """

    def __init__(self):
        """Initialize RiskManager with configuration from flags.json"""
        self.config = self._load_config()

    def _load_config(self):
        """
        Load risk management configuration from flags.json.

        Returns:
            dict: Risk management settings with defaults if file unavailable
        """
        try:
            with open(FLAGS_FILE, 'r') as f:
                cfg = json.load(f)
                return cfg.get("risk_management", self._default_config())
        except Exception as e:
            print(f"[WARNING] Could not load risk config from {FLAGS_FILE}: {e}", file=sys.stderr)
            return self._default_config()

    def _default_config(self):
        """Return default risk management configuration"""
        return {
            "max_daily_loss_usd": 500,
            "max_concurrent_per_instrument": 2,
            "max_total_open_signals": 5,
            "correlation_check": True,
            "correlation_pairs": {
                "EURUSD": ["GBPUSD"],
                "GBPUSD": ["EURUSD"]
            }
        }

    def get_daily_loss(self):
        """
        Calculate cumulative daily P&L from signals_log.csv.

        Returns:
            float: Total P&L for today in USD (negative = loss)
        """
        if not os.path.exists(SIGNALS_LOG):
            return 0.0

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        total_pips = 0.0

        try:
            with open(SIGNALS_LOG, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    time_str = row.get("time", "")
                    # Extract date part (YYYY-MM-DD) from time column
                    if time_str.startswith(today):
                        pips_str = row.get("pips", "0")
                        # Handle empty pips (rejected trades, open positions)
                        if pips_str.strip():
                            try:
                                total_pips += float(pips_str)
                            except ValueError:
                                pass  # Skip non-numeric values
        except Exception as e:
            print(f"[WARNING] Error reading signals_log: {e}", file=sys.stderr)
            return 0.0

        # Convert pips to USD (1 pip = $0.10 for gold)
        PIP_VALUE = 0.10
        return total_pips * PIP_VALUE

    def get_open_positions(self):
        """
        Count currently open positions across all instruments.

        Scans TRADE_STATE files (~/.tv_fast_*_trade.json) for active trades.

        Returns:
            dict: {"per_instrument": {symbol: count, ...}, "total": int}
        """
        # TODO: Implement in subtask-2-3
        return {"per_instrument": {}, "total": 0}

    def check_correlation(self, symbol, direction):
        """
        Check if opening a position would violate correlation rules.

        Args:
            symbol: Instrument symbol (e.g., "GBPUSD")
            direction: Trade direction ("LONG" or "SHORT")

        Returns:
            dict: {"blocked": bool, "reason": str}
        """
        # TODO: Implement in subtask-2-4
        return {"blocked": False, "reason": ""}

    def risk_check(self, symbol, direction):
        """
        Main risk check entry point. Validates all risk limits before signal generation.

        Checks:
        - Daily loss limit
        - Max positions per instrument
        - Max total positions
        - Correlation constraints

        Args:
            symbol: Instrument symbol (e.g., "XAUUSD")
            direction: Trade direction ("LONG" or "SHORT")

        Returns:
            dict: {"allowed": bool, "reasons": [list of breach reasons]}
        """
        # TODO: Implement in subtask-2-5
        return {"allowed": True, "reasons": []}


if __name__ == "__main__":
    # Simple test interface
    print("RiskManager module test")
    rm = RiskManager()
    print(f"Config loaded: {rm.config}")
    print(f"Daily loss: ${rm.get_daily_loss():.2f}")
    print(f"Open positions: {rm.get_open_positions()}")
    check = rm.risk_check("XAUUSD", "LONG")
    print(f"Risk check XAUUSD LONG: allowed={check['allowed']}")
    print("Test complete!")
