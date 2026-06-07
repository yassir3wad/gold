#!/usr/bin/env python3
"""Regression tests for draw_zones.py tagging helpers."""
import draw_zones as D


def test_lab_of_tags_drawings():
    assert D.TAG in D.lab_of("Resistance 4H (flip)", "R")
    assert D.TAG in D.lab_of("Support 1H", "S")
    print("✓ draw labels are tagged for scoped cleanup")


if __name__ == "__main__":
    test_lab_of_tags_drawings()
    print("\n✓ ALL draw_zones tests passed")
