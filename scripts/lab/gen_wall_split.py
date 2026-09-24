#!/usr/bin/env python3
"""把每条控制器臂相对【最近同配置静态锚点】的墙钟差，拆成 idle 分量与 busy 分量。

为什么需要：论文 sec_results 用 hz1 与 cap3_hc 这一对论证「低占用不能解释结果」，
并把 19 分钟的差额归给步成本。实测拆开是 idle 12.6 分 + busy 6.8 分 —— 65% 是 idle。
一对样本支撑不了任何结论，本脚本在**全部**臂上做同一拆分。

两个必须守住的点（都曾写错）：
  1. 恒等式是 **span = idle + busy**，不是 wall = idle + busy。
     decomp.csv 里 wall_min 比 span_min 小 ~6 分钟（采样器比请求早启动、晚停止），
     拿 wall 去减 idle+busy 会凭空多出一个偏移量，且该偏移在各臂上不同。
  2. G（生成 token 总数）在各臂间并非严格相等（700.2~708.3 ktok，跨度 1%），
     所以 busy = G*tau/(Rbar*60000) 的差只能拆到"G 浮动"这一残差为止，如实报出。

用法: python3 gen_wall_split.py
"""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "..", "paper", "data")
C = 60000.0          # ms -> min 的换算：busy_min = tau_ms * G / (Rbar * 60000)

def load(n):
    return {r["run"]: r for r in csv.DictReader(l for l in open(os.path.join(D, n)) if not l.startswith("#"))}

dec = load("decomp.csv")

# 控制器臂 -> 曲线族。HiCache 臂只对 HiCache 锚点 —— 跨配置外推正是 codex 抓到的错。
CONTROLLERS = ["foyer_hc", "foyer_hz1", "foyer_hz2_r2", "foyer_hz0_r2", "foyer_bres_r2",
               "foyer_breshz1", "foyer_nogate", "foyer_rg4", "foyfix_hc"]
HC_ANCHORS  = ["pairB_cap2hc", "cap3_hc", "cap4_hc"]
DEV_ANCHORS = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]

def implied_G(r):
    """busy_min = tau_ms*G/(Rbar*60000)  =>  G = busy_min*Rbar*60000/tau_ms"""
    return float(r["busy_min"]) * float(r["running"]) * C / float(r["step_back_ms"])

rows = []
for arm in CONTROLLERS:
    if arm not in dec:
        continue
    a = dec[arm]
    near = min(HC_ANCHORS, key=lambda n: abs(float(dec[n]["running"]) - float(a["running"])))
    b = dec[near]

    # 恒等式用 span
    d_span = float(a["span_min"]) - float(b["span_min"])
    d_idle = float(a["idle_min"]) - float(b["idle_min"])
    d_busy = float(a["busy_min"]) - float(b["busy_min"])
    # decomp.csv 只存一位小数，三项各自舍入 -> 容差取 0.2（远小于任何真实差额）
    assert abs(d_span - (d_idle + d_busy)) < 0.2, ("恒等式破裂", arm, d_span, d_idle, d_busy)

    ta, tb = float(a["step_back_ms"]), float(b["step_back_ms"])
    ra, rb = float(a["running"]), float(b["running"])
    Ga, Gb = implied_G(a), implied_G(b)
    G = 0.5 * (Ga + Gb)
    # 先在固定 Rbar_a 上换 tau，再在固定 tau_b 上换 Rbar
    tau_eff  = G * (ta - tb) / (ra * C)
    rbar_eff = G * tb * (1.0 / ra - 1.0 / rb) / C
    resid = d_busy - (tau_eff + rbar_eff)      # 只该来自 Ga != Gb

    rows.append(dict(arm=arm, anchor=near, d_span=d_span, d_idle=d_idle, d_busy=d_busy,
                     frac_idle=(d_idle / d_span) if d_span else float("nan"),
                     tau_eff=tau_eff, rbar_eff=rbar_eff, resid=resid,
                     dRbar=ra - rb, tau_a=ta, tau_b=tb, wall_a=float(a["wall_min"])))

# 残差必须小到 G 的 1% 浮动能解释的量级
for r in rows:
    assert abs(r["resid"]) < 0.02 * abs(r["d_busy"]) + 1.5, ("残差超出 G 浮动可解释范围", r)

rows.sort(key=lambda r: r["d_span"])
print("相对最近 HiCache 静态锚点（span 口径，恒等式精确）")
print("%-14s %-13s %7s %7s %7s %8s %7s %7s %6s %7s"
      % ("arm", "anchor", "d_span", "d_idle", "d_busy", "idle占比", "tau项", "Rbar项", "残差", "dRbar"))
for r in rows:
    print("%-14s %-13s %+7.1f %+7.1f %+7.1f %7.0f%% %+7.1f %+7.1f %+6.1f %+7.2f"
          % (r["arm"], r["anchor"], r["d_span"], r["d_idle"], r["d_busy"],
             100 * r["frac_idle"], r["tau_eff"], r["rbar_eff"], r["resid"], r["dRbar"]))

slower = [r for r in rows if r["d_span"] > 0]
print()
if slower:
    fr = sorted(100 * r["frac_idle"] for r in slower)
    print("比锚点慢的 %d 条：idle 分量占差额 中位 %.0f%% / 均值 %.0f%% / 范围 %.0f~%.0f%%"
          % (len(slower), fr[len(fr) // 2], sum(fr) / len(fr), fr[0], fr[-1]))
print("d_idle > 0 的臂：%d/%d" % (sum(1 for r in rows if r["d_idle"] > 0), len(rows)))
print("d_busy > 0 的臂：%d/%d" % (sum(1 for r in rows if r["d_busy"] > 0), len(rows)))

out = os.path.join(D, "wall_split.csv")
with open(out, "w") as f:
    f.write("# 控制器臂相对最近【同配置 HiCache】静态锚点的 span 差分解 —— gen_wall_split.py 生成\n")
    f.write("# 恒等式 span = idle + busy（不是 wall！decomp 的 wall 比 span 小约 6 分钟采样偏移）\n")
    f.write("arm,anchor,d_span_min,d_idle_min,d_busy_min,frac_idle,tau_contrib_min,rbar_contrib_min,resid_min,dRbar\n")
    for r in rows:
        f.write("%s,%s,%.1f,%.1f,%.1f,%.3f,%.1f,%.1f,%.2f,%.3f\n" % (
            r["arm"], r["anchor"], r["d_span"], r["d_idle"], r["d_busy"],
            r["frac_idle"], r["tau_eff"], r["rbar_eff"], r["resid"], r["dRbar"]))
print("-> %s" % out)
