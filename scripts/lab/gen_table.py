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
import csv, os, sys

# 表里的行标签（与论文一致），以及它们的排序位置由 Δ 决定
LABEL = {
    "default": "no control",
    "cap1": "cap1", "cap2": "cap2", "cap3_fixed": "cap3 (fixed)",
    "cap4": "cap4", "cap5": "cap5",
    "pairB_cap2hc": "cap2+HC", "cap3_hc": "cap3+HC", "cap4_hc": "cap4+HC",
    "cap4_hc_r2": "cap4+HC (repeat)", "cap3_hc_r2": "cap3+HC (repeat)",
    "foyer_hc_r2": "horizon$=$3 (2nd run)", "foyer_sf0_r2": "single-flight off",
    "foyer_hz1": "horizon$=$1",
    "foyer_hz1_r2": "horizon$=$1 (repeat)", "foyer_hc": "horizon$=$3 (base)",
    "foyer_hz2": "horizon$=$2", "foyer_bres": "resident base",
    "foyer_hz0": "horizon$=$0", "foyer_breshz1": "horizon$=$1, no hw",
    "foyer_nogate": "no gate, no resv.", "foyer_rg4": "running gate$=$4",
    "foyfix_hc": "all throttles off",
    "aimd2": "AIMD, retuned", "aimd2_paper": "AIMD, paper params",
}
ENV_KEYS = ["cap4_hc", "cap4_hc_r2", "cap3_hc", "cap3_hc_r2", "pairB_cap2hc", "cap1"]  # 候选锚点（由上左包络自动筛）


def load(p):
    return list(csv.DictReader(l for l in open(p) if not l.startswith("#")))


def _envelope(keys, runs):
    """候选锚点的上左包络：按墙钟升序扫，SLO 破纪录的才留在前沿上。

    本函数仍用来决定【谁在前沿上】（表里标 anchor 用），但 Δ 的插值不自己算 ——
    见 main() 里对 frontier.py 的调用。
    """
    out, best = [], -1
    for k in sorted(keys, key=lambda k: float(runs[k]["wall_min"])):
        s = float(runs[k]["slo_pct"])
        if s > best:
            out.append((float(runs[k]["wall_min"]), s, k)); best = s
    return out


def _frontier_mod():
    """把 frontier.py 作为唯一的前沿定义与插值来源 import 进来。

    为什么必须共用：frontier.py 的 FRONT 锚点写死到 1 位小数（230.3 / 81.9），
    而本脚本原来从 runs.csv 自己推包络再自己插值。两条各算各的，同一条臂
    两边能差 0.02pp —— 表 I 写 -0.55、正文写 -0.57 就是这么来的
    （2026-09-24 被审稿人抓到）。§repro 同时点名两个脚本，它们必须给同一个数。
    """
    import importlib.util
    fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontier.py")
    spec = importlib.util.spec_from_file_location("_frontier", fp)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    runs = {r["run"]: r for r in load(sys.argv[1]) if r["tier"] == "200"}

    # 全精度覆盖：runs.csv 是手抄 run_summary.py 的 1 位小数表，而 frontier.py
    # 从原始日志算全精度（263.340318 vs 263.3）。同一条插值公式喂不同精度会差
    # 0.02pp —— 表 I 写 -0.55、正文写 -0.57 就是这么来的（2026-09-24 被审稿人抓到）。
    # 有 runs_precise.csv 就以它为准，两条管线共用一个来源。
    cand_p = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "runs_precise.csv")
    n_ov = 0
    if os.path.exists(cand_p):
        for r in load(cand_p):
            k = r["run"].replace("pois200_", "")
            if k in runs:
                runs[k]["wall_min"] = r["wall_min"]
                runs[k]["slo_pct"] = r["slo_pct"]
                n_ov += 1
        assert n_ov > 15, "runs_precise.csv 只覆盖了 %d 行，路径或前缀不对" % n_ov
    else:
        print("%% 警告：没有 runs_precise.csv，用 1 位小数的 runs.csv（delta 会与 frontier.py 差 ~0.02pp）",
              file=sys.stderr)
    env = [(w, s) for w, s, _ in _envelope(ENV_KEYS, runs)]

    # 同机争用标记：读 concurrency.csv，被标 CONTESTED 的臂在表里加 \ddagger，
    # 提醒读者这一行的墙钟/SLO/Δ 是在同机 >=4 条车道下测的、与其余各行不可比，
    # 已重测（见 §repro）。表是脚本生成的，标记也必须从这里出，不能手加。
    conc = {}
    cand = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "concurrency.csv")
    if os.path.exists(cand):
        for r in load(cand):
            conc[r["run"].replace("pois200_", "")] = r["verdict"]
        assert len(conc) > 50, "concurrency.csv 只读到 %d 行" % len(conc)
    # 短名（表里的 key）-> concurrency.csv 的短名：一致，直接查
    def dagger(k):
        return "$^\\ddagger$" if conc.get(k) == "CONTESTED" else ""

    FR = _frontier_mod()          # 唯一的前沿定义与插值（见 _frontier_mod 的注释）

    def front_slo(w):
        return FR.front_slo(w)

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
        # 显示回 1 位小数（表里就是这样印的），但 ds 是用全精度算出来的
        return "    %-17s & %.1f & %s & %.1f & %s \\\\" % (
            LABEL[k] + dagger(k), float(r["wall_min"]), r["conc"],
            float(r["slo_pct"]), ds)

    print("    \\multicolumn{5}{l}{\\emph{Static caps}}\\\\")
    for k in ["default", "cap1", "cap2", "cap3_fixed", "cap4", "cap5"]:
        print(row(k, anchor=(k == "cap1")))
    print("    \\midrule")
    print("    \\multicolumn{5}{l}{\\emph{Static caps + HiCache}}\\\\")
    # 只把【真正落在上左包络上】的点标成 anchor —— 不能按 ENV_KEYS 一律标，
    # 因为 cap4_hc 已经被它自己的重复支配了，它不在前沿上。
    on_front = {n for _, _, n in _envelope(ENV_KEYS, runs)}
    for k in ["pairB_cap2hc", "cap3_hc", "cap3_hc_r2", "cap4_hc", "cap4_hc_r2"]:
        print(row(k, anchor=(k in on_front)))
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
