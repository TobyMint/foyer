import json,collections,sys
def load(f):
    out={}; failed=collections.defaultdict(bool)
    for l in open(f):
        r=json.loads(l)
        s=r['session_id']
        if r.get('status')!='SUCCESS': failed[s]=True; continue
        out[(s,int(r['round_idx']))]=r
    return out,failed
def go(lab,fF,fD):
    F,ff=load(fF); D,fd=load(fD)
    dead={s for s in set(ff)|set(fd) if ff[s] or fd[s]}
    common=set(F)&set(D)
    t0f=min(float(F[k]['submit_timestamp']) for k in common)
    t0d=min(float(D[k]['submit_timestamp']) for k in common)
    per=collections.defaultdict(int)
    for s,k in common: per[s]=max(per[s],k)
    rows=[]
    for s in per:
        if s in dead: continue
        a=max(float(F[(s,k)]['complete_timestamp'])-t0f for k in range(per[s]+1) if (s,k) in F)
        b=max(float(D[(s,k)]['complete_timestamp'])-t0d for k in range(per[s]+1) if (s,k) in D)
        rows.append([s,per[s],a/60,b/60,a/b])
    rows.sort(key=lambda x:-x[4])
    rat=sorted(r[4] for r in rows); n=len(rows)
    print(f'--- {lab} ---  可比会话 {n}（排除被打死的 {len(dead)} 个）')
    print(f'   我们更慢 {sum(1 for r in rows if r[4]>1)}/{n}   比 p10={rat[n//10]:.2f} p50={rat[n//2]:.2f} p90={rat[9*n//10]:.2f} max={rat[-1]:.2f}')
    for r in rows[:3]: print(f'      {r[0][-8:]} {r[1]:>3}轮  {r[2]:>5.0f} vs {r[3]:>5.0f}  {r[4]:.2f}')
    return rows
go('long19 hc2','long19_foyer/steps.jsonl','long19_default/steps.jsonl')
go('big27  hc2','big27f/steps.jsonl','big27d/steps.jsonl')
