#!/usr/bin/env python3
"""Tests for tpo.py — grouping the Realtime TPO Profile indicator's VA/POC line objects into per-session
value areas (VAH = max lime, VAL = min lime, POC = yellow), matched by RGB. Pure stdlib.
    python3 test_tpo.py   (exit 0 = all pass)
"""
import sys
import tpo as T

_r = []
def check(n, c): _r.append((n, bool(c)))


# real shapes observed on the chart: lime VA = 0x4076E600 (1081533952), yellow POC = 0x403BEBFF (1077668863),
# aqua separator = 0xFFD4BC00 (vertical, horizontal=False), with alpha varying.
LIME = 1081533952; YELLOW = 1077668863; AQUA = 4292131840


def test_pairs_and_poc():
    lines = [
        {"horizontal": True, "color": LIME,   "x1": 31, "y1": 4523.93},
        {"horizontal": True, "color": LIME,   "x1": 31, "y1": 4541.91},
        {"horizontal": True, "color": LIME,   "x1": 29, "y1": 4461.35},
        {"horizontal": True, "color": LIME,   "x1": 29, "y1": 4383.41},
        {"horizontal": True, "color": YELLOW, "x1": 29, "y1": 4389.40},
        {"horizontal": False,"color": AQUA,   "x1": 5,  "y1": 4500, "y2": 4400},  # vertical separator -> ignored
    ]
    s = T.tpo_sessions(lines)
    by = {d["x"]: d for d in s}
    check("session 31: VAH=max lime, VAL=min lime", by[31]["vah"] == 4541.91 and by[31]["val"] == 4523.93)
    check("session 29: VAH/VAL/POC correct, POC inside VA",
          by[29]["vah"] == 4461.35 and by[29]["val"] == 4383.41 and by[29]["poc"] == 4389.40
          and by[29]["val"] <= by[29]["poc"] <= by[29]["vah"])
    check("vertical separator (horizontal=False) ignored", 5 not in by)
    check("sorted by x", [d["x"] for d in s] == sorted(d["x"] for d in s))


def test_rgb_match_ignores_alpha():
    # same RGB, different alpha bytes -> still recognized as VA/POC
    lines = [
        {"horizontal": True, "color": 0x004076E600 & 0xFFFFFFFF, "x1": 7, "y1": 4600},
        {"horizontal": True, "color": (0xFF000000 | 0x0076E600), "x1": 7, "y1": 4500},
        {"horizontal": True, "color": (0x80000000 | 0x003BEBFF), "x1": 7, "y1": 4550},
    ]
    s = T.tpo_sessions(lines)
    by = {d["x"]: d for d in s}
    check("alpha-robust: VA pair recognized", by[7]["vah"] == 4600 and by[7]["val"] == 4500)
    check("alpha-robust: POC recognized", by[7]["poc"] == 4550)


def test_poc_only_session():
    lines = [{"horizontal": True, "color": YELLOW, "x1": 30, "y1": 4515.56}]
    s = T.tpo_sessions(lines)
    check("poc-only session emitted with null VA", s and s[0]["poc"] == 4515.56 and s[0]["vah"] is None)


def test_unrelated_colors_dropped():
    lines = [{"horizontal": True, "color": AQUA, "x1": 9, "y1": 4400},
             {"horizontal": True, "color": None, "x1": 9, "y1": 4410}]
    check("no VA/POC -> no session", T.tpo_sessions(lines) == [])


def test_session_sp():
    # Verbose TPO labels: ONE clean VA set at the anchor x (=28); the session's SP sit at x=28/29 (±1).
    # Replay residue / other sessions' SP sit at a far x (here 10) and MUST be dropped.
    labels = [
        {"text": "VAH", "price": 4467.28, "x": 28},
        {"text": "VAL", "price": 4348.87, "x": 28},
        {"text": "POC", "price": 4461.64, "x": 28},
        {"text": "SP", "price": 4382.70, "x": 29},   # current session SP (anchor+1) -> keep
        {"text": "SP", "price": 4388.34, "x": 29},
        {"text": "SP", "price": 4427.81, "x": 28},   # at anchor -> keep
        {"text": "SP", "price": 4494.11, "x": 10},   # residue from another cursor state -> drop
        {"text": "SP", "price": 4428.57, "x": 5},    # residue -> drop
    ]
    sp = T.session_sp(labels)
    check("session_sp: keeps only anchor-x (±1) SP", sorted(sp) == [4382.70, 4388.34, 4427.81])
    check("session_sp: drops far-x residue", 4494.11 not in sp and 4428.57 not in sp)


def test_session_sp_no_va():
    check("session_sp: no VA anchor -> []", T.session_sp([{"text": "SP", "price": 4400, "x": 5}]) == [])


def test_session_sp_no_sp():
    # a day with VA labels but genuinely no single prints -> []
    labels = [{"text": "VAH", "price": 4479, "x": 12}, {"text": "VAL", "price": 4444, "x": 12},
              {"text": "POC", "price": 4463, "x": 12}]
    check("session_sp: VA but no SP -> []", T.session_sp(labels) == [])


def test_group_sp():
    z = T.group_sp([4427, 4423, 4400, 4394, 4388, 4382])   # one run 4382-4400 + a tight pair 4423/4427
    check("group_sp: 2 zones from 2 clusters", len(z) == 2)
    check("group_sp: zones are [lo,hi], sorted", z[0] == [4382, 4400] and z[-1] == [4423, 4427])
    check("group_sp: empty -> []", T.group_sp([]) == [])
    check("group_sp: single level -> one point-zone", T.group_sp([4400]) == [[4400, 4400]])
    check("group_sp: dedups + ignores None", T.group_sp([4400, 4400, None]) == [[4400, 4400]])


def main():
    for fn in (test_pairs_and_poc, test_rgb_match_ignores_alpha, test_poc_only_session, test_unrelated_colors_dropped,
               test_session_sp, test_session_sp_no_va, test_session_sp_no_sp, test_group_sp):
        try: fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False); print(f"  !! {fn.__name__}: {e}")
    p = sum(1 for _, ok in _r if ok); t = len(_r)
    for n, ok in _r:
        if not ok: print(f"  [FAIL] {n}")
    print(f"\n{'OK' if p == t else 'FAIL'} {p}/{t} checks passed")
    sys.exit(0 if p == t else 1)


if __name__ == "__main__":
    main()
