#!/usr/bin/env python3
"""
Trade journaler. Creates trades/<name>/ with a chart screenshot + notes.md (full rationale).
Usage:
  python3 journal_trade.py --name "SHORT_4443_2103" --side SHORT --entry 4443 --sl 4448 \
      --tp1 4438 --tp2 4433 --grade "with-trend" --pattern "R4447 rejection" \
      --reason "free text rationale; use \\n for new lines"
Re-run with --close --result "..." to append the outcome to an existing trade's notes.
"""
import subprocess, json, os, sys, shutil, time, csv as _csv

TVDIR = os.path.expanduser("~/tradingview-mcp")
TRADES = os.path.join(TVDIR, "trades")
CSV = os.path.join(TRADES, "journal_log.csv")
CSV_COLS = ["name", "side", "entry", "sl", "tp1", "tp2", "grade", "pattern", "result"]

def csv_upsert(row):
    os.makedirs(TRADES, exist_ok=True)
    rows, found = [], False
    if os.path.exists(CSV):
        with open(CSV) as f:
            rows = list(_csv.DictReader(f))
    for r in rows:
        if r.get("name") == row["name"]:
            r.update(row); found = True
    if not found:
        rows.append(row)
    with open(CSV, "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in CSV_COLS})

def tv(*a):
    r = subprocess.run(["node", "src/cli/index.js", *a], cwd=TVDIR, capture_output=True, text=True, timeout=40)
    try: return json.loads(r.stdout)
    except Exception: return {}

TF_LABEL = {"D": "daily", "240": "4h", "60": "1h", "15": "15m", "5": "5m", "1": "1m"}

def reset_scale():
    """Double-click the price axis (x=1712 on the 1728-wide window) to reset auto-scale —
    without this, higher TFs render with a locked/crushed price scale (the 'broken/zoomed' look)."""
    tv("ui", "mouse", "--x", "1712", "--y", "400", "--double")
    time.sleep(1.5)

def shots(folder, tfs, prefix):
    """Screenshot the chart across multiple timeframes (HTF context + 1m execution); restore 1m after."""
    taken = []
    try:
        for tf in tfs:
            expected = "1D" if tf == "D" else tf
            # set TF and CONFIRM it applied (the 1m fast-cron can reset it mid-capture) — retry up to 4x
            for _ in range(4):
                tv("timeframe", tf)
                time.sleep(2.5)     # let TradingView re-render + load the new TF
                if str(tv("state").get("resolution")) == expected:
                    break
            reset_scale()           # auto-fit the price scale for THIS timeframe (critical for HTFs)
            s = tv("screenshot").get("file_path")
            if s and os.path.exists(s):
                lab = TF_LABEL.get(tf, tf)
                shutil.copy(s, os.path.join(folder, f"{prefix}_{lab}.png"))
                taken.append(lab)
    finally:
        tv("timeframe", "1")       # restore execution TF for the fast monitor
        time.sleep(2)
    return taken

def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag)+1] if flag in sys.argv else default

def main():
    name = arg("--name")
    if not name:
        print("ERR: --name required"); return
    folder = os.path.join(TRADES, name)
    os.makedirs(folder, exist_ok=True)

    if "--close" in sys.argv:
        with open(os.path.join(folder, "notes.md"), "a") as f:
            f.write(f"\n\n## OUTCOME\n{arg('--result','')}\n")
        reset_scale()
        s = tv("screenshot").get("file_path")
        if s and os.path.exists(s):
            shutil.copy(s, os.path.join(folder, "exit.png"))
        csv_upsert({"name": name, "result": arg("--result", "")})
        print(f"Closed/updated journal + CSV: {folder}")
        return

    price = tv("quote").get("last")
    # ONE screenshot of the analysed chart (auto-scaled). Per-TF reasoning goes in the notes (text), not images.
    reset_scale()
    s = tv("screenshot").get("file_path")
    if s and os.path.exists(s):
        shutil.copy(s, os.path.join(folder, "entry.png"))
    imgs = "![entry](entry.png)"

    side = arg("--side"); entry = arg("--entry"); sl = arg("--sl")
    tp1 = arg("--tp1"); tp2 = arg("--tp2"); grade = arg("--grade", "")
    pattern = arg("--pattern", ""); reason = arg("--reason", "").replace("\\n", "\n")
    tf_daily = arg("--tf-daily", "").replace("\\n", "\n")
    tf_4h = arg("--tf-4h", "").replace("\\n", "\n")
    tf_1h = arg("--tf-1h", "").replace("\\n", "\n")
    tf_15m = arg("--tf-15m", "").replace("\\n", "\n")
    tf_1m = arg("--tf-1m", "").replace("\\n", "\n")
    risk = abs(float(entry) - float(sl)) * 10 if entry and sl else "?"
    r1 = abs(float(tp1) - float(entry)) * 10 if tp1 and entry else "?"
    r2 = abs(float(tp2) - float(entry)) * 10 if tp2 and entry else "?"

    md = f"""# Trade: {name}

| Field | Value |
|---|---|
| Side | **{side}** |
| Entry | {entry} |
| Stop Loss | {sl}  (~{risk:.0f}p risk) |
| TP1 | {tp1}  (+{r1:.0f}p) |
| TP2 | {tp2}  (+{r2:.0f}p) |
| Grade | {grade} |
| Pattern/Setup | {pattern} |
| Price at journaling | {price} |

## Chart (analysed TF)
{imgs}

## Timeframe analysis — what each TF showed that allowed the entry
| TF | Read |
|---|---|
| **Daily** | {tf_daily} |
| **4H** | {tf_4h} |
| **1H** | {tf_1h} |
| **15m** | {tf_15m} |
| **1m (entry/confirm)** | {tf_1m} |

## Why we entered
{reason}

## Why this ENTRY
(entry rationale captured in reason above)

## Why this STOP LOSS
SL at {sl}: placed beyond the level/structure that invalidates the thesis. Risk ~{risk:.0f} pips.

## Why these TARGETS
TP1 {tp1} (+{r1:.0f}p) = first structure/partial; TP2 {tp2} (+{r2:.0f}p) = next swing/extension.

## Management rule
Take partial at TP1, move stop to breakeven, trail the runner. Quick-scalp: if TP1 not hit within ~10 min, exit.
"""
    with open(os.path.join(folder, "notes.md"), "w") as f:
        f.write(md)
    csv_upsert({"name": name, "side": side, "entry": entry, "sl": sl, "tp1": tp1,
                "tp2": tp2, "grade": grade, "pattern": pattern, "result": "OPEN"})
    print(f"Journaled: {folder}\n - entry.png\n - notes.md\n - logged to trades/journal_log.csv")

if __name__ == "__main__":
    main()
