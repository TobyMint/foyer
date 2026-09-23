#!/usr/bin/env python3
"""池占用对比 —— 论文 §V-A 那张「控制器没用满内存」的表。

为什么需要：论文原来的解释是「加并发抬高步时间、抵消掉收益」。但那个抵消只有
32%，解释不了九条变体全败。真正的近因在控制器自己的日志里：它以为用了 92%，
实际只用 49%，同时 66 个会话在排队。

⚠ 坑：metrics.csv 的 `sglang:token_usage` 是**比例不是 token 数**，
`full_token_usage` 恒为 0，真正的 token 数在 `sglang:num_used_tokens`。
第一版把比例当 token 数除以池子，算出全是 0。

用法: python3 gen_occupancy.py <results_dir> <out.csv> [run ...]
"""
import csv, os, statistics, sys

RUNS = ["cap1","cap2","cap3_fixed","cap4","cap5","pairB_cap2hc","cap3_hc","cap4_hc",
        "cap4_hc_r2","foyer_hc","foyer_hz1","foyer_hz2","foyer_hz0","foyer_bres",
        "foyer_breshz1","foyer_nogate","foyer_rg4","foyfix_hc","aimd2","aimd2_paper"]


def main():
    root, out = sys.argv[1], sys.argv[2]
    runs = sys.argv[3:] or RUNS
    rows = []
    print("%-14s %9s %9s %9s %9s" % ("run", "占用中位%", "占用均值%", "队列均值", "在跑均值"))
    for r in runs:
        p = os.path.join(root, "pois200_" + r, "metrics.csv")
        if not os.path.exists(p):
            continue
        rd = list(csv.DictReader(open(p)))
        def col(name):
            return [float(x[name]) for x in rd if x.get(name) not in (None, "")]
        u = col("sglang:token_usage")           # 比例，不是 token 数
        if not u:
            continue
        q, n = col("sglang:num_queue_reqs"), col("sglang:num_running_reqs")
        rows.append({
            "run": r,
            "occ_p50_pct": round(statistics.median(u) * 100, 1),
            "occ_mean_pct": round(statistics.mean(u) * 100, 1),
            "queue_mean": round(statistics.mean(q), 2) if q else "",
            "running_mean": round(statistics.mean(n), 2) if n else "",
        })
        print("%-14s %9.1f %9.1f %9.2f %9.2f" % (
            r, rows[-1]["occ_p50_pct"], rows[-1]["occ_mean_pct"],
            rows[-1]["queue_mean"], rows[-1]["running_mean"]))
    with open(out, "w", newline="") as f:
        f.write("# 池占用与排队 —— 由 scripts/lab/gen_occupancy.py 生成\n")
        f.write("# occ = sglang:token_usage 的中位/均值（这是【比例】，不是 token 数）\n")
        f.write("# 论文 §V-A 的论点：控制器只用到 49% 的池子，而最快的静态 cap 用 70%\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("->", out)


if __name__ == "__main__":
    main()
