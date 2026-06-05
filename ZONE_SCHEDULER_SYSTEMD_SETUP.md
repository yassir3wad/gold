# Zone Scheduler Systemd Service Setup

This guide covers installation and management of the zone_scheduler systemd service for automated HTF zone refresh.

## Prerequisites

1. Python 3 with APScheduler installed: `pip3 install apscheduler`
2. zone_scheduler.py and dependencies in ~/tradingview-mcp
3. zone_scheduler_config.json configured
4. telegram_config.json configured (if notifications enabled)

## Installation

### 1. Configure the service file

Edit `zone_scheduler.service` and replace placeholders:

```bash
# Replace YOUR_USERNAME with your actual username
sed -i "s/YOUR_USERNAME/$(whoami)/g" zone_scheduler.service

# If using a non-standard installation path, update WorkingDirectory
# Default: /home/YOUR_USERNAME/tradingview-mcp
```

### 2. Install the service

```bash
# Copy service file to systemd directory
sudo cp zone_scheduler.service /etc/systemd/system/

# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable zone_scheduler

# Start the service
sudo systemctl start zone_scheduler
```

### 3. Verify installation

```bash
# Check service status
sudo systemctl status zone_scheduler

# View logs
sudo journalctl -u zone_scheduler -f

# Or check application log file
tail -f ~/tradingview-mcp/logs/zone_scheduler.log
```

## Service Management

### Start/Stop/Restart

```bash
# Start
sudo systemctl start zone_scheduler

# Stop
sudo systemctl stop zone_scheduler

# Restart
sudo systemctl restart zone_scheduler

# Reload configuration (after editing zone_scheduler_config.json)
sudo systemctl reload-or-restart zone_scheduler
```

### Check Status

```bash
# Service status
sudo systemctl status zone_scheduler

# Is service running?
sudo systemctl is-active zone_scheduler

# Is service enabled on boot?
sudo systemctl is-enabled zone_scheduler
```

### View Logs

```bash
# Tail logs (live)
sudo journalctl -u zone_scheduler -f

# View last 100 lines
sudo journalctl -u zone_scheduler -n 100

# View logs since boot
sudo journalctl -u zone_scheduler -b

# View logs with timestamps
sudo journalctl -u zone_scheduler -o short-iso

# Application log file
tail -f ~/tradingview-mcp/logs/zone_scheduler.log
```

### Disable Service

```bash
# Stop and disable
sudo systemctl stop zone_scheduler
sudo systemctl disable zone_scheduler

# Remove service file (optional)
sudo rm /etc/systemd/system/zone_scheduler.service
sudo systemctl daemon-reload
```

## Configuration

### zone_scheduler_config.json

Located in `~/tradingview-mcp/zone_scheduler_config.json`:

```json
{
  "refresh_interval_hours": 4,
  "session_refresh_enabled": true,
  "session_offset_minutes": 5,
  "enabled_instruments": ["XAUUSD", "GBPUSD", "EURUSD"],
  "stale_threshold_hours": 6,
  "notifications_enabled": true,
  "refresh_on_session_open": ["london", "ny"],
  "session_times": {
    "london": "07:00",
    "ny": "13:00",
    "asia": "00:00"
  }
}
```

After modifying configuration:

```bash
sudo systemctl restart zone_scheduler
```

## Troubleshooting

### Service won't start

```bash
# Check for errors
sudo systemctl status zone_scheduler -l

# Check journal for details
sudo journalctl -u zone_scheduler -n 50

# Test manually
cd ~/tradingview-mcp
python3 zone_scheduler.py --verbose --once
```

### Permission errors

```bash
# Ensure user owns working directory
sudo chown -R $(whoami):$(whoami) ~/tradingview-mcp

# Check log directory exists and is writable
mkdir -p ~/tradingview-mcp/logs
chmod 755 ~/tradingview-mcp/logs
```

### Missing dependencies

```bash
# Install required packages
pip3 install apscheduler

# Verify imports
python3 -c "import apscheduler; print('OK')"
```

### Service crashes on startup

```bash
# Run health check
python3 zone_scheduler.py --check-health

# Test configuration loading
python3 -c "import zone_scheduler; zone_scheduler.load_config(); print('OK')"

# Check for missing zone files
ls ~/tradingview-mcp/zones_*.json
```

### Zone files not updating

```bash
# Check scheduler is running
sudo systemctl status zone_scheduler

# Check logs for refresh cycles
tail -f ~/tradingview-mcp/logs/zone_scheduler.log | grep "refresh"

# Manually trigger refresh
cd ~/tradingview-mcp
bash refresh_zones_now.sh --notify
```

### Stale zone warnings

```bash
# Check zone health
python3 check_zone_health.py

# Force immediate refresh
python3 zone_scheduler.py --once

# Or use wrapper script
bash refresh_zones_now.sh
```

## Security Notes

The service file includes security hardening:

- **NoNewPrivileges**: Prevents privilege escalation
- **PrivateTmp**: Isolated /tmp directory
- **ProtectSystem**: Read-only system directories
- **ProtectHome**: Read-only home directories (except WorkingDirectory)
- **ReadWritePaths**: Explicit write access to logs and zone files
- **MemoryLimit**: 512M memory cap
- **CPUQuota**: 50% CPU limit

If you experience permission issues, check:

1. User has read/write access to ~/tradingview-mcp/logs
2. User has read/write access to ~/tradingview-mcp/zones_*.json
3. ReadWritePaths in service file match actual paths

## Monitoring

### Automated monitoring with systemd

```bash
# Enable email alerts on service failure (requires mail setup)
sudo systemctl edit zone_scheduler

# Add:
[Service]
OnFailure=status-email@%n.service
```

### Health check integration

The scheduler runs health checks:

- **Startup**: Checks zone freshness on daemon start
- **Hourly**: Periodic health checks while running
- **Alerts**: Telegram notifications if stale zones detected (>6 hours old)

Manual health check:

```bash
python3 zone_scheduler.py --check-health
# Exit code 0: all healthy
# Exit code 1: stale or missing zones
```

### Resource usage monitoring

```bash
# CPU/memory usage
systemctl status zone_scheduler

# Detailed resource stats
systemd-cgtop -1 | grep zone_scheduler
```

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop zone_scheduler
sudo systemctl disable zone_scheduler

# Remove service file
sudo rm /etc/systemd/system/zone_scheduler.service

# Reload systemd
sudo systemctl daemon-reload

# Remove application files (optional)
rm -rf ~/tradingview-mcp/zone_scheduler.py
rm -rf ~/tradingview-mcp/logs/zone_scheduler.log*
```

## Additional Notes

- The service runs with `Restart=always`, so it will automatically recover from crashes
- Logs rotate at 10MB with 5 backups (configured in zone_scheduler.py)
- Both systemd journal and application logs are available
- The service waits for network connectivity before starting (`After=network-online.target`)
- Graceful shutdown with 30-second timeout for cleanup

## See Also

- `zone_scheduler.py --help` - CLI options
- `OPERATIONS.md` - Operations guide
- `zone_scheduler_config.json` - Configuration reference
