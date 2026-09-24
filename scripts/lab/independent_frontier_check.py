#!/usr/bin/env python3
"""独立复算论文头条数字 —— 【不 import 任何生成器】，从 trace 与原始日志直接算。

为什么要有：`check_paper_numbers.py` 查的是【正文 ↔ paper/data/*.csv】一致，
而 `paper/data/*.csv` 全部由 `scripts/lab/*.py` 生成。如果某个生成器的定义写错了，
正文与 CSV 会「一致地错」，检查器看不出来。这个脚本把最关键的几个量
**从头再实现一遍**，与生成器的输出对拍：

  1. 复用上界（trace 的 prefix_len 求和）—— 论文的 21,540,371 / 28,526,871 = 75.51%
  2. 每个静态锚点的墙钟与 SLO —— 直接从 steps.jsonl 的时间戳与 first_token_ms 算
  3. 静态上左包络与每条臂的有符号距离 Δ —— 独立写一遍插值

判据：本脚本的输出必须与 `paper/data/runs_precise.csv` / `table1.csv` 逐位相符
（容差 1e-3）。**跑完自己比对，不一致就以本脚本为准去查生成器。**

用法: python3 independent_frontier_check.py <trace.csv> <results_dir>
"""
import csv, json, os, sys

TOL = 1e-3
SLO_MS = 10000.0
STATIC = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5",
          "pairB_cap2hc", "cap3_hc", "cap4_hc", "cap3_hc_r2", "cap4_hc_r2"]
ARMS = ["foyer_sf0_r2", "foyer_hz1", "foyer_hc", "foyer_hz2", "foyer_hz0",
        "foyer_bres_r2", "foyer_breshz1", "foyer_nogate", "foyer_rg4", "foyfix_hc"]


def bound(trace_p):
    rows = list(csv.DictReader(open(trace_p)))
    pre = sum(int(r["prefix_len"]) for r in rows)
    tot = sum(int(r["prefix_len"]) + int(r["input_len"]) for r in rows)
    return pre, tot


def wall_slo(root, run):
    """墙钟 = max(complete) − min(submit)（与 run_summary.py:91 逐字同口径）；
    SLO = first_token_ms < 10s 的占比。两个量都只碰客户端日志。"""
    d = os.path.join(root, run)
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    subs = [s["submit_timestamp"] for s in st if s.get("submit_timestamp")]
    comps = [s["complete_timestamp"] for s in st if s.get("complete_timestamp")]
    tt = [s["first_token_ms"] for s in st if s.get("first_token_ms") is not None]
    return (max(comps) - min(subs)) / 60.0, 100.0 * sum(1 for x in tt if x < SLO_MS) / len(tt)


def main():
    trace_p, root = sys.argv[1], sys.argv[2]
    pre, tot = bound(trace_p)
    print("复用上界 = %d / %d = %.4f  = %.2f%%" % (pre, tot, pre / tot, 100 * pre / tot))

    pts = sorted((*wall_slo(root, "pois200_" + r), r) for r in STATIC)
    env, best = [], -1.0
    for w, s, r in pts:
        if s > best:
            env.append((w, s)); best = s
    print("包络锚点（独立重算）:")
    for w, s in env:
        print("   %.4f / %.4f" % (w, s))

    def front(w):
        for (w0, s0), (w1, s1) in zip(env, env[1:]):
            if w0 <= w <= w1:
                return s0 + (w - w0) / (w1 - w0) * (s1 - s0)
        return None

    # 与生成器落盘的值对拍
    ref_p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "..", "paper", "data", "table1.csv")
    ref = {}
    if os.path.exists(ref_p):
        ref = {r["run"]: r for r in csv.DictReader(l for l in open(ref_p) if not l.startswith("#"))}

    bad = 0
    print("\n%-16s %10s %10s %10s %10s" % ("run", "墙钟(算)", "墙钟(csv)", "Δ(算)", "Δ(csv)"))
    for r in ARMS:
        key = "pois200_" + r
        if not os.path.isdir(os.path.join(root, key)):
            print("%-16s （本地没有这条 run）" % r); continue
        w, s = wall_slo(root, key)
        f = front(w)
        d = s - f if f is not None else float("nan")
        rc = ref.get(r)
        dw = float(rc["wall_min"]) if rc else float("nan")
        dd = float(rc["delta_pp"]) if rc else float("nan")
        ok = (abs(w - dw) < TOL) and (abs(d - dd) < TOL)
        if not ok:
            bad += 1
        print("%-16s %10.4f %10.4f %10.4f %10.4f  %s" % (r, w, dw, d, dd, "OK" if ok else "<< 不一致"))
    print("\n结论：%s" % ("全部逐位相符（独立重算与生成器输出一致）" if not bad
                        else "有 %d 处不一致 —— 以本脚本为准去查生成器" % bad))
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
