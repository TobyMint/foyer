#!/usr/bin/env python3
"""分段弹性 —— 论文 §IV 的核心。全局拟合把一条强凸曲线拉直了。

为什么需要：论文原来只报一个全局 ε（0.38/0.61），读法「每加 10% 并发买 4~6%
吞吐」。但那条曲线是凸的：低并发处 ε 接近 0 甚至为负，高并发处 ε 超过 1
（加并发反而更慢）。

【已撤回的主张，2026-09-24】本文件产出的曲线是 **device-only（无 HiCache）** 配置上的。
曾经用它解释控制器为什么输（「九条臂都落在 ε>1 的贵段」）—— 那是错的：九条控制器臂
**全部开着 HiCache**。在它们自己的配置上 ε 全段 <1、没有悬崖（见 gen_elasticity_hc.py）。
正文已按此改写：判据现在只用来【排除工作负载侧的解释】，不用来解释控制器失败。

所以本文件回答的是「这个（配置, 负载）上加并发多贵」，不是「控制器输在哪」。

⚠ τ 必须用 busy 条件均值反推的 τ₁（decomp.csv 的 step_back_ms）。用全时段
均值会得到一份被撤回过的数（低一个 busy 占比）。

用法: python3 gen_elasticity.py <decomp.csv> <out.csv>
"""
import csv, math, os, sys

IDS = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]


def eps(t0, r0, t1, r1):
    """分段弹性 ε = dln(tau1)/dln(R̄) —— **唯一实现**，gen_elasticity_hc.py import 它。

    τ₁ 用 decomp.csv 的 `step_back_ms`（busy 条件均值反推），R̄ 用同表的 `running`
    （也是 busy 条件口径）—— 两个都别换成全时段均值，见 gen_elasticity.py 开头的说明。
    `gen_elasticity_hc.py` 原来自己写了一遍、注释声称「与 gen_elasticity.py 完全一致」；
    2026-09-25 对拍过确实一致，但按 CLAUDE.md 的规矩抽出来共用。
    """
    if min(r0, r1, t0, t1) <= 0 or r0 == r1:
        return None
    return math.log(t1 / t0) / math.log(r1 / r0)


def main():
    src, out = sys.argv[1], sys.argv[2]
    d = {r["run"]: r for r in csv.DictReader(l for l in open(src) if not l.startswith("#"))}
    pts = [(float(d[k]["running"]), float(d[k]["step_back_ms"]), k) for k in IDS]
    rows = []
    print("%-13s -> %-13s %8s %8s %8s" % ("from", "to", "R̄", "τ₁", "ε"))
    for (r0, t0, n0), (r1, t1, n1) in zip(pts, pts[1:]):
        e = eps(t0, r0, t1, r1)
        rows.append({"from": n0, "to": n1, "r0": round(r0, 2), "r1": round(r1, 2),
                     "tau0_ms": t0, "tau1_ms": t1, "epsilon": round(e, 2)})
        print("%-13s -> %-13s %8.2f %8.1f %+8.2f" % (n0, n1, r1, t1, e))
    # 控制器臂落在哪一段。⚠ decomp.csv 只有 5 条 foyer；另外 4 条要从
    # metrics.csv 现算，别拿 5 条冒充 9 条（第一版就是这么错的）。
    # 从 arm_running.csv 读，不再硬编码。原来那行注释说「见 occupancy.csv」，
    # 但 occupancy.csv 的 running_mean 是【全时段均值】(0.97~1.41)，不含 1.63+。
    # 这个错让 §IV 的「五条在 1.63 以上」与同稿的归因表当场互相否证。
    arm_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                           "paper", "data", "arm_running.csv")
    cr = []
    if os.path.exists(arm_csv):
        for r in csv.DictReader(l for l in open(arm_csv) if not l.startswith("#")):
            if r["family"] == "controller" and not r["run"].startswith("aimd"):
                cr.append(float(r["running_busy"]))
    assert cr, "读不到 arm_running.csv，先跑 gen_arm_running.py"
    # 正文 §IV 的「九条 Foyer 臂」—— 与打印段共用同一个列表，不另写一份
    NINE = ["foyer_hc", "foyer_hz1", "foyer_hz2", "foyer_hz0_r2", "foyer_bres_r2",
            "foyer_breshz1", "foyer_nogate", "foyer_rg4", "foyer_sf0_r2"]
    nb = [float(r["running_busy"]) for r in csv.DictReader(
        l for l in open(arm_csv) if not l.startswith("#")) if r["run"] in NINE]
    print()
    print("九条控制器的 Foyer 臂 R̄busy: %.2f ~ %.2f" % (min(cr), max(cr)))
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
        f.write("# 更正(2026-09-24)：本曲线仅描述【无 HiCache】配置。九条控制器臂全部开 HiCache，\n")
        f.write("# 在它们自己的配置上 epsilon 全段 <1、无悬崖（见 gen_elasticity_hc.py），\n")
        f.write("# 故本曲线不用于解释控制器失败。\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
        # 【两个集合都报，并写清各是哪个】。2026-09-25：正文引的「控制器运行区间
        # 1.35~1.69」是【九条 Foyer 臂】的区间，而 cr 是更宽的「controller 族、
        # 非 aimd」—— 它含 foyer_hz1_r2（一条重复臂，R̄ 2.10）。只印一个 max
        # 而不写集合，下一个人会以为正文区间写错了（或反过来照它去改正文）。
        f.write("# controller_arms_Rbar_min,%f\n" % min(cr))
        f.write("# controller_arms_Rbar_max,%f\n" % max(cr))
        f.write("# controller_arms_set,controller 族且非 aimd（%d 条，含重复臂 hz1_r2/hc_r2 与 pairA/pairB_foyerhc）\n" % len(cr))
        if nb:
            f.write("# nine_foyer_arms_Rbar_min,%f\n" % min(nb))
            f.write("# nine_foyer_arms_Rbar_max,%f\n" % max(nb))
            f.write("# nine_foyer_arms_set,正文 §IV 引的那九条（不含 aimd / pair*_foyerhc / foyfix / 重复臂）\n")
            f.write("# nine_foyer_arms_ge_1.53,%d\n" % sum(1 for x in nb if x >= 1.53))
    print("->", out)


if __name__ == "__main__":
    main()
