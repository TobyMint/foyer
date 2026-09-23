#!/usr/bin/env python3
"""九条控制器臂的 **busy 条件** 在跑数均值 —— 论文 §IV 与归因表必须用同一个口径。

为什么需要：§IV 原来写「九条臂跑在 1.35~1.69」，而那个列表是**硬编码**在
gen_elasticity.py 里、注释还指错了文件（说「见 occupancy.csv」，但
occupancy.csv 的 running_mean 是全时段均值，范围 0.97~1.41，根本不含 1.63+）。
同一篇稿子两页之后的归因表又用了全时段均值当 R̄ 列。同一个符号两个口径。

busy 条件均值 = 全时段均值 / busy 占比，与 gen_decomp.py 里 τ₁ 的分母一致。

用法: python3 gen_arm_running.py <results_dir> <out.csv>
"""
import csv, os, statistics, sys

ARMS = ["foyer_hc", "foyer_hz1", "foyer_hz2", "foyer_hz0", "foyer_bres",
        "foyer_breshz1", "foyer_nogate", "foyer_rg4", "foyfix_hc",
        "aimd2", "aimd2_paper"]
STATIC = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5",
          "pairB_cap2hc", "cap3_hc", "cap4_hc", "cap4_hc_r2"]


def one(path):
    rd = list(csv.DictReader(open(path)))
    rn = [float(x["sglang:num_running_reqs"]) for x in rd if x["sglang:num_running_reqs"]]
    if not rn:
        return None
    allm = statistics.mean(rn)
    busy_frac = sum(1 for v in rn if v > 0) / len(rn)
    return allm, (allm / busy_frac if busy_frac else 0.0), busy_frac


def main():
    root, out = sys.argv[1], sys.argv[2]
    rows = []
    print("%-16s %8s %9s %8s" % ("run", "R̄全时", "R̄busy", "busy占比"))
    for group, names in (("controller", ARMS), ("static", STATIC)):
        for r in names:
            p = os.path.join(root, "pois200_" + r, "metrics.csv")
            if not os.path.exists(p):
                continue
            res = one(p)
            if not res:
                continue
            a, b, f = res
            rows.append({"run": r, "family": group, "running_all": round(a, 3),
                         "running_busy": round(b, 3), "busy_frac": round(f, 3)})
            print("%-16s %8.2f %9.2f %8.3f" % (r, a, b, f))
    with open(out, "w", newline="") as f:
        f.write("# 在跑数的两个口径 —— 由 scripts/lab/gen_arm_running.py 生成\n")
        f.write("# running_all: metrics.csv 的 sglang:num_running_reqs 全时段均值\n")
        f.write("# running_busy: running_all / busy占比 —— 论文 §III 与 §IV 一律用这个\n")
        f.write("# 论文里引用 R̄ 时必须指明是哪一个；两个口径差 1.3~1.7 倍\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    ctrl = [r["running_busy"] for r in rows if r["family"] == "controller"]
    if ctrl:
        print()
        print("控制器臂 R̄busy: %.2f ~ %.2f（%d 条）" % (min(ctrl), max(ctrl), len(ctrl)))
        print("  >=1.53 的: %d 条" % sum(1 for x in ctrl if x >= 1.53))
    print("->", out)


if __name__ == "__main__":
    main()
