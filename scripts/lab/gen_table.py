#!/usr/bin/env python3
"""从 runs.csv 生成论文表 I 的 LaTeX 表体 —— 让「每个判决都由一个脚本产出」成为真的。

为什么必须有：表 I 的 Δ 列原来是手抄的，其中两行抄错了（rg4 写成 −24.0 实际
−25.02；foyfix 写成 −48.7 实际 −47.15）。而正文第 §7 声称每个判决都由单一脚本
从原始日志产出 —— 手抄的表让这句话不成立。这个脚本把表变成可复现的。

判决口径与 scripts/lab/frontier.py 一致：
  包络 = 静态点（含 +HC）的上左包络
  Δ = 该点的 SLO − 包络在同墙钟处的插值 SLO
  判读：Δ > +1.0 越过 / −1.0 ≤ Δ ≤ +1.0 平局 / Δ < −1.0 在线下

用法: python3 gen_table.py ../paper/data/runs.csv
"""
import csv, sys

# 表里的行标签（与论文一致），以及它们的排序位置由 Δ 决定
LABEL = {
    "cap1": "cap1", "cap2": "cap2", "cap3_fixed": "cap3 (fixed)",
    "cap4": "cap4", "cap5": "cap5",
    "pairB_cap2hc": "cap2+HC", "cap3_hc": "cap3+HC", "cap4_hc": "cap4+HC",
    "foyer_hz1": "horizon$=$1", "foyer_hc": "horizon$=$3 (base)",
    "foyer_hz2": "horizon$=$2", "foyer_bres": "resident base",
    "foyer_hz0": "horizon$=$0", "foyer_breshz1": "horizon$=$1, no hw",
    "foyer_nogate": "no gate, no resv.", "foyer_rg4": "running gate$=$4",
    "foyfix_hc": "all throttles off",
    "aimd2": "AIMD, retuned", "aimd2_paper": "AIMD, paper params",
}
ENV_KEYS = ["cap4_hc", "cap3_hc", "pairB_cap2hc", "cap1"]   # 上左包络的四个锚点


def load(p):
    return list(csv.DictReader(l for l in open(p) if not l.startswith("#")))


def main():
    runs = {r["run"]: r for r in load(sys.argv[1]) if r["tier"] == "200"}
    env = sorted((float(runs[k]["wall_min"]), float(runs[k]["slo_pct"]))
                 for k in ENV_KEYS)

    def front_slo(w):
        for (w0, s0), (w1, s1) in zip(env, env[1:]):
            if w0 <= w <= w1:
                return s0 + (w - w0) / (w1 - w0) * (s1 - s0)
        return None

    def delta(k):
        r = runs[k]
        f = front_slo(float(r["wall_min"]))
        return None if f is None else float(r["slo_pct"]) - f

    def row(k, anchor=False):
        r = runs[k]
        d = delta(k)
        ds = "\\emph{anchor}" if anchor else ("$+$%.2f" % d if d > 0 else "$-$%.2f" % -d)
        if anchor:
            ds = "\\emph{anchor}"
        return "    %-17s & %s & %s & %s & %s \\\\" % (
            LABEL[k], r["wall_min"], r["conc"], r["slo_pct"], ds)

    print("    \\multicolumn{5}{l}{\\emph{Static caps}}\\\\")
    for k in ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]:
        print(row(k, anchor=(k == "cap1")))
    print("    \\midrule")
    print("    \\multicolumn{5}{l}{\\emph{Static caps + HiCache}}\\\\")
    for k in ["pairB_cap2hc", "cap3_hc", "cap4_hc"]:
        print(row(k, anchor=True))
    print("    \\midrule")
    print("    \\multicolumn{5}{l}{\\emph{\\sys{} controller variants}}\\\\")
    foyer = sorted([k for k in LABEL if k.startswith("foyer") or k == "foyfix_hc"],
                   key=lambda k: -delta(k))
    for k in foyer:
        print(row(k))
    print("    \\midrule")
    print("    \\multicolumn{5}{l}{\\emph{Independent adaptive controller (\\S\\ref{sec:results:aimd})}}\\\\")
    for k in sorted(["aimd2", "aimd2_paper"], key=lambda k: -delta(k)):
        print(row(k))


if __name__ == "__main__":
    main()
