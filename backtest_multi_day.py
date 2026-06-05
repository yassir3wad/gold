#!/usr/bin/env python3
"""Multi-day walk-forward backtesting framework.
Iterates over a date range, running single-day backtests for each day."""
import argparse, datetime as dt, json, subprocess, os
import scalp_fast as S

# Constants
PIP = 0.10
GATE = 40        # vol gate: last-10-bar range in pips
HORIZON = 10     # 10-min rule: TP1 must hit within 10 bars

def tv(*a):
    r = subprocess.run(["node","src/cli/index.js",*a], cwd=os.path.dirname(os.path.abspath(__file__)),
                       capture_output=True, text=True, timeout=40)
    try: return json.loads(r.stdout)
    except: return {}

def pivots(b, L=3, R=3):
    sh, sl = [], []
    for i in range(L, len(b)-R):
        if all(b[i]['high']>=b[i-k]['high'] for k in range(1,L+1)) and all(b[i]['high']>=b[i+k]['high'] for k in range(1,R+1)): sh.append((i,b[i]['high']))
        if all(b[i]['low']<=b[i-k]['low'] for k in range(1,L+1)) and all(b[i]['low']<=b[i+k]['low'] for k in range(1,R+1)): sl.append((i,b[i]['low']))
    return sh, sl

def line(p1,p2):
    (x1,y1),(x2,y2)=p1,p2
    if x2==x1: return None
    m=(y2-y1)/(x2-x1); return m, y1-m*x1

def detect(b):
    """Mirror scalp_fast: return (side, entry, struct, why) or None for the window b (last bar = trigger)."""
    n=len(b); last=b[-1]
    rng10=(max(x['high'] for x in b[-10:])-min(x['low'] for x in b[-10:]))/PIP
    if rng10<GATE: return None
    body=last['close']-last['open']; body_p=abs(body)/PIP
    avg=sum(abs(x['close']-x['open']) for x in b[-20:])/20/PIP
    strong=body_p>1.6*max(avg,0.5); bull=body>0
    sh,sl=pivots(b)
    res_tl=line(sh[-2],sh[-1]) if len(sh)>=2 else None
    sup_tl=line(sl[-2],sl[-1]) if len(sl)>=2 else None
    res_at=res_tl[0]*(n-1)+res_tl[1] if res_tl else None
    sup_at=sup_tl[0]*(n-1)+sup_tl[1] if sup_tl else None
    hi15=max(x['high'] for x in b[-15:]); lo15=min(x['low'] for x in b[-15:])
    tight=(hi15-lo15)/PIP<35
    dtop=len(sh)>=2 and abs(sh[-1][1]-sh[-2][1])/PIP<8
    dbot=len(sl)>=2 and abs(sl[-1][1]-sl[-2][1])/PIP<8
    buf=2*PIP; p2=b[-2]; p2b=(p2['close']-p2['open'])/PIP
    S_=[]
    if res_at and strong and bull and last['close']>res_at+buf and last['open']<=res_at+buf: S_.append(("LONG","res-TL break",lo15))
    if sup_at and strong and not bull and last['close']<sup_at-buf and last['open']>=sup_at-buf: S_.append(("SHORT","sup-TL break",hi15))
    if tight and strong and bull and last['close']>hi15: S_.append(("LONG","range break",lo15))
    if tight and strong and not bull and last['close']<lo15: S_.append(("SHORT","range break",hi15))
    if dbot and strong and bull and last['close']>hi15: S_.append(("LONG","double-bottom",min(sl[-1][1],sl[-2][1])))
    if dtop and strong and not bull and last['close']<lo15: S_.append(("SHORT","double-top",max(sh[-1][1],sh[-2][1])))
    if strong and bull and p2b>1.0*max(avg,0.5): S_.append(("LONG","impulse",min(last['low'],p2['low'])))
    if strong and not bull and p2b<-1.0*max(avg,0.5): S_.append(("SHORT","impulse",max(last['high'],p2['high'])))
    if not S_: return None
    side,why,struct=S_[0]
    return side, last['close'], struct, why

def levels(side, entry, struct):
    if side=="LONG":
        sl=max(min(struct, entry-30*PIP), entry-35*PIP); return sl, entry+50*PIP, entry+100*PIP
    sl=min(max(struct, entry+30*PIP), entry+35*PIP); return sl, entry-50*PIP, entry-100*PIP

def parse_date(s):
    """Parse YYYY-MM-DD string to date object."""
    try:
        return dt.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid date format '{s}': {e}")

def iter_days(start, end):
    """Yield each date from start to end (inclusive)."""
    current = start
    while current <= end:
        yield current
        current += dt.timedelta(days=1)

def backtest_day(day):
    """Run backtest for a single day. Returns dict with results."""
    b=tv("ohlcv","-n","290").get("bars",[])
    if not b:
        return {"date": day, "bars": 0, "signals": 0, "wins": 0, "losses": 0, "timeouts": 0, "net_pips": 0, "trades": []}

    trades=[]; i=25
    while i < len(b)-1:
        sig=detect(b[:i+1])
        if not sig: i+=1; continue
        side,entry,struct,why=sig
        sl,tp1,tp2=levels(side,entry,struct)
        grade="B"
        if S.near_htf(entry,S.HTF_R): grade="A+" if side=="SHORT" else "A"
        elif S.near_htf(entry,S.HTF_S): grade="A+" if side=="LONG" else "A"
        # simulate forward up to HORIZON bars
        outcome="timeout"; exitp=None; res_bar=None
        for j in range(i+1, min(i+1+HORIZON, len(b))):
            bar=b[j]
            if side=="SHORT":
                if bar['high']>=sl: outcome,exitp,res_bar="SL",sl,j; break
                if bar['low']<=tp1: outcome,exitp,res_bar="TP1",tp1,j; break
            else:
                if bar['low']<=sl: outcome,exitp,res_bar="SL",sl,j; break
                if bar['high']>=tp1: outcome,exitp,res_bar="TP1",tp1,j; break
        if outcome=="timeout":
            res_bar=min(i+HORIZON,len(b)-1); exitp=b[res_bar]['close']
        pips=(entry-exitp)/PIP if side=="SHORT" else (exitp-entry)/PIP
        trades.append((side,grade,why,round(entry,1),round(sl,1),round(tp1,1),outcome,round(pips,0)))
        i=res_bar+1   # one trade at a time: resume after it resolves

    # compute stats
    wins=[t for t in trades if t[6]=="TP1"]
    losses=[t for t in trades if t[6]=="SL"]
    tos=[t for t in trades if t[6]=="timeout"]
    net=sum(t[7] for t in trades)

    return {
        "date": day,
        "bars": len(b),
        "signals": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "timeouts": len(tos),
        "net_pips": net,
        "trades": trades
    }

def generate_walk_forward_windows(start_date, end_date, train_days, test_days):
    """Generate sliding windows for walk-forward optimization.
    Returns list of (train_start, train_end, test_start, test_end) tuples."""
    windows = []
    current_start = start_date

    while True:
        train_start = current_start
        train_end = train_start + dt.timedelta(days=train_days - 1)
        test_start = train_end + dt.timedelta(days=1)
        test_end = test_start + dt.timedelta(days=test_days - 1)

        # Stop if test period extends beyond end_date
        if test_end > end_date:
            break

        windows.append((train_start, train_end, test_start, test_end))

        # Slide window forward by test_days
        current_start = test_start

    return windows

def backtest_period(start_date, end_date):
    """Run backtest for a date range. Returns aggregated results."""
    days = list(iter_days(start_date, end_date))
    all_results = []

    for day in days:
        result = backtest_day(day)
        all_results.append(result)

    # Aggregate stats
    total_signals = sum(r['signals'] for r in all_results)
    total_wins = sum(r['wins'] for r in all_results)
    total_losses = sum(r['losses'] for r in all_results)
    total_timeouts = sum(r['timeouts'] for r in all_results)
    total_net = sum(r['net_pips'] for r in all_results)
    win_rate = (total_wins / (total_wins+total_losses)*100) if (total_wins or total_losses) else 0

    return {
        "days": len(days),
        "signals": total_signals,
        "wins": total_wins,
        "losses": total_losses,
        "timeouts": total_timeouts,
        "net_pips": total_net,
        "win_rate": win_rate,
        "daily_results": all_results
    }

def main():
    parser = argparse.ArgumentParser(description="Multi-day walk-forward backtesting")
    parser.add_argument("--start-date", required=True, type=parse_date, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, type=parse_date, help="End date (YYYY-MM-DD)")
    parser.add_argument("--walk-forward", action="store_true", help="Enable walk-forward optimization mode")
    parser.add_argument("--train-days", type=int, default=5, help="Training window size in days (default: 5)")
    parser.add_argument("--test-days", type=int, default=2, help="Testing window size in days (default: 2)")
    parser.add_argument("--dry-run", action="store_true", help="Print dates without running backtests")
    args = parser.parse_args()

    if args.start_date > args.end_date:
        parser.error(f"start-date {args.start_date} is after end-date {args.end_date}")

    if args.train_days < 1:
        parser.error(f"train-days must be at least 1")
    if args.test_days < 1:
        parser.error(f"test-days must be at least 1")

    # Walk-forward mode
    if args.walk_forward:
        windows = generate_walk_forward_windows(args.start_date, args.end_date, args.train_days, args.test_days)
        if not windows:
            parser.error(f"Date range too small for train-days={args.train_days} and test-days={args.test_days}")

        print(f"Walk-forward optimization mode")
        print(f"Date range: {args.start_date} to {args.end_date}")
        print(f"Training window: {args.train_days} days")
        print(f"Testing window: {args.test_days} days")
        print(f"Number of windows: {len(windows)}\n")

        if args.dry_run:
            print("Dry-run mode: walk-forward windows...")
            for i, (train_start, train_end, test_start, test_end) in enumerate(windows, 1):
                print(f"  Window {i}:")
                print(f"    Train: {train_start} to {train_end} ({args.train_days} days)")
                print(f"    Test:  {test_start} to {test_end} ({args.test_days} days)")
        else:
            window_results = []
            for i, (train_start, train_end, test_start, test_end) in enumerate(windows, 1):
                print(f"\n{'='*60}")
                print(f"WINDOW {i}/{len(windows)}")
                print('='*60)
                print(f"Train: {train_start} to {train_end} ({args.train_days} days)")
                print(f"Test:  {test_start} to {test_end} ({args.test_days} days)\n")

                # Run training period
                print(f"--- Training Period ---")
                train_results = backtest_period(train_start, train_end)
                print(f"Signals: {train_results['signals']}  |  Wins: {train_results['wins']}  |  Losses: {train_results['losses']}  |  Timeouts: {train_results['timeouts']}")
                print(f"Win rate: {train_results['win_rate']:.0f}%  |  Net: {train_results['net_pips']:+.0f} pips")

                # Run testing period
                print(f"\n--- Testing Period ---")
                test_results = backtest_period(test_start, test_end)
                print(f"Signals: {test_results['signals']}  |  Wins: {test_results['wins']}  |  Losses: {test_results['losses']}  |  Timeouts: {test_results['timeouts']}")
                print(f"Win rate: {test_results['win_rate']:.0f}%  |  Net: {test_results['net_pips']:+.0f} pips")

                window_results.append({
                    "window": i,
                    "train_start": train_start,
                    "train_end": train_end,
                    "test_start": test_start,
                    "test_end": test_end,
                    "train": train_results,
                    "test": test_results
                })

            # Print walk-forward summary
            print(f"\n{'='*60}")
            print("WALK-FORWARD SUMMARY")
            print('='*60)
            total_test_signals = sum(w['test']['signals'] for w in window_results)
            total_test_wins = sum(w['test']['wins'] for w in window_results)
            total_test_losses = sum(w['test']['losses'] for w in window_results)
            total_test_timeouts = sum(w['test']['timeouts'] for w in window_results)
            total_test_net = sum(w['test']['net_pips'] for w in window_results)
            overall_test_wr = (total_test_wins / (total_test_wins+total_test_losses)*100) if (total_test_wins or total_test_losses) else 0

            print(f"Windows tested: {len(window_results)}")
            print(f"Test period signals: {total_test_signals}")
            print(f"Test period wins: {total_test_wins}")
            print(f"Test period losses: {total_test_losses}")
            print(f"Test period timeouts: {total_test_timeouts}")
            print(f"Test period win rate: {overall_test_wr:.0f}%")
            print(f"Test period net: {total_test_net:+.0f} pips (~${total_test_net:+.0f} @0.1 lot)")

            print("\nPer-window test results:")
            for w in window_results:
                print(f"  Window {w['window']}: {w['test']['net_pips']:+.0f} pips (WR: {w['test']['win_rate']:.0f}%)")

    # Normal sequential mode
    else:
        days = list(iter_days(args.start_date, args.end_date))
        print(f"Date range: {args.start_date} to {args.end_date} ({len(days)} days)")

        if args.dry_run:
            print("\nDry-run mode: iterating over dates...")
            for day in days:
                print(f"  {day}")
            print(f"\nTotal: {len(days)} days")
        else:
            print("\nRunning backtests...")
            all_results = []
            for day in days:
                print(f"\n{'='*60}")
                print(f"Backtesting {day}")
                print('='*60)
                result = backtest_day(day)
                all_results.append(result)

                # Print day summary
                print(f"Bars: {result['bars']}  |  Signals: {result['signals']}  |  TP1 wins: {result['wins']}  |  SL losses: {result['losses']}  |  Timeouts: {result['timeouts']}")
                wr = (result['wins']/ (result['wins']+result['losses'])*100) if (result['wins'] or result['losses']) else 0
                print(f"Win rate (excl timeouts): {wr:.0f}%   Net: {result['net_pips']:+.0f} pips (~${result['net_pips']:+.0f} @0.1 lot)")

                # Print trades
                if result['trades']:
                    print("\n# side  grade  pattern            entry    SL     TP1     result   pips")
                    for t in result['trades']:
                        print(f"{t[0]:5} {t[1]:3} {t[2]:16} {t[3]:7} {t[4]:6} {t[5]:7}  {t[6]:7} {t[7]:+.0f}")

            # Print overall summary
            print(f"\n{'='*60}")
            print("OVERALL SUMMARY")
            print('='*60)
            total_signals = sum(r['signals'] for r in all_results)
            total_wins = sum(r['wins'] for r in all_results)
            total_losses = sum(r['losses'] for r in all_results)
            total_timeouts = sum(r['timeouts'] for r in all_results)
            total_net = sum(r['net_pips'] for r in all_results)
            overall_wr = (total_wins / (total_wins+total_losses)*100) if (total_wins or total_losses) else 0
            print(f"Days tested: {len(days)}")
            print(f"Total signals: {total_signals}")
            print(f"Total TP1 wins: {total_wins}")
            print(f"Total SL losses: {total_losses}")
            print(f"Total timeouts: {total_timeouts}")
            print(f"Overall win rate (excl timeouts): {overall_wr:.0f}%")
            print(f"Overall net: {total_net:+.0f} pips (~${total_net:+.0f} @0.1 lot)")

if __name__=="__main__":
    main()
