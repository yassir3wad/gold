#!/usr/bin/env python3
"""Regression tests for the zone-scheduler config fixes:
  - the `notifications` object is actually honored (was dead config)
  - the `enabled` master switch is surfaced
Chart-safe (pure config parsing, no TradingView/network)."""
import json, os, tempfile
import zone_scheduler as z

def _load(cfg):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(cfg, f); f.close()
    z.CONFIG_FILE = f.name
    try: return z.load_config()
    finally: os.unlink(f.name)

def test_notifications_object_honored():
    c = _load({"notifications": {"send_on_refresh": False, "send_on_stale_warning": True}})
    assert c["notifications_enabled"] is False, "send_on_refresh:false must disable refresh notifications"
    assert c["stale_notifications_enabled"] is True, "send_on_stale_warning:true must keep stale alerts on"
    print("✓ notifications object honored (refresh off, stale on)")

def test_stale_toggle_independent():
    c = _load({"notifications": {"send_on_refresh": True, "send_on_stale_warning": False}})
    assert c["notifications_enabled"] is True and c["stale_notifications_enabled"] is False
    print("✓ stale toggle is independent of refresh toggle")

def test_enabled_switch_present():
    assert _load({"enabled": False})["enabled"] is False
    assert _load({"enabled": True})["enabled"] is True
    print("✓ enabled master switch is surfaced in config")

def test_session_refresh_toggle_blocks_jobs():
    class FakeScheduler:
        def __init__(self):
            self.jobs = []
        def add_job(self, *args, **kwargs):
            self.jobs.append((args, kwargs))

    real_file, real_scheduler = z.CONFIG_FILE, getattr(z, "BackgroundScheduler", None)
    try:
        cfg = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump({
            "enabled": True,
            "session_refresh_enabled": False,
            "refresh_on_session_open": ["london", "ny"],
            "session_times": {"london": "08:00", "ny": "13:00"},
        }, cfg)
        cfg.close()
        z.CONFIG_FILE = cfg.name
        z.BackgroundScheduler = FakeScheduler
        sched = z.ZoneScheduler(interval_hours=1, run_once=False)
        sched.add_session_jobs()
        assert sched.scheduler.jobs == [], "disabled session refresh must not schedule Cron jobs"
        print("✓ session refresh toggle blocks session jobs")
    finally:
        z.CONFIG_FILE = real_file
        if real_scheduler is not None:
            z.BackgroundScheduler = real_scheduler
        os.unlink(cfg.name)

def test_defaults_when_no_notifications():
    c = _load({})   # no notifications object -> default on
    assert c["notifications_enabled"] is True and c["stale_notifications_enabled"] is True
    print("✓ defaults to notifications-on when object absent")

def test_refresh_job_surfaces_symbol_failure():
    class Result:
        def __init__(self, returncode, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    real_load_config = z.load_config
    real_run = z.subprocess.run
    try:
        z.load_config = lambda: {"enabled_instruments": ["XAUUSD"], "notifications_enabled": False}

        def fake_run(*args, **kwargs):
            return Result(1, stdout="", stderr="boom")

        z.subprocess.run = fake_run
        ok = z.refresh_zones_job()
        assert ok is False, "refresh_zones_job must return False when a symbol refresh fails"
        print("✓ refresh job surfaces symbol failure")
    finally:
        z.load_config = real_load_config
        z.subprocess.run = real_run

def test_health_check_surfaces_parse_errors():
    tmp = tempfile.TemporaryDirectory()
    real_expanduser = z.os.path.expanduser
    real_load_config = z.load_config
    try:
        z.os.path.expanduser = lambda path: tmp.name if path == "~/tradingview-mcp" else real_expanduser(path)
        z.load_config = lambda: {"enabled_instruments": ["XAUUSD"], "stale_threshold_hours": 6, "stale_notifications_enabled": False}
        with open(os.path.join(tmp.name, "zones_xauusd.json"), "w") as f:
            f.write("{bad json")
        out = z.check_zone_health(send_alert=False)
        assert out["error_count"] == 1 and out["stale_count"] == 0 and out["missing_count"] == 0
        print("✓ health check surfaces malformed zone files")
    finally:
        z.os.path.expanduser = real_expanduser
        z.load_config = real_load_config
        tmp.cleanup()

if __name__ == "__main__":
    for fn in (test_notifications_object_honored, test_stale_toggle_independent,
               test_enabled_switch_present, test_session_refresh_toggle_blocks_jobs,
               test_defaults_when_no_notifications, test_refresh_job_surfaces_symbol_failure,
               test_health_check_surfaces_parse_errors):
        fn()
    print("\n✓ ALL config-fix tests passed")
