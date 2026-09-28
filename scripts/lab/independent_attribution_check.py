#!/usr/bin/env python3
"""独立复算「逐臂归因」—— 【不 import 生成器】，按**正文写的那条规则**重新分类。

为什么要有：`paper/data/attribution.csv` 是论文 §V 那张 12 行的归因表的唯一来源，
而分类规则只在 `gen_attribution.py` 里实现了一份。如果那份实现的阈值写错
（例如 0.92 写成 0.90、或把「可比性」那一条又漏掉 —— 它**历史上漏过一次**，
让 foyfix_hc 被误归），正文与 CSV 会**一致地错**，检查器（读 CSV）看不出来。
这与 `independent_frontier_check.py` / `independent_elasticity_check.py` 是同一层：
**独立的是实现，不是输入。**

**规则照抄正文**（§V）：
  1. 对照 = 墙钟最接近的静态 cap；
  2. 在跑数 < 对照的 92\\% → 「内存没用满」；
  3. 在跑数相差 ≤ 8\\% **且** τ₁ > 对照的 108\\% → 「步成本更高」；
  4. τ₁ > 108\\% 但在跑数不可比 → 「步成本更高（但对照的在跑数不可比）」；
  5. 其余 → 残差。

⚠ **对照集合**：本脚本用 `table1.csv` 里**所有** static 族行（不抄生成器那份
11 条硬编码名单）。实测这会让 `foyfix_hc` 与 `aimd2_paper_r3` 两条臂的「最近静态」
变成 **`pairA_cap2hc`**（它**不在论文表 I 里**，`NOT_PRINTED`），而生成器给的是 `cap2`
—— 两者的墙钟只差 **0.2 分钟**（304.46 vs 304.25），是名副其实的平手。
**分类结果不受影响**（12 条逐条相同）。正文已把口径写成「the static cap **of
Table~\ref{tab:runs}** closest to it」，与生成器一致；本脚本仍然报出这个差异，
因为它说明**分类依赖对照集合**，是下一个人会踩的地方。

用法: python3 independent_attribution_check.py <paper/data> [table1.csv]
"""
import csv, os, sys

RULE_TXT = "在跑数 < 对照的 92% -> 内存没用满；τ₁ > 对照的 108% 且在跑数相差 <=8% -> 步成本更高"
NEAR_RATIO = 0.92
COMPARABLE = 0.08
TAU_RATIO = 1.08


def load(p):
    return {list(r.values())[0]: r for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))}


def rows_of(p):
    return list(csv.DictReader(l for l in open(p) if not l.startswith("#")))


def classify(r_a, r_n, t_a, t_n):
    """按正文的规则分类（独立实现，不看生成器的代码）。"""
    if r_a is not None and r_n is not None and r_a < r_n * NEAR_RATIO:
        return "内存没用满"
    if t_a is not None and t_n is not None and t_a > t_n * TAU_RATIO:
        if r_a is not None and r_n is not None and abs(r_a - r_n) <= COMPARABLE * r_n:
            return "步成本更高"
        return "步成本更高（但对照的在跑数不可比）"
    return "残差（只能报观测）"


def main():
    d = sys.argv[1]
    t1p = sys.argv[2] if len(sys.argv) > 2 else os.path.join(d, "table1.csv")
    runs = load(os.path.join(d, "runs.csv"))
    armr = load(os.path.join(d, "arm_running.csv"))
    dec = load(os.path.join(d, "decomp.csv"))
    ref = {r["arm"]: r for r in rows_of(os.path.join(d, "attribution.csv"))}
    t1 = rows_of(t1p)

    # 静态对照集合：**从 table1.csv 现取**（static 族的行），不抄生成器的名单
    statics = [r["run"] for r in t1 if r["run"].startswith(("cap", "pair"))]
    if not statics:
        raise SystemExit("!! table1.csv 里没有静态行，先跑 gen_table.py")

    bad = 0
    diff_near, diff_cls = [], []
    print("%-16s %9s %9s %8s %8s  %-14s %-14s %s"
          % ("arm", "R̄", "R̄_对照", "τ₁", "τ₁_对照", "最近静态(本)", "最近静态(表)", "class"))
    for a in sorted(ref, key=lambda k: -float(ref[k]["wall_min"] or 0)):
        if a not in runs or a not in dec:
            print("  !! %s 在 runs.csv/decomp.csv 里找不到" % a)
            bad += 1
            continue
        wall = float(runs[a]["wall_min"])
        near = min((s for s in statics if s in runs),
                   key=lambda s: abs(float(runs[s]["wall_min"]) - wall))
        ra = float(armr[a]["running_busy"])
        rn = float(armr[near]["running_busy"])
        ta = float(dec[a]["step_back_ms"])
        tn = float(dec[near]["step_back_ms"])
        cls = classify(ra, rn, ta, tn)
        r_near = ref[a]["nearest_static"]
        r_cls = ref[a]["class"]
        if near != r_near:
            diff_near.append((a, near, r_near))
        if cls != r_cls:
            diff_cls.append((a, cls, r_cls))
        print("%-16s %9.3f %9.3f %8.1f %8.1f  %-14s %-14s %s%s"
              % (a, ra, rn, ta, tn, near, r_near, cls,
                 "" if (near == r_near and cls == r_cls) else "   <<< 不一致"))

    print()
    if diff_near:
        print("⚠ 「最近静态」取法不同（%d 条）—— 分类可能因此不同：" % len(diff_near))
        for a, mine, theirs in diff_near:
            print("   %-16s 本脚本 %s，attribution.csv %s" % (a, mine, theirs))
    if diff_cls:
        print("!! 分类不符（%d 条）：" % len(diff_cls))
        for a, mine, theirs in diff_cls:
            print("   %-16s 本脚本 %s，attribution.csv %s" % (a, mine, theirs))
        bad += len(diff_cls)
    if not diff_cls:
        # ⚠ 2026-09-27：`12` 是**写死**的 —— `foyer_scan` 进来之后是 13 条，
        # 而这句话会让人以为表里只有 12 条（与「守卫自己的名单写死」同族）。
        print("结论：%d 条臂的分类与 attribution.csv 逐条相符（对照取法差异见上，若有）"
              % len(ref))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
