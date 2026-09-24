#!/usr/bin/env python3
"""HiCache 配置下的分段弹性 —— 与 device-only 曲线并列。

为什么必须单独算：论文 §IV 的判据曲线是从**五个 device-only 静态 cap** 上测的
（cap1/cap2/cap3_fixed/cap4/cap5），而九条控制器臂**全部开着 HiCache**。
codex 抓到这一点：「机制来自无 HiCache 的五个静态点，却用来解释有 HiCache 的臂」。
decomp.csv 里其实已经有 HiCache 的静态 cap（pairB_cap2hc / cap3_hc / cap4_hc），
本脚本把它们单独串成一条曲线，看控制器的运行区间在**它自己那套配置**下 eps 是几。

口径与 gen_elasticity.py 完全一致：tau1 = busy_min*60*Rbar_busy/tokens（busy 条件均值）。
"""
import csv, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_elasticity as _GE  # noqa: E402  ε 的共用定义

HERE = os.path.dirname(os.path.abspath(__file__))
DEC = os.path.join(HERE, "..", "..", "paper", "data", "decomp.csv")
ARM = os.path.join(HERE, "..", "..", "paper", "data", "arm_running.csv")

# 两条曲线。名字对应 decomp.csv 的 run 列。
DEVICE = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]
HC     = ["pairB_cap2hc", "cap3_hc", "cap4_hc"]

def load(p):
    return {r["run"]: r for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))}

def eps(d, a, b):
    """走 gen_elasticity.eps —— 共用定义，不另写一份（CLAUDE.md 纪律 2）。

    本函数原来自己实现了一遍，而文件开头写着「口径与 gen_elasticity.py 完全一致」。
    2026-09-25 对拍过：两边确实一致；但那是运气，改成 import。
    """
    return _GE.eps(float(d[a]["step_back_ms"]), float(d[a]["running"]),
                   float(d[b]["step_back_ms"]), float(d[b]["running"]))

def curve(d, names, label):
    print("== %s ==" % label)
    print("  %-14s %6s %9s" % ("run", "Rbar", "tau1(ms)"))
    for n in names:
        assert n in d, "decomp.csv 缺 %s" % n
        print("  %-14s %6s %9s" % (n, d[n]["running"], d[n]["step_back_ms"]))
    out = []
    for a, b in zip(names, names[1:]):
        e = eps(d, a, b)
        ra, rb = float(d[a]["running"]), float(d[b]["running"])
        out.append((a, b, ra, rb, float(d[a]["step_back_ms"]), float(d[b]["step_back_ms"]), e))
        print("  %-12s -> %-12s  Rbar %.2f->%.2f  tau %.1f->%.1f  eps = %+.3f"
              % (a, b, ra, rb, float(d[a]["step_back_ms"]), float(d[b]["step_back_ms"]), e))
    print()
    return out

def main():
    d = load(DEC)
    dev = curve(d, DEVICE, "device-only（论文 §IV 现在用的那条）")
    hc  = curve(d, HC,     "HiCache（控制器臂实际运行的配置）")

    print("== 控制器臂的 Rbar_busy 落在哪 ==")
    arms = []
    if os.path.exists(ARM):
        for r in csv.DictReader(l for l in open(ARM) if not l.startswith("#")):
            if r["family"] == "controller":
                arms.append((r["run"], float(r["running_busy"])))
    arms.sort(key=lambda x: x[1])
    for name, rb in arms:
        dev_seg = next((s for s in dev if s[2] <= rb <= s[3]), None)
        hc_seg  = next((s for s in hc  if s[2] <= rb <= s[3]), None)
        print("  %-14s Rbar=%.3f   device-only: %s   HiCache: %s" % (
            name, rb,
            ("%s->%s eps=%+.2f" % (dev_seg[0], dev_seg[1], dev_seg[6])) if dev_seg else "（曲线外）",
            ("%s->%s eps=%+.2f" % (hc_seg[0],  hc_seg[1],  hc_seg[6]))  if hc_seg  else "（曲线外）"))
    print()

    # 断言：两条曲线都必须单调可算，且 HiCache 段数 == 点数-1
    assert all(s[6] is not None for s in dev), "device-only 曲线有段算不出来"
    assert all(s[6] is not None for s in hc),  "HiCache 曲线有段算不出来"
    assert len(hc) == len(HC) - 1

    n_ge1_dev = sum(1 for s in dev if s[6] >= 1.0)
    n_ge1_hc  = sum(1 for s in hc  if s[6] >= 1.0)
    print("eps>=1 的段数：device-only %d/%d，HiCache %d/%d" % (n_ge1_dev, len(dev), n_ge1_hc, len(hc)))

    out = os.path.join(HERE, "..", "..", "paper", "data", "elasticity_hc.csv")
    with open(out, "w") as f:
        f.write("# 两条分段弹性曲线并列 —— gen_elasticity_hc.py 生成\n")
        f.write("# config: device_only = §IV 现用；hicache = 控制器臂实际配置\n")
        f.write("config,from,to,r0,r1,tau0_ms,tau1_ms,epsilon\n")
        for cfg, segs in (("device_only", dev), ("hicache", hc)):
            for a, b, r0, r1, t0, t1, e in segs:
                f.write("%s,%s,%s,%.2f,%.2f,%.1f,%.1f,%.3f\n" % (cfg, a, b, r0, r1, t0, t1, e))
    print("-> %s" % out)

if __name__ == "__main__":
    main()
