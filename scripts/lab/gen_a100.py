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

口径与 gen_reuse.py / gen_decomp.py 逐字一致（复用上界从 trace 直接求和、
兑现率 = 实测复用 / 上界、R̄_busy = 全时段均值 / busy 占比）。

用法: python3 gen_a100.py <trace.csv> <a100_results_dir> <main_results_dir> <out.csv> [run ...]
"""
import csv, json, os, statistics, sys

RUNS = ["a100_cap2", "a100_cap3", "a100_cap4", "a100_cap5"]
# 3090 的 device-only 对照点（与主表同族：无 HiCache、同 memfrac、同 trace）
MAIN = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]


def bound(trace_p):
    rows = list(csv.DictReader(open(trace_p)))
    pre = sum(int(r["prefix_len"]) for r in rows)
    tot = sum(int(r["prefix_len"]) + int(r["input_len"]) for r in rows)
    return pre, tot


def one(d):
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    subs = [s["submit_timestamp"] for s in st if s.get("submit_timestamp")]
    comps = [s["complete_timestamp"] for s in st if s.get("complete_timestamp")]
    wall = (max(comps) - min(subs)) / 60.0

    rd = list(csv.DictReader(open(os.path.join(d, "metrics.csv"))))
    rn = [float(x["sglang:num_running_reqs"]) for x in rd if x.get("sglang:num_running_reqs")]
    occ = [float(x["sglang:token_usage"]) for x in rd if x.get("sglang:token_usage")]
    busy_frac = sum(1 for v in rn if v > 0) / len(rn) if rn else 0.0
    running_busy = (statistics.mean(rn) / busy_frac) if busy_frac else 0.0

    ts = [float(x["ts"]) for x in rd if x.get("ts")]
    span_min = (max(ts) - min(ts)) / 60.0 if ts else 0.0
    busy_min = span_min - sum(1 for v in rn if v == 0) * 5.0 / 60.0
    tokens = sum(s.get("output_len_actual") or 0 for s in st)
    tau1 = busy_min * 60.0 * running_busy / tokens * 1000.0 if tokens else 0.0

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
        if not os.path.exists(os.path.join(d, "summary.json")):
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
        f.write("# 兑现率 = reuse_tok / 上界（%d），口径与 gen_reuse.py 逐字一致\n" % pre)
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
        print("!! A100 上还没跑完（未写入）：" + " ".join(missing))


if __name__ == "__main__":
    main()
