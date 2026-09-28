#!/usr/bin/env python3
"""独立复算弹性 ε —— 【不 import 任何生成器】，从 decomp.csv 的原始列直接算。

为什么要有：`check_paper_numbers.py` 里那几条 ε 守卫是 **import
`gen_elasticity_hc.eps`**（共用定义，本项目纪律 2）—— 那是**对的**（同一个量只有一份
实现），但它意味着：**如果 `eps` 本身写错了，守卫会与它一致地错，0 MISS 照旧**。
`independent_frontier_check.py` 已经用同样的理由给「前沿与 Δ」立了第二条线，
这个脚本给「ε」立第二条线 —— 它是论文贡献之一（「把问题化成一个可测的数」）。

**独立到什么程度**：不 import 任何生成器，连 `math.log` 的用法都另写一遍
（`log(b/a)` 与 `log(b)-log(a)` 是同一个数，但**参数顺序写反**这类错会被抓住）。
它能抓的是【实现 bug】【抄录错误】【用错列】这三类。

判据（全部硬断言，不匹配就非零退出）：
  1. 设备侧五点的**分段 ε** 与 `paper/data/elasticity.csv` 逐位相符（容差 1e-3）；
  2. 两条曲线的分段 ε 与 `paper/data/elasticity_hc.csv` 逐位相符；
  3. **拟合 ε**（对五点做 ln τ ~ ln R̄ 的最小二乘）在两位小数口径下等于正文的
     0.38（模型自洽）/ 0.61（逐请求），并打印 R² —— 正文写「$R^2 = 0.89$ for the latter」。

⚠ 「两位小数口径」是**正文自己声明的**（§IV 写着用 `decomp.csv` 的 `running` 到两位），
所以这里用 `round(x, 2)` 的输入；六位口径的读数另有一组守卫（`arm_running.csv` 的
`Rbar_busy`），本脚本不重复它。

用法: python3 independent_elasticity_check.py <decomp.csv> [elasticity.csv] [elasticity_hc.csv]
"""
import csv, math, os, sys

DEVICE = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]
HC = ["pairB_cap2hc", "cap3_hc", "cap4_hc", "cap5_hc", "cap6_hc", "cap8_hc"]
PAPER_EPS_MODEL, PAPER_EPS_REQ, PAPER_R2_REQ = 0.38, 0.61, 0.89


def load(p):
    return {r["run"]: r for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))}


def seg_eps(r0, t0, r1, t1):
    """ε = dln(tau)/dln(R̄) —— 独立写一遍（不用生成器的 eps）。"""
    return math.log(t1 / t0) / math.log(r1 / r0)


def fit(xs, ys):
    """ln y ~ ln x 的最小二乘斜率与 R² —— 独立写一遍。"""
    X = [math.log(v) for v in xs]
    Y = [math.log(v) for v in ys]
    n = len(X)
    mx, my = sum(X) / n, sum(Y) / n
    sxx = sum((a - mx) ** 2 for a in X)
    sxy = sum((a - mx) * (b - my) for a, b in zip(X, Y))
    sl = sxy / sxx
    resid = sum((b - (my + sl * (a - mx))) ** 2 for a, b in zip(X, Y))
    sst = sum((b - my) ** 2 for b in Y)
    return sl, 1 - resid / sst


def main():
    dec_p = sys.argv[1]
    el_p = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(dec_p)), "elasticity.csv")
    elhc_p = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
        os.path.dirname(os.path.abspath(dec_p)), "elasticity_hc.csv")
    d = load(dec_p)
    bad = 0

    def chain(names, label):
        nonlocal bad
        print("== %s ==" % label)
        out = []
        for a, b in zip(names, names[1:]):
            assert a in d and b in d, "decomp.csv 缺 %s 或 %s" % (a, b)
            # ⚠ 正文声明的口径：`decomp.csv` 的 `running` 到**两位小数**（§IV 写明了）。
            # 不 round 会得到另一个数（六位口径），那不是错，是**另一个口径**。
            ra = round(float(d[a]["running"]), 2)
            rb = round(float(d[b]["running"]), 2)
            ta = float(d[a]["step_back_ms"]); tb = float(d[b]["step_back_ms"])
            if rb <= ra:
                print("  %-14s -> %-14s  R̄ 倒序 —— 不可算（与生成器同样跳过）" % (a, b))
                continue
            e = seg_eps(ra, ta, rb, tb)
            out.append((a, b, e))
            print("  %-14s -> %-14s  R̄ %.2f->%.2f  tau %.1f->%.1f  eps = %+.4f"
                  % (a, b, ra, rb, ta, tb, e))
        return out

    dev = chain(DEVICE, "device-only（§IV 现用）")
    hc = chain(HC, "with HiCache（控制器实际配置）")

    # ---- 对拍 1：与 elasticity.csv 的 device_only 分段逐位相符 ----
    if os.path.exists(el_p):
        ref = list(csv.DictReader(l for l in open(el_p) if not l.startswith("#")))
        ref = [r for r in ref if "epsilon" in r]
        if ref:
            if len(ref) != len(dev):
                print("  !! 段数不一致：本脚本 %d，elasticity.csv %d" % (len(dev), len(ref)))
                bad += 1
            print("\n对拍 elasticity.csv（device_only，%d 段）:" % len(ref))
            for (a, b, e), r in zip(dev, ref):
                if r["from"] != a or r["to"] != b:
                    print("  !! 段不一致：本脚本 %s->%s，CSV %s->%s" % (a, b, r["from"], r["to"]))
                    bad += 1
                    continue
                # ⚠ 容差要按**CSV 的精度**定：`elasticity.csv` 存两位小数，
                # 拿 2e-3 去比 0.4328 与 0.43 会得到 0.0028 的「不符」——
                # **那是舍入，不是分歧**。判据是「本脚本四舍五入到 CSV 那位后相等」，
                # 即 |差| ≤ 半个末位 + 1e-9。（第一版就栽在这里：自己造了三条假警报。）
                de = abs(e - float(r["epsilon"]))
                ok = de <= 0.5e-2 + 1e-9
                print("  %-14s -> %-14s  本脚本 %+.4f (%.2f)  CSV %+.2f  %s"
                      % (a, b, e, round(e, 2), float(r["epsilon"]), "OK" if ok else "!! 不符"))
                bad += 0 if ok else 1
    else:
        print("\n!! 找不到 %s，分段 ε 没对拍上" % el_p)
        bad += 1

    # ---- 对拍 2：与 elasticity_hc.csv 两条曲线逐位相符 ----
    if os.path.exists(elhc_p):
        rows = [r for r in csv.DictReader(l for l in open(elhc_p) if not l.startswith("#"))]
        for cfg, mine in (("device_only", dev), ("hicache", hc)):
            ref = [r for r in rows if r.get("config") == cfg]
            print("\n对拍 elasticity_hc.csv（%s，%d 段）:" % (cfg, len(ref)))
            for (a, b, e), r in zip(mine, ref):
                if r["from"] != a or r["to"] != b:
                    print("  !! 段不一致：本脚本 %s->%s，CSV %s->%s" % (a, b, r["from"], r["to"]))
                    bad += 1
                    continue
                de = abs(e - float(r["epsilon"]))       # 这张表存三位小数
                ok = de <= 0.5e-3 + 1e-9
                print("  %-14s -> %-14s  本脚本 %+.4f (%.3f)  CSV %+.3f  %s"
                      % (a, b, e, round(e, 3), float(r["epsilon"]), "OK" if ok else "!! 不符"))
                bad += 0 if ok else 1
            if len(ref) != len(mine):
                print("  !! 段数不一致：本脚本 %d，CSV %d" % (len(mine), len(ref)))
                bad += 1
    else:
        print("\n!! 找不到 %s，两条曲线没对拍上" % elhc_p)
        bad += 1

    # ---- 对拍 3：拟合 ε（正文的 0.38 / 0.61，两位小数口径）+ R² ----
    xs = [round(float(d[c]["running"]), 2) for c in DEVICE]
    e1, r2_1 = fit(xs, [float(d[c]["step_back_ms"]) for c in DEVICE])
    e2, r2_2 = fit(xs, [float(d[c]["step_perreq_ms"]) for c in DEVICE])
    print("\n拟合 ε（device-only 五点，ln τ ~ ln R̄，两位小数口径）:")
    print("  模型自洽 τ₁: eps = %.4f -> 两位 %.2f（正文 %.2f）  R² = %.3f"
          % (e1, round(e1, 2), PAPER_EPS_MODEL, r2_1))
    print("  逐请求 τ₂: eps = %.4f -> 两位 %.2f（正文 %.2f）  R² = %.3f（正文 %.2f）"
          % (e2, round(e2, 2), PAPER_EPS_REQ, r2_2, PAPER_R2_REQ))
    for got, want, what in ((round(e1, 2), PAPER_EPS_MODEL, "模型自洽 ε"),
                            (round(e2, 2), PAPER_EPS_REQ, "逐请求 ε")):
        if abs(got - want) > 1e-9:
            print("  !! %s 不符：本脚本 %.2f，正文 %.2f" % (what, got, want))
            bad += 1
    if abs(r2_2 - PAPER_R2_REQ) > 5e-3:
        print("  !! R² 不符：本脚本 %.3f，正文 %.2f" % (r2_2, PAPER_R2_REQ))
        bad += 1

    print("\n结论：%s" % ("全部相符（独立重算与生成器输出一致）" if not bad
                        else "有 %d 处不符 —— 以本脚本为准去查生成器" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
