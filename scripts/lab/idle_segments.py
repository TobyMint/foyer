#!/usr/bin/env python3
"""导出引擎空转段的长度分布 —— 论文 C3「空转是结构性的」的直接证据。

空转段的定义：metrics.csv 里 sglang:num_running_reqs 连续为 0 的采样区间。
论文的主张是这些段【很长】（与 tool wait 同量级），所以不是采样噪声、
也不是控制器抖动造成的瞬时状态。

用法: python3 idle_segments.py <results_dir> <out.csv> [run ...]
"""
import csv, os, statistics, sys

SAMPLE_S = 5.0
RUNS = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5", "pairB_cap2hc", "cap3_hc",
        "cap4_hc", "foyer_hc", "foyer_hz1", "foyer_hz2", "foyer_hz0", "foyer_bres"]


def segments(path):
    hdr = open(path).readline().strip().split(",")
    i_ts = hdr.index("ts"); i_rn = hdr.index("sglang:num_running_reqs")
    rows = []
    for line in open(path).readlines()[1:]:
        c = line.rstrip("\n").split(",")
        if len(c) <= max(i_ts, i_rn):
            continue
        try:
            ts = float(c[i_ts])
        except ValueError:
            continue
        try:
            rn = float(c[i_rn])
        except ValueError:
            continue
        rows.append((ts, rn))
    segs, start, prev = [], None, None
    for t, rn in rows:
        if rn == 0:
            if start is None:
                start = prev if prev is not None else t
        else:
            if start is not None:
                segs.append(t - start)
                start = None
        prev = t
    if start is not None:
        segs.append(rows[-1][0] - start)
    # 采样周期是 5s，单点空转记成 0 秒没有意义；合并相邻采样点时已经按真实
    # 时间戳差计算，所以这里只丢掉 < 1s 的（首尾截断产生的）
    return [s for s in segs if s >= 1.0]


def main():
    root, out = sys.argv[1], sys.argv[2]
    runs = sys.argv[3:] or RUNS
    pooled = open(out.replace(".csv", "_raw.csv"), "w", newline="")
    raw = csv.writer(pooled)
    raw.writerow(["run", "duration_s"])
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "n_segments", "median_s", "p90_s", "max_s", "total_idle_min"])
        for r in runs:
            p = os.path.join(root, "pois200_" + r, "metrics.csv")
            if not os.path.exists(p):
                continue
            s = segments(p)
            if not s:
                continue
            s.sort()
            w.writerow([r, len(s), round(statistics.median(s), 1),
                        round(s[int(0.9 * (len(s) - 1))], 1), round(s[-1], 1),
                        round(sum(s) / 60, 1)])
            for d in s:
                raw.writerow([r, round(d, 1)])
            print("%-13s n=%4d 中位 %6.1fs  p90 %6.1fs  最长 %6.1fs" %
                  (r, len(s), statistics.median(s), s[int(0.9 * (len(s) - 1))], s[-1]))
    pooled.close()
    print("->", out, "和", out.replace(".csv", "_raw.csv"))


if __name__ == "__main__":
    main()
