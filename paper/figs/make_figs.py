#!/usr/bin/env python3
"""生成论文用的图（PDF，IEEE 尺寸）。

数据全部来自 ../data/*.csv，那些文件是从实验机 run_summary.py / metrics.csv 导出的实测值。
每个图在下面都有 docstring 说明它支撑哪条主张。

用法:  python3 make_figs.py
"""
import csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

plt.rcParams.update({
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8,
    "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.grid": True, "grid.alpha": 0.3, "grid.linewidth": 0.4,
    "figure.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})

C_STATIC, C_STATIC_HC, C_FOYER = "#4C72B0", "#55A868", "#C44E52"


def load(name):
    with open(os.path.join(DATA, name)) as f:
        rows = [l for l in f if not l.startswith("#")]
    return list(csv.DictReader(rows))


# ---------------------------------------------------------------- 图 1：前沿
def fig_frontier():
    """C4：九条 Foyer 变体零条越过静态前沿。

    横轴墙钟、纵轴 SLO。方=静态 cap，圆=Foyer。折线是静态点的上左包络，
    **落在折线下方或线上 = 没有越过**——因为按时间片混合两个 cap 就能逼近线上任一点。
    """
    rows = [r for r in load("runs.csv") if r["tier"] == "200" and int(r["steps"]) >= 999]
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    front = sorted([(float(r["wall_min"]), float(r["slo_pct"]))
                    for r in rows if r["family"].startswith("static")])
    # 上左包络
    env, best = [], -1
    for w, s in front:
        if s > best:
            env.append((w, s)); best = s
    ax.plot(*zip(*env), "-", color="0.35", lw=0.9, zorder=1, label="static envelope")
    for fam, c, mk, lab in [("static", C_STATIC, "s", "static cap"),
                            ("static_hc", C_STATIC_HC, "^", "static cap + HiCache"),
                            ("foyer", C_FOYER, "o", "Foyer")]:
        xs = [float(r["wall_min"]) for r in rows if r["family"] == fam]
        ys = [float(r["slo_pct"]) for r in rows if r["family"] == fam]
        ax.scatter(xs, ys, c=c, marker=mk, s=26, zorder=3, label=lab,
                   edgecolors="white", linewidths=0.4)
    ax.annotate("cap4+HC", (213.0, 63.4), (222, 52), fontsize=6,
                arrowprops=dict(arrowstyle="-", lw=0.5, color="0.4"))
    ax.annotate("cap3+HC", (236.4, 81.1), (247, 88), fontsize=6,
                arrowprops=dict(arrowstyle="-", lw=0.5, color="0.4"))
    ax.annotate("best Foyer\n(on the line)", (255.8, 84.8), (272, 74), fontsize=6,
                arrowprops=dict(arrowstyle="-", lw=0.5, color="0.4"))
    ax.set_xlabel("end-to-end wall clock (min)")
    ax.set_ylabel("SLO attainment (\\%)")
    ax.set_ylim(20, 100); ax.set_xlim(195, 545)
    ax.legend(loc="lower right", frameon=False)
    fig.savefig(os.path.join(HERE, "fig1_frontier.pdf"))
    plt.close(fig)


# ------------------------------------------------------- 图 2：墙钟两段分解
def fig_decomp():
    """C1/C3：墙钟 = 有效工作 + 空转；空转 7.4%–36.3%，且与并发负相关。

    空转的成因是结构性的——会话在 tool_wait 期间不发请求，而存活会话只有约 2 个。
    注意 bres：它把空转压到 10.1%，但有效工作涨到 271 分钟，两件事互相抵消。
    """
    rows = sorted(load("decomp.csv"), key=lambda r: float(r["wall_min"]))
    rows = [r for r in rows if r["idle_pct"]]
    y = range(len(rows))
    busy = [float(r["busy_min"]) for r in rows]
    idle = [float(r["idle_min"]) for r in rows]
    fig, ax = plt.subplots(figsize=(3.5, 3.0))
    ax.barh(y, busy, color="#7FA8D0", label="busy (engine running)", height=0.62)
    ax.barh(y, idle, left=busy, color="#E8A33D", label="idle (no request in flight)", height=0.62)
    ax.set_yticks(list(y))
    ax.set_yticklabels([r["run"].replace("pois200_", "") for r in rows], fontsize=6)
    ax.invert_yaxis()
    ax.set_xlabel("wall clock (min)")
    for i, r in enumerate(rows):
        ax.text(float(r["wall_min"]) + 6, i, "%.0f%%" % float(r["idle_pct"]),
                va="center", fontsize=6, color="#8a5a10")
    ax.legend(loc="upper right", frameon=False, bbox_to_anchor=(1.0, 1.0))
    fig.savefig(os.path.join(HERE, "fig2_decomp.pdf"))
    plt.close(fig)


# --------------------------------------------------- 图 3：步时间的两个测量
def fig_steptime():
    """C2：步时间由两个【独立】方法测到，两者排序一致。

    这一点必须在论文里说清楚：`metrics.csv` 的 itl/e2e/ttft 列全是空的，
    所以步时间不是引擎直采的。方法一是从墙钟反推的导出量，方法二是逐请求的
    decode 间隔——两者系统性差 8–16%，但 cap5 和 bres 在两个方法里都是异常值。
    """
    rows = [r for r in load("decomp.csv") if r["step_back_ms"]]
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    xs = [float(r["running"]) for r in rows]
    ax.scatter(xs, [float(r["step_back_ms"]) for r in rows], marker="o", s=28,
               facecolors="none", edgecolors=C_FOYER, linewidths=0.9,
               label="back-derived (wall $\\times$ conc / tokens)")
    ax.scatter([x + 0.012 for x in xs], [float(r["step_perreq_ms"]) for r in rows],
               marker="x", s=26, color=C_STATIC, linewidths=1.0,
               label="per-request (independent)")
    for r in rows:
        ax.annotate(r["run"].replace("pois200_", "").replace("foyer_", "F:"),
                    (float(r["running"]), float(r["step_back_ms"])),
                    (3, 4), textcoords="offset points", fontsize=6)
    ax.axhline(16.2, ls=":", lw=0.8, color="0.4")
    ax.text(1.02, 16.6, "weights-read floor (15.2 GB / 936 GB/s)",
            fontsize=6, color="0.35")
    ax.set_xlabel("mean running requests")
    ax.set_ylabel("step time (ms)")
    ax.set_ylim(12, 40)
    ax.legend(loc="upper left", frameon=False)
    fig.savefig(os.path.join(HERE, "fig3_steptime.pdf"))
    plt.close(fig)


# ------------------------------------------------ 图 4：空转率 vs 并发
def fig_idle_conc():
    """C3 的对照：空转率随并发单调下降——并发越低浪费越多。"""
    rows = [r for r in load("decomp.csv") if r["idle_pct"]]
    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    ax.scatter([float(r["running"]) for r in rows],
               [float(r["idle_pct"]) for r in rows],
               c=C_STATIC, s=26, edgecolors="white", linewidths=0.4)
    for r in rows:
        ax.annotate(r["run"].replace("pois200_", "").replace("foyer_", "F:"),
                    (float(r["running"]), float(r["idle_pct"])),
                    (3, 3), textcoords="offset points", fontsize=6)
    ax.set_xlabel("mean running requests")
    ax.set_ylabel("idle fraction of wall clock (\\%)")
    fig.savefig(os.path.join(HERE, "fig4_idle_conc.pdf"))
    plt.close(fig)


# ------------------------------------------------------ 图 5：负载两端反转
def fig_loadtier():
    """C6：同一个节流开关，低载是纯负担、高载是承重的。

    ⚠ 25 档那两根柱子来自旧 harness，与 200 档不同代——图里必须标出来，
    否则是跨代比较。新 harness 的同代对照（foyer_push_25）被占卡打断，未跑完。
    """
    rows = load("loadtier.csv")
    fig, axes = plt.subplots(1, 2, figsize=(3.5, 2.3))
    for ax, tier in zip(axes, ["25", "200"]):
        sub = [r for r in rows if r["tier"] == tier]
        on = [r for r in sub if r["throttle"] == "on"][0]
        off = [r for r in sub if r["throttle"] == "off"][0]
        ax.bar([0, 1], [float(on["wall_min"]), float(off["wall_min"])],
               color=["#7FA8D0", "#E8A33D"], width=0.6)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["throttle\nON", "OFF"])
        ax.set_title("%s sessions" % tier)
        ax.set_ylabel("wall clock (min)" if tier == "25" else "")
        d = (float(off["wall_min"]) - float(on["wall_min"])) / float(on["wall_min"]) * 100
        ax.text(0.5, max(float(on["wall_min"]), float(off["wall_min"])) * 0.92,
                "%+.0f%%" % d, ha="center", fontsize=8, weight="bold",
                color="#8a5a10" if d < 0 else "#1a5a1a")
        if tier == "25":
            ax.text(0.5, -0.42, "old harness", transform=ax.transAxes,
                    ha="center", fontsize=6, color="0.45")
    fig.savefig(os.path.join(HERE, "fig5_loadtier.pdf"))
    plt.close(fig)


# ------------------------------------------------------------ 图 6：horizon
def fig_horizon():
    """C5 之一：增长预留的扫描。不是单调的——h=0 打崩 SLO，h=2 比 h=3 还慢。"""
    rows = sorted(load("horizon.csv"), key=lambda r: int(r["horizon"]))
    h = [int(r["horizon"]) for r in rows]
    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    ax.plot(h, [float(r["wall_min"]) for r in rows], "o-", color=C_FOYER,
            ms=4, lw=1.0, label="wall clock")
    ax.set_xlabel("growth reserve (horizon rounds)")
    ax.set_ylabel("wall clock (min)", color=C_FOYER)
    ax.tick_params(axis="y", labelcolor=C_FOYER)
    ax2 = ax.twinx()
    ax2.plot(h, [float(r["slo_pct"]) for r in rows], "s--", color=C_STATIC,
             ms=4, lw=1.0, label="SLO")
    ax2.set_ylabel("SLO (\\%)", color=C_STATIC)
    ax2.tick_params(axis="y", labelcolor=C_STATIC)
    ax2.grid(False)
    ax.set_xticks(h)
    fig.savefig(os.path.join(HERE, "fig6_horizon.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    for fn in (fig_frontier, fig_decomp, fig_steptime, fig_idle_conc,
               fig_loadtier, fig_horizon):
        fn()
        print("ok", fn.__name__)
