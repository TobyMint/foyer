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
# Match run_matrix's own pool guard (TURNSTILE_POOL_TOL, default 20) rather than
# demanding an exact match. The guard is what decides whether a run is recorded at
# all, so using a stricter rule here would drop runs the pipeline itself accepted —
# e.g. pois200_foyer_rl90 landed at 101,430, a 0.002% deviation that is far below
# the measurement noise on every axis this figure plots. A run outside the
# tolerance still refuses to plot.
POOL_TOL = 20
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
# static=4 + HiCache, added 2026-09-21 the day it landed. Without it the plotted
# frontier is simply wrong: it is the fastest arm in the table AND it has no
# controller, because HiCache removes the tradeoff cap2 and cap4 sit on -- hit
# 0.681 at 219.0 min, against cap2 0.677 at 310.5 and cap4 0.459 at 257.6.
PINK = "#e377c2"
# Guardrail arms and the conservative sweep — see the ROWS comment for why these
# are deliberately shades that read as "not the headline".
BROWN = "#8c564b"
TEAL = "#17becf"
OLIVE = "#bcbd22"


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
    if pool is None or abs(pool - EXPECT_POOL) > POOL_TOL:
        raise RuntimeError(
            f"{name}: pool {pool} is more than {POOL_TOL} from {EXPECT_POOL}, "
            f"refusing to plot")
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
    # "不限流 default" is deliberately NOT plotted: it is the no-control reference
    # and its 1.6% hit rate sits an order of magnitude below every policy here, so
    # it would force either a broken axis or a squashed cluster. It stays in the
    # numbers wherever the prose needs it.
    ("静态 cap1", "pois200_cap1", BLUE, None),
    ("静态 cap2 (n=3)", "pois200_cap2", BLUE, None),
    # This label used to read "cap3_r2 (实为 cap4)", on the theory that the runner's
    # cap race let 195/200 admissions land at active=3 so it ran at 4 in flight.
    # That reading was refuted from the source on 2026-09-22 (claim register R11):
    # the CAS is `while cur < cap` so cur == cap is unreachable, and log_admission
    # records cur + 1 -- so admissions at active=3 ARE the cap-3 signature.
    # cap3_r2 was a valid cap-3 run all along; cap3_fixed below is the same config
    # run a second time, and the two signatures are identical field by field.
    ("cap3_r2", "pois200_cap3_r2", BLUE, None),
    ("cap3_fixed", "pois200_cap3_fixed", BLUE, None),
    ("静态 cap4", "pois200_cap4", BLUE, None),
    ("静态 cap5", "pois200_cap5", BLUE, None),
    ("cap4 + HiCache", "pois200_cap4_hc", PINK, None),
    ("Foyer", "pois200_foyer", GREEN, None),
    ("Foyer + HiCache (n=3)", "pois200_foyer_hc", PURPLE, None),
    # The guardrail arms (2026-09-21). They exist to answer "was v3 too
    # conservative?" and the answer is no: both sit BELOW the static frontier,
    # while Foyer itself sits above it. Colouring them as degraded is deliberate —
    # a reader should see at a glance that these are ours-but-worse, not the
    # headline. rl99 has the higher target utilisation and the worse outcome, which
    # is the whole point of keeping it on the figure.
    ("Foyer rl90", "pois200_foyer_rl90", BROWN, None),
    ("Foyer rl99", "pois200_foyer_rl99", RED, None),
    ("Foyer t90", "pois200_foyer_t90", TEAL, None),
    ("Foyer t85", "pois200_foyer_t85", OLIVE, None),
    ("Concur（重调）", "pois200_aimd2", ORANGE, None),
    # The paper-parameter arm. Its 370.7 is the defensible Concur number (the
    # earlier 364.3 came from a process-reaper kill with unfinished metadata).
    ("Concur（原参数）", "pois200_aimd2_paper", GRAY, None),
]


def main():
    data = {}
    for label, run, _c, _s in ROWS:
        if run and os.path.isfile(os.path.join(RESULTS, run, "summary.json")):
            data[label] = load(run)

    fig = plt.figure(figsize=(15.5, 7.2))
    # Single linear axis, floored just under cap5 (27.5%). The no-control run is
    # not plotted anymore, which is what made a broken axis necessary before: with
    # everything shown the spread is 27.5-69.7 and one axis holds it comfortably.
    ax = fig.add_axes([0.055, 0.11, 0.40, 0.76])

    # ---- left: Pareto -------------------------------------------------------
    for label, run, colour, _s in ROWS:
        if label not in data:
            continue
        d = data[label]
        ax.scatter([d["wall"]], [d["hit"]], s=150, marker="o", color=colour, zorder=5)
    # Limits set BEFORE placing labels: collision avoidance needs to convert
    # offset points into data space, and that conversion depends on the limits.
    # (Both must be explicit. Auto-scaling would settle on different bounds than
    # the ones the label math used, and the labels would drift after the fact.)
    ax.set_ylim(20, 78)
    ax.set_xlim(200, 560)

    # Collision-aware label placement, same approach as fig_frontier.py. The old
    # version hand-set one offset per label, and it had gone stale: 静态 cap2's
    # label ran 65 minutes to the right and straight through Foyer t85's point,
    # which nobody noticed because the two labels overlapped into an unreadable
    # smear in the same colour family. Trying candidates in preference order and
    # rejecting any that lands on a label already placed fixes the whole class,
    # including labels added later.
    def _width(s, fs):
        # CJK is full-width, ASCII about 0.55em. Only used for overlap tests.
        return sum(1.0 if ord(c) > 0x2E80 else 0.55 for c in s) * fs

    placed = []
    for label, run, colour, _s in ROWS:
        if label not in data:
            continue
        d = data[label]
        x, y = d["wall"], d["hit"]
        xr = ax.get_xlim()[1] - ax.get_xlim()[0]
        yr = ax.get_ylim()[1] - ax.get_ylim()[0]
        bb = ax.get_window_extent()
        dpi = ax.figure.dpi
        xpt = xr / (bb.width * 72.0 / dpi)     # data units per point
        ypt = yr / (bb.height * 72.0 / dpi)
        w, h = _width(label, 10), 12.5
        for dx, dy, ha in ((11, 5, "left"), (11, -14, "left"), (-11, 5, "right"),
                           (-11, -14, "right"), (0, 14, "center"), (0, -20, "center"),
                           (11, 18, "left"), (-11, 18, "right"), (0, 26, "center"),
                           (11, -26, "left"), (-11, -26, "right"), (0, -34, "center")):
            lx = x + dx * xpt + (0 if ha == "center" else (w / 2 * xpt if dx > 0 else -w / 2 * xpt))
            ly = y + (dy + h / 2) * ypt
            if not any(abs(lx - px) < (w + pw) / 2 * xpt and abs(ly - py) < (h + ph) / 2 * ypt
                       for px, py, pw, ph in placed):
                break
        placed.append((lx, ly, w, h))
        ax.annotate(label, (x, y), textcoords="offset points", xytext=(dx, dy),
                    fontsize=10, color=colour, ha=ha)

    pts = sorted([(d["wall"], d["hit"]) for d in data.values()])
    frontier = []
    for w, h in pts:
        if not frontier or h > frontier[-1][1]:
            frontier.append((w, h))
    if len(frontier) > 1:
        ax.plot([p[0] for p in frontier], [p[1] for p in frontier], "--",
                color=GRAY, lw=1.6, zorder=1, label="当前数据的前沿")
    pending = [label for label, _r, _c, _s in ROWS if label not in data]
    if pending:
        note = "还没测的：" + "、".join(l.replace("静态 ", "") for l in pending)
        ax.text(0.5, 0.02, note, transform=ax.transAxes, ha="center", fontsize=9.5,
                color="0.25", bbox=dict(boxstyle="round,pad=0.45", fc="#f5f5f5", ec="0.8"))
    ax.set_xlabel("端到端墙钟 (min) —— 越低越好")
    ax.set_ylabel("前缀缓存命中率 (%) —— 越高越好", labelpad=8)
    ax.set_title("泊松到达档（200 会话，λ=0.04/s）", fontsize=13)
    ax.grid(alpha=0.3)

    ax.legend(loc="lower right", fontsize=9)

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

    fig.text(0.5, 0.022, "数据源：results/night/<run>/；墙钟取 metadata.wall_s，缺失时按步骤跨度计算；"
                         "SLO = TTFT<10s 的步骤占比。图只画池子校验通过的 run（与流水线同口径，容差 ±20 token）。",
             ha="center", fontsize=9, color="0.35")
    # Repeat counts, because the figure shows one point per config and someone
    # reading the prose ("three runs of Foyer + HiCache") would look for three
    # points. The spread is real but small next to a 250-550 minute axis -- 11.6
    # minutes is under 4% of the width -- so it is stated, not drawn.
    fig.text(0.5, 0.002, "n = 同配置独立重复次数，图中每档画其中一次；"
                         "各档跨次极差 < 5%（cap3_r2 与 cap3_fixed 是同配置的两条，两点都画出）。",
             ha="center", fontsize=8.5, color="0.45")
    fig.savefig(os.path.join(OUT, "fig_poisson_status.png"))
    print("wrote fig_poisson_status.png ->", OUT)
    for label, run, _c, _s in ROWS:
        print(("  ✅ " if label in data else "  ⏳ ") + label +
              ("" if label not in data else
               f"  wall={data[label]['wall']:.1f}min hit={data[label]['hit']:.1f}% "
               f"slo={data[label]['slo']:.1f}% ttft={data[label]['ttft_p50']:.2f}s"))


if __name__ == "__main__":
    main()
