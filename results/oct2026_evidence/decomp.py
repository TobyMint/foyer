import csv, json, sys
from collections import defaultdict

def load_metrics(p):
    rows=[]
    for r in csv.DictReader(open(p)):
        try: ts=float(r["ts"])
        except: continue
        def g(k):
            v=r.get(k,"")
            try: return float(v)
            except: return 0.0
        rows.append(dict(ts=ts, run=g("sglang:num_running_reqs"),
                         q=g("sglang:num_queue_reqs"),
                         used=g("sglang:num_used_tokens"),
                         gen=g("sglang:generation_tokens_total"),
                         pre=g("sglang:prompt_tokens_total"),
                         ev=g("sglang:evicted_tokens_total"),
                         tgt=g("sglang:generation_tokens_total")))
    rows.sort(key=lambda x:x["ts"])
    return rows

def load_steps(p):
    out=[]
    for l in open(p):
        r=json.loads(l)
        if r.get("status")!="SUCCESS": continue
        out.append(r)
    return out

def busy_union(steps):
    """Union of [submit, complete] intervals -> busy seconds."""
    iv=sorted((float(r["submit_timestamp"]), float(r["complete_timestamp"])) for r in steps)
    tot=0.0; cs,ce=None,None
    for s,e in iv:
        if cs is None: cs,ce=s,e
        elif s<=ce: ce=max(ce,e)
        else: tot+=ce-cs; cs,ce=s,e
    if cs is not None: tot+=ce-cs
    return tot, iv

def work_of(steps):
    """总工作量 = Σ(实际算的 token) = uncached_prompt + completion"""
    w=0
    for r in steps:
        w += int(r["server_uncached_prompt_tokens"]) + int(r["server_completion_tokens"])
    return w

def need_of(steps):
    return sum(int(r["input_len"])+int(r["output_len_actual"]) for r in steps)

for arm in ("long19_foyer","long19_default"):
    st=load_steps(f"{arm}/steps.jsonl"); mt=load_metrics(f"{arm}/metrics.csv")
    t0=min(float(r["submit_timestamp"]) for r in st)
    t1=max(float(r["complete_timestamp"]) for r in st)
    mk=(t1-t0)/60
    bu,iv=busy_union(st)
    W=work_of(st); N=need_of(st)
    print(f"\n=== {arm} ===")
    print(f"  会话 {len(set(r['session_id'] for r in st))}  步 {len(st)}")
    print(f"  makespan {mk:8.1f} 分   busy {bu/60:7.1f} 分   空闲 {100*(mk-bu/60)/mk:5.1f}%")
    print(f"  工作量 {W/1e6:6.2f}M   必要量 {N/1e6:6.2f}M   浪费 {W/N:5.2f}x")
    print(f"  吞吐  {W/1e6/mk:6.4f} M/分  (全时段)   {W/1e6/(bu/60):6.4f} M/分 (仅busy)")

    # 并发的时间加权分布
    dur=defaultdict(float); wsum=defaultdict(float)
    for a,b in zip(mt, mt[1:]):
        dt=b["ts"]-a["ts"]
        if dt<=0 or dt>60: continue
        n=int(round(a["run"]))
        dur[n]+=dt
        wsum[n]+= (b["gen"]-a["gen"]) + (b["pre"]-a["pre"]) if b["gen"]>=a["gen"] else 0
    T=sum(dur.values())
    print("  并发分布（时间加权）与各档吞吐：")
    for n in sorted(dur):
        pct=100*dur[n]/T
        rate=wsum[n]/dur[n] if dur[n]>0 else 0
        bar="#"*int(pct/2)
        print(f"    n={n}  {pct:5.1f}%  {rate:7.1f} tok/s  {bar}")
    # 累计
    tot_gen=mt[-1]["gen"]-mt[0]["gen"]; tot_pre=mt[-1]["pre"]-mt[0]["pre"]
    print(f"  引擎累计 token: prompt {tot_pre/1e6:.2f}M + gen {tot_gen/1e6:.2f}M = {(tot_pre+tot_gen)/1e6:.2f}M")
    print(f"  驱逐累计 evicted_tokens_total: {mt[-1]['ev']/1e6:.2f}M")
