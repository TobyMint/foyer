#!/bin/bash
# Server-side finisher: waits for both repeat-lane DONE markers, then writes a
# self-contained summary file. Survives laptop reboots / session loss — the next
# session just reads REPEATS_SUMMARY.txt.
N=/data/xbw/turnstile/results/night
while [ ! -f $N/lane_repA_DONE ] || [ ! -f $N/lane_repB_DONE ]; do sleep 300; done
sleep 60
python3 - <<'EOF' > /data/xbw/turnstile/results/night/REPEATS_SUMMARY.txt 2>&1
import json, statistics, os
def load(run):
    p=f'/data/xbw/turnstile/results/night/{run}'
    meta=json.load(open(p+'/metadata.json'))
    ttfts=[];fails=0;sessions=set()
    for line in open(p+'/steps.jsonl'):
        try: r=json.loads(line)
        except: continue
        if r.get('session_id'): sessions.add(r['session_id'])
        if r.get('status')!='SUCCESS': fails+=1; continue
        if r.get('first_token_ms') is not None: ttfts.append(r['first_token_ms'])
    hit=None
    if os.path.exists(p+'/summary.json'):
        hit=json.load(open(p+'/summary.json')).get('replay',{}).get('server_prefix_hit_rate')
    return dict(n=len(sessions),wall=meta.get('wall_s',0)/60,rc=meta.get('runner_rc'),fails=fails,
                hit=(hit*100 if hit is not None else float('nan')),
                p50=(sorted(ttfts)[len(ttfts)//2] if ttfts else float('nan')),
                mean=(statistics.mean(ttfts) if ttfts else float('nan')),
                slo=(sum(1 for t in ttfts if t<10000)/len(ttfts)*100 if ttfts else float('nan')))
runs=['budget2','budget2_r2','budget2_r3','cap4','cap4_r2','cap4_r3','aimd','aimd_r2','aimd_r3',
      'budget2_nohw','budget2_nosf','budget2_nosv']
print('%-16s%6s%8s%6s%7s%8s%10s%10s%8s'%('run','sess','wall_m','rc','fails','hit%','ttft_p50','ttft_mean','slo%'))
res={}
for r in runs:
    try:
        d=load(r); res[r]=d
        print('%-16s%6d%8.0f%6s%7d%8.1f%10.1f%10.1f%8.1f'%(r,d['n'],d['wall'],d['rc'],d['fails'],d['hit'],d['p50'],d['mean'],d['slo']))
    except Exception as e: print('%-16s ERR %s'%(r,e))
# error-bar ranges per config
import collections
groups=collections.defaultdict(list)
for r,d in res.items():
    base=r.replace('_r2','').replace('_r3','')
    groups[base].append(d)
print('\n=== repeat ranges (min-max over runs incl. original) ===')
for g,ds in sorted(groups.items()):
    if len(ds)>1:
        print('%-14s n=%d  hit %.1f-%.1f  ttft_p50 %.1f-%.1f  slo %.1f-%.1f  wall %.0f-%.0f'%(
            g,len(ds),min(x['hit'] for x in ds),max(x['hit'] for x in ds),
            min(x['p50'] for x in ds)/1000,max(x['p50'] for x in ds)/1000,
            min(x['slo'] for x in ds),max(x['slo'] for x in ds),
            min(x['wall'] for x in ds),max(x['wall'] for x in ds)))
EOF
echo done >> /data/xbw/turnstile/results/night/REPEATS_SUMMARY.txt
