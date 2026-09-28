#!/usr/bin/env python3
"""两条新 run 落地后的**分诊**：机械判出「走哪个分支」，不靠现场回忆。

为什么要有：`foyer_scan_r2` / `foyer_sf0_r3` 的跑前预期各写了三种
（在 `lane_scan_r2.sh` / `lane_sf0_r3.sh` 头部、实验机上），
而**判据是 `frontier.classify`（带 ±1.0pp 打平带），不是「Δ 是正是负」**。
现场手判很容易漏掉带内/带外那一档，或者把「> +1.0」记成「>= +1.0」
（`classify` 的上界是 `delta > TIE_PP`，下界是 `delta >= -TIE_PP` —— 两侧不对称，
本项目在守卫里已经为此栽过一次）。

本脚本**不判断"该写什么"**，只把事实摆出来：
每条臂的 Δ、判词、与带的两侧距离、以及新重复组的 Δ 全距。
措辞仍然照 `lane_*.sh` 头部预写的三种预期办，**不许只报有利的那种**。

用法（在纸稿仓库根目录）:
    python3 scripts/lab/landing_triage.py

前置：`table1.csv` 与 `replicates.csv` 已经按落地清单重生成过。
本脚本**只读**，不改任何文件。
"""
import csv, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frontier as FR       # noqa: E402  TIE_PP 与 classify 的**唯一实现**

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
D = os.path.join(ROOT, "paper", "data")
# ⚠ **不许在这里写 `TIE = 1.0`。** 第一版就是那么写的，而检查器里有一条守卫
# （`check_paper_numbers.py` 的「±1.0pp 打平带的定义不在 frontier.py 且唯一」）
# **当场把它抓了出来** —— 那条守卫正是为「打平带被复制成第二份实现」设的，
# 而复制一份的下场是：某天有人只改了 `frontier.TIE_PP`，这里还按 1.0 判。
TIE = FR.TIE_PP
NEW = ["foyer_scan_r2", "foyer_sf0_r3"]
PAIRS = {"foyer_scan": "foyer_scan_r2", "foyer_sf0_r2": "foyer_sf0_r3"}


def _is_static(nm):
    """与 `check_paper_numbers.py` 里那条守卫逐字一致 —— 两处必须一起改。"""
    return nm.startswith("cap") or re.match(r"pair[AB]_cap", nm) is not None


_RP = {}


def _delta_of(name):
    """用 `runs_precise.csv` + `frontier.front_slo()` 算某 run 的 Δ。

    ⚠ **不许改回 `table1.csv` 的 `delta_pp`** —— 那是超集/子集关系，见下面 A7 的注释。
    """
    r = _RP.get("pois200_" + name)
    if not r:
        return None
    return float(r["slo_pct"]) - FR.front_slo(float(r["wall_min"]))


def load(p):
    with open(p, encoding="utf-8") as f:
        return [r for r in csv.DictReader(l for l in f if not l.startswith("#"))]


def classify(d):
    """**直接转调 `frontier.classify`** —— 不在这里重写一遍阈值分支。

    第一版自己写了一份（`if d > TIE: ABOVE elif d >= -TIE: TIE ...`），
    连「两侧不对称」这件事都要靠注释提醒自己 —— 那正是**两份实现**的老路。
    判词表也统一取 `FR.classify` 的原文（`ABOVE  (越过前沿)` 等），
    本脚本只负责把事实摆出来，不重新命名判词。
    """
    return FR.classify(d)


def main():
    t1p = os.path.join(D, "table1.csv")
    if not os.path.exists(t1p):
        raise SystemExit("!! 缺 %s —— 先按落地清单重生成" % t1p)
    t1 = {r["run"]: r for r in load(t1p)}
    global _RP
    _RP = {r["run"]: r for r in load(os.path.join(D, "runs_precise.csv"))}

    print("=" * 72)
    print("一、两条新 run 进来了吗")
    print("=" * 72)
    missing = []
    for n in NEW:
        if n not in t1:
            print("  ✗ %-16s **不在 table1.csv 里**" % n)
            missing.append(n)
            continue
        r = t1[n]
        d = float(r["delta_pp"])
        print("  ✓ %-16s Δ=%+7.4f  pp   判词 %-6s  墙钟 %s  SLO %s  %s"
              % (n, d, classify(d), r["wall_min"], r["slo_pct"],
                 # ⚠ `contested` 列在 CSV 里是 `"0"`/`"1"`，不是空 ⇒ 原来的
                 # `not in ("", None)` 对每一条都成立，**所有行都印 ‡**。
                 "‡争用" if str(r.get("contested") or "").strip() in ("1", "True",
                                                                      "CONTESTED") else ""))
    if missing:
        print("\n  ⇒ 还缺 %s：**不要开始改稿**，先确认 summary.json 在、"
              "并按落地清单把生成器名单加全。" % ", ".join(missing))
        return 1
    print("\n  frontier 的判决列（表里印的那个）：%s"
          % {n: t1[n]["verdict"] for n in NEW})

    print()
    print("=" * 72)
    print("二、scan 臂：越线复现了吗（**直接决定头条**）")
    print("=" * 72)
    s0, s1 = (float(t1["foyer_scan"]["delta_pp"]), float(t1[NEW[0]]["delta_pp"]))
    v0, v1 = classify(s0), classify(s1)
    print("  第一次 foyer_scan    Δ=%+.4f  → %s" % (s0, v0))
    print("  重复   foyer_scan_r2 Δ=%+.4f  → %s" % (s1, v1))
    print("  两次之差             %.4f pp" % abs(s1 - s0))
    print()
    # ⚠⚠ 2026-09-27：**这里原来写的是 `if v1 == "ABOVE"`，而 `v0/v1` 来自
    # `frontier.classify()`，它返回的是 `"ABOVE  (越过前沿)"` —— **等号永远不成立**，
    # 于是【恒落到最后一个 else】，把「两次读数都越线」报成「越线不复现」。
    # 这是「守卫自己算错、却看起来通过」那一族的又一次，而且**发生在我刚把
    # 那条教训写进 CLAUDE.md 之后**。
    # ⇒ 判据改成**前缀**比（`v1.startswith("ABOVE")`），并且下面的分支顺序也调了：
    #   先问「是否 ABOVE」，再问「两次差是否 >1pp」，最后才是 (b)。
    if v1.startswith("ABOVE"):
        print("  ⇒ 预期 (a) **越线复现**。")
        print("    头条按「有一条臂越过」改写，且要写成**两次读数都越过**；")
        print("    现在正文写的「one run, unresolved」必须升级 —— 摘要也要改（记得重新数词，上限 265）。")
    elif abs(s1 - s0) > TIE:
        print("  ⇒ 预期 (c) **两次相差 > 1.0pp**。")
        print("    这条臂不可分辨，照实说；并且「0.5 到 4.6pp 是最紧组全距」")
        print("    **必须按新数据重算**（本对的 Δ 全距 = %.4f）。" % abs(s1 - s0))
    else:
        print("  ⇒ 预期 (b) **越线不复现**。")
        print("    头条回到「九条无一越线」，但必须写明：")
        print("    「第十条臂的一次读数曾越过（+1.30），重复（%+.2f）反驳了它」。" % s1)
    print()
    print("  ⚠ 还要看 ready 时钟那一列（`arrival_slo.csv` 的 `delta_ready_pp`）——")
    print("    §VI 的「三条跨带」计数与 §V 的 −0.07pp 那句都跟着它走。")

    print()
    print("=" * 72)
    print("三、sf0 臂：第二近那条")
    print("=" * 72)
    f0, f1 = (float(t1["foyer_sf0_r2"]["delta_pp"]), float(t1[NEW[1]]["delta_pp"]))
    print("  第一次 foyer_sf0_r2  Δ=%+.4f  → %s" % (f0, classify(f0)))
    print("  重复   foyer_sf0_r3  Δ=%+.4f  → %s" % (f1, classify(f1)))
    print("  两次之差             %.4f pp" % abs(f1 - f0))
    if classify(f1).startswith("ABOVE"):   # ⚠ 同上：前缀比，不能用等号
        print("\n  ⇒ **有控制器越线，头条被推翻，照实改写，不许只报有利的那种。**")
    else:
        print("\n  ⇒ 仍在带内/线下方：§V「单飞关掉也扫队列、却落在线下 0.55pp」")
        print("    那句要带上两次读数（现在是单次读数 −0.55）。")

    print()
    print("=" * 72)
    print("四、控制器重复组的 Δ 全距（正文那句「0.5 to 4.6pp」的出处）")
    print("=" * 72)
    rp = os.path.join(D, "replicates.csv")
    rs = load(rp)
    rows = []
    for r in rs:
        names = (r.get("runs") or "").split()
        if len(names) < 2:
            continue
        # 静态锚点不算「控制器配置」。⚠ 判据与 `check_paper_numbers.py` 里那条
        # 守卫**逐字一致**（`_is_static`）—— 不能按名字前缀判：Foyer base 组里有
        # `pairA_foyerhc` / `pairB_foyerhc`，按前缀会把**整组**排除。
        if any(_is_static(n) for n in names):
            continue
        # ⚠⚠ 2026-09-27（中立复核 r49 第 A7 条）：**这里原来用 `table1.csv` 的
        # `delta_pp`，是错的基准。** `pairA_foyerhc`/`pairB_foyerhc` 根本不在
        # `table1.csv` 里 ⇒ base 组只剩两条 ⇒ 全距 **0.49**，比 hz2 的 0.51 还小
        # ⇒ 本脚本按升序打印时，**会让人得出「最紧的是 base」**（与正文相反）。
        # 正确基准：`runs_precise.csv` + `frontier.front_slo()`（同一实现），
        # 与检查器里那条守卫**同源**，也与正文一致。
        dv = [d for d in (_delta_of(n) for n in names) if d is not None]
        if len(dv) >= 2:
            rows.append((r["group"], max(dv) - min(dv)))
    for g, rg in sorted(rows, key=lambda x: x[1]):
        print("  %-34s 全距 %.2f pp" % (g[:34], rg))
    if rows:
        lo, hi = min(x[1] for x in rows), max(x[1] for x in rows)
        print()
        print("  组数 %d；区间 **%.1f to %.1f**（正文现写「0.5 to 4.6」；"
              "组数现写「three」）" % (len(rows), lo, hi))
        print("  → §V 与 §VI 各有一次这句话，**两处都要改**；"
              "§V 还有「the tightest of the N groups」。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
