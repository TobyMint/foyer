#!/usr/bin/env python3
"""落地第二批：把 `foyer_scan_r3` / `foyer_hc_slru` 加进**所有** run 名单。

与 `apply_landing_edits.py`（上一批 `scan_r2`/`sf0_r3`）同一个模式，理由也一样：
「生成器的 run 名单漏一个就静默改口径」是本项目栽过三次的错，手改十几处就是十几次机会。

## 两条 run 的**种类不同**，所以加的处所也不同

- `foyer_scan_r3` —— **同配置重复**（`scan` / `scan_r2` 的第三次读数）。
  探针是 `foyer_scan_r2`：**它出现过的每一处就是这条也要加的地方**。
- `foyer_hc_slru` —— **不是重复**，是驱逐政策对照（同配置、只多
  `--radix-eviction-policy slru`）。探针法对它**不直接适用**；
  它要加在「按机械判据枚举 host-tier 族 / 全部 200 档 run」的地方：
  判据（主 trace + HiCache + >=995 步）**本来就会把它收进集合**
  （`gen_eviction.py` 的 `_derive()` 在它落地后直接报
  「列表里有而判据不认 ['foyer_hc_slru', 'foyer_scan_r3']」）。

## 不加的地方，以及为什么

- `gen_attribution.py` 的 `ARMS`：本表一向「**一个配置一个代表**」，
  `scan_r3` 是 `scan` 的重复，加进去会把同一条臂数两遍（该文件注释里
  对 `foyer_hz2_r3` 写过同一条理由）。
- `gen_replicates.py` 的 `GROUPS`：`scan_r3` 加进「scans the queue」组；
  `foyer_hc_slru` **不新开组**（它没有重复，本表只收 >=2 条的组）。
- `frontier.py` 的 `FRONT`：那是包络锚点集合，重复与对照都不是锚点。
- `independent_frontier_check.py` 的 `ARMS`：覆盖「论文判过的臂」，
  `scan_r3` 加（`scan` 在），`foyer_hc_slru` 不加（论文不报它的 Δ）。

用法（落地、且 rsync 回本地之后）:
    python3 scripts/lab/apply_landing_edits_r3.py            # 干跑
    python3 scripts/lab/apply_landing_edits_r3.py --apply    # 真改
"""
import os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
APPLY = "--apply" in sys.argv

# (文件, 锚点, 替换, 说明) —— 锚点都取名单的**最后一行/一整行**，不依赖行号
EDITS = [
    ("scripts/lab/gen_runs.py",
     'foyer_scan_r2 200 foyer\nfoyer_sf0_r3 200 foyer"""',
     'foyer_scan_r2 200 foyer\nfoyer_scan_r3 200 foyer\nfoyer_sf0_r3 200 foyer"""',
     "ROWS（表 I 的行来源）—— 只加 scan_r3"),

    ("scripts/lab/gen_table.py",
     '    "foyer_scan_r2": "scans the queue (2nd run)",\n',
     '    "foyer_scan_r2": "scans the queue (2nd run)",\n'
     '    "foyer_scan_r3": "scans the queue (3rd run)",\n',
     "LABEL（表 I 的行标签）—— 只加 scan_r3"),

    ("scripts/lab/gen_arm_running.py",
     '"foyer_hz2_r3", "foyer_scan", "foyer_scan_r2", "foyer_sf0_r3",',
     '"foyer_hz2_r3", "foyer_scan", "foyer_scan_r2", "foyer_scan_r3",\n'
     '        "foyer_hc_slru", "foyer_sf0_r3",',
     "ARMS（在跑数/墙钟表；**不进 NINE**）"),

    ("scripts/lab/gen_occupancy.py",
     '"foyfix_hc","aimd2","aimd2_paper_r3","foyer_sf0_r2","foyer_scan_r2","foyer_sf0_r3"]',
     '"foyfix_hc","aimd2","aimd2_paper_r3","foyer_sf0_r2","foyer_scan_r2",\n'
     '        "foyer_scan_r3","foyer_hc_slru","foyer_sf0_r3"]',
     "RUNS（占用表）"),

    ("scripts/lab/slo_sensitivity.py",
     '"foyer_nogate","foyer_rg4","foyer_scan","foyer_scan_r2","foyer_sf0_r3","foyfix_hc",',
     '"foyer_nogate","foyer_rg4","foyer_scan","foyer_scan_r2","foyer_scan_r3",\n'
     '        "foyer_hc_slru","foyer_sf0_r3","foyfix_hc",',
     "RUNS（阈值表 5s/10s/20s）"),

    ("scripts/lab/gen_arrival_slo.py",
     '"foyer_nogate","foyer_rg4","foyer_scan","foyer_sf0_r2","foyer_scan_r2","foyer_sf0_r3",',
     '"foyer_nogate","foyer_rg4","foyer_scan","foyer_sf0_r2","foyer_scan_r2",\n'
     '        "foyer_scan_r3","foyer_hc_slru","foyer_sf0_r3",',
     "RUNS（ready 时钟）"),

    ("scripts/lab/gen_eviction.py",
     '        "foyer_scan_r2", "foyer_sf0_r3",\n',
     '        "foyer_scan_r2", "foyer_scan_r3", "foyer_hc_slru", "foyer_sf0_r3",\n',
     "RUNS（host-tier 集合 —— ⚠ 集合从 28 变 **30**，正文要跟着改）"),

    ("scripts/lab/gen_stall.py",
     '"pois200_foyer_scan", "pois200_foyer_scan_r2",\n'
     '        "pois200_foyer_sf0_r3", "pois200_foyfix_hc"]',
     '"pois200_foyer_scan", "pois200_foyer_scan_r2", "pois200_foyer_scan_r3",\n'
     '        "pois200_foyer_hc_slru", "pois200_foyer_sf0_r3", "pois200_foyfix_hc"]',
     "RUNS（停摆/控制周期表）"),

    ("scripts/lab/gen_replicates.py",
     '    "scans the queue": ["foyer_scan", "foyer_scan_r2"],',
     '    "scans the queue": ["foyer_scan", "foyer_scan_r2", "foyer_scan_r3"],',
     "GROUPS（重复散布 —— scan 组从 2 条变 3 条）"),

    ("scripts/lab/independent_frontier_check.py",
     '        "foyer_scan_r2", "foyer_sf0_r3"]',
     '        "foyer_scan_r2", "foyer_scan_r3", "foyer_sf0_r3"]',
     "ARMS（独立复算的覆盖面）"),
]


def main():
    ok = skip = fail = 0
    for rel, old, new, tag in EDITS:
        p = os.path.join(ROOT, rel)
        name = os.path.basename(rel)
        try:
            s = open(p, encoding="utf-8").read()
        except Exception as e:
            print("✗ %-28s %-40s 读不到：%r" % (name, tag, e)); fail += 1; continue
        if "foyer_scan_r3" in s:
            print("· %-28s %-40s 已含 scan_r3，跳过" % (name, tag)); skip += 1; continue
        n = s.count(old)
        if n != 1:
            print("✗ %-28s %-40s 锚出现 %d 次（应为 1）—— **没有改动**" % (name, tag, n))
            fail += 1
            continue
        if not APPLY:
            print("→ %-28s %-40s 待改（干跑）" % (name, tag)); ok += 1; continue
        assert isinstance(new, str)
        open(p, "w", encoding="utf-8").write(s.replace(old, new))
        print("✓ %-28s %-40s 已改" % (name, tag)); ok += 1
    print("\n共 %d 处：%s %d，跳过 %d，失败 %d"
          % (len(EDITS), "已改" if APPLY else "待改", ok, skip, fail))
    if fail:
        print("⚠ 有失败项 —— **不要往下走**，先把锚点看清楚")
    if not APPLY and not fail:
        print("（这是干跑；加 --apply 才真改）")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
