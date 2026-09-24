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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_decomp as _GD  # noqa: E402  busy 占比的共用定义

# sf0_r2 与 hc_r2 必须在里面：归因表引用 sf0 的在跑数，而它原来不在本表里，
# gen_attribution 于是静默回退到 occupancy.csv 的【全时段均值】口径（1.26），
# 而其余 11 行都是 busy 条件口径（sf0 的 busy 值是 1.45）—— 口径混用（2026-09-24 审稿人抓）。
# 这就是 CLAUDE.md 纪律 3 的又一个实例：生成器的 run 列表不全会静默改变下游口径。
# pairA_foyerhc / pairB_foyerhc：匹配对实验的两条 Foyer 臂（同 trace、同 HiCache，
# 与 static 的 pairA/pairB_cap2hc 配对）。它们【不在表 I】但属于 host-tier 族，
# §model 的「host tier 兑现区间」要把它们算进去 —— 少一条就会让区间说错
# （2026-09-24 第 12 轮审稿人：foyfix_hc 的 72.8% 被排除在「84.2–92.4%」之外）。
ARMS = ["foyer_sf0_r2", "foyer_hc", "foyer_hc_r2", "foyer_hz1", "foyer_hz1_r2", "foyer_hz2_r2",
        "foyer_hz0_r2", "foyer_bres_r2", "foyer_breshz1", "foyer_nogate", "foyer_rg4",
        "foyfix_hc", "pairA_foyerhc", "pairB_foyerhc", "aimd2", "aimd2_paper"]
STATIC = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5",
          "pairA_cap2hc", "pairB_cap2hc", "cap3_hc", "cap4_hc", "cap3_hc_r2", "cap4_hc_r2"]


def one(path):
    rd = list(csv.DictReader(open(path)))
    rn = [float(x["sglang:num_running_reqs"]) for x in rd if x["sglang:num_running_reqs"]]
    if not rn:
        return None
    allm = statistics.mean(rn)
    # busy 占比走 gen_decomp.busy_fraction（相邻采样的实际间隔积分），
    # **不**再自己数非零采样 —— 同一个量两条管线必须共用定义（CLAUDE.md 纪律 2）。
    # 2026-09-25 codex 第 21 轮：计数法在这条表上给 cap1 1.000000、
    # gen_decomp 给 0.998027。改动后 arm_running.csv 的 R̄busy 会动第 3 位小数，
    # 正文印到 2 位，不受影响。
    busy_frac = _GD.busy_fraction(_GD.read_metrics(path))
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
            # 精度必须够：gen_slope 的斜率是 d(realized)/d(R̄)，R̄ 只给 3 位会让
            # 斜率在第 2 位就偏（2026-09-24 审稿人用原始 metrics 复算，
            # 三条斜率对不上：-66.77 vs -66.73、-157.1 vs -157.8、-127.6 vs -127.0）。
            rows.append({"run": r, "family": group, "running_all": round(a, 6),
                         "running_busy": round(b, 6), "busy_frac": round(f, 6)})
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
        # 论文 §IV/§VI 引用的「控制器运行区间 1.35~1.69」是【九条 Foyer 臂】的区间
        # （不含 AIMD、不含 pairA/pairB_foyerhc、不含 foyfix）。两个都报，
        # 免得看汇总的人以为正文的区间写错了。
        NINE = ["foyer_hc", "foyer_hz1", "foyer_hz2_r2", "foyer_hz0_r2", "foyer_bres_r2",
                "foyer_breshz1", "foyer_nogate", "foyer_rg4", "foyer_sf0_r2"]
        nb = [r["running_busy"] for r in rows if r["run"] in NINE]
        if nb:
            print("正文 §IV 的九条 Foyer 臂 R̄busy: %.2f ~ %.2f（%d 条）"
                  % (min(nb), max(nb), len(nb)))
        print("控制器臂 R̄busy: %.2f ~ %.2f（%d 条）" % (min(ctrl), max(ctrl), len(ctrl)))
        print("  >=1.53 的: %d 条" % sum(1 for x in ctrl if x >= 1.53))
    print("->", out)


if __name__ == "__main__":
    main()
