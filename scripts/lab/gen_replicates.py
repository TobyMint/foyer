#!/usr/bin/env python3
"""生成 paper/data/replicates.csv —— 同配置重复 run 的离散度。

为什么需要：论文的判决全靠一句「+0.20pp 在 run-to-run 波动内」。没有实测的
重复 run，这句话就是无源之水，审稿人会直接问「你怎么知道 0.2pp 是噪声」。
实验集里确实有重复：cap2+HiCache 跑了两条，Foyer 基线跑了三条。

用法: python3 gen_replicates.py <results_dir> <out.csv>
"""
import csv, glob, json, os, statistics, sys

# 同配置分组。按 run_summary 的 policy 串判的，不是按名字——名字会骗人。
GROUPS = {
    "cap4+HiCache (frontier anchor)": ["cap4_hc", "cap4_hc_r2"],
    "cap2+HiCache (frontier anchor)": ["pairA_cap2hc", "pairB_cap2hc"],
    "Foyer base (hw=0,t=0.95,h=3)": ["pairA_foyerhc", "pairB_foyerhc", "foyer_hc", "foyer_hc_r2"],
    "horizon=1 (the best arm)": ["foyer_hz1", "foyer_hz1_r2"],
    "cap3+HiCache (frontier anchor)": ["cap3_hc", "cap3_hc_r2"],
}


def wall_and_slo(d):
    st = [json.loads(l) for l in open(os.path.join(d, "steps.jsonl")) if l.strip()]
    subs = [s["submit_timestamp"] for s in st if s.get("submit_timestamp")]
    comps = [s["complete_timestamp"] for s in st if s.get("complete_timestamp")]
    tt = [s["first_token_ms"] for s in st if s.get("first_token_ms") is not None]
    if not subs or not comps or not tt:
        return None
    wall = (max(comps) - min(subs)) / 60.0
    slo = 100.0 * sum(1 for t in tt if t < 10000) / len(tt)
    return wall, slo, len(st)


def main():
    root, out = sys.argv[1], sys.argv[2]
    rows = []
    print("%-30s %8s %8s %8s   %s" % ("group", "n", "wall_sd", "wall_cv%", "各次墙钟"))
    for name, runs in GROUPS.items():
        vals = []
        for r in runs:
            d = os.path.join(root, "pois200_" + r)
            if not os.path.isdir(d):
                print("  !! 缺 %s" % r); continue
            res = wall_and_slo(d)
            if not res:
                print("  !! %s 读不出时间戳" % r); continue
            w, s, n = res
            vals.append((r, w, s, n))
        if len(vals) < 2:
            continue
        ws = [v[1] for v in vals]
        ss = [v[2] for v in vals]
        sd = statistics.pstdev(ws)
        cv = 100 * sd / statistics.mean(ws)
        sd_slo = statistics.pstdev(ss)
        print("%-30s %8d %8.2f %8.2f   %s" % (
            name, len(vals), sd, cv, " ".join("%.1f" % w for w in ws)))
        rows.append({
            "group": name, "n": len(vals),
            "wall_min_mean": round(statistics.mean(ws), 1),
            "wall_min_sd": round(sd, 2),
            "wall_cv_pct": round(cv, 2),
            "wall_range_pct": round(100 * (max(ws) - min(ws)) / statistics.mean(ws), 2),
            "slo_mean": round(statistics.mean(ss), 1),
            "slo_sd_pp": round(sd_slo, 2),
            "slo_range_pp": round(max(ss) - min(ss), 2),
            "runs": " ".join(v[0] for v in vals),
        })
    with open(out, "w", newline="") as f:
        f.write("# 同配置重复 run 的离散度 —— 由 scripts/lab/gen_replicates.py 生成\n")
        f.write("# 论文里「+0.20pp 在 run-to-run 波动内」这句就靠这张表\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("->", out)


if __name__ == "__main__":
    main()
