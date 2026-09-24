#!/usr/bin/env python3
"""正文数字 ↔ 数据文件的逐项对照 —— 改完论文后跑一遍。

为什么要有这个：2026-09-24 一天里，每一批修正都引入过被下一轮审查抓到的新错误
（`audit_numbers.py` 只管"这个数在不在任何 CSV 里"，不管"它是否等于 CSV 里那个量
算出来的值"）。本脚本补上后半截：对每一组【有生成器】的派生量，把 CSV 算出来的值
与正文里的串做匹配。

它不是万能的 —— 匹配是字符串级的，正文里一个数可能以 1 位或 2 位小数出现，
所以每个断言都同时试几种写法。**它只回答"正文里有没有这个值"，不回答
"这个值用在这里对不对"**，后者仍然要靠审查。

用法: python3 check_paper_numbers.py          # 全部检查
      python3 check_paper_numbers.py -v       # 连通过的一起列
"""
import csv, glob, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
TEX = sorted(glob.glob(os.path.join(ROOT, "paper", "*.tex")))
VERBOSE = "-v" in sys.argv


def load(p):
    return [r for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))]


def paper_text():
    return {os.path.basename(f): open(f, encoding="utf-8").read() for f in TEX}


def has(text, v):
    """正文里有没有这个数。试 1~4 位小数、以及千分位两种写法。"""
    s = str(v)
    if "." in s:
        for d in (1, 2, 3, 4):
            t = "%.*f" % (d, float(s))
            if t in text:
                return True
        return False
    n = int(float(s))
    return (str(n) in text or "{:,}".format(n) in text
            or ("{:,}".format(n).replace(",", "{,}")) in text)


def main():
    P = paper_text()
    alltext = "\n".join(P.values())
    fails, checks = [], 0

    def ck(desc, val, where=None):
        nonlocal checks
        checks += 1
        src = P.get(where, "") if where else alltext
        if has(src, val):
            if VERBOSE:
                print("  OK   %-58s %s" % (desc, val))
        else:
            fails.append((desc, val, where or "全篇"))

    # ---- reuse.csv：兑现率 ----
    for r in load(os.path.join(ROOT, "paper/data/reuse.csv")):
        ck("%s 兑现率" % r["run"], "%.1f" % (float(r["realized_frac"]) * 100))
        ck("%s 复用率(prompt 占比)" % r["run"], "%.1f" % (float(r["reuse_frac"]) * 100))
    hc = [r for r in load(os.path.join(ROOT, "paper/data/reuse.csv"))
          if r["family"] == "hicache"]
    bad = [r for r in hc if r["contested"] == "CONTESTED"]
    good = [r for r in hc if r["contested"] != "CONTESTED"]
    for tag, sel in (("受损", bad), ("干净", good)):
        ck("%s host-tier 复用下界" % tag, min(r["reuse_frac"] for r in sel))
        ck("%s host-tier 复用上界" % tag, max(r["reuse_frac"] for r in sel))

    # ---- reuse_x.csv：第二条 trace ----
    for r in load(os.path.join(ROOT, "paper/data/reuse_x.csv")):
        ck("xtrace %s 兑现率" % r["run"], "%.1f" % (float(r["realized_frac"]) * 100))

    # ---- slope.csv ----
    for r in load(os.path.join(ROOT, "paper/data/slope.csv")):
        ck("斜率 %s %s->%s" % (r["trace"], r["r0"], r["r1"]),
           r["slope_pp_per_unit"].lstrip("-"))

    # ---- table1.csv：表 I 的 Δ ----
    for r in load(os.path.join(ROOT, "paper/data/table1.csv")):
        if r.get("delta_pp"):
            ck("表 I %s 的 Δ" % r["run"], r["delta_pp"].lstrip("-"), "sec_results.tex")

    # ---- hitrate.csv ----
    for r in load(os.path.join(ROOT, "paper/data/hitrate.csv")):
        ck("round-1+ %s" % r["run"], r["observed_round1_pct"])

    # ---- toolwait.csv ----
    for r in load(os.path.join(ROOT, "paper/data/toolwait.csv")):
        for c in ("demand_med_s", "demand_mean_s", "measured_mean_s"):
            ck("toolwait %s %s" % (r["run"], c), r[c])

    # ---- idle_pooled.csv ----
    for r in load(os.path.join(ROOT, "paper/data/idle_pooled.csv")):
        for c in ("n_segments", "mean_s", "median_s", "pct_idle_time_in_gt20s"):
            ck("idle %s %s" % (r["set"], c), r[c])

    # ---- decomp.csv：三个区间 ----
    d = load(os.path.join(ROOT, "paper/data/decomp.csv"))
    T13 = {"cap1", "cap2", "cap3_fixed", "cap4", "cap5", "pairB_cap2hc", "cap3_hc",
           "cap4_hc", "foyer_hc", "foyer_hz1", "foyer_hz2", "foyer_hz0", "foyer_bres"}
    d13 = [r for r in d if r["run"] in T13]
    for desc, vals in (
            ("τ₁ 上界", [float(r["step_back_ms"]) for r in d13 if r["step_back_ms"]]),
            ("τ₁ 下界", [float(r["step_back_ms"]) for r in d13 if r["step_back_ms"]]),
            ("τ₂ 上界", [float(r["step_perreq_ms"]) for r in d13 if r["step_perreq_ms"]]),
            ("τ₂ 下界", [float(r["step_perreq_ms"]) for r in d13 if r["step_perreq_ms"]])):
        ck(desc, max(vals) if "上界" in desc else min(vals))
    ex = [float(r["excess_pct"]) for r in d13 if r["excess_pct"]]
    ck("τ₁/τ₂ 超出下界", min(ex)); ck("τ₁/τ₂ 超出上界", max(ex))

    # ---- concurrency.csv 的计数 ----
    c = load(os.path.join(ROOT, "paper/data/concurrency.csv"))
    ck("CONTESTED 总数", sum(1 for r in c if r["verdict"] == "CONTESTED"),
       "sec_discussion.tex")

    # ---- projection.csv ----
    for r in load(os.path.join(ROOT, "paper/data/projection.csv")):
        if r["run"] == "pois200_foyer_hc":
            ck("foyer_hc 投影倍数", r["ratio"])
            ck("foyer_hc free%", r["free_pct"])

    print("共 %d 项检查，%d 项没在正文里找到：" % (checks, len(fails)))
    for desc, val, where in fails:
        print("  MISS %-56s %-12s (%s)" % (desc, val, where))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
