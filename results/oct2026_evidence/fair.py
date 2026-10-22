import json,collections,sys
def load(f):
    st=[json.loads(l) for l in open(f)]
    return {(r['session_id'],int(r['round_idx'])):r for r in st if r.get('status')=='SUCCESS'}
def go(lab,fF,fD):
    F=load(fF); D=load(fD); common=set(F)&set(D)
    t0f=min(float(F[k]['submit_timestamp']) for k in common)
    t0d=min(float(D[k]['submit_timestamp']) for k in common)
    per=collections.defaultdict(int)
    for s,k in common: per[s]=max(per[s],k)
    rows=[]
    for s in per:
        a=max(float(F[(s,k)]['complete_timestamp'])-t0f for k in range(per[s]+1) if (s,k) in F)
        b=max(float(D[(s,k)]['complete_timestamp'])-t0d for k in range(per[s]+1) if (s,k) in D)
        rows.append((s,per[s],a/60,b/60,a/b))
    rows.sort(key=lambda x:-x[2])
    rat=sorted(r[4] for r in rows)
    n=len(rows); worse=sum(1 for r in rows if r[4]>1)
    print(f'--- {lab} ---  可比会话 {n}（共同集 {len(common)} 步）')
    print(f'   我们更慢: {worse}/{n}    每会话比 p10={rat[n//10]:.2f} p50={rat[n//2]:.2f} p90={rat[9*n//10]:.2f} max={rat[-1]:.2f}')
    print(f'   绝对最慢: 我们 {rows[0][2]:.0f} 分 vs 无控制 {rows[0][3]:.0f} 分')
    print(f'   绝对最快: 我们 {rows[-1][2]:.0f} 分 vs 无控制 {rows[-1][3]:.0f} 分')
    return rows
go('long19 hc2','long19_foyer/steps.jsonl','long19_default/steps.jsonl')
go('big27  hc2','big27f/steps.jsonl','big27d/steps.jsonl')
