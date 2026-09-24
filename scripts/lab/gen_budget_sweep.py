#!/usr/bin/env python3
"""预算分数（Route 3「硬天花板」）两条臂的实测值 —— paper/data/budget_sweep.csv。

§V 的 Route 3 写「降低预算分数是最粗的旋钮，行为与其他路线一样：把工作点沿前沿滑动」，
但**没有任何数据文件承载这句话** —— `t85`/`t90` 两条 run 不在表 I 里
（它们是早期扫描、与表 I 的其他行不同代），正文也没印它们的数。
这个脚本把 frontier.py 算出来的墙钟/SLO/Δ 落盘，让那句断言可核对。

用法: python3 gen_budget_sweep.py <results_dir> <out.csv>
"""
import csv, os, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
# 两条臂：budget3:hw=0;target=0.85 / 0.90（表 I 的 base 是 target=0.95）
RUNS = [("foyer_t85", "0.85"), ("foyer_t90", "0.90")]


def front_mod():
    spec = importlib.util.spec_from_file_location("_fr_bs", os.path.join(HERE, "frontier.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def main():
    root, out_p = sys.argv[1], sys.argv[2]
    FR = front_mod()
    FR.RESULTS = os.path.abspath(root)
    rows = []
    print("%-12s %9s %8s %8s %9s" % ("run", "墙钟min", "SLO%", "前沿SLO", "Δ(pp)"))
    for run, target in RUNS:
        d = FR.summarise("pois200_" + run)
        if not d:
            raise SystemExit("!! %s 读不到 —— 缺 run 不静默跳过" % run)
        f = FR.front_slo(d["wall"])
        if f is None:
            raise SystemExit("!! %s 落在锚点范围外，无法给 Δ" % run)
        rows.append(dict(run=run, target=target, steps=d["steps"],
                         wall_min="%.4f" % d["wall"], slo_pct="%.4f" % d["slo"],
                         front_slo="%.4f" % f, delta_pp="%.4f" % (d["slo"] - f)))
        print("%-12s %9.1f %8.1f %8.1f %+9.2f" % (
            run, d["wall"], d["slo"], f, d["slo"] - f))
    hdr = ["# Route 3（硬天花板 / 预算分数）的两条臂 —— 由 scripts/lab/gen_budget_sweep.py 生成",
           "# Δ 用 frontier.py 的同一套锚点与插值（不另写判据）；±1.0pp 是打平带。",
           "# 这两条不在表 I 里：它们是早期扫描，与表 I 的行不同代（表 I 的标题已说明）。",
           "run,target,steps,wall_min,slo_pct,front_slo,delta_pp"]
    body = "\n".join(hdr) + "\n" + "\n".join(
        "%s,%s,%d,%s,%s,%s,%s" % (r["run"], r["target"], r["steps"], r["wall_min"],
                                  r["slo_pct"], r["front_slo"], r["delta_pp"]) for r in rows) + "\n"
    assert isinstance(body, str)
    with open(out_p, "w") as f:
        f.write(body)
    print("-> %s（%d 行）" % (out_p, len(rows)))


if __name__ == "__main__":
    main()
