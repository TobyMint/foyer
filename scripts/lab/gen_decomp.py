#!/usr/bin/env python3
"""从原始日志重新生成 paper/data/decomp.csv —— 论文 C1/C2/C3 的唯一数据来源。

为什么要有这个脚本：这张表原来是在终端里手算然后粘进 CSV 的，结果
`pairB_cap2hc` 那一行的 busy/idle 被写成了另一条 run 的值（总长 220.9 分），
而 wall 填的是正确的 295.0 —— 两个数自相矛盾，图 2 因此画出一根短得离谱的
柱子，标签飘在右边 80 分钟处。手算的表没有残差检查，所以这种错误不会被发现。

本脚本对每条 run 做三件事，并且**强制**检查：
  1. busy + idle 必须精确等于采样跨度 span（残差 != 0 直接报错退出）
  2. span 与 run_summary 的 wall 之差必须落在 [0, 12] 分钟（采样边界造成的固定偏移）
  3. 任何一步失败就把该 run 标成 INVALID，不写入 CSV

用法:  python3 gen_decomp.py <results_dir> <out.csv> [run ...]
"""
import csv, json, os, statistics, sys, glob

HEADER = ["run", "wall_min", "span_min", "idle_min", "busy_min", "idle_pct",
          "running", "running_all", "step_back_ms", "step_perreq_ms",
          # τ₁/τ₂ 的超出比例 —— §III 引用「τ₁ 比 τ₂ 高 7.9~39.8%」这个区间。
          # 它是两个导出量之比，此前不落盘（审计报成"找不到源头"）。
          "excess_pct"]

# 采样周期。metrics.csv 每 5 秒一行。
SAMPLE_S = 5.0
# 采样跨度允许比 run_summary 的墙钟长多少（秒）。采样器比第一个请求早启动、
# 比最后一个请求晚停下，这个偏移在全部 run 上是恒定的 ~6 分钟。
SPAN_SLACK_S = (0.0, 12 * 60)


def read_metrics(path):
    """返回 [(ts, num_running_reqs_or_None)]。"""
    rows = []
    with open(path) as f:
        hdr = f.readline().strip().split(",")
        if "sglang:num_running_reqs" not in hdr:
            raise RuntimeError("%s 没有 sglang:num_running_reqs 列" % path)
        i_ts = hdr.index("ts")
        i_rn = hdr.index("sglang:num_running_reqs")
        for line in f:
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
                rn = None
            rows.append((ts, rn))
    if len(rows) < 10:
        raise RuntimeError("%s 只有 %d 个采样点" % (path, len(rows)))
    return rows


def decompose(rows):
    """把相邻样本之间的间隔按【前一个】样本的状态归类。

    这是论文 C1 的定义。返回分钟数；残差必须为 0。
    """
    span = rows[-1][0] - rows[0][0]
    busy = idle = other = 0.0
    for (t0, r0), (t1, _) in zip(rows, rows[1:]):
        dt = t1 - t0
        if dt <= 0 or dt > SAMPLE_S * 3:      # 采样断档：既不算 busy 也不算 idle
            other += dt
            continue
        if r0 is None:
            other += dt
        elif r0 == 0:
            idle += dt
        else:
            busy += dt
    resid = span - busy - idle - other
    assert abs(resid) < 1e-6, "分解残差 %.6f s != 0" % resid
    assert other == 0.0, "有 %.1f s 采样断档，该 run 的分解不可信" % other
    return span / 60, busy / 60, idle / 60, 100 * idle / span


def read_steps(path):
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def step_perreq_ms(steps):
    """方法二：逐请求 decode 间隔的中位。只取 output_len >= 32 的步。"""
    vals = []
    for s in steps:
        n = s.get("output_len_actual") or 0
        tot = s.get("total_duration_ms")
        ft = s.get("first_token_ms")
        if n >= 32 and tot is not None and ft is not None and n > 1:
            vals.append((tot - ft) / (n - 1))
    return statistics.median(vals) if vals else None


def busy_stats(rows_m, tokens):
    """busy 时间、条件在跑均值与 τ₁ 的【唯一实现】。

    下游（`gen_superseded.py` 等）必须 import 这个，**不许各写一份** —— CLAUDE.md 纪律 2。
    2026-09-25 的教训：`gen_superseded.py` 曾自己写一份，把每个零样本固定算成 5 秒，
    于是同一条旧 bres 在那边给 34.2ms、在这边给 34.1ms（codex 第 21 轮抓出），
    而脚本的注释还写着「与 gen_decomp.py 同一套口径 —— 不另写一份实现」。
    返回 (span_min, busy_min, idle_min, idle_pct, running_all, running, step_back)。
    """
    span_min, busy_min, idle_min, idle_pct = decompose(rows_m)
    running_all = statistics.mean(v for _, v in rows_m if v is not None)
    # τ 的分母必须是【busy 期间的条件均值】，不是全时段均值。
    #
    # 式子 W_busy ≈ G/R̄ · τ 里，R̄ 是「每一步在跑几个请求」；而全时段
    # 采样均值把空转的那些 0 也算进去了，等于 R̄_busy × busy 占比。
    # 拿它乘 busy 时间，得到的 τ 会系统性地【低】一个 busy 占比：
    # cap1 空转 36.3%，于是 18.5ms 而不是真实的 ~28.9ms。
    # 这个错误曾经让「两个测量相差 12% 以内」这句话成立 —— 其实是
    # 两个错误互相抵消。
    busy_frac = busy_min / span_min if span_min else 1.0
    running = running_all / busy_frac if busy_frac > 0 else running_all
    step_back = (busy_min * 60 * running / tokens * 1000) if tokens else None
    return span_min, busy_min, idle_min, idle_pct, running_all, running, step_back


def main():
    root = sys.argv[1]
    out_path = sys.argv[2]
    runs = sys.argv[3:]
    if not runs:
        runs = sorted(os.path.basename(os.path.dirname(p))
                      for p in glob.glob(os.path.join(root, "*", "metrics.csv")))

    rows, bad = [], []
    for r in runs:
        d = os.path.join(root, r)
        try:
            rows_m = read_metrics(os.path.join(d, "metrics.csv"))
            steps = read_steps(os.path.join(d, "steps.jsonl"))
            tokens = sum(s.get("output_len_actual") or 0 for s in steps)

            # 必须在这里算：下面的采样跨度校验要用 span_min。
            # 2026-09-25 重构时把它挪到了校验之后，于是 27 个 run 全部因 span_min
            # 未绑定落进 bad，decomp.csv 被写成 0 行（跑了两遍才发现）。
            span_min, busy_min, idle_min, idle_pct, running_all, running, step_back = \
                busy_stats(rows_m, tokens)

            # 墙钟的口径必须和 run_summary.py 逐字一致，否则图 2 的柱子长度
            # 和图 1 的横坐标就是两个数。见 run_summary.py:91：
            #   墙钟 = 最后一个完成 − 最早一个提交
            # 不能用 st[0]：steps.jsonl 是按完成时间排的。
            subs = [s["submit_timestamp"] for s in steps if s.get("submit_timestamp")]
            comps = [s["complete_timestamp"] for s in steps if s.get("complete_timestamp")]
            if not subs or not comps:
                bad.append((r, "steps.jsonl 缺 submit/complete 时间戳"))
                continue
            wall_min = (max(comps) - min(subs)) / 60.0

            if not (SPAN_SLACK_S[0] <= (span_min - wall_min) * 60 <= SPAN_SLACK_S[1]):
                bad.append((r, "采样跨度 %.1f 分与墙钟 %.1f 分差 %.1f 分，超出容许的 0-12 分"
                            % (span_min, wall_min, span_min - wall_min)))
                continue
            rows.append({
                "run": r.replace("pois200_", ""),
                "wall_min": round(wall_min, 1),
                "span_min": round(span_min, 1),
                "idle_min": round(idle_min, 1),
                "busy_min": round(busy_min, 1),
                "idle_pct": round(idle_pct, 1),
                "running": round(running, 2), "running_all": round(running_all, 2),
                "step_back_ms": round(step_back, 1) if step_back else "",
                "step_perreq_ms": (round(step_perreq_ms(steps), 1)
                                   if step_perreq_ms(steps) else ""),
                # τ₁/τ₂ 超出比例。两个量都非空才算，否则留空。
                "excess_pct": (round(100 * (step_back / step_perreq_ms(steps) - 1), 1)
                               if (step_back and step_perreq_ms(steps)) else ""),
            })
        except Exception as e:
            bad.append((r, str(e)))

    if bad:
        print("!! 以下 run 未通过校验，未写入 CSV：")
        for r, why in bad:
            print("   %-24s %s" % (r, why))

    with open(out_path, "w", newline="") as f:
        f.write("# 墙钟的两段分解 + 步时间 —— 由 scripts/lab/gen_decomp.py 生成，勿手改\n")
        f.write("# busy/idle: 相邻采样按前一时刻 sglang:num_running_reqs 是否为 0 归类；busy+idle==span（有断言）\n")
        f.write("# span_min: metrics.csv 的采样跨度；wall_min: run_summary 的墙钟。两者差 ~6 分，是采样边界\n")
        f.write("# step_back: busy分钟 x 在跑均值 / 产出token（导出量；用 busy 不用墙钟，见下）; step_perreq: 逐请求 decode 间隔中位（独立测量）\n")
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
    print("写入 %s：%d 行" % (out_path, len(rows)))


if __name__ == "__main__":
    main()
