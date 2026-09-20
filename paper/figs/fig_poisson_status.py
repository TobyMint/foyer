#!/usr/bin/env python3
"""Poisson arrival table status: everything measured so far + what is still missing.

Reads the run dirs directly (refuses to plot a run whose KV pool is not the aligned
101,432) and renders a Pareto plot next to a status table. Usage:
    fig_poisson_status.py <results_dir> <out_dir>
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

BLUE = "#1f77b4"
GREEN = "#2ca02c"
ORANGE = "#ff7f0e"
RED = "#d62728"
GRAY = "#b0b0b0"
# Foyer + HiCache gets its own hue: with the star marker gone, every point is a
# plain dot and colour is the only thing telling the two Foyer variants apart.
PURPLE = "#9467bd"


def read_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return rows


def load(name):
    d = os.path.join(RESULTS, name)
    meta = json.load(open(os.path.join(d, "metadata.json")))
    summ = json.load(open(os.path.join(d, "summary.json")))
    pool = meta.get("pool_tokens")
    if pool != EXPECT_POOL:
        raise RuntimeError(f"{name}: pool {pool} != {EXPECT_POOL}, refusing to plot")
    steps = read_jsonl(os.path.join(d, "steps.jsonl"))
    ttft = [r["first_token_ms"] for r in steps
            if r.get("status") == "SUCCESS" and r.get("first_token_ms") is not None]
    spans = [(r["submit_timestamp"], r["complete_timestamp"]) for r in steps
             if r.get("submit_timestamp") and r.get("complete_timestamp")]
    wall = (meta.get("wall_s") or 0) / 60 or (
        (max(c for _, c in spans) - min(s for s, _ in spans)) / 60 if spans else None)
    return {
        "wall": wall,
        "hit": 100 * (summ["replay"].get("server_prefix_hit_rate") or 0),
        "ttft_p50": (summ["replay"].get("ttft_ms_p50") or 0) / 1000.0,
        "slo": 100 * sum(1 for t in ttft if t < SLO_MS) / len(ttft) if ttft else None,
        "fails": summ["replay"].get("failed_steps"),
        "steps": len(steps),
    }


# (label, run name or None, colour, status note)
ROWS = [
    ("不限流 default", "pois200_default", RED, "排队中（正在跑）"),
    ("静态 cap1", "pois200_cap1", BLUE, "排队中"),
    ("静态 cap2", "pois200_cap2", BLUE, None),
    ("静态 cap3", "pois200_cap3_r2", BLUE, None),
    ("静态 cap4", "pois200_cap4", BLUE, None),
    ("静态 cap5", "pois200_cap5", BLUE, None),
    ("Foyer", "pois200_foyer", GREEN, None),
    ("Foyer + HiCache", "pois200_foyer_hc", PURPLE, None),
    ("Concur", "pois200_aimd2", ORANGE, None),
]


def main():
    data = {}
    for label, run, _c, _s in ROWS:
        if run and os.path.isfile(os.path.join(RESULTS, run, "summary.json")):
            data[label] = load(run)

    fig = plt.figure(figsize=(15.5, 7.2))
    ax = fig.add_axes([0.055, 0.11, 0.40, 0.76])

    # ---- left: Pareto -------------------------------------------------------
    for label, run, colour, _s in ROWS:
        if label not in data:
            continue
        d = data[label]
        ax.scatter([d["wall"]], [d["hit"]], s=150, marker="o",
                   color=colour, zorder=5)
        # Name only — the numbers live in the table on the right.
        dx, dy, ha = (11, 5, "left")
        if label.startswith("静态 cap2"):
            dx, dy, ha = (-11, 4, "right")
        ax.annotate(label, (d["wall"], d["hit"]), textcoords="offset points",
                    xytext=(dx, dy), fontsize=10, color=colour, ha=ha)
    pts = sorted([(d["wall"], d["hit"]) for d in data.values()])
    frontier = []
    for w, h in pts:
        if not frontier or h > frontier[-1][1]:
            frontier.append((w, h))
    if len(frontier) > 1:
        ax.plot([p[0] for p in frontier], [p[1] for p in frontier], "--",
                color=GRAY, lw=1.6, zorder=1, label="当前数据的前沿")
    pending = [label for label, _r, _c, _s in ROWS if label not in data]
    note = "还没测的：" + "、".join(l.replace("静态 ", "") for l in pending)
    ax.text(0.5, 0.02, note, transform=ax.transAxes, ha="center", fontsize=9.5,
            color="0.25", bbox=dict(boxstyle="round,pad=0.45", fc="#f5f5f5", ec="0.8"))
    ax.set_xlabel("端到端墙钟 (min) —— 越低越好")
    ax.set_ylabel("前缀缓存命中率 (%) —— 越高越好")
    ax.set_title("泊松到达档（200 会话，λ=0.04/s）", fontsize=13)
    ax.grid(alpha=0.3)
    ax.set_ylim(30, 78)
    ax.legend(loc="upper right", fontsize=9)

    # ---- right: status table -------------------------------------------------
    ax2 = fig.add_axes([0.50, 0.11, 0.47, 0.76])
    ax2.axis("off")
    cols = ["策略", "墙钟(min)", "命中%", "SLO%", "TTFT p50(s)"]
    body = []
    for label, run, colour, note in ROWS:
        if label in data:
            d = data[label]
            body.append([label, f"{d['wall']:.1f}", f"{d['hit']:.1f}",
                         f"{d['slo']:.1f}", f"{d['ttft_p50']:.2f}"])
        else:
            body.append([label, "—", "—", "—", "—"])
    tbl = ax2.table(cellText=body, colLabels=cols, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.0, 1.62)
    for (row, col), cell in tbl.get_celld().items():
        cell.set_edgecolor("#dddddd")
        if row == 0:
            cell.set_facecolor("#eeeeee")
            cell.set_text_props(fontweight="bold")
            continue
        label = body[row - 1][0]
        if label in data:
            cell.set_facecolor("#f7fff7")
        else:
            cell.set_facecolor("#fafafa")
            cell.set_text_props(color="0.45")
    ax2.set_title("全部泊松行的状态（统一 KV 池 101,432 token，池子逐 run 校验）",
                  fontsize=13, pad=18)

    fig.text(0.5, 0.015, "数据源：results/night/<run>/；墙钟取 metadata.wall_s，缺失时按步骤跨度计算；"
                         "SLO = TTFT<10s 的步骤占比。图只画池子校验通过的 run。",
             ha="center", fontsize=9, color="0.35")
    fig.savefig(os.path.join(OUT, "fig_poisson_status.png"))
    print("wrote fig_poisson_status.png ->", OUT)
    for label, run, _c, _s in ROWS:
        print(("  ✅ " if label in data else "  ⏳ ") + label +
              ("" if label not in data else
               f"  wall={data[label]['wall']:.1f}min hit={data[label]['hit']:.1f}% "
               f"slo={data[label]['slo']:.1f}% ttft={data[label]['ttft_p50']:.2f}s"))


if __name__ == "__main__":
    main()
