import datetime
from collections import Counter
RE_LINE=datetime.datetime.strptime
def stamps(p):
    out=[]
    for l in open(p, errors="ignore"):
        if " batch, " in l and l.startswith("["):
            try: out.append(datetime.datetime.strptime(l[1:20],"%Y-%m-%d %H:%M:%S").timestamp())
            except: pass
    return sorted(set(out))
for arm in ("long19_foyer","long19_default"):
    s=stamps(f"/tmp/an/srv/{arm}.log")
    span=s[-1]-s[0]
    gaps=[b-a for a,b in zip(s,s[1:])]
    g=sorted(gaps)
    idle=sum(g for g in gaps if g>5)
    print(f"=== {arm} ===")
    print(f"  有 batch 的秒数 {len(s)}  跨度 {span/60:.1f} 分  覆盖 {100*len(s)/span:.1f}%")
    print(f"  间隔: p50={g[len(g)//2]:.0f}s p90={g[9*len(g)//10]:.0f}s p99={g[99*len(g)//100]:.0f}s max={g[-1]:.0f}s")
    print(f"  >5 秒的空隙: {sum(1 for x in gaps if x>5)} 个, 合计 {idle/60:.1f} 分 ({100*idle/span:.1f}%)")
    print(f"  >60 秒的空隙: {sum(1 for x in gaps if x>60)} 个, 合计 {sum(x for x in gaps if x>60)/60:.1f} 分")
