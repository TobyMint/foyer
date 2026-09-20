#!/usr/bin/env python3
"""TTFT CDF for the Poisson main table — the threshold-free view of the same data.

Every curve is the fraction of successful steps whose TTFT is below x. p50, p90 and
SLO@10s are all readings of the same curves, so the plot answers "why 10 s?" without
arguing about thresholds: the healthy policies rise steeply and flatten out, the
uncontrolled run hugs zero until minutes. Refuses to plot a run whose KV pool is not
aligned. Usage: fig_ttft_cdf.py <results_dir> <out_dir>
"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = sys.argv[1] if len(sys.argv) > 1 else "/data/xbw/turnstile/results/night"
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
EXPECT_POOL = 101432
SLO_MS = 10000.0

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 140

# label, run, colour, linewidth
RUNS = [
    ("Foyer（主表行）", "pois200_foyer", "#2ca02c", 3.0),
    ("静态 cap2", "pois200_cap2", "#1f77b4", 2.4),
    ("静态 cap3", "pois200_cap3_r2", "#6baed6", 1.8),
    ("静态 cap4", "pois200_cap4", "#9ecae1", 1.8),
    ("Concur（重调参数）", "pois200_aimd2", "#ff7f0e", 2.2),
    ("不限流 default", "pois200_default", "#d62728", 2.6),
]


def load_ttft(run):
    d = os.path.join(RESULTS, run)
    pool = json.load(open(os.path.join(d, "metadata.json"))).get("pool_tokens")
    if pool != EXPECT_POOL:
        raise RuntimeError(f"{run}: pool {pool} != {EXPECT_POOL}, refusing to plot")
    out = []
    with open(os.path.join(d, "steps.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            if r.get("status") == "SUCCESS" and r.get("first_token_ms") is not None:
                out.append(r["first_token_ms"])
    return sorted(out)


def main():
    fig = plt.figure(figsize=(15.0, 6.8))
    ax = fig.add_axes([0.05, 0.115, 0.60, 0.775])
    rows = []
    for label, run, colour, lw in RUNS:
        if not os.path.isfile(os.path.join(RESULTS, run, "summary.json")):
            print(f"skip (unfinished): {label}")
            continue
        xs = load_ttft(run)
        n = len(xs)
        ys = [(i + 1) / n * 100 for i in range(n)]
        ax.step([x / 1000 for x in xs], ys, where="post", color=colour, lw=lw, label=label)
        p50 = next(x for x, y in zip(xs, ys) if y >= 50) / 1000
        p90 = next(x for x, y in zip(xs, ys) if y >= 90) / 1000
        slo = 100 * sum(1 for x in xs if x < SLO_MS) / n
        rows.append((label, colour, p50, p90, slo, n))

    ax.axvline(10, color="0.35", ls="--", lw=1.4)
    ax.annotate("SLO 阈值 10s\n（曲线在 10s 处的高度 = SLO 达标率）", (10, 8),
                xytext=(11.5, 18), fontsize=10, color="0.3",
                arrowprops=dict(arrowstyle="->", color="0.4", lw=1.1))
    ax.axhline(50, color="0.85", lw=1.0)
    ax.set_xscale("log")
    ax.set_xlim(0.5, 3600)
    ax.set_ylim(0, 101)
    ax.set_xticks([0.5, 1, 2, 5, 10, 30, 60, 300, 1800])
    ax.set_xticklabels(["0.5s", "1s", "2s", "5s", "10s", "30s", "1min", "5min", "30min"])
    ax.set_xlabel("单步 TTFT（对数坐标）—— 越低越好")
    ax.set_ylabel("累计占比（TTFT ≤ x 的步数比例）")
    ax.set_title("泊松到达档（200 会话，λ=0.04/s）：TTFT 累积分布（CDF）", fontsize=13)
    ax.grid(alpha=0.3, which="both")
    ax.legend(loc="center right", fontsize=9.5, framealpha=0.95)

    # right-hand panel: the same curves as numbers (p50 / p90 / SLO@10s)
    ax2 = fig.add_axes([0.685, 0.12, 0.295, 0.78])
    ax2.axis("off")
    body = [[lbl, f"{p50:.2f}s", f"{p90:.1f}s", f"{slo:.1f}%", f"{n}"]
            for lbl, _c, p50, p90, slo, n in rows]
    tbl = ax2.table(cellText=body,
                    colLabels=["策略", "p50", "p90", "SLO@10s", "步数"],
                    loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.0, 2.0)
    tbl.auto_set_column_width(col=list(range(5)))
    colours = {lbl: c for lbl, c, _p, _q, _s, _n in rows}
    for (row, col), cell in tbl.get_celld().items():
        cell.set_edgecolor("#dddddd")
        if row == 0:
            cell.set_facecolor("#eeeeee")
            cell.set_text_props(fontweight="bold")
            continue
        cell.set_facecolor("#fbfbfb")
        if col == 0:
            cell.set_text_props(color=colours[body[row - 1][0]], fontweight="bold")
    ax2.set_title("同一条曲线上的读数\n（读 SLO@10s = 曲线在 10s 处的高度）",
                  fontsize=11.5, pad=14)
    fig.text(0.5, 0.012, "TTFT 从请求提交给引擎算起（不含门外排队与暂停等待），"
                         "所有受控策略同口径；口径与阈值敏感性见 §4；每个 run 的池子已校验。",
             ha="center", fontsize=9, color="0.35")
    
    path = os.path.join(OUT, "fig_ttft_cdf.png")
    fig.savefig(path)
    print("wrote", path)
    for label, _c, p50, p90, slo, n in rows:
        print(f"  {label:<18} n={n:<4} p50={p50:6.2f}s p90={p90:7.1f}s SLO@10s={slo:5.1f}%")


if __name__ == "__main__":
    main()
