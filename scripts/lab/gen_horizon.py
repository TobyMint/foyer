#!/usr/bin/env python3
"""horizon 扫描（growth reserve 的轮数）—— paper/data/horizon.csv。

**为什么要有这个脚本**：这张表原来**没有生成器**，是手维护的
（2026-09-25 codex 第 23 轮指出：`hz0`/`hz2` 被干净重跑替代后，
这张表和由它画的**图 6** 都还留着旧读数，于是图注里「两轮比三轮慢 15 分钟」
在新数据下是**反的** —— `hz2_r2` 271.0 比基线 291.3 快 20.3 分钟）。
汇总表手维护违反本项目第一条血的教训（「手算的表一定会错」）。

**数据源**：只用 `table1.csv`（它由 `gen_table.py` 生成，且已含重跑后的值）。
四个点＝同一 policy 下只改 `horizon=` 的那四个配置：

    horizon=0  → foyer_hz0_r2
    horizon=1  → foyer_hz1
    horizon=2  → foyer_hz2_r2
    horizon=3  → foyer_hc（基线，horizon=3 是默认）

⚠ 这三个非基线的 run 里，**两个是重跑后的**（hz0/hz2 原来被主机争用污染）。
用哪一条写在这里、不靠记忆：只认 `table1.csv` 现在那一行。

用法: python3 gen_horizon.py <table1.csv> <out.csv>
"""
import csv, os, sys

# (horizon 轮数, table1.csv 里的 run 名)
POINTS = [(0, "foyer_hz0_r2"), (1, "foyer_hz1"), (2, "foyer_hz2_r2"), (3, "foyer_hc")]
FIELDS = ["horizon", "run", "wall_min", "slo_pct", "conc"]


def main():
    t1_p, out_p = sys.argv[1], sys.argv[2]
    t1 = {r["run"]: r for r in csv.DictReader(l for l in open(t1_p) if not l.startswith("#"))}
    rows, missing = [], []
    for h, run in POINTS:
        r = t1.get(run)
        if r is None:
            missing.append("%d:%s" % (h, run))
            continue
        rows.append({"horizon": h, "run": run,
                     "wall_min": "%.1f" % float(r["wall_min"]),
                     "slo_pct": "%.1f" % float(r["slo_pct"]),
                     "conc": "%.2f" % float(r["conc"])})
    if missing:
        raise SystemExit("!! table1.csv 里缺这些 run：%s —— 别写半张表" % "、".join(missing))

    with open(out_p, "w", newline="") as f:
        f.write("# growth reserve 的 horizon 扫描 —— gen_horizon.py 生成，勿手改\n")
        f.write("# 四个点只改 horizon= 这一个参数；数据源是 table1.csv（已含重跑后的值）。\n")
        f.write("# ⚠ 这张表原来【没有生成器】、是手维护的，于是重跑落地后它和图 6 都留着旧读数，\n")
        f.write("#   图注里「两轮比三轮慢 15 分钟」在新数据下是反的（2026-09-25 codex 第 23 轮）。\n")
        f.write("# conc 列与表 I 同一口径（live 会话数，不是 sglang:num_running_reqs）。\n")
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("写入 %s：%d 行" % (out_p, len(rows)))
    base = [r for r in rows if r["horizon"] == 3][0]
    for r in rows:
        print("  horizon=%d  %-14s %6s 分钟  SLO %5s%%  并发 %s  （对基线 %+.1f 分，%+.1f pp）"
              % (r["horizon"], r["run"], r["wall_min"], r["slo_pct"], r["conc"],
                 float(r["wall_min"]) - float(base["wall_min"]),
                 float(r["slo_pct"]) - float(base["slo_pct"])))


if __name__ == "__main__":
    main()
