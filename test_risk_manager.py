#!/usr/bin/env python3
"""Test suite for RiskManager — daily loss limits, position limits, correlation checks.
Pure stdlib, no pytest. Run:  python3 test_risk_manager.py   (exit 0 = all pass, 1 = a failure).

Covers: config loading, daily loss calculation from signals_log.csv, open position counting
from trade state files, correlation checks, and full risk_check() integration with all gates."""
import os, sys, json, csv, tempfile, datetime as dt

# Import the RiskManager from the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import risk_manager as rm

_results = []
def check(name, cond):
    """Track test results"""
    _results.append((name, bool(cond)))

def approx(a, b, tol=1e-6):
    """Float comparison with tolerance"""
    return a is not None and b is not None and abs(a - b) <= tol


# ─────────────────────────────────────────────────────────────────────────────
# 1) Config loading and defaults
# ─────────────────────────────────────────────────────────────────────────────
def test_default_config():
    """Test default configuration values"""
    config = rm.RiskManager()._default_config()
    check("config: has max_daily_loss_usd", "max_daily_loss_usd" in config)
    check("config: default loss limit is 500", config["max_daily_loss_usd"] == 500)
    check("config: has max_concurrent_per_instrument", "max_concurrent_per_instrument" in config)
    check("config: default per-instrument is 2", config["max_concurrent_per_instrument"] == 2)
    check("config: has max_total_open_signals", "max_total_open_signals" in config)
    check("config: default total signals is 5", config["max_total_open_signals"] == 5)
    check("config: has correlation_check", "correlation_check" in config)
    check("config: correlation enabled by default", config["correlation_check"] is True)
    check("config: has correlation_pairs", "correlation_pairs" in config)
    check("config: EURUSD correlates with GBPUSD", "GBPUSD" in config["correlation_pairs"].get("EURUSD", []))


def test_config_loading_with_temp_file():
    """Test loading configuration from a temporary flags.json"""
    with tempfile.TemporaryDirectory() as tmpdir:
        flags_path = os.path.join(tmpdir, "flags.json")

        # Create a custom config
        custom_config = {
            "risk_management": {
                "max_daily_loss_usd": 1000,
                "max_concurrent_per_instrument": 3,
                "max_total_open_signals": 10,
                "correlation_check": False,
                "correlation_pairs": {}
            }
        }

        with open(flags_path, 'w') as f:
            json.dump(custom_config, f)

        # Override FLAGS_FILE path temporarily
        original_flags = rm.FLAGS_FILE
        rm.FLAGS_FILE = flags_path

        try:
            manager = rm.RiskManager()
            check("config: custom max_daily_loss loaded", manager.config["max_daily_loss_usd"] == 1000)
            check("config: custom per_instrument loaded", manager.config["max_concurrent_per_instrument"] == 3)
            check("config: custom total_signals loaded", manager.config["max_total_open_signals"] == 10)
            check("config: correlation_check disabled", manager.config["correlation_check"] is False)
        finally:
            rm.FLAGS_FILE = original_flags


# ─────────────────────────────────────────────────────────────────────────────
# 2) Daily loss calculation from signals_log.csv
# ─────────────────────────────────────────────────────────────────────────────
def test_daily_loss_empty_log():
    """Test daily loss with no log file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        nonexistent_log = os.path.join(tmpdir, "nonexistent.csv")
        original_log = rm.SIGNALS_LOG
        rm.SIGNALS_LOG = nonexistent_log

        try:
            manager = rm.RiskManager()
            loss = manager.get_daily_loss()
            check("daily_loss: empty log returns 0", approx(loss, 0.0))
        finally:
            rm.SIGNALS_LOG = original_log


def test_daily_loss_calculation():
    """Test daily loss calculation with sample trades"""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "signals_log.csv")
        today = dt.datetime.now().strftime("%Y-%m-%d")
        yesterday = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%Y-%m-%d")

        # Create a signals log with mixed dates and outcomes
        rows = [
            {"time": f"{today} 09:00", "sym": "XAUUSD", "pips": "50", "result": "TP1"},     # +50 pips today
            {"time": f"{today} 10:00", "sym": "XAUUSD", "pips": "-35", "result": "SL"},    # -35 pips today
            {"time": f"{today} 11:00", "sym": "XAUUSD", "pips": "20", "result": "TP1"},    # +20 pips today
            {"time": f"{yesterday} 09:00", "sym": "XAUUSD", "pips": "100", "result": "TP1"}, # yesterday (excluded)
            {"time": f"{today} 12:00", "sym": "XAUUSD", "pips": "", "result": "PENDING"},  # pending (no pips)
        ]

        with open(log_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["time", "sym", "pips", "result"])
            writer.writeheader()
            writer.writerows(rows)

        original_log = rm.SIGNALS_LOG
        rm.SIGNALS_LOG = log_path

        try:
            manager = rm.RiskManager()
            loss = manager.get_daily_loss()
            # Total today: 50 - 35 + 20 = 35 pips
            # 35 pips × $0.10 = $3.50
            check("daily_loss: sums only today's trades", approx(loss, 3.5))
        finally:
            rm.SIGNALS_LOG = original_log


def test_daily_loss_with_losses():
    """Test daily loss when in drawdown"""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "signals_log.csv")
        today = dt.datetime.now().strftime("%Y-%m-%d")

        # Create a losing day
        rows = [
            {"time": f"{today} 09:00", "sym": "XAUUSD", "pips": "-35", "result": "SL"},
            {"time": f"{today} 10:00", "sym": "XAUUSD", "pips": "-35", "result": "SL"},
            {"time": f"{today} 11:00", "sym": "XAUUSD", "pips": "-35", "result": "SL"},
        ]

        with open(log_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["time", "sym", "pips", "result"])
            writer.writeheader()
            writer.writerows(rows)

        original_log = rm.SIGNALS_LOG
        rm.SIGNALS_LOG = log_path

        try:
            manager = rm.RiskManager()
            loss = manager.get_daily_loss()
            # Total: -105 pips × $0.10 = -$10.50
            check("daily_loss: negative when losing", loss < 0)
            check("daily_loss: correct loss amount", approx(loss, -10.5))
        finally:
            rm.SIGNALS_LOG = original_log


# ─────────────────────────────────────────────────────────────────────────────
# 3) Open position counting from trade state files
# ─────────────────────────────────────────────────────────────────────────────
def test_open_positions_none():
    """Test position counting with no open trades"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Temporarily override home directory
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            positions = manager.get_open_positions()
            check("positions: no trades gives empty dict", len(positions["per_instrument"]) == 0)
            check("positions: total is 0", positions["total"] == 0)
        finally:
            if original_home:
                os.environ["HOME"] = original_home


def test_open_positions_single_instrument():
    """Test counting positions for single instrument"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an active trade state file
        trade_file = os.path.join(tmpdir, ".tv_fast_XAUUSD_trade.json")
        with open(trade_file, 'w') as f:
            json.dump({"active": True, "direction": "LONG", "entry": 2450.0}, f)

        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            positions = manager.get_open_positions()
            check("positions: XAUUSD count is 1", positions["per_instrument"].get("XAUUSD") == 1)
            check("positions: total is 1", positions["total"] == 1)
        finally:
            if original_home:
                os.environ["HOME"] = original_home


def test_open_positions_multiple_instruments():
    """Test counting positions across multiple instruments"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create multiple trade state files
        trades = [
            (".tv_fast_XAUUSD_trade.json", {"active": True, "direction": "LONG"}),
            (".tv_fast_EURUSD_trade.json", {"active": True, "direction": "SHORT"}),
            (".tv_fast_GBPUSD_trade.json", {"active": True, "direction": "LONG"}),
        ]

        for filename, data in trades:
            with open(os.path.join(tmpdir, filename), 'w') as f:
                json.dump(data, f)

        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            positions = manager.get_open_positions()
            check("positions: XAUUSD counted", positions["per_instrument"].get("XAUUSD") == 1)
            check("positions: EURUSD counted", positions["per_instrument"].get("EURUSD") == 1)
            check("positions: GBPUSD counted", positions["per_instrument"].get("GBPUSD") == 1)
            check("positions: total is 3", positions["total"] == 3)
        finally:
            if original_home:
                os.environ["HOME"] = original_home


def test_open_positions_inactive_ignored():
    """Test that inactive trades are not counted"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create active and inactive trades
        active_file = os.path.join(tmpdir, ".tv_fast_XAUUSD_trade.json")
        inactive_file = os.path.join(tmpdir, ".tv_fast_EURUSD_trade.json")

        with open(active_file, 'w') as f:
            json.dump({"active": True, "direction": "LONG"}, f)

        with open(inactive_file, 'w') as f:
            json.dump({"active": False, "direction": "SHORT"}, f)

        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            positions = manager.get_open_positions()
            check("positions: only active trades counted", positions["total"] == 1)
            check("positions: inactive EURUSD not counted", "EURUSD" not in positions["per_instrument"])
        finally:
            if original_home:
                os.environ["HOME"] = original_home


# ─────────────────────────────────────────────────────────────────────────────
# 4) Correlation checks
# ─────────────────────────────────────────────────────────────────────────────
def test_correlation_check_disabled():
    """Test correlation check when disabled in config"""
    with tempfile.TemporaryDirectory() as tmpdir:
        flags_path = os.path.join(tmpdir, "flags.json")
        with open(flags_path, 'w') as f:
            json.dump({"risk_management": {"correlation_check": False}}, f)

        original_flags = rm.FLAGS_FILE
        rm.FLAGS_FILE = flags_path

        try:
            manager = rm.RiskManager()
            result = manager.check_correlation("GBPUSD", "LONG")
            check("correlation: disabled returns not blocked", result["blocked"] is False)
        finally:
            rm.FLAGS_FILE = original_flags


def test_correlation_no_conflicts():
    """Test correlation check with no conflicting positions"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            result = manager.check_correlation("GBPUSD", "LONG")
            check("correlation: no conflicts returns not blocked", result["blocked"] is False)
        finally:
            if original_home:
                os.environ["HOME"] = original_home


def test_correlation_blocked_same_direction():
    """Test correlation blocking when correlated position exists in same direction"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create flags.json with default correlation config
        flags_path = os.path.join(tmpdir, "flags.json")
        with open(flags_path, 'w') as f:
            json.dump({
                "risk_management": {
                    "correlation_check": True,
                    "correlation_pairs": {
                        "EURUSD": ["GBPUSD"],
                        "GBPUSD": ["EURUSD"]
                    }
                }
            }, f)

        # Create an active EURUSD LONG position
        eurusd_trade = os.path.join(tmpdir, ".tv_fast_EURUSD_trade.json")
        with open(eurusd_trade, 'w') as f:
            json.dump({"active": True, "direction": "LONG"}, f)

        original_flags = rm.FLAGS_FILE
        original_home = os.environ.get("HOME")
        rm.FLAGS_FILE = flags_path
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            # Try to open GBPUSD LONG (correlated with EURUSD)
            result = manager.check_correlation("GBPUSD", "LONG")
            check("correlation: blocks correlated LONG", result["blocked"] is True)
            check("correlation: provides reason", "EURUSD" in result["reason"])
        finally:
            rm.FLAGS_FILE = original_flags
            if original_home:
                os.environ["HOME"] = original_home


def test_correlation_allowed_opposite_direction():
    """Test correlation allows opposite direction trades"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create flags.json with default correlation config
        flags_path = os.path.join(tmpdir, "flags.json")
        with open(flags_path, 'w') as f:
            json.dump({
                "risk_management": {
                    "correlation_check": True,
                    "correlation_pairs": {
                        "EURUSD": ["GBPUSD"],
                        "GBPUSD": ["EURUSD"]
                    }
                }
            }, f)

        # Create an active EURUSD LONG position
        eurusd_trade = os.path.join(tmpdir, ".tv_fast_EURUSD_trade.json")
        with open(eurusd_trade, 'w') as f:
            json.dump({"active": True, "direction": "LONG"}, f)

        original_flags = rm.FLAGS_FILE
        original_home = os.environ.get("HOME")
        rm.FLAGS_FILE = flags_path
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            # Try to open GBPUSD SHORT (opposite direction, should be allowed)
            result = manager.check_correlation("GBPUSD", "SHORT")
            check("correlation: allows opposite direction", result["blocked"] is False)
        finally:
            rm.FLAGS_FILE = original_flags
            if original_home:
                os.environ["HOME"] = original_home


# ─────────────────────────────────────────────────────────────────────────────
# 5) Full risk_check() integration tests
# ─────────────────────────────────────────────────────────────────────────────
def test_risk_check_all_clear():
    """Test risk_check when all conditions are satisfied"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create minimal winning log
        log_path = os.path.join(tmpdir, "signals_log.csv")
        today = dt.datetime.now().strftime("%Y-%m-%d")

        with open(log_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["time", "pips"])
            writer.writeheader()
            writer.writerow({"time": f"{today} 09:00", "pips": "50"})

        original_log = rm.SIGNALS_LOG
        original_home = os.environ.get("HOME")
        rm.SIGNALS_LOG = log_path
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            result = manager.risk_check("XAUUSD", "LONG")
            check("risk_check: all clear allows trade", result["allowed"] is True)
            check("risk_check: no reasons when allowed", len(result["reasons"]) == 0)
        finally:
            rm.SIGNALS_LOG = original_log
            if original_home:
                os.environ["HOME"] = original_home


def test_risk_check_daily_loss_breach():
    """Test risk_check blocks when daily loss limit breached"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a losing day exceeding $500 limit
        log_path = os.path.join(tmpdir, "signals_log.csv")
        today = dt.datetime.now().strftime("%Y-%m-%d")

        # -6000 pips × $0.10 = -$600 (exceeds $500 limit)
        rows = [{"time": f"{today} {i:02d}:00", "pips": "-100"} for i in range(60)]

        with open(log_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["time", "pips"])
            writer.writeheader()
            writer.writerows(rows)

        original_log = rm.SIGNALS_LOG
        original_home = os.environ.get("HOME")
        rm.SIGNALS_LOG = log_path
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            result = manager.risk_check("XAUUSD", "LONG")
            check("risk_check: daily loss blocks trade", result["allowed"] is False)
            check("risk_check: daily loss reason included", any("Daily loss limit" in r for r in result["reasons"]))
        finally:
            rm.SIGNALS_LOG = original_log
            if original_home:
                os.environ["HOME"] = original_home


def test_risk_check_per_instrument_limit():
    """Test risk_check blocks when per-instrument limit reached"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create custom config with limit of 1 per instrument
        flags_path = os.path.join(tmpdir, "flags.json")
        with open(flags_path, 'w') as f:
            json.dump({
                "risk_management": {
                    "max_concurrent_per_instrument": 1,
                    "max_total_open_signals": 10
                }
            }, f)

        # Create 1 active XAUUSD trade (hitting limit of 1)
        with open(os.path.join(tmpdir, ".tv_fast_XAUUSD_trade.json"), 'w') as f:
            json.dump({"active": True, "direction": "LONG"}, f)

        log_path = os.path.join(tmpdir, "signals_log.csv")
        with open(log_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["time", "pips"])
            writer.writeheader()

        original_flags = rm.FLAGS_FILE
        original_log = rm.SIGNALS_LOG
        original_home = os.environ.get("HOME")
        rm.FLAGS_FILE = flags_path
        rm.SIGNALS_LOG = log_path
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            result = manager.risk_check("XAUUSD", "LONG")
            check("risk_check: per-instrument limit blocks", result["allowed"] is False)
            check("risk_check: per-instrument reason included",
                  any("position limit reached" in r for r in result["reasons"]))
        finally:
            rm.FLAGS_FILE = original_flags
            rm.SIGNALS_LOG = original_log
            if original_home:
                os.environ["HOME"] = original_home


def test_risk_check_total_position_limit():
    """Test risk_check blocks when total position limit reached"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create 5 trades across different symbols (hitting default limit of 5)
        symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF"]
        for sym in symbols:
            trade_file = os.path.join(tmpdir, f".tv_fast_{sym}_trade.json")
            with open(trade_file, 'w') as f:
                json.dump({"active": True, "direction": "LONG"}, f)

        log_path = os.path.join(tmpdir, "signals_log.csv")
        with open(log_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["time", "pips"])
            writer.writeheader()

        original_log = rm.SIGNALS_LOG
        original_home = os.environ.get("HOME")
        rm.SIGNALS_LOG = log_path
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            result = manager.risk_check("NZDUSD", "LONG")  # Try to add 6th position
            check("risk_check: total limit blocks trade", result["allowed"] is False)
            check("risk_check: total limit reason included",
                  any("Total position limit" in r for r in result["reasons"]))
        finally:
            rm.SIGNALS_LOG = original_log
            if original_home:
                os.environ["HOME"] = original_home


def test_risk_check_correlation_breach():
    """Test risk_check blocks on correlation conflict"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create flags.json with correlation config
        flags_path = os.path.join(tmpdir, "flags.json")
        with open(flags_path, 'w') as f:
            json.dump({
                "risk_management": {
                    "correlation_check": True,
                    "correlation_pairs": {
                        "EURUSD": ["GBPUSD"],
                        "GBPUSD": ["EURUSD"]
                    }
                }
            }, f)

        # Create active EURUSD LONG
        eurusd_trade = os.path.join(tmpdir, ".tv_fast_EURUSD_trade.json")
        with open(eurusd_trade, 'w') as f:
            json.dump({"active": True, "direction": "LONG"}, f)

        log_path = os.path.join(tmpdir, "signals_log.csv")
        with open(log_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["time", "pips"])
            writer.writeheader()

        original_flags = rm.FLAGS_FILE
        original_log = rm.SIGNALS_LOG
        original_home = os.environ.get("HOME")
        rm.FLAGS_FILE = flags_path
        rm.SIGNALS_LOG = log_path
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            result = manager.risk_check("GBPUSD", "LONG")  # Correlated with EURUSD
            check("risk_check: correlation blocks trade", result["allowed"] is False)
            check("risk_check: correlation reason included",
                  any("Correlated position" in r for r in result["reasons"]))
        finally:
            rm.FLAGS_FILE = original_flags
            rm.SIGNALS_LOG = original_log
            if original_home:
                os.environ["HOME"] = original_home


def test_risk_check_multiple_breaches():
    """Test risk_check reports all breached limits"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create conditions for multiple breaches
        # 1. Excessive daily loss
        log_path = os.path.join(tmpdir, "signals_log.csv")
        today = dt.datetime.now().strftime("%Y-%m-%d")
        rows = [{"time": f"{today} {i:02d}:00", "pips": "-100"} for i in range(60)]

        with open(log_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["time", "pips"])
            writer.writeheader()
            writer.writerows(rows)

        # 2. Max positions reached
        for i, sym in enumerate(["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF"]):
            with open(os.path.join(tmpdir, f".tv_fast_{sym}_trade.json"), 'w') as f:
                json.dump({"active": True, "direction": "LONG"}, f)

        original_log = rm.SIGNALS_LOG
        original_home = os.environ.get("HOME")
        rm.SIGNALS_LOG = log_path
        os.environ["HOME"] = tmpdir

        try:
            manager = rm.RiskManager()
            result = manager.risk_check("NZDUSD", "SHORT")
            check("risk_check: multiple breaches blocks", result["allowed"] is False)
            check("risk_check: multiple reasons reported", len(result["reasons"]) >= 2)
            check("risk_check: daily loss in reasons",
                  any("Daily loss" in r for r in result["reasons"]))
            check("risk_check: total limit in reasons",
                  any("Total position" in r for r in result["reasons"]))
        finally:
            rm.SIGNALS_LOG = original_log
            if original_home:
                os.environ["HOME"] = original_home


# ─────────────────────────────────────────────────────────────────────────────
# Test runner
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("RiskManager Test Suite")
    print("=" * 80)

    # Run all tests
    test_default_config()
    test_config_loading_with_temp_file()
    test_daily_loss_empty_log()
    test_daily_loss_calculation()
    test_daily_loss_with_losses()
    test_open_positions_none()
    test_open_positions_single_instrument()
    test_open_positions_multiple_instruments()
    test_open_positions_inactive_ignored()
    test_correlation_check_disabled()
    test_correlation_no_conflicts()
    test_correlation_blocked_same_direction()
    test_correlation_allowed_opposite_direction()
    test_risk_check_all_clear()
    test_risk_check_daily_loss_breach()
    test_risk_check_per_instrument_limit()
    test_risk_check_total_position_limit()
    test_risk_check_correlation_breach()
    test_risk_check_multiple_breaches()

    # Report results
    print("\nTest Results:")
    print("-" * 80)

    passed = sum(1 for _, result in _results if result)
    failed = sum(1 for _, result in _results if not result)

    for name, result in _results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print("=" * 80)
    print(f"\nTotal: {len(_results)} tests | Passed: {passed} | Failed: {failed}")

    if failed > 0:
        print(f"\n✗ TEST SUITE FAILED: {failed} test(s) failed")
        sys.exit(1)
    else:
        print("\n✓ TEST SUITE PASSED: All tests passed successfully!")
        sys.exit(0)
