#!/usr/bin/env python3
"""逐请求 decode 间隔 τ₂ 的【分时段】读数 —— paper/data/tau2_windows.csv。

为什么要有：论文 §repro 用两个【半小时尺度】的对照说明争用与 τ₂ 同起同落：

  - `cap1` 前十二个半小时桶恒在 20.3~20.9 ms，之后三个桶是 21.3 / 27.1 / 21.1
    （另外两条 run 起来之后）；
  - `foyer_t85` 从 29.8 ms 降到 22.3~22.6 ms（邻居离开之后四个桶），`foyer_rl99` 从 32.4 到 25.2 / 25.1。

这些数此前只存在于 `docs/finding_concurrency_contamination_20260924.md` 的手抄时间序列里，
不在任何 `paper/data/*.csv` —— 违反本项目「论文里每个数字都要能追到 CSV / 代码 / 日志」
（2026-09-25 codex 第 15 轮指出的追溯缺口）。本脚本把同一批数按桶重算并落盘。

⚠ **桶宽是半小时，不是分钟。** 半小时是「还分辨得出转折、且每个引用的桶里至少二十步」
的最宽窗口；更细的序列噪声更大，**不支持分钟级主张，论文也没做**（§repro 原话）。
本文件的自述原来写成「同一分钟内跳变把争用钉死」，比论文的主张强，2026-09-25 改掉。

τ₂ 的定义与 `gen_concurrency.py` 的 `tau2()` 逐字一致：逐请求
`(total_duration_ms − first_token_ms) / (output_len_actual − 1)`，取中位，
只用 `output_len_actual ≥ 32` 的步。分桶按【完成时刻】的绝对墙钟（epoch 秒）。

用法: python3 gen_tau2_windows.py <results_dir> <out.csv> [<桶宽分钟>=30]
"""
import csv, json, os, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_decomp as _GD  # noqa: E402  τ₂ 判据的共用定义

BUCKET_MIN = 30.0
RUNS = ["cap1", "foyer_t85", "foyer_rl99"]


def steps(d):
    return [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]


def tau2_rows(st):
    """逐条的 (间隔 ms, 完成时刻)。**判据走 gen_decomp.perreq_one —— 共用定义，不另写一份。**

    2026-09-25：本函数原来自己判「output_len >= 32 且时间戳非空」，而
    `gen_concurrency.tau2()` 多一条 `status == "SUCCESS"` —— 偏偏本文件的自述
    还写着「与 gen_concurrency.py 的 tau2() 逐字一致」。全库实测只有 `default`
    一条 run 受影响（τ₂ 差 0.022 ms），但那是运气不是设计。
    """
    out = []
    for s in st:
        v = _GD.perreq_one(s)
        if v is None:
            continue
        out.append((v, s.get("complete_timestamp")))
    return out


def main():
    root, out_p = sys.argv[1], sys.argv[2]
    bucket_s = float(sys.argv[3]) * 60.0 if len(sys.argv) > 3 else BUCKET_MIN * 60.0
    rows = []
    for run in RUNS:
        d = os.path.join(root, run) if os.path.isdir(os.path.join(root, run)) \
            else os.path.join(root, "pois200_" + run)
        if not os.path.isdir(d):
            raise SystemExit("!! 缺目录 %s —— 这张表的三个 run 是论文点名的对照，"
                             "少一条就写不出结论" % d)
        st = steps(d)
        tr = [(v, t) for v, t in tau2_rows(st) if t]
        if not tr:
            raise SystemExit("!! %s 没有可比的时间戳" % run)
        t0 = min(t for _, t in tr)
        buckets = {}
        for v, t in tr:
            k = int((t - t0) // bucket_s)
            buckets.setdefault(k, []).append(v)
        for k in sorted(buckets):
            v = sorted(buckets[k])
            rows.append(dict(
                run=run,
                bucket_start_s="%.0f" % (t0 + k * bucket_s),
                bucket_min="%d" % (k * bucket_s / 60.0),
                n=len(v),
                tau2_p50_ms="%.1f" % statistics.median(v),
                tau2_min_ms="%.1f" % v[0],
                tau2_max_ms="%.1f" % v[-1]))

    with open(out_p, "w", newline="") as f:
        f.write("# 逐请求 decode 间隔 τ₂ 的分时段读数 —— gen_tau2_windows.py 生成，勿手改\n")
        f.write("# τ₂ 定义与 gen_concurrency.py 的 tau2() 逐字一致（逐请求、中位、output_len>=32）\n")
        f.write("# 分桶按完成时刻的绝对墙钟；bucket_start_s 是 epoch 秒，bucket_min 是相对该 run 首个可比步的分钟\n")
        # ⚠ 这里是【半小时】尺度，不是分钟 —— 原来自述写成「同一分钟内跳变把争用钉死」，
        # 比论文主张强；论文 §repro 明写更细的序列「不支持分钟级主张，我们也不做」。
        # 2026-09-25 中立子 agent 指出生成器自述与论文相反。
        f.write("# 用途：§repro 的两个【半小时尺度】对照（cap1 的 20.3~20.9 -> 21.3/27.1/21.1，\n")
        f.write("#   t85 的 29.8 -> 22.3~22.6、rl99 的 32.4 -> 25.2）。此前只在 docs/ 的手抄序列里。\n")
        f.write("# ⚠ 桶宽半小时，不支持分钟级主张（论文 §repro 明写不做）。\n")
        w = csv.DictWriter(f, fieldnames=["run", "bucket_start_s", "bucket_min", "n",
                                          "tau2_p50_ms", "tau2_min_ms", "tau2_max_ms"])
        w.writeheader()
        w.writerows(rows)
    print("写入 %s：%d 行（桶宽 %.0f 分钟）" % (out_p, len(rows), bucket_s / 60.0))
    for r in rows:
        print("  %-12s 第 %3s 分  n=%-4s τ₂ 中位 %6s（%s ~ %s）" % (
            r["run"], r["bucket_min"], r["n"], r["tau2_p50_ms"],
            r["tau2_min_ms"], r["tau2_max_ms"]))


if __name__ == "__main__":
    main()
