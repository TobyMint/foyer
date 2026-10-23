#!/usr/bin/env python3
"""SLO / goodput 口径：每一步"用户等多久拿到第一个 token"，以及有多少步达标。

用法：
    python3 slo_goodput.py <run_dir> [<run_dir> ...] [--csv out.csv] [--steps-csv out.csv]

## 为什么不能直接用 first_token_ms

`first_token_ms` 是**引擎侧**的 TTFT：请求已经进引擎、开始 prefill 到吐第一个 token。
而我们这套准入会在**门外**让会话等（挂起 / 排队 / 等配额）。2026-10-10 已经栽过一次：
拿 `submit_timestamp` 当到达时刻，把门外等待整个漏掉，得出 72 倍的假读数（真值 1.8 倍）。

所以这里对每一步算三个量，**三个都打印**：

    ready_i      会话"本可以继续"的时刻
                 = 到达时刻 (i=0)，或 complete_{i-1} + tool_wait_after_{i-1} (i>0)
    door_wait_i  submit_i - ready_i          ← 我们的准入让它等的时间
    ttft_i       first_token_ms              ← 引擎让它等的时间

    round_latency_i = door_wait_i + ttft_i          （用户从"能继续"到"看见字"）
    step_latency_i  = door_wait_i + total_duration_i（用户从"能继续"到"这一步写完"）

**SLO 判据用 round_latency**（10 s，预注册值，见 docs/plan_positive_paper_20261023.md §3）。
同时也报 engine-only（first_token_ms）口径，因为它能和别人的数字直接对，但**不能单独引用**：
它把自家门外的等待当成不存在。

## 输出

对每条 run 一行（`--csv` 写文件）：

    run, done, n_steps, n_sessions, makespan_min, steps_per_h,
    door_p50/p90/max_s, ttft_p50/p90/max_s, round_p50/p90/max_s,
    miss10_engine_pct, miss10_round_pct,
    goodput_steps_per_h, goodput_ratio_pct,
    e2e_med/p90_min, sess_deadline_pct_60/120/240/480,
    uncached_Mtok, decode_Mtok, work_Mtok

`done` 来自 `summary.json` 是否存在 —— **在跑的 run 不要和跑完的比**。
（`steps.jsonl` 存在不算跑完：崩溃的 run 也会写 summary，见 CLAUDE.md。）

## 口径共用

makespan / 会话端到端 / 工作量的定义直接 import `atonce_report.report()`，
不另写一份（项目纪律：两条管线算同一个量必须共用定义）。
"""
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atonce_report import report as atonce_report  # noqa: E402  共用 makespan/e2e/工作量口径

SLO_S = 10.0          # 预注册的 per-step TTFT SLO（秒）
SESSION_DL_MIN = (60, 120, 240, 480)


def load_success(d):
    """只收 SUCCESS 且 first_token_ms 非空的步；按会话、按 round_idx 排序。"""
    p = os.path.join(d, "steps.jsonl")
    if not os.path.exists(p):
        raise SystemExit("!! %s 缺 steps.jsonl" % d)
    by_session = {}
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
        by_session.setdefault(r["session_id"], []).append(r)
    for v in by_session.values():
        v.sort(key=lambda r: r.get("round_idx", 0))
    return by_session


def step_latencies(d):
    """逐步的 (door_wait, ttft, total_duration)，单位秒。

    返回 (rows, n_unknown)：rows 是 dict 列表；n_unknown 是"前一步缺失/轮次不连续，
    因此 ready 时刻不可知"的步数（这些步只报 engine 口径，不进 door_wait 统计）。
    """
    S = load_success(d)
    rows, n_unknown = [], 0
    for sid, v in S.items():
        for i, r in enumerate(v):
            submit = r["submit_timestamp"]
            if i == 0:
                ready = submit - r["arrival_time_ms"] / 1000.0
                known = True
            else:
                prev = v[i - 1]
                consecutive = r.get("round_idx", i) == prev.get("round_idx", i - 1) + 1
                if consecutive and prev.get("tool_wait_after_ms") is not None:
                    ready = prev["complete_timestamp"] + prev["tool_wait_after_ms"] / 1000.0
                    known = True
                else:
                    ready = None
                    known = False
                    n_unknown += 1
            door = (submit - ready) if known else None
            rows.append({
                "session": sid,
                "round": r.get("round_idx", i),
                "prompt_len": r.get("server_prompt_tokens") or r.get("prompt_len") or 0,
                "uncached": r.get("server_uncached_prompt_tokens") or 0,
                "door": door,
                "ttft": r["first_token_ms"] / 1000.0,
                "dur": r["total_duration_ms"] / 1000.0,
                "known": known,
            })
    return rows, n_unknown


def pct(xs, p):
    """简单分位（不插值），与项目其它脚本一致。"""
    if not xs:
        return float("nan")
    xs = sorted(xs)
    k = min(len(xs) - 1, int(len(xs) * p))
    return xs[k]


def summarize(d, slo_s=SLO_S):
    base = atonce_report(d)                  # 共用口径：makespan / e2e / 工作量
    rows, n_unknown = step_latencies(d)

    door = [r["door"] for r in rows if r["known"]]
    ttft = [r["ttft"] for r in rows]
    rnd = [r["door"] + r["ttft"] for r in rows if r["known"]]
    step = [r["door"] + r["dur"] for r in rows if r["known"]]

    miss_engine = 100.0 * sum(1 for x in ttft if x > slo_s) / len(ttft) if ttft else float("nan")
    miss_round = 100.0 * sum(1 for x in rnd if x > slo_s) / len(rnd) if rnd else float("nan")

    makespan_h = base["makespan_min"] / 60.0
    ok_round = sum(1 for x in rnd if x <= slo_s)

    # 会话级：从"到达"到"本会话最后一步完成"（跨臂可比，含全部门内门外等待）
    S = load_success(d)
    t0 = min(r["submit_timestamp"] - r["arrival_time_ms"] / 1000.0
             for v in S.values() for r in v[:1])
    e2e_min = sorted((max(x["complete_timestamp"] for x in v)
                      - (t0 + v[0]["arrival_time_ms"] / 1000.0)) / 60.0
                     for v in S.values())

    out = {
        "run": base["run"],
        "done": int(os.path.exists(os.path.join(d, "summary.json"))),
        "n_steps": base["n_steps"],
        "n_sessions": base["n_sessions"],
        "n_unknown_ready": n_unknown,
        "makespan_min": round(base["makespan_min"], 1),
        "steps_per_h": round(base["n_steps"] / makespan_h, 1) if makespan_h > 0 else float("nan"),
        "door_p50_s": round(pct(door, .5), 2),
        "door_p90_s": round(pct(door, .9), 2),
        "door_max_s": round(max(door), 1) if door else float("nan"),
        "door_sum_h": round(sum(door) / 3600.0, 2),
        "ttft_p50_s": round(pct(ttft, .5), 2),
        "ttft_p90_s": round(pct(ttft, .9), 2),
        "ttft_max_s": round(max(ttft), 1) if ttft else float("nan"),
        "round_p50_s": round(pct(rnd, .5), 2),
        "round_p90_s": round(pct(rnd, .9), 2),
        "round_max_s": round(max(rnd), 1) if rnd else float("nan"),
        "step_p50_s": round(pct(step, .5), 2),
        "step_p90_s": round(pct(step, .9), 2),
        "miss10_engine_pct": round(miss_engine, 1),
        "miss10_round_pct": round(miss_round, 1),
        "goodput_steps_per_h": round(ok_round / makespan_h, 1) if makespan_h > 0 else float("nan"),
        "goodput_ratio_pct": round(100.0 * ok_round / len(rnd), 1) if rnd else float("nan"),
        "e2e_med_min": round(st.median(e2e_min), 1),
        "e2e_p90_min": round(e2e_min[int(len(e2e_min) * 0.9)], 1),
        "uncached_Mtok": round(base["uncached_Mtok"], 2),
        "decode_Mtok": round(base["decode_Mtok"], 2),
        "work_Mtok": round(base["work_Mtok"], 2),
    }
    for dl in SESSION_DL_MIN:
        out["sess_dl_%d_pct" % dl] = round(
            100.0 * sum(1 for x in e2e_min if x <= dl) / len(e2e_min), 1)
    return out, rows


HEAD = ["run", "done", "n_steps", "n_sessions", "makespan_min", "steps_per_h",
        "door_p50_s", "door_p90_s", "door_max_s", "door_sum_h",
        "ttft_p50_s", "ttft_p90_s", "ttft_max_s",
        "round_p50_s", "round_p90_s", "round_max_s",
        "step_p50_s", "step_p90_s",
        "miss10_engine_pct", "miss10_round_pct",
        "goodput_steps_per_h", "goodput_ratio_pct",
        "e2e_med_min", "e2e_p90_min"]
HEAD += ["sess_dl_%d_pct" % d for d in SESSION_DL_MIN]
HEAD += ["uncached_Mtok", "decode_Mtok", "work_Mtok"]


def main(argv):
    dirs, csv_out, steps_csv = [], None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--csv":
            i += 1
            csv_out = argv[i]
        elif a == "--steps-csv":
            i += 1
            steps_csv = argv[i]
        else:
            dirs.append(a)
        i += 1
    if not dirs:
        raise SystemExit(__doc__)

    outs, allsteps = [], {}
    for d in dirs:
        o, rows = summarize(d)
        outs.append(o)
        allsteps[o["run"]] = rows

    # ---- 控制台表（人读）----
    print("%-18s %5s %5s %9s %8s %8s %9s %9s %9s %8s" % (
        "run", "done", "步", "makespan", "door_p90", "ttft_p50", "round_p90",
        "漏10s(引擎)", "漏10s(轮)", "good/h"))
    for o in outs:
        print("%-18s %5d %5d %7.1fmin %7.1fs %7.1fs %8.1fs %9.1f%% %10.1f%% %8.1f" % (
            o["run"], o["done"], o["n_steps"], o["makespan_min"],
            o["door_p90_s"], o["ttft_p50_s"], o["round_p90_s"],
            o["miss10_engine_pct"], o["miss10_round_pct"], o["goodput_steps_per_h"]))
    for o in outs:
        if not o["done"]:
            print("  ⚠ %s 还没有 summary.json —— 在跑/未跑完，不要与跑完的臂比" % o["run"])
        if o["n_unknown_ready"]:
            print("  ⚠ %s 有 %d 步 ready 时刻不可知（前一步缺失/轮次不连续），只进引擎口径"
                  % (o["run"], o["n_unknown_ready"]))

    print()
    print("会话级 deadline 扫描（从到达算的端到端达标率）：")
    print("%-18s %8s %8s %8s %8s %10s %10s" % (
        "run", "≤60m", "≤120m", "≤240m", "≤480m", "e2e中位", "e2e_p90"))
    for o in outs:
        print("%-18s %7.1f%% %7.1f%% %7.1f%% %7.1f%% %8.1fmin %8.1fmin" % (
            o["run"], o["sess_dl_60_pct"], o["sess_dl_120_pct"],
            o["sess_dl_240_pct"], o["sess_dl_480_pct"], o["e2e_med_min"], o["e2e_p90_min"]))

    # ---- CSV（给论文/图用）----
    if csv_out:
        os.makedirs(os.path.dirname(os.path.abspath(csv_out)), exist_ok=True)
        with open(csv_out, "w") as f:
            f.write(",".join(HEAD) + "\n")
            for o in outs:
                f.write(",".join(str(o[k]) for k in HEAD) + "\n")
        print("\n写 %s（%d 行）" % (csv_out, len(outs)))

    if steps_csv:
        os.makedirs(os.path.dirname(os.path.abspath(steps_csv)), exist_ok=True)
        with open(steps_csv, "w") as f:
            f.write("run,session,round,prompt_len,uncached,door_s,ttft_s,dur_s,ready_known\n")
            for run, rows in allsteps.items():
                for r in rows:
                    f.write("%s,%s,%d,%d,%d,%s,%.3f,%.3f,%d\n" % (
                        run, r["session"], r["round"], r["prompt_len"], r["uncached"],
                        "" if r["door"] is None else "%.3f" % r["door"],
                        r["ttft"], r["dur"], int(r["known"])))
        print("写 %s（%d 步）" % (steps_csv, sum(len(v) for v in allsteps.values())))


if __name__ == "__main__":
    main(sys.argv[1:])
