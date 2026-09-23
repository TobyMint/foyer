#!/usr/bin/env python3
"""重算墙钟的两段分解，并诊断「busy+idle != wall」的那部分时间去哪了。

论文 C1 主张墙钟 = busy + idle。之前 decomp.csv 是手算的，本脚本把它变成
可复现的，并且把残差单独报出来——残差大的 run 就是分解不可信的那条。
"""
import csv, json, os, sys, glob

def load_metrics(p):
    rows = []
    with open(p) as f:
        hdr = f.readline().strip().split(",")
        if "sglang:num_running_reqs" not in hdr:
            return None, None
        i_ts = hdr.index("ts"); i_rn = hdr.index("sglang:num_running_reqs")
        for line in f:
            c = line.rstrip("\n").split(",")
            if len(c) <= max(i_ts, i_rn): continue
            try: ts = float(c[i_ts])
            except ValueError: continue
            v = c[i_rn]
            try: rn = float(v)
            except ValueError: rn = None
            rows.append((ts, rn))
    return rows, hdr

def decompose(rows, sample=5.0):
    """把相邻样本间的间隔按前一个样本的状态归类。"""
    span = rows[-1][0] - rows[0][0]
    busy = idle = other = 0.0
    nan_gap = 0.0
    longest_idle = 0.0; cur = 0.0
    for (t0, r0), (t1, _) in zip(rows, rows[1:]):
        dt = t1 - t0
        if dt <= 0 or dt > sample * 3:      # 采样断档，单独记
            nan_gap += dt; cur = 0.0; continue
        if r0 is None:
            other += dt; cur = 0.0
        elif r0 == 0:
            idle += dt; cur += dt; longest_idle = max(longest_idle, cur)
        else:
            busy += dt; cur = 0.0
    return dict(span_min=span/60, busy_min=busy/60, idle_min=idle/60,
                other_min=other/60, gap_min=nan_gap/60,
                idle_pct=100*idle/span if span else 0, longest_idle_s=longest_idle)

def main(root, runs):
    print("%-18s %8s %8s %8s %8s %8s %7s %8s" %
          ("run", "wall", "busy", "idle", "other", "gap", "idle%", "resid"))
    print("-" * 82)
    for r in runs:
        p = os.path.join(root, r, "metrics.csv")
        if not os.path.exists(p): print("%-18s  (no metrics.csv)" % r); continue
        rows, _ = load_metrics(p)
        if not rows: print("%-18s  (no num_running_reqs column)" % r); continue
        d = decompose(rows)
        sj = os.path.join(root, r, "summary.json")
        wall = None
        if os.path.exists(sj):
            try:
                j = json.load(open(sj))
                wall = j.get("wall_min") or j.get("result", {}).get("wall_min")
            except Exception: pass
        resid = (d["span_min"] - d["busy_min"] - d["idle_min"] - d["other_min"] - d["gap_min"])
        print("%-18s %8.1f %8.1f %8.1f %8.1f %8.1f %7.1f %8.2f" %
              (r.replace("pois200_", ""), d["span_min"], d["busy_min"], d["idle_min"],
               d["other_min"], d["gap_min"], d["idle_pct"], resid))

if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "/data/xbw/turnstile/results/night"
    runs = sys.argv[2:] or sorted(os.path.basename(os.path.dirname(p))
                                  for p in glob.glob(os.path.join(root, "*", "metrics.csv")))
    main(root, runs)
