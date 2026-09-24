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
    """正文里有没有这个数。试 1~4 位小数、以及千分位两种写法。

    传进来的如果不是纯数字（例如「54.5 & 1.455 & 28.9」这样的多列片段），
    就按**字面子串**查 —— 多列一起查比单查一个数可靠得多，单查一个数太容易
    在别处撞车（2026-09-25 加归因表检查时加的这条通路）。"""
    s = str(v)
    try:
        float(s)
    except ValueError:
        return s in text
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
    fails, secondary, checks = [], [], 0

    def ck(desc, val, where=None, tier="P"):
        """tier="P" 正文引用过这个量，必须出现；tier="S" 论文【不逐条印】这个量
        （只印它的一个聚合/区间），找不到是预期内的，单独列出来供人扫一眼。

        为什么要有这一档：2026-09-24 之前 124 项检查里常年有 20 多项 MISS，
        全是"论文没逐条印"的假阳性 —— 假阳性一多，真 MISS 就淹掉了
        （这正是这个脚本要防的那类错误，只不过发生在脚本自己身上）。
        但 S 档不许变成"眼不见为净"：它照旧逐条打印，只是不计入退出码。
        """
        nonlocal checks
        checks += 1
        src = P.get(where, "") if where else alltext
        if has(src, val):
            if VERBOSE:
                print("  OK   %-58s %s" % (desc, val))
        elif tier == "S":
            secondary.append((desc, val, where or "全篇"))
        else:
            fails.append((desc, val, where or "全篇"))

    # ---- reuse.csv：兑现率 ----
    for r in load(os.path.join(ROOT, "paper/data/reuse.csv")):
        # 兑现率：表 2 印了 device-only 五行与 host tier 三个静态点，其余臂只进区间
        in_tab = r["run"] in ("cap1", "cap2", "cap3_fixed", "cap4", "cap5",
                              "pairB_cap2hc", "cap3_hc", "cap4_hc")
        ck("%s 兑现率" % r["run"], "%.1f" % (float(r["realized_frac"]) * 100),
           tier="P" if in_tab else "S")
        # prompt 占比：正文只举 cap1 的 69.9% 当例子，其余不逐条印
        ck("%s 复用率(prompt 占比)" % r["run"], "%.1f" % (float(r["reuse_frac"]) * 100),
           tier="P" if r["run"] == "cap1" else "S")
    hc = [r for r in load(os.path.join(ROOT, "paper/data/reuse.csv"))
          if r["family"] == "hicache"]
    bad = [r for r in hc if r["contested"] == "CONTESTED"]
    good = [r for r in hc if r["contested"] != "CONTESTED"]
    # host-tier 的【兑现率区间】：正文 §model 印的是 72.8--92.5%（全部 19 条 host-tier
    # run）与 90.2--92.4%（跨控制器区间的三个静态点）。按正文的口径（百分比、1 位小数）
    # 检查；reuse_frac（占 prompt 的比例）正文不印，降为次要档。
    # 2026-09-24 之前这里查的是 reuse_frac 的原始小数字符串，而 "0.5" 这种
    # 1 位小数写法在全篇到处都是 —— 那种检查等于永远通过，抓不到任何东西。
    for tag, sel in (("受损", bad), ("干净", good)):
        ck("%s host-tier 复用下界(占 prompt)" % tag, "%.1f" % (min(float(r["reuse_frac"]) for r in sel) * 100), tier="S")
        ck("%s host-tier 复用上界(占 prompt)" % tag, "%.1f" % (max(float(r["reuse_frac"]) for r in sel) * 100), tier="S")
    allhc = hc
    ck("host-tier 兑现下界", "%.1f" % (min(float(r["realized_frac"]) for r in allhc) * 100))
    ck("host-tier 兑现上界", "%.1f" % (max(float(r["realized_frac"]) for r in allhc) * 100))
    st3 = [r for r in hc if r["run"] in ("pairB_cap2hc", "cap3_hc", "cap4_hc")]
    ck("静态 host-tier 兑现下界", "%.1f" % (min(float(r["realized_frac"]) for r in st3) * 100))
    ck("静态 host-tier 兑现上界", "%.1f" % (max(float(r["realized_frac"]) for r in st3) * 100))

    # ---- reuse_x.csv：第二条 trace ----
    for r in load(os.path.join(ROOT, "paper/data/reuse_x.csv")):
        # 正文印的是「74.8% 掉到 64.0%」两个端点与逐段斜率，中间两条只在 slope.csv 里
        # 正文印的是区间的两个端点（当前是 cap2 的 74.8 与 cap6 的 62.5）与逐段斜率；
        # 中间几条只在 slope.csv 里。端点会随扫描推进而变 —— 改这里时同步改正文。
        ck("xtrace %s 兑现率" % r["run"], "%.1f" % (float(r["realized_frac"]) * 100),
           tier="P" if r["run"] in ("realhr_cap2", "realhr_cap8") else "S")

    # ---- §VI 引的平均占用（13.9% / 25.2%）----
    _rx2 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/reuse_x.csv"))}
    if "realhr_cap2" in _rx2 and "occ_mean_pct" in _rx2["realhr_cap2"]:
        ck("第二条 trace cap2 的平均占用", _rx2["realhr_cap2"]["occ_mean_pct"], "sec_xtrace.tex")
    occ2 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/occupancy.csv"))}
    if "cap1" in occ2:
        ck("主 trace cap1 的平均占用", occ2["cap1"]["occ_mean_pct"], "sec_xtrace.tex")

    # ---- 第二条 trace 的重复对（cap4 vs cap4_r2）：散布 ----
    rx = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/reuse_x.csv"))}
    if "realhr_cap4" in rx and "realhr_cap4_r2" in rx:
        d = abs(float(rx["realhr_cap4"]["realized_frac"])
                - float(rx["realhr_cap4_r2"]["realized_frac"])) * 100
        ck("第二条 trace 重复对的兑现散布", "%.1f" % d, "sec_xtrace.tex")

    # ---- slope.csv ----
    for r in load(os.path.join(ROOT, "paper/data/slope.csv")):
        ck("斜率 %s %s->%s" % (r["trace"], r["r0"], r["r1"]),
           r["slope_pp_per_unit"].lstrip("-"))

    # ---- 表 I 的每一行：墙钟 / 并发 / SLO 三个显示列 ----
    # 2026-09-24 补：no-control 那一行的 conc 曾是 1.69，而 1.69 是
    # num_running_reqs 的均值 —— 也就是标题里写明「Conc. 不是它」的那个量。
    # 那种错（同一列两个口径）本脚本抓不到，但「表里的数与数据文件对不上」能抓到，
    # 所以把三列都纳入。wall/conc/slo 在表里印 1 位小数。
    runs_csv = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/runs.csv"))}
    # table1.csv 覆盖 runs.csv 的全部行；正文的表只印其中一部分。
    # pairA_cap2hc 被 pairB 在两个轴上都支配，正文【不印它】（只在候选锚点里出现），
    # 所以这两项是预期内的不匹配，跳过。
    NOT_PRINTED = {"pairA_cap2hc"}
    for r in load(os.path.join(ROOT, "paper/data/table1.csv")):
        k = r["run"]
        if k in NOT_PRINTED:
            continue
        ck("表 I %s 的墙钟" % k, "%.1f" % float(r["wall_min"]), "sec_results.tex")
        ck("表 I %s 的 SLO" % k, "%.1f" % float(r["slo_pct"]), "sec_results.tex")
        if k in runs_csv:
            ck("表 I %s 的并发" % k, "%.1f" % float(runs_csv[k]["conc"]), "sec_results.tex")

    # ---- table1.csv：表 I 的 Δ ----
    for r in load(os.path.join(ROOT, "paper/data/table1.csv")):
        if r.get("delta_pp"):
            ck("表 I %s 的 Δ" % r["run"], r["delta_pp"].lstrip("-"), "sec_results.tex")

    # ---- occupancy.csv 的臂数（正文两处引了「二十三条臂」）----
    occ = load(os.path.join(ROOT, "paper/data/occupancy.csv"))
    ck("occupancy.csv 的臂数", len(occ), "sec_results.tex")

    # ---- tier25.csv：表 II 的每一列（2026-09-24 补上生成器 gen_tier25.py 后纳入）----
    for r in load(os.path.join(ROOT, "paper/data/tier25.csv")):
        ck("表 II %s 墙钟" % r["run"], r["wall_min"], "sec_discussion.tex")
        ck("表 II %s 并发" % r["run"], r["conc"], "sec_discussion.tex")
        ck("表 II %s SLO" % r["run"], r["slo_pct"], "sec_discussion.tex")
        ck("表 II %s 段SD" % r["run"], r["seg_sd_pp"], "sec_discussion.tex")

    # ---- gate_attrib.csv 注释行里落定的两个中位数 ----
    # 「两个中位数会随集合变」（§V 的稳健性声明）用的就是这两行；它们只存在于
    # CSV 的注释里，所以单独解析。all_rows_median 这一行是 2026-09-24 才补上的 ——
    # 在此之前正文引用的「every run in that file」两个数在文件里根本查不到。
    ga = open(os.path.join(ROOT, "paper/data/gate_attrib.csv"), encoding="utf-8").read()
    for tag in ("eight_median", "all_rows_median"):
        mt = re.search(r"^# %s.*?valve_pct=([\d.]+),projection_over_pct=([\d.]+)" % tag,
                       ga, re.M)
        if mt:
            ck("gate_attrib %s 阀门" % tag, mt.group(1), "sec_results.tex")
            ck("gate_attrib %s 投影超预算" % tag, mt.group(2), "sec_results.tex")
        else:
            fails.append(("gate_attrib.csv 缺 %s 行" % tag, "-", "sec_results.tex"))

    # ---- gate_attrib.csv：foyer_hc 的饿死守卫三件套（§V 用它论证「超预算时只有它能进」）----
    gah = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/gate_attrib.csv"))}
    if "pois200_foyer_hc" in gah:
        r = gah["pois200_foyer_hc"]
        ck("foyer_hc 被强制准入数", r["forced_admits"], "sec_results.tex")
        ck("foyer_hc 总准入数", r["total_admits"], "sec_results.tex")
        ck("foyer_hc 投影超预算周期数", r["cycles_over_budget"], "sec_results.tex")
        ck("foyer_hc 超预算时放行数", r["admitted_while_over"], "sec_results.tex")
        ck("foyer_hc 被强制准入占比", "%.1f" % (100.0 * int(r["forced_admits"]) / int(r["total_admits"])),
           "sec_results.tex")

    # ---- stall.csv：§V 的「不放行窗口」（2026-09-24 复核时原数字复现不出来，改用本表）----
    for r in load(os.path.join(ROOT, "paper/data/stall.csv")):
        if r["run"] in ("foyer_hz0", "foyer_breshz1", "foyer_rg4"):
            ck("stall %s 窗口时长" % r["run"], r["max_s"], "sec_results.tex")
            ck("stall %s 占墙钟%%" % r["run"], r["pct_wall"], "sec_results.tex")

    # ---- budget_sweep.csv（Route 3 的两条臂）----
    for r in load(os.path.join(ROOT, "paper/data/budget_sweep.csv")):
        ck("预算扫描 %s 墙钟" % r["run"], r["wall_min"], "sec_results.tex")
        ck("预算扫描 %s SLO" % r["run"], r["slo_pct"], "sec_results.tex")
        ck("预算扫描 %s 的 Δ" % r["run"], r["delta_pp"].lstrip("-"), "sec_results.tex")

    # ---- hitrate.csv ----
    # 论文逐条印的是这十条（§related 的 80.8->32.8 与 host tier 的 80.7/79.6/78.7、
    # §V 的 80.6 与 bres 的 80.2）；其余是 2026-09-24 补进文件、正文未逐条印的臂。
    HIT_PRINTED = {"pois200_cap1", "pois200_cap2", "pois200_cap3_fixed", "pois200_cap4",
                   "pois200_cap5", "pois200_pairB_cap2hc", "pois200_cap3_hc",
                   "pois200_cap4_hc", "pois200_foyer_hc", "pois200_foyer_bres_r2"}
    for r in load(os.path.join(ROOT, "paper/data/hitrate.csv")):
        ck("round-1+ %s" % r["run"], r["observed_round1_pct"],
           tier="P" if r["run"] in HIT_PRINTED else "S")

    # ---- tau2_windows.csv：§repro 的两个「同一 run 内」对照 ----
    tw = {r["run"]: [] for r in load(os.path.join(ROOT, "paper/data/tau2_windows.csv"))}
    for r in load(os.path.join(ROOT, "paper/data/tau2_windows.csv")):
        tw.setdefault(r["run"], []).append(r)
    _cap = tw.get("cap1", [])
    if _cap:
        ck("cap1 前 5.5h 的桶中位下界", min(x["tau2_p50_ms"] for x in _cap[:12]), "sec_discussion.tex")
        ck("cap1 前 5.5h 的桶中位上界", max(x["tau2_p50_ms"] for x in _cap[:12]), "sec_discussion.tex")
        for i, x in enumerate(_cap[12:15]):
            ck("cap1 争用后第 %d 桶" % (i + 1), x["tau2_p50_ms"], "sec_discussion.tex")
    # 转折点按【桶序号】取：t85 是第 120 分那一桶（29.8），rl99 是第 270 分那一桶（32.4）
    for _run, _key, _m in (("foyer_t85", "t85", "120"), ("foyer_rl99", "rl99", "270")):
        for x in tw.get(_run, []):
            if x["bucket_min"] == _m:
                ck("%s 转折前桶（第 %s 分）" % (_key, _m), x["tau2_p50_ms"], "sec_discussion.tex")

    # ---- superseded.csv：§discussion 引的「污染 vs 干净」复用值 ----
    for r in load(os.path.join(ROOT, "paper/data/superseded.csv")):
        ck("superseded %s 复用占比" % r["run"], r["reuse_frac"], "sec_discussion.tex")
        ck("superseded %s τ₂" % r["run"], r["tau2_ms"], "sec_discussion.tex")

    # ---- attribution.csv：§V 的十二行归因表（2026-09-25 补：此前这张表完全没有检查）----
    at = load(os.path.join(ROOT, "paper/data/attribution.csv"))
    if at:
        # 正文里印的是 occ_pct / running / tau1_ms 三列 + 类别
        # 正文印的是 occ_pct / running / tau1_ms 三列，各自位数不同（running 到 3 位）。
        # 单独查一个数太容易在别处撞车，所以查【三列连起来】那个片段。
        for r in at:
            ck("归因 %s 的 占用&R̄&τ₁ 三连" % r["arm"],
               "%s & %.3f & %s" % (r["occ_pct"], float(r["running"]), r["tau1_ms"]),
               "sec_results.tex")
        import collections as _c
        _cls = _c.Counter(r["class"] for r in at)
        # 正文：「4 of the 12 rows are attributed: three to unused memory ... one to step cost,
        #       five have a tau no matched comparison can confirm, and three are residuals」
        ck("归因行数", str(len(at)), "sec_results.tex")
        ck("归因-内存没用满", str(_cls.get("内存没用满", 0)), "sec_results.tex")
        ck("归因-步成本", str(_cls.get("步成本更高", 0)), "sec_results.tex")
        ck("归因-τ高不可比", str(_cls.get("步成本更高（但对照的在跑数不可比）", 0)), "sec_results.tex")
        ck("归因-残差", str(_cls.get("残差（只能报观测）", 0)), "sec_results.tex")

    # ---- §III 的两个例证（default 与 foyfix_hc 对 foyer_hc 的分量差）----
    _dd = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    if "foyer_hc" in _dd:
        _b = _dd["foyer_hc"]
        for _r, _tag in (("default", "§III 无控制臂"), ("foyfix_hc", "§III 全关节流臂"),
                         ("foyer_bres_r2", "§III 去记账臂")):
            if _r not in _dd:
                continue
            for _k, _lbl in (("idle_min", "空转"), ("busy_min", "忙时"), ("wall_min", "墙钟")):
                _d = float(_dd[_r][_k]) - float(_b[_k])
                ck("%s 的 Δ%s" % (_tag, _lbl),
                   ("%.1f" if abs(_d) < 100 else "%.0f") % abs(_d), "sec_model.tex")

    # ---- repeat_spread.csv：§VI 引的那两个「这条 trace 自己的重复对」----
    rs = load(os.path.join(ROOT, "paper/data/repeat_spread.csv"))
    for r in rs:
        names = r["runs"].split()
        if "realhr_cap4" in names:
            ck("realhr cap4 重复对墙钟散布", r["spread_pct"], "sec_xtrace.tex")
        if "realhr_foyer" in names:
            # 这一组的 2 位小数不够（真值 0.023%），正文印的是 0.02 —— 所以从
            # metadata 的 wall_s（秒，未舍入）复算，而不是用表里那一列。
            import json as _j
            try:
                wa = _j.load(open(os.path.join(ROOT, "results/night/realhr_foyer/metadata.json")))["wall_s"]
                wb = _j.load(open(os.path.join(ROOT, "results/night/realhr_foyer_r2/metadata.json")))["wall_s"]
                ck("realhr foyer 重复对墙钟散布", "%.2f" % (100.0 * abs(wa - wb) / ((wa + wb) / 2)),
                   "sec_xtrace.tex")
            except Exception as e:
                ck("realhr foyer 重复对墙钟散布（读不到 metadata：%s）" % e, "?", "sec_xtrace.tex")

    # ---- replicates.csv：§VI 的「重复对墙钟散布 1.8--4.7%」----
    rp = load(os.path.join(ROOT, "paper/data/replicates.csv"))
    if rp:
        rr = sorted(float(r["wall_range_pct"]) for r in rp)
        ck("replicates 墙钟散布下界", "%.1f" % rr[0], "sec_xtrace.tex")
        ck("replicates 墙钟散布上界", "%.1f" % rr[-1], "sec_xtrace.tex")

    # ---- toolwait.csv ----
    for r in load(os.path.join(ROOT, "paper/data/toolwait.csv")):
        for c in ("demand_med_s", "demand_mean_s", "measured_mean_s"):
            ck("toolwait %s %s" % (r["run"], c), r[c])
        # 第二条 trace 的两行（§VI/§criterion 引的 20.2 s / 39.9 s）
        if r["run"].startswith("realhr_"):
            ck("toolwait %s 要求中位" % r["run"], r["demand_med_s"], "sec_xtrace.tex")
            ck("toolwait %s 要求均值" % r["run"], r["demand_mean_s"], "sec_xtrace.tex")
        # §background 的「中位 1.001 / 两个均值之比 1.065」
        if r["run"] == "pois200_foyer_hc":
            ck("toolwait foyer_hc 比值中位", "%.3f" % float(r["ratio_med"]), "sec_background.tex")
            ck("toolwait foyer_hc 均值之比", "%.3f" % float(r["ratio_ratio_of_means"]), "sec_background.tex")

    # ---- idle_pooled.csv ----
    for r in load(os.path.join(ROOT, "paper/data/idle_pooled.csv")):
        # 正文印 all_runs；minus_* 是「去掉被争用标记的 run 之后结论不变」的稳健性
        # 变体，只在 §repro 里被描述，没有逐条印数
        for c in ("n_segments", "mean_s", "median_s", "pct_idle_time_in_gt20s"):
            ck("idle %s %s" % (r["set"], c), r[c],
               tier="P" if r["set"] == "all_runs" else "S")

    # ---- decomp.csv：三个区间 ----
    d = load(os.path.join(ROOT, "paper/data/decomp.csv"))
    T13 = {"cap1", "cap2", "cap3_fixed", "cap4", "cap5", "pairB_cap2hc", "cap3_hc",
           "cap4_hc", "foyer_hc", "foyer_hz1", "foyer_hz2", "foyer_hz0", "foyer_bres_r2"}
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
            # 正文 §V：「the growth reserve, which alone is 26,762 tokens, 28% of the budget」
            ck("foyer_hc 增长预留 tokens", r.get("growth_p50", ""))

    # ---- 图是否比数据旧 ----
    # 2026-09-24 碰巧发现：数据在 19:05/19:22 改过而图停在 18:43，正文的数与图对不上，
    # 而没有任何东西会提醒。图的输入是 decomp.csv / runs.csv / occupancy.csv 等。
    figs = glob.glob(os.path.join(ROOT, "paper", "figs", "fig*.pdf"))
    if figs:
        newest_data = max((os.path.getmtime(f) for f in glob.glob(
            os.path.join(ROOT, "paper", "data", "*.csv"))), default=0)
        stale = [os.path.basename(f) for f in figs if os.path.getmtime(f) < newest_data]
        checks += 1
        if stale:
            import datetime as _dt
            fails.append(("图比 paper/data 旧（需重跑 make_figs.py）",
                          "%d 张" % len(stale),
                          _dt.datetime.fromtimestamp(newest_data).strftime("%H:%M")))
        elif VERBOSE:
            print("  OK   图不比数据旧")

    print("共 %d 项检查：%d 项 MISS（正文引用过、却没找到，必须处置），"
          "%d 项次要未印（论文只印聚合值，属预期）。" % (checks, len(fails), len(secondary)))
    for desc, val, where in fails:
        print("  MISS %-56s %-12s (%s)" % (desc, val, where))
    if secondary and (VERBOSE or fails):
        print("  —— 次要（不计入退出码，供扫一眼）——")
        for desc, val, where in secondary:
            print("  ..   %-56s %-12s (%s)" % (desc, val, where))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
