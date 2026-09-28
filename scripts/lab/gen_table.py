#!/usr/bin/env python3
"""从 runs.csv 生成论文表 I 的 LaTeX 表体 —— 让「每个判决都由一个脚本产出」成为真的。

为什么必须有：表 I 的 Δ 列原来是手抄的，其中两行抄错了（rg4 写成 −24.0 实际
−25.02；foyfix 写成 −48.7 实际 −47.15）。而正文第 §7 声称每个判决都由单一脚本
从原始日志产出 —— 手抄的表让这句话不成立。这个脚本把表变成可复现的。

判决口径与 scripts/lab/frontier.py 一致：
  包络 = 静态点（含 +HC）的上左包络
  Δ = 该点的 SLO − 包络在同墙钟处的插值 SLO
  判读：Δ > +1.0 越过 / −1.0 ≤ Δ ≤ +1.0 平局 / Δ < −1.0 在线下

用法: python3 gen_table.py ../paper/data/runs.csv            # 论文里那张表（28 行）
      python3 gen_table.py ../paper/data/runs.csv --full     # 完整表（36 行，supplement 用）
"""
import csv, os, sys

# ---------------------------------------------------------------- 论文版的「不印」名单
# 2026-09-27：RTAS 2027 技术正文 11 页硬限 ⇒ 表 I（`\label{tab:runs}`）从 35 行缩到
# 27 行，下面这 8 条静态 cap 移出正文、改由 supplement 的**完整 run 表**承载。
#
# ⚠⚠ **2026-09-27 第二次落地（r55 中立复核 F1/F2 抓到的过期值）**：扫队列臂的第三次
# 读数（`foyer_scan_r3`）进了正文，于是**当前是 28 行 / 完整 36 行**（差仍是 8 行）。
# 上面那句「35 → 27」与再下面那句「此前印 35、正文印 27」都是**当时的历史**，保留不动；
# 但**当前值只在两处**：本文件顶部的「用法」与本文件末尾 `--full` 那条注释。
# 之所以要单独写这一段：`paper/supplement_material.md` §S9 声称「逐条走一遍实现，
# **不看脚本的 docstring 摘要**」，而它自己那格里的「35」恰恰是从**这里**抄的 ——
# docstring 自己过期，抄它的人就一起过期。
#
# ⚠ 这不是「少印几行」的显示细节 —— 它正是**生成器与 LaTeX 必须重新对齐**的那一处。
# 此前 gen_table.py 印 35 行、`sec_results.tex` 印 27 行，于是
# `check_paper_numbers.py` 的「表 I 缺生成器里的行」把 8 行报成 MISS、「表 I 逐行对拍」
# 只能在交集上比 —— 两份名单各说各的，没有任何一条检查能同时看见两边。
#
# 判据：**默认 stdout 就是论文里那张表**（逐行与 LaTeX 相同），`--full` 才给完整表。
# 于是「表 I 逐行对拍」可以**双向**比（生成器多的 / 正文多的都要报），
# 而 8 行移出后它们的守卫**改锚到 supplement 的完整表**（值一个都没丢，只是换了印处）。
PAPER_OMIT = {
    "cap2",        # 304.2 / 1.99 / 89.5 —— 同族的 cap2+HC 是前沿锚点
    "cap3_fixed",  # 258.7 / 2.89 / 74.4 —— 设备侧三点之一，判决由 cap3+HC 一对承担
    "cap3_pd",     # 246.4 / 2.97 / 79.3 —— 配对实验的 device 半边
    "cap4",        # 249.9 / 3.94 / 55.7
    "cap5",        # 260.9 / 4.89 / 27.1
    "cap3_ph",     # 233.8 / 2.97 / 81.5 —— 配对实验的 host 半边
    "cap5_hc",     # 227.6 / 4.74 / 47.3
    "cap8_hc",     # 241.8 / 7.63 /  9.5 —— 兑现率低端的那个点
}

# 表里的行标签（与论文一致），以及它们的排序位置由 Δ 决定
LABEL = {
    "default": "no control",
    "cap1": "cap1", "cap2": "cap2", "cap3_fixed": "cap3 (fixed)",
    "cap3_pd": "cap3 (paired, dev)", "cap3_ph": "cap3 (paired, +HC)",
    "cap4": "cap4", "cap5": "cap5",
    "pairB_cap2hc": "cap2+HC", "cap3_hc": "cap3+HC", "cap4_hc": "cap4+HC",
    "cap5_hc": "cap5+HC", "cap6_hc": "cap6+HC", "cap8_hc": "cap8+HC",
    "cap4_hc_r2": "cap4+HC (repeat)", "cap3_hc_r2": "cap3+HC (repeat)",
    "foyer_hc_r2": "horizon$=$3 (2nd run)", "foyer_sf0_r2": "single-flight off",
    "foyer_scan_r2": "scans the queue (2nd run)",
    "foyer_scan_r3": "scans the queue (3rd run)",
    "foyer_sf0_r3": "single-flight off (2nd run)",
    "foyer_hz1": "horizon$=$1", "foyer_hz1_r3": "horizon$=$1 (3rd run)",
    "foyer_hz1_r2": "horizon$=$1 (repeat)", "foyer_hc": "horizon$=$3 (base)",
    "foyer_hz2_r2": "horizon$=$2", "foyer_bres_r2": "resident base",
    "foyer_hz2_r3": "horizon$=$2 (2nd run)", "foyer_scan": "scans the queue",
    "foyer_hz0_r2": "horizon$=$0", "foyer_breshz1_r2": "horizon$=$1, no hw",
    "foyer_nogate": "no gate, no resv.", "foyer_rg4": "running gate$=$4",
    "foyfix_hc": "all throttles off",
    "aimd2": "AIMD, retuned", "aimd2_paper_r3": "AIMD, paper params",
}
# 候选锚点（由上左包络自动筛）。2026-09-25 加 `cap6_hc` —— 它是**静态点里最快的**，
# 所以是包络的最左端点（`frontier.py` 的 FRONT 同一天也加了它）。
# 2026-09-26 加 `cap3_pd` / `cap3_ph`（同卡背靠背的层级配对）。**它们不移动包络**：
# 两条都被 `cap3_hc_r2`（230.3 / 81.88）支配。加进来是为了让候选集完整。
ENV_KEYS = ["cap6_hc", "cap4_hc", "cap4_hc_r2", "cap3_hc", "cap3_hc_r2",
            "cap3_pd", "cap3_ph", "pairB_cap2hc", "cap1"]


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


def _csv_str(x):
    return x if isinstance(x, str) else str(x)


def emit_csv(runs, env, delta, front_slo, conc, out_p):
    """把表 I 的每一列落成一个 CSV —— 包括 Δ。

    为什么必须落盘：论文声称「每个判决都由一个脚本产出」，而 Δ 是【渲染时算的】，
    不存任何数据文件。审计于是把正文里每一个 Δ 数字都报成"找不到源头"
    （2026-09-24 一类假阳性有十几个）。判决列必须和其它列一样可被引用。
    """
    FR = _frontier_mod()
    fields = ["run", "label", "wall_min", "conc", "slo_pct", "front_slo",
              "delta_pp", "verdict", "contested", "anchor"]
    out = ["# 表 I 的每一列（含 Δ）—— 由 scripts/lab/gen_table.py 生成，勿手改",
           "# front_slo = frontier.py 的 front_slo(wall)（同一函数，不是另写一遍）",
           "# delta_pp  = slo_pct - front_slo；超出锚点范围为空",
           "# verdict   = 按 ±1.0pp 判带：>+1 越过 / 在带内平局 / <-1 在线下",
           "# contested = 同机争用窗口标记（concurrency.csv），与表里的 ‡ 同源",
           ",".join(fields)]
    env_w = {n for _, _, n in _envelope(ENV_KEYS, runs)}
    lines = []
    for k in sorted(runs, key=lambda k: float(runs[k]["wall_min"])):
        r = runs[k]
        w, sl = float(r["wall_min"]), float(r["slo_pct"])
        f = FR.front_slo(w)
        d = "" if f is None else "%.4f" % (sl - f)
        # ⚠ 2026-09-27：原来**内联**了 ±1.0（`> 1.0` / `>= -1.0`）——
        # 与 `frontier.classify` 是第二份判据，而唯一性守卫的正则看不到内联式。
        # 改成调用 `FR.classify_short`（从 `classify` 派生）。
        v = "OUT-OF-RANGE" if f is None else FR.classify_short(sl - f)
        # ⚠ 用 csv.writer 而不是手拼逗号：label 里有逗号（"AIMD, retuned"、
        # "no gate, no resv." 等四条），手拼会让字段数多于表头、DictReader 整体错位
        # （2026-09-24 审稿人抓）。csv.writer 会自动加引号。
        import io as _io
        buf = _io.StringIO()
        _w = csv.writer(buf)
        _w.writerow([_csv_str(x) for x in [
            r["run"], LABEL.get(k, k), "%.4f" % w, r["conc"], "%.4f" % sl,
            "" if f is None else "%.4f" % f, d, v, conc.get(k, "?"),
            "1" if k in env_w else "0"]])
        lines.append(buf.getvalue().rstrip("\r\n"))
    body = "\n".join(out + lines) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as fh:
        fh.write(body)
    print("  判决表 -> %s（%d 行）" % (out_p, len(lines)))


def main():
    # `--full` ⇒ 印完整表（36 行），供 supplement 用；默认印论文里那张表（28 行）。
    # ⚠ **论文版与完整版只差这一个名单** —— 不许在别处再判断一次「印不印」。
    FULL = "--full" in sys.argv

    def _pr(k):
        """这一行印不印在【论文】的表里。`--full` 下一律印。"""
        return FULL or k not in PAPER_OMIT

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
        # 每一行都必须有全精度坐标：正文的脚注声称四条步数不足 999 的 run
        # 「与其余各行用同一个全精度来源」，而这条路径曾经静默回落到 1 位小数的
        # runs.csv（2026-09-24 审稿人抓：三条 Δ 因此差了 0.01~0.04pp）。
        # 只断言「覆盖 > 15 行」挡不住这个 —— 它必须逐行点名。
        miss = sorted(k for k in runs if k not in {r["run"].replace("pois200_", "")
                                                   for r in load(cand_p)})
        if miss:
            raise SystemExit(
                "!! 这些 run 没有 runs_precise.csv 的坐标，会静默回落到 1 位小数：%s\n"
                "   在实验机（或完整镜像）上跑 `python3 frontier.py --csv` 重新生成。"
                % ", ".join(miss))
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
        if d is None:
            # 墙钟落在 FRONT 锚点范围**之外**：`front_slo` 按设计返回 None
            # （「范围外没有可比的前沿，不能给判决，否则端点外推会凭空造出越过」）。
            # 2026-09-25 `cap6_hc`（207.8 分）比最快的锚点 `cap4_hc_r2`（209.1）
            # 还快，**首次触发** —— 此前 `d > 0` 直接崩（NoneType 比 int）。
            ds = "\\emph{left of front}"
        elif anchor:
            ds = "\\emph{anchor}"
        else:
            # ⚠ `d == 0` 时不能走 `$-$%.2f % -d`（`-0.0` ⇒ 印成 `$-$-0.00`）。
            # 落在这条上的点其实就是锚点本身，标 anchor 更准确。
            ds = ("\\emph{anchor}" if abs(d) < 5e-5
                  else ("$+$%.2f" % d if d > 0 else "$-$%.2f" % -d))
        # 显示回 1 位小数（表里就是这样印的），但 ds 是用全精度算出来的
        # ⚠ 2026-09-27（落地）：`Conc.` 原来直接印 `runs.csv` 的原始串（2 位小数），
        # 于是 `no control` 那行印成 **94.91**，而正文的约定是「大于 10 印 1 位」
        # （`check_paper_numbers.py` 那条「表 I %s 的墙钟&并发&SLO 三连」守卫就是
        # 按这个约定写的，一直在报假 MISS 或反过来）。**生成器与守卫必须同一约定**，
        # 否则「重生成再抄进正文」这条路会把正文改坏。
        _cc = float(r["conc"])
        _cs = "%.1f" % _cc if _cc > 10 else "%.2f" % _cc
        return "    %-17s & %.1f & %s & %.1f & %s \\\\" % (
            LABEL[k] + dagger(k), float(r["wall_min"]), _cs,
            float(r["slo_pct"]), ds)

    print("    \\multicolumn{5}{l}{\\emph{Static caps}}\\\\")
    for k in [x for x in ["default", "cap1", "cap2", "cap3_fixed", "cap3_pd", "cap4", "cap5"]
              if _pr(x)]:
        print(row(k, anchor=(k == "cap1")))
    print("    \\midrule")
    print("    \\multicolumn{5}{l}{\\emph{Static caps + HiCache}}\\\\")
    # 只把【真正落在上左包络上】的点标成 anchor —— 不能按 ENV_KEYS 一律标，
    # 因为 cap4_hc 已经被它自己的重复支配了，它不在前沿上。
    # ⚠ `on_front` 仍按 **ENV_KEYS 全集**算（含被 `PAPER_OMIT` 移出的 cap3_ph）——
    # 包络的定义与「印哪几行」是两件事，不要因为少印一行就去动包络。
    on_front = {n for _, _, n in _envelope(ENV_KEYS, runs)}
    # ⚠ 这个列表就是表 I「Static caps + HiCache」段的**内容清单**。
    # 2026-09-25 教训：表 I 的 LaTeX 是**手写**在 sec_results.tex 里的，
    # 而这里是它的生成器 —— 两边会分叉。`cap5_hc` 入表时我只改了 tex，
    # 这里漏了，于是「生成器输出的表」比正文少一行。已由
    # check_paper_numbers.py 的「表 I 逐行对拍」守住（双向，见那里）。
    for k in [x for x in ["pairB_cap2hc", "cap3_hc", "cap3_ph", "cap3_hc_r2", "cap4_hc",
                          "cap4_hc_r2", "cap5_hc", "cap6_hc", "cap8_hc"] if _pr(x)]:
        print(row(k, anchor=(k in on_front)))
    print("    \\midrule")
    print("    \\multicolumn{5}{l}{\\emph{\\sys{} controller variants}}\\\\")
    foyer = sorted([k for k in LABEL if (k.startswith("foyer") or k == "foyfix_hc")
                    and _pr(k)],
                   key=lambda k: -delta(k))
    for k in foyer:
        print(row(k))
    print("    \\midrule")
    print("    \\multicolumn{5}{l}{\\emph{Independent adaptive controller (\\S\\ref{sec:results:aimd})}}\\\\")
    for k in sorted([k for k in ["aimd2", "aimd2_paper_r3"] if _pr(k)],
                    key=lambda k: -delta(k)):
        print(row(k))
    # 同时把每一列（含 Δ）落成 CSV
    import sys as _sys
    if "--csv" in _sys.argv:
        i = _sys.argv.index("--csv")
        emit_csv(runs, env, delta, front_slo, conc, _sys.argv[i + 1])


if __name__ == "__main__":
    main()
