#!/usr/bin/env python3
"""空转段的合并统计（全部 vs 排除受争用影响的 run）—— paper/data/idle_pooled.csv。

为什么要有：论文 §III 引用「1849 段，中位 5.6 s，均值 20.6 s，idle 时间中 69.6%
在 >20 s 的段里」。但那 1849 段里含四条被同机争用影响的 run（争用抬高 τ，
busy 变长、idle 变短，所以段时长【可能】被影响）。本脚本回答：排除它们之后
这些数会变吗？

答案是不会（中位 5.60→5.00 s，均值 20.65→21.02 s，>20 s 占比 69.6%→70.6%）。
这是因为段时长由【工具等待】决定，是工作负载属性，不是步成本的函数 ——
所以这个检查反过来支持了论文「空转是结构性的」这一主张。

用法: python3 gen_idle_pooled.py paper/data/idle_seg_raw.csv paper/data/concurrency.csv <out.csv>
"""
import csv, statistics, sys

BAD = None


def load(p):
    return [r for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))]


def main():
    raw_p, conc_p, out_p = sys.argv[1:4]
    bad = {r["run"].replace("pois200_", "") for r in load(conc_p)
           if r["verdict"] == "CONTESTED"}
    rows = load(raw_p)
    assert len(rows) > 1000, "原始段只有 %d 条，路径或格式不对" % len(rows)

    # 四个变体都出：合并在位/均值对【并哪些 run】的敏感性本身就是要报的东西。
    # 实测：中位被 cap1 一条主导（它占 22% 的段，自身中位 5.0 s），去掉它中位
    # 从 5.60 跳到 10.00；而均值（18.3~21.0）与 >20s 占比（64.8~70.6%）稳定。
    damaged = {"foyer_hz2", "foyer_hz0", "foyer_bres"}   # 实测被争用损害的三条
    out = []
    for name, excl in (("all_runs", set()),
                       ("minus_cap1", {"cap1"}),
                       ("minus_damaged3", damaged),
                       ("minus_contested4", bad & {r["run"] for r in rows})):
        sel = [r for r in rows if r["run"] not in excl]
        v = [float(r["duration_s"]) for r in sel]
        tot = sum(v)
        out.append({
            "set": name, "n_segments": len(v), "n_runs": len({r["run"] for r in sel}),
            "median_s": "%.2f" % statistics.median(v),
            "mean_s": "%.2f" % statistics.mean(v),
            "p90_s": "%.2f" % sorted(v)[int(0.9 * len(v))],
            "max_s": "%.1f" % max(v),
            "pct_idle_time_in_gt20s": "%.1f" % (100 * sum(x for x in v if x > 20) / tot),
            "pct_segments_gt20s": "%.1f" % (100 * sum(1 for x in v if x > 20) / len(v)),
        })

    header = "\n".join([
        "# 空转段的合并统计 —— 由 scripts/lab/gen_idle_pooled.py 生成，勿手改",
        "# clean_only = 排除 concurrency.csv 里判 CONTESTED 的 run（它们的 τ 被同机争用抬高）",
        "# 四个变体：中位与 p90 被 cap1 主导（它占 22% 的段），均值与 >20s 占比稳定。",
        "# 论文引用的「中位 5.6 s」必须写成区间；「均值 ~20 s」与「>20s 占 idle 时间 ~2/3」稳健。",
        "set,n_segments,n_runs,median_s,mean_s,p90_s,max_s,pct_idle_time_in_gt20s,pct_segments_gt20s"])
    fields = ["set", "n_segments", "n_runs", "median_s", "mean_s", "p90_s", "max_s",
              "pct_idle_time_in_gt20s", "pct_segments_gt20s"]
    body = header + "\n" + "\n".join(",".join(str(r[k]) for k in fields) for r in out) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as fh:
        fh.write(body)
    print("写入 %s" % out_p)
    for r in out:
        print("  %-11s n=%4d(%2d run) 中位 %5s 均值 %5s  p90 %6s  >20s 占 idle 时间 %5s%%"
              % (r["set"], r["n_segments"], r["n_runs"], r["median_s"], r["mean_s"],
                 r["p90_s"], r["pct_idle_time_in_gt20s"]))


if __name__ == "__main__":
    main()
