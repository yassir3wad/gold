#!/usr/bin/env python3
"""
ai-signal/send_signal.py — format a committee scalp signal and push it to Telegram
(text alert + chart screenshot), reusing the project's telegram_notify module.

Usage:
  echo '<signal json>' | python3 ai-signal/send_signal.py [--dry-run]

Signal JSON shape (the AI tick agent emits this):
{
  "decision": "ENTER",                 # only ENTER is sent; WAIT/REJECT/MANAGE are ignored here
  "symbol": "PEPPERSTONE:XAUUSD",
  "direction": "SHORT",                # LONG | SHORT
  "strategy": "OFVWAP + SVP HD",       # which committee members fired
  "committee": "4/5 agree",            # confluence tally
  "regime": "trend-down (15m)",
  "location": "VAH/upper-band 4345 reject",
  "entry": 4343.0, "sl": 4350.0, "tp1": 4330.0, "tp2": 4320.0,
  "rr_tp1": 1.4,
  "reason": "15m VWAP reject + SVP VAH confluence, with-trend; 5m-timed entry",
  "screenshot": "/Users/yassir3wad/tradingview-mcp/screenshots/ai_signal_xxx.png"
}
"""
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/tradingview-mcp"))
import telegram_notify as tg


def _fmt(sig: dict) -> str:
    emoji = "🟢" if sig.get("direction", "").upper() == "LONG" else "🔴"
    L = []
    L.append(f"{emoji} GOLD SCALP — {sig.get('direction','?')}")
    L.append(f"Strategy: {sig.get('strategy','?')}  ({sig.get('committee','')})")
    if sig.get("regime"):   L.append(f"Regime: {sig['regime']}")
    if sig.get("location"): L.append(f"Location: {sig['location']}")
    L.append(f"Entry: {sig.get('entry','?')}")
    L.append(f"SL: {sig.get('sl','?')}")
    tps = f"TP1: {sig.get('tp1','?')}"
    if sig.get("tp2"): tps += f"   TP2: {sig['tp2']}"
    L.append(tps)
    if sig.get("rr_tp1"): L.append(f"R:R(TP1): ~{sig['rr_tp1']}")
    if sig.get("reason"):  L.append(f"\n{sig['reason']}")
    return "\n".join(str(x) for x in L)


def send(sig: dict, dry_run: bool = False) -> bool:
    if sig.get("decision", "").upper() != "ENTER":
        print(f"[skip] decision={sig.get('decision')} (only ENTER is sent)")
        return False
    title = f"AI Scalp Signal — {sig.get('symbol','XAUUSD').split(':')[-1]}"
    body = _fmt(sig)
    ok_txt = tg.send_alert(title, body, dry_run=dry_run)
    ok_img = True
    shot = sig.get("screenshot")
    if shot and os.path.exists(shot):
        ok_img = tg.send_photo(shot, caption=f"{sig.get('direction','')} {sig.get('entry','')}", dry_run=dry_run)
    elif shot:
        print(f"[warn] screenshot not found: {shot}", file=sys.stderr)
    return bool(ok_txt and ok_img)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    raw = sys.stdin.read().strip()
    if not raw:
        print("no signal json on stdin"); sys.exit(1)
    try:
        sig = json.loads(raw)
    except Exception as e:
        print(f"bad json: {e}", file=sys.stderr); sys.exit(1)
    ok = send(sig, dry_run=dry)
    print("sent" if ok else "not-sent")
    sys.exit(0 if ok else 2)
