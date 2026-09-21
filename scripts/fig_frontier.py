#!/usr/bin/env python3
"""The Poisson frontier, drawn twice: against cache hit rate and against SLO.

Why two panels. Every claim about which policy is better in this project turns on
a threshold, and the threshold is chosen rather than measured:

    SLO >= 85%  ->  the candidates are Foyer+HiCache and cap2, and Foyer wins by 4.3%
    SLO >= 60%  ->  cap4+HiCache wins by 26%

Same runs, same wall clocks, opposite answer. A single-axis plot hides that, and
hiding it is how a chosen threshold gets mistaken for a result. So the same points
are drawn against both axes, with the Pareto frontier recomputed for each, and the
reader can see the crossing for themselves.

Points come from the run directories, not from tables.md, so a stale table cannot
propagate here. Pool is checked the same way run_matrix's guard checks it.

    fig_frontier.py <results_dir> <out_dir>
"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = sys.argv[1] if len(sys.argv) > 1 else "/data/xbw/turnstile/results/night"
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
EXPECT_POOL, POOL_TOL, SLO_MS = 101432, 20, 10000.0

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 140

BLUE, GREEN, ORANGE, RED = "#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"
GRAY, PURPLE, BROWN, TEAL = "#b0b0b0", "#9467bd", "#8c564b", "#17becf"
OLIVE, PINK = "#bcbd22", "#e377c2"

# (label, run, colour, show-label)
ROWS = [
    ("静态 cap1", "pois200_cap1", BLUE, True),
    ("静态 cap2", "pois200_cap2", BLUE, True),
    ("cap3_r2（实为 cap4）", "pois200_cap3_r2", BLUE, False),
    ("静态 cap4", "pois200_cap4", BLUE, True),
    ("静态 cap5", "pois200_cap5", BLUE, True),
    # static=4 + HiCache, landed 2026-09-21. It is the fastest arm in the table and
    # it has no controller: HiCache removes the tradeoff cap2 and cap4 sit on.
    ("cap4 + HiCache", "pois200_cap4_hc", PINK, True),
    ("Foyer", "pois200_foyer", GREEN, False),
    ("Foyer + HiCache", "pois200_foyer_hc", PURPLE, True),
    ("Foyer t90（预算版）", "pois200_foyer_t90", TEAL, False),
    ("Foyer t85（预算版）", "pois200_foyer_t85", OLIVE, False),
    ("Foyer rl90（红线版）", "pois200_foyer_rl90", BROWN, False),
    ("Foyer rl99（红线版）", "pois200_foyer_rl99", RED, True),
    ("Concur（重调）", "pois200_aimd2", ORANGE, False),
    ("Concur（原参数）", "pois200_aimd2_paper", GRAY, False),
]


def load(name):
    d = os.path.join(RESULTS, name)
    try:
        meta = json.load(open(os.path.join(d, "metadata.json")))
        summ = json.load(open(os.path.join(d, "summary.json")))["replay"]
    except (OSError, ValueError, KeyError):
        return None
    pool = meta.get("pool_tokens")
    if pool is None or abs(pool - EXPECT_POOL) > POOL_TOL:
        return None                       # same tolerance as run_matrix's own guard
    ttfts = []
    tmin = tmax = None
    try:
        with open(os.path.join(d, "steps.jsonl")) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("status") == "SUCCESS" and r.get("first_token_ms") is not None:
                    ttfts.append(r["first_token_ms"])
                c = r.get("complete_timestamp")
                if c:
                    tmin = c if tmin is None else min(tmin, c)
                    tmax = c if tmax is None else max(tmax, c)
    except OSError:
        return None
    if not ttfts:
        return None

    # wall_s is absent for runs killed before metadata was finalised -- the two
    # Concur arms, per ledger Q4. Without this fallback they plot at x=0, which does
    # not just look wrong, it puts them on the Pareto frontier as the fastest thing
    # measured. Fall back to the step span and MARK it, because the two numbers are
    # not the same quantity: the span starts at the first completed step and ends at
    # the last, so it excludes server start-up and drain.
    wall, span = (meta.get("wall_s") or 0) / 60.0, None
    if wall <= 0:
        if tmin is None or tmax is None or tmax <= tmin:
            return None
        wall, span = (tmax - tmin) / 60.0, True
    return {
        "wall": wall,
        "hit": 100.0 * summ.get("server_prefix_hit_rate", 0.0),
        "slo": 100.0 * sum(1 for x in ttfts if x < SLO_MS) / len(ttfts),
        "pool": pool,
        "span": span,
    }


def pareto(pts, xk, yk):
    """Upper-left frontier: keep a point only if nothing is faster AND higher."""
    out = []
    for p in sorted(pts, key=lambda q: q[xk]):
        if not out or p[yk] > out[-1][yk]:
            # drop anything the new point dominates
            while len(out) > 1 and out[-1][yk] <= p[yk]:
                out.pop()
            out.append(p)
    return out


def panel(ax, data, yk, ylabel, title, ann):
    pts = [(lbl, d) for lbl, d in data.items()]
    # Collision-aware label placement. Foyer+HiCache (297.6, 89.8) and cap2
    # (310.5, 89.5) are 13 minutes and 0.3 points apart, so the default "up and to
    # the right" put one label straight through the other. Rather than special-case
    # that pair, flip a label below its point when it lands within reach of one
    # already placed -- the same thing will happen again as runs are added.
    placed = []
    for lbl, run, colour, show in ROWS:
        if lbl not in data:
            continue
        d = data[lbl]
        ax.scatter([d["wall"]], [d[yk]], s=140, marker="o", color=colour,
                   zorder=5, edgecolor="white", linewidth=0.8)
        if show:
            # An asterisk marks a wall clock that came from the step span rather
            # than metadata.wall_s. They are different quantities, so the figure
            # says which rows are which instead of silently mixing them.
            #
            # Placement is collision-aware in DATA space, converted from offset
            # points through the axes' real size. Comparing raw point coordinates
            # is not enough and I tried it first: cap2 (310.5, 67.7) and
            # Foyer+HiCache (297.6, 69.7) are 2 points apart vertically but their
            # LABELS are ~10 characters wide, so they still overlapped.
            x, y = d["wall"], d[yk]
            xr = ax.get_xlim()[1] - ax.get_xlim()[0]
            yr = ax.get_ylim()[1] - ax.get_ylim()[0]
            bb = ax.get_window_extent()
            dpi = ax.figure.dpi
            xpt = xr / (bb.width * 72.0 / dpi)
            ypt = yr / (bb.height * 72.0 / dpi)
            for dx, dy in ((8, 6), (8, -16), (-80, 6), (-80, -16)):
                lx, ly = x + dx * xpt, y + dy * ypt
                if not any(abs(lx - px) < 0.075 * xr and abs(ly - py) < 0.045 * yr
                           for px, py in placed):
                    break
            placed.append((lx, ly))
            ax.annotate(lbl + ("*" if d.get("span") else ""),
                        (x, y), textcoords="offset points", xytext=(dx, dy),
                        ha="left" if dx > 0 else "right",
                        fontsize=8.6, color=colour)
    fr = pareto([d for _l, d in pts], "wall", yk)
    if len(fr) > 1:
        ax.plot([p["wall"] for p in fr], [p[yk] for p in fr], "--",
                color=GRAY, lw=1.6, zorder=3, label="当前数据的前沿")
    ax.set_xlabel("端到端墙钟 (min) —— 越左越好")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=11.5)
    ax.grid(True, color="#e8e6e0", lw=0.7)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(fontsize=8.4, loc="lower left", framealpha=0.9)
    # * = wall from the step span, not metadata.wall_s (two killed runs)
    if ann:
        ax.annotate(ann, xy=(0.98, 0.03), xycoords="axes fraction",
                    ha="right", va="bottom", fontsize=8.8, color="#444",
                    bbox=dict(boxstyle="round,pad=0.45", fc="#fff8e6", ec="#e0c98a"))


def main():
    data = {}
    for label, run, _c, _s in ROWS:
        d = load(run)
        if d:
            data[label] = d
    if not data:
        print("no runs with a valid pool in %s" % RESULTS)
        return 1

    fig, (a, b) = plt.subplots(1, 2, figsize=(14.6, 6.0))
    panel(a, data, "hit", "前缀缓存命中率 (%) —— 越高越好",
          "口径一：对缓存命中率",
          "SLO ≥ 85% 时 foyer_hc 领先 cap2 4.3%")
    panel(b, data, "slo", "SLO% (TTFT < 10s 的占比) —— 越高越好",
          "口径二：对 SLO",
          "SLO ≥ 60% 时 cap4+HiCache 领先 26%")
    fig.suptitle("同一批 run，两条口径，赢家不同 —— 门槛是选的不是测的",
                 fontsize=13, y=0.985)
    fig.tight_layout(rect=[0, 0.015, 1, 0.94])
    path = os.path.join(OUT, "fig_frontier.png")
    fig.savefig(path)
    print("wrote %s" % path)

    print("\n%-24s %8s %8s %8s" % ("run", "wall", "hit%", "SLO%"))
    for lbl, d in sorted(data.items(), key=lambda kv: kv[1]["wall"]):
        print("%-24s %8.1f %8.1f %8.1f" % (lbl, d["wall"], d["hit"], d["slo"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
