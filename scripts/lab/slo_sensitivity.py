#!/usr/bin/env python3
"""SLO 阈值敏感性：整条前沿的纵轴都由「TTFT<10s」切出来，换个阈值会怎样？

审稿人一定会问。这是纯分析，用现有 steps.jsonl 就能做。

同时给出每条 run 的 TTFT 分位数，让读者看到 SLO 这个数是怎么被阈值切出来的。
"""
import json, os, statistics, sys, glob

THRESH = [5.0, 10.0, 20.0]
# cap3_hc_r2 / cap4_hc_r2 是重复 run，2026-09-24 起按其重复顶掉首次的规矩一并纳入
RUNS = ["cap1","cap2","cap3_fixed","cap3_pd","cap4","cap5","pairB_cap2hc","cap3_hc","cap3_ph","cap3_hc_r2","cap4_hc","cap4_hc_r2","cap5_hc","cap6_hc","cap8_hc",
        "foyer_hc","foyer_hc_r2","foyer_hz1","foyer_hz1_r2","foyer_hz1_r3","foyer_sf0_r2","foyer_hz2_r2","foyer_hz2_r3","foyer_hz0_r2","foyer_bres_r2","foyer_breshz1_r2",
        "foyer_nogate","foyer_rg4","foyer_scan","foyer_scan_r2","foyer_scan_r3",
        "foyer_hc_slru","foyer_sf0_r3","foyfix_hc",
        "aimd2","aimd2_paper_r3"]


import envelope as _ENV   # noqa: E402  包络与插值的**唯一实现**


def main():
    root = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    _rows = []
    print("%-14s %8s %7s %7s %7s %7s %7s" %
          ("run", "TTFT50", "p90", "p99", "SLO5%", "SLO10%", "SLO20%"))
    out = {}
    _envs, _deltas = {}, {}
    _dl = {t: {} for t in THRESH}
    for r in RUNS:
        p = os.path.join(root, "pois200_" + r, "steps.jsonl")
        if not os.path.exists(p):
            continue
        tt = [json.loads(l)["first_token_ms"] for l in open(p)
              if l.strip() and json.loads(l).get("first_token_ms") is not None]
        if not tt:
            continue
        tt.sort()
        def pct(q): return tt[min(len(tt) - 1, int(q * len(tt)))] / 1000.0
        slo = {t: 100.0 * sum(1 for x in tt if x < t * 1000) / len(tt) for t in THRESH}
        out[r] = (pct(.5), pct(.9), pct(.99), slo)
        print("%-14s %8.1f %7.1f %7.1f %7.1f %7.1f %7.1f" %
              (r, pct(.5), pct(.9), pct(.99), slo[5.0], slo[10.0], slo[20.0]))

    # 三个阈值下的静态前沿，看排序是否稳定
    print()
    # ⚠ 墙钟一律从 table1.csv 读【全精度】值。以前这里写死的是舍入到 0.1 分的数，
    # 于是同一个 Δ 在本表和表 I / §V 里差一位小数（sf0_r2 的 10s 距离：−0.6 vs −0.55）
    # —— 又是「两条管线算同一个量必须共用定义」那一条（2026-09-25 自查发现）。
    _t1 = {}
    _t1p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "paper", "data", "table1.csv")
    if os.path.exists(_t1p):
        _t1 = {r["run"]: float(r["wall_min"]) for r in
               __import__("csv").DictReader(l for l in open(_t1p) if not l.startswith("#"))}
    # ⚠⚠ 2026-09-27（独立复核）：**墙钟要用全精度**。`table1.csv` 的 `wall_min` 是
    # **4 位小数**（263.3403），而 `frontier.py` 从 `steps.jsonl` 现算（263.340318）。
    # 差 1.8e-5 分 × 前沿斜率 0.15 ≈ 2.7e-6，正好把 `sf0_r2` 的 Δ 推过 `%.4f` 的边界
    # （−0.551849 → −0.5518 vs −0.551852 → −0.5519）。于是同一条臂在两张表里
    # **第 4 位不同**（`sf0_r2` 与 `aimd2` 各一条）—— 正文只印 1 位、判决不受影响，
    # 但「与表 I 逐位一致」这句话不成立。改用 `runs_precise.csv`（全精度）后对齐。
    _t1q = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "paper", "data", "runs_precise.csv")
    if os.path.exists(_t1q):
        _t1 = {r["run"].replace("pois200_", ""): float(r["wall_min"]) for r in
               __import__("csv").DictReader(l for l in open(_t1q) if not l.startswith("#"))}
    stat = {"cap1": 527.4, "cap2": 304.2, "cap3_fixed": 258.7, "cap4": 249.9,
            "cap5": 260.9, "pairB_cap2hc": 295.0, "cap3_hc": 236.4, "cap3_hc_r2": 230.3,
            "cap4_hc": 213.0, "cap4_hc_r2": 209.1}
    stat = {k: _t1.get(k, v) for k, v in stat.items()}
    # ⚠ 锚点集合必须与表 I / §V 的 FRONT 一致 —— 那些锚点是在【10 s 阈值】下
    # 取的上左包络，换阈值时锚点集合不变、只换它们的纵坐标。以前这里是自己
    # 从 stat 字典重建一遍包络，于是同一条臂在两张表里有两个 Δ（2026-09-25 自查发现）。
    import importlib.util as _iu
    _sp = _iu.spec_from_file_location("_fr_slo", os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontier.py"))
    _FR = _iu.module_from_spec(_sp); _sp.loader.exec_module(_FR)
    for t in THRESH:
        # ⚠ 包络与插值**都调共用实现**（`envelope.upper_left` / `envelope.piecewise`）。
        # 原来这两样在本文件里各写了一份 —— 上面那段注释已经说明「锚点集合必须与
        # 表 I/§V 的 FRONT 一致」，但只修了【锚点集合】，构建包络的循环与插值函数
        # 仍是第二、第三份实现（2026-09-26 codex 第 31 轮的构造暴露的）。
        # 语义核对：原实现先比未舍入的 s、再存 round(s,1)；这里改成先舍入再比 ——
        # 只有当两个锚点的 SLO 在 0.1pp 内且顺序相反时才会不同，实测输出逐字相同。
        # ⚠ 2026-09-27：**锚点的纵坐标不许舍入** —— `frontier.FRONT` 存的是全精度，
        # 这里原来 `round(..., 1)` 之后才建包络，于是同一条臂在两张表里有两个 Δ：
        # `foyer_scan` 的 10s 距离在表 I/§V 是 **+1.3044**，在本表是 **+1.2917**
        # （差别 0.013pp，最大 0.028pp 出现在 5s）。实测**当前没有任何判决翻转**
        # （最贴边的是 `sf0_r2` 的 20s：+0.977/+0.983，两侧都 < 1.0），
        # 但「同一个量两份精度」正是本项目明令禁止的那一条，而且余量只剩 0.02pp。
        pts = sorted((w, out[name][3][t]) for w, _, name in _FR.FRONT if name in out)
        env = _ENV.upper_left(pts)
        print("阈值 %4.0fs 的静态前沿: %s" % (t, " -> ".join("%.0f/%.1f" % e for e in env)))
        _envs[t] = list(env)
        # 各 Foyer/AIMD 变体相对该前沿的有符号距离
        def front_slo(w):
            return _ENV.piecewise(w, env)
        # ⚠ **臂列表必须覆盖全部控制器臂**，不能手写子集。
        # 原来这里是硬编码的 8 条，而它漏掉了 `foyer_hz2_r2` —— **正是头条所依赖的
        # 那条臂**（10s 下最近、−0.30），而它在 20s 阈值下 **+1.02 ⇒ 越过**
        # （独立复核第 22 轮复算，我逐位复核过）。**漏掉的方向对论文有利。**
        # 判据改成机械的：凡在 RUNS 里、算出了 SLO 的控制器臂都算。
        deltas = []
        for r in RUNS:
            if r not in out or not (r.startswith("foyer") or r.startswith("aimd")):
                continue
            w = _t1.get(r)
            if w is None:
                print("  !! %s 不在 table1.csv 里 —— 墙钟拿不到，跳过（不猜）" % r)
                continue
            f = front_slo(w)
            if f is None:
                continue
            d = out[r][3][t] - f
            _dl[t][r] = d
            deltas.append("%s %+.1f" % (r.replace("foyer_", ""), d))
        print("            距离: %s" % "  ".join(deltas))

    # 落盘：论文 §VI 的阈值敏感性表要能追到一个文件，不能只活在终端输出里
    if out_path:
        import csv as _csv
        with open(out_path, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["# 阈值敏感性 —— slo_sensitivity.py 生成"])
            w.writerow(["# 每个阈值下各控制器相对该阈值静态前沿的有符号距离（pp）"])
            w.writerow(["# ⚠ 覆盖【全部】控制器臂 —— 2026-09-26 修：原来硬编码 8 条，"
                        "漏了 foyer_hz2_r2（头条所依赖的那条，20s 下 +1.02 越过）"])
            w.writerow(["run"] + ["slo%d_pp" % t for t in THRESH])
            # ⚠ **名单必须覆盖全部 RUNS**。原来这里硬编码 8 条，而它漏掉了
            # `foyer_hz2_r2` —— **正是头条所依赖的那条臂**（10s 下最近、−0.30），
            # 而它在 20s 阈值下 **+1.02 ⇒ 越过**（独立复核第 22 轮复算，我逐位复核过）。
            # 漏掉的方向**对论文有利**，所以必须修。
            # 现在的判据：凡是算出了 Δ 的臂都写进表，不再手写子集。
            # 一行一条控制器臂，值直接来自算好的 `_dl`（不再靠字符串前缀去 `_deltas` 里找）。
            for r in RUNS:
                if r not in _dl[THRESH[0]]:
                    continue
                # ⚠ 2026-09-26：落盘精度从 `%+.2f` 提到 **`%+.4f`**。
                # 为什么：正文那张表印 **1 位小数**，而守卫必须从**本文件**重算那三格
                # —— 2 位小数的 `-16.25` 再降到 1 位会得到 `-16.2`（round-half-even），
                # 而全精度真值 `-16.2549…` 降到 1 位是 **`-16.3`**。
                # 于是守卫报了一条 MISS，**而正文是对的**（假 MISS 的又一次）。
                # 数据文件比论文多留精度是本项目的既定口径（见 `runs_precise.csv`）。
                w.writerow([r.replace("foyer_", "")] +
                           ["%+.4f" % _dl[t][r] for t in THRESH])
            w.writerow([])
            w.writerow(["# 各阈值下的静态前沿锚点"])
            w.writerow(["threshold_s"] + ["anchor%d_wall,anchor%d_slo" % (i + 1, i + 1) for i in range(4)])
            for t in THRESH:
                flat = [x for e in _envs.get(t, []) for x in e]
                w.writerow([t] + flat)
        print("-> %s" % out_path)


if __name__ == "__main__":
    main()
