#!/usr/bin/env python3
"""Cap-sweep cliff figure for the report: 25-session tier, aligned 101,432-token pool.
Left: prefix cache hit rate. Right: makespan (wall). Static caps 1-8 as a line;
adaptive policies as a separated marker group (they own no fixed cap)."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e8e7e3"
BLUE, ORANGE, AQUA, MUTED = "#2a78d6", "#eb6834", "#1baf7a", "#8a8a85"

caps = [1, 2, 3, 4, 5, 6, 7, 8]
hit = [68.2, 68.1, 64.9, 55.2, 36.6, 31.7, 7.5, 4.5]
wall = [63.3, 37.4, 30.4, 30.4, 28.7, 27.9, 32.1, 33.4]
adaptive = [  # (label, hit%, wall_min, color, short)
    ("Foyer (default cfg)", 66.8, 54.8, ORANGE, "Foyer"),
    ("Foyer (throttle fixed)", 64.4, 33.0, ORANGE, "Foyer-fix"),
    ("Concur (faithful)", 55.6, 35.5, AQUA, "Concur"),
    ("budget2 (oracle bound)", 52.4, 27.9, MUTED, "budget2"),
]

fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3), dpi=170)
fig.patch.set_facecolor(SURFACE)
AX = 9.2  # adaptive group x-anchor, beyond a divider

for ax, y, ylab, title in [
        (axes[0], hit, "Prefix cache hit rate (%)", "Quality: hit rate"),
        (axes[1], wall, "Makespan (min)", "Cost: end-to-end wall time")]:
    ax.set_facecolor(SURFACE)
    ax.plot(caps, y, "-o", color=BLUE, lw=2, ms=7, zorder=3)
    ax.axvline(8.75, color=GRID, lw=1, ls="--", zorder=1)
    xs = [AX + i * 1.65 for i in range(len(adaptive))]
    for xv, (lab, hv, wv, c, short) in zip(xs, adaptive):
        v = hv if y is hit else wv
        ax.scatter([xv], [v], s=90, color=c, zorder=3, edgecolors=SURFACE, linewidths=1.5)
        ax.annotate(short, (xv, v), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=8.5, color=INK2)
    ax.set_xticks(caps + xs)
    ax.set_xticklabels([f"cap{c}" for c in caps] + [short.replace("\n", " ")
                       for *_, short in adaptive], fontsize=8)
    for t, (_, _, _, c, _) in zip(ax.get_xticklabels()[8:], adaptive):
        t.set_color(c)
    ax.set_xlim(0.4, 15.6)
    ax.set_ylabel(ylab, fontsize=10, color=INK)
    ax.set_title(title, fontsize=11, color=INK, loc="left")
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)

# selective direct labels on the cliff
axes[0].annotate("55.2", (4, 55.2), textcoords="offset points", xytext=(-16, 4),
                 ha="center", fontsize=8.5, color=INK)
axes[0].annotate("36.6", (5, 36.6), textcoords="offset points", xytext=(16, -4),
                 ha="center", fontsize=8.5, color=INK)
axes[0].annotate("7.5", (7, 7.5), textcoords="offset points", xytext=(0, 8),
                 ha="center", fontsize=8.5, color=INK)
axes[0].annotate("cliff", (6.2, 52), fontsize=9.5, color=ORANGE, style="italic",
                 ha="center")

fig.suptitle("Concurrency-cap sweep, 25-session tier (aligned 101,432-token KV pool, RTX 3090)",
             fontsize=11.5, color=INK, x=0.02, ha="left")
plt.tight_layout(rect=[0, 0, 1, 0.93])
plt.savefig("/data/xbw/turnstile/paper/fig_cap_cliff_25tier.png", facecolor=SURFACE)
print("saved")
