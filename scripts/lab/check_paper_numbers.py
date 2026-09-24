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
import csv, glob, importlib.util, json, os, re, sys

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
    # 先说复合串（多列片段，如 "54.5 & 1.455 & 28.9"）：它 float() 一定会抛，
    # 而**原来那个 except 分支直接 return s in text 就出去了** —— 于是下面放宽
    # 空白的逻辑永远走不到（2026-09-25 加复合串检查时连踩两次）。
    # 表里的列是【对齐过的】，「91.2 &  5.1」中间可能有两个空格，必须放宽 & 两侧空白。
    if " & " in s:
        import re as _re
        # re.escape 把 " & " 转义成 "\ \&\ "（空格和 & 都被转义），按【那个】替换
        pat = _re.escape(s).replace("\\ \\&\\ ", r"\s*&\s*")
        return _re.search(pat, text) is not None
    try:
        float(s)
    except ValueError:
        # 非数字的复合串：**空白一律弹性**。LaTeX 源码会在词与词之间换行
        # （「170.5, 173.2\nand 191.5」），字面查会莫名其妙地对不上
        # （2026-09-25 改不放假窗口那三条时踩到）。
        import re as _re2
        return _re2.search(r"\s+".join(_re2.escape(w) for w in s.split()), text) is not None
    if "." in s:
        for d in (1, 2, 3, 4):
            t = "%.*f" % (d, float(s))
            if t in text:
                return True
        return False
    n = int(float(s))
    return (str(n) in text or "{:,}".format(n) in text
            or ("{:,}".format(n).replace(",", "{,}")) in text)



def _import_running_all(run):
    """从 metrics.csv 现算 sglang:num_running_reqs 的全时段均值 —— 与
    gen_arm_running.py 的 running_all 同一个量（那边也从同一个列算）。"""
    p = os.path.join(ROOT, "results/night", run, "metrics.csv")
    v = [float(x["sglang:num_running_reqs"]) for x in csv.DictReader(open(p))
         if x.get("sglang:num_running_reqs")]
    return sum(v) / len(v)


AUDIT = []


def _audit(desc, val, src):
    """记录每个被检查的值在【它被检查的那段正文】里出现多少次。

    为什么：`ck` 是字符串级的，一个值出现 20 次和出现 1 次，检查强度完全不同 ——
    出现次数越多，越可能是在别处撞上的（2026-09-25 的「假通过」就是这么来的：
    §III 的 39.3 变成 39.2 之后检查器仍通过，因为 39.2 在别处出现过）。
    这次审计只把弱的检查**列出来供人看**，不自动判它们错。
    """
    try:
        AUDIT.append((str(src).count(str(val)), desc, str(val)))
    except Exception:
        pass


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
        _audit(desc, val, src)
        if has(src, val):
            if VERBOSE:
                print("  OK   %-58s %s" % (desc, val))
        elif tier == "S":
            secondary.append((desc, val, where or "全篇"))
        else:
            fails.append((desc, val, where or "全篇"))

    def ck_near(desc, val, where, keyword, window=260, tier="P"):
        """值必须出现在【关键词附近】—— 补 `ck` 的假通过。

        为什么要有：`ck` 是字符串级的，它只问「这个数在不在正文里」。
        2026-09-25 抓到一个实例：§III 写基线步成本「39.3 ms」，而统一 τ₂ 定义后
        `decomp.csv` 里它已经是 **39.2** —— `ck` 却通过了，因为「39.2」在
        §V 的归因表里作为另一条臂的 Occ. 出现过。**同一个数在别处出现，
        不等于它用在了这里。** 这正是本项目「从错的列抄数」那一类的镜像。
        """
        nonlocal checks
        checks += 1
        src = P.get(where, "") if where else alltext
        i = src.find(str(keyword))
        hit = False
        while i >= 0:
            lo, hi = max(0, i - window), i + window
            if has(src[lo:hi], val):
                hit = True
                break
            i = src.find(str(keyword), i + 1)
        if hit:
            if VERBOSE:
                print("  OK   %-58s %s（近 %s）" % (desc, val, keyword))
        elif tier == "S":
            secondary.append((desc, val, where or "全篇"))
        else:
            fails.append((desc + "（须在「%s」附近）" % keyword, val, where or "全篇"))

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
    # 2026-09-25 改成查【三个数连起来】的复合串。原来逐列查，而并发是 1.0/2.6/3.9
    # 这种短值 —— --audit 显示 "3.9" 在正文出现 6 次，逐列查等于空转。
    # 复合串一旦有一个数变了就对不上，这才叫检查。
    runs_csv = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/runs.csv"))}
    NOT_PRINTED = {"pairA_cap2hc"}
    for r in load(os.path.join(ROOT, "paper/data/table1.csv")):
        k = r["run"]
        if k in NOT_PRINTED:
            continue
        if k in runs_csv:
            # 位数按【正文印的】给：墙钟 1 位、并发 2 位、SLO 1 位
            # （table1.csv 存的是 4 位，直接拿来比会对不上 —— 刚踩过）
            # no-control 那一行的 Conc. 是【百分比】(94.9)，不是并发数 ——
            # 表 I 的脚注专门说明了这一点（2026-09-24 修过一次量纲错）。
            _cc = float(runs_csv[k]["conc"])
            ck("表 I %s 的墙钟&并发&SLO 三连" % k,
               "%.1f & %s & %.1f" % (float(r["wall_min"]),
                                     "%.1f" % _cc if _cc > 10 else "%.2f" % _cc,
                                     float(r["slo_pct"])),
               "sec_results.tex")


    for r in load(os.path.join(ROOT, "paper/data/table1.csv")):
        if r.get("delta_pp"):
            ck("表 I %s 的 Δ" % r["run"], r["delta_pp"].lstrip("-"), "sec_results.tex")

    # ---- occupancy.csv 的臂数（正文两处引了「二十三条臂」）----
    occ = load(os.path.join(ROOT, "paper/data/occupancy.csv"))
    ck("occupancy.csv 的臂数", len(occ), "sec_results.tex")

    # ---- tier25.csv：表 II 的每一列（2026-09-24 补上生成器 gen_tier25.py 后纳入）----
    for r in load(os.path.join(ROOT, "paper/data/tier25.csv")):
        # 同上：四列连成一个复合串。单查「5.1」「92.8」这种短值会撞车。
        ck("表 II %s 墙钟&并发&SLO&段SD 四连" % r["run"],
           "%s & %s & %s & %s" % (r["wall_min"], r["conc"], r["slo_pct"], r["seg_sd_pp"]),
           "sec_discussion.tex")

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
        # 这两个数**必须一起查**：放行数是 9，单独查「9」在正文里出现 135 次，
        # 等于空转（2026-09-25 --audit 扫出来的）。正文那句话是
        # 「of 3{,}700 such cycles, nine admitted」—— 查这一整串。
        _NUM9 = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
                 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
        ck("§V 超预算周期数与放行数（复合句）",
           "of %s such cycles, %s admitted"
           % ("{:,}".format(int(r["cycles_over_budget"])).replace(",", "{,}"),
              _NUM9.get(int(r["admitted_while_over"]), "?")),
           "sec_results.tex")
        ck("foyer_hc 被强制准入占比", "%.1f" % (100.0 * int(r["forced_admits"]) / int(r["total_admits"])),
           "sec_results.tex")

    # ---- stall.csv：§V 的「不放行窗口」（2026-09-24 复核时原数字复现不出来，改用本表）----
    # 正文把那三条写成【一句】：「170.5, 173.2 and 191.5\,s, 0.9--1.1\% of the run's
    # wall clock」。逐条查 0.9 / 1.0 / 1.08 这种短值会撞车（--audit: "0.9" 出现 15 次），
    # 所以照正文那句的形态拼一下再查。
    _st = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/stall.csv"))}
    _three = [r for r in ("foyer_hz0_r2", "foyer_breshz1", "foyer_rg4") if r in _st]
    if len(_three) == 3:
        _s = sorted((float(_st[k]["max_s"]), float(_st[k]["pct_wall"])) for k in _three)
        _e = sorted(float(_st[k]["pct_wall"]) for k in _three)
        # 正文按这个顺序印三个时长（191.5 最后），先照数值升序拼，两种顺序都试
        _a = "%.1f, %.1f and %.1f" % (_s[0][0], _s[1][0], _s[2][0])
        _b = "%.1f, %.1f and %.1f" % (_s[2][0], _s[1][0], _s[0][0])
        checks += 1
        if not (has(P["sec_results.tex"], _a) or has(P["sec_results.tex"], _b)):
            fails.append(("§V 三条臂的不放行窗口时长（升序或降序都试过）", _a, "sec_results.tex"))
        ck("§V 三条臂的不放行窗口占墙钟区间",
           "%.1f--%.1f" % (_e[0], _e[2]), "sec_results.tex")
        # foyfix_hc 的「九条、合计 12%」：查复合串
        if "foyfix_hc" in _st:
            ck("§V 关掉全部节流的臂：九条窗口",
               "%s of them" % {9: "nine"}.get(int(_st["foyfix_hc"]["n_windows"]), "?"),
               "sec_results.tex")

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

    # ---- frontier_split.csv：辅助表，但必须与表 I 的 Δ 一致 ----
    # 它【不在正文里】，可是读者会打开 paper/data/ 逐个看。2026-09-25 codex 第 19 轮
    # 就是因为这张表给 hz1 +0.22（正文 −0.93）而判「从 paper/data 能追到互相矛盾的答案」。
    _fs = {r["arm"]: r["delta_pp"] for r in
           load(os.path.join(ROOT, "paper/data/frontier_split.csv")) if r.get("front") == "mixed"}
    _tt = {r["run"]: r["delta_pp"] for r in load(os.path.join(ROOT, "paper/data/table1.csv"))}
    for _k, _v in _fs.items():
        if _k in _tt:
            ck("frontier_split 的 %s 混合判決与表 I 一致" % _k, "%.2f" % float(_tt[_k]),
               "frontier_split.csv", tier="S")

    # ---- §III 的 host-tier 集合：判据 + 两条具名排除 必须正好等于 reuse.csv 的行数 ----
    _ru = load(os.path.join(ROOT, "paper/data/reuse.csv"))
    _hc = [r for r in _ru if r["family"] == "hicache"]
    ck("host-tier 集合条数（正文说 nineteen）", str(len(_hc)), "sec_model.tex")
    if "foyer_hz1_r2" in {r["run"] for r in _hc}:
        ck("§III 被点名排除的 hz1_r2 混进了集合", "NOPE", "sec_model.tex")

    # ---- superseded.csv：§discussion 引的「污染 vs 干净」复用值 ----
    for r in load(os.path.join(ROOT, "paper/data/superseded.csv")):
        ck("superseded %s 复用占比" % r["run"], r["reuse_frac"], "sec_discussion.tex")
        ck("superseded %s τ₂" % r["run"], r["tau2_ms"], "sec_discussion.tex")

        # τ₁ 必须与 gen_decomp 的 step_back_ms **逐位一致** —— 同一个量，两条管线，
        # 必须共用定义（CLAUDE.md 纪律 2）。2026-09-25 codex 第 21 轮发现它们差 0.1 ms
        # （旧 bres 这条管线给 34.2、gen_decomp 给 34.1），原因是 gen_superseded 自己
        # 又写了一份实现，把每个零样本固定算成 5 秒。修完之后两边都走
        # gen_decomp.busy_stats；下面这段就是那次事故的回归护栏。
        _d = os.path.join(ROOT, "results/night", "pois200_" + r["run"])
        if os.path.isdir(_d):
            _iu = importlib.util
            _sp = _iu.spec_from_file_location(
                "_gd", os.path.join(ROOT, "scripts/lab/gen_decomp.py"))
            _GD = _iu.module_from_spec(_sp)
            _sp.loader.exec_module(_GD)
            _steps = [json.loads(l) for l in open(os.path.join(_d, "steps.jsonl")) if l.strip()]
            _tok = sum(s.get("output_len_actual") or 0 for s in _steps)
            if _tok:
                _sb = "%.1f" % _GD.busy_stats(
                    _GD.read_metrics(os.path.join(_d, "metrics.csv")), _tok)[6]
                if _sb != r["tau1_ms"]:
                    fails.append(("superseded %s τ₁ ＝ gen_decomp 的步成本" % r["run"],
                                  "%s vs %s" % (r["tau1_ms"], _sb),
                                  "scripts/lab/gen_decomp.py（共用定义被破坏了）"))

    # ---- §VI 的两个 +0.40（realhr 控制器臂的重复佐证）----
    _rx = load(os.path.join(ROOT, "paper/data/reuse_x.csv"))
    if _rx:
        import importlib.util as _iu
        _sp = _iu.spec_from_file_location("_fr2", os.path.join(ROOT, "scripts/lab/frontier.py"))
        _FR = _iu.module_from_spec(_sp); _sp.loader.exec_module(_FR)
        _FR.RESULTS = os.path.join(ROOT, "results/night")
        for _r in ("realhr_foyer", "realhr_foyer_r2"):
            _s = _FR.summarise(_r)
            if _s:
                _f = _FR.front_slo_xtrace(_s["wall"]) if hasattr(_FR, "front_slo_xtrace") else None
                if _f is None:
                    # realhr 的前沿在 gen_elasticity_x 里建，frontier.py 不管这条 trace；
                    # 这里至少把墙钟与 SLO 本身钉住（正文引的是它们派生的 Δ）。
                    ck("%s 的 SLO" % _r, "%.1f" % _s["slo"], "sec_xtrace.tex") if _s["slo"] < 99.95 else None

    # ---- slo_sensitivity.csv：§VI 阈值段的「越线不复现」（hz1 +1.5 / hz1_r2 -2.3）----
    for r in load(os.path.join(ROOT, "paper/data/slo_sensitivity.csv")):
        if r.get("run") == "hz1":
            ck("§VI hz1 在 20s 的距离", r["slo20_pp"], "sec_discussion.tex")
        if r.get("run") == "hz1_r2":
            ck("§VI hz1_r2 在 20s 的距离", r["slo20_pp"], "sec_discussion.tex")
        if r.get("run") == "hc":
            ck("§VI base 在 10s 的距离", r["slo10_pp"], "sec_discussion.tex")
        if r.get("run") == "bres_r2":
            ck("§VI bres 在 10s 的距离", r["slo10_pp"], "sec_discussion.tex")

    # ---- §III 的 τ₁/τ₂ 三个派生区间（2026-09-25 发现集合没点名、值也对不上）----
    # 原来写「2.6--8.2 ms of a 27--37 ms step」，而 decomp.csv 里排除 hz1_r2 后
    # 差值是 2.6--8.8、τ₂ 是 20.6--39.2。**集合从来没写出来**，所以谁也没法复算。
    _acc = [r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))
            if r["run"] != "foyer_hz1_r2" and r["excess_pct"]]
    if _acc:
        _ex = [float(r["excess_pct"]) for r in _acc]
        _gp = [float(r["step_back_ms"]) - float(r["step_perreq_ms"]) for r in _acc]
        _t2 = [float(r["step_perreq_ms"]) for r in _acc]
        ck("§III excess_pct 下界", "%.1f" % min(_ex), "sec_model.tex")
        ck("§III excess_pct 上界", "%.1f" % max(_ex), "sec_model.tex")
        ck_near("§III τ₁−τ₂ 下界", "%.1f" % min(_gp), "sec_model.tex", "absolute terms")
        ck_near("§III τ₁−τ₂ 上界", "%.1f" % max(_gp), "sec_model.tex", "absolute terms")
        ck_near("§III τ₂ 下界", "%.1f" % min(_t2), "sec_model.tex", "absolute terms")
        ck_near("§III τ₂ 上界", "%.1f" % max(_t2), "sec_model.tex", "absolute terms")

    # ---- §III 基线步成本那句：值必须出现在「baseline」附近 ----
    # 2026-09-25：这句原来写 39.3，而统一 τ₂ 定义后 decomp.csv 里 default 的
    # step_perreq_ms 是 39.2。`ck` 因为 39.2 在别处出现过而放过了它。
    _dc = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    if "default" in _dc and _dc["default"]["step_perreq_ms"]:
        ck_near("§III 基线步成本（τ₂）", _dc["default"]["step_perreq_ms"],
                "sec_model.tex", "baseline")

    # ---- §VII 重写后新引的机制读数（闸门归因 + 占用投影）----
    # 2026-09-25 中立子 agent 第 9 轮指出：正文原来用「队列深 + 引擎只跑一个」
    # 论证「队列是节流造出来的」，而那个并列在 200 档基线上【一模一样地成立】
    # （foyer_hc 的 running 均值 1.137，push_25 是 1.136）—— 区分不了任何东西。
    # 现在改成引闸门归因与占用投影。这几个数必须能从表里追到。
    _ga = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/gate_attrib.csv"))}
    _pj = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/projection.csv"))}
    _k25 = "pois200_foyer_push_25"
    if _k25 in _ga:
        ck("§VII 25 档被挡周期数", _ga[_k25]["blocked_cycles"], "sec_discussion.tex")
        ck("§VII 25 档安全阀占比", _ga[_k25]["valve_pct"], "sec_discussion.tex")
        ck("§VII 25 档回合闸门占比", _ga[_k25]["round_gate_pct"], "sec_discussion.tex")
    if _k25 in _pj:
        ck("§VII 25 档投影占预算%", _pj[_k25]["proj_pct_of_budget"], "sec_discussion.tex")
        ck("§VII 25 档引擎上报占预算%", _pj[_k25]["occ_pct_of_budget"], "sec_discussion.tex")
    # 「两档的在跑数几乎一样」——这是那段论证的前提，钉住它
    _ar = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/arm_running.csv"))}
    if "foyer_hc" in _ar:
        ck("§VII 200 档基线在跑均值", "%.3f" % float(_ar["foyer_hc"]["running_all"]),
           "sec_discussion.tex")
    ck("§VII 25 档在跑均值", "%.3f" % float(_import_running_all(_k25)), "sec_discussion.tex")

    # ---- τ₂ 的三份实现必须逐 run 相同（共用定义的守护检查）----
    # `gen_concurrency.tau2()` 在实验机上跑、那边没有 scripts/lab/，所以它保留
    # 自己那份实现；`gen_decomp.perreq_one()` 是本地这一份，`gen_tau2_windows.py`
    # 已经改成 import 它。**注释说「逐字一致」不算数，这里逐 run 算一遍。**
    # 2026-09-25 这两份真的不一致过：gen_concurrency 有 `status == "SUCCESS"` 过滤，
    # 另两份没有（实测只有 `default` 一条 run 受影响）。
    _gd = importlib.util
    _sp = _gd.spec_from_file_location("_gd2", os.path.join(ROOT, "scripts/lab/gen_decomp.py"))
    _GD = _gd.module_from_spec(_sp); _sp.loader.exec_module(_GD)
    _sp2 = _gd.spec_from_file_location("_gc", os.path.join(ROOT, "scripts/lab/gen_concurrency.py"))
    _GC = _gd.module_from_spec(_sp2); _sp2.loader.exec_module(_GC)
    _root = os.path.join(ROOT, "results/night")
    _n = 0
    for _r in load(os.path.join(ROOT, "paper/data/decomp.csv")):
        _sp3 = os.path.join(_root, "pois200_" + _r["run"], "steps.jsonl")
        if not os.path.exists(_sp3):
            continue
        _steps = [json.loads(l) for l in open(_sp3) if l.strip()]
        _a = _GD.perreq_ms(_steps)
        _b = _GC.tau2(_root, "pois200_" + _r["run"])
        if _a is not None and _b is not None and abs(_a - _b) > 1e-9:
            fails.append(("τ₂ 两份实现不一致：%s" % _r["run"],
                          "gen_decomp %.4f vs gen_concurrency %.4f" % (_a, _b),
                          "scripts/lab/gen_decomp.py 与 gen_concurrency.py"))
        _n += 1
    if VERBOSE:
        print("  OK   τ₂ 两份实现在 %d 条 run 上逐位一致" % _n)

    # ---- elasticity.csv 表头：§IV 那句「覆盖整个控制器运行区间（1.35 到 1.69）」----
    # 这个区间是【九条 Foyer 臂】的，不是 controller 族全体的（后者含重复臂 hz1_r2，
    # R̄ 到 2.10）。表头两个集合都写出来了，这里查九条那个 —— 集合选错正是本项目
    # 反复栽的坑，所以把它钉住。
    _el = open(os.path.join(ROOT, "paper/data/elasticity.csv"), encoding="utf-8").read()
    _mn = re.search(r"^# nine_foyer_arms_Rbar_min,([\d.]+)", _el, re.M)
    _mx = re.search(r"^# nine_foyer_arms_Rbar_max,([\d.]+)", _el, re.M)
    if _mn and _mx:
        ck("§IV 控制器运行区间下界", "%.2f" % float(_mn.group(1)), "sec_criterion.tex")
        ck("§IV 控制器运行区间上界", "%.2f" % float(_mx.group(1)), "sec_criterion.tex")

    # ---- elasticity_x.csv：§VI 的 realhr 控制器臂（含它那个不复现的越线）----
    for r in load(os.path.join(ROOT, "paper/data/elasticity_x.csv")):
        if r.get("kind") == "arm" and r["name"].startswith("realhr_foyer"):
            ck("%s 的 5s 距离" % r["name"], r["delta5_pp"], "sec_xtrace.tex")
            ck("%s 的 10s 距离" % r["name"], r["delta10_pp"], "sec_xtrace.tex")

    # ---- §III 的两个例证（重测后都换过/改过数）----
    # 2026-09-25 codex 第 23 轮：这两处原来用旧 hz0 的数，而重测后
    # ①「两个相似在跑数」那例变成 1.58 / 30.2 ms；
    # ②**非单调反例失效了** —— 旧 hz0（1.66）比 cap4（1.65）并发高且空转多，
    #   新 hz0_r2 是 1.58 / 16.9%，成了「并发更低、空转更多」，什么也证明不了。
    #   换成 no gate（1.68 / 20.7%）对 cap4（1.65 / 10.4%）。
    _a3 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/arm_running.csv"))}
    _d3 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    for _k in ("foyer_nogate", "cap4", "foyer_hz0_r2", "cap4_hc"):
        if _k in _a3 and _k in _d3:
            ck_near("§III %s 的空转%%" % _k, "%.1f" % float(_d3[_k]["idle_pct"]),
                    "sec_model.tex", "idle")
            # ⚠ 关键词不要带反斜杠 —— 在 heredoc 里 `\t` 会变成制表符，
            # 匹配不上还看不出来（2026-09-25 刚踩）。用纯文本词。
            ck_near("§III %s 的 R̄busy（两位）" % _k, "%.2f" % float(_a3[_k]["running_busy"]),
                    "sec_model.tex",
                    "idles" if _k in ("foyer_nogate", "cap4") else "requests at")

    # ---- horizon 扫描（图 6）----
    # 2026-09-25 codex 第 23 轮：这张表原来【没有生成器】、是手维护的，
    # hz0/hz2 被重跑替代后它和图 6 都还留着旧读数，图注里「两轮比三轮慢 15 分钟」
    # 在新数据下是【反的】。现已由 gen_horizon.py 从 table1.csv 生成，这里逐项钉住。
    _hz = load(os.path.join(ROOT, "paper/data/horizon.csv"))
    if _hz:
        _base = [r for r in _hz if r["horizon"] == "3"]
        _h0 = [r for r in _hz if r["horizon"] == "0"]
        _h1 = [r for r in _hz if r["horizon"] == "1"]
        _h2 = [r for r in _hz if r["horizon"] == "2"]
        if _base and _h0:
            ck("图6 去掉预留损失的 SLO（10.0）",
               "%.1f" % (float(_base[0]["slo_pct"]) - float(_h0[0]["slo_pct"])), "sec_results.tex")
        if _base and _h2:
            ck("图6 两轮对三轮的墙钟差（快 20 分）",
               "%.0f" % abs(float(_h2[0]["wall_min"]) - float(_base[0]["wall_min"])),
               "sec_results.tex")
        if _h1:
            ck("图6 一轮的墙钟", _h1[0]["wall_min"], "sec_results.tex")
        # ⚠ 不要为图 6 的四个墙钟各加一条 ck_near —— 图注本来就不逐条印它们，
        # 硬钉只会得到假 MISS（2026-09-25 加这块时先写错了，四条全 MISS）。
        # 图与 horizon.csv 的一致性由「图不比 paper/data 旧」那条覆盖。

    # ---- §III「未解释」段的回归（τ₁ ~ 重算量，18 条干净 host-tier）----
    # 2026-09-25 加：此前正文里这个 r 与最大残差**没有任何检查覆盖**，
    # 我在改条数时把残差猜成了 1.5（真值 1.6）—— 猜出来的数正是要靠检查挡住的。
    import math as _mm2
    # ⚠ `load()` 返回的是【列表】不是字典 —— 直接写 `r["run"] in _dx` 恒为 False，
    # 整块会静默不执行（2026-09-25 加这块时踩到，靠 DEBUG 打印才看见）。
    _rx = load(os.path.join(ROOT, "paper/data/reuse.csv"))
    _dx = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    _ex = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/eviction.csv"))}
    _clean = [r["run"] for r in _rx
              if r["family"] == "hicache" and r["contested"] != "CONTESTED"
              and r["run"] in _dx and _dx[r["run"]]["step_back_ms"]]
    if len(_clean) >= 5:
        _xs = [float(_ex[k]["uncached_tok"]) / 1e6 for k in _clean]
        _ys = [float(_dx[k]["step_back_ms"]) for k in _clean]
        _mx, _my = sum(_xs) / len(_xs), sum(_ys) / len(_ys)
        _b = sum((x - _mx) * (y - _my) for x, y in zip(_xs, _ys)) / sum((x - _mx) ** 2 for x in _xs)
        _a = _my - _b * _mx
        _r = (sum((x - _mx) * (y - _my) for x, y in zip(_xs, _ys))
              / _mm2.sqrt(sum((x - _mx) ** 2 for x in _xs) * sum((y - _my) ** 2 for y in _ys)))
        _res = max(abs(y - (_a + _b * x)) for x, y in zip(_xs, _ys))
        ck("§III 回归的条数", len(_clean), "sec_model.tex")
        ck("§III 回归的 r", "%+.2f" % _r, "sec_model.tex")
        ck_near("§III 回归的最大残差", "%.1f" % _res, "sec_model.tex", "straight line")

    # ---- §II 的「最佳臂对最近静态锚点」的数 ----
    # 2026-09-25：最佳臂在 hz2_r2 落地后【换人了】—— 原来是 sf0_r2（−0.55），
    # 现在是 hz2_r2（−0.30）。§II 那句跟着换，检查也跟着换；
    # sf0_r2 的那两个差值正文不再引，降为次要档（它还留在表 I 与 §V 里）。
    _t1 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/table1.csv"))}
    if {"foyer_sf0_r2", "foyer_hz2_r2", "cap3_hc_r2", "cap3_hc", "foyer_hz1"} <= set(_t1):
        for _best in ("foyer_hz2_r2", "foyer_sf0_r2"):
            _tier = "P" if _best == "foyer_hz2_r2" else "S"
            for _anch in ("cap3_hc_r2", "cap3_hc"):
                ck("§II %s 对 %s" % (_best, _anch),
                   "%.1f" % (float(_t1[_best]["slo_pct"]) - float(_t1[_anch]["slo_pct"])),
                   "sec_background.tex", tier=_tier)
        ck("§II hz1 对 cap3_hc",
           "%.1f" % (float(_t1["foyer_hz1"]["slo_pct"]) - float(_t1["cap3_hc"]["slo_pct"])),
           "sec_background.tex")

    # ---- §III 的层级匹配对（三列：占用均值 / R̄busy / 兑现率）----
    _oc = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/occupancy.csv"))}
    _ar = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/arm_running.csv"))}
    _ru = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/reuse.csv"))}
    for _r in ("cap3_fixed", "cap3_hc", "cap3_hc_r2"):
        if _r in _oc and _r in _ar and _r in _ru:
            ck("§III %s 占用均值" % _r, _oc[_r]["occ_mean_pct"], "sec_model.tex")
            ck("§III %s R̄busy" % _r, "%.2f" % float(_ar[_r]["running_busy"]), "sec_model.tex")
            ck("§III %s 兑现" % _r, "%.1f" % (100 * float(_ru[_r]["realized_frac"])), "sec_model.tex")

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
        # ⚠ 这几条**不能查单个数字** —— 归因数只有个位数（1/3/5），
        # 审计显示「1」在正文里出现 184 次、「3」165 次，等于空转
        # （2026-09-25 加了 --audit 才看见）。改成查【正文那一整句复合串】，
        # 计数一变这句话就对不上，检查才有意义。
        _NUM = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
                7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}
        _n_mem = _cls.get("内存没用满", 0)
        _n_step = _cls.get("步成本更高", 0)
        _n_high = _cls.get("步成本更高（但对照的在跑数不可比）", 0)
        _n_res = _cls.get("残差（只能报观测）", 0)
        ck("§V 归因计数复合句（N of the M rows are attributed）",
           "%d of the %d rows are attributed" % (_n_mem + _n_step, len(at)),
           "sec_results.tex")
        ck("§V 归因分项（三条内存 / 一条步成本 / 五条 τ 高 / 三条残差）",
           "%s to unused memory" % _NUM.get(_n_mem, "?"), "sec_results.tex")
        ck("§V τ 高行数", "%s\\nhave a $\\tau$" % _NUM.get(_n_high, "?"),
           "sec_results.tex", tier="S")
        ck("§V 残差行数", "and %s are residuals" % _NUM.get(_n_res, "?"), "sec_results.tex")

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

    # ---- 摘要与 §V 的「非支配」声明：sf0_r2 不被表 I 的任何静态行支配 ----
    # 这是摘要里唯一一处【正面】声明（"not dominated ... 4.4pp above the nearest"），
    # 所以它必须机械可复算。判据就是非支配的定义：没有一条静态行在【墙钟更快】的
    # 同时【SLO 也更高】。
    _t = load(os.path.join(ROOT, "paper/data/table1.csv"))
    _stat = [r for r in _t if not r["run"].startswith(("foyer", "aimd", "foyfix"))
             and r["run"] != "default"]
    _sf = [r for r in _t if r["run"] == "foyer_sf0_r2"]
    if _sf and _stat:
        _w0, _s0 = float(_sf[0]["wall_min"]), float(_sf[0]["slo_pct"])
        _dom = [r["run"] for r in _stat
                if (float(r["wall_min"]) < _w0 and float(r["slo_pct"]) >= _s0)
                or (float(r["slo_pct"]) > _s0 and float(r["wall_min"]) <= _w0)]
        # 原来查的是 str(len(_dom))，也就是查「0」在摘要里出不出现 ——
        # --audit 显示 "0" 出现 20 次，等于空转。改成查【那句话本身】：
        # 只要支配行的数目变成非 0，这句话就不该留在摘要里，字面查才对得上。
        if len(_dom) == 0:
            ck("摘要「not dominated」声明", "\\emph{not dominated} by", "main.tex")
        else:
            fails.append(("摘要仍写 not dominated，但实测有 %d 条静态行支配 sf0_r2" % len(_dom),
                          "、".join(_dom), "main.tex"))

    # ---- backlog.csv：§VII 的队列长度 ----
    # 每个 run 两行：window=run（[最早提交, 最后完成]，与全篇墙钟同一窗口）与
    # window=all（全部控制周期）。**正文主张用 run 那一行**；all 那一行是稳健性对照，
    # 只以「4.1 而不是 3.7」和两个分母的形式出现。
    # 2026-09-25 codex 第 21 轮指出：只报全周期会把首个请求提交之前的空队列算进来，
    # 而 25 档短，那一段占它 12% 的周期（200 档只占 2%），于是中位从 18 掉到 16。
    # 键改成 (run, window) —— 原来按 run 建字典会静默只留后一行。
    _bl = {(r["run"], r["window"]): r
           for r in load(os.path.join(ROOT, "paper/data/backlog.csv"))}
    _early = [v for (r, w), v in _bl.items()
              if r.startswith("load25c_budget3") and w == "run"]
    if _early:
        ck("§VII 更早一代 25 档的上界",
           "%.0f" % max(float(x["waiting_p50"]) for x in _early), "sec_discussion.tex")
        ck("§VII 更早一代 25 档的下界",
           "%.0f" % min(float(x["waiting_p50"]) for x in _early), "sec_discussion.tex")

    _25 = _bl.get(("pois200_foyer_push_25", "run"))
    for _r in ("pois200_foyer_hc", "pois200_foyer_push_25"):
        if (_r, "run") in _bl:
            _k = _bl[(_r, "run")]
            ck("§VII %s 队列中位（运行窗口）" % _r, "%.0f" % float(_k["waiting_p50"]),
               "sec_discussion.tex")
            ck("§VII %s 队列最大（运行窗口）" % _r, _k["waiting_max"], "sec_discussion.tex")
            # 运行窗口的周期数正文不逐条印（印的是全周期数 + 窗口外的条数，
            # 两者相减就是它）。降为次要档，别拿「没印」当 MISS。
            ck("§VII %s 周期数（运行窗口）" % _r, _k["samples"], "sec_discussion.tex", tier="S")
            # 2026-09-25 中立子 agent 重写了这一段：现在引的是【归一化后的份额】、
            # 三个相位中位、以及非零周期占比 —— 都不是「哪个窗口的中位」。
            ck("§VII %s 本档会话数" % _r, _k["n_sessions"], "sec_discussion.tex")
            ck("§VII %s 扣住本档的比例" % _r, "%.0f" % float(_k["pct_of_tier"]), "sec_discussion.tex")
            # 相位中位**不能逐个数字查** —— 21/89/6/18/0 这种个位数正文里到处都是
            # （审计显示 "0" 出现 101 次、检查等于空转）。查正文里那一整句复合串。
            if _r.endswith("foyer_hc") and _25:
                for _lab, _a, _b in (("第一", "median_p10", "median_p10"),
                                     ("第二", "median_mid", "median_mid"),
                                     ("第三", "median_p90", "median_p90")):
                    ck("§VII %s 相位（200 档在前）" % _lab,
                       "%s against %s" % ("%.0f" % float(_k[_a]), "%.0f" % float(_25[_b])),
                       "sec_discussion.tex")
            ck("§VII %s 非零周期占比" % _r, _k["pct_nonzero"], "sec_discussion.tex")
        if (_r, "all") in _bl:
            # 2026-09-25 重写后，正文【不再跨档比队列长度】（两个 trace 不可比，
            # 按本档会话数归一后方向反过来）。全周期那一档留在 CSV 里供复算，正文不印。
            _a = _bl[(_r, "all")]
            for _lab, _val in (("队列中位", "%.0f" % float(_a["waiting_p50"])),
                               ("队列最大", _a["waiting_max"]),
                               ("周期数", _a["samples"])):
                ck("§VII %s %s（全周期）" % (_r, _lab), _val,
                   "sec_discussion.tex", tier="S")

    # ---- §IV 的 HiCache 弹性曲线（首跑）与「换成重复也不改结论」那句 ----
    import math as _m
    _dd = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    _aa = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/arm_running.csv"))}
    def _eps(a0, a1):
        t0 = float(_dd[a0]["step_back_ms"]); t1 = float(_dd[a1]["step_back_ms"])
        r0 = float(_aa[a0]["running_busy"]); r1 = float(_aa[a1]["running_busy"])
        return _m.log(t1 / t0) / _m.log(r1 / r0)
    if {"pairB_cap2hc", "cap3_hc", "cap4_hc"} <= set(_dd) | set(_aa):
        ck("§IV HiCache 首跑段 1", "%.2f" % _eps("pairB_cap2hc", "cap3_hc"), "sec_criterion.tex")
        ck("§IV HiCache 首跑段 2", "%.2f" % _eps("cap3_hc", "cap4_hc"), "sec_criterion.tex")
        ck("§IV HiCache 重复段 1", "%.2f" % _eps("pairB_cap2hc", "cap3_hc_r2"), "sec_criterion.tex")
        ck("§IV HiCache 重复段 2", "%.2f" % _eps("cap3_hc_r2", "cap4_hc_r2"), "sec_criterion.tex")

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
           "cap4_hc", "foyer_hc", "foyer_hz1", "foyer_hz2_r2", "foyer_hz0_r2", "foyer_bres_r2"}
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

    if "--audit" in sys.argv:
        AUDIT.sort(reverse=True)
        print("\n===== 检查强度审计：被检查的值在它被检查的那段正文里出现几次 =====")
        print("（出现次数多 = 检查弱：值可能是在别处撞上的。只列 >=3 次的。）")
        _weak = [(n, d, v) for n, d, v in AUDIT if n >= 3]
        for n, d, v in _weak[:45]:
            print("  %3d 次  %-56s %s" % (n, d, v))
        print("  %d 项检查里，%d 项的值出现 >=3 次" % (len(AUDIT), len(_weak)))

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
