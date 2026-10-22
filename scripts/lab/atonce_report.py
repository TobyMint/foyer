#!/usr/bin/env python3
"""一次性全倒负载的端到端对照：**我们的方案 vs 完全不管**。

用法：`python3 atonce_report.py <run_dir> [<run_dir> ...]`

为什么单独一个脚本：2026-10-10 起换了一条**新的负载轴**（`arrival_time` 全 0 =
所有会话同时到达），论文原来那套指标（Δ vs 前沿、deadline 达标率）不适用，
要量的是**端到端时间**。这个脚本把三种口径一次算清楚，免得事后挑说法。

## 三个口径（都会被打印，不许只报对自己有利的那个）

1. **mkespan** = 最后一个 complete − 第一个 arrival（全部会话跑完的总时间）
2. **会话端到端** = 每个会话自己的 last complete − 自己的 arrival（中位 / p90）
3. **工作量** = Σ `server_uncached_prompt_tokens`（真正要算的 prefill）+ Σ `server_completion_tokens`

## 判据：倍数 = 工作量比 × 吞吐比

    端到端倍数(我们/无控制) = (无控制工作量 / 我们工作量) × (我们吞吐 / 无控制吞吐)

两个因子都打印，**因为它们的乘积才是结论** —— 只看工作量会得出「我们该赢 3 倍」，
只看吞吐会得出「我们该输 3 倍」，两个都不对。

⚠ 口径注意：`arrival_time` 在 steps.jsonl 里是**相对 run 起点的毫秒数**；
真实时刻要用 `submit_timestamp − arrival_time_ms/1000` 反推 run 起点 t0。
**不要把 `submit_timestamp` 当到达时刻** —— 2026-10-10 我这么算过，把「控制器让会话
在门外等的时间」漏掉了，得出过一个 72 倍的假读数（真值 1.8 倍）。
"""
import json
import os
import statistics as st
import sys
from collections import defaultdict


def load(d):
    """读一个 run 的 steps.jsonl，只收 SUCCESS 且 first_token_ms 非空的步。"""
    p = os.path.join(d, "steps.jsonl")
    if not os.path.exists(p):
        raise SystemExit("!! %s 缺 steps.jsonl" % d)
    by_session = defaultdict(list)
    allrows = []
    n_bad = 0
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            n_bad += 1
            continue
        if r.get("status") != "SUCCESS" or r.get("first_token_ms") is None:
            n_bad += 1
            continue
        by_session[r["session_id"]].append(r)
        allrows.append(r)
    return by_session, allrows, n_bad


def report(d):
    S, rows, n_bad = load(d)
    if not rows:
        raise SystemExit("!! %s 没有可用步" % d)

    # run 起点：submit_timestamp - arrival_time_ms/1000（每个会话取第一个 round）
    t0 = min(r["submit_timestamp"] - r["arrival_time_ms"] / 1000.0 for r in rows)

    # 1) makespan
    t_first_arrival = t0 + min(r["arrival_time_ms"] for r in rows) / 1000.0
    t_last_done = max(r["complete_timestamp"] for r in rows)
    makespan_min = (t_last_done - t_first_arrival) / 60.0

    # 2) 会话端到端（从【到达】算，这是用户真正等的那个数）
    e2e = []
    for sid, v in S.items():
        v.sort(key=lambda r: r.get("round_idx", 0))
        arr = t0 + v[0]["arrival_time_ms"] / 1000.0
        e2e.append((max(x["complete_timestamp"] for x in v) - arr) / 60.0)
    e2e.sort()

    # 3) 工作量
    uncached = sum(r.get("server_uncached_prompt_tokens") or 0 for r in rows)
    decode = sum(r.get("server_completion_tokens") or 0 for r in rows)
    ttft = sorted(r["first_token_ms"] for r in rows)
    slo = 100.0 * sum(1 for x in ttft if x < 10000) / len(ttft)

    name = os.path.basename(d.rstrip("/"))
    return {
        "run": name,
        "n_steps": len(rows),
        "n_sessions": len(S),
        "n_skipped": n_bad,
        "makespan_min": makespan_min,
        "e2e_med_min": st.median(e2e),
        "e2e_p90_min": e2e[int(len(e2e) * 0.9)],
        "work_Mtok": (uncached + decode) / 1e6,
        "uncached_Mtok": uncached / 1e6,
        "decode_Mtok": decode / 1e6,
        "throughput_Ktok_per_min": (uncached + decode) / 1e3 / makespan_min,
        "slo_pct": slo,
        "ttft_med_ms": ttft[len(ttft) // 2],
    }


def common_set(dirs):
    """两条（或更多）臂都【成功完成】的 (session_id, round_idx) 集合。

    为什么需要它：2026-10-10 实测，一条 500 步的 trace 上有 3 步死在
    `connection closed before message completed`（服务端日志 0 错误），
    而**每一步失败都会让那个会话再也不推进**（r9 失败 ⇒ r10~r19 全不做）。
    于是「跑到多少步」是随机的 —— 两条臂各自跑到哪一步都不一样。
    ⇒ 只在**都完成了的那些步**上比 makespan 与工作量，失败落在哪里都不影响公平。
    """
    sets = []
    for d in dirs:
        keys = set()
        p = os.path.join(d, "steps.jsonl")
        for line in open(p):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("status") == "SUCCESS" and r.get("first_token_ms") is not None:
                keys.add((r["session_id"], r.get("round_idx", 0)))
        sets.append((d, keys))
    common = set.intersection(*[s for _, s in sets]) if sets else set()
    return common, sets


def report_on(d, keys):
    """与 report() 同口径，但**只在给定的 (session_id, round_idx) 子集上**。"""
    p = os.path.join(d, "steps.jsonl")
    by_session = defaultdict(list)
    rows = []
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("status") != "SUCCESS" or r.get("first_token_ms") is None:
            continue
        if (r["session_id"], r.get("round_idx", 0)) not in keys:
            continue
        by_session[r["session_id"]].append(r)
        rows.append(r)
    if not rows:
        raise SystemExit("!! %s 在共同集上没有任何步" % d)
    t0 = min(r["submit_timestamp"] - r["arrival_time_ms"] / 1000.0 for r in rows)
    makespan_min = (max(r["complete_timestamp"] for r in rows) - t0) / 60.0
    uncached = sum(r.get("server_uncached_prompt_tokens") or 0 for r in rows)
    decode = sum(r.get("server_completion_tokens") or 0 for r in rows)
    return {
        "run": os.path.basename(d.rstrip("/")),
        "n_steps": len(rows),
        "n_sessions": len(by_session),
        "makespan_min": makespan_min,
        "work_Mtok": (uncached + decode) / 1e6,
        "throughput_Ktok_per_min": (uncached + decode) / 1e3 / makespan_min,
    }


def main():
    dirs = sys.argv[1:]
    if not dirs:
        raise SystemExit(__doc__)
    rs = [report(d) for d in dirs]

    print("%-22s %6s %6s %10s %10s %10s %10s %8s %9s" % (
        "run", "步", "会话", "makespan", "端到端中位", "端到端p90",
        "工作量", "吞吐", "SLO%"))
    for r in rs:
        print("%-22s %6d %6d %8.1fmin %8.1fmin %8.1fmin %8.2fM %6.1fK/m %8.1f%%" % (
            r["run"], r["n_steps"], r["n_sessions"], r["makespan_min"],
            r["e2e_med_min"], r["e2e_p90_min"], r["work_Mtok"],
            r["throughput_Ktok_per_min"], r["slo_pct"]))
        if r["n_skipped"]:
            print("  ⚠ 跳过 %d 步（非 SUCCESS 或 first_token_ms 为空）" % r["n_skipped"])

    # 判据：倍数 = 工作量比 × 吞吐比
    if len(rs) == 2:
        a, b = rs  # a = 我们的方案，b = 无控制（调用时按这个顺序传）
        wr = b["work_Mtok"] / a["work_Mtok"]
        tr = a["throughput_Ktok_per_min"] / b["throughput_Ktok_per_min"]
        print()
        print("判据（a=%s 是我们的，b=%s 是无控制）:" % (a["run"], b["run"]))
        print("  工作量比 (b/a)      = %.3f   ← >1 对我们有利" % wr)
        print("  吞吐比   (a/b)      = %.3f   ← >1 对我们有利" % tr)
        print("  乘积（预测的端到端倍数） = %.3f" % (wr * tr))
        print("  实测 makespan 倍数  = %.3f   ← 应与乘积一致" % (
            b["makespan_min"] / a["makespan_min"]))
        print("  实测端到端中位倍数   = %.3f" % (b["e2e_med_min"] / a["e2e_med_min"]))
        print("  deadline 达标率      = %.1f%% → %.1f%%  (%.1f×)" % (
            b["slo_pct"], a["slo_pct"], a["slo_pct"] / max(b["slo_pct"], 1e-9)))

    # ---- 共同完成集口径（2026-10-10 加：部分运行是常态）----
    if len(rs) >= 2:
        common, sets = common_set(dirs)
        print()
        print("=" * 78)
        print("共同完成集口径（只保留【每条臂都成功完成】的步）")
        print("=" * 78)
        for d, k in sets:
            print("  %-24s 完成 %4d 步；与共同集比少了 %d 步" % (
                os.path.basename(d.rstrip("/")), len(k), len(k) - len(common)))
        if not common:
            print("  !! 共同集是空的 —— 两条臂没有任何一步都完成")
            return
        cs = [report_on(d, common) for d in dirs]
        print()
        print("  %-24s %6s %10s %12s" % ("run", "步", "makespan", "工作量"))
        for r in cs:
            print("  %-24s %6d %8.1fmin %10.2fM" % (
                r["run"], r["n_steps"], r["makespan_min"], r["work_Mtok"]))
        if len(cs) == 2:
            a, b = cs
            wr = b["work_Mtok"] / a["work_Mtok"]
            tr = a["throughput_Ktok_per_min"] / b["throughput_Ktok_per_min"]
            print()
            print("  在共同集上（a=%s 是我们的，b=%s 是无控制）:" % (a["run"], b["run"]))
            print("    工作量比 (b/a) = %.3f   吞吐比 (a/b) = %.3f   乘积 = %.3f" % (wr, tr, wr * tr))
            print("    实测 makespan 倍数 = %.3f" % (b["makespan_min"] / a["makespan_min"]))


if __name__ == "__main__":
    main()
