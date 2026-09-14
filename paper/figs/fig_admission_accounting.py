#!/usr/bin/env python3
"""Figure: capacity-accounting admission — the ledger test (illustrative walkthrough).

Left panel: composition of the ledger at a decision instant (sessions A,B admitted;
candidate C's need overflows the admission budget -> queue).
Right panel: ledger level across one scheduling episode (admit / reject / valve-shed / revive).
Illustrative numbers: pool 10w tokens, budget rho=0.85, margin m=1.15,
first prompt 1.7w, forecast growth 1.3w -> need per session (1.7+1.3)*1.15 = 3.45w.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

SURFACE = "#fcfcfb"
TXT, TXT2 = "#0b0b0b", "#52514e"
A_CUR, A_GRO, A_MAR = "#2a78d6", "#86b6ef", "#cde2fb"      # blue family (session A)
B_CUR, B_GRO, B_MAR = "#eb6834", "#f6a583", "#fbd0bd"      # orange family (session B)
CAND = "#d03b3b"                                            # status-critical (rejected test)
LEDGER = "#2a78d6"
GRID = "#e5e4e0"

plt.rcParams.update({
    "font.size": 9, "text.color": TXT, "axes.edgecolor": TXT2,
    "axes.labelcolor": TXT, "xtick.color": TXT2, "ytick.color": TXT2,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
})

fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.5, 4.0))
fig.subplots_adjust(left=0.055, right=0.985, top=0.86, bottom=0.14, wspace=0.18)

BUDGET, POOL = 8.5, 10.0

# ---------------- Left: ledger composition at a decision instant ----------------
segs = [  # (width, color, hatch, label)
    (1.7,  A_CUR, "",  "A: current 1.7"),
    (1.3,  A_GRO, "",  "A: growth 1.3"),
    (0.45, A_MAR, "",  "margin"),
    (1.7,  B_CUR, "",  "B: current 1.7"),
    (1.3,  B_GRO, "",  "B: growth 1.3"),
    (0.45, B_MAR, "",  ""),
    (3.45, CAND, "///", "C candidate: 3.45"),
]
x = 0.0
for w, c, h, lab in segs:
    axL.barh(0.5, w, left=x, height=0.34, color=c, hatch=h,
             edgecolor=SURFACE, linewidth=1.6)
    x += w
axL.axvline(BUDGET, color=TXT2, linestyle=(0, (4, 3)), linewidth=1.4)
axL.axvline(POOL, color=TXT2, linestyle=(0, (1, 2)), linewidth=1.0)
axL.text(BUDGET - 0.15, 0.16, "admission budget $\\rho\\,C_{pool}$ = 8.5w",
         ha="right", va="center", fontsize=8.5, color=TXT)
axL.text(POOL, 0.30, "$C_{pool}$ 10w", ha="right", va="center", fontsize=8.5, color=TXT2)
axL.text(x + 0.12, 0.5, "does not fit\n-> queue", ha="left", va="center",
         fontsize=9, color=CAND, fontweight="bold")
axL.annotate("", xy=(BUDGET + 0.05, 0.5), xytext=(x, 0.5),
             arrowprops=dict(arrowstyle="->", color=CAND, lw=1.2, alpha=0.0))  # spacer
# cumulative labels under the bar
axL.text(3.45 / 2, 0.28, "A: (1.7+1.3)×1.15 = 3.45w", ha="center", fontsize=8.5, color=TXT2)
axL.text(3.45 + 3.45 / 2, 0.28, "B: 3.45w", ha="center", fontsize=8.5, color=TXT2)
axL.set_xlim(0, 12.3)
axL.set_ylim(0, 1.15)
axL.set_yticks([])
axL.set_xticks(range(0, 11, 2))
axL.set_xticklabels([f"{v}w" for v in range(0, 11, 2)])
axL.set_xlabel("KV pool tokens (illustrative)")
axL.set_title("Ledger at a decision instant", fontsize=10.5, loc="left", color=TXT)
axL.legend(handles=[
    Patch(facecolor=A_CUR, label="session A"),
    Patch(facecolor=B_CUR, label="session B"),
    Patch(facecolor=A_GRO, label="growth reserve"),
    Patch(facecolor=A_MAR, label="safety margin"),
    Patch(facecolor=CAND, hatch="///", label="candidate C (rejected)"),
], loc="upper left", fontsize=8, frameon=False, ncol=2)
for s in ("top", "right", "left"):
    axL.spines[s].set_visible(False)

# ---------------- Right: ledger level across one episode ----------------
ts   = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 5.9]
vals = [0.0, 3.45, 6.9, 6.9, 8.3, 4.9, 4.4]
axR.plot(ts[:2], vals[:2], color=LEDGER, lw=2)
axR.plot(ts[1:5], vals[1:5], color=LEDGER, lw=2)
axR.plot(ts[4:], vals[4:], color=LEDGER, lw=2)
axR.plot([2.0, 2.6], [6.9, 10.35], color=CAND, lw=1.4, linestyle=(0, (3, 2)))
axR.plot([2.6], [10.35], marker="x", color=CAND, markersize=8, markeredgewidth=2)
axR.plot([2.6, 3.0], [10.35, 6.9], color=CAND, lw=1.4, linestyle=(0, (3, 2)))
axR.axhline(BUDGET, color=TXT2, linestyle=(0, (4, 3)), linewidth=1.4)
axR.text(0.05, BUDGET + 0.18, "admission budget 8.5w", fontsize=8.5, color=TXT)

for tx, ty, lab, dx, dy, ha in [
    (1.0, 3.45, "t1  A admit", 0.08, 0.15, "left"),
    (2.0, 6.9,  "t2  B admit", -0.08, 0.55, "right"),
    (2.6, 10.35, "t3  test C: 10.35 > 8.5\n-> queue", 0.15, -0.15, "left"),
    (3.6, 7.8,  "t4  sessions grow", 0.0, -0.95, "center"),
    (4.35, 4.9, "t5  valve: pause B\n(youngest first)", 0.1, 0.5, "left"),
    (5.9, 4.4,  "t6  A exits,\nC admits", 0.0, -1.35, "center"),
]:
    axR.plot([tx], [ty], marker="o", color=LEDGER, markersize=6,
             markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=5)
    axR.text(tx + dx, ty + dy, lab, fontsize=7.8, color=TXT, va="bottom", ha=ha)

axR.set_xlim(0, 6.6)
axR.set_ylim(0, 11.6)
axR.set_xticks(ts)
axR.set_xticklabels(["", "t1", "t2", "t3", "t4", "t5", "t6"])
axR.set_xlabel("time (one scheduling episode)")
axR.set_ylabel("ledger level (w tokens)")
axR.set_title("Ledger across one episode", fontsize=10.5, loc="left", color=TXT)
axR.grid(axis="y", color=GRID, linewidth=0.8)
axR.set_axisbelow(True)
for s in ("top", "right"):
    axR.spines[s].set_visible(False)

fig.suptitle("Capacity-accounting admission: admit s iff  m·(Σᵢ∈A(xᵢ+ĝᵢ) + xₛ+ĝₛ) ≤ ρ·C_pool",
             fontsize=11, color=TXT, x=0.055, ha="left", y=0.965)

out = "/root/paper/foyer/paper/figs/fig_admission_accounting.png"
fig.savefig(out, dpi=200, facecolor=SURFACE)
print("saved", out)
