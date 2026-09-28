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

# sf0_r2 是全表最接近前沿的臂（Δ −0.57），论文反复引用它；它原来既不在
# 这张表、也不在 decomp.csv，导致「九臂归因」那一节没有它（2026-09-24 审稿人指出）
RUNS = ["cap1","cap2","cap3_fixed","cap3_pd","cap4","cap5","pairB_cap2hc","cap3_hc","cap3_ph","cap4_hc","cap5_hc","cap6_hc","cap8_hc",
        "cap4_hc_r2","cap3_hc_r2","foyer_hc","foyer_hc_r2","foyer_hz1","foyer_hz1_r3","foyer_hz2_r2","foyer_hz2_r3",
        "foyer_hz0_r2","foyer_bres_r2","foyer_breshz1_r2","foyer_nogate","foyer_rg4","foyer_scan",
        "foyfix_hc","aimd2","aimd2_paper_r3","foyer_sf0_r2","foyer_scan_r2",
        "foyer_scan_r3","foyer_hc_slru","foyer_sf0_r3"]


def main():
    root, out = sys.argv[1], sys.argv[2]
    runs = sys.argv[3:] or RUNS
    rows = []
    print("%-14s %9s %9s %9s %9s" % ("run", "占用中位%", "占用均值%", "队列均值", "在跑均值"))
    for r in runs:
        p = os.path.join(root, "pois200_" + r, "metrics.csv")
        # 缺 run 必须【报错】而不是跳过：本表被 §V-A 的「二十条臂」口径引用，
        # 少两行会让正文的计数与数据文件对不上（2026-09-24 就是这样：
        # RUNS 列了 23 条，CSV 只有 21 行 —— cap4_hc_r2 与 cap3_hc_r2 是在
        # 这张表生成之后才跑完的，于是它们无声地不在表里）。
        # 见 CLAUDE.md 纪律 3：生成器的 run 列表不全会静默改变下游口径。
        if not os.path.exists(p):
            raise SystemExit("!! %s 缺 metrics.csv（目录 %s）—— 缺 run 不静默跳过" % (r, p))
        rd = list(csv.DictReader(open(p)))
        def col(name):
            return [float(x[name]) for x in rd if x.get(name) not in (None, "")]
        u = col("sglang:token_usage")           # 比例，不是 token 数
        if not u:
            raise SystemExit("!! %s 的 metrics.csv 里没有 token_usage" % r)
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
