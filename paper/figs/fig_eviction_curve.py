#!/usr/bin/env python3
"""Eviction-vs-quality curve: how much pressure-driven eviction does each policy buy,
and what does it cost?

Every run records sglang:evicted_tokens_total, but every run also evicts a floor of
~0.98M tokens from ordinary session-end cleanup (even cap1, at concurrency 1, evicts
981,957). So the informative quantity is the EXCESS over that floor: eviction caused
by memory pressure rather than by a session finishing. Both panels share that x-axis,
normalised per session so the 25- and 200-session tiers are comparable.

The point of the figure: zero pressure eviction is not the optimum. cap1 (no pressure
eviction) is the slowest policy on the board; the knee sits near 4K tokens/session.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e8e7e3"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
KNEE = 4.0

# (x = excess eviction per session in K tokens, hit%, wall_min)
S25 = [(0.0, 68.2, 63.3), (0.08, 68.1, 37.4), (4.1, 64.9, 30.4), (16.4, 55.2, 30.4),
       (39.9, 36.6, 28.7), (47.1, 31.7, 27.9), (79.0, 7.5, 32.1), (82.8, 4.5, 33.4)]
S200 = [(41.1, 69.9, 515.7), (45.2, 67.0, 301.7), (56.7, 59.0, 249.4),
        (76.6, 45.1, 265.6), (101.3, 28.0, 265.5)]

# every marker carries its own label spec: (x, hit%, wall, text, colour, dx, dy, ha, panel)
# panel: "q" = quality only, "c" = cost only, "b" = both
MARKERS = [
    (1.8,  66.8,  54.8, "Foyer",        BLUE,     0, -17, "center", "b"),
    (5.2,  66.3,  42.0, "Foyer fix",    BLUE,     8, 10, "left",   "b"),
    (15.9, 55.6,  35.5, "Concur",       BLUE,    10, -4, "left",   "b"),
    (43.5, 69.8, 459.1, "Foyer old",    ORANGE, -10,  8, "right",  "b"),
    (48.3, 64.8, 311.4, "Foyer",        ORANGE,   0, -18, "center", "b"),
    (71.7, 48.4, 291.4, "Concur",       ORANGE,   0, -18, "center", "b"),
    (52.8, 64.1,  22.8, "cap6+HiCache", AQUA,    11,   4, "left",   "b"),
]
END = {  # direct end-labels for the two sweeps: (x, y25, y200, text, colour, dx, dy, ha, va)
    "q": [(82.8, 4.5, None, "25-session sweep\ncap1 → cap8", BLUE, 10, 0, "left", "center"),
          (101.3, 28.0, None, "200-session sweep\ncap1 → cap5", ORANGE, 8, 6, "left", "center")],
    "c": [(82.8, 33.4, None, "25-session sweep", BLUE, 8, -16, "left", "top"),
          (101.3, 265.5, None, "200-session sweep", ORANGE, 6, 0, "left", "center")],
}


def draw(ax, yi, panel):
    ax.plot([p[0] for p in S25], [p[yi] for p in S25], "-o", color=BLUE, lw=2, ms=6,
            markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=3)
    ax.plot([p[0] for p in S200], [p[yi] for p in S200], "-o", color=ORANGE, lw=2, ms=6,
            markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=3)

    for (x, y, w, text, col, dx, dy, ha, on) in END[panel]:
        ax.annotate(text, (x, y), textcoords="offset points", xytext=(dx, dy),
                    ha=ha, va="center", fontsize=8.5, color=col, linespacing=1.35)

    hi = yi == 0   # marker index into MARKERS for the value we plot
    for (x, h, w, text, col, dx, dy, ha, on) in MARKERS:
        v = h if yi == 0 else w
        ax.scatter([x], [v], s=105, marker=("s" if text.startswith("cap6") else "D"),
                   color=col, edgecolors=SURFACE, linewidths=1.5, zorder=4)
        ax.annotate(text, (x, v), textcoords="offset points", xytext=(dx, dy),
                    ha=ha, fontsize=8, color=col, fontweight="bold", zorder=5)

    ax.axvline(KNEE, color=INK2, lw=1.1, ls="--", zorder=1, alpha=0.6)
    ax.annotate("knee", (KNEE, ax.get_ylim()[1]), textcoords="offset points",
                xytext=(4, -12), fontsize=8.5, color=INK2, ha="left", va="top")
    ax.set_xlim(-8, 152)
    ax.set_xlabel("pressure-driven eviction per session (K tokens)", fontsize=9.5, color=INK)
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)


fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8), dpi=170)
fig.patch.set_facecolor(SURFACE)
for ax in axes:
    ax.set_facecolor(SURFACE)

draw(axes[0], 0, "q")
axes[0].set_ylabel("Prefix cache hit rate (%)", fontsize=10, color=INK)
axes[0].set_title("Quality", fontsize=11.5, color=INK, loc="left")
axes[0].set_ylim(-4, 78)

draw(axes[1], 1, "c")
axes[1].set_ylabel("Makespan (min)", fontsize=10, color=INK)
axes[1].set_title("Cost", fontsize=11.5, color=INK, loc="left")
axes[1].set_ylim(-25, 570)

fig.suptitle("Zero eviction is not the optimum — cap1, the only policy with no pressure "
             "eviction, is also the slowest", fontsize=11.5, color=INK, x=0.006, ha="left", y=0.985)
fig.tight_layout(rect=[0, 0, 1, 0.945])
fig.savefig("fig_eviction_curve.png", facecolor=SURFACE)
print("wrote fig_eviction_curve.png")
