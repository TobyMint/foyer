#!/usr/bin/env python3
"""从 trace 本身算出论文 §2 用的"工作集"事实。

用法：
    python3 gen_trace_facts.py data/replay_long19.csv [--pool 101502] [--csv out.csv]

为什么要有这个脚本：论文 Intro/Background 里那一串数字（12.9× 超订、12× 重读税、
38× prefix/append、0.21s vs 18.6s、12.7× 上界）是**整篇文章的动机**，
每一个都必须能从这个脚本重新算出来。手抄过一次就会漂（项目纪律：不许手算表）。

## 口径（写死在代码里，正文引数时必须与这里一致）

- **上下文 ctx_i**：第 i 轮**开始时**的上下文 = `prefix_len + input_len`
  （trace 的 `prefix_len` 是这一轮之前可复用的前缀，`input_len` 是这一轮新加的）。
- **工作集 W**：每个会话**最后一轮**的 ctx 之和 —— 所有会话都活着时的驻留量。
  这是"如果全部会话同时驻留需要多少 KV"。
- **超订倍数** = W / pool。pool 是引擎实际报告的 KV 池（device 层，token 数）。
- **重读税**：不做复用的话每轮都要重读 `prefix_len` ⇒ Σ prefix / Σ input。
- **重算上界**：完全不复用（每轮从零 prefill）⇒ Σ ctx / Σ input。
  这是"不做任何缓存"与"完美复用"之间的工作量比。
- **工具等待**：`tool_wait_after_ms` 的分布；>10 s 的间隔占条数比与占总停放时长比。

## 输出

`--csv` 写长表：key,value,unit,note。论文里每个数对应一行。
"""
import csv
import statistics as st
import sys


def load(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append({
                "session": r["session_id"],
                "round": int(r["round_idx"]),
                "prefix": int(r["prefix_len"]),
                "input": int(r["input_len"]),
                "output": int(r["output_len"]),
                "twait": float(r["tool_wait_after_ms"]),
                "arrival": float(r["arrival_time"]),
            })
    return rows


def growth_facts(by_sess, alpha=0.4, horizon=3, margin=1.15):
    """每会话的逐轮增长 + 控制器那条 EMA 储备的覆盖率。

    储备口径与控制器的默认值一致（controller_budget3.py：--ema-alpha 0.4、
    --horizon-rounds 3、--margin 1.15），即 g_hat = margin * horizon * EMA(growth)。
    """
    g, res, cov, tot = [], [], 0, 0
    for v in by_sess.values():
        ema = None
        for i in range(len(v) - 1):
            c = v[i]["prefix"] + v[i]["input"]
            gr = v[i + 1]["prefix"] + v[i + 1]["input"] - c
            ema = gr if ema is None else alpha * gr + (1 - alpha) * ema
            r = margin * horizon * ema
            g.append(gr)
            res.append(r)
            tot += 1
            cov += 1 if gr <= r else 0
    g.sort()
    res.sort()
    return g, res, (100.0 * cov / tot if tot else float("nan"))


def facts(rows, pool):
    by_sess = {}
    for r in rows:
        by_sess.setdefault(r["session"], []).append(r)
    for v in by_sess.values():
        v.sort(key=lambda r: r["round"])

    n_rounds = len(rows)
    n_sess = len(by_sess)
    g_sorted, res_sorted, cov = growth_facts(by_sess)
    ctx = [r["prefix"] + r["input"] for r in rows]          # 每轮开始时的上下文
    terminal = [v[-1]["prefix"] + v[-1]["input"] for v in by_sess.values()]
    W = sum(terminal)
    pref = sum(r["prefix"] for r in rows)
    app = sum(r["input"] for r in rows)
    bound = sum(ctx)

    ctx_s = sorted(ctx)
    pre_s = sorted(r["prefix"] for r in rows)
    app_s = sorted(r["input"] for r in rows)
    tw = sorted(r["twait"] for r in rows)
    parked = sum(tw)
    big = [x for x in tw if x > 10000.0]

    def q(xs, p):
        return xs[min(len(xs) - 1, int(len(xs) * p))]

    out = [
        ("n_sessions", n_sess, "sessions", "trace 里的会话数"),
        ("n_rounds", n_rounds, "rounds", "trace 里的轮数（= 请求数）"),
        ("rounds_per_session_med", st.median(len(v) for v in by_sess.values()), "rounds", ""),
        ("rounds_per_session_max", max(len(v) for v in by_sess.values()), "rounds", ""),
        ("working_set_tok", W, "tokens", "每个会话最后一轮的 ctx 之和（全部驻留所需 KV）"),
        ("pool_tok", pool, "tokens", "引擎报告的 KV 池（metadata.json pool_tokens）"),
        ("overcommit_x", round(W / pool, 2), "x", "working_set / pool"),
        ("ctx_med_tok", q(ctx_s, .5), "tokens", "逐轮上下文的中位"),
        ("ctx_mean_tok", round(st.mean(ctx), 0), "tokens", "逐轮上下文的均值"),
        ("ctx_p90_tok", q(ctx_s, .9), "tokens", ""),
        ("ctx_max_tok", max(ctx), "tokens", ""),
        ("working_set_per_session_tok", round(W / n_sess, 0), "tokens",
         "均值会话的【终态】工作集 = working_set / n_sessions"),
        ("pool_in_working_sets", round(pool / (W / n_sess), 2), "sessions",
         "pool 能装下几个【均值会话的终态工作集】—— 正文引的 1.47 就是这一行"),
        ("pool_in_ctx_mean", round(pool / st.mean(ctx), 2), "sessions",
         "pool / 逐轮上下文均值（另一种口径，别与上一行混用）"),
        ("pool_in_ctx_med", round(pool / q(ctx_s, .5), 2), "sessions",
         "pool / 逐轮上下文中位（另一种口径）"),
        ("prefix_sum_tok", pref, "tokens", "Σ prefix_len：不复用时每轮都要重读的量"),
        ("append_sum_tok", app, "tokens", "Σ input_len：真正新增的量"),
        ("reread_x", round(pref / app, 2), "x", "prefix_sum / append_sum = 重读税"),
        ("prefix_p50_tok", q(pre_s, .5), "tokens", "逐轮 prefix 的中位"),
        ("append_p50_tok", q(app_s, .5), "tokens", "逐轮 append 的中位"),
        ("prefix_append_p50_x", round(q(pre_s, .5) / max(q(app_s, .5), 1), 1), "x",
         "单轮 prefix/append 中位之比"),
        ("output_p50_tok", q(sorted(r["output"] for r in rows), .5), "tokens",
         "每轮生成的 token 中位（正文里'about 150 tokens out'）"),
        ("recompute_sum_tok", bound, "tokens", "Σ ctx：完全不复用时的 prefill 工作量"),
        ("recompute_bound_x", round(bound / app, 2), "x", "recompute_sum / append_sum"),
        ("toolwait_med_ms", round(q(tw, .5), 0), "ms", ""),
        ("toolwait_mean_ms", round(st.mean(tw), 0), "ms", ""),
        ("toolwait_p90_ms", round(q(tw, .9), 0), "ms", ""),
        ("toolwait_max_ms", round(max(tw), 0), "ms", ""),
        ("toolwait_gt10s_pct", round(100.0 * len(big) / len(tw), 1), "%", ">10s 的间隔占条数比"),
        ("toolwait_gt10s_share_pct", round(100.0 * sum(big) / parked, 1), "%",
         ">10s 的间隔占总停放时长比"),
        ("parked_total_h", round(parked / 1000.0 / 3600.0, 2), "h", "Σ tool_wait"),
        ("growth_med_tok", g_sorted[len(g_sorted) // 2], "tokens", "逐轮 ctx 增长的中位"),
        ("growth_mean_tok", round(st.mean(g_sorted), 0), "tokens", ""),
        ("growth_p90_tok", g_sorted[int(.9 * len(g_sorted))], "tokens", ""),
        ("growth_p99_tok", g_sorted[int(.99 * len(g_sorted))], "tokens", ""),
        ("reserve_med_tok", round(res_sorted[len(res_sorted) // 2], 0), "tokens",
         "控制器那条储备 g_hat = margin*horizon*EMA（1.15*3*EMA(0.4)）的中位"),
        ("reserve_frac_of_ctx", round(res_sorted[len(res_sorted) // 2] / q(ctx_s, .5), 3), "x",
         "储备 / 逐轮上下文中位 —— 正文引的 7.7% 就是这一行"),
        ("reserve_coverage_pct", round(cov, 1), "%",
         "下一轮实际增长 <= 储备 的比例（trace 上 583 个转移）"),
        ("all_arrive_at_zero", int(max(r["arrival"] for r in rows) == 0), "bool",
         "1 = 一次性全倒（atonce）"),
    ]
    return out


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    path, pool, csv_out = argv[0], 101502, None
    i = 1
    while i < len(argv):
        if argv[i] == "--pool":
            i += 1
            pool = int(argv[i])
        elif argv[i] == "--csv":
            i += 1
            csv_out = argv[i]
        i += 1
    rows = load(path)
    fs = facts(rows, pool)

    for k, v, u, note in fs:
        print("%-26s %12s %-10s %s" % (k, v, u, note))

    if csv_out:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(csv_out)), exist_ok=True)
        with open(csv_out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["key", "value", "unit", "note", "source"])
            for k, v, u, note in fs:
                w.writerow([k, v, u, note, path])
        print("\n写 %s（%d 行）" % (csv_out, len(fs)))


if __name__ == "__main__":
    main(sys.argv[1:])
