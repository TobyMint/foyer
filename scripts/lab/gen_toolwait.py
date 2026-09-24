#!/usr/bin/env python3
"""轮次间隔：trace 要求的 vs 实测的 —— paper/data/toolwait.csv。

为什么要有：论文摘要里那句「the wait averages 16.85 s, not the sub-second figure
the trace's median suggests」的数字【一度不在任何 CSV 里】（2026-09-24 审计发现）。
按本项目纪律，摘要级的数字必须有出处。

口径（必须写清，否则差一个分母就得到完全不同的均值 —— 我自己就先算错过一次）：
  轮次转换 = 【同会话相邻两轮】。等价于「每个会话除最后一轮之外的每一行」，
  因为某一轮的 tool_wait_after_ms 就是到下一轮的等待。**每个会话的最后一轮
  没有后继，必须排除**：不排除的话分母是 999（全部行）而均值只有 12.65 s，
  排除后分母是 799 而均值 15.82 s。这两个数差 25%，全在于分母。
  （trace 的 tool_wait_after_ms 又只有 662 个正值 —— 把零值也滤掉均值变成 19.10 s，
   那是第三种口径。三种都不是错的，但正文必须指明用的是哪一种。）

  要求值 = trace 的 tool_wait_after_ms（重放管线要等这么久）
  实测值 = run 的 steps.jsonl 里，上一轮 complete_timestamp 到下一轮
           submit_timestamp 的实际间隔（含等 permit 的门时间）

用法: python3 gen_toolwait.py <trace.csv> <results_dir> <out.csv> <run> [<run> ...]
"""
import csv, collections, datetime, json, os, statistics, sys


def pct(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(p * len(s)))]


def transitions(trace):
    """返回 [(session_id, round_idx, tool_wait_after_ms)]，只含同会话相邻轮。"""
    rows = list(csv.DictReader(open(trace)))
    mx = collections.defaultdict(int)
    for r in rows:
        mx[r["session_id"]] = max(mx[r["session_id"]], int(r["round_idx"]))
    out = [(r["session_id"], int(r["round_idx"]), float(r["tool_wait_after_ms"]))
           for r in rows if int(r["round_idx"]) < mx[r["session_id"]]]
    assert len(out) == len(rows) - len(mx), \
        "轮次转换数 %d != 行数 %d - 会话数 %d" % (len(out), len(rows), len(mx))
    return out, len(rows), len(mx)


def measured(steps_path):
    """实测间隔：同一会话里，上一轮 complete 到下一轮 submit。"""
    st = [json.loads(l) for l in open(steps_path) if l.strip()]
    by = collections.defaultdict(dict)
    for s in st:
        by[s["session_id"]][s["round_idx"]] = s
    out = []
    for sid, d in by.items():
        for k in sorted(d):
            if k + 1 in d:
                out.append((d[k + 1]["submit_timestamp"] - d[k]["complete_timestamp"]) * 1000.0)
    return out


def main():
    trace, root, out_p = sys.argv[1], sys.argv[2], sys.argv[3]
    runs = sys.argv[4:]
    tr, nrows, nsess = transitions(trace)
    dem = [w for _, _, w in tr]

    rows = []
    for r in runs:
        sp = os.path.join(root, r, "steps.jsonl")
        if not os.path.exists(sp):
            print("!! 缺 %s" % sp)
            continue
        me = measured(sp)
        assert len(me) == len(dem), \
            "%s: 实测转换数 %d != trace 的 %d —— 分母不一致，均值不可比" % (r, len(me), len(dem))
        rows.append({"run": r, "n_transitions": len(me),
                     "demand_med_s": "%.2f" % (statistics.median(dem) / 1000),
                     "demand_mean_s": "%.2f" % (statistics.mean(dem) / 1000),
                     "demand_p90_s": "%.2f" % (pct(dem, 0.9) / 1000),
                     "measured_med_s": "%.2f" % (statistics.median(me) / 1000),
                     "measured_mean_s": "%.2f" % (statistics.mean(me) / 1000),
                     "measured_p90_s": "%.2f" % (pct(me, 0.9) / 1000)})

    header = "\n".join([
        "# trace: %s（%d 行 - %d 会话 = %d 次转换）" % (os.path.basename(trace), nrows, nsess, len(dem)),
        "# 轮次间隔：trace 要求 vs 实测 —— 由 scripts/lab/gen_toolwait.py 生成，勿手改",
        "# 轮次转换 = 同会话相邻两轮 = 每会话除最后一轮外的每一行",
        "# ⚠ 分母不同，均值差很多，正文引用时必须指明口径：",
        "#     全部 999 行（含每会话最后一轮，无后继）  均值 12.65 s",
        "#     799 次轮次转换（本表）                  均值 15.82 s   <- 论文用的",
        "#     662 个非零 tool_wait                     均值 19.10 s",
        "# 论文摘要的 16.85 s 是【实测】列的均值（run 的 steps.jsonl 实测间隔，",
        "# 含等 permit 的门时间），15.82 s 是 trace 要求值。",
        "run,n_transitions,demand_med_s,demand_mean_s,demand_p90_s,measured_med_s,measured_mean_s,measured_p90_s"])
    fields = ["run", "n_transitions", "demand_med_s", "demand_mean_s", "demand_p90_s",
              "measured_med_s", "measured_mean_s", "measured_p90_s"]
    body = header + "\n" + "\n".join(",".join(str(r[k]) for k in fields) for r in rows) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as fh:
        fh.write(body)

    print("轮次转换 %d（%d 行 - %d 会话）" % (len(dem), nrows, nsess))
    print("要求值: 中位 %.2f s  均值 %.2f s  p90 %.2f s" % (
        statistics.median(dem) / 1000, statistics.mean(dem) / 1000, pct(dem, 0.9) / 1000))
    for r in rows:
        print("  %-24s 实测 中位 %5s  均值 %5s  p90 %5s" % (
            r["run"], r["measured_med_s"], r["measured_mean_s"], r["measured_p90_s"]))


if __name__ == "__main__":
    main()
