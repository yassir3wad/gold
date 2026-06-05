#!/usr/bin/env python3
"""Mine the trade logs into 'what actually works' — win-rate, net pips, profit factor and expectancy
broken down by setup type, grade, side, hour, plus a rejection-reason breakdown so you can see what the
scanner over-produces (→ what to pre-skip). Read-only: it never touches live state, charts, or Telegram.

Ingests every logs/<sym>/<YYYY-MM-DD>.csv PLUS the legacy signals_log.csv (the bulk gold history),
deduped by id. P/L is taken from the `pips` column (the source of truth); win = net pips > 0.

    python3 analyze_logs.py                 # everything, all pairs
    python3 analyze_logs.py --symbol XAUUSD # one pair
    python3 analyze_logs.py --days 7        # only the last 7 days
    python3 analyze_logs.py --md            # also write a dated summary to logs/_analysis/
"""
import os, sys, csv as _csv, glob, datetime as _dt
from collections import defaultdict

TVDIR = os.path.expanduser("~/tradingview-mcp")
COLS = ["id", "time", "side", "grade", "pattern", "entry", "sl", "tp1",
        "rng10", "body_p", "htf", "result", "exit", "pips"]
EXECUTED = {"TP1", "TP2", "SL", "timeout", "superseded", "BE"}   # a real trade was taken
TP_HIT   = {"TP1", "TP2"}

# rejection-reason buckets: substrings (lowercased) that map a reject note to a cause family.
REJECT_BUCKETS = {
    "dead chop":      ["chop", "whipsaw", "er 0.0", "er 0.1", "er 0.2", "dead tape", "directionless"],
    "counter-trend":  ["counter-trend", "counter ", "against the", "fading the", "regime up", "regime down"],
    "no room / R:R":  ["cramped", "no room", "room only", "neg r:r", "negative r:r", "into the wall",
                       "into resistance", "into support", "into the floor", "into structure", "poor r:r",
                       "upside-down", "0.4:1", "0.34", "0.43", "0.5:1"],
    "RSI extreme":    ["oversold", "overbought", "rsi 2", "rsi 3", "rsi 7", "rsi 8", "blow-off",
                       "capitulation", "exhaustion"],
    "chasing / knife":["chasing", "chase", "knife", "falling", "dead-cat", "climax", "vertical run",
                       "buying the top", "selling the bottom", "extended"],
    "duplicate":      ["duplicate", "stacking", "already", "re-trigger", "re-entry", "same thesis"],
}


def _num(x):
    try: return float(str(x).replace(",", "").strip())
    except Exception: return None


def _norm_grade(g):
    g = (g or "").strip()
    if not g or g.startswith("("): return "?"
    return g.split(" (")[0].strip()   # "B (open space)" -> "B"; "A+" / "C-into-zone" unchanged


OUTCOMES_DB = os.path.join(TVDIR, "outcomes.db")


def _load_rows_db(symbol=None, days=None):
    """Read rows from the SQLite outcomes DB, shaped identically to the CSV loader: each dict tagged
    with `sym` (from the DB `symbol` column), deduped by id (the DB already enforces a unique id)."""
    import outcome_db
    cutoff = _dt.datetime.now() - _dt.timedelta(days=days) if days else None
    out = []
    for r in outcome_db.rows(symbol=symbol, db=OUTCOMES_DB):
        r = dict(r)
        r["sym"] = (r.get("symbol") or "").upper() or (symbol.upper() if symbol else "XAUUSD")
        if cutoff:
            t = _parse_time(r.get("time"))
            if t and t < cutoff: continue
        out.append(r)
    return out


def load_rows(symbol=None, days=None):
    """Return list of dict rows tagged with `sym`, deduped by id. Newest source wins on conflict.
    Reads from the SQLite outcomes DB when it exists (the dual-written store); otherwise falls back
    to the CSV files (legacy behavior). Same row-dict shape either way."""
    if os.path.exists(OUTCOMES_DB):
        try:
            return _load_rows_db(symbol, days)
        except Exception:
            pass   # any DB read issue → fall back to CSV (never lose the analysis)
    cutoff = None
    if days:
        cutoff = _dt.datetime.now() - _dt.timedelta(days=days)
    sources = []   # (path, sym_hint)
    for p in sorted(glob.glob(os.path.join(TVDIR, "logs", "*", "*.csv"))):
        sym = os.path.basename(os.path.dirname(p)).upper()
        sources.append((p, sym))
    legacy = os.path.join(TVDIR, "signals_log.csv")
    if os.path.exists(legacy):
        sources.append((legacy, "XAUUSD"))   # legacy file predates the per-pair split = gold
    by_id = {}
    for path, sym in sources:
        if symbol and sym != symbol.upper():
            continue
        try: rows = list(_csv.DictReader(open(path)))
        except Exception: continue
        for r in rows:
            r["sym"] = sym
            if cutoff:
                t = _parse_time(r.get("time"))
                if t and t < cutoff: continue
            rid = r.get("id") or f"{path}:{len(by_id)}"
            by_id[rid] = r   # later sources overwrite — fine, ids don't collide across files in practice
    return list(by_id.values())


def _parse_time(s):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try: return _dt.datetime.strptime((s or "").strip(), fmt)
        except Exception: pass
    return None


def stats(pips):
    """Summary stats for a list of pip P/Ls (floats). Win = >0, loss = <0, scratch = 0."""
    n = len(pips)
    if not n:
        return dict(n=0, wins=0, losses=0, scratch=0, wr=0.0, net=0.0, pf=0.0,
                    avg_win=0.0, avg_loss=0.0, exp=0.0)
    wins   = [p for p in pips if p > 0]
    losses = [p for p in pips if p < 0]
    scratch = n - len(wins) - len(losses)
    gw = sum(wins); gl = -sum(losses)
    return dict(
        n=n, wins=len(wins), losses=len(losses), scratch=scratch,
        wr=100.0*len(wins)/n,
        net=sum(pips),
        pf=(gw/gl if gl else float("inf")),
        avg_win=(gw/len(wins) if wins else 0.0),
        avg_loss=(gl/len(losses) if losses else 0.0),
        exp=sum(pips)/n,
    )


def _pf(x):
    return "∞" if x == float("inf") else f"{x:.2f}"


def table(title, groups, lines):
    """groups: dict label -> stats dict. Sorted by net desc."""
    lines.append("")
    lines.append(f"── {title} ".ljust(78, "─"))
    lines.append(f"{'':22}{'n':>4}{'win%':>7}{'net':>8}{'PF':>6}{'avgW':>7}{'avgL':>7}{'exp':>7}")
    for label, s in sorted(groups.items(), key=lambda kv: -kv[1]["net"]):
        if not s["n"]: continue
        lines.append(f"{label[:21]:22}{s['n']:>4}{s['wr']:>6.0f}%{s['net']:>+8.0f}"
                     f"{_pf(s['pf']):>6}{s['avg_win']:>+7.0f}{s['avg_loss']:>-7.0f}{s['exp']:>+7.1f}")


def group_stats(rows, keyfn):
    g = defaultdict(list)
    for r in rows:
        p = _num(r.get("pips"))
        if p is None: continue
        g[keyfn(r)].append(p)
    return {k: stats(v) for k, v in g.items()}


def analyze(rows):
    lines = []
    executed = [r for r in rows if r.get("result") in EXECUTED and _num(r.get("pips")) is not None]
    rejected = [r for r in rows if r.get("result") == "rejected"]
    autoskip = [r for r in rows if r.get("result") == "auto-skip"]
    pending  = [r for r in rows if r.get("result") == "PENDING"]
    pl = [_num(r["pips"]) for r in executed]

    s = stats(pl)
    tp_hits = sum(1 for r in executed if r.get("result") in TP_HIT)
    lines.append("=" * 78)
    lines.append(f"  TRADE LOG ANALYSIS   ({s['n']} executed · {len(rejected)} rejected · "
                 f"{len(autoskip)} auto-skipped · {len(pending)} open)")
    lines.append("=" * 78)
    if s["n"]:
        lines.append(f"  Net: {s['net']:+.0f} pips    Win rate: {s['wr']:.0f}%  ({s['wins']}W / "
                     f"{s['losses']}L / {s['scratch']}=)    TP-hit rate: {100*tp_hits/s['n']:.0f}%")
        lines.append(f"  Profit factor: {_pf(s['pf'])}    Avg win: {s['avg_win']:+.0f}p    "
                     f"Avg loss: -{s['avg_loss']:.0f}p    Expectancy: {s['exp']:+.1f}p/trade")
    else:
        lines.append("  No executed trades in range.")

    if executed:
        table("By setup type", group_stats(executed, lambda r: r.get("pattern", "?")), lines)
        table("By grade",      group_stats(executed, lambda r: _norm_grade(r.get("grade"))), lines)
        table("By side",       group_stats(executed, lambda r: r.get("side", "?")), lines)
        table("By symbol",     group_stats(executed, lambda r: r.get("sym", "?")), lines)
        def hourkey(r):
            t = _parse_time(r.get("time"))
            return f"{t.hour:02d}:00" if t else "??"
        table("By hour (local)", group_stats(executed, hourkey), lines)

    # rejection breakdown — what the scanner over-produces (a reject can hit multiple buckets)
    if rejected:
        counts = defaultdict(int); unmatched = 0
        for r in rejected:
            note = str(r.get("pips", "")).lower()
            hit = False
            for bucket, keys in REJECT_BUCKETS.items():
                if any(k in note for k in keys):
                    counts[bucket] += 1; hit = True
            if not hit: unmatched += 1
        lines.append("")
        lines.append(f"── Rejection causes  ({len(rejected)} rejected — multi-tag) ".ljust(78, "─"))
        for bucket, c in sorted(counts.items(), key=lambda kv: -kv[1]):
            bar = "█" * round(30 * c / len(rejected))
            lines.append(f"  {bucket:18}{c:>4}  {bar}")
        if unmatched:
            lines.append(f"  {'(other)':18}{unmatched:>4}")
        # most-rejected setup types — these are the scanner's noisiest producers
        rej_by_pat = defaultdict(int)
        for r in rejected: rej_by_pat[r.get("pattern", "?")] += 1
        lines.append("  most-rejected setups: " +
                     ", ".join(f"{p} ({c})" for p, c in sorted(rej_by_pat.items(), key=lambda kv: -kv[1])[:5]))

    # hard-floor auto-skips — what the pre-hold floor absorbed before review (un-tradeable, never reached you)
    if autoskip:
        fb = defaultdict(int)
        for r in autoskip:
            note = str(r.get("pips", "")).lower()
            if "neg r:r" in note:   fb["neg R:R"] += 1
            if "counter" in note:   fb["counter-trend"] += 1
            if "dead chop" in note: fb["dead chop"] += 1
            if "wrong-way" in note: fb["wrong-way RSI"] += 1
        lines.append("")
        lines.append(f"── Hard-floor auto-skips  ({len(autoskip)} absorbed pre-review) ".ljust(78, "─"))
        for cause, c in sorted(fb.items(), key=lambda kv: -kv[1]):
            lines.append(f"  {cause:18}{c:>4}")
        skip_pat = defaultdict(int)
        for r in autoskip: skip_pat[r.get("pattern", "?")] += 1
        lines.append("  by setup: " + ", ".join(f"{p} ({c})" for p, c in sorted(skip_pat.items(), key=lambda kv: -kv[1])[:5]))

    # actionable read
    if executed:
        by_pat = group_stats(executed, lambda r: r.get("pattern", "?"))
        good = [p for p, st in by_pat.items() if st["net"] > 0 and st["n"] >= 2]
        bad  = [p for p, st in by_pat.items() if st["net"] < 0 and st["n"] >= 2]
        lines.append("")
        lines.append("── Read ".ljust(78, "─"))
        if good: lines.append("  ✅ paying setups (n≥2): " + ", ".join(good))
        if bad:  lines.append("  ❌ losing setups (n≥2): " + ", ".join(bad))
        lines.append("  ⚠ small sample — treat as directional until each cell has ~20+ trades.")
    return "\n".join(lines)


def main():
    symbol = None; days = None; write_md = "--md" in sys.argv
    if "--symbol" in sys.argv:
        try: symbol = sys.argv[sys.argv.index("--symbol") + 1]
        except Exception: pass
    if "--days" in sys.argv:
        try: days = int(sys.argv[sys.argv.index("--days") + 1])
        except Exception: pass
    rows = load_rows(symbol, days)
    report = analyze(rows)
    print(report)
    if write_md:
        d = os.path.join(TVDIR, "logs", "_analysis")
        os.makedirs(d, exist_ok=True)
        fn = os.path.join(d, _dt.datetime.now().strftime("%Y-%m-%d") + ".md")
        with open(fn, "w") as f:
            f.write("```\n" + report + "\n```\n")
        print(f"\n→ written to {fn}")


if __name__ == "__main__":
    main()
