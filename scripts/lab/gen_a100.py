#!/usr/bin/env python3
"""lab-A100 第二配置验证 —— paper/data/a100.csv。

**这张表不参与主表的前沿。** 池子差 9.7 倍（983,728 vs 101,432），把它混进主 trace
的静态点里算包络是错的。它只回答一个问题：

    **同一个 R̄ 上，池子更大的卡兑现了多少？**

预注册判据（`docs/a100_toolchain_20260925.md`，看结果前定死）：
  3090 device-only 的兑现率：cap1 92.5% / cap2 89.7% / cap3 79.0% / cap4 60.7% / cap5 36.4%
  （R̄_busy 1.00 → 1.84）。若「兑现率由容量定」，A100 上同一批 cap 在同一 R̄ 上
  应兑现明显更高（预期 >=85%），塌点被推到更高 R̄。
  **若 A100 在同样 R̄ 上塌到同样水平，「容量定塌点」被证伪。两种结果都照实写。**

口径**共用定义，不另写一份**（CLAUDE.md 纪律 2）：
  - 上界           → import gen_reuse.trace_ceiling（与 reuse.csv 同一个函数）
  - busy 占比 / R̄  → import gen_decomp.busy_stats（区间积分口径，与 decomp.csv 同一份）
  - 兑现率         = 实测复用 / 上界
2026-09-25 codex 第 21 轮指出：原来这三样都是本脚本自己重写的，而 docstring 写着
「逐字一致」—— 兑现率那一项恰好对得上，busy 占比那一项对不上（cap1 0.998027 对 1.000000）。

用法: python3 gen_a100.py <trace.csv> <a100_results_dir> <main_results_dir> <out.csv> [run ...]
"""
import csv, json, math, os, statistics, sys

# 同目录下的两个生成器 —— 上界与 busy 占比的**共用定义**（CLAUDE.md 纪律 2）。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_decomp as _GD  # noqa: E402
import gen_reuse as _GR   # noqa: E402

# cap1 是补跑的：预注册判据列了五个 cap，而最初的车道只排了 cap2~cap5，
# 表里会有一行 3090 的 cap1 没有 A100 对应点（codex 第 22 轮指出）。
# 它由 scripts/chain_a100.sh 在当前车道跑完后自动接上。
# ⚠ 深扫的两条（`a100_cap8` / `a100_cap16`）在 2026-09-26 补上 —— 它们补的是
# **前沿的右半段**：静态墙钟随 cap 单调下降（cap3 136.5 → cap4 110.7 → cap5 96.4），
# 扫描停在 cap5 时「最快的静态点」只是**扫描的端点**，不是前沿。
# 它们的池子可能不是 983{,}728（共享卡，SGLang 按启动时的空闲显存定池子）——
# 表里记实际值，正文照实披露（与 a100_cap1 的 971,456 同类）。
RUNS = ["a100_cap1", "a100_cap2", "a100_cap3", "a100_cap4", "a100_cap5",
        "a100_cap8", "a100_cap16"]
# 3090 的 device-only 对照点（与主表同族：无 HiCache、同 memfrac、同 trace）
MAIN = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]


def bound(trace_p):
    """上界走 gen_reuse.trace_ceiling —— 与 reuse.csv 的 bound_tok 是同一个函数，
    不在这里重写一遍（重写就会有一天两边分叉）。"""
    ce = _GR.trace_ceiling(trace_p)
    return ce["ceiling_tok"], ce["prompt_tok"]


def occ_stats(d):
    """池占用的两个统计量（%）：(中位, 均值)。

    **唯一的实现**，`one()` 与 `gen_tierpair.py` 都用它 —— 后者要拿占用率做
    配对实验的「受控」前提，而预注册文件举的旧配对例子（55.8\\%/55.5\\%）用的是
    **均值**，`one()` 报的 `occ_p50_pct` 是**中位**。两个统计量可能给出不同的
    前提判决，所以两个都算出来、都判（2026-09-26 codex 第 30 轮抓到）。
    """
    rd = list(csv.DictReader(open(os.path.join(d, "metrics.csv"))))
    occ = [float(x["sglang:token_usage"]) for x in rd if x.get("sglang:token_usage")]
    if not occ:
        return 0.0, 0.0
    return 100 * statistics.median(occ), 100 * sum(occ) / len(occ)


def wall_slo_of(st):
    """(墙钟分钟, SLO%) —— **唯一的实现**。

    2026-09-26 抽出来：`gen_a100_baseline.py` 也要这一对量，而它当时**各写了一份**
    （同文件里 τ₂/占用已经走 import，墙钟/SLO 没走 —— 「抽成共用只做了一半」）。
    口径：墙钟 = 最后一个 complete − 第一个 submit，单位秒（`complete_timestamp`
    是 **epoch 秒的浮点**，不是毫秒）；SLO = 首 token < 10 s 的步占比。
    """
    subs = [x["submit_timestamp"] for x in st if x.get("submit_timestamp")]
    comps = [x["complete_timestamp"] for x in st if x.get("complete_timestamp")]
    if not subs or not comps:
        return None, None
    wall = (max(comps) - min(subs)) / 60.0
    slo = 100.0 * sum(1 for x in st
                      if x.get("first_token_ms") is not None
                      and x["first_token_ms"] < 10000) / len(st)
    return wall, slo


def tau2_of(st):
    """逐请求 decode 间隔的中位（ms）—— **唯一的实现**。

    2026-09-26 抽出来：`gen_a100_baseline.py` 也要这个量，重写一份就会有一天两边
    分叉（CLAUDE.md「口径一致不能写在注释里，要写在 import 里」）。
    样本判据：有首 token、有总时长、且输出 >= 32 token（太短的除不出稳定的斜率）。
    """
    durs = []
    for s in st:
        o = s.get("output_len_actual") or 0
        if o < 32 or s.get("first_token_ms") is None or s.get("total_duration_ms") is None:
            continue
        durs.append((s["total_duration_ms"] - s["first_token_ms"]) / (o - 1))
    return statistics.median(durs) if durs else 0.0


def one(d):
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    wall, slo = wall_slo_of(st)

    _occ_p50, _occ_mean = occ_stats(d)
    tokens = sum(s.get("output_len_actual") or 0 for s in st)

    # busy 占比 / R̄_busy / τ₁ 一律走 gen_decomp.busy_stats —— 与 decomp.csv 同一个函数。
    # 原来这里是「数非零采样 / 总采样」，等于假定采样间隔严格均匀；
    # 与 gen_decomp 的区间积分在 cap1 上差 0.002（0.998027 对 1.000000）。
    _sp, _bu, _id, _pc, _ra, running_busy, tau1 = _GD.busy_stats(
        _GD.read_metrics(os.path.join(d, "metrics.csv")), tokens)
    tau1 = tau1 or 0.0

    tau2 = tau2_of(st)

    prompt = sum(s.get("prompt_len") or 0 for s in st)
    unc = sum(s.get("server_uncached_prompt_tokens") or 0 for s in st)
    # ⚠⚠ **必须先断言「每一步都真的被服务了」，否则 reuse = prompt - uncached 是假的。**
    # 2026-09-25 独立复算抓到：`pois200_cap2_hp`（半池）有 **104/999 步**被引擎服务成
    # **1-token 退化响应**（`server_prompt_tokens=1`、`first_token_ms=None`、
    # `finish_reason=None`、**`error=None`**，runner 记成 SUCCESS），它们的**计划 prompt
    # 整块**（6,515,669 tokens，占缺口 100.00%）没进实测和，于是被上式算成了「复用」——
    # 兑现率虚报成 87.12%，而引擎自报的命中只有 56.88%。**差 30 个百分点，进了正文。**
    # 同一条路径也放过「有失败步」的 run（失败步 server_prompt_tokens=None）：
    # `pois200_foyer_hz2` 2 步 -> 虚报 60,314（0.28 pp），`budget200c_default` 121 步 -> 4.76M。
    # 干净的 run 计划==实测，看不出问题 —— 这正是它活了这么久的原因。
    # **判据来自 `gen_eviction.py:171-187`**（那里早就写明「prompt 必须与 uncached 同源」
    # 并断言了 `prompt_tokens_total == 计划 prefill`）；本函数此前**各写了一份**。
    meas = sum(s.get("server_prompt_tokens") or 0 for s in st)
    if meas != prompt:
        raise SystemExit(
            "!! %s：计划 prompt %d != 实测 prompt %d（缺口 %d，%.2f%%）—— 有步骤没被真正服务，"
            "`prompt - uncached` 会把缺口算成复用。兑现率不可用，别拿它写表。"
            % (os.path.basename(os.path.normpath(d)), prompt, meas, prompt - meas,
               100.0 * (prompt - meas) / prompt))
    m = {}
    mp = os.path.join(d, "metadata.json")
    if os.path.exists(mp):
        m = json.load(open(mp))
    return dict(steps=len(st), wall_min="%.1f" % wall,
                pool_tokens=m.get("pool_tokens") or 0,
                Rbar_busy="%.6f" % running_busy,
                occ_p50_pct="%.1f" % _occ_p50,
                occ_mean_pct="%.1f" % _occ_mean,
                tau1_ms="%.1f" % tau1, tau2_ms="%.1f" % tau2,
                slo_pct="%.1f" % slo,
                prompt_tok=prompt, reuse_tok=prompt - unc,
                reuse_frac="%.4f" % ((prompt - unc) / prompt if prompt else 0))


def crossing(points):
    """兑现率【穿过 50%】时的 R̄ —— 分段线性插值。points = [(Rbar, realized_pct), ...] 按 R̄ 升序。

    这是 A100 判据的**唯一判决轴**（docs/prereg_a100_addendum_20260925.md 第一节）。
    只在相邻两点跨越 50% 时给值；全程高于 50% 或全程低于 50% 都返回 None，
    两种情况由 verdict() 分开处理（前者是支持、后者是证伪，不能混）。
    """
    pts = sorted(points)
    for (r0, y0), (r1, y1) in zip(pts, pts[1:]):
        if (y0 - 50.0) * (y1 - 50.0) <= 0 and y0 != y1:
            return r0 + (50.0 - y0) / (y1 - y0) * (r1 - r0)
    return None


def verdict(a100_pts, main_csv):
    """按预注册补丁给判决。**判据写在代码里，不由人读表得出**（CLAUDE.md 纪律 4）。

    3090 的交叉点从 reuse.csv 的 device-only 五点算（只算一次，作为常数对照），
    A100 的从它自己的曲线算。判决表：
      A100 交叉点 > 3090 交叉点            -> 支持
      A100 交叉点 <= 3090 交叉点           -> 证伪
      全程没到过 50% 以下 且 max R̄ >= 3090 交叉点 -> 支持（且必须满足那个 R̄ 条件）
      全程没到过 50% 以上（即一直低于 50%）-> 证伪（更彻底的塌陷）
      其余（没跨过、又没测到那个 R̄）      -> 「在 R̄ <= X 内未观察到塌点」
    """
    dev = []
    with open(main_csv) as f:
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            if r["family"] == "device_only":
                dev.append((float(r["Rbar_busy"]), float(r["realized_frac"]) * 100))
    base = crossing(dev)
    out = {"base_crossing": base, "a100_crossing": None, "verdict": ""}
    if not a100_pts or base is None:
        out["verdict"] = "A100 数据还没落地（或缺 3090 对照），不判决"
        return out
    a = crossing(a100_pts)
    out["a100_crossing"] = a
    lo = min(y for _, y in a100_pts)
    hi = max(y for _, y in a100_pts)
    mx = max(r for r, _ in a100_pts)
    if a is not None:
        out["verdict"] = ("支持（A100 交叉点 %.4f > 3090 的 %.4f）" % (a, base) if a > base
                          else "证伪（A100 交叉点 %.4f <= 3090 的 %.4f）" % (a, base))
    elif lo > 50.0:
        # 「全程高于 50%」这一支**才**需要数据充分性守卫。
        # 2026-09-25 codex 第 24 轮指出：守卫原来加在最外层，于是**抢在预注册的
        # 交叉点规则前面**返回「数据不足」—— 例如 (1.8, 80) 与 (2.2, 40) 两点
        # 已经插出 A100 交叉点 2.1 > 1.7344，按预注册应当判「支持」，却被拦下。
        # **那等于改了判据的含义**，而我明说过判据一个字不改。已挪进这一支。
        if not any(r <= base for r, _ in a100_pts):
            out["verdict"] = ("**数据不足，不判决**：A100 的 %d 个点全部落在 R̄ > %.4f，"
                              "而「全程高于 50%%」这一支要求至少一个点落在交叉点【以下】"
                              "的区间里 —— 否则该条件是**空真**，不是证据。"
                              % (len(a100_pts), base))
            return out
        out["verdict"] = (("支持（全程高于 50%%，且 max R̄ %.4f >= 3090 的 %.4f）" % (mx, base))
                          if mx >= base else
                          ("在 R̄ <= %.4f 内未观察到塌点 —— **不能判成支持**："
                           "没测到 %.4f 那儿（中立子 agent 第 9 轮补的条件）" % (mx, base)))
    else:
        out["verdict"] = "证伪（全程低于 50%%，比 3090 更彻底）"
    return out


def eps_segments(rows, machine):
    """分段弹性 eps = dln tau1 / dln Rbar —— 与 paper/data/elasticity_hc.csv 同口径。

    **Rbar 必须圆到 2 位**：elasticity_hc.csv 的 Rbar 来自 decomp.csv 的 running 列，
    那一列本身就是 2 位小数。不圆的话同一段在两表里会差 0.03
    （cap3_fixed->cap4：1.534018->1.650488 算 +1.189，1.53->1.65 算 +1.152），
    而正文印的是后者。**口径一致优先于「多几位更准」。**
    """
    pts = sorted((round(float(r["Rbar_busy"]), 2), float(r["tau1_ms"]), r["run"])
                 for r in rows if r["machine"] == machine)
    out = []
    for (r0, t0, n0), (r1, t1, n1) in zip(pts, pts[1:]):
        if r1 <= r0 or t0 <= 0:
            continue
        out.append(dict(machine=machine, frm=n0, to=n1,
                        r0="%.2f" % r0, r1="%.2f" % r1,
                        tau0_ms="%.1f" % t0, tau1_ms="%.1f" % t1,
                        epsilon="%+.3f" % (math.log(t1 / t0) / math.log(r1 / r0))))
    return out


def main():
    trace_p, a100_root, main_root, out_p = sys.argv[1:5]
    runs = sys.argv[5:] or RUNS
    pre, tot = bound(trace_p)
    rows, missing = [], []
    for r in runs:
        d = os.path.join(a100_root, r)
        if not os.path.exists(os.path.join(d, "summary.json")):
            missing.append(r)
            continue
        x = one(d)
        x.update(run=r, machine="A100-80G", bound_frac="%.4f" % (pre / tot),
                 realized_frac="%.6f" % (x["reuse_tok"] / pre))
        rows.append(x)
    for r in MAIN:
        d = os.path.join(main_root, "pois200_" + r)
        # 缺了要报，不能 continue 了事（CLAUDE.md 纪律 3：生成器的 run 列表不全会静默丢数据）。
        # 2026-09-25 自查发现：A100 那半边会报 missing，3090 这半边却静默跳过 ——
        # 那样对照点少了一条，表还是照印，看的人不知道比的是什么。
        if not os.path.exists(os.path.join(d, "summary.json")):
            missing.append("pois200_" + r + "（3090 对照点）")
            continue
        x = one(d)
        x.update(run=r, machine="3090-24G", bound_frac="%.4f" % (pre / tot),
                 realized_frac="%.6f" % (x["reuse_tok"] / pre))
        rows.append(x)
    rows.sort(key=lambda x: (x["machine"], float(x["Rbar_busy"])))

    if missing:
        # ⚠ **必须退出，不能只打印**。2026-09-26 实际栽过一次：本地镜像缺 A100 五条
        # 静态 run 时，这个脚本把 `paper/data/a100.csv` **静默写残**（丢 5 行、
        # `a100_elasticity.csv` 从 7 段写成 4 段），我是靠「跑前备份 + 跑完 diff」
        # 才发现的。CLAUDE.md 纪律 3：「缺了要报，不能 continue 了事」——
        # **打印一行不算报**，退出码才算。
        raise SystemExit("!! 缺 summary.json，拒写表（CLAUDE.md 纪律 3）：\n   "
                         + "\n   ".join(missing))

    with open(out_p, "w", newline="") as f:
        f.write("# lab-A100 第二配置验证 —— gen_a100.py 生成，勿手改\n")
        f.write("# ⚠ 本表【不参与主表前沿】：池子差 9.7 倍，混算包络是错的。\n")
        f.write("# 只回答一个问题：同一个 R̄ 上，池子更大的卡兑现了多少？\n")
        f.write("# 预注册判据见 docs/a100_toolchain_20260925.md（同模型/trace/引擎/memfrac，只改卡）。\n")
        f.write("# 复用上界从 trace 求和 = %d / %d = %.4f\n" % (pre, tot, pre / tot))
        w = csv.DictWriter(f, fieldnames=["run", "machine", "steps", "wall_min", "pool_tokens",
                                          "Rbar_busy", "occ_p50_pct", "occ_mean_pct",
                                          "tau1_ms", "tau2_ms",
                                          "slo_pct", "prompt_tok", "reuse_tok", "reuse_frac",
                                          "bound_frac", "realized_frac"])
        f.write("# 兑现率 = reuse_tok / 上界（%d）—— 上界调 gen_reuse.trace_ceiling，\n" % pre)
        f.write("# R̄busy / τ₁ 调 gen_decomp.busy_stats，两个都是共用定义（CLAUDE.md 纪律 2）。\n")
        f.write("# occ_p50_pct / occ_mean_pct 都来自 gen_a100.occ_stats（与 occupancy.csv 同一份）。\n")
        f.write("# 3090 那五行的兑现率与 R̄busy 应与 reuse.csv 逐位相同；不同就是口径又分叉了。\n")
        w.writeheader()
        w.writerows(rows)
    print("写入 %s：%d 行（A100 %d 条，3090 对照 %d 条）"
          % (out_p, len(rows), sum(1 for r in rows if r["machine"].startswith("A100")),
             sum(1 for r in rows if r["machine"].startswith("3090"))))
    print("%-12s %-9s %6s %9s %7s %9s %8s" % ("run", "machine", "池", "R̄busy", "占用", "兑现", "τ₂"))
    for r in rows:
        print("%-12s %-9s %6s %9s %7s%% %9s %8s" % (
            r["run"], r["machine"], r["pool_tokens"], r["Rbar_busy"],
            r["occ_p50_pct"], r["realized_frac"][:6], r["tau2_ms"]))
    # ---- 分段弹性（**附加佐证，不是判据**）----
    # 判决只有一条轴：兑现率穿过 50% 的 R̄。这个 ε 是同一量在 A100 上的读数，
    # 用来解释判决，**不许抬成第二条判据**（预注册那一页论证过为什么只留一条）。
    eps = eps_segments(rows, "3090-24G") + eps_segments(rows, "A100-80G")
    if eps:
        e_p = os.path.join(os.path.dirname(os.path.abspath(out_p)), "a100_elasticity.csv")
        with open(e_p, "w", newline="") as f:
            f.write("# 两卡的步成本弹性 eps = dln tau1 / dln Rbar —— gen_a100.py 生成，勿手改\n")
            f.write("# ⚠ 这是【附加佐证】，**不是判据**。判决只有一条轴：兑现率穿过 50% 的 Rbar。\n")
            # 2026-09-25 晚改：A100 上**已经**跑了一条控制器（a100_foyer_hz2），
            # 但它不在本表里 —— 本表只放静态 cap。控制器对 A100 自己前沿的判决
            # 在 paper/data/a100_delta.csv（gen_a100_delta.py），那里连着闸门读数。
            f.write("# ⚠ 本表只放【静态 cap】。A100 上跑的控制器（a100_foyer_hz2）不在此表，\n")
            f.write("#   它的判决与闸门读数在 paper/data/a100_delta.csv（gen_a100_delta.py）。\n")
            f.write("# 口径与 paper/data/elasticity_hc.csv 相同：Rbar 取 2 位小数，tau1 = step_back_ms。\n")
            w2 = csv.DictWriter(f, fieldnames=["machine", "frm", "to", "r0", "r1",
                                               "tau0_ms", "tau1_ms", "epsilon"])
            w2.writeheader(); w2.writerows(eps)
        print("\n分段弹性（附加佐证，非判据）-> %s" % e_p)
        for e in eps:
            print("  %-9s %-11s -> %-11s  Rbar %s->%s  tau1 %s->%s   eps = %s"
                  % (e["machine"], e["frm"], e["to"], e["r0"], e["r1"],
                     e["tau0_ms"], e["tau1_ms"], e["epsilon"]))

    # ---- 预注册判据（判据在代码里，不由人读表得出）----
    ap = [(float(r["Rbar_busy"]), float(r["realized_frac"]) * 100)
          for r in rows if r["machine"].startswith("A100")]
    v = verdict(ap, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "..", "paper", "data", "reuse.csv"))
    print("\n预注册判据（docs/prereg_a100_addendum_20260925.md 第一节，唯一判决轴）")
    print("  3090 的 50%% 交叉点 R̄ = %s" % ("%.4f" % v["base_crossing"] if v["base_crossing"] else "?"))
    print("  A100 的 50%% 交叉点 R̄ = %s" % ("%.4f" % v["a100_crossing"] if v["a100_crossing"] else "（未跨越）"))
    print("  判决：%s" % v["verdict"])


if __name__ == "__main__":
    main()
