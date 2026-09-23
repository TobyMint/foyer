#!/usr/bin/env python3
"""重算 SLO：把「门外等待」（等 permit）算进去。

为什么需要：现有 SLO 用的是 steps.jsonl 的 first_token_ms，那只从**提交引擎**
算起。但会话在被准入之前要等 permit —— 而**那正是准入控制的代价**。用
submit→first-token 衡量 SLO，等于让控制器不为它造成的排队付账。

⚠ 坑：`arrival_time_ms` 是**会话**的到达时刻，同一会话的每一轮都相同。
拿它去减每一轮的 submit_timestamp 会得到「会话已存活多久」，不是等待 ——
第一版就是这么错的（算出 84 分钟的"等待"）。

正确的每轮「就绪时刻」：
  第 0 轮   = run_start + arrival_time_ms
  第 k 轮   = 上一轮 complete_timestamp + tool_wait_after_ms
门外等待 = submit_timestamp − 就绪时刻（截断到 >= 0）

用法: python3 gen_arrival_slo.py <results_dir> <out.csv> [run ...]
"""
import csv, json, os, statistics, sys

RUNS = ["cap1","cap2","cap3_fixed","cap4","cap5","pairB_cap2hc","cap3_hc","cap4_hc",
        "foyer_hc","foyer_hz1","foyer_hz2","foyer_hz0","foyer_bres","foyer_breshz1",
        "foyer_nogate","foyer_rg4","foyfix_hc","aimd2","aimd2_paper"]
THRESH = 10000.0



def main():
    root, out = sys.argv[1], sys.argv[2]
    runs = sys.argv[3:] or RUNS
    rows = []
    print("%-14s %7s %7s %7s %8s %8s %8s" % (
        "run", "SLO内%", "SLO外%", "差pp", "等p50", "等p90", "等max(秒)"))
    for r in runs:
        p = os.path.join(root, "pois200_" + r, "steps.jsonl")
        if not os.path.exists(p):
            continue
        st = [json.loads(l) for l in open(p) if l.strip()]
        by = {}
        for s in st:
            by.setdefault(s["session_id"], []).append(s)
        # run_start：用第 0 轮的 submit 减 arrival 的最小值对齐（最早提交的那个会话）
        cands = [s["submit_timestamp"] - s["arrival_time_ms"] / 1000.0
                 for s in st if s["round_idx"] == 0 and s.get("submit_timestamp")]
        if not cands:
            continue
        base = min(cands)

        inside, outside, waits = [], [], []
        for sid, ss in by.items():
            ss.sort(key=lambda s: s["round_idx"])
            ready = None
            for i, s in enumerate(ss):
                ft, sub = s.get("first_token_ms"), s.get("submit_timestamp")
                if ft is None or sub is None:
                    continue
                if i == 0:
                    ready = base + s["arrival_time_ms"] / 1000.0
                else:
                    prev = ss[i - 1]
                    pc, tw = prev.get("complete_timestamp"), prev.get("tool_wait_after_ms") or 0
                    if pc is None:
                        ready = None
                    else:
                        ready = pc + tw / 1000.0
                if ready is None:
                    continue
                q = max(0.0, sub - ready) * 1000.0
                inside.append(ft)
                outside.append(ft + q)
                waits.append(q)
                # 下一轮的 ready 用本轮的 complete + tool_wait
        if not inside:
            continue
        si = 100 * sum(1 for x in inside if x < THRESH) / len(inside)
        so = 100 * sum(1 for x in outside if x < THRESH) / len(outside)
        print("%-14s %7.1f %7.1f %7.1f %8.0f %8.0f %8.0f" % (
            r, si, so, so - si, statistics.median(waits),
            sorted(waits)[int(.9 * len(waits))], max(waits) / 1000))
        rows.append({"run": r, "slo_engine_pct": round(si, 1),
                     "slo_ready_pct": round(so, 1), "delta_pp": round(so - si, 1),
                     "wait_p50_ms": round(statistics.median(waits)),
                     "wait_p90_ms": round(sorted(waits)[int(.9 * len(waits))]),
                     "wait_max_s": round(max(waits) / 1000)})
    if not rows:
        print("没有可用数据"); return
    with open(out, "w", newline="") as f:
        f.write("# SLO 两种口径 —— 由 scripts/lab/gen_arrival_slo.py 生成\n")
        f.write("# slo_engine: TTFT<10s，从【提交引擎】算起（论文现用口径）\n")
        f.write("# slo_ready:  TTFT<10s，从【该轮就绪】算起（含等 permit 的门外时间）\n")
        f.write("# delta_pp = slo_ready - slo_engine，即准入控制造成的门外等待的代价\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("->", out)


if __name__ == "__main__":
    main()
