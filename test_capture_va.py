#!/usr/bin/env python3
"""Regression tests for capture_va.py cleanup."""
import sys

import capture_va as C


def test_replay_stops_on_failure():
    calls = []
    real_tv = C.tv
    real_argv = sys.argv
    try:
        def spy(*args, chart=None):
            calls.append((args, chart))
            if args[:2] == ("chart", "--from"):
                raise RuntimeError("boom")
            if args == ("tab", "list"):
                return {"tabs": [{"index": 1, "chart_id": "CH1"}]}
            if args == ("state",):
                return {"studies": []}
            return {}

        C.tv = spy
        sys.argv = ["capture_va.py", "--chart", "CH1", "--symbol", "XAUUSD", "--week-end", "2026-06-01"]
        try:
            C.main()
        except RuntimeError:
            pass
        assert any(call[0] == ("replay", "stop") and call[1] == "CH1" for call in calls), \
            "replay must be stopped in finally"
        print("✓ replay stopped on capture failure")
    finally:
        C.tv = real_tv
        sys.argv = real_argv


if __name__ == "__main__":
    test_replay_stops_on_failure()
    print("\n✓ ALL capture_va tests passed")
