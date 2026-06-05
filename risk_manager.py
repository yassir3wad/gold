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
        import glob

        per_instrument = {}
        total = 0

        # Scan for all trade state files matching the pattern
        home = os.path.expanduser("~")
        pattern = os.path.join(home, ".tv_fast_*_trade.json")

        for filepath in glob.glob(pattern):
            try:
                with open(filepath, 'r') as f:
                    trade_state = json.load(f)

                # Check if this is an active trade
                if trade_state.get("active", False):
                    # Extract symbol from filename: ~/.tv_fast_SYMBOL_trade.json
                    basename = os.path.basename(filepath)
                    # Remove prefix ".tv_fast_" and suffix "_trade.json"
                    if basename.startswith(".tv_fast_") and basename.endswith("_trade.json"):
                        symbol = basename[9:-11]  # Strip ".tv_fast_" (9 chars) and "_trade.json" (11 chars)
                    else:
                        # Handle default file: ~/.tv_fast_trade.json (no symbol in name, default to XAUUSD)
                        symbol = "XAUUSD"

                    # Count this position
                    per_instrument[symbol] = per_instrument.get(symbol, 0) + 1
                    total += 1

            except Exception as e:
                # Skip files that can't be read or parsed
                print(f"[WARNING] Could not read trade state {filepath}: {e}", file=sys.stderr)
                continue

        return {"per_instrument": per_instrument, "total": total}

    def check_correlation(self, symbol, direction):
        """
        Check if opening a position would violate correlation rules.

        Args:
            symbol: Instrument symbol (e.g., "GBPUSD")
            direction: Trade direction ("LONG" or "SHORT")

        Returns:
            dict: {"blocked": bool, "reason": str}
        """
        import glob

        # Skip if correlation checking is disabled
        if not self.config.get("correlation_check", False):
            return {"blocked": False, "reason": ""}

        # Get correlated pairs for this symbol
        correlation_pairs = self.config.get("correlation_pairs", {})
        correlated_symbols = correlation_pairs.get(symbol, [])

        # If no correlated pairs defined, allow trade
        if not correlated_symbols:
            return {"blocked": False, "reason": ""}

        # Check for open positions in correlated pairs
        home = os.path.expanduser("~")

        for correlated_symbol in correlated_symbols:
            # Look for trade state file for this correlated symbol
            pattern = os.path.join(home, f".tv_fast_{correlated_symbol}_trade.json")
            files = glob.glob(pattern)

            for filepath in files:
                try:
                    with open(filepath, 'r') as f:
                        trade_state = json.load(f)

                    # Check if trade is active and in same direction
                    if trade_state.get("active", False):
                        trade_direction = trade_state.get("direction", "").upper()

                        if trade_direction == direction.upper():
                            return {
                                "blocked": True,
                                "reason": f"Correlated position already open: {correlated_symbol} {trade_direction}"
                            }
                except Exception as e:
                    # Skip files that can't be read
                    print(f"[WARNING] Could not read trade state {filepath}: {e}", file=sys.stderr)
                    continue

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
        reasons = []

        # 1. Check daily loss limit
        daily_pnl = self.get_daily_loss()
        max_loss = self.config.get("max_daily_loss_usd", 500)
        if daily_pnl < 0 and abs(daily_pnl) >= max_loss:
            reasons.append(f"Daily loss limit reached: ${abs(daily_pnl):.2f} / ${max_loss:.2f}")

        # 2. Check position limits
        positions = self.get_open_positions()

        # Check per-instrument limit
        per_instrument = positions.get("per_instrument", {})
        current_count = per_instrument.get(symbol, 0)
        max_per_instrument = self.config.get("max_concurrent_per_instrument", 2)
        if current_count >= max_per_instrument:
            reasons.append(f"{symbol} position limit reached: {current_count} / {max_per_instrument}")

        # Check total position limit
        total_count = positions.get("total", 0)
        max_total = self.config.get("max_total_open_signals", 5)
        if total_count >= max_total:
            reasons.append(f"Total position limit reached: {total_count} / {max_total}")

        # 3. Check correlation constraints
        correlation_check = self.check_correlation(symbol, direction)
        if correlation_check.get("blocked", False):
            reasons.append(correlation_check.get("reason", "Correlation conflict"))

        # Return result
        allowed = len(reasons) == 0
        return {"allowed": allowed, "reasons": reasons}


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
