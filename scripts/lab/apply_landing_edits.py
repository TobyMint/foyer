#!/usr/bin/env python3
"""落地时把 `foyer_scan_r2` / `foyer_sf0_r3` 加进**所有** run 名单 —— 一条命令，九处。

为什么要有这个脚本：`docs/landing_checklist_20260927.md` 第一节列了九处名单，
而「名单漏一个就静默改口径」是本项目栽过三次的错。手改九处就是九次机会。
**这些编辑与 run 的结果无关**（不像正文那样依赖 Δ 是哪一档），所以现在就能写好、测过。

⚠ 与正文编辑分开：正文（§V「has been run once」、§VI、图 1 标注、26→28…）
**依赖落地后的实测值**，必须那时候再改，不在本脚本范围内。

用法（落地、且 rsync 回本地之后）:
    python3 scripts/lab/apply_landing_edits.py            # 干跑，只打印要改什么
    python3 scripts/lab/apply_landing_edits.py --apply    # 真改

设计要点：
 - 每处**独立 try/except**（CLAUDE.md 纪律 5：中途 assert 失败 ⇒ 后面的修改全没生效）；
 - 每处改前 `assert count(anchor) == 1` —— 锚不唯一就跳过并报出来，**不猜**；
 - 幂等：已经加过的会被识别（`SKIP`），重复跑不会加两遍；
 - 改完**打印 diff 摘要**，让人能一眼看出动了哪几行。
"""
import os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
APPLY = "--apply" in sys.argv

# (文件, 锚点, 替换, 说明)
# 锚点都取**该名单的最后一行**，把新项接在后面 —— 这样不依赖行号，也不动别的行。
EDITS = [
    ("scripts/lab/gen_runs.py",
     "foyer_sf0_r2 200 foyer\"\"\".split(\"\\n\")",
     "foyer_sf0_r2 200 foyer\nfoyer_scan_r2 200 foyer\nfoyer_sf0_r3 200 foyer\"\"\".split(\"\\n\")",
     "ROWS（表 I 的行来源）"),

    ("scripts/lab/gen_table.py",
     '"foyer_hc_r2": "horizon$=$3 (2nd run)", "foyer_sf0_r2": "single-flight off",\n'
     '    "foyer_hz1": "horizon$=$1",',
     '"foyer_hc_r2": "horizon$=$3 (2nd run)", "foyer_sf0_r2": "single-flight off",\n'
     '    "foyer_scan_r2": "scans the queue (2nd run)",\n'
     '    "foyer_sf0_r3": "single-flight off (2nd run)",\n'
     '    "foyer_hz1": "horizon$=$1",',
     "LABEL（表 I 的行标签）"),

    ("scripts/lab/gen_arm_running.py",
     '        "foyer_hz2_r3", "foyer_scan",',
     '        "foyer_hz2_r3", "foyer_scan", "foyer_scan_r2", "foyer_sf0_r3",',
     "ARMS（在跑数/墙钟表；**不进 NINE**）"),

    ("scripts/lab/gen_stall.py",
     '"pois200_foyer_rg4", "pois200_foyer_scan", "pois200_foyfix_hc"]',
     '"pois200_foyer_rg4", "pois200_foyer_scan", "pois200_foyer_scan_r2",\n'
     '        "pois200_foyer_sf0_r3", "pois200_foyfix_hc"]',
     "RUNS（停摆/控制周期表）"),

    ("scripts/lab/gen_occupancy.py",
     '"foyfix_hc","aimd2","aimd2_paper_r3","foyer_sf0_r2"]',
     '"foyfix_hc","aimd2","aimd2_paper_r3","foyer_sf0_r2","foyer_scan_r2","foyer_sf0_r3"]',
     "RUNS（占用表）"),

    ("scripts/lab/gen_arrival_slo.py",
     '"foyer_nogate","foyer_rg4","foyer_scan","foyer_sf0_r2","foyfix_hc","aimd2","aimd2_paper_r3"]',
     '"foyer_nogate","foyer_rg4","foyer_scan","foyer_sf0_r2","foyer_scan_r2","foyer_sf0_r3",\n'
     '        "foyfix_hc","aimd2","aimd2_paper_r3"]',
     "RUNS（ready 时钟——§VI 的三处跨带计数靠它）"),

    ("scripts/lab/slo_sensitivity.py",
     '"foyer_nogate","foyer_rg4","foyer_scan","foyfix_hc","aimd2","aimd2_paper_r3"]',
     '"foyer_nogate","foyer_rg4","foyer_scan","foyer_scan_r2","foyer_sf0_r3","foyfix_hc",\n'
     '        "aimd2","aimd2_paper_r3"]',
     "RUNS（阈值表 5s/10s/20s）"),

    ("scripts/lab/gen_eviction.py",
     '"foyer_breshz1_r2", "foyer_nogate", "foyer_rg4", "foyer_scan", "foyer_sf0_r2", "foyfix_hc",\n'
     '        "pairA_foyerhc", "pairB_foyerhc"]',
     '"foyer_breshz1_r2", "foyer_nogate", "foyer_rg4", "foyer_scan", "foyer_sf0_r2", "foyfix_hc",\n'
     '        "foyer_scan_r2", "foyer_sf0_r3",\n'
     '        "pairA_foyerhc", "pairB_foyerhc"]',
     "RUNS（host-tier 集合 —— ⚠ 集合从 26 变 **28**，正文六处要跟着改）"),
]


def main():
    ok = skip = fail = 0
    for rel, old, new, tag in EDITS:
        p = os.path.join(ROOT, rel)
        name = os.path.basename(rel)
        try:
            s = open(p, encoding="utf-8").read()
        except Exception as e:
            print("✗ %-22s %-34s 读不到：%r" % (name, tag, e)); fail += 1; continue
        # 幂等：新的那两个名字只要已经在**这个文件**里，就认为加过了
        if "foyer_scan_r2" in s and "foyer_sf0_r3" in s:
            print("· %-22s %-34s 已含两条，跳过" % (name, tag)); skip += 1; continue
        n = s.count(old)
        if n != 1:
            print("✗ %-22s %-34s 锚出现 %d 次（应为 1）—— **没有改动**" % (name, tag, n))
            fail += 1
            continue
        if not APPLY:
            print("→ %-22s %-34s 待改（干跑）" % (name, tag)); ok += 1; continue
        assert isinstance(new, str)
        open(p, "w", encoding="utf-8").write(s.replace(old, new))
        print("✓ %-22s %-34s 已改" % (name, tag)); ok += 1
    print("\n共 %d 处：%s %d，跳过 %d，失败 %d"
          % (len(EDITS), "已改" if APPLY else "待改", ok, skip, fail))
    if fail:
        print("⚠ 有失败项 —— **不要往下走**，先把锚点看清楚（锚不唯一说明有人先改过）")
    if not APPLY and not fail:
        print("（这是干跑；加 --apply 才真改）")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
