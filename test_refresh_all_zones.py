#!/usr/bin/env python3
"""Regression tests for refresh_all_zones.py comparison logic.

These pin the zone-diff behavior that the scheduler relies on:
  - missing old file should count the new zones as additions
  - missing new file should count the old zones as removals
  - ordinary diffs still classify added/removed/modified correctly
"""
import refresh_all_zones as R

_r = []


def check(name, cond):
    _r.append((name, bool(cond)))


def test_missing_old_counts_additions():
    new = {"htf_r": [(1, 2, "a"), (3, 4, "b")], "htf_s": [(5, 6, "c")]}
    out = R.compare_zones(None, new)
    check("missing old -> additions count all zones", out["added"] == 3 and out["removed"] == 0 and out["modified"] == 0)


def test_missing_new_counts_removals():
    old = {"htf_r": [(1, 2, "a"), (3, 4, "b")], "htf_s": [(5, 6, "c")]}
    out = R.compare_zones(old, None)
    check("missing new -> removals count all zones", out["removed"] == 3 and out["added"] == 0 and out["modified"] == 0)


def test_modified_and_unchanged():
    old = {"htf_r": [(1, 2, "old"), (3, 4, "same")], "htf_s": []}
    new = {"htf_r": [(1, 2, "new"), (3, 4, "same"), (7, 8, "added")], "htf_s": []}
    out = R.compare_zones(old, new)
    check("modified counted once", out["modified"] == 1)
    check("unchanged counted once", out["unchanged"] == 1)
    check("added counted once", out["added"] == 1)


if __name__ == "__main__":
    for fn in (test_missing_old_counts_additions, test_missing_new_counts_removals, test_modified_and_unchanged):
        fn()
    for name, ok in _r:
        if not ok:
            print(f"  [FAIL] {name}")
    passed = sum(1 for _, ok in _r if ok)
    print(f"\n{'✅' if passed == len(_r) else '❌'} {passed}/{len(_r)} checks passed")
    raise SystemExit(0 if passed == len(_r) else 1)
