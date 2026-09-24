#!/usr/bin/env python3
"""九臂逐项归因表 —— codex 第四轮排的最高价值剩余工作。

论文现在有两个局部机制（分段弹性、没用满内存），但都没对九条臂逐一说清
「你的败绩由哪个机制解释、剩下多少是没解释的」。这张表把每个臂的
占用 / 忙时在跑数 / 步成本 / 忙闲分解 / 残差 摆在一起，并对照一个相邻的静态锚点。

判据：对每个控制器臂，找**墙钟最接近的静态 cap**，比它们的在跑数与步成本。
如果控制器在跑数更低 → 「没用满内存」类；如果在跑数相当但步成本更高 →
「步成本」类；两者都不显著 → 残差，只能报为观测。

用法: python3 gen_attribution.py <runs.csv> <occupancy.csv> <decomp.csv> <out.csv>
"""
import csv, os, sys

# 九条 Foyer 变体 + 两个 AIMD 设置。hz0 原来漏在这里，导致正文说「九条变体」
# 而表里只有八条 —— codex 抓到的。
# sf0_r2 必须在里面：它是全表最接近前沿的臂（Δ −0.57），论文反复引用它，
# 归因表却没有它，正文也没解释为什么不在（2026-09-24 审稿人指出）。
ARMS = ["foyer_sf0_r2", "foyer_hz1", "foyer_hc", "foyer_hz2", "foyer_hz0", "foyer_bres_r2",
        "foyer_breshz1", "foyer_nogate", "foyer_rg4", "foyfix_hc",
        "aimd2", "aimd2_paper"]
STATIC = ["cap4_hc", "cap4_hc_r2", "cap3_hc", "pairB_cap2hc", "cap1",
          "cap4", "cap3_fixed", "cap2", "cap5"]


def load(p):
    return {r[list(r)[0]]: r for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))}


def load_concurrency():
    import os as _os
    p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..",
                      "paper", "data", "concurrency.csv")
    if not _os.path.exists(p):
        return {}
    return {r["run"]: r["verdict"] for r in
            csv.DictReader(l for l in open(p) if not l.startswith("#"))}


CONC = load_concurrency()


def main():
    runs, occ, dec = load(sys.argv[1]), load(sys.argv[2]), load(sys.argv[3])
    # R̄ 一律用 busy 条件口径，与 §IV 的弹性一致 —— 原来这张表用的是
    # occupancy.csv 的全时段均值，导致同一符号在相隔两页的地方有两个值
    armr = {}
    ap = os.path.join(os.path.dirname(sys.argv[3]), "arm_running.csv")
    if os.path.exists(ap):
        armr = {r["run"]: r for r in csv.DictReader(l for l in open(ap) if not l.startswith("#"))}
    def rb(k):
        if k in armr: return float(armr[k]["running_busy"])
        return float(occ[k]["running_mean"]) if k in occ else None
    out = sys.argv[4]
    rows = []
    print("%-14s %7s %7s %8s %8s %9s %s" % (
        "arm", "Δpp", "占用%", "R̄busy", "τ₁ms", "最近静态", "类别"))
    for a in ARMS:
        if a not in runs:
            continue
        wall = float(runs[a]["wall_min"])
        # 墙钟最接近的静态臂
        near = min((s for s in STATIC if s in runs),
                   key=lambda s: abs(float(runs[s]["wall_min"]) - wall))
        o_a = float(occ[a]["occ_p50_pct"]) if a in occ else None
        o_n = float(occ[near]["occ_p50_pct"])
        r_a = rb(a)
        r_n = rb(near)
        t_a = float(dec[a]["step_back_ms"]) if a in dec else None
        t_n = float(dec[near]["step_back_ms"]) if near in dec else None

        # 分类。判据照抄正文：「在跑数明显低于对照」→ 内存没用满；
        # 「在跑数【相当】但步成本更高」→ 步成本。第二个条件必须带可比性约束 ——
        # 原实现只查 t_a > t_n*1.08，于是任何跑得更多的臂都会因为 τ 更高而被归成
        # 「步成本」，而那只是 τ 随 R̄ 的常规趋势，不是机制。2026-09-24 修：
        # foyfix_hc（R̄ 1.675）对着 cap2（R̄ 1.271）被误归，就是这条漏掉的。
        COMPARABLE = 0.08      # 在跑数相差 8% 以内才算"相当"
        if o_a is not None and r_a is not None and r_a < r_n * 0.92:
            cls = "内存没用满"
        elif (t_a and t_n and t_a > t_n * 1.08
              and r_a is not None and abs(r_a - r_n) <= COMPARABLE * r_n):
            cls = "步成本更高"
        elif t_a and t_n and t_a > t_n * 1.08:
            cls = "步成本更高（但对照的在跑数不可比）"
        else:
            cls = "残差（只能报观测）"
        # 争用标记：与表 I 的 ‡ 同源（都读 concurrency.csv），不再手写 ——
        # 手写过一次，把 rg4/foyfix 也标了，而审计里它们是 clean（2026-09-24 审稿人抓）。
        rows.append({"arm": a, "contested": CONC.get("pois200_" + a, "?"),
                     "wall_min": wall, "nearest_static": near,
                     "occ_pct": o_a, "running": r_a, "tau1_ms": t_a,
                     "static_occ_pct": o_n, "static_running": r_n,
                     "static_tau1_ms": t_n, "class": cls})
        print("%-14s %7s %7s %8s %8s %9s %s" % (
            a, (runs[a]["slo_pct"]), o_a, r_a, t_a, near, cls))
    with open(out, "w", newline="") as f:
        f.write("# 十二臂逐项归因 —— 由 scripts/lab/gen_attribution.py 生成\n")
        f.write("# 每个控制器臂对照墙钟最接近的静态臂\n")
        f.write("# class 的阈值与正文逐字对应：在跑数 < 对照的 92% -> 内存没用满；\n")
        f.write("#   τ₁ > 对照的 108% 且在跑数相差 <=8% -> 步成本更高；\n")
        f.write("#   τ₁ 超 108% 但在跑数不可比 -> 步成本更高（但对照的在跑数不可比）；其余 -> 残差。\n")
        f.write("# contested: 与表 I 的 ‡ 同源（concurrency.csv）；CONTESTED 的 tau 列不可用\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("->", out)


if __name__ == "__main__":
    main()
