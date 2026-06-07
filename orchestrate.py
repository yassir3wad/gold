#!/usr/bin/env python3
"""One tick of the hands-free multi-pair loop:
  1) meta-scan all pairs (scan_pairs scoring),
  2) AI-review (--review) only the pairs that matter THIS tick = the top-scored / score>=FOCUS_MIN pairs
     (catch new setups) PLUS any pair with an ACTIVE trade (so TP/SL/BE management is never dropped),
  3) print a consolidated readout + flag any HELD trades for Claude to approve/reject.
Light by design: only the focus pairs get the full --review (the heavy 30m regime visit is cached ~20m).
    python3 orchestrate.py
"""
import subprocess, json, os, datetime as dt
import scan_pairs
TVDIR = os.path.expanduser("~/tradingview-mcp")
INSTR = json.load(open(os.path.join(TVDIR, "instruments.json")))
FOCUS_MIN = 55          # review any pair scoring >= this
TOP_N = 1               # always review at least the top-N scored pairs

def _state(sym, kind):
    return os.path.expanduser(f"~/.tv_fast_{sym.lower()}_{kind}.json")

def pinned_pairs():
    """Pairs to ALWAYS review regardless of score (e.g. 'keep an eye on gold'). Clear by emptying the file."""
    try: return [s.upper() for s in json.load(open(os.path.expanduser("~/.tv_fast_pinned.json")))]
    except Exception: return []

def active_pairs():
    out = []
    for sym in INSTR:
        if sym.startswith("_"): continue
        try:
            if json.load(open(_state(sym, "trade"))).get("active"): out.append(sym)
        except Exception: pass
    return out

def review(sym):
    try:
        result = subprocess.run(["bash", "aireview.sh", sym], cwd=TVDIR,
                                capture_output=True, text=True, timeout=140)
    except Exception:
        return False
    if result.returncode != 0:
        return False
    return os.path.exists(_state(sym, "pending"))

def orch_log(line):
    """Append one compact line/tick to a durable per-day all-pairs timeline (logs/_orch/<localdate>.log)."""
    try:
        d = os.path.join(TVDIR, "logs", "_orch")
        os.makedirs(d, exist_ok=True)
        f = os.path.join(d, dt.datetime.now().astimezone().strftime("%Y-%m-%d") + ".log")
        ts = dt.datetime.now().astimezone().strftime("%H:%M")
        with open(f, "a") as fh: fh.write(f"{ts} {line}\n")
    except Exception: pass

def main():
    rows = []
    for sym, cfg in INSTR.items():
        if sym.startswith("_"): continue
        s = scan_pairs.score_pair(sym, cfg)
        if s: rows.append(s)
    rows.sort(key=lambda r: -r["score"])
    act = set(active_pairs()); pin = set(pinned_pairs())
    focus = set(r["sym"] for r in rows[:TOP_N]) | set(r["sym"] for r in rows if r["score"] >= FOCUS_MIN) | act | pin

    print(f"=== ORCH {dt.datetime.now().astimezone():%Y-%m-%d %H:%M %Z} ===")
    score_str = "  ".join(f"{r['sym']}:{r['score']}({'in '+r['sess'] if r['sess']!='—' else 'off'},ER{r['er']})" for r in rows)
    print("scores: " + score_str)
    held = []
    for sym in sorted(focus):
        is_held = review(sym)
        tag = "ACTIVE-TRADE" if sym in act else ("pinned" if sym in pin else "focus")
        print(f"-- reviewed {sym} [{tag}]" + ("  *** HELD — REVIEW ***" if is_held else "  (nothing held)"))
        if is_held: held.append(sym)
    if held:
        print("\n>> HELD trades: " + ", ".join(held))
        for sym in held:
            try:
                t = json.load(open(_state(sym, "pending")))
                print(f"   {sym}: {t['side']} {t['grade']} | {t['why']} @ {t['entry']} | SL {t['sl']} TP1 {t['tp1']} | "
                      f"lot {t.get('lot','?')} | RSI {round(t.get('rsi',0),1)} ER {t.get('chop_er')} room {t.get('room')}p bias {t.get('bias')}")
            except Exception: pass
        print(">> Claude: review each, then approve.sh <SYM> \"reason\" / reject.sh <SYM> \"reason\".")
    else:
        print(f"\n>> no held trades. focus={rows[0]['sym'] if rows else '-'} (score {rows[0]['score'] if rows else '-'}); others quiet.")

    foc = rows[0]['sym'] if rows else '-'
    tail = ("HELD " + ",".join(held)) if held else f"quiet (focus {foc})"
    orch_log(f"{score_str} | {tail}")

if __name__ == "__main__":
    main()
