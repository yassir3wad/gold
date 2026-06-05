#!/usr/bin/env python3
"""End-of-day Telegram digest — today's W/L, net pips, profit factor, and what the hard floor absorbed.
Read-only on the logs; sends via the same Telegram config the scanner uses. Run it from the loop at session
close, or by hand:
    python3 digest.py                 # today (rolling 24h), all pairs -> Telegram (+ print)
    python3 digest.py --print         # build + print only, no send
    python3 digest.py --symbol XAUUSD # one pair
"""
import os, sys, datetime as dt
sys.path.insert(0, os.path.expanduser("~/tradingview-mcp"))
import analyze_logs as al


def build_digest(rows, date_label):
    """Pure: render the daily summary text from log rows (so it's unit-testable, no I/O)."""
    executed = [r for r in rows if r.get("result") in al.EXECUTED and al._num(r.get("pips")) is not None]
    autoskip = [r for r in rows if r.get("result") == "auto-skip"]
    rejected = [r for r in rows if r.get("result") == "rejected"]
    s = al.stats([al._num(r["pips"]) for r in executed])
    if not executed:
        head = f"📊 Gold scalper — {date_label}\nNo trades taken today."
    else:
        pf = "∞" if s["pf"] == float("inf") else f"{s['pf']:.2f}"
        best = max(executed, key=lambda r: al._num(r["pips"]))
        worst = min(executed, key=lambda r: al._num(r["pips"]))
        head = (f"📊 Gold scalper — {date_label}\n"
                f"Trades: {s['n']} ({s['wins']}W / {s['losses']}L / {s['scratch']}=)  "
                f"Net: {s['net']:+.0f}p  PF {pf}  Exp {s['exp']:+.1f}p\n"
                f"Best {al._num(best['pips']):+.0f}p [{best.get('pattern','?')}]  ·  "
                f"Worst {al._num(worst['pips']):+.0f}p [{worst.get('pattern','?')}]")
    tail = f"\n🛡️ Filtered: {len(autoskip)} auto-skipped (floor) · {len(rejected)} rejected — none reached you."
    return head + tail


def main():
    do_print = "--print" in sys.argv
    symbol = None
    if "--symbol" in sys.argv:
        try: symbol = sys.argv[sys.argv.index("--symbol") + 1]
        except Exception: pass
    rows = al.load_rows(symbol, days=1)
    txt = build_digest(rows, dt.datetime.now().astimezone().strftime("%Y-%m-%d"))
    print(txt)
    if not do_print:
        import scalp_fast as sf
        sf._tg_text(txt)
        print("\n→ sent to Telegram")


if __name__ == "__main__":
    main()
