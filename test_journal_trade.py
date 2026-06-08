#!/usr/bin/env python3
"""Regression tests for journal_trade.py cleanup."""
import os
import tempfile

import journal_trade as J


def test_shots_restores_timeframe_on_failure():
    calls = []
    real_tv = J.tv
    try:
        def spy(*args):
            calls.append(args)
            if args[:1] == ("screenshot",):
                raise RuntimeError("boom")
            if args[:1] == ("state",):
                return {"resolution": "5"}
            return {}

        J.tv = spy
        folder = tempfile.mkdtemp()
        try:
            J.shots(folder, ["4h"], "entry")
        except RuntimeError:
            pass
        assert ("timeframe", "5") in calls, "shots must restore the original timeframe in finally"
        print("✓ shots restores original timeframe on failure")
    finally:
        J.tv = real_tv


if __name__ == "__main__":
    test_shots_restores_timeframe_on_failure()
    print("\n✓ ALL journal_trade tests passed")
