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

**必须在实验机上跑**：本表统计【所有】带 controller.jsonl 的 run。本地镜像是部分
快照（2026-09-24：本地 34 行 vs 实验机 47 行），在本地跑会把正文引用的区间与中位数
算错 —— 正文原写「1.24 to 2.00 / median 1.75 / over every run 1.01 to 4.11 / 1.35」，
在 47 行的实验机版本上是 1.24--2.00（中位 1.78）、1.01--4.11（中位 1.55）。
见 CLAUDE.md「本地镜像是部分快照」。下面有 MIN_ROWS 断言。
"""
import csv, glob, json, os, statistics, sys

def med(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None

TRACE_MAIN = "replay_pois200_l04.csv"     # 论文的「this trace」= 主 trace


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
                         # growth_p50：增长预留单独的中位。论文 §V 的「growth reserve
                         # alone is 26,762 tokens, 28% of the budget」用的就是它 ——
                         # 2026-09-24 审稿人指出这个数在文件里查不到（能复算，但没落盘），
                         # 于是加列。注意是【全部周期的中位】，不是只看有准入/有等待的周期。
                         growth_p50=med([d.get("growth_sum") or 0 for d in L]),
                         proj_pct=100.0 * pm / b, occ_pct=100.0 * om / b,
                         # free = 预算里还空着的百分比。论文 §V 的「7.6% free」
                         # 就是这个数 —— 此前不落盘，审计报成找不到源头。
                         free_pct=100.0 - 100.0 * pm / b,
                         ratio=(pm / om) if om else float("nan")))
    # 镜像完整性护栏：本表是【对 run 集合】取区间与中位数，少 run 就少样本、数字静默变。
    # 断言必须落在【产出行数】上，不能落在文件数上 —— 本地有 63 个 controller.jsonl
    # （实验机 83），可用行却只有 34（实验机 47）：按文件数设阈值根本拦不住
    # （2026-09-24 第一次就设错了，本地照样跑完并写出了偏小的区间）。
    assert len(rows) >= 45, (
        "只产出 %d 行（实验机 47 行）—— 这多半是部分镜像，本脚本必须在实验机上跑。" % len(rows))
    # 集合与中位数落进文件（2026-09-24 第 5 轮审查：正文说「this trace 上的二十条
    # 控制器臂」，但按 trace 分流后主 trace 只有 19 条、区间是 1.24--1.91/中位 1.75，
    # 「1.24--2.00/1.78」只有把 25 档那条（trace=replay_night25.csv）算进来才成立。
    # 判据写进文件，正文与它对齐。
    def _tr(run):
        try:
            return os.path.basename(json.load(open(os.path.join(root, run, "metadata.json"))).get("trace") or "")
        except Exception:
            return "?"
    # 只算【跑完的】run：在跑的 run（还没写 summary.json）其控制器日志长度不定，
    # 比值会随进度漂移 —— 实测在跑的 bres_r2 给出 1.95，把主 trace 的区间上端撑到 1.95。
    def _done(run):
        return os.path.exists(os.path.join(root, run, "summary.json"))
    main = [r for r in rows if _tr(r["run"]) == TRACE_MAIN and r["ratio"] == r["ratio"]
            and _done(r["run"])]
    plus = main + [r for r in rows if r["run"].endswith("realhr_foyer") and r["ratio"] == r["ratio"]]
    allr = [r for r in rows if r["ratio"] == r["ratio"] and _done(r["run"])]
    def _med(v):
        v = sorted(v); return v[len(v) // 2] if v else float("nan")
    _sets = [("main_trace", main), ("main_plus_second_trace_arm", plus), ("all_rows", allr)]
    rows.sort(key=lambda r: -r["ratio"])
    print("%-26s %7s %9s %9s %9s %8s" % ("run", "采样", "投影中位", "占用中位", "投影%", "倍数"))
    for r in rows:
        print("%-26s %7d %9.0f %9.0f %8.1f%% %8.2f"
              % (r["run"], r["samples"], r["proj_p50"], r["occ_p50"], r["proj_pct"], r["ratio"]))
    with open(out, "w") as f:
        f.write("# 控制器占用投影 —— gen_projection.py 生成\n")
        f.write("# projection = max(resident, ctx_sum) + growth_sum（绕开被候选循环重绑的 base 字段）\n")
        f.write("# growth_p50 = 全部周期上 growth_sum 的中位（正文 §V 的 26,762 tokens 即 foyer_hc 的该列）\n")
        for tag, sel in _sets:
            rr = [float(x["ratio"]) for x in sel]
            f.write("# %s: n=%d, min=%.2f, max=%.2f, upper_median=%.2f\n"
                    % (tag, len(rr), min(rr), max(rr), _med(rr)))
        f.write("#   main_trace = metadata.trace 是 %s 且已写出 summary.json 的 run（正文的「this trace」）\n"
                % TRACE_MAIN)
        f.write("#   另两条集合写在这里是因为正文引了它们的区间：只把「另一条 trace 的控制器臂」"
                "加进来是 main_plus_second_trace_arm，其余全部是 all_rows\n")
        f.write("run,samples,budget,proj_p50,occ_p50,growth_p50,proj_pct_of_budget,"
                "occ_pct_of_budget,free_pct,ratio\n")
        for r in rows:
            f.write("%s,%d,%d,%.0f,%.0f,%.0f,%.1f,%.1f,%.1f,%.2f\n" % (
                r["run"], r["samples"], r["budget"], r["proj_p50"], r["occ_p50"],
                r["growth_p50"], r["proj_pct"], r["occ_pct"], r["free_pct"], r["ratio"]))
    print("-> %s" % out)

if __name__ == "__main__":
    main()
