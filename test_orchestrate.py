#!/usr/bin/env python3
"""Regression tests for orchestrate.py review handling."""
import orchestrate as O


def test_review_fails_on_subprocess_error_even_if_pending_exists():
    class Result:
        returncode = 1

    real_run = O.subprocess.run
    real_exists = O.os.path.exists
    try:
        O.subprocess.run = lambda *a, **k: Result()
        O.os.path.exists = lambda path: path.endswith(".json")
        assert O.review("XAUUSD") is False, "failed review subprocess must not be treated as held"
        print("✓ review fails on subprocess error even if pending exists")
    finally:
        O.subprocess.run = real_run
        O.os.path.exists = real_exists


def test_review_succeeds_only_when_pending_created():
    class Result:
        returncode = 0

    real_run = O.subprocess.run
    real_exists = O.os.path.exists
    try:
        O.subprocess.run = lambda *a, **k: Result()
        O.os.path.exists = lambda path: True
        assert O.review("XAUUSD") is True, "successful review with pending file should be held"
        print("✓ review succeeds when subprocess returns 0 and pending exists")
    finally:
        O.subprocess.run = real_run
        O.os.path.exists = real_exists


if __name__ == "__main__":
    test_review_fails_on_subprocess_error_even_if_pending_exists()
    test_review_succeeds_only_when_pending_created()
    print("\n✓ ALL orchestrate tests passed")
