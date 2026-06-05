# Scanner State Schema Documentation

## Overview

The TradingView scanner uses a consolidated, schema-validated JSON state file to persist critical data across restarts. This ensures trade management continuity, duplicate alert suppression, and cooldown enforcement survive scanner crashes, manual stops, or system reboots.

**State File Location:** `~/.tv_scanner_state.json`

**Schema Version:** `1.0`

## State File Structure

The state file is a human-readable JSON document with the following top-level structure:

```json
{
  "version": "1.0",
  "active_trades": {},
  "cooldowns": {},
  "watch_state": {},
  "scan_timestamps": {}
}
```

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Schema version identifier (currently "1.0") |
| `active_trades` | object | Maps trading symbols to their active trade state |
| `cooldowns` | object | Maps trading symbols to cooldown expiration timestamps |
| `watch_state` | object | Maps trading symbols to watch/monitoring state |
| `scan_timestamps` | object | Maps trading symbols to last successful scan timestamp |

## Field Definitions

### Active Trades (`active_trades`)

Maps trading symbols (e.g., "XAUUSD", "GBPUSD") to active trade state objects.

**Structure:**
```json
{
  "active_trades": {
    "XAUUSD": {
      "active": true,
      "id": 1717524800,
      "side": "LONG",
      "entry": 2450.0,
      "sl": 2420.0,
      "tp1": 2500.0,
      "tp2": 2550.0,
      "tp1_hit": false,
      "be_trig": 35,
      "t0": 1717524800.123,
      "mfe": 0.0,
      "be_moved": false
    }
  }
}
```

**Trade State Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `active` | boolean | Yes | Whether trade is currently active |
| `id` | integer | Yes | Unique signal ID (timestamp-based) for duplicate detection |
| `side` | string | Yes | Trade direction: "LONG" or "SHORT" |
| `entry` | float | Yes | Entry price level |
| `sl` | float | Yes | Stop loss price level |
| `tp1` | float | Yes | First take profit target price |
| `tp2` | float | Yes | Second take profit target price |
| `tp1_hit` | boolean | Yes | Flag indicating if first TP has been hit (prevents duplicate TP1 alerts) |
| `be_trig` | float/null | No | Breakeven trigger distance in pips (null if not set) |
| `t0` | float | Yes | Trade initiation timestamp (Unix time) |
| `mfe` | float | No | Maximum favorable excursion (tracking for analytics) |
| `be_moved` | boolean | No | Flag indicating if stop loss was moved to breakeven |

**Purpose:**
- Enables TP/SL management to continue after scanner restart
- Prevents duplicate trade entry alerts via signal ID tracking
- Tracks TP1/TP2 hit flags to prevent duplicate Telegram alerts for the same target

### Cooldowns (`cooldowns`)

Maps trading symbols to cooldown expiration timestamps. Cooldowns prevent duplicate signals within a configurable time window (typically 5 minutes).

**Structure:**
```json
{
  "cooldowns": {
    "XAUUSD": 1717524800.456,
    "GBPUSD": 1717524500.123
  }
}
```

**Value:** Unix timestamp (float) representing when the cooldown was initiated

**Purpose:**
- Prevents duplicate trade signals for the same symbol within cooldown window
- Persists across restarts to avoid duplicate Telegram alerts after scanner recovery
- Default cooldown duration: 5 minutes (configurable)

**Usage:**
- Cooldown is set when a signal fires
- Scanner checks cooldown before generating new signals
- If `current_time - cooldown_timestamp < cooldown_seconds`, signal is suppressed

### Watch State (`watch_state`)

Maps trading symbols to watch/monitoring state. Used by the scanner to track signal deduplication keys and monitoring context.

**Structure:**
```json
{
  "watch_state": {
    "XAUUSD": {
      "t": 1717524800.789,
      "price": 2450.25,
      "label": "watch_long_setup",
      "key": "xauusd_1717524800_long_2450"
    }
  }
}
```

**Watch State Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `t` | float | Timestamp when watch state was set |
| `price` | float | Price level being watched (optional) |
| `label` | string | Human-readable label for watch context (optional) |
| `key` | string | Deduplication key for signal tracking (optional) |

**Purpose:**
- Deduplicates signals across scanner restarts (via `key` field)
- Tracks pending setup monitoring state
- Preserves watch context for debugging and analytics

### Scan Timestamps (`scan_timestamps`)

Maps trading symbols to their last successful scan timestamp. Enables orchestrator health monitoring and debugging.

**Structure:**
```json
{
  "scan_timestamps": {
    "XAUUSD": 1717524860.123,
    "GBPUSD": 1717524920.456,
    "NAS100": 1717524980.789
  }
}
```

**Value:** Unix timestamp (float) of last successful scan completion

**Purpose:**
- Orchestrator uses this to display "last scan: Xm ago" for each instrument
- Enables identification of stale/failing scanners (no recent scan timestamp)
- Helps debug coverage gaps in multi-instrument scanning
- Timestamp is updated on every scan completion, regardless of signal outcome

## Example Complete State File

```json
{
  "version": "1.0",
  "active_trades": {
    "XAUUSD": {
      "active": true,
      "id": 1717524800,
      "side": "LONG",
      "entry": 2450.0,
      "sl": 2420.0,
      "tp1": 2500.0,
      "tp2": 2550.0,
      "tp1_hit": false,
      "be_trig": 35,
      "t0": 1717524800.123,
      "mfe": 15.5,
      "be_moved": false
    },
    "GBPUSD": {
      "active": true,
      "id": 1717524500,
      "side": "SHORT",
      "entry": 1.2650,
      "sl": 1.2680,
      "tp1": 1.2600,
      "tp2": 1.2550,
      "tp1_hit": true,
      "be_trig": null,
      "t0": 1717524500.456,
      "mfe": 35.2,
      "be_moved": true
    }
  },
  "cooldowns": {
    "XAUUSD": 1717524800.456,
    "GBPUSD": 1717524500.123,
    "NAS100": 1717524650.789
  },
  "watch_state": {
    "XAUUSD": {
      "t": 1717524800.789,
      "price": 2450.25,
      "label": "watch_long_setup",
      "key": "xauusd_1717524800_long_2450"
    }
  },
  "scan_timestamps": {
    "XAUUSD": 1717524860.123,
    "GBPUSD": 1717524920.456,
    "NAS100": 1717524980.789,
    "US30": 1717525040.012,
    "EURUSD": 1717525100.345,
    "USDJPY": 1717525160.678,
    "AUDUSD": 1717525220.901
  }
}
```

## Schema Validation

The StateManager performs automatic schema validation on startup:

1. **Required Keys Check:** Ensures all top-level keys exist (`version`, `active_trades`, `cooldowns`, `watch_state`, `scan_timestamps`)
2. **Type Validation:** Verifies each top-level field is a dictionary (except `version` which is a string)
3. **Graceful Degradation:** On validation failure, logs a warning and initializes fresh default state

**Validation Error Examples:**
- Missing required keys: `StateManager` logs warning, returns default state
- Invalid JSON syntax: JSON decode error logged, returns default state
- Wrong field types: Type validation fails, returns default state

## Corruption Handling

The scanner is designed to recover gracefully from corrupted state files:

### Detection

Corruption is detected in three ways:
1. **JSON Parse Errors:** Invalid JSON syntax (malformed brackets, quotes, etc.)
2. **Schema Validation Failures:** Missing required keys
3. **Type Mismatches:** Fields have wrong types (e.g., `active_trades` is a string instead of object)

### Recovery

When corruption is detected:
1. Warning is logged: `"State file corrupted (invalid JSON): <error>. Starting with fresh state."`
2. Default empty state is initialized:
   ```json
   {
     "version": "1.0",
     "active_trades": {},
     "cooldowns": {},
     "watch_state": {},
     "scan_timestamps": {}
   }
   ```
3. Scanner continues operation normally with fresh state
4. No exceptions bubble up - scanner never crashes due to state corruption

### Prevention

To minimize corruption risk, the StateManager uses **atomic writes**:
1. State is written to temporary file: `~/.tv_scanner_state.json.tmp`
2. Temporary file is atomically renamed to: `~/.tv_scanner_state.json`
3. This ensures the state file is never left in a partially-written state

## State Lifecycle

### Initialization

1. StateManager checks if state file exists at `~/.tv_scanner_state.json`
2. If not found: Creates default empty state
3. If found: Loads and validates JSON
4. If validation fails: Falls back to default empty state

### Updates

State is updated via StateManager methods:
- `set_active_trade()`: Creates/updates active trade
- `save_cooldown()`: Sets cooldown timestamp
- `save_watch_state()`: Saves watch/monitoring state
- `save_scan_timestamp()`: Records scan completion time

Each update triggers an atomic write to disk.

### Persistence Frequency

- **Active Trades:** Updated when signal fires, TP/SL hit, or trade closed
- **Cooldowns:** Updated when signal fires
- **Watch State:** Updated when monitoring state changes
- **Scan Timestamps:** Updated at end of every scan cycle (~60 seconds)

### Cleanup

- **Active Trades:** Cleared when trade is closed (SL/TP2 hit)
- **Cooldowns:** Automatically expire after cooldown duration (no manual cleanup)
- **Watch State:** Cleared when watch condition expires or trade fires
- **Scan Timestamps:** Never cleaned up (historical record)

## Migration from Legacy State Files

Prior to StateManager, the scanner used fragmented per-file state storage:
- `~/.tv_fast_trade_<symbol>.json` - Trade state
- `~/.tv_fast_cd_<symbol>.json` - Cooldown state
- `~/.tv_fast_watch_cd_<symbol>.json` - Watch state

### Migration Path

StateManager provides `import_legacy_state()` method to migrate old files:

```python
from src.state_manager import StateManager

state_manager = StateManager('scanner')

# Migrate trade state
state_manager.import_legacy_state('XAUUSD', '~/.tv_fast_trade_xauusd.json', 'trade')

# Migrate cooldown
state_manager.import_legacy_state('XAUUSD', '~/.tv_fast_cd_xauusd.json', 'cd')

# Migrate watch state
state_manager.import_legacy_state('XAUUSD', '~/.tv_fast_watch_cd_xauusd.json', 'watch')
```

**Automated Migration Script:** `scripts/migrate_state.py` (see migration script documentation)

### Migration Notes

1. **Backward Compatibility:** StateManager does not read or write legacy files - migration is one-way
2. **Data Preservation:** All trade context, cooldowns, and watch state are preserved during migration
3. **Idempotent:** Migration can be run multiple times safely (existing state not overwritten)
4. **Validation:** Migrated state undergoes same schema validation as normal state loads

## StateManager API Reference

### Initialization

```python
from src.state_manager import StateManager

# Default state file: ~/.tv_scanner_state.json
state_manager = StateManager(namespace='scanner')

# Custom state file (for testing)
state_manager = StateManager(namespace='test', state_file='/tmp/test_state.json')
```

### Trade State Methods

```python
# Set active trade
state_manager.set_active_trade(
    symbol='XAUUSD',
    side='LONG',
    entry=2450.0,
    sl=2420.0,
    tp1=2500.0,
    tp2=2550.0,
    signal_id=1717524800,
    be_trig=35  # Optional
)

# Get active trade
trade = state_manager.get_active_trade('XAUUSD')
# Returns: {'active': True, 'id': 1717524800, 'side': 'LONG', ...} or None

# Update trade fields
state_manager.update_trade_state('XAUUSD', {'tp1_hit': True, 'mfe': 15.5})

# Clear trade
state_manager.clear_active_trade('XAUUSD')

# Get all active trades
all_trades = state_manager.get_all_active_trades()
# Returns: {'XAUUSD': {...}, 'GBPUSD': {...}}
```

### Cooldown Methods

```python
# Set cooldown
state_manager.set_cooldown('XAUUSD', cooldown_minutes=5)

# Check if in cooldown
if state_manager.in_cooldown('XAUUSD', cooldown_minutes=5):
    print("Symbol in cooldown, skip signal")

# Get remaining cooldown time
remaining = state_manager.get_cooldown_remaining('XAUUSD', cooldown_minutes=5)
print(f"Cooldown expires in {remaining:.0f} seconds")
```

### Watch State Methods

```python
# Save watch state
state_manager.save_watch_state('XAUUSD', {
    't': time.time(),
    'price': 2450.25,
    'label': 'watch_long_setup',
    'key': 'xauusd_1717524800_long_2450'
})

# Get watch state
watch = state_manager.get_watch_state('XAUUSD')
# Returns: {'t': 1717524800.789, 'price': 2450.25, ...} or None
```

### Scan Timestamp Methods

```python
# Save scan timestamp
state_manager.save_scan_timestamp('XAUUSD')  # Uses current time
state_manager.save_scan_timestamp('XAUUSD', timestamp=1717524800.123)

# Get scan timestamp
last_scan = state_manager.get_scan_timestamp('XAUUSD')
# Returns: 1717524860.123 or None
```

## Testing & Validation

### Test Files

Comprehensive integration tests validate state persistence:

1. **`test_fresh_start_local.py`** - Fresh start with no existing state
2. **`test_restart_persistence.py`** - State persistence across scanner restart
3. **`test_corrupted_state.py`** - Graceful degradation on corruption
4. **`test_cooldown_persistence.py`** - Cooldown persistence across restart
5. **`test_orchestrator_state.py`** - Multi-instrument state tracking

### Running Tests

```bash
# Run all state tests
python3 test_fresh_start_local.py
python3 test_restart_persistence.py
python3 test_corrupted_state.py
python3 test_cooldown_persistence.py
python3 test_orchestrator_state.py
```

### Manual Verification

To manually verify state persistence:

1. **Start Scanner:**
   ```bash
   python3 scalp_fast.py --symbol XAUUSD
   ```

2. **Verify State File Created:**
   ```bash
   cat ~/.tv_scanner_state.json | python3 -m json.tool
   ```

3. **Simulate Crash:**
   - Wait for signal to fire (or manually trigger via test)
   - Kill scanner with Ctrl+C

4. **Verify State Persisted:**
   ```bash
   # Check active trade saved
   python3 -c "from src.state_manager import StateManager; sm = StateManager('scanner'); print(sm.get_active_trade('XAUUSD'))"
   ```

5. **Restart Scanner:**
   ```bash
   python3 scalp_fast.py --symbol XAUUSD
   ```

6. **Verify Trade Management Continues:**
   - Check logs for "Restored active trade" message
   - Verify TP/SL management updates appear
   - Verify no duplicate Telegram alerts sent

## Troubleshooting

### State File Not Found

**Symptom:** Scanner logs "State file not found at ~/.tv_scanner_state.json. Starting with fresh state."

**Cause:** First run or state file was deleted

**Resolution:** Normal behavior - state file will be created on first state update

### Corrupted State File

**Symptom:** Scanner logs "State file corrupted (invalid JSON): ... Starting with fresh state."

**Cause:** Partial write, manual edit, or disk corruption

**Resolution:** 
1. Automatic - Scanner recovers with fresh state
2. Manual - Restore from backup if available:
   ```bash
   cp ~/.tv_scanner_state.json.backup ~/.tv_scanner_state.json
   ```

### Duplicate Alerts After Restart

**Symptom:** Same Telegram alert sent again after scanner restart

**Cause:** State not persisted or cooldown not loaded

**Resolution:**
1. Verify state file exists and is valid JSON
2. Check logs for "Restored active trade" message
3. Verify cooldown persistence:
   ```bash
   python3 -c "from src.state_manager import StateManager; sm = StateManager('scanner'); print(sm._state['cooldowns'])"
   ```

### Active Trade Not Restored

**Symptom:** TP/SL management doesn't continue after restart

**Cause:** Trade state not marked as `active: true` or trade was cleared before restart

**Resolution:**
1. Check state file for active trade entry:
   ```bash
   python3 -c "from src.state_manager import StateManager; sm = StateManager('scanner'); print(sm.get_active_trade('XAUUSD'))"
   ```
2. Verify `active: true` flag in state file
3. Check scanner logs for trade clear events before restart

## Security & Best Practices

### File Permissions

State file should be readable/writable only by scanner user:

```bash
chmod 600 ~/.tv_scanner_state.json
```

### Backup

Recommended backup strategy:

```bash
# Cron job to backup state every hour
0 * * * * cp ~/.tv_scanner_state.json ~/.tv_scanner_state.json.backup
```

### Monitoring

Monitor state file health:

```bash
# Check state file size (should be < 100KB for normal operation)
ls -lh ~/.tv_scanner_state.json

# Validate JSON syntax
python3 -m json.tool ~/.tv_scanner_state.json > /dev/null && echo "Valid" || echo "Corrupted"

# Check last modified time (should update every ~60 seconds when scanner running)
stat ~/.tv_scanner_state.json
```

### Performance

- State file I/O is minimal (~1-2 writes per minute per instrument)
- Atomic writes prevent corruption but add negligible overhead (<1ms)
- State file grows linearly with number of active instruments (typical size: 5-50KB)

## Version History

### Version 1.0 (Current)

- Initial consolidated state schema
- Support for active trades, cooldowns, watch state, and scan timestamps
- Atomic writes with graceful degradation
- Schema validation on load
- Migration support from legacy per-file state
