#!/usr/bin/env python3
"""被【重跑替代】的旧测量：重跑前后逐列对照 —— paper/data/superseded.csv。

为什么要有这张表：2026-09-25 把 `foyer_bres` 换成 `foyer_bres_r2` 之后，
正文 §discussion 用「同一条臂污染时复用 0.6943、干净时 0.6904」来证明
**体积列看不出污染**。但旧的那一行已经从 `reuse.csv` / `eviction.csv` 里被替换掉了
（`SUPERSEDED` 名单把旧名排除在集合外），**0.6943 在 `paper/data/` 里再也查不到** ——
违反本项目「论文里每个数字都要能追到 CSV / 代码 / 日志」这条纪律
（2026-09-25 子 agent 第 7 轮抓到）。

这张表把每一对（旧、新）在同一套口径下的关键列并排放出来，让那句论证可追。
**必须在实验机上跑吗**：不必 —— 它逐 run 读原始日志，不对 run 集合计数。
但旧 run 的目录本地镜像里得有（`foyer_bres` 在）。

用法: python3 gen_superseded.py <results_dir> <out.csv>
"""
import csv, json, os, statistics, sys

# 被判争用污染、已由同名 + _r2 替代的旧测量。与 gen_eviction.py / gen_repeat_spread.py
# 的 SUPERSEDED 同一份名单；这里额外记录【为什么】以及替代它的新 run。
PAIRS = [
    ("foyer_bres", "foyer_bres_r2",
     "同机 >=4 条车道 >=60 分钟，τ₂ 被抬到 31.3ms（干净值 24.8）"),
]

FIELDS = ["run", "role", "wall_min", "slo_pct", "occ_p50_pct", "occ_mean_pct",
          "running_busy", "tau1_ms", "tau2_ms", "reuse_tok", "prompt_tok",
          "reuse_frac", "note"]


def one(d):
    """与 gen_decomp.py / gen_occupancy.py 同一套口径 —— 不另写一份实现：
    wall = max(complete) − min(submit)；占用取 sglang:token_usage 的比例中位；
    R̄_busy = 全时段均值 / busy 占比；τ₁ = busy_min·R̄busy/tokens；τ₂ = 逐请求 decode 间隔中位。
    """
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    subs = [s["submit_timestamp"] for s in st if s.get("submit_timestamp")]
    comps = [s["complete_timestamp"] for s in st if s.get("complete_timestamp")]
    wall = (max(comps) - min(subs)) / 60.0

    rd = list(csv.DictReader(open(os.path.join(d, "metrics.csv"))))
    rn = [float(x["sglang:num_running_reqs"]) for x in rd if x.get("sglang:num_running_reqs")]
    occ = [float(x["sglang:token_usage"]) for x in rd if x.get("sglang:token_usage")]
    busy_frac = sum(1 for v in rn if v > 0) / len(rn) if rn else 0.0
    running_all = statistics.mean(rn) if rn else 0.0
    running_busy = running_all / busy_frac if busy_frac else 0.0

    ts = [x["ts"] for x in rd if x.get("ts")]
    span_min = (max(float(t) for t in ts) - min(float(t) for t in ts)) / 60.0 if ts else 0.0
    idle_min = sum(1 for v in rn if v == 0) * 5.0 / 60.0
    busy_min = span_min - idle_min

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
    return dict(wall_min="%.1f" % wall, slo_pct="%.1f" % slo,
                occ_p50_pct="%.1f" % (100 * statistics.median(occ) if occ else 0),
                occ_mean_pct="%.1f" % (100 * statistics.mean(occ) if occ else 0),
                running_busy="%.4f" % running_busy, tau1_ms="%.1f" % tau1,
                tau2_ms="%.1f" % tau2, reuse_tok=prompt - unc, prompt_tok=prompt,
                reuse_frac="%.4f" % ((prompt - unc) / prompt if prompt else 0))


def main():
    root, out = sys.argv[1], sys.argv[2]
    rows = []
    for old, new, why in PAIRS:
        for run, role in ((old, "superseded"), (new, "replacement")):
            d = os.path.join(root, "pois200_" + run)
            if not os.path.isdir(d):
                raise SystemExit("!! 缺目录 %s —— 这张表的全部意义就是这两条并排，"
                                 "少一条就别写文件" % d)
            r = dict(run=run, role=role, note=why if role == "superseded" else "")
            r.update(one(d))
            rows.append(r)

    with open(out, "w", newline="") as f:
        f.write("# 被重跑替代的旧测量：重跑前后逐列对照 —— gen_superseded.py 生成，勿手改\n")
        f.write("# 用途：正文 §discussion 的「体积列看不出污染」那句，引的就是这张表的\n")
        f.write("#   reuse_frac 两行（旧 0.6943 / 新 0.6904）与 tau2_ms（31.3 / 24.8）。\n")
        f.write("# 口径与 gen_decomp.py / gen_occupancy.py 逐字一致（同一套定义，不另写实现）。\n")
        f.write("# 旧 run 已被 gen_eviction.py / gen_repeat_spread.py 的 SUPERSEDED 排除在\n")
        f.write("#   各自集合外，所以这几列在 reuse.csv / eviction.csv 里查不到 —— 这里补上。\n")
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("写入 %s：%d 行" % (out, len(rows)))
    for r in rows:
        print("  %-16s %-12s 墙钟 %s  τ₂ %s  复用占比 %s  占用 %s%%" % (
            r["run"], r["role"], r["wall_min"], r["tau2_ms"], r["reuse_frac"], r["occ_p50_pct"]))


if __name__ == "__main__":
    main()
