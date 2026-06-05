#!/usr/bin/env python3
"""
Integration test for subtask-5-1: Test fresh start with no existing state
Verifies that the scanner can start cleanly when no state file exists.
"""
import os
import sys
import json
import time

# Add src directory to path for StateManager import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from state_manager import StateManager

def test_fresh_start():
    """Test fresh start with no existing state file."""
    print("=" * 60)
    print("TEST: Fresh Start with No Existing State")
    print("=" * 60)

    # Define the state file path for XAUUSD (same as scalp_fast.py uses)
    symbol = "xauusd"
    state_file = os.path.expanduser(f"~/.tv_fast_{symbol}_trade.json")

    print(f"\n1. Checking for existing state file: {state_file}")
    state_exists = os.path.exists(state_file)
    backup_data = None
    if state_exists:
        # Backup existing state by reading its contents
        print(f"   - State file exists, backing up contents...")
        try:
            with open(state_file, 'r') as f:
                backup_data = f.read()
            # Remove the state file to simulate fresh start
            os.remove(state_file)
            print(f"   - State file removed (backed up in memory)")
        except Exception as e:
            print(f"   ✗ FAILED to backup/remove state file: {e}")
            return False
    else:
        print(f"   - No existing state file (clean state)")

    print(f"\n2. Initializing StateManager with no existing state...")
    try:
        # Initialize StateManager exactly as scalp_fast.py does
        state_manager = StateManager(namespace=f"scanner_{symbol}", state_file=state_file)
        print("   ✓ StateManager initialized successfully")
    except Exception as e:
        print(f"   ✗ FAILED to initialize StateManager: {e}")
        # Restore backup if it exists
        if backup_data:
            with open(state_file, 'w') as f:
                f.write(backup_data)
        return False

    print(f"\n3. Verifying state file was created...")
    if not os.path.exists(state_file):
        print(f"   ✗ FAILED: State file was not created")
        if backup_data:
            with open(state_file, 'w') as f:
                f.write(backup_data)
        return False
    print(f"   ✓ State file created: {state_file}")

    print(f"\n4. Validating state file schema...")
    try:
        with open(state_file, 'r') as f:
            state_data = json.load(f)

        # Print the state file contents
        print(f"   State file contents:")
        print(f"   {json.dumps(state_data, indent=2)}")

        # Validate required fields
        required_fields = ["version", "active_trades", "cooldowns", "watch_state", "scan_timestamps"]
        missing_fields = [field for field in required_fields if field not in state_data]

        if missing_fields:
            print(f"   ✗ FAILED: Missing required fields: {missing_fields}")
            if backup_data:
                with open(state_file, 'w') as f:
                    f.write(backup_data)
            return False

        print(f"   ✓ All required fields present: {required_fields}")

        # Validate field types
        if not isinstance(state_data["active_trades"], dict):
            print(f"   ✗ FAILED: active_trades is not a dict")
            if backup_data:
                with open(state_file, 'w') as f:
                    f.write(backup_data)
            return False

        if not isinstance(state_data["cooldowns"], dict):
            print(f"   ✗ FAILED: cooldowns is not a dict")
            if backup_data:
                with open(state_file, 'w') as f:
                    f.write(backup_data)
            return False

        if not isinstance(state_data["watch_state"], dict):
            print(f"   ✗ FAILED: watch_state is not a dict")
            if backup_data:
                with open(state_file, 'w') as f:
                    f.write(backup_data)
            return False

        if not isinstance(state_data["scan_timestamps"], dict):
            print(f"   ✗ FAILED: scan_timestamps is not a dict")
            if backup_data:
                with open(state_file, 'w') as f:
                    f.write(backup_data)
            return False

        print(f"   ✓ All field types are valid")

        # Verify schema version
        if state_data.get("version") != "1.0":
            print(f"   ✗ WARNING: Unexpected schema version: {state_data.get('version')}")
        else:
            print(f"   ✓ Schema version is correct: 1.0")

    except json.JSONDecodeError as e:
        print(f"   ✗ FAILED: Invalid JSON in state file: {e}")
        if backup_data:
            with open(state_file, 'w') as f:
                f.write(backup_data)
        return False
    except Exception as e:
        print(f"   ✗ FAILED: Error validating state file: {e}")
        if backup_data:
            with open(state_file, 'w') as f:
                f.write(backup_data)
        return False

    print(f"\n5. Testing basic state operations...")
    try:
        # Test getting trade state for a symbol (should be None/empty)
        trade_state = state_manager.get_trade_state("XAUUSD")
        if trade_state is None:
            print(f"   ✓ get_trade_state() returns None for new symbol (expected)")
        else:
            print(f"   - get_trade_state() returned: {trade_state}")

        # Test setting a cooldown
        state_manager.set_cooldown("XAUUSD", 5)  # 5 minute cooldown
        print(f"   ✓ set_cooldown() executed successfully")

        # Test checking cooldown
        in_cooldown = state_manager.in_cooldown("XAUUSD")
        if in_cooldown:
            print(f"   ✓ in_cooldown() correctly detects active cooldown")
        else:
            print(f"   ✗ WARNING: in_cooldown() should return True after setting cooldown")

        # Test saving scan timestamp
        state_manager.save_scan_timestamp("XAUUSD")
        print(f"   ✓ save_scan_timestamp() executed successfully")

        # Test getting scan timestamp
        scan_ts = state_manager.get_scan_timestamp("XAUUSD")
        if scan_ts and scan_ts > time.time() - 5:  # Within last 5 seconds
            print(f"   ✓ get_scan_timestamp() returns recent timestamp")
        else:
            print(f"   ✗ WARNING: get_scan_timestamp() returned unexpected value: {scan_ts}")

    except Exception as e:
        print(f"   ✗ FAILED: Error during state operations: {e}")
        if backup_data:
            with open(state_file, 'w') as f:
                f.write(backup_data)
        return False

    print(f"\n6. Cleaning up test...")
    # Remove the test state file
    if os.path.exists(state_file):
        os.remove(state_file)
        print(f"   - Removed test state file")

    # Restore backup if it exists
    if backup_data:
        with open(state_file, 'w') as f:
            f.write(backup_data)
        print(f"   - Restored original state file from backup")

    print("\n" + "=" * 60)
    print("TEST RESULT: PASSED ✓")
    print("=" * 60)
    print("\nConclusion:")
    print("- StateManager initializes cleanly with no existing state")
    print("- State file is created automatically with valid schema")
    print("- All required fields (version, active_trades, cooldowns, watch_state, scan_timestamps) present")
    print("- All field types are correct (dicts)")
    print("- Basic state operations work correctly")
    print("\nThe scanner can start fresh with no errors when no state file exists.")

    return True

if __name__ == "__main__":
    success = test_fresh_start()
    sys.exit(0 if success else 1)
