#!/usr/bin/env python3
"""控制器的占用投影 —— 论文 §V「控制器以为快满了」那句话的唯一数据来源。

为什么必须单独立一个脚本：原来那个 89,073 是手算的，复现不出来。核实时还发现
日志里的 `base` 字段【不可信】—— controller_budget3.py 在候选循环里重绑了
`base = s["ctx"] or s["prompt0"]`（候选者的上下文），而写日志是在循环【之后】，
所以有候选被尝试的周期里，日志里的 base 是候选者的值，不是投影的地板。

投影的正确算法（controller_budget3.py:321-326）：
    resident   = floor * pool_tokens      # 引擎设备侧占用
    ctx_sum    = sum(活跃会话的 ctx 或 prompt0)
    growth_sum = sum(forecast(s) for s in active)
    projection = max(resident, ctx_sum) + growth_sum

本脚本用 ctx_sum / resident / growth_sum 三个【独立记录】的字段重算投影，
绕开被污染的 base。

用法: gen_projection.py <results_dir> <out.csv>
"""
import csv, glob, json, os, statistics, sys

def med(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None

def main():
    root = sys.argv[1]
    out = sys.argv[2]
    rows = []
    for p in sorted(glob.glob(os.path.join(root, "*", "controller.jsonl"))):
        run = os.path.basename(os.path.dirname(p))
        if run.startswith("_"):
            continue
        L = []
        for line in open(p):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if "budget" in d and "ctx_sum" in d and "growth_sum" in d:
                L.append(d)
        if len(L) < 200:
            continue
        b = L[-1]["budget"]
        proj = [max(d.get("resident") or 0, d.get("ctx_sum") or 0) + (d.get("growth_sum") or 0)
                for d in L]
        occ = [d.get("resident") or 0 for d in L]
        pm, om = med(proj), med(occ)
        rows.append(dict(run=run, samples=len(L), budget=b,
                         proj_p50=pm, occ_p50=om,
                         proj_pct=100.0 * pm / b, occ_pct=100.0 * om / b,
                         ratio=(pm / om) if om else float("nan")))
    rows.sort(key=lambda r: -r["ratio"])
    print("%-26s %7s %9s %9s %9s %8s" % ("run", "采样", "投影中位", "占用中位", "投影%", "倍数"))
    for r in rows:
        print("%-26s %7d %9.0f %9.0f %8.1f%% %8.2f"
              % (r["run"], r["samples"], r["proj_p50"], r["occ_p50"], r["proj_pct"], r["ratio"]))
    with open(out, "w") as f:
        f.write("# 控制器占用投影 —— gen_projection.py 生成\n")
        f.write("# projection = max(resident, ctx_sum) + growth_sum（绕开被候选循环重绑的 base 字段）\n")
        f.write("run,samples,budget,proj_p50,occ_p50,proj_pct_of_budget,occ_pct_of_budget,ratio\n")
        for r in rows:
            f.write("%s,%d,%d,%.0f,%.0f,%.1f,%.1f,%.2f\n" % (
                r["run"], r["samples"], r["budget"], r["proj_p50"], r["occ_p50"],
                r["proj_pct"], r["occ_pct"], r["ratio"]))
    print("-> %s" % out)

if __name__ == "__main__":
    main()
