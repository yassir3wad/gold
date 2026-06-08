#!/usr/bin/env python3
"""Regression tests for replay cleanup in draw_review.py and collect_bars.py."""
import sys

import collect_bars as C
import draw_review as D


def test_collect_bars_stops_replay_on_failure():
    calls = []
    real_tv = C.tv
    real_argv = sys.argv
    try:
        def spy(chart, *a):
            calls.append((chart, a))
            if a[:2] == ("ohlcv", "-n"):
                raise RuntimeError("boom")
            return {"bars": [], "tabs": []}

        C.tv = spy
        sys.argv = ["collect_bars.py", "--date", "2026-06-01", "--chart", "CH1"]
        try:
            C.main()
        except RuntimeError:
            pass
        assert any(a == ("replay", "stop") for _, a in calls), "collect_bars must stop replay in finally"
        print("✓ collect_bars stops replay on failure")
    finally:
        C.tv = real_tv
        sys.argv = real_argv


def test_draw_review_stops_replay_on_failure():
    calls = []
    real_tv = D.tv
    real_argv = sys.argv
    try:
        def spy(chart, *a):
            calls.append((chart, a))
            if a[:2] == ("draw", "clear"):
                raise RuntimeError("boom")
            if a[:1] == ("state",):
                return {"studies": []}
            if a[:1] == ("ohlcv",):
                return {"bars": [{"time": 1, "close": 1.0}, {"time": 2, "close": 1.0}]}
            return {}

        D.tv = spy
        sys.argv = ["draw_review.py", "--date", "2026-06-01", "--chart", "CH1"]
        try:
            D.main()
        except RuntimeError:
            pass
        assert any(a == ("replay", "stop") for _, a in calls), "draw_review must stop replay in finally"
        print("✓ draw_review stops replay on failure")
    finally:
        D.tv = real_tv
        sys.argv = real_argv


if __name__ == "__main__":
    test_collect_bars_stops_replay_on_failure()
    test_draw_review_stops_replay_on_failure()
    print("\n✓ ALL replay cleanup tests passed")
