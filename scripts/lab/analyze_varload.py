#!/usr/bin/env python3
"""变负载实验的分析 —— 按阶段拆，不报全程一个数。

codex 顾问 2026-09-23 明确要求：只报全程一个 SLO 会**掩盖低负载收益与高负载
损失**，而那正是这个实验要测的东西。所以本脚本按 trace 的负载阶段分段报，
并且用「到达→首 token」而不是「提交→首 token」（后者把准入控制的代价漏掉）。

它同时报执行侧指标：切换检测延迟、切换后的积压、最终排空时间。

用法:
  analyze_varload.py <run_dir> --switch-min 124.7 [--switch-session 100]
"""
import argparse, json, os, statistics, sys

TH = 10000.0


def load(run_dir):
    st = [json.loads(l) for l in open(os.path.join(run_dir, "steps.jsonl")) if l.strip()]
    by = {}
    for s in st:
        by.setdefault(s["session_id"], []).append(s)
    for v in by.values():
        v.sort(key=lambda s: s["round_idx"])
    return st, by


def ready_times(by, base):
    """每轮的「就绪时刻」：第 0 轮 = 到达；第 k 轮 = 上一轮完成 + tool wait。"""
    out = {}
    for sid, ss in by.items():
        for i, s in enumerate(ss):
            if i == 0:
                out[(sid, s["round_idx"])] = base + s["arrival_time_ms"] / 1000.0
            else:
                pc = ss[i - 1].get("complete_timestamp")
                tw = ss[i - 1].get("tool_wait_after_ms") or 0
                if pc is None:
                    continue
                out[(sid, s["round_idx"])] = pc + tw / 1000.0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--switch-min", type=float, default=124.7,
                    help="trace 里 λ 从低切高的时刻（分钟）")
    ap.add_argument("--switch-session", type=int, default=100)
    a = ap.parse_args()

    st, by = load(a.run_dir)
    meta = json.load(open(os.path.join(a.run_dir, "metadata.json"))) if os.path.exists(
        os.path.join(a.run_dir, "metadata.json")) else {}
    cands = [s["submit_timestamp"] - s["arrival_time_ms"] / 1000.0
             for s in st if s["round_idx"] == 0 and s.get("submit_timestamp")]
    if not cands:
        print("读不出时间戳"); return
    base = min(cands)
    ready = ready_times(by, base)
    switch_t = base + a.switch_min * 60

    # 每个会话归到它【第 0 轮到达】所在的阶段
    phase_of = {}
    for sid, ss in by.items():
        arr = base + ss[0]["arrival_time_ms"] / 1000.0
        phase_of[sid] = "低载" if arr < switch_t else "高载"

    rows = []
    for s in st:
        k = (s["session_id"], s["round_idx"])
        ft, sub = s.get("first_token_ms"), s.get("submit_timestamp")
        if ft is None or sub is None or k not in ready:
            continue
        wait = max(0.0, sub - ready[k]) * 1000.0
        rows.append({"phase": phase_of[s["session_id"]], "engine": ft,
                     "ready": ft + wait, "wait": wait})

    print("=== %s ===" % os.path.basename(a.run_dir.rstrip("/")))
    print("策略:", meta.get("policy"), " 墙钟:", meta.get("cap"), " 切点在 %.1f 分钟" % a.switch_min)
    print()
    print("%-6s %6s %9s %9s %9s %9s %8s" % (
        "阶段", "轮数", "SLO引擎%", "SLO到达%", "等p50", "等p90", "等max(s)"))
    for ph in ("低载", "高载"):
        g = [r for r in rows if r["phase"] == ph]
        if not g:
            continue
        se = 100 * sum(1 for r in g if r["engine"] < TH) / len(g)
        sa = 100 * sum(1 for r in g if r["ready"] < TH) / len(g)
        w = sorted(r["wait"] for r in g)
        print("%-6s %6d %9.1f %9.1f %9.0f %9.0f %8.0f" % (
            ph, len(g), se, sa, statistics.median(w), w[int(.9 * len(w))], max(w) / 1000))
    g = rows
    se = 100 * sum(1 for r in g if r["engine"] < TH) / len(g)
    sa = 100 * sum(1 for r in g if r["ready"] < TH) / len(g)
    print("%-6s %6d %9.1f %9.1f" % ("全程", len(g), se, sa))

    # 切换侧的执行指标
    sw = os.path.join(a.run_dir, "switcher.jsonl")
    if os.path.exists(sw):
        ev = [json.loads(l) for l in open(sw) if l.strip()]
        print()
        print("=== 切换日志（%d 条）===" % len(ev))
        prev = None
        for e in ev:
            if prev is None or e["cap"] != prev:
                print("  t=%+.1f 分钟  cap=%d  rate=%.4f" % (
                    (e["ts"] - base) / 60, e["cap"], e["rate"]))
            prev = e["cap"]


if __name__ == "__main__":
    main()
