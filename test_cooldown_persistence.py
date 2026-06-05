#!/usr/bin/env python3
"""
Integration Test: Cooldown Persistence Across Scanner Restart

Tests the cooldown persistence use case from spec:
- Trigger a signal to start cooldown
- Immediately kill and restart scanner
- Verify cooldown is still active (no duplicate signal within cooldown window)
- Wait for cooldown to expire
- Verify new signal can fire

This test validates: "I don't want to receive duplicate Telegram alerts after restarting the scanner"
"""
import os
import sys
import time
import tempfile
import shutil

# Add src directory to path for StateManager import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from state_manager import StateManager


def test_cooldown_persistence():
    """Test cooldown persistence across scanner restart."""
    print("\n" + "="*80)
    print("TEST: Cooldown Persistence Across Scanner Restart")
    print("="*80)

    # Use temp directory for test isolation
    test_dir = tempfile.mkdtemp(prefix="tv_scanner_cooldown_test_")
    test_state_file = os.path.join(test_dir, "scanner_state.json")
    print(f"\n✓ Test state file: {test_state_file}")

    # Test with a short cooldown for faster testing (use fractional minutes for quick test)
    # Note: StateManager API uses minutes, so 2/60 = 0.0333 minutes = 2 seconds
    TEST_COOLDOWN_SECONDS = 2
    COOLDOWN_MINUTES = TEST_COOLDOWN_SECONDS / 60.0  # Convert to minutes for API compatibility

    print(f"✓ Using test cooldown: {TEST_COOLDOWN_SECONDS} seconds ({COOLDOWN_MINUTES:.4f} minutes)")

    try:
        # =====================================================================
        # PHASE 1: Signal Fires - Cooldown Started
        # =====================================================================
        print("\n" + "-"*80)
        print("PHASE 1: Signal Fires - Cooldown Started")
        print("-"*80)

        # Initialize StateManager for XAUUSD (first scanner instance)
        scanner1 = StateManager(namespace="scanner", state_file=test_state_file)
        print("✓ Scanner 1 initialized")

        # Simulate signal detection
        symbol = "XAUUSD"
        signal_id_1 = int(time.time())

        print(f"\n🚨 Signal #{signal_id_1} fired for {symbol}")
        print(f"   Signal Type: LONG breakout")
        print(f"   Entry: 2450.0")

        # Set cooldown (mimics what happens at line 943 in scalp_fast.py)
        # Note: set_cooldown expects minutes, not seconds
        cooldown_start_time = time.time()
        scanner1.set_cooldown(symbol, COOLDOWN_MINUTES)
        print(f"✓ Cooldown started at {cooldown_start_time}")

        # Verify cooldown is active immediately after setting
        # Note: in_cooldown expects minutes parameter
        is_in_cooldown = scanner1.in_cooldown(symbol, COOLDOWN_MINUTES)
        assert is_in_cooldown, "❌ FAILED: Cooldown should be active immediately after signal"
        print(f"✓ Cooldown is active (blocks duplicate signals)")

        # Get cooldown remaining time
        remaining = scanner1.get_cooldown_remaining(symbol, COOLDOWN_MINUTES)
        print(f"✓ Cooldown remaining: {remaining:.1f} seconds")
        assert remaining > 0, "❌ FAILED: Cooldown remaining should be > 0"

        # Verify state file was created with cooldown
        assert os.path.exists(test_state_file), "State file should exist after cooldown saved"
        print(f"✓ State file exists: {test_state_file}")

        # =====================================================================
        # PHASE 2: Scanner Restart (Simulated) - Cooldown Should Persist
        # =====================================================================
        print("\n" + "-"*80)
        print("PHASE 2: Scanner Restart - Cooldown Should Persist")
        print("-"*80)

        # Calculate elapsed time
        elapsed_before_restart = time.time() - cooldown_start_time
        print(f"\n⏱️  Elapsed time before restart: {elapsed_before_restart:.2f} seconds")
        print(f"💀 Simulating scanner kill (Ctrl+C)...")

        # Simulate scanner termination by deleting the scanner1 instance
        del scanner1
        print("✓ Scanner 1 terminated")

        # Small delay to simulate restart
        time.sleep(0.2)

        print("\n🔄 Restarting scanner...")

        # Create NEW StateManager instance (mimics scanner restart)
        # This should load the existing state from disk, including cooldown
        scanner2 = StateManager(namespace="scanner", state_file=test_state_file)
        print("✓ Scanner 2 initialized")

        # =====================================================================
        # PHASE 3: Verify Cooldown Still Active After Restart
        # =====================================================================
        print("\n" + "-"*80)
        print("PHASE 3: Verify Cooldown Still Active After Restart")
        print("-"*80)

        # Calculate elapsed time since cooldown started
        elapsed_after_restart = time.time() - cooldown_start_time
        print(f"\n⏱️  Total elapsed time: {elapsed_after_restart:.2f} seconds")

        # Check if cooldown is still active (should be, since we just restarted)
        is_in_cooldown_after = scanner2.in_cooldown(symbol, COOLDOWN_MINUTES)

        assert is_in_cooldown_after, "❌ FAILED: Cooldown should still be active after restart"
        print("✓ Cooldown STILL ACTIVE after restart")

        # Get remaining cooldown time
        remaining_after = scanner2.get_cooldown_remaining(symbol, COOLDOWN_MINUTES)
        print(f"✓ Cooldown remaining: {remaining_after:.1f} seconds")
        assert remaining_after > 0, "❌ FAILED: Cooldown remaining should be > 0"
        assert remaining_after <= TEST_COOLDOWN_SECONDS, "❌ FAILED: Remaining should be <= original cooldown"

        # Simulate duplicate signal detection after restart
        print("\n🔍 Attempting to fire duplicate signal...")
        signal_id_2 = int(time.time())

        # This mimics the cooldown check at line 601 in scalp_fast.py
        if scanner2.in_cooldown(symbol, COOLDOWN_MINUTES):
            print(f"✓ Signal #{signal_id_2} BLOCKED by cooldown (no duplicate alert)")
            print("✓ Duplicate Telegram alert PREVENTED")
        else:
            print(f"❌ FAILED: Signal #{signal_id_2} would fire (DUPLICATE ALERT)")
            assert False, "Duplicate signal should be blocked by cooldown"

        # =====================================================================
        # PHASE 4: Wait for Cooldown to Expire
        # =====================================================================
        print("\n" + "-"*80)
        print("PHASE 4: Wait for Cooldown to Expire")
        print("-"*80)

        # Calculate how long we need to wait
        remaining = scanner2.get_cooldown_remaining(symbol, COOLDOWN_MINUTES)
        wait_time = remaining + 0.5  # Add 0.5s buffer to ensure expiration

        print(f"\n⏳ Waiting {wait_time:.1f} seconds for cooldown to expire...")
        time.sleep(wait_time)

        elapsed_final = time.time() - cooldown_start_time
        print(f"⏱️  Total elapsed time: {elapsed_final:.2f} seconds")

        # Check cooldown is now expired
        is_in_cooldown_expired = scanner2.in_cooldown(symbol, COOLDOWN_MINUTES)
        assert not is_in_cooldown_expired, "❌ FAILED: Cooldown should be expired"
        print("✓ Cooldown EXPIRED")

        # Verify remaining time is 0
        remaining_expired = scanner2.get_cooldown_remaining(symbol, COOLDOWN_MINUTES)
        assert remaining_expired == 0.0, "❌ FAILED: Cooldown remaining should be 0"
        print("✓ Cooldown remaining: 0.0 seconds")

        # =====================================================================
        # PHASE 5: Verify New Signal Can Fire After Expiration
        # =====================================================================
        print("\n" + "-"*80)
        print("PHASE 5: Verify New Signal Can Fire After Expiration")
        print("-"*80)

        print("\n🔍 Attempting to fire new signal after cooldown expired...")
        signal_id_3 = int(time.time())

        # This mimics the cooldown check at line 601 in scalp_fast.py
        if scanner2.in_cooldown(symbol, COOLDOWN_MINUTES):
            print(f"❌ FAILED: Signal #{signal_id_3} blocked (cooldown should be expired)")
            assert False, "New signal should be allowed after cooldown expires"
        else:
            print(f"✓ Signal #{signal_id_3} ALLOWED (cooldown expired)")
            print("✓ New signal can fire")
            print("✓ New Telegram alert would be sent")

        # Set new cooldown for this signal
        scanner2.set_cooldown(symbol, COOLDOWN_MINUTES)
        print("✓ New cooldown started for signal #3")

        # =====================================================================
        # PHASE 6: Another Restart - Verify New Cooldown Persists
        # =====================================================================
        print("\n" + "-"*80)
        print("PHASE 6: Another Restart - Verify New Cooldown Persists")
        print("-"*80)

        print("\n💀 Simulating another scanner kill...")
        cooldown_start_time_2 = time.time()
        del scanner2
        time.sleep(0.2)

        print("🔄 Restarting scanner again...")
        scanner3 = StateManager(namespace="scanner", state_file=test_state_file)
        print("✓ Scanner 3 initialized")

        # Verify new cooldown is still active
        is_in_cooldown_new = scanner3.in_cooldown(symbol, COOLDOWN_MINUTES)
        assert is_in_cooldown_new, "❌ FAILED: New cooldown should be active after restart"
        print("✓ New cooldown STILL ACTIVE after restart")

        remaining_new = scanner3.get_cooldown_remaining(symbol, COOLDOWN_MINUTES)
        print(f"✓ New cooldown remaining: {remaining_new:.1f} seconds")
        assert remaining_new > 0, "❌ FAILED: New cooldown remaining should be > 0"

        # =====================================================================
        # PHASE 7: Test Multiple Symbols (Multi-Instrument Isolation)
        # =====================================================================
        print("\n" + "-"*80)
        print("PHASE 7: Test Multiple Symbols (Multi-Instrument Isolation)")
        print("-"*80)

        # Test that cooldowns are per-symbol (XAUUSD cooldown doesn't affect GBPUSD)
        symbol2 = "GBPUSD"
        print(f"\n🔍 Testing cooldown isolation between symbols...")
        print(f"   {symbol} is in cooldown")
        print(f"   {symbol2} should NOT be in cooldown")

        # Check GBPUSD cooldown (should not exist)
        is_gbpusd_cooldown = scanner3.in_cooldown(symbol2, COOLDOWN_MINUTES)
        assert not is_gbpusd_cooldown, f"❌ FAILED: {symbol2} should not be in cooldown"
        print(f"✓ {symbol2} NOT in cooldown (correct isolation)")

        # Fire signal for GBPUSD
        signal_id_gbpusd = int(time.time())
        print(f"\n🚨 Signal #{signal_id_gbpusd} fired for {symbol2}")
        scanner3.set_cooldown(symbol2, COOLDOWN_MINUTES)
        print(f"✓ Cooldown started for {symbol2}")

        # Verify both symbols now have independent cooldowns
        xauusd_cooldown = scanner3.in_cooldown(symbol, COOLDOWN_MINUTES)
        gbpusd_cooldown = scanner3.in_cooldown(symbol2, COOLDOWN_MINUTES)

        assert xauusd_cooldown, f"❌ FAILED: {symbol} should still be in cooldown"
        assert gbpusd_cooldown, f"❌ FAILED: {symbol2} should be in cooldown"
        print(f"✓ Both symbols have independent cooldowns")
        print(f"   {symbol}: {scanner3.get_cooldown_remaining(symbol, COOLDOWN_MINUTES):.1f}s remaining")
        print(f"   {symbol2}: {scanner3.get_cooldown_remaining(symbol2, COOLDOWN_MINUTES):.1f}s remaining")

        # =====================================================================
        # TEST COMPLETE
        # =====================================================================
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)
        print("\nVerified:")
        print("  ✓ Cooldown is set when signal fires")
        print("  ✓ Cooldown persists across scanner restart")
        print("  ✓ Duplicate signals blocked within cooldown window")
        print("  ✓ Duplicate Telegram alerts prevented after restart")
        print("  ✓ Cooldown remaining time calculated correctly")
        print("  ✓ New signals can fire after cooldown expires")
        print("  ✓ Multiple restarts preserve cooldown state correctly")
        print("  ✓ Per-symbol cooldown isolation works correctly")
        print("\n🎉 Cooldown persistence across restart: WORKING CORRECTLY")
        print("\nUser Story Validated:")
        print("  'I don't want to receive duplicate Telegram alerts after restarting the scanner' ✓")

        return True

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup test directory
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"\n🧹 Cleaned up test directory: {test_dir}")


if __name__ == "__main__":
    success = test_cooldown_persistence()
    sys.exit(0 if success else 1)
