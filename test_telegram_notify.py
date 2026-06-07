#!/usr/bin/env python3
"""Regression tests for Telegram notifier API-response handling."""
import json
import os
import tempfile

import telegram_notify as T


def _temp_config():
    cfg = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump({"bot_token": "token", "chat_id": "123"}, cfg)
    cfg.close()
    return cfg.name


def test_send_message_rejects_api_error_payload():
    real_cfg = T.CONFIG_FILE
    real_run = T.subprocess.run
    cfg = _temp_config()
    try:
        T.CONFIG_FILE = cfg
        T.subprocess.run = lambda *a, **k: type("R", (), {"returncode": 0, "stdout": '{"ok":false,"description":"bad"}'})()
        assert T.send_message("hello") is False, "Telegram API error payload must not count as sent"
        print("✓ send_message rejects API error payload")
    finally:
        T.CONFIG_FILE = real_cfg
        T.subprocess.run = real_run
        os.unlink(cfg)


def test_send_alert_rejects_non_json_payload():
    real_cfg = T.CONFIG_FILE
    real_run = T.subprocess.run
    cfg = _temp_config()
    try:
        T.CONFIG_FILE = cfg
        T.subprocess.run = lambda *a, **k: type("R", (), {"returncode": 0, "stdout": "not json"})()
        assert T.send_alert("title", "body") is False, "non-JSON Telegram response must fail"
        print("✓ send_alert rejects non-JSON payload")
    finally:
        T.CONFIG_FILE = real_cfg
        T.subprocess.run = real_run
        os.unlink(cfg)


if __name__ == "__main__":
    test_send_message_rejects_api_error_payload()
    test_send_alert_rejects_non_json_payload()
    print("\n✓ ALL telegram notifier tests passed")
