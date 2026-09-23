#!/usr/bin/env python3
"""「有会话在等、却一个都不放行」的周期里，到底是哪个闸门在挡？

为什么需要：重构后的 §IV 说「引擎有空间，是控制器不拉杆」。那么必须回答
【哪个闸门】在挡。controller_budget3.py 的准入判定是一个合取式：

    if waiting and not valve and not gate_full and (prev_started or sf_disabled):
        逐个候选试 projection + n <= budget

所以「不放行」有四个互斥来源，本脚本逐个计数：
  valve        SLO 阀门关（TTFT 超过目标）
  gate_full    round gate 开且引擎在跑数已达上限
  prev_started 单飞闸门：上一个被放行的会话还没开始一轮，且距上次放行 < 60s
  projection   projection 已超预算，任何候选者都塞不进
  budget_fit   都不是 —— 有候选者但逐个都塞不进（head-of-line）
注意：日志里没有 prev_started，它是【排除法】得到的残差，如实标注。
"""
import glob, json, os, sys

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    rows = []
    for p in sorted(glob.glob(os.path.join(root, "*", "controller.jsonl"))):
        run = os.path.basename(os.path.dirname(p))
        if run.startswith("_"):
            continue
        c = {"valve": 0, "gate_full": 0, "proj_over": 0, "residual": 0, "blocked": 0, "n": 0}
        for line in open(p):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if "budget" not in d or "waiting_n" not in d:
                continue
            c["n"] += 1
            if d["waiting_n"] <= 0 or (d.get("n_admitted") or 0) > 0:
                continue
            c["blocked"] += 1
            if d.get("valve"):
                c["valve"] += 1
            elif d.get("gate_full"):
                c["gate_full"] += 1
            elif (d.get("base") or 0) + (d.get("growth_sum") or 0) > d["budget"]:
                c["proj_over"] += 1
            else:
                c["residual"] += 1     # 含 prev_started 与候选不 fit 两类
        if c["n"] < 50 or c["blocked"] == 0:
            continue
        b = c["blocked"]
        rows.append((run, c["n"], b,
                     100.0 * c["valve"] / b, 100.0 * c["gate_full"] / b,
                     100.0 * c["proj_over"] / b, 100.0 * c["residual"] / b))
    rows.sort(key=lambda r: -r[6])
    print("%-26s %6s %8s %8s %9s %9s %10s" % (
        "run", "采样", "被挡周期", "阀门%", "roundgate%", "投影超%", "残差%(单飞等)"))
    for r in rows:
        print("%-26s %6d %8d %8.1f %9.1f %9.1f %10.1f" % r)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                       "paper", "data", "gate_attrib.csv")
    with open(out, "w") as f:
        f.write("# 「有等待不放行」周期的闸门归因 —— gen_gate_attrib.py 生成\n")
        f.write("# 残差列 = 排除 valve/gate_full/投影超预算之后剩下的，主要来自单飞闸门 prev_started\n")
        f.write("run,samples,blocked_cycles,valve_pct,round_gate_pct,projection_over_pct,residual_pct\n")
        for r in rows:
            f.write("%s,%d,%d,%.1f,%.1f,%.1f,%.1f\n" % r)
    print("-> %s" % out)

if __name__ == "__main__":
    main()
