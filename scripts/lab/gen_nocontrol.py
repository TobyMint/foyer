#!/usr/bin/env python3
"""无准入控制基线的数 —— 论文明引了三个数但原来没有来源文件。

子 agent 第二轮指出：TTFT 中位 1774 s、命中率 1.6%、以及 Related Work 的
80.6/80.8/78.5 在 paper/data/ 里都追不到。CLAUDE.md 的「每个数字都要能追到」
对这几个数当时是不成立的。

用法: python3 gen_nocontrol.py <results_dir> <out.csv>
"""
import csv, json, os, statistics, sys

RUNS = ["default", "foyer_hc", "cap4_hc", "foyer_hz1", "cap2"]


def hit(run, root):
    """计划/实测前缀命中率，四种口径都给，免得再出现「同一条 trace 两个数」。"""
    p = os.path.join(root, "pois200_" + run, "steps.jsonl")
    if not os.path.exists(p):
        return {}
    st = [json.loads(l) for l in open(p) if l.strip()]
    def sel(rows):
        return [s for s in rows if s.get("planned_prefix_hit_rate") is not None]
    def aw(rows):
        v = [s["planned_prefix_hit_rate"] for s in rows]
        return 100 * statistics.mean(v) if v else None
    def wt(rows):
        num = sum(s["planned_prefix_hit_rate"] * (s.get("prefix_len") or 0) for s in rows)
        den = sum((s.get("prefix_len") or 0) for s in rows)
        return 100 * num / den if den else None
    a, r1 = sel(st), sel([s for s in st if s["round_idx"] >= 1])
    return {"plan_all_mean": aw(a), "plan_all_tok": wt(a),
            "plan_r1_mean": aw(r1), "plan_r1_tok": wt(r1)}


def main():
    root, out = sys.argv[1], sys.argv[2]
    rows = []
    print("%-10s %10s %10s %10s %10s" % ("run", "TTFT中位s", "TTFT p90s", "SLO%", "计划命中(r1均值)%"))
    for r in RUNS:
        p = os.path.join(root, "pois200_" + r, "steps.jsonl")
        if not os.path.exists(p):
            continue
        st = [json.loads(l) for l in open(p) if l.strip()]
        tt = sorted(s["first_token_ms"] for s in st if s.get("first_token_ms") is not None)
        if not tt:
            continue
        h = hit(r, root)
        rows.append({
            "run": r, "n_steps": len(st),
            "ttft_p50_s": round(tt[len(tt) // 2] / 1000, 1),
            "ttft_p90_s": round(tt[int(.9 * len(tt))] / 1000, 1),
            "slo_pct": round(100 * sum(1 for x in tt if x < 10000) / len(tt), 1),
            **{k: (round(v, 2) if v else "") for k, v in h.items()},
        })
        print("%-10s %10.1f %10.1f %10.1f %10.1f" % (
            r, rows[-1]["ttft_p50_s"], rows[-1]["ttft_p90_s"], rows[-1]["slo_pct"],
            h.get("plan_r1_mean") or 0))
    with open(out, "w", newline="") as f:
        f.write("# 无准入控制基线 + 命中率的四种口径 —— 由 scripts/lab/gen_nocontrol.py 生成\n")
        f.write("# ttft_p50_s/p90_s: 引擎侧 first_token_ms 的分位（不含等 permit）\n")
        f.write("# plan_*: 四种口径。论文 §Related Work 用 plan_r1_mean；\n")
        f.write("#         无控制那段的 75.5% 是 runner 自己报的全步口径，与此不同\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("->", out)


if __name__ == "__main__":
    main()
