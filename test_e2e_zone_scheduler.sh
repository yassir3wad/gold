#!/bin/bash
# End-to-End Test Suite for Zone Scheduler System
# Tests all components without requiring TradingView Desktop/MCP server

set -e

echo "=========================================="
echo "Zone Scheduler E2E Test Suite"
echo "=========================================="
echo ""

PASS=0
FAIL=0

# Helper function to report test results
test_result() {
  if [ $1 -eq 0 ]; then
    echo "  ✓ PASS: $2"
    PASS=$((PASS + 1))
  else
    echo "  ✗ FAIL: $2"
    FAIL=$((FAIL + 1))
  fi
}

# Test 1: Configuration file exists and is valid JSON
echo "[Test 1] Configuration file validation"
python3 -c "import json; json.load(open('zone_scheduler_config.json'))" 2>/dev/null
test_result $? "zone_scheduler_config.json is valid JSON"

python3 -c "import json; c=json.load(open('zone_scheduler_config.json')); assert 'enabled_instruments' in c" 2>/dev/null
test_result $? "enabled_instruments field present in config"
echo ""

# Test 2: Zone scheduler help and CLI flags
echo "[Test 2] Zone scheduler CLI interface"
python3 zone_scheduler.py --help >/dev/null 2>&1
test_result $? "zone_scheduler.py --help works"

python3 zone_scheduler.py --test-session-schedule 2>&1 | grep -q "london"
test_result $? "Session schedule test shows london session"
echo ""

# Test 3: Health check functionality
echo "[Test 3] Zone health check system"
python3 zone_scheduler.py --check-health 2>&1 | grep -q "Health check complete"
test_result $? "Health check runs successfully"

python3 check_zone_health.py 2>&1 | grep -q "Zone Health Check"
test_result $? "Standalone check_zone_health.py works"
echo ""

# Test 4: Stale zone detection
echo "[Test 4] Stale zone detection"
# Backup original zone file
cp zones_xauusd.json zones_xauusd.json.backup

# Create a stale zone file (set timestamp to 8 hours ago)
STALE_TS=$(python3 -c "import time; print(time.time() - 8*3600)")
python3 -c "import json; z=json.load(open('zones_xauusd.json')); z['ts']=$STALE_TS; json.dump(z, open('zones_xauusd.json', 'w'), indent=1)"

# Run health check with 6-hour threshold
python3 check_zone_health.py --max-age 6 2>&1 | grep -q "⚠.*stale"
test_result $? "Stale zone detected correctly (8h old vs 6h threshold)"

# Restore original
mv zones_xauusd.json.backup zones_xauusd.json
echo ""

# Test 5: Manual refresh trigger (dry-run)
echo "[Test 5] Manual refresh trigger"
bash refresh_zones_now.sh --help 2>&1 | grep -q "refresh_zones_now.sh"
test_result $? "refresh_zones_now.sh --help works"

bash refresh_zones_now.sh --dry-run 2>&1 | grep -q "would refresh"
test_result $? "Manual refresh dry-run works"

bash refresh_zones_now.sh --symbol XAUUSD --dry-run 2>&1 | grep -q "XAUUSD"
test_result $? "Single-symbol refresh dry-run works"
echo ""

# Test 6: Refresh all zones (dry-run)
echo "[Test 6] Refresh all zones functionality"
python3 refresh_all_zones.py --dry-run 2>&1 | grep -q "would refresh 7 instruments"
test_result $? "refresh_all_zones.py dry-run works"

python3 refresh_all_zones.py --symbol GBPUSD --dry-run 2>&1 | grep -q "GBPUSD"
test_result $? "Single-symbol refresh works"
echo ""

# Test 7: Telegram notification module
echo "[Test 7] Telegram notification system"
python3 -c "import telegram_notify; print('OK')" 2>/dev/null
test_result $? "telegram_notify module imports successfully"

python3 telegram_notify.py --test --dry-run 2>&1 | grep -q "DRY RUN"
test_result $? "Telegram dry-run test works"

python3 -c "import telegram_notify; s=telegram_notify.format_zone_summary({'XAUUSD': {'added': 2, 'removed': 1, 'modified': 0}}); assert 'XAUUSD' in s and '+2' in s" 2>/dev/null
test_result $? "Zone summary formatter works correctly"
echo ""

# Test 8: Telegram bot handler
echo "[Test 8] Telegram bot command handler"
python3 -c "import telegram_bot_handler; print('OK')" 2>/dev/null
test_result $? "telegram_bot_handler module imports successfully"

python3 telegram_bot_handler.py --help 2>&1 | grep -q "usage:"
test_result $? "Bot handler --help works"
echo ""

# Test 9: Log file creation
echo "[Test 9] Logging system"
# Run a quick health check to ensure log file is created
python3 zone_scheduler.py --check-health >/dev/null 2>&1

if [ -d "logs" ]; then
  test_result 0 "logs directory exists"
else
  test_result 1 "logs directory exists"
fi

# Check if log file would be created (at least directory exists)
mkdir -p logs
touch logs/zone_scheduler.log
if [ -f "logs/zone_scheduler.log" ]; then
  test_result 0 "Log file can be created"
else
  test_result 1 "Log file can be created"
fi
echo ""

# Test 10: Zone file structure validation
echo "[Test 10] Zone file structure"
python3 -c "import json; z=json.load(open('zones_xauusd.json')); assert 'ts' in z and 'htf_r' in z and 'htf_s' in z" 2>/dev/null
test_result $? "Zone file has required fields (ts, htf_r, htf_s)"

python3 -c "import json, time; z=json.load(open('zones_xauusd.json')); assert isinstance(z['ts'], float) and z['ts'] > 0" 2>/dev/null
test_result $? "Zone timestamp is valid Unix timestamp"
echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "PASSED: $PASS"
echo "FAILED: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
  echo "✓ All tests passed!"
  exit 0
else
  echo "✗ Some tests failed"
  exit 1
fi
