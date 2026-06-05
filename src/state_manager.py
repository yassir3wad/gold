#!/usr/bin/env python3
"""
Consolidated StateManager for scanner persistence across restarts.
Provides schema-validated JSON storage with atomic writes and graceful degradation.
"""
import json
import os
import time
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Schema version for state file
SCHEMA_VERSION = "1.0"

# Default state file location
DEFAULT_STATE_FILE = os.path.expanduser("~/.tv_scanner_state.json")


class StateManager:
    """
    Consolidated state manager for scanner with schema-validated JSON storage.

    Features:
    - Atomic writes (write to .tmp then rename)
    - Schema validation with graceful degradation
    - Per-symbol state management for trades, cooldowns, watch state, and scan timestamps
    """

    def __init__(self, namespace: str = "scanner", state_file: Optional[str] = None):
        """
        Initialize StateManager.

        Args:
            namespace: Namespace for this state manager instance (e.g., 'scanner', 'test')
            state_file: Optional custom state file path. If None, uses DEFAULT_STATE_FILE
        """
        self.namespace = namespace
        self.state_file = state_file or DEFAULT_STATE_FILE
        self._state = self._load_state()

    def _get_default_state(self) -> Dict[str, Any]:
        """Return default empty state structure."""
        return {
            "version": SCHEMA_VERSION,
            "active_trades": {},
            "cooldowns": {},
            "watch_state": {},
            "scan_timestamps": {}
        }

    def _load_state(self) -> Dict[str, Any]:
        """
        Load state from disk with graceful degradation.

        Returns:
            State dictionary. Returns empty default state if file doesn't exist or is corrupted.
        """
        if not os.path.exists(self.state_file):
            logger.info(f"State file not found at {self.state_file}. Starting with fresh state.")
            return self._get_default_state()

        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)

            # Validate schema
            if not self._validate_schema(state):
                logger.warning(f"State file schema validation failed. Starting with fresh state.")
                return self._get_default_state()

            logger.info(f"Loaded state from {self.state_file}")
            return state

        except json.JSONDecodeError as e:
            logger.warning(f"State file corrupted (invalid JSON): {e}. Starting with fresh state.")
            return self._get_default_state()

        except Exception as e:
            logger.warning(f"Failed to load state file: {e}. Starting with fresh state.")
            return self._get_default_state()

    def _validate_schema(self, state: Dict[str, Any], require_version: bool = True) -> bool:
        """
        Validate state schema structure.

        Args:
            state: State dictionary to validate
            require_version: Whether to require the "version" key (default True)

        Returns:
            True if schema is valid, False otherwise
        """
        try:
            # Check required top-level keys
            required_keys = {"active_trades", "cooldowns", "watch_state", "scan_timestamps"}
            if require_version:
                required_keys.add("version")

            if not all(key in state for key in required_keys):
                return False

            # Check types
            if not isinstance(state["active_trades"], dict):
                return False
            if not isinstance(state["cooldowns"], dict):
                return False
            if not isinstance(state["watch_state"], dict):
                return False
            if not isinstance(state["scan_timestamps"], dict):
                return False

            return True

        except Exception:
            return False

    def _save_state(self):
        """
        Save state to disk using atomic write (write to .tmp then rename).

        This ensures the state file is never left in a partially-written state.
        """
        try:
            tmp_file = f"{self.state_file}.tmp"

            # Write to temp file first
            with open(tmp_file, 'w') as f:
                json.dump(self._state, f, indent=2)

            # Atomic rename
            os.rename(tmp_file, self.state_file)

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    # Trade state methods

    def save_trade_state(self, symbol: str, trade_data: Dict[str, Any]):
        """
        Save trade state for a symbol.

        Args:
            symbol: Trading symbol (e.g., 'XAUUSD')
            trade_data: Trade data dictionary
        """
        try:
            self._state["active_trades"][symbol] = trade_data
            self._save_state()
        except Exception as e:
            logger.error(f"Failed to save trade state for {symbol}: {e}")

    def get_trade_state(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get trade state for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Trade data dictionary or None if not found
        """
        try:
            return self._state["active_trades"].get(symbol)
        except Exception:
            return None

    def set_active_trade(self, symbol: str, side: str, entry: float, sl: float,
                        tp1: float, tp2: float, signal_id: int, be_trig: float = None):
        """
        Set active trade for a symbol.

        Args:
            symbol: Trading symbol
            side: 'LONG' or 'SHORT'
            entry: Entry price
            sl: Stop loss price
            tp1: First take profit price
            tp2: Second take profit price
            signal_id: Unique signal ID
            be_trig: Breakeven trigger price (optional)
        """
        try:
            trade_data = {
                "active": True,
                "id": signal_id,
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "tp1_hit": False,
                "be_trig": be_trig,
                "t0": time.time()
            }
            self.save_trade_state(symbol, trade_data)
        except Exception as e:
            logger.error(f"Failed to set active trade for {symbol}: {e}")

    def get_active_trade(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get active trade for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Trade data if active, None otherwise
        """
        try:
            trade = self.get_trade_state(symbol)
            if trade and trade.get("active"):
                return trade
            return None
        except Exception:
            return None

    def clear_active_trade(self, symbol: str):
        """
        Clear active trade for a symbol.

        Args:
            symbol: Trading symbol
        """
        try:
            if symbol in self._state["active_trades"]:
                del self._state["active_trades"][symbol]
                self._save_state()
        except Exception as e:
            logger.error(f"Failed to clear active trade for {symbol}: {e}")

    def update_trade_state(self, symbol: str, updates: Dict[str, Any]):
        """
        Update specific fields in trade state.

        Args:
            symbol: Trading symbol
            updates: Dictionary of fields to update
        """
        try:
            if symbol in self._state["active_trades"]:
                self._state["active_trades"][symbol].update(updates)
                self._save_state()
        except Exception as e:
            logger.error(f"Failed to update trade state for {symbol}: {e}")

    def get_all_active_trades(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active trades across all symbols.

        Returns:
            Dictionary mapping symbols to their active trade data
        """
        try:
            return {
                symbol: trade
                for symbol, trade in self._state["active_trades"].items()
                if trade.get("active")
            }
        except Exception:
            return {}

    # Cooldown methods

    def save_cooldown(self, symbol: str, timestamp: float = None):
        """
        Save cooldown timestamp for a symbol.

        Args:
            symbol: Trading symbol
            timestamp: Unix timestamp. If None, uses current time.
        """
        try:
            self._state["cooldowns"][symbol] = timestamp or time.time()
            self._save_state()
        except Exception as e:
            logger.error(f"Failed to save cooldown for {symbol}: {e}")

    def check_cooldown(self, symbol: str, cooldown_seconds: int) -> bool:
        """
        Check if symbol is in cooldown period.

        Args:
            symbol: Trading symbol
            cooldown_seconds: Cooldown duration in seconds

        Returns:
            True if in cooldown, False if cooldown expired or not set
        """
        try:
            cd_time = self._state["cooldowns"].get(symbol)
            if cd_time is None:
                return False

            elapsed = time.time() - cd_time
            return elapsed < cooldown_seconds
        except Exception:
            return False

    def set_cooldown(self, symbol: str, cooldown_minutes: int):
        """
        Set cooldown for a symbol (convenience method).

        Args:
            symbol: Trading symbol
            cooldown_minutes: Cooldown duration in minutes
        """
        self.save_cooldown(symbol, time.time())

    def in_cooldown(self, symbol: str, cooldown_minutes: int = 5) -> bool:
        """
        Check if symbol is in cooldown period (convenience method).

        Args:
            symbol: Trading symbol
            cooldown_minutes: Cooldown duration in minutes (default: 5)

        Returns:
            True if in cooldown, False otherwise
        """
        return self.check_cooldown(symbol, cooldown_minutes * 60)

    def get_cooldown_remaining(self, symbol: str, cooldown_minutes: int = 5) -> float:
        """
        Get remaining cooldown time in seconds (convenience method).

        Args:
            symbol: Trading symbol
            cooldown_minutes: Cooldown duration in minutes (default: 5)

        Returns:
            Remaining cooldown time in seconds, or 0 if not in cooldown
        """
        try:
            cd_time = self._state["cooldowns"].get(symbol)
            if cd_time is None:
                return 0.0

            elapsed = time.time() - cd_time
            remaining_seconds = (cooldown_minutes * 60) - elapsed

            if remaining_seconds > 0:
                return remaining_seconds
            else:
                return 0.0
        except Exception:
            return 0.0

    # Watch state methods

    def save_watch_state(self, symbol: str, watch_data: Dict[str, Any]):
        """
        Save watch state for a symbol.

        Args:
            symbol: Trading symbol
            watch_data: Watch data dictionary (e.g., {t: timestamp, price: float, label: str})
        """
        try:
            self._state["watch_state"][symbol] = watch_data
            self._save_state()
        except Exception as e:
            logger.error(f"Failed to save watch state for {symbol}: {e}")

    def get_watch_state(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get watch state for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Watch data dictionary or None if not found
        """
        try:
            return self._state["watch_state"].get(symbol)
        except Exception:
            return None

    # Scan timestamp methods

    def save_scan_timestamp(self, symbol: str, timestamp: float = None):
        """
        Save last scan timestamp for a symbol.

        Args:
            symbol: Trading symbol
            timestamp: Unix timestamp. If None, uses current time.
        """
        try:
            self._state["scan_timestamps"][symbol] = timestamp or time.time()
            self._save_state()
        except Exception as e:
            logger.error(f"Failed to save scan timestamp for {symbol}: {e}")

    def get_scan_timestamp(self, symbol: str) -> Optional[float]:
        """
        Get last scan timestamp for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Unix timestamp or None if not found
        """
        try:
            return self._state["scan_timestamps"].get(symbol)
        except Exception:
            return None

    # Migration methods

    def import_legacy_state(self, symbol: str, file_path: str, state_type: str):
        """
        Import legacy state file into consolidated state.

        Args:
            symbol: Trading symbol
            file_path: Path to legacy state file
            state_type: Type of state ('trade', 'cd', 'watch', 'vp')
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"Legacy state file not found: {file_path}")
                return

            with open(file_path, 'r') as f:
                legacy_data = json.load(f)

            if state_type == 'trade':
                # Migrate trade state
                if legacy_data.get("active"):
                    self._state["active_trades"][symbol] = legacy_data
                    logger.info(f"Migrated active trade for {symbol} from {file_path}")

            elif state_type == 'cd':
                # Migrate cooldown - assume the file contains a timestamp or dict with timestamp
                if isinstance(legacy_data, (int, float)):
                    self._state["cooldowns"][symbol] = legacy_data
                elif isinstance(legacy_data, dict) and 't' in legacy_data:
                    self._state["cooldowns"][symbol] = legacy_data['t']
                logger.info(f"Migrated cooldown for {symbol} from {file_path}")

            elif state_type == 'watch':
                # Migrate watch state
                self._state["watch_state"][symbol] = legacy_data
                logger.info(f"Migrated watch state for {symbol} from {file_path}")

            self._save_state()

        except Exception as e:
            logger.error(f"Failed to import legacy state from {file_path}: {e}")

    def validate_schema(self, state: Dict[str, Any]) -> bool:
        """
        Public method to validate schema (used in tests).
        Does not require the "version" key, only validates core state structure.

        Args:
            state: State dictionary to validate

        Returns:
            True if schema is valid, False otherwise
        """
        return self._validate_schema(state, require_version=False)
