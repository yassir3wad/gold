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


def _fmt_prepare(sig: dict) -> str:
    """Heads-up 'get ready' alert — a setup is forming but NOT yet triggered."""
    L = []
    L.append(f"⏳ GOLD — SETUP FORMING (get ready)")
    if sig.get("setup"):   L.append(f"Setup: {sig['setup']}")
    if sig.get("regime"):  L.append(f"Regime: {sig['regime']}")
    if sig.get("price"):   L.append(f"Price now: {sig['price']}")
    if sig.get("watch"):   L.append(f"Watching: {sig['watch']}")
    # Either/both directional triggers, written out so the user can pre-stage.
    if sig.get("long_trigger"):  L.append(f"\n🟢 LONG if: {sig['long_trigger']}")
    if sig.get("short_trigger"): L.append(f"🔴 SHORT if: {sig['short_trigger']}")
    if sig.get("note"):    L.append(f"\n{sig['note']}")
    L.append("\n(heads-up only — no entry yet; the ENTER signal follows on the confirmed close)")
    return "\n".join(str(x) for x in L)


def send(sig: dict, dry_run: bool = False) -> bool:
    decision = sig.get("decision", "").upper()

    # PREPARE = pre-alert: a fresh setup is imminent (coiled at a breakout/reject level),
    # not yet a confirmed closed-candle entry. Sent so the user can get ready.
    if decision == "PREPARE":
        title = f"AI Scalp PREPARE — {sig.get('symbol','XAUUSD').split(':')[-1]}"
        body = _fmt_prepare(sig)
        shot = sig.get("screenshot")
        if shot and os.path.exists(shot):
            return bool(tg.send_photo(shot, caption=f"{title}\n\n{body}", dry_run=dry_run))
        return bool(tg.send_alert(title, body, dry_run=dry_run))

    if decision != "ENTER":
        print(f"[skip] decision={sig.get('decision')} (only ENTER / PREPARE are sent)")
        return False
    title = f"AI Scalp Signal — {sig.get('symbol','XAUUSD').split(':')[-1]}"
    body = _fmt(sig)
    shot = sig.get("screenshot")
    # Single Telegram message: image on top, full signal text as the caption.
    # (Telegram caption limit is 1024 chars; the signal body is well under that.)
    if shot and os.path.exists(shot):
        caption = f"{title}\n\n{body}"
        return bool(tg.send_photo(shot, caption=caption, dry_run=dry_run))
    if shot:
        print(f"[warn] screenshot not found: {shot}", file=sys.stderr)
    # No screenshot -> fall back to a text-only alert.
    return bool(tg.send_alert(title, body, dry_run=dry_run))


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
