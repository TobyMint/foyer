import csv, json
from collections import defaultdict

def metrics(p):
    out=[]
    for r in csv.DictReader(open(p)):
        try: ts=float(r["ts"])
        except: continue
        def g(k):
            try: return float(r[k])
            except: return 0.0
        out.append((ts, g("sglang:num_running_reqs"), g("sglang:num_queue_reqs"), g("sglang:num_used_tokens")))
    out.sort(); return out

def at(mt, t):
    lo,hi=0,len(mt)-1
    while lo<hi:
        m=(lo+hi)//2
        if mt[m][0]<t: lo=m+1
        else: hi=m
    return mt[lo]

for arm in ("long19_foyer","long19_default"):
    mt=metrics(arm+"/metrics.csv")
    st=[json.loads(l) for l in open(arm+"/steps.jsonl")]
    st=[r for r in st if r.get("status")=="SUCCESS"]
    buck=defaultdict(lambda:[0,0.0,0])   # n -> [tokens, seconds, count]
    for r in st:
        u=int(r["server_uncached_prompt_tokens"])+int(r["server_completion_tokens"])
        dur=float(r["total_duration_ms"])/1000.0
        mid=(float(r["submit_timestamp"])+float(r["complete_timestamp"]))/2
        n=int(round(at(mt,mid)[1]))
        b=buck[n]; b[0]+=u; b[1]+=dur; b[2]+=1
    print(f"\n=== {arm} ===")
    print(f"{'并发':>4}{'步数':>7}{'有效token':>12}{'占算力':>8}{'算力率tok/s':>12}{'每token ms':>11}")
    tot=sum(b[0] for b in buck.values()); tt=sum(b[1] for b in buck.values())
    for n in sorted(buck):
        u,d,c=buck[n]
        print(f"{n:>4}{c:>7}{u/1e6:>11.2f}M{100*u/tot:>7.1f}%{u/d:>12.0f}{1000*d/u:>11.2f}")
    print(f"{'合计':>4}{sum(b[2] for b in buck.values()):>7}{tot/1e6:>11.2f}M{100:>7.1f}%{tot/tt:>12.0f}{1000*tt/tot:>11.2f}")
