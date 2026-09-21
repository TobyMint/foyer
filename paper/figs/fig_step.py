#!/usr/bin/env python3
"""The step: wall clock versus ENGINE concurrency, and its throughput counterpart.

This is the figure for the paper's first contribution, and it did not exist before
2026-09-21 because the step was not visible while the x axis was session-level
concurrency (which includes tool_wait and therefore compresses the range).

Two panels, same x:

  left   wall clock, showing two bands with a gap and no transition between them
  right  aggregate decode throughput, the independent verification, which steps in
         the same place. `default` is called out: it has the highest engine
         concurrency of any run and still lands in the LOW throughput cluster,
         because its 1.6% cache hit rate sends its compute to recompute.

Engine concurrency (mean of sglang:num_running_reqs) and throughput come from
metrics.csv; wall clock and hit rate come from metadata.json, so the wall clock here
matches every table in the paper. A run is plotted only if its KV pool passed the
same guard the pipeline uses.

    fig_step.py <results_dir> <out_dir>
"""
import csv
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = sys.argv[1] if len(sys.argv) > 1 else "/data/xbw/turnstile/results/night"
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
EXPECT_POOL = 101432
POOL_TOL = 20

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 140

STATIC_C, FOYER_C, FOYER_HC_C = "#1f77b4", "#2ca02c", "#9467bd"
CONCUR_C, GUARD_C, BAD_C = "#ff7f0e", "#8c564b", "#d62728"
GRAY = "#9a9a9a"

# (label, run dir, colour, label offset in the LEFT panel, ... in the RIGHT panel)
#
# Two offset sets because the two panels have different y values for the same x, so
# a single offset that clears a neighbour on one panel collides on the other. The
# crowded x-range is 1.03-1.14, where six arms sit within 0.11 of each other; those
# six are the reason this is hand-placed rather than automated.
ROWS = [
    ("静态 cap1", "pois200_cap1", STATIC_C, (9, 3), (9, 3)),
    ("静态 cap2", "pois200_cap2", STATIC_C, (-58, -3), (-54, 5)),
    ("cap3_r2 (实为 cap4)", "pois200_cap3_r2", STATIC_C, (-16, 10), (-112, 2)),
    ("静态 cap4", "pois200_cap4", STATIC_C, (-88, -6), (9, 4)),
    ("静态 cap5", "pois200_cap5", STATIC_C, (9, 8), (9, 3)),
    ("Foyer", "pois200_foyer", FOYER_C, (9, 3), (9, 4)),
    ("Foyer + HiCache", "pois200_foyer_hc", FOYER_HC_C, (9, -13), (9, -13)),
    ("Foyer t90", "pois200_foyer_t90", GUARD_C, (9, 3), (-48, 4)),
    ("Foyer t85", "pois200_foyer_t85", GUARD_C, (9, 3), (9, -12)),
    ("Foyer rl90", "pois200_foyer_rl90", GUARD_C, (9, 3), (9, 3)),
    ("Foyer rl99", "pois200_foyer_rl99", BAD_C, (9, 3), (9, 3)),
    ("Concur（重调）", "pois200_aimd2", CONCUR_C, (9, -14), (9, -13)),
    ("Concur（原参数）", "pois200_aimd2_paper", GRAY, (-120, -3), (-116, -3)),
    ("不限流 default", "pois200_default", BAD_C, (9, 8), (9, -14)),
]
DEFAULT_RUN = "pois200_default"


def load(run):
    d = os.path.join(RESULTS, run)
    mp, sp = os.path.join(d, "metrics.csv"), os.path.join(d, "summary.json")
    if not (os.path.exists(mp) and os.path.exists(sp)):
        return None
    try:
        meta = json.load(open(os.path.join(d, "metadata.json")))
        pool = meta.get("pool_tokens")
        if pool is None or abs(pool - EXPECT_POOL) > POOL_TOL:
            return None
    except (OSError, ValueError):
        return None

    ts, gen, running = [], [], []
    with open(mp) as fh:
        for row in csv.DictReader(fh):
            try:
                ts.append(float(row["ts"]))
                gen.append(float(row["sglang:generation_tokens_total"]))
                running.append(float(row["sglang:num_running_reqs"]))
            except (ValueError, TypeError, KeyError):
                pass
    if len(ts) < 500:
        return None
    span_min = (ts[-1] - ts[0]) / 60.0
    if span_min < 60:                       # partial run: still going or killed
        return None

    with open(sp) as fh:
        summ = json.load(fh)

    # Wall clock: metadata's own `wall_s` when the run finalised, otherwise the span
    # of the completed steps. The fallback exists because two arms (both of them
    # Concur's) were killed by the box's process-reaper and never wrote `wall_s`.
    # Falling back to the METRICS span instead would be wrong here — the metrics
    # scraper starts after the server is up and stops before teardown, so it reports
    # 370.7 for a run whose session replay actually took 364.0, and that number would
    # then disagree with every table in the paper. Flagged so the reader knows which
    # points carry an estimated wall rather than a recorded one.
    wall_s = meta.get("wall_s")
    estimated = wall_s is None
    if estimated:
        st = []
        try:
            with open(os.path.join(d, "steps.jsonl")) as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        st.append(json.loads(line).get("complete_timestamp"))
        except (OSError, ValueError):
            pass
        st = [t for t in st if t]
        if len(st) < 2:
            return None
        wall_min = (max(st) - min(st)) / 60.0
    else:
        wall_min = wall_s / 60.0

    return {
        "conc": sum(running) / len(running),
        "tok_s": max(gen) / (span_min * 60),
        "wall": wall_min,
        "estimated": estimated,
        # Prefix hit rate lives in the runner's replay block, not at the top level.
        "hit": 100.0 * (summ.get("replay", {}).get("server_prefix_hit_rate") or 0.0),
    }


def main():
    data = []
    for label, run, colour, off_l, off_r in ROWS:
        got = load(run)
        if got is None:
            print("skip %s (incomplete or pool not aligned)" % run)
            continue
        got.update(label=label, run=run, colour=colour, off_l=off_l, off_r=off_r)
        data.append(got)
    if not data:
        print("nothing to plot")
        return 1
    data.sort(key=lambda r: r["conc"])

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.6, 6.1))
    fig.subplots_adjust(left=0.060, right=0.988, top=0.845, bottom=0.135, wspace=0.20)

    # The divide the data shows. Not a fitted threshold: there is no observation
    # between conc 1.33 and 1.44, so any line in that gap describes the data equally
    # well. Drawn as a band to say so rather than pretending to a precise cut.
    for ax in (axL, axR):
        ax.axvspan(1.33, 1.44, color="#e8e6e0", zorder=0)
        ax.axvline(1.385, color=GRAY, lw=0.9, ls=":", zorder=1)
        ax.grid(True, color="#e8e6e0", lw=0.7, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.set_xlabel("引擎并发  mean(sglang:num_running_reqs)")

    for r in data:
        # An estimated wall clock gets a dashed ring rather than being silently
        # identical to a recorded one — the provenance of a number the whole figure
        # is about should be visible on the figure.
        ring = dict(edgecolor=r["colour"] if r["estimated"] else "white",
                    linewidth=1.4 if r["estimated"] else 0.9, linestyle="--" if r["estimated"] else "-")
        for ax, yk in ((axL, "wall"), (axR, "tok_s")):
            ax.scatter(r["conc"], r[yk], s=74, color=r["colour"], zorder=3, **ring)
        axL.annotate(r["label"], (r["conc"], r["wall"]), textcoords="offset points",
                     xytext=r["off_l"], fontsize=8.4, color=r["colour"], zorder=4)
        axR.annotate(r["label"], (r["conc"], r["tok_s"]), textcoords="offset points",
                     xytext=r["off_r"], fontsize=8.4, color=r["colour"], zorder=4)

    axL.set_ylabel("端到端墙钟 (min) — 越低越好")
    axL.set_title("墙钟对并发是台阶，不是曲线", fontsize=11.5, pad=13)
    axL.set_ylim(243, 552)
    axL.set_xlim(0.50, 1.93)
    # Shade the two bands themselves rather than floating a caption near them: the
    # claim IS that the data occupies two disjoint ranges, so the ranges should be
    # the thing you see. Every one of the 14 arms falls inside one band or the other.
    axL.axhspan(297.0, 340.0, color="#f4f2ec", zorder=0)
    axL.axhspan(257.0, 271.0, color="#f4f2ec", zorder=0)
    # Both captions live in the empty left margin: nothing is plotted below y=400 for
    # x<1.0, so the text never has to dodge a point.
    axL.text(0.545, 318.5, "台阶之下\n297–340 min\n组内互不单调",
             fontsize=8.8, color="#5a5a5a", ha="left", va="center", zorder=2)
    axL.text(0.545, 264.0, "台阶之上\n257–271 min\ncap3/cap4 在此", fontsize=8.8,
             color="#5a5a5a", ha="left", va="center", zorder=2)

    axR.set_ylabel("聚合解码吞吐 (tok/s) — 越高越好")
    axR.set_title("同一个台阶，用另一个独立的量复现", fontsize=11.5, pad=13)
    axR.set_ylim(19, 50)
    axR.set_xlim(0.50, 1.88)
    d = next((r for r in data if r["run"] == DEFAULT_RUN), None)
    if d:
        # Short, placed in the empty lower-middle, arrow to the point it describes.
        axR.annotate("并发最高，命中率却只有 1.6%\n算力被重算吃掉 → 落回低吞吐簇",
                     xy=(d["conc"], d["tok_s"]), xytext=(1.16, 24.4),
                     fontsize=8.8, color=BAD_C, ha="center",
                     arrowprops=dict(arrowstyle="->", color=BAD_C, lw=1.1,
                                     connectionstyle="arc3,rad=-0.18"),
                     zorder=4)

    fig.suptitle("引擎并发 ~1.4 处的台阶：墙钟与吞吐在同一位置同时跳变"
                 "（泊松 λ=0.04/s，200 会话，14 条策略）",
                 fontsize=12.6, y=0.972)
    fig.text(0.5, 0.018,
             "灰带 (1.33,1.44) 内无观测点，崖位未被分辨（cap3_fixed 是唯一定住它的测量；cap3_r2 实为 cap4）。"
             "吞吐分母经闸门校验，总生成 token 离散度 0.76%。虚线环 = 墙钟由步骤跨度估计。",
             ha="center", fontsize=7.8, color="#666")
    path = os.path.join(OUT, "fig_step.png")
    fig.savefig(path)
    print("wrote %s" % path)
    for r in data:
        print("  %-20s conc=%.2f wall=%.1f tok/s=%.1f hit=%.1f%%" %
              (r["label"], r["conc"], r["wall"], r["tok_s"], r["hit"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
