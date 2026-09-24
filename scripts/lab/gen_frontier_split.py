#!/usr/bin/env python3
"""把前沿按配置拆开：HiCache-only 前沿 vs device-only 前沿 vs 混合前沿。

为什么必须拆：实验机日志核实（grep enable_hierarchical_cache）结果是
  - 九条控制器臂 全部 True
  - HiCache 静态点 pairB_cap2hc / cap3_hc / cap4_hc = True
  - device-only 点 cap1/cap2/cap3_fixed/cap4/cap5 = False
  - aimd2 = False
论文现在用的前沿把两种配置的静态点混在一起，控制器（全 HiCache）却去和
混合前沿比。公平对照是 HiCache-only 前沿 —— 而且它更快（cap4_hc 213.0 分，
比 device-only 最快的 cap4 249.9 分快 37 分）。

判决口径照抄 scripts/lab/frontier.py：上-左包络，Δ = SLO - 包络插值，
|Δ| <= 1.0pp 记为打平。**不改判据，只换锚点集合。**
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "..", "paper", "data")
BAND = 1.0

def load(n):
    return [r for r in csv.DictReader(l for l in open(os.path.join(D, n)) if not l.startswith("#"))]

# ⚠ 墙钟必须取【全精度】的 runs_precise.csv（frontier.py --csv 的产物），
# 不能用 decomp.csv 的 1 位小数 —— 那会让同一个 Δ 在本表和表 I 里差 0.1pp
# （foyer_hc 的混合前沿：−1.14 vs −1.24）。2026-09-25 自查发现，
# 与 slo_sensitivity 那次是同一类（两条管线算同一个量必须共用定义）。
runs = {r["run"].replace("pois200_", ""): {"wall_min": r["wall_min"], "slo_pct": r["slo_pct"]}
        for r in load("runs_precise.csv")}
dec  = runs

# ⚠ 锚点集合要【完整】。原来 HC 那一侧只有三条、漏了两个重复 run
# （cap3_hc_r2 / cap4_hc_r2），而论文的 FRONT 正是用重复顶掉首跑的 ——
# 于是同一个 Δ 在本表和表 I 里差 0.1pp（foyer_hc：−1.13 vs −1.24）。
# 2026-09-25 自查发现。envelope() 会自己挑上左包络，这里只负责把候选列全。
# 三套候选。**"mixed" 必须与论文的 FRONT 逐字相同** —— 它就是这个脚本的对照组，
# 从 frontier.py 直接 import FRONT 的锚点名字，不自己再写一份（写第二份就会漂）。
# ⚠ 别把 cap2_hc 放进候选：那是 763 步被中止的 run。
import importlib.util as _iu
_sp = _iu.spec_from_file_location("_fr_fs", os.path.join(HERE, "frontier.py"))
_FR = _iu.module_from_spec(_sp); _sp.loader.exec_module(_FR)
MIXED_ANCHORS = [n for _, _, n in _FR.FRONT]
HC_ANCHORS  = ["pairA_cap2hc", "pairB_cap2hc", "cap3_hc", "cap4_hc",
               "cap3_hc_r2", "cap4_hc_r2"]
DEV_ANCHORS = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]
CONTROLLERS = ["foyer_hc", "foyer_hz1", "foyer_hz2", "foyer_hz0_r2", "foyer_bres_r2",
               "foyer_breshz1", "foyer_nogate", "foyer_rg4", "foyfix_hc"]

def envelope(anchors):
    """上-左包络：(wall, slo) 中不被任何点支配的集合，按 wall 升序。"""
    pts = []
    for a in anchors:
        if a not in runs or a not in dec:
            continue
        w = float(dec[a]["wall_min"]); s = float(runs[a]["slo_pct"])
        pts.append((w, s, a))
    pts.sort()
    env, best = [], -1e9
    for w, s, a in pts:
        if s > best:
            env.append((w, s, a)); best = s
    return env

def interp(env, w):
    """在包络上对 wall 做线性插值取 SLO。"""
    if not env: return None
    if w <= env[0][0]:  return env[0][1]
    if w >= env[-1][0]: return env[-1][1]
    for (w0, s0, _), (w1, s1, _) in zip(env, env[1:]):
        if w0 <= w <= w1:
            if w1 == w0: return max(s0, s1)
            return s0 + (s1 - s0) * (w - w0) / (w1 - w0)
    return env[-1][1]

def judge(env, arm):
    w = float(dec[arm]["wall_min"]); s = float(runs[arm]["slo_pct"])
    ref = interp(env, w)
    d = s - ref
    verdict = "打平" if abs(d) <= BAND else ("在线上方" if d > 0 else "在线下方")
    return w, s, ref, d, verdict

env_hc  = envelope(HC_ANCHORS)
env_dev = envelope(DEV_ANCHORS)
env_mix = envelope(MIXED_ANCHORS)   # 论文的 FRONT，逐字相同

def show(name, env):
    print("== %s 前沿 ==" % name)
    for w, s, a in env:
        print("   %-14s wall %6.1f  SLO %5.1f" % (a, w, s))
    print()

show("HiCache-only", env_hc)
show("device-only", env_dev)
show("混合（论文现用）", env_mix)

print("控制器臂在三套前沿下的判决")
print("%-14s %6s %6s | %-28s | %-28s | %-28s"
      % ("arm", "wall", "SLO", "HiCache-only", "device-only", "混合"))
res = {}
for arm in CONTROLLERS:
    if arm not in runs or arm not in dec: continue
    cols, vals = [], {}
    for nm, env in (("hc", env_hc), ("dev", env_dev), ("mix", env_mix)):
        w, s, ref, d, v = judge(env, arm)
        vals[nm] = (w, s, ref, d, v)
        cols.append("%+6.2fpp %s" % (d, v))
    res[arm] = vals
    w, s = vals["hc"][0], vals["hc"][1]
    print("%-14s %6.1f %6.1f | %-28s | %-28s | %-28s" % (arm, w, s, cols[0], cols[1], cols[2]))

print()
for nm, label in (("hc", "HiCache-only"), ("dev", "device-only"), ("mix", "混合")):
    n_above = sum(1 for a in res if res[a][nm][4] == "在线上方")
    n_tie   = sum(1 for a in res if res[a][nm][4] == "打平")
    print("%-14s 在线上方 %d 条，打平 %d 条，共 %d 条" % (label, n_above, n_tie, len(res)))

out = os.path.join(D, "frontier_split.csv")
with open(out, "w") as f:
    f.write("# 三套前沿下控制器臂的判决 —— gen_frontier_split.py 生成\n")
    f.write("# 口径同 frontier.py（上-左包络 + 线性插值 + ±1.0pp 打平带），只换锚点集合\n")
    f.write("arm,wall_min,slo_pct,front,ref_slo,delta_pp,verdict\n")
    for arm, vals in res.items():
        for nm, label in (("hc","hicache"),("dev","device"),("mix","mixed")):
            w, s, ref, d, v = vals[nm]
            f.write("%s,%.1f,%.1f,%s,%.2f,%+.2f,%s\n" % (arm, w, s, label, ref, d, v))
print("-> %s" % out)
