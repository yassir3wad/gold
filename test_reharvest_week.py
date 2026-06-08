#!/usr/bin/env python3
"""Regression tests for reharvest_week.py replay cleanup."""
import sys

import reharvest_week as R


def test_replay_stops_on_fetch_failure():
    calls = []

    real_fetch = R.tpo.fetch_va
    real_tv = R.tpo._default_tv
    real_get = R.vs.get
    real_put = R.vs.put
    real_argv = sys.argv
    try:
        R.tpo.fetch_va = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        R.tpo._default_tv = lambda *a, **k: calls.append(a)
        R.vs.get = lambda *a, **k: {}
        R.vs.put = lambda *a, **k: None
        sys.argv = ["reharvest_week.py", "2026-06-01", "2026-06-01"]
        R.main()
        assert any(call[1:3] == ("replay", "stop") for call in calls), "replay must be stopped in finally"
        print("✓ replay stopped on fetch failure")
    finally:
        R.tpo.fetch_va = real_fetch
        R.tpo._default_tv = real_tv
        R.vs.get = real_get
        R.vs.put = real_put
        sys.argv = real_argv


if __name__ == "__main__":
    test_replay_stops_on_fetch_failure()
    print("\n✓ ALL reharvest_week tests passed")
