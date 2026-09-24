#!/usr/bin/env python3
"""准入队列长度（等待中的会话数）—— paper/data/backlog.csv。

为什么要有：§VII 说「200 档的等待会话数是同代 25 档的四倍（中位 66 对 16，
最大 135 对 25）」，而这三个数此前**不在任何 CSV 里** —— 只能从
`controller.jsonl` 的 `waiting_n` 现场算。违反本项目「论文里每个数字都要能追到
CSV / 代码 / 日志」那条（2026-09-25 自查发现）。

为什么这张表是 §VII 的关键：控制器「不赢」的一种辩解是「负载太轻、没有可调的空间」。
等待队列长度是这个辩解的直接读数 —— 而它在 200 档是 66、在 25 档是 16，
即【队列是被节流本身制造出来的】，不是需求松紧的证据。§VII 的论证就靠这个。

口径：读 `controller.jsonl` 每一行的 `waiting_n`（控制器每个 2 s 周期记一次）。
中位与最大值取全部周期。**不做任何筛选** —— 筛选会改变这个数，而它正是论点本身。

用法: python3 gen_backlog.py <results_dir> <out.csv> [run ...]
"""
import csv, json, os, statistics, sys

# 论文引用的三条 + 它们的前代对照。前代那几条是为了让 §VII 的
# 「更早一代的 25 档读 9--11」也能追。
# 只列【有 controller.jsonl】的 run —— 静态 cap 不记准入队列，列进来只会刷屏
# 「缺」，把真正的缺失淹掉（2026-09-25 第一次跑就是这样）。
RUNS = ["pois200_foyer_hc", "pois200_foyer_hz1", "pois200_foyer_hz2",
        "pois200_foyer_hz0", "pois200_foyer_bres_r2", "pois200_foyer_breshz1",
        "pois200_foyer_nogate", "pois200_foyer_rg4", "pois200_foyer_sf0_r2",
        "pois200_foyer_push_25",          # §VII 的同代 25 档控制器臂
        "load25c_budget3"]                # 更早一代的 25 档，正文引作 9--11 那条


def waiting(d):
    p = os.path.join(d, "controller.jsonl")
    v = []
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            x = json.loads(line)
        except ValueError:
            continue
        if "waiting_n" in x:
            v.append(x["waiting_n"])
    return v


def main():
    root, out = sys.argv[1], sys.argv[2]
    runs = sys.argv[3:] or RUNS
    rows, missing = [], []
    for r in runs:
        # 25 档那批目录带 `pois200_` 前缀，主 trace 那批不带 —— 两种都试。
        # （2026-09-25 第一次跑时只试了不带前缀的，于是把 25 档整批报成「缺」，
        #   而那正是 §VII 要引的那三条。run 目录命名不统一是这个项目的老毛病，
        #   凡按名字找目录的脚本都要两种都试。）
        d = None
        for cand in (os.path.join(root, r), os.path.join(root, "pois200_" + r)):
            if os.path.exists(os.path.join(cand, "controller.jsonl")):
                d = cand
                break
        if d is None:
            missing.append(r)
            continue
        v = waiting(d)
        if not v:
            missing.append(r + "（日志里没有 waiting_n）")
            continue
        v_sorted = sorted(v)
        rows.append(dict(
            run=os.path.basename(d), samples=len(v),
            waiting_p50=statistics.median(v),
            waiting_p90=v_sorted[int(0.9 * (len(v_sorted) - 1))],
            waiting_max=max(v),
            # 非零周期的占比：队列为空说明那一刻没有积压，是另一回事
            pct_nonzero="%.1f" % (100.0 * sum(1 for x in v if x > 0) / len(v))))
    with open(out, "w", newline="") as f:
        f.write("# 准入队列长度（每个 2 s 控制周期记一次的 waiting_n）—— gen_backlog.py 生成，勿手改\n")
        f.write("# 用途：§VII 的「200 档等待会话中位 66 / 最大 135，同代 25 档中位 16 / 最大 25」，\n")
        f.write("#   以及「更早一代的 25 档读 9--11」。取舍：中位、p90、最大一起报（中位会骗人）。\n")
        f.write("# 口径：全部控制周期，不做筛选 —— 它是「队列由节流制造」这个论点的读数本身。\n")
        w = csv.DictWriter(f, fieldnames=["run", "samples", "waiting_p50", "waiting_p90",
                                          "waiting_max", "pct_nonzero"])
        w.writeheader()
        w.writerows(rows)
    print("写入 %s：%d 行" % (out, len(rows)))
    for r in rows:
        print("  %-20s 采样 %-6s 中位 %-5s p90 %-5s 最大 %-5s（非零 %s%%）" % (
            r["run"], r["samples"], r["waiting_p50"], r["waiting_p90"],
            r["waiting_max"], r["pct_nonzero"]))
    if missing:
        print("!! 没写进去（本地镜像没有，或日志里没这个字段）：")
        for m in missing:
            print("   " + m)


if __name__ == "__main__":
    main()
