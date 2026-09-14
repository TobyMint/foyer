#!/usr/bin/env python3
"""Figure: state-preserving session suspension (host-tier KV residency) — pillar 2.

Left  : session lifecycle. Queue -> Device (L1) <-> Host tier (L2) -> Done.
        The red dashed arrow is the counterfactual every existing engine takes:
        evicted KV is discarded, so the session is recomputed from scratch.
Right : per-event cost of returning a 20K-token session — load back vs recompute.
        Estimates only (direct measurement pending), stated on the figure.

Numbers: KV = 56 KB/token (7B, GQA-4, fp16) -> 20K tokens ~ 1.1 GB;
PCIe Gen3 x16 ~ 12 GB/s; prefill ~ 4.7 K tok/s (backed out of our own TTFT data).
Measured anchor: cap6 collapse, hit 31.7% -> 64.1% with the host tier on.
"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Patch

SURFACE = "#fcfcfb"
TXT, TXT2 = "#0b0b0b", "#52514e"
BLUE, BLUE_L = "#2a78d6", "#cde2fb"
ORANGE, ORANGE_L = "#eb6834", "#fbd0bd"
RED = "#d03b3b"

plt.rcParams.update({
    "font.size": 9, "text.color": TXT,
    "figure.facecolor": SURFACE,
})

fig = plt.figure(figsize=(11.5, 4.2))
axL = fig.add_axes([0.02, 0.05, 0.60, 0.84])
axL.set_xlim(0, 10)
axL.set_ylim(0, 7)
axL.axis("off")
axR = fig.add_axes([0.76, 0.28, 0.22, 0.50])


def box(ax, x, y, w, h, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.06,rounding_size=0.18",
                                linewidth=1.7, edgecolor=ec, facecolor=fc,
                                mutation_aspect=1))


def arrow(ax, p, q, color, style="-|>", ls="-", rad=0.0, lw=1.9):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=13,
                                 linewidth=lw, color=color, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}",
                                 shrinkA=0, shrinkB=0, zorder=3))


# ---- boxes ----------------------------------------------------------------
box(axL, 0.15, 3.15, 2.30, 1.50, "#ffffff", TXT2)          # queue
box(axL, 3.60, 3.15, 3.00, 1.50, BLUE_L, BLUE)             # device
box(axL, 3.60, 0.35, 3.00, 1.50, ORANGE_L, ORANGE)         # host
box(axL, 7.95, 3.15, 1.90, 1.50, "#ffffff", TXT2)          # done

axL.text(1.30, 4.10, "Queue", ha="center", fontsize=10.5, color=TXT)
axL.text(1.30, 3.72, "waiting\nsessions", ha="center", va="top", fontsize=8.5, color=TXT2)

axL.text(5.10, 4.30, "Device (L1)", ha="center", fontsize=10.5, color=TXT)
axL.text(5.10, 3.90, "KV pool — running", ha="center", va="top", fontsize=8.5, color=TXT2)

axL.text(5.10, 1.50, "Host tier (L2)", ha="center", fontsize=10.5, color=TXT)
axL.text(5.10, 1.10, "parked KV — history kept\n11.6 GB $\\approx$ 10 $\\times$ 20K sessions",
         ha="center", va="top", fontsize=8.5, color=TXT2)

axL.text(8.90, 4.10, "Done", ha="center", fontsize=10.5, color=TXT)
axL.text(8.90, 3.72, "released", ha="center", va="top", fontsize=8.5, color=TXT2)

# ---- arrows ---------------------------------------------------------------
arrow(axL, (2.45, 3.90), (3.60, 3.90), BLUE)
axL.text(3.02, 4.62, "admit", ha="center", fontsize=8.5, color=TXT)
axL.text(3.02, 4.36, "(capacity ledger,\n§3.1)", ha="center", va="top",
         fontsize=7.8, color=TXT2)

arrow(axL, (5.60, 3.15), (5.60, 1.85), ORANGE)
axL.text(5.78, 2.50, "suspend: offload KV\n(device freed, history kept)",
         ha="left", va="center", fontsize=8.5, color=TXT)

arrow(axL, (4.60, 1.85), (4.60, 3.15), ORANGE)
axL.text(4.42, 2.50, "revive: load back\nno recompute", ha="right", va="center",
         fontsize=8.5, color=TXT)

arrow(axL, (6.66, 3.90), (7.95, 3.90), TXT2)
axL.text(7.30, 4.16, "complete", ha="center", fontsize=8.5, color=TXT2)

# counterfactual: discard -> recompute (what engines do today)
arrow(axL, (7.10, 3.15), (8.15, 2.55), RED, ls=(0, (4, 2.5)), rad=-0.25)
axL.text(8.20, 2.30, "existing engines:\n"
                     "KV discarded $\\rightarrow$ recompute\n(~4.3 s per 20K, est.)",
         ha="left", va="top", fontsize=7.8, color=RED)

axL.legend(handles=[
    Patch(facecolor=BLUE_L, edgecolor=BLUE, label="in device (L1)"),
    Patch(facecolor=ORANGE_L, edgecolor=ORANGE, label="parked in host (L2)"),
    Patch(facecolor="none", edgecolor=RED, linestyle=(0, (4, 2.5)),
          label="discard path (today)"),
], loc="upper left", fontsize=8, frameon=False, bbox_to_anchor=(0.0, 1.0))

axL.text(0.15, 0.02,
         "measured anchor: at the collapse configuration (cap6, 25 sessions) the host tier "
         "lifts hit rate 31.7% $\\rightarrow$ 64.1%",
         ha="left", va="bottom", fontsize=7.8, color=TXT2)

# ---- right panel: per-event cost ------------------------------------------
labels = ["Recompute\nafter discard", "Load back\nfrom host"]
vals = [4.3, 0.1]
colors = [RED, ORANGE]
ypos = [1.0, 0.0]
for y, v, c in zip(ypos, vals, colors):
    axR.barh(y, v, height=0.42, color=c)
axR.text(4.45, 1.0, "$\\approx$4.3 s  (est.)", va="center", ha="left",
         fontsize=9, color=TXT)
axR.text(0.28, 0.0, "$\\approx$0.1 s  (est.)", va="center", ha="left",
         fontsize=9, color=TXT)
axR.set_yticks(ypos)
axR.set_yticklabels(labels, fontsize=8.5, color=TXT)
axR.set_xlim(0, 6.0)
axR.set_title("Cost of one return\n(20K session, seconds)", fontsize=10.5,
              loc="left", color=TXT)
axR.grid(axis="x", color="#e5e4e0", linewidth=0.8)
axR.set_axisbelow(True)
for s in ("top", "right", "left"):
    axR.spines[s].set_visible(False)
axR.tick_params(axis="y", length=0)

fig.text(0.74, 0.20, "estimated: 56 KB/token $\\times$ 20K $\\approx$ 1.1 GB\n"
                     "PCIe Gen3 x16 $\\approx$ 12 GB/s; prefill $\\approx$ 4.7 K tok/s\n"
                     "— direct measurement pending",
         fontsize=7.5, color=TXT2, va="top", ha="left")

fig.suptitle("State-preserving suspension: evicted sessions park in the host tier "
             "instead of being discarded",
             fontsize=11, color=TXT, x=0.02, ha="left", y=0.975)

out = sys.argv[1] if len(sys.argv) > 1 else "/root/paper/foyer/paper/figs/fig_host_tier.png"
fig.savefig(out, dpi=200, facecolor=SURFACE)
print("saved", out)
