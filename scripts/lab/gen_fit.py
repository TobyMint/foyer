#!/usr/bin/env python3
"""`paper/data/fit.csv` —— §III 那句「a straight line through the twenty-six,
$r=+0.85$ with a largest residual of 1.92\\,ms」的**唯一出处**。

## 为什么要有这个脚本

2026-09-27 的中立复核（r49）指出：这个数**在仓库里没有任何生成器算它** ——
复核者按最自然的定义（x = 每 run 的未重算 token 数、y = `decomp.csv` 的
`step_back_ms`、普通最小二乘、26 条）复现出 **0.8524 / 1.9197**，与正文印的
0.85 / 1.92 相符，但他只能记成「**按自然定义复现成功**，不算口径已核」——
因为**没有脚本可以指**。这正是「所有数字可追溯到脚本或日志」这条停止条件上的缺口。

本脚本把那一次复算**固定成代码**：口径写死在这里，正文引 `fit.csv`。

## 口径（写死，改口径必须同时改正文与 `check_paper_numbers.py`）

- **x** = `eviction.csv` 的 `uncached_tok`（**全精度原始计数**，不是 `uncached_M`
  那列舍入到 0.1M 的版本 —— 拿舍入列去拟合会让 r 动到第三位）
- **y** = `decomp.csv` 的 `step_back_ms`（τ₁，与 §III/§IV 用的同一列）
- **集合** = `eviction.csv` 的 `hicache == 1` 行 ∩ `decomp.csv` 有 τ₁ 的行
  = **26 条**（28 条 host-tier 减去 `pairA_foyerhc`/`pairB_foyerhc` ——
  它们在 `eviction.csv` 里但没有步成本）
- **拟合** = 普通最小二乘 `y = a + b·x`；**r** = 皮尔逊相关系数；
  **max|res|** = 残差绝对值的最大者（ms）
- 正文按 **2 位小数**印（`r = +0.85`、`1.92\\,ms`），`fit.csv` 存 **6 位**。

用法: python3 gen_fit.py <paper/data> <out.csv>
"""
import csv, math, os, sys

XCOL = "uncached_tok"      # eviction.csv
YCOL = "step_back_ms"      # decomp.csv


def load(p):
    with open(p, encoding="utf-8") as f:
        return [r for r in csv.DictReader(l for l in f if not l.startswith("#"))]


def main():
    d = sys.argv[1]
    out = sys.argv[2]
    ev = load(os.path.join(d, "eviction.csv"))
    dc = {r["run"]: r for r in load(os.path.join(d, "decomp.csv"))}

    pts = []
    for r in ev:
        if str(r.get("hicache")) not in ("1", "True"):
            continue
        y = (dc.get(r["run"]) or {}).get(YCOL)
        x = r.get(XCOL)
        if not x or not y:
            continue
        try:
            pts.append((r["run"], float(x), float(y)))
        except ValueError:
            continue

    if len(pts) < 3:
        raise SystemExit("!! 有效点只有 %d 条，拟合没有意义" % len(pts))

    n = len(pts)
    xs = [p[1] for p in pts]
    ys = [p[2] for p in pts]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    res = [y - (a + b * x) for _, x, y in pts]
    sst = sum((y - my) ** 2 for y in ys)
    sse = sum(v * v for v in res)
    r = math.sqrt(1.0 - sse / sst)
    mxres = max(abs(v) for v in res)
    worst = max(pts, key=lambda p: abs(p[2] - (a + b * p[1])))

    print("拟合：n=%d  r=%.6f  max|res|=%.6f ms" % (n, r, mxres))
    print("  斜率 %.6e / 截距 %.6f；最大残差在 %s" % (b, a, worst[0]))
    print("  正文按 2 位小数印：r=%.2f，残差 %.2f ms" % (r, mxres))

    with open(out, "w", newline="") as f:
        f.write("# §III 那条拟合 —— 由 scripts/lab/gen_fit.py 生成，勿手改\n")
        f.write("# x=%s（eviction.csv，全精度）/ y=%s（decomp.csv）；OLS；"
                "集合 = hicache 行 ∩ 有 tau1 的行\n" % (XCOL, YCOL))
        f.write("# ⚠ 正文（sec_model.tex）按 2 位小数印 r 与 max|res|\n")
        w = csv.writer(f)
        w.writerow(["n", "r", "slope", "intercept", "max_abs_resid_ms", "max_resid_run"])
        w.writerow([n, "%.6f" % r, "%.6e" % b, "%.6f" % a,
                    "%.6f" % mxres, worst[0]])
        w.writerow([])
        w.writerow(["run", "uncached_tok", "step_back_ms", "fitted", "resid"])
        for (nm, x, y), rv in zip(pts, res):
            w.writerow([nm, "%.0f" % x, "%.4f" % y, "%.4f" % (a + b * x), "%.4f" % rv])
    print("->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
