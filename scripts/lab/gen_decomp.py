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
          "running", "step_back_ms", "step_perreq_ms"]

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
            span_min, busy_min, idle_min, idle_pct = decompose(rows_m)
            steps = read_steps(os.path.join(d, "steps.jsonl"))
            tokens = sum(s.get("output_len_actual") or 0 for s in steps)

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

            running = statistics.mean(v for _, v in rows_m if v is not None)
            # 方法一必须用【busy 时间】反推，不能用墙钟。
            # 论文的式子是 W_busy ≈ G/R̄ · τ，取反得 τ = W_busy·R̄/G。
            # 用墙钟会把这个 run 的空转也算进步时间：cap1 空转 36.3%，
            # 用墙钟得 28.5ms、用 busy 得 18.4ms，而逐请求测量是 20.6ms——
            # 前者偏离 +38%，后者偏离 -11%。用墙钟时 cap1 的排序也整个跑偏。
            step_back = (busy_min * 60 * running / tokens * 1000) if tokens else None
            rows.append({
                "run": r.replace("pois200_", ""),
                "wall_min": round(wall_min, 1),
                "span_min": round(span_min, 1),
                "idle_min": round(idle_min, 1),
                "busy_min": round(busy_min, 1),
                "idle_pct": round(idle_pct, 1),
                "running": round(running, 2),
                "step_back_ms": round(step_back, 1) if step_back else "",
                "step_perreq_ms": (round(step_perreq_ms(steps), 1)
                                   if step_perreq_ms(steps) else ""),
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
