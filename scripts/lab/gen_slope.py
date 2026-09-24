#!/usr/bin/env python3
"""兑现率的逐段斜率 —— paper/data/slope.csv（论文 §VI 的头条数字来源）。

§VI 的核心对比是「两条 trace 的坍塌形状不同」：
  realhr    -31.3  -36.6  -28.4        基本恒定 —— R̄ 1.41 时还没到悬崖
  主 trace  -10.8  -41.0  -157.4  -126.7    R̄ 1.53 后斜率爆炸
这五个数是论文里第一次出现"斜率"这个口径，此前是当场算的、不在任何 CSV 里。

斜率定义：相邻两点的兑现率之差 / 运行数之差，单位是「百分点每单位 R̄」。

用法: python3 gen_slope.py <reuse.csv> <reuse_x.csv> <out.csv>
"""
import csv, sys


def load(p):
    return [r for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))]


def main():
    src = [(("main", r["run"]), float(r["Rbar_busy"]), float(r["realized_frac"]))
           for r in load(sys.argv[1]) if r["family"] == "device_only"]
    # 只取【静态点】——控制器臂不参与前沿/序列，混进来会把两段连成一段
    # （第一版没滤，把 realhr_foyer 也算进去，于是 realhr 变成 3 段而不是 4 段）
    src += [(("xtrace", r["run"]), float(r["Rbar_busy"]), float(r["realized_frac"]))
            for r in load(sys.argv[2]) if "_cap" in r["run"]]
    by = {}
    for (tr, run), r, f in src:
        by.setdefault(tr, []).append((r, f, run))
    rows = []
    for tr, pts in by.items():
        pts.sort()
        for (r0, f0, n0), (r1, f1, n1) in zip(pts, pts[1:]):
            rows.append({
                "trace": tr, "from_run": n0, "to_run": n1,
                "r0": "%.3f" % r0, "r1": "%.3f" % r1,
                "realized0_pct": "%.1f" % (f0 * 100), "realized1_pct": "%.1f" % (f1 * 100),
                "slope_pp_per_unit": "%.1f" % ((f1 - f0) * 100 / (r1 - r0)),
            })
    # 全范围斜率单独出两行：正文用它与另一条 trace 比"整体陡不陡"。
    # ⚠ 必须全范围对全范围 —— 曾经拿 realhr 的【三点】斜率(-34.5)去比主 trace 的
    # 全范围(-66.8)，区间不可比，而且 realhr 自己的全范围其实是 -32.3。
    for tr, pts in by.items():
        pts.sort()
        r0, f0, n0 = pts[0]; r1, f1, n1 = pts[-1]
        rows.append({"trace": tr, "from_run": n0, "to_run": n1,
                     "r0": "%.3f" % r0, "r1": "%.3f" % r1,
                     "realized0_pct": "%.1f" % (f0 * 100),
                     "realized1_pct": "%.1f" % (f1 * 100),
                     "slope_pp_per_unit": "%.2f" % ((f1 - f0) * 100 / (r1 - r0))})
    rows.sort(key=lambda x: (x["trace"], float(x["r0"]), float(x["r1"])))
    header = "\n".join([
        "# 兑现率的逐段斜率 —— 由 scripts/lab/gen_slope.py 生成，勿手改",
        "# slope = Δrealized / ΔR̄，单位「百分点每单位忙时在跑数」",
        "# 用途：§VI 说两条 trace 的【形状】不同 —— 主 trace 是阈值（悬崖），",
        "#   xtrace 在同一段跨度内斜率基本恒定、还没到悬崖。",
        "# 每组的【最后一行】是该 trace 的全范围斜率（正文比整体陡不陡必须用这两行，",
        "# 不能拿一条的三点斜率去比另一条的全范围 —— 2026-09-24 犯过）。",
        "trace,from_run,to_run,r0,r1,realized0_pct,realized1_pct,slope_pp_per_unit"])
    fields = ["trace", "from_run", "to_run", "r0", "r1", "realized0_pct",
              "realized1_pct", "slope_pp_per_unit"]
    body = header + "\n" + "\n".join(",".join(str(x[k]) for k in fields) for x in rows) + "\n"
    assert isinstance(body, str)
    with open(sys.argv[3], "w") as fh:
        fh.write(body)
    print("写入 %s：%d 行" % (sys.argv[3], len(rows)))
    for x in rows:
        print("  %-7s R̄ %s->%s  兑现 %5s->%5s  斜率 %s" % (
            x["trace"], x["r0"], x["r1"], x["realized0_pct"], x["realized1_pct"],
            x["slope_pp_per_unit"]))


if __name__ == "__main__":
    main()
