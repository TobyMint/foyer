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
import csv, json, os, statistics, sys

# 同目录下的两个生成器 —— 上界与 busy 占比的**共用定义**（CLAUDE.md 纪律 2）。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_decomp as _GD  # noqa: E402
import gen_reuse as _GR   # noqa: E402

# cap1 是补跑的：预注册判据列了五个 cap，而最初的车道只排了 cap2~cap5，
# 表里会有一行 3090 的 cap1 没有 A100 对应点（codex 第 22 轮指出）。
# 它由 scripts/chain_a100.sh 在当前车道跑完后自动接上。
RUNS = ["a100_cap1", "a100_cap2", "a100_cap3", "a100_cap4", "a100_cap5"]
# 3090 的 device-only 对照点（与主表同族：无 HiCache、同 memfrac、同 trace）
MAIN = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]


def bound(trace_p):
    """上界走 gen_reuse.trace_ceiling —— 与 reuse.csv 的 bound_tok 是同一个函数，
    不在这里重写一遍（重写就会有一天两边分叉）。"""
    ce = _GR.trace_ceiling(trace_p)
    return ce["ceiling_tok"], ce["prompt_tok"]


def one(d):
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    subs = [s["submit_timestamp"] for s in st if s.get("submit_timestamp")]
    comps = [s["complete_timestamp"] for s in st if s.get("complete_timestamp")]
    wall = (max(comps) - min(subs)) / 60.0

    rd = list(csv.DictReader(open(os.path.join(d, "metrics.csv"))))
    occ = [float(x["sglang:token_usage"]) for x in rd if x.get("sglang:token_usage")]
    tokens = sum(s.get("output_len_actual") or 0 for s in st)

    # busy 占比 / R̄_busy / τ₁ 一律走 gen_decomp.busy_stats —— 与 decomp.csv 同一个函数。
    # 原来这里是「数非零采样 / 总采样」，等于假定采样间隔严格均匀；
    # 与 gen_decomp 的区间积分在 cap1 上差 0.002（0.998027 对 1.000000）。
    _sp, _bu, _id, _pc, _ra, running_busy, tau1 = _GD.busy_stats(
        _GD.read_metrics(os.path.join(d, "metrics.csv")), tokens)
    tau1 = tau1 or 0.0

    durs = []
    for s in st:
        o = s.get("output_len_actual") or 0
        if o < 32 or s.get("first_token_ms") is None or s.get("total_duration_ms") is None:
            continue
        durs.append((s["total_duration_ms"] - s["first_token_ms"]) / (o - 1))
    tau2 = statistics.median(durs) if durs else 0.0

    prompt = sum(s.get("prompt_len") or 0 for s in st)
    unc = sum(s.get("server_uncached_prompt_tokens") or 0 for s in st)
    slo = 100.0 * sum(1 for s in st
                      if s.get("first_token_ms") is not None and s["first_token_ms"] < 10000) / len(st)
    m = {}
    mp = os.path.join(d, "metadata.json")
    if os.path.exists(mp):
        m = json.load(open(mp))
    return dict(steps=len(st), wall_min="%.1f" % wall,
                pool_tokens=m.get("pool_tokens") or 0,
                Rbar_busy="%.6f" % running_busy,
                occ_p50_pct="%.1f" % (100 * statistics.median(occ) if occ else 0),
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
        out["verdict"] = (("支持（全程高于 50%%，且 max R̄ %.4f >= 3090 的 %.4f）" % (mx, base))
                          if mx >= base else
                          ("在 R̄ <= %.4f 内未观察到塌点 —— **不能判成支持**："
                           "没测到 %.4f 那儿（中立子 agent 第 9 轮补的条件）" % (mx, base)))
    else:
        out["verdict"] = "证伪（全程低于 50%%，比 3090 更彻底）"
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

    with open(out_p, "w", newline="") as f:
        f.write("# lab-A100 第二配置验证 —— gen_a100.py 生成，勿手改\n")
        f.write("# ⚠ 本表【不参与主表前沿】：池子差 9.7 倍，混算包络是错的。\n")
        f.write("# 只回答一个问题：同一个 R̄ 上，池子更大的卡兑现了多少？\n")
        f.write("# 预注册判据见 docs/a100_toolchain_20260925.md（同模型/trace/引擎/memfrac，只改卡）。\n")
        f.write("# 复用上界从 trace 求和 = %d / %d = %.4f\n" % (pre, tot, pre / tot))
        w = csv.DictWriter(f, fieldnames=["run", "machine", "steps", "wall_min", "pool_tokens",
                                          "Rbar_busy", "occ_p50_pct", "tau1_ms", "tau2_ms",
                                          "slo_pct", "prompt_tok", "reuse_tok", "reuse_frac",
                                          "bound_frac", "realized_frac"])
        f.write("# 兑现率 = reuse_tok / 上界（%d）—— 上界调 gen_reuse.trace_ceiling，\n" % pre)
        f.write("# R̄busy / τ₁ 调 gen_decomp.busy_stats，两个都是共用定义（CLAUDE.md 纪律 2）。\n")
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
    if missing:
        print("!! 未写入（缺 summary.json）：")
        for m in missing:
            print("   " + m)

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
