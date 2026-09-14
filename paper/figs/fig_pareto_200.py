#!/usr/bin/env python3
"""Figure: the headline result — quality vs throughput Pareto, 200-session tier.

x = end-to-end makespan (minutes, lower is better)
y = prefix cache hit rate (%, higher is better)

Points: the static concurrency sweep (cap1..cap5), the faithful Concur reproduction
(aimd2), the clairvoyant reservation baseline (budget2), and Foyer. Uncontrolled
("default") collapses with 121 failed steps and is marked as such.

Data: paper draft §5.2, aligned KV pool, night200 clean trace.
"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
TXT, TXT2 = "#0b0b0b", "#52514e"
BLUE = "#2a78d6"      # static sweep
ORANGE = "#eb6834"    # dynamic baselines
AQUA = "#1baf7a"      # Foyer
RED = "#d03b3b"       # collapse (status)
GREY = "#8a8984"
GRID = "#e5e4e0"

plt.rcParams.update({"font.size": 9, "text.color": TXT, "figure.facecolor": SURFACE})

fig = plt.figure(figsize=(10.5, 5.0))
ax = fig.add_axes([0.075, 0.12, 0.80, 0.76])

pts = [
    # name, wall_min, hit%, color, marker, label offset (dx, dy), size, ha
    ("cap1",    515.7, 69.9, BLUE,   "o", (0, 11),   8, "center"),
    ("cap2",    301.7, 67.0, BLUE,   "o", (0, 11),   8, "center"),
    ("cap3",    249.4, 59.0, BLUE,   "o", (0, 11),   8, "center"),
    ("cap4",    265.6, 45.1, BLUE,   "o", (10, -3),  8, "left"),
    ("cap5",    265.5, 28.0, BLUE,   "o", (10, -3),  8, "left"),
    ("aimd2",   291.4, 48.4, ORANGE, "s", (10, 3),   8, "left"),
    ("budget2", 247.4, 46.9, GREY,   "D", (-9, 2),   7, "right"),
    ("Foyer",   459.1, 69.8, AQUA,   "o", (0, 12),   11, "center"),
    ("Foyer r3", 555.3, 68.6, AQUA,  "o", (0, -17),  8, "center"),
]
for name, w, h, c, m, off, size, ha in pts:
    ax.plot([w], [h], marker=m, markersize=size, color=c,
            markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=5,
            linestyle="none")
    ax.annotate(name, (w, h), textcoords="offset points", xytext=off,
                fontsize=8.6, color=TXT, ha=ha, va="center", zorder=6)

# collapse point
ax.plot([228.1], [0.0], marker="x", markersize=11, color=RED,
        markeredgewidth=2.4, zorder=5)
ax.annotate("default (no admission control)\n228 min, 121 of 200 sessions failed",
            (228.1, 0.0), textcoords="offset points", xytext=(16, 16),
            fontsize=8.6, color=RED, zorder=6)

# Pareto frontier through the non-dominated deployable points
front = [(249.4, 59.0), (301.7, 67.0), (459.1, 69.8), (515.7, 69.9)]
ax.plot([p[0] for p in front], [p[1] for p in front], color=TXT2, lw=1.3,
        linestyle=(0, (5, 3)), zorder=2)
ax.annotate("Pareto frontier", (360, 66.2), fontsize=8.2, color=TXT2,
            ha="left", va="top", zorder=3)

# the two comparisons worth saying out loud
ax.text(487, 67.4, "same quality,\n11% less wall", fontsize=8.2, color=AQUA,
        ha="center", va="top")
ax.annotate("Concur repro is dominated\nby static cap3", xy=(296, 48.4),
            xytext=(360, 44.0), fontsize=8.2, color=ORANGE, ha="left",
            va="center", zorder=6,
            arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.1, alpha=0.8))

ax.set_xlim(210, 590)
ax.set_ylim(-6, 78)
ax.set_xlabel("end-to-end makespan (min)  —  lower is better", color=TXT)
ax.set_ylabel("prefix cache hit rate (%)  —  higher is better", color=TXT)
ax.set_title("200-session replay: quality vs throughput", fontsize=11, loc="left",
             color=TXT, pad=10)
ax.grid(color=GRID, lw=0.7)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

from matplotlib.lines import Line2D
ax.legend(handles=[
    Line2D([], [], marker="o", color="none", markerfacecolor=BLUE,
           markeredgecolor=BLUE, markersize=8, label="static cap sweep"),
    Line2D([], [], marker="s", color="none", markerfacecolor=ORANGE,
           markeredgecolor=ORANGE, markersize=8, label="dynamic baselines"),
    Line2D([], [], marker="o", color="none", markerfacecolor=AQUA,
           markeredgecolor=AQUA, markersize=9, label="Foyer"),
    Line2D([], [], marker="x", color=RED, markersize=9, markeredgewidth=2.2,
           label="collapse (failures)"),
], loc="lower right", fontsize=8.4, frameon=False, ncol=2,
   bbox_to_anchor=(1.0, 0.0), columnspacing=1.4)

fig.text(0.075, 0.015, "aligned KV pool (114,495 tok), clean trace (999 rows), single RTX 3090;  "
                       "aimd2 = faithful Concur reproduction, budget2 = clairvoyant (non-deployable) reference",
         fontsize=7.8, color=TXT2)

out = sys.argv[1] if len(sys.argv) > 1 else "/root/paper/foyer/paper/figs/fig_pareto_200.png"
fig.savefig(out, dpi=200, facecolor=SURFACE)
print("saved", out)
