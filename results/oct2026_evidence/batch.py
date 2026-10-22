import re, sys, datetime
from collections import defaultdict
RE_P=re.compile(r"^\[([\d\- :]+)\] Prefill batch, #new-seq: (\d+), #new-token: (\d+), #cached-token: (\d+), token usage: ([\d.]+), #running-req: (\d+), #queue-req: (\d+)")
RE_D=re.compile(r"^\[([\d\- :]+)\] Decode batch, #running-req: (\d+), #token: (\d+), token usage: ([\d.]+), .*gen throughput \(token/s\): ([\d.]+), #queue-req: (\d+)")
def parse(p):
    ev=[]
    for l in open(p, errors="ignore"):
        m=RE_P.match(l)
        if m:
            t=datetime.datetime.strptime(m.group(1),"%Y-%m-%d %H:%M:%S")
            ev.append((t.timestamp(),"P",int(m.group(2)),int(m.group(3)),int(m.group(4)),float(m.group(5)),int(m.group(6)),int(m.group(7)),0.0)); continue
        m=RE_D.match(l)
        if m:
            t=datetime.datetime.strptime(m.group(1),"%Y-%m-%d %H:%M:%S")
            ev.append((t.timestamp(),"D",0,0,0,float(m.group(4)),int(m.group(2)),int(m.group(6)),float(m.group(5))))
    ev.sort(); return ev
for arm in ("long19_foyer","long19_default"):
    ev=parse(f"/tmp/an/srv/{arm}.log")
    t0=min(e[0] for e in ev); t1=max(e[0] for e in ev)
    pre=[e for e in ev if e[1]=="P"]; dec=[e for e in ev if e[1]=="D"]
    print(f"\n=== {arm} ===  跨度 {(t1-t0)/60:.1f} 分   prefill 批 {len(pre)}   decode 批 {len(dec)}")
    # decode 时间加权
    dur=defaultdict(float); thr=defaultdict(float); use=defaultdict(float)
    for a,b in zip(dec,dec[1:]):
        dt=b[0]-a[0]
        if not(0<dt<=5): continue
        n=min(a[6],8); dur[n]+=dt; thr[n]+=a[8]*dt; use[n]+=a[5]*dt
    T=sum(dur.values())
    print(f"  {'running':>8}{'占比':>8}{'时间(min)':>11}{'生成吞吐tok/s':>14}{'池占用%':>9}")
    for n in sorted(dur):
        print(f"  {n:>8}{100*dur[n]/T:>7.1f}%{dur[n]/60:>11.1f}{thr[n]/dur[n]:>14.0f}{100*use[n]/dur[n]:>9.1f}")
    print(f"  {'合计':>8}{100:>7.1f}%{T/60:>11.1f}{thr and sum(thr.values())/T:>14.0f}{100*sum(use.values())/T:>9.1f}")
    # prefill 累计
    nt=sum(e[3] for e in pre); nc=sum(e[4] for e in pre)
    print(f"  prefill 累计: new-token {nt/1e6:.2f}M  cached-token {nc/1e6:.2f}M  (命中 {100*nc/max(nt+nc,1):.1f}%)")
