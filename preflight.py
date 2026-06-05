#!/usr/bin/env python3
"""Morning pre-flight check — confirm the system is ready before the session opens:
TradingView/CDP connected, HTF zones fresh, news calendar loaded. One glance before London.
    python3 preflight.py
The status logic (fresh_status / overall) is pure + unit-tested; main() wires the real checks.
"""
import os, sys, json, time, subprocess, datetime as dt
TVDIR = os.path.expanduser("~/tradingview-mcp")


def fresh_status(exists, age_seconds, max_age):
    """'missing' if the file is absent, else 'ok' if within max_age seconds, else 'stale'."""
    if not exists:
        return "missing"
    return "ok" if age_seconds <= max_age else "stale"


def overall(statuses):
    """'READY' only when every check is 'ok'; otherwise 'CHECK'."""
    return "READY" if all(s == "ok" for s in statuses) else "CHECK"


def _age(path):
    try: return (True, time.time() - os.path.getmtime(path))
    except Exception: return (False, 0.0)


def main():
    try: instr = json.load(open(os.path.join(TVDIR, "instruments.json")))
    except Exception: instr = {}
    lines, statuses = [], []

    # 1) TradingView / CDP connection — a light state read proves the bridge is up
    try:
        r = subprocess.run(["node", "src/cli/index.js", "state"], cwd=TVDIR,
                           capture_output=True, text=True, timeout=30)
        conn = '"success": true' in r.stdout
    except Exception:
        conn = False
    statuses.append("ok" if conn else "missing")
    lines.append(f"  {'✅' if conn else '❌'} TradingView / CDP connection")

    # 2) HTF zones fresh per instrument (rebuild ~6h; flag if older than the usable-age ceiling)
    for sym, cfg in instr.items():
        if sym.startswith("_"): continue
        exists, age = _age(os.path.join(TVDIR, f"zones_{sym.lower()}.json"))
        st = fresh_status(exists, age, 18 * 3600)
        statuses.append(st)
        age_s = f" ({age/3600:.1f}h old)" if exists else ""
        lines.append(f"  {'✅' if st == 'ok' else '⚠️'} zones {sym}: {st}{age_s}")

    # 3) news calendar loaded + recent
    exists, age = _age(os.path.join(TVDIR, "news_week.json"))
    st = fresh_status(exists, age, 24 * 3600)
    statuses.append(st)
    lines.append(f"  {'✅' if st == 'ok' else '⚠️'} news calendar: {st}")

    verdict = overall(statuses)
    print(f"=== Pre-flight {dt.datetime.now().astimezone():%Y-%m-%d %H:%M %Z} ===  {verdict}")
    print("\n".join(lines))
    if verdict != "READY":
        print("\n→ Fixes: `tv_launch` if CDP down · `python3 refresh_zones.py --symbol <SYM>` for stale zones "
              "· `python3 news.py result` to load news.")


if __name__ == "__main__":
    main()
