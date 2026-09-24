#!/usr/bin/env python3
"""SLO 阈值敏感性：整条前沿的纵轴都由「TTFT<10s」切出来，换个阈值会怎样？

审稿人一定会问。这是纯分析，用现有 steps.jsonl 就能做。

同时给出每条 run 的 TTFT 分位数，让读者看到 SLO 这个数是怎么被阈值切出来的。
"""
import json, os, statistics, sys, glob

THRESH = [5.0, 10.0, 20.0]
# cap3_hc_r2 / cap4_hc_r2 是重复 run，2026-09-24 起按其重复顶掉首次的规矩一并纳入
RUNS = ["cap1","cap2","cap3_fixed","cap4","cap5","pairB_cap2hc","cap3_hc","cap3_hc_r2","cap4_hc","cap4_hc_r2",
        "foyer_hc","foyer_hz1","foyer_hz2","foyer_hz0","foyer_bres_r2","foyer_breshz1",
        "foyer_nogate","foyer_rg4","foyfix_hc","aimd2","aimd2_paper"]


def main():
    root = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    _rows = []
    print("%-14s %8s %7s %7s %7s %7s %7s" %
          ("run", "TTFT50", "p90", "p99", "SLO5%", "SLO10%", "SLO20%"))
    out = {}
    _envs, _deltas = {}, {}
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
    stat = {"cap1": 527.4, "cap2": 304.2, "cap3_fixed": 258.7, "cap4": 249.9,
            "cap5": 260.9, "pairB_cap2hc": 295.0, "cap3_hc": 236.4, "cap3_hc_r2": 230.3,
            "cap4_hc": 213.0, "cap4_hc_r2": 209.1}
    for t in THRESH:
        pts = sorted((stat[k], out[k][3][t]) for k in stat if k in out)
        env, best = [], -1
        for w, s in pts:
            if s > best:
                env.append((w, round(s, 1))); best = s
        print("阈值 %4.0fs 的静态前沿: %s" % (t, " -> ".join("%.0f/%.1f" % e for e in env)))
        _envs[t] = list(env)
        # 各 Foyer/AIMD 变体相对该前沿的有符号距离
        def front_slo(w):
            for (w0, s0), (w1, s1) in zip(env, env[1:]):
                if w0 <= w <= w1:
                    return s0 + (w - w0) / (w1 - w0) * (s1 - s0)
            return None
        deltas = []
        for r in ["foyer_hz1", "foyer_hc", "foyer_bres_r2", "foyer_nogate", "aimd2_paper"]:
            if r in out:
                w = {"foyer_hz1": 255.8, "foyer_hc": 291.3, "foyer_bres_r2": 265.9,
                     "foyer_nogate": 272.3, "aimd2_paper": 364.3}[r]
                f = front_slo(w)
                if f is not None:
                    deltas.append("%s %+.1f" % (r.replace("foyer_", ""), out[r][3][t] - f))
        print("            距离: %s" % "  ".join(deltas))
        _deltas[t] = deltas

    # 落盘：论文 §VI 的阈值敏感性表要能追到一个文件，不能只活在终端输出里
    if out_path:
        import csv as _csv
        with open(out_path, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["# 阈值敏感性 —— slo_sensitivity.py 生成"])
            w.writerow(["# 每个阈值下各控制器相对该阈值静态前沿的有符号距离（pp）"])
            w.writerow(["run"] + ["slo%d_pp" % t for t in THRESH])
            names = ["foyer_hz1", "foyer_hc", "foyer_bres_r2", "foyer_nogate", "aimd2_paper"]
            for r in names:
                row = [r.replace("foyer_", "")]
                for t in THRESH:
                    hit = [d for d in _deltas.get(t, []) if d.startswith(r.replace("foyer_", "") + " ")]
                    row.append(hit[0].split()[-1] if hit else "")
                w.writerow(row)
            w.writerow([])
            w.writerow(["# 各阈值下的静态前沿锚点"])
            w.writerow(["threshold_s"] + ["anchor%d_wall,anchor%d_slo" % (i + 1, i + 1) for i in range(4)])
            for t in THRESH:
                flat = [x for e in _envs.get(t, []) for x in e]
                w.writerow([t] + flat)
        print("-> %s" % out_path)


if __name__ == "__main__":
    main()
