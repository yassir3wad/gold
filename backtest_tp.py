import backtest_day as B
PIP=B.PIP; HOR=10
b=B.tv("ohlcv","-n","290").get("bars",[])
def run(tp1_p, trail0=None, lock=None):
    # trail0: move SL to (entry +/- lock) once price reaches +trail0 pips. Else fixed TP1.
    i=25; trades=[]
    while i<len(b)-1:
        sig=B.detect(b[:i+1])
        if not sig: i+=1; continue
        side,entry,struct,why=sig
        sl=B.levels(side,entry,struct)[0]
        tp1=entry+tp1_p*PIP if side=="LONG" else entry-tp1_p*PIP
        out="timeout"; xp=None; rb=None; cur_sl=sl
        for j in range(i+1,min(i+1+HOR,len(b))):
            bar=b[j]
            if side=="SHORT":
                # trailing
                if trail0 and bar['low']<=entry-trail0*PIP: cur_sl=min(cur_sl, entry-lock*PIP)
                if bar['high']>=cur_sl: out,xp,rb=("SL" if cur_sl>=entry else "trail",cur_sl,j); break
                if bar['low']<=tp1: out,xp,rb="TP1",tp1,j; break
            else:
                if trail0 and bar['high']>=entry+trail0*PIP: cur_sl=max(cur_sl, entry+lock*PIP)
                if bar['low']<=cur_sl: out,xp,rb=("SL" if cur_sl<=entry else "trail",cur_sl,j); break
                if bar['high']>=tp1: out,xp,rb="TP1",tp1,j; break
        if out=="timeout": rb=min(i+HOR,len(b)-1); xp=b[rb]['close']
        pips=(entry-xp)/PIP if side=="SHORT" else (xp-entry)/PIP
        trades.append((out,round(pips)))
        i=rb+1
    net=sum(p for _,p in trades); wins=sum(1 for o,p in trades if p>0); n=len(trades)
    return n,wins,net
print(f"bars={len(b)}\n")
print("CONFIG                       trades  green  net_pips(~$)")
for tp in [20,25,30,40,50]:
    n,w,net=run(tp); print(f"fixed TP1 +{tp:<3}p                  {n:5}  {w:5}   {net:+}")
n,w,net=run(50, trail0=20, lock=10); print(f"trail: lock +10 after +20p     {n:5}  {w:5}   {net:+}")
n,w,net=run(50, trail0=15, lock=5);  print(f"trail: lock +5 after +15p      {n:5}  {w:5}   {net:+}")
