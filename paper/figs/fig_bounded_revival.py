#!/usr/bin/env python3
"""Figure: cost-bounded session revival (pillar 3) — the W/T promotion rule.

Left : the promotion plane. x = waited time W (since suspension), y = revival cost T.
       The diagonal is the iso-priority boundary W/T = beta; sessions below it are
       eligible. The vertical is the max-pause bound (liveness). The two bands are
       the two cost tiers: KV still in host (~0.1 s) vs KV discarded (recompute).
Right: the same four parked sessions under the current arrival order vs the W/T rule.

Illustrative numbers: beta = 1000 (dimensionless), W_max = 30 min.
Costs: load x*s/BW with 56 KB/token, PCIe Gen3 x16 ~ 12 GB/s (~0.1 s for 20K);
recompute x/R_prefill with ~4.7 K tok/s (~4.3 s for 20K). Estimates — see pillar-2 figure.
"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

SURFACE = "#fcfcfb"
TXT, TXT2 = "#0b0b0b", "#52514e"
ORANGE = "#eb6834"
RED = "#d03b3b"
GRID = "#e5e4e0"

plt.rcParams.update({"font.size": 9, "text.color": TXT, "figure.facecolor": SURFACE})

fig = plt.figure(figsize=(11.5, 4.3))
axL = fig.add_axes([0.055, 0.15, 0.42, 0.70])
axR = fig.add_axes([0.53, 0.05, 0.45, 0.86])
axR.axis("off")

BETA, WMAX = 1000.0, 30.0          # threshold, max-pause (minutes)
T_HOST, T_LOST = 0.1, 4.3          # seconds for a 20K session

# ---------------- left: the promotion plane ----------------
W = np.logspace(np.log10(0.3), np.log10(90), 200)          # minutes
T_line = (W * 60.0) / BETA                                   # seconds
axL.fill_between(W, 0.03, T_line, color="#eaf1fb", zorder=0)
axL.plot(W, T_line, color=TXT2, lw=1.6, zorder=2)
axL.axvline(WMAX, color=TXT2, lw=1.4, linestyle=(0, (4, 3)), zorder=2)

axL.set_xscale("log")
axL.set_yscale("log")
axL.set_xlim(0.3, 90)
axL.set_ylim(0.03, 30)
axL.set_xlabel("W — waited since suspension (minutes)", color=TXT)
axL.set_ylabel("T — revival cost (seconds)", color=TXT)

# tier bands
axL.axhline(T_HOST, color=ORANGE, lw=1.2, alpha=0.55, zorder=1)
axL.axhline(T_LOST, color=RED, lw=1.2, alpha=0.55, zorder=1)
axL.text(0.33, T_HOST * 1.25, "KV in host:  load back   $\\approx$0.1 s",
         fontsize=8, color=ORANGE, va="bottom")
axL.text(0.33, T_LOST * 1.25, "KV discarded: recompute $\\approx$4.3 s",
         fontsize=8, color=RED, va="bottom")

# boundary + deadline labels
axL.text(86, 7.5, "$W/T=\\beta$", fontsize=9.5, color=TXT2, ha="right", va="bottom")
axL.text(WMAX * 1.15, 0.036, "max-pause bound $W_{\\max}$\n(liveness)", fontsize=8,
         color=TXT2, ha="left", va="bottom")

# example parked sessions (label offsets chosen to avoid the band labels)
pts = [("A", 3.0, T_HOST, "1800", (8, -14)),
       ("B", 45.0, T_LOST, "628", (8, 6)),
       ("C", 0.5, T_HOST, "300", (6, -15)),
       ("D", 5.0, T_LOST, "70", (8, 6))]
for name, w, t, pi, off in pts:
    c = ORANGE if t == T_HOST else RED
    axL.plot([w], [t], marker="o", markersize=8, color=c,
             markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=5)
    axL.annotate(f"{name}  $\\Pi$={pi}", (w, t), textcoords="offset points",
                 xytext=off, fontsize=8, color=TXT)

axL.grid(color=GRID, lw=0.7, which="major")
axL.set_axisbelow(True)
for s in ("top", "right"):
    axL.spines[s].set_visible(False)

axL.legend(handles=[
    Patch(facecolor=ORANGE, label="parked in host (cheap)"),
    Patch(facecolor=RED, label="KV discarded (expensive)"),
    Patch(facecolor="#eaf1fb", edgecolor=TXT2, label="eligible region"),
], loc="upper left", fontsize=7.6, frameon=False)

# ---------------- right: ordering consequence ----------------
axR.text(0.0, 0.98, "Same four parked sessions, two orders", fontsize=10.5, color=TXT)
axR.text(0.0, 0.90, "promotion priority  $\\Pi = W/T$", fontsize=8.8, color=TXT2)

rows_cur = [("B", "45 min", "628", RED), ("D", "5 min", "70", RED),
            ("A", "3 min", "1800", ORANGE), ("C", "0.5 min", "300", ORANGE)]
rows_new = [("A", "3 min", "1800", ORANGE), ("B", "45 min", "628", RED),
            ("C", "0.5 min", "300", ORANGE), ("D", "5 min", "70", RED)]

axR.text(0.00, 0.80, "arrival order (today)", fontsize=9.2, color=TXT)
axR.text(0.54, 0.80, "W/T priority (new rule)", fontsize=9.2, color=TXT)
for col, rows in ((0.00, rows_cur), (0.54, rows_new)):
    for i, (name, w, pi, c) in enumerate(rows):
        y = 0.665 - i * 0.145
        axR.text(col, y, "■", fontsize=9, color=c, va="center")
        axR.text(col + 0.045, y, f"{i+1}.  {name}", fontsize=9.2, color=TXT, va="center")
        axR.text(col + 0.135, y, w, fontsize=8.2, color=TXT2, va="center")
        axR.text(col + 0.30, y, f"$\\Pi$={pi}", fontsize=8.2, color=TXT2, va="center")

axR.text(0.00, 0.03,
         "A host-parked session outranks a discarded one that waited 15$\\times$ longer;\n"
         "every session is revived at $W_{\\max}$ regardless — waiting stays bounded.",
         fontsize=8, color=TXT2, va="bottom")

fig.suptitle("Cost-bounded revival: promote by $W/T$ (waited time over revival cost), "
             "priced by storage tier", fontsize=11, color=TXT, x=0.055, ha="left", y=0.965)

out = sys.argv[1] if len(sys.argv) > 1 else "/root/paper/foyer/paper/figs/fig_bounded_revival.png"
fig.savefig(out, dpi=200, facecolor=SURFACE)
print("saved", out)
