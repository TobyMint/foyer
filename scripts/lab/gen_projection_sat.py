#!/usr/bin/env python3
"""控制器「以为池子满了」的直接度量：投影超过预算的采样占比。

为什么需要：论文 §V 现在只用「投影中位 89,073 对预算 96,360，即 7% 空闲」
来说明控制器高估占用。那是一个时点快照。真正决定它行不行的是
**投影是否【超过】预算** —— 一旦超过，判定式 projection + n <= budget
对任何候选者都不成立，控制器就一个都不放（除非 starve guard 强推）。

这个量在变负载 run 上被推到极端（见 docs/finding_hicache_elasticity_20260923.md），
但它在**现有的恒负载 run 上也能算**，且是零 GPU 成本的。

口径：projection = base + growth_sum（controller_budget3.py:326）。
      blocked = projection > budget。
      另报「有会话在等却一个都没放」的占比，这是用户可见的后果。
"""
import csv, glob, json, os, sys

def stats(path):
    n = blocked = wq_noadm = 0
    base_over = 0
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if "budget" not in d or "growth_sum" not in d:
            continue
        n += 1
        proj = (d.get("base") or 0) + (d.get("growth_sum") or 0)
        if proj > d["budget"]:
            blocked += 1
        if (d.get("waiting_n") or 0) > 0 and (d.get("n_admitted") or 0) == 0:
            wq_noadm += 1
        if (d.get("base") or 0) > d["budget"]:
            base_over += 1
    return n, blocked, wq_noadm, base_over

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    rows = []
    for p in sorted(glob.glob(os.path.join(root, "*", "controller.jsonl"))):
        run = os.path.basename(os.path.dirname(p))
        if run.startswith("_"):
            continue
        n, blocked, wq, bo = stats(p)
        if n < 50:
            continue
        rows.append((run, n, 100.0 * blocked / n, 100.0 * wq / n, 100.0 * bo / n))
    rows.sort(key=lambda r: -r[2])
    print("%-26s %7s %12s %14s %12s" % ("run", "采样", "投影超预算%", "有等待不放行%", "base超预算%"))
    for r in rows:
        print("%-26s %7d %12.1f %14.1f %12.1f" % r)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                       "paper", "data", "projection_sat.csv")
    with open(out, "w") as f:
        f.write("# 控制器投影饱和度 —— gen_projection_sat.py 生成\n")
        f.write("# projection = base + growth_sum；blocked = projection > budget\n")
        f.write("run,samples,proj_over_budget_pct,waiting_but_none_admitted_pct,base_over_budget_pct\n")
        for r in rows:
            f.write("%s,%d,%.1f,%.1f,%.1f\n" % r)
    print("-> %s" % out)

if __name__ == "__main__":
    main()
