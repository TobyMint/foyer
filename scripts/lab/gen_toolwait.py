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


def ratios(steps_path):
    """逐转换的 实测/要求 比值。配对必须按【同一会话的相邻轮次】做 ——
    不能把实测列表与 trace 的要求列表直接 zip：两个列表的顺序不同
    （实测按会话/轮次枚举，要求按 trace 行序），zip 出来的比值是错配的，
    中位会从 1.001 掉到 0.35（2026-09-24 本脚本第一版就犯了这个错，
    而且不报错、看起来还挺合理）。要求值取本轮 steps 里的 tool_wait_after_ms，
    它与 trace 的要求逐位相同（trace 的同一字段）。
    """
    st = [json.loads(l) for l in open(steps_path) if l.strip()]
    by = collections.defaultdict(dict)
    for s in st:
        by[s["session_id"]][s["round_idx"]] = s
    out = []
    for sid, d in by.items():
        for k in sorted(d):
            if k + 1 in d:
                dem = (d[k].get("tool_wait_after_ms") or 0) / 1000.0
                if dem > 0:
                    out.append((d[k + 1]["submit_timestamp"] - d[k]["complete_timestamp"]) / dem)
    return out


def main():
    """用法: gen_toolwait.py <root> <out.csv> <trace.csv>:<run> [<trace.csv>:<run> ...]

    2026-09-24 改：原来只接一条 trace，于是 §VI 引用的第二条 trace 的
    20.2 s / 39.9 s 不在文件里，而正文却写「toolwait.csv carries both traces」
    —— 那是一句关于文件内容的假陈述。现在每条 run 自带 trace。
    """
    root, out_p = sys.argv[1], sys.argv[2]
    specs = []
    for a in sys.argv[3:]:
        tr_p, _, run = a.rpartition(":")
        if not tr_p or not run:
            raise SystemExit("!! 参数要写成 <trace.csv>:<run>，收到 %r" % a)
        specs.append((tr_p, run))
    cache = {}
    rows = []
    for tr_p, r in specs:
        if tr_p not in cache:
            tr, nrows, nsess = transitions(tr_p)
            cache[tr_p] = ([w for _, _, w in tr], nrows, nsess)
        dem, nrows, nsess = cache[tr_p]
        tr_b = os.path.basename(tr_p)
        sp = os.path.join(root, r, "steps.jsonl")
        if not os.path.exists(sp):
            print("!! 缺 %s" % sp)
            continue
        me = measured(sp)
        rr = ratios(sp)
        assert len(me) == len(dem), \
            "%s: 实测转换数 %d != trace 的 %d —— 分母不一致，均值不可比" % (r, len(me), len(dem))
        rows.append({"run": r, "trace": tr_b, "n_transitions": len(me),
                     "demand_med_s": "%.2f" % (statistics.median(dem) / 1000),
                     "demand_mean_s": "%.2f" % (statistics.mean(dem) / 1000),
                     "demand_p90_s": "%.2f" % (pct(dem, 0.9) / 1000),
                     "measured_med_s": "%.2f" % (statistics.median(me) / 1000),
                     "measured_mean_s": "%.2f" % (statistics.mean(me) / 1000),
                     "measured_p90_s": "%.2f" % (pct(me, 0.9) / 1000),
                     # 逐转换的 实测/要求 比值的中位与均值。§background 用它论证
                     # 「典型转换上 harness 什么都没加（中位 1.001），差额全在尾部
                     # （两个均值之比 1.065）」—— 这两个数 2026-09-24 之前只在正文里。
                     # 只在【非零要求】的转换上算（要求为 0 的比值没有意义）。
                     # >10 s 的**占比**：§I 引了它（「22% of gaps over ten seconds」），
                     # 而那个 22 是**只拿 662 个正值为分母**算的（144/662=21.8%），
                     # 与同句的另外两个统计量（都拿 799 个转换当分母）**分母不同** ——
                     # 本文件的 docstring 早就警告过这一族。这里把两个分母都印出来。
                     "demand_gt10_pct_of_transitions": "%.1f" % (
                         100.0 * sum(1 for x in dem if x > 10000) / len(dem)),
                     "demand_gt10_pct_of_positive": "%.1f" % (
                         100.0 * sum(1 for x in dem if x > 10000)
                         / max(1, sum(1 for x in dem if x > 0))),
                     "demand_positive_n": sum(1 for x in dem if x > 0),
                     "ratio_med": "%.4f" % statistics.median(rr),
                     "ratio_mean": "%.4f" % statistics.mean(rr),
                     "ratio_ratio_of_means": "%.4f" % (
                         statistics.mean(me) / statistics.mean(dem))})

    header = "\n".join([
        "# 每条 run 自带 trace（见下表 trace 列）；转换定义：同会话相邻两轮。",
        "# 轮次间隔：trace 要求 vs 实测 —— 由 scripts/lab/gen_toolwait.py 生成，勿手改",
        "# 轮次转换 = 同会话相邻两轮 = 每会话除最后一轮外的每一行",
        "# ⚠ 分母不同，均值差很多，正文引用时必须指明口径：",
        "#     全部 999 行（含每会话最后一轮，无后继）  均值 12.65 s",
        "#     799 次轮次转换（本表）                  均值 15.82 s   <- 论文用的",
        "#     662 个非零 tool_wait                     均值 19.10 s",
        "# ⚠ >10 s 的占比也有两个分母：demand_gt10_pct_of_transitions（799，18.0%）与",
        "#   demand_gt10_pct_of_positive（662，21.8%）—— §I 原来写「22% of gaps」用的是后者，",
        "#   而同句的另外两个统计量用的是前者。两个都印出来，正文必须指明用哪个。",
        "# 论文摘要的 16.85 s 是【实测】列的均值（run 的 steps.jsonl 实测间隔，",
        "# 含等 permit 的门时间），15.82 s 是 trace 要求值。",
        "# ratio_med/ratio_mean: 逐转换的 实测/要求 比值（只在要求>0 的转换上算）；",
        "#   ratio_ratio_of_means: 两个均值之比 —— 正文的「中位 1.001 / 均值比 1.065」是前两者的两个数",
        "run,trace,n_transitions,demand_med_s,demand_mean_s,demand_p90_s,measured_med_s,"
        "measured_mean_s,measured_p90_s,demand_gt10_pct_of_transitions,"
        "demand_gt10_pct_of_positive,demand_positive_n,ratio_med,ratio_mean,"
        "ratio_ratio_of_means"])
    fields = ["run", "trace", "n_transitions", "demand_med_s", "demand_mean_s", "demand_p90_s",
              "measured_med_s", "measured_mean_s", "measured_p90_s",
              "demand_gt10_pct_of_transitions", "demand_gt10_pct_of_positive",
              "demand_positive_n",
              "ratio_med", "ratio_mean", "ratio_ratio_of_means"]
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
