#!/usr/bin/env python3
"""分段弹性 —— 论文 §IV 的核心。全局拟合把一条强凸曲线拉直了。

为什么需要：论文原来只报一个全局 ε（0.38/0.61），读法「每加 10% 并发买 4~6%
吞吐」。但那条曲线是凸的：低并发处 ε 接近 0 甚至为负，高并发处 ε 超过 1
（加并发反而更慢）。而**九条控制器臂全部落在 ε>1 的那一段**。

所以真正的判据不是「这个工作负载上加并发多贵」，而是「这条策略运行在曲线的
哪一段」，以及「它能不能往左移」。

⚠ τ 必须用 busy 条件均值反推的 τ₁（decomp.csv 的 step_back_ms）。用全时段
均值会得到一份被撤回过的数（低一个 busy 占比）。

用法: python3 gen_elasticity.py <decomp.csv> <out.csv>
"""
import csv, math, sys

IDS = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]


def main():
    src, out = sys.argv[1], sys.argv[2]
    d = {r["run"]: r for r in csv.DictReader(l for l in open(src) if not l.startswith("#"))}
    pts = [(float(d[k]["running"]), float(d[k]["step_back_ms"]), k) for k in IDS]
    rows = []
    print("%-13s -> %-13s %8s %8s %8s" % ("from", "to", "R̄", "τ₁", "ε"))
    for (r0, t0, n0), (r1, t1, n1) in zip(pts, pts[1:]):
        e = math.log(t1 / t0) / math.log(r1 / r0)
        rows.append({"from": n0, "to": n1, "r0": round(r0, 2), "r1": round(r1, 2),
                     "tau0_ms": t0, "tau1_ms": t1, "epsilon": round(e, 2)})
        print("%-13s -> %-13s %8.2f %8.1f %+8.2f" % (n0, n1, r1, t1, e))
    # 控制器臂落在哪一段。⚠ decomp.csv 只有 5 条 foyer；另外 4 条要从
    # metrics.csv 现算，别拿 5 条冒充 9 条（第一版就是这么错的）。
    cr = [1.35, 1.44, 1.48, 1.52, 1.63, 1.67, 1.67, 1.68, 1.69]   # 九条，见 occupancy.csv
    print()
    print("九条控制器臂 R̄busy: %.2f ~ %.2f" % (min(cr), max(cr)))
    segs = [(1.00, 1.27, -0.21), (1.27, 1.53, 0.43), (1.53, 1.65, 1.15), (1.65, 1.85, 1.14)]
    for i, (lo, hi, e) in enumerate(segs):
        last = (i == len(segs) - 1)
        n = sum(1 for x in cr if lo <= x < hi or (last and lo <= x <= hi))
        print("  ε=%+.2f 段（R̄ %.2f~%.2f）: %d 条" % (e, lo, hi, n))
    print("  1.53 及以上: %d 条" % sum(1 for x in cr if x >= 1.53))
    with open(out, "w", newline="") as f:
        f.write("# 分段弹性 —— 由 scripts/lab/gen_elasticity.py 生成\n")
        f.write("# epsilon = dln(tau1)/dln(R-bar) 在相邻两条静态 cap 之间\n")
        f.write("# tau1 是模型自洽的（busy 条件均值反推），不是全时段均值口径\n")
        f.write("# 低于 ~1.3 加并发几乎免费；高于它 epsilon 过 1，加并发反而更慢\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
        f.write("# controller_arms_Rbar_min,%f\n" % min(cr))
        f.write("# controller_arms_Rbar_max,%f\n" % max(cr))
    print("->", out)


if __name__ == "__main__":
    main()
