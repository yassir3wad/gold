#!/usr/bin/env python3
"""Regression tests for counterfactual.py timestamp parsing."""
import datetime as dt

import counterfactual as C


def test_unix_parses_naive_time_as_utc():
    ts = C._unix("2026-06-04 12:30")
    expected = dt.datetime(2026, 6, 4, 12, 30, tzinfo=dt.timezone.utc).timestamp()
    assert ts == expected, "naive log timestamps must be interpreted as UTC"
    print("✓ naive timestamps parsed as UTC")


if __name__ == "__main__":
    test_unix_parses_naive_time_as_utc()
    print("\n✓ ALL counterfactual tests passed")
