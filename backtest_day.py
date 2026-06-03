#!/usr/bin/env python3
"""Backtest the scalp_fast momentum logic over the available 1m history.
Replays bar-by-bar (one trade at a time), simulates TP1/SL/timeout outcomes."""
import json, subprocess, os, datetime as dt
import scalp_fast as S
PIP = 0.10
GATE = 40        # vol gate: last-10-bar range in pips
HORIZON = 10     # 10-min rule: TP1 must hit within 10 bars

def tv(*a):
    r = subprocess.run(["node","src/cli/index.js",*a], cwd=os.path.expanduser("~/tradingview-mcp"),
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

def main():
    b=tv("ohlcv","-n","290").get("bars",[])
    print(f"bars={len(b)}  window {dt.datetime.utcfromtimestamp(b[0]['time'])}–{dt.datetime.utcfromtimestamp(b[-1]['time'])} UTC")
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
    # report
    wins=[t for t in trades if t[6]=="TP1"]; losses=[t for t in trades if t[6]=="SL"]; tos=[t for t in trades if t[6]=="timeout"]
    net=sum(t[7] for t in trades)
    print(f"\nSIGNALS: {len(trades)}  |  TP1 wins: {len(wins)}  |  SL losses: {len(losses)}  |  timeouts: {len(tos)}")
    wr = (len(wins)/ (len(wins)+len(losses))*100) if (wins or losses) else 0
    print(f"Win rate (excl timeouts): {wr:.0f}%   Net: {net:+.0f} pips (~${net:+.0f} @0.1 lot)")
    print("\n# side  grade  pattern            entry    SL     TP1     result   pips")
    for t in trades:
        print(f"{t[0]:5} {t[1]:3} {t[2]:16} {t[3]:7} {t[4]:6} {t[5]:7}  {t[6]:7} {t[7]:+.0f}")

if __name__=="__main__":
    main()
