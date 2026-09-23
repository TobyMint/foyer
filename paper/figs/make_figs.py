#!/usr/bin/env python3
"""生成论文用的图（PDF，IEEE 尺寸）。

数据全部来自 ../data/*.csv，那些文件由 scripts/lab/gen_decomp.py 与
run_summary.py 从实验机的原始日志导出。

用法:  python3 make_figs.py

排版纪律（2026-09-23 逐张看图之后定下的）：
  1. 线宽统一：边框/刻度 0.6，网格 0.4，数据线 1.0。混用会让实线看起来
     比同宽的虚线粗一倍。
  2. 图例一律放到坐标轴【外面】（下方两列），不放进绘图区——绘图区里没有
     一块空白大到能放图例而不压住任何数据点。
  3. 标注用 ha 对齐到点的外侧，不许横着穿过别的点。
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
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.minor.width": 0.5, "ytick.minor.width": 0.5,
    "xtick.major.size": 2.6, "ytick.major.size": 2.6,
    "lines.linewidth": 1.0,
    "figure.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})

C_STATIC, C_STATIC_HC, C_FOYER = "#4C72B0", "#55A868", "#C44E52"


def load(name):
    with open(os.path.join(DATA, name)) as f:
        rows = [l for l in f if not l.startswith("#")]
    return list(csv.DictReader(rows))


def short(run):
    """pois200_foyer_hz1 -> F:hz1。图上位置紧张，统一缩写。"""
    s = run.replace("pois200_", "").replace("pairB_", "").replace("pairA_", "")
    return s.replace("foyer_", "F:").replace("_fixed", "")


def legend_below(ax, ncol=2, y=-0.26):
    """图例放坐标轴下方。绘图区里没有足够大的空白，放进去必然压数据点。"""
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, y), ncol=ncol,
              frameon=False, handletextpad=0.4, columnspacing=1.4,
              borderaxespad=0.0)


# ---------------------------------------------------------------- 图 1：前沿
def fig_frontier():
    """C4：九条 Foyer 变体零条越过静态前沿。

    横轴墙钟、纵轴 SLO。方=静态 cap，三角=静态 cap+HiCache，圆=Foyer。
    折线是静态点的上左包络；**落在折线下方或线上 = 没有越过**——因为按时间片
    混合两个 cap 就能逼近线上任一点。
    """
    rows = [r for r in load("runs.csv") if r["tier"] == "200" and int(r["steps"]) >= 999]
    fig, ax = plt.subplots(figsize=(3.5, 2.9))
    front = sorted([(float(r["wall_min"]), float(r["slo_pct"]))
                    for r in rows if r["family"].startswith("static")])
    env, best = [], -1
    for w, s in front:
        if s > best:
            env.append((w, s)); best = s
    ax.plot(*zip(*env), "-", color="0.35", lw=1.0, zorder=1, label="static envelope")
    for fam, c, mk, lab in [("static", C_STATIC, "s", "static cap"),
                            ("static_hc", C_STATIC_HC, "^", "static cap + HiCache"),
                            ("foyer", C_FOYER, "o", "Foyer")]:
        xs = [float(r["wall_min"]) for r in rows if r["family"] == fam]
        ys = [float(r["slo_pct"]) for r in rows if r["family"] == fam]
        ax.scatter(xs, ys, c=c, marker=mk, s=24, zorder=3, label=lab,
                   edgecolors="white", linewidths=0.45)
    # 标注一律甩到点的外侧，引线短而直，不横穿别的点
    for txt, xy, xytext, ha in [
            ("cap4+HC",          (213.0, 63.4), (207, 49), "left"),
            ("cap3+HC",          (236.4, 81.1), (232, 88), "right"),
            ("best Foyer\n(on the line)", (255.8, 84.8), (248, 70), "right")]:
        # cap4+HC 甩到右边：往左会让文字压住 y 轴的 "50" 刻度
        ax.annotate(txt, xy, xytext=xytext, ha=ha, va="center",
                    fontsize=6, color="0.15", linespacing=1.25,
                    arrowprops=dict(arrowstyle="-", lw=0.6, color="0.45",
                                    shrinkA=1.5, shrinkB=2.5))
    ax.set_xlabel("end-to-end wall clock (min)", labelpad=1)
    ax.set_ylabel("SLO attainment (\\%)")
    ax.set_ylim(20, 100); ax.set_xlim(188, 548)
    ax.set_yticks([20, 30, 40, 50, 60, 70, 80, 90, 100])
    legend_below(ax, ncol=2, y=-0.24)
    fig.savefig(os.path.join(HERE, "fig1_frontier.pdf"))
    plt.close(fig)


# ------------------------------------------------------- 图 2：墙钟两段分解
def fig_decomp():
    """C1/C3：墙钟 = 有效工作 + 空转；空转 7.4%–36.3%。

    柱长是【采样跨度】span（busy+idle 精确等于它），不是 run_summary 的墙钟；
    两者差约 6 分钟，是采样器比第一个请求早启动造成的，已在图注里说明。
    """
    rows = sorted(load("decomp.csv"), key=lambda r: float(r["wall_min"]))
    rows = [r for r in rows if r["idle_pct"]]
    y = range(len(rows))
    busy = [float(r["busy_min"]) for r in rows]
    idle = [float(r["idle_min"]) for r in rows]
    fig, ax = plt.subplots(figsize=(3.5, 3.1))
    ax.barh(y, busy, color="#7FA8D0", label="busy (engine running)", height=0.66)
    ax.barh(y, idle, left=busy, color="#E8A33D",
            label="idle (no request in flight)", height=0.66)
    ax.set_yticks(list(y))
    ax.set_yticklabels([short(r["run"]) for r in rows], fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlabel("sampled span (min)", labelpad=1)
    ax.set_xlim(0, 620)
    for i, r in enumerate(rows):
        # 标签放在整根柱子的右端外侧——原来用 wall_min 定位，而柱长是
        # busy+idle，两者不等时标签就会飘到离柱子很远的地方
        ax.text(float(r["busy_min"]) + float(r["idle_min"]) + 8, i,
                "%.0f%%" % float(r["idle_pct"]), va="center", fontsize=6.5,
                color="#8a5a10")
    legend_below(ax, ncol=1, y=-0.16)
    fig.savefig(os.path.join(HERE, "fig2_decomp.pdf"))
    plt.close(fig)


# --------------------------------------------------- 图 3：步时间的两个测量
def fig_steptime():
    """C2：步时间由两个【独立】方法测到，且两者给出一致的排序。

    `metrics.csv` 的 itl/e2e/ttft 列全是空的，所以这不是引擎直采：
    方法一是从 busy 时间反推的导出量，方法二是逐请求的 decode 间隔。

    画成哑铃图而不是散点图，有两个理由：
      1. 13 条 run 各有两个测量，散点图的文字标注必然互相压住；
      2. 这张图要证的是【排序一致】。按方法一排序、把方法二画在旁边，
         如果两组标记的纵向次序基本相同，一致性就是看出来的。实测 Spearman
         rho=0.967，剩下的分歧都是步时间相差 2ms 以内的相邻互换。
    ⚠ 步时间【不】随并发单调（cap4_hc 并发 1.60 → 25.7ms，F:hz0 并发 1.41 →
      33.1ms），所以横轴不再是并发。图只报测量，不给因果。
    """
    rows = [r for r in load("decomp.csv") if r["step_back_ms"]]
    rows.sort(key=lambda r: float(r["step_back_ms"]))
    y = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(3.5, 2.9))
    for i, r in enumerate(rows):
        a, b = float(r["step_back_ms"]), float(r["step_perreq_ms"])
        ax.plot([b, a], [i, i], "-", color="0.78", lw=0.9, zorder=1)
    ax.scatter([float(r["step_back_ms"]) for r in rows], y, marker="o", s=24,
               facecolors="none", edgecolors=C_FOYER, linewidths=1.0, zorder=3,
               label="back-derived (busy $\\times$ conc / tokens)")
    ax.scatter([float(r["step_perreq_ms"]) for r in rows], y, marker="x", s=22,
               color=C_STATIC, linewidths=1.0, zorder=3,
               label="per-request (independent)")
    ax.set_yticks(y)
    ax.set_yticklabels([short(r["run"]) for r in rows], fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlabel("step time (ms)", labelpad=1)
    ax.set_xlim(13, 39)
    ax.axvline(16.2, ls=(0, (1, 1.6)), lw=0.8, color="0.45")
    # 放左下角：最上面几行的 × 标记会一直伸到 x≈24，文字摆在顶部会撞上
    ax.text(16.8, len(rows) - 0.55, "weights-read floor\n(15.2 GB / 936 GB/s)",
            fontsize=6, color="0.35", va="bottom", linespacing=1.25)
    legend_below(ax, ncol=1, y=-0.16)
    fig.savefig(os.path.join(HERE, "fig3_steptime.pdf"))
    plt.close(fig)


# ------------------------------------------------ 图 4：空转率 vs 墙钟
def fig_idle_segments():
    """C3 的直接证据：空转段【很长】，和 tool wait 同量级。

    画的是生存函数 P(空闲段 > x)。论文的主张是这些段不是采样噪声、也不是
    控制周期抖动造成的瞬时状态，而是会话在 tool wait 期间真的不发请求——
    所以段长必须和 tool wait 可比。中位 10–20s，p90 约 25s，最长 366–511s，
    对照实测的平均 tool wait 16.85s。

    这张图取代了原来那张「空转率 vs 并发」：那张要证的单调性在补齐数据后
    【不成立】（F:hz0 并发 1.41 时空转 15.2%，cap4 并发 1.48 时只有 10.4%），
    而且它画的东西在总分解图里已经有了。
    """
    rows = load("idle_seg_raw.csv")
    d = sorted(float(r["duration_s"]) for r in rows)
    n = len(d)
    ys = [100.0 * (n - i) / n for i in range(n)]
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    ax.step(d, ys, where="post", color=C_STATIC, lw=1.0)
    # 两条参考线的文字都放到曲线【上方】。原来都放在 y=6，而 16.85s 的说明
    # 横向一直伸到 x≈60，正好撞上「1 min」。
    for x, lab, ty in [(16.85, "mean tool wait\n16.85 s", 97),
                       (60.0, "1 min", 76)]:
        ax.axvline(x, ls=(0, (1, 1.6)), lw=0.8, color="0.45")
        ax.text(x * 1.07, ty, lab, fontsize=6, color="0.35", va="top",
                linespacing=1.25)
    med = d[n // 2]
    ax.plot([med], [50], "o", ms=3.5, color=C_FOYER, zorder=4)
    ax.annotate("median %.0f s" % med, (med, 50), xytext=(5, 5),
                textcoords="offset points", fontsize=6, color="0.15")
    ax.set_xscale("log")
    ax.set_xlim(4, 700); ax.set_ylim(0, 100)
    ax.text(4.6, 4, "5 s sampling makes\n10 s the floor", fontsize=6,
            color="0.45", linespacing=1.25)
    ax.set_xlabel("duration of an idle stretch (s, log scale)", labelpad=1)
    ax.set_ylabel("\\% of stretches longer than $x$")
    fig.savefig(os.path.join(HERE, "fig4_idle_segments.pdf"))
    plt.close(fig)


# ------------------------------------------------------ 图 5：负载两端反转
def fig_loadtier():
    """C6：同一个节流开关，低载是纯负担、高载是承重的。

    ⚠ 25 档那两根柱子来自旧 harness，与 200 档不同代——图里必须标出来，
    否则是跨代比较。新 harness 的同代对照（foyer_push_25）被占卡打断，未跑完。
    """
    rows = load("loadtier.csv")
    fig, axes = plt.subplots(1, 2, figsize=(3.5, 2.4))
    for ax, tier in zip(axes, ["25", "200"]):
        sub = [r for r in rows if r["tier"] == tier]
        on = float([r for r in sub if r["throttle"] == "on"][0]["wall_min"])
        off = float([r for r in sub if r["throttle"] == "off"][0]["wall_min"])
        ax.bar([0, 1], [on, off], color=["#7FA8D0", "#E8A33D"], width=0.62)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["throttle\nON", "OFF"])
        ax.set_title("%s sessions" % tier, pad=3)
        if tier == "25":
            ax.set_ylabel("wall clock (min)")
        top = max(on, off)
        # 百分比标签放在两根柱子【上方】的空白处，不压在柱子上
        ax.set_ylim(0, top * 1.30)
        ax.text(0.5, top * 1.06, "%+.0f%%" % ((off - on) / on * 100),
                ha="center", va="bottom", fontsize=8, weight="bold",
                color="#8a5a10" if off < on else "#1a5a1a")
        ax.set_xlim(-0.55, 1.55)
        if tier == "25":
            ax.set_xlabel("harness: earlier revision", fontsize=6, color="0.45",
                          labelpad=2)
    fig.savefig(os.path.join(HERE, "fig5_loadtier.pdf"))
    plt.close(fig)


# ------------------------------------------------------------ 图 6：horizon
def fig_horizon():
    """C5 之一：增长预留的扫描。不是单调的——h=0 打崩 SLO，h=2 比 h=3 还慢。"""
    rows = sorted(load("horizon.csv"), key=lambda r: int(r["horizon"]))
    h = [int(r["horizon"]) for r in rows]
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    l1, = ax.plot(h, [float(r["wall_min"]) for r in rows], "o-", color=C_FOYER,
                  ms=4, lw=1.0, label="wall clock (left)")
    ax.set_xlabel("growth reserve (horizon rounds)", labelpad=1)
    ax.set_ylabel("wall clock (min)", color=C_FOYER)
    ax.tick_params(axis="y", labelcolor=C_FOYER)
    ax.set_xticks(h); ax.set_xlim(-0.3, 3.3)
    ax2 = ax.twinx()
    l2, = ax2.plot(h, [float(r["slo_pct"]) for r in rows], "s--", color=C_STATIC,
                   ms=4, lw=1.0, label="SLO (right)")
    ax2.set_ylabel("SLO (\\%)", color=C_STATIC)
    ax2.tick_params(axis="y", labelcolor=C_STATIC)
    ax2.grid(False)
    ax2.set_ylim(70, 95)
    # 两条线颜色跟各自的轴走，光靠颜色区分不够——加图例，并统一线宽
    ax.legend(handles=[l1, l2], loc="upper center", bbox_to_anchor=(0.5, -0.24),
              ncol=2, frameon=False, handletextpad=0.4, columnspacing=1.4,
              borderaxespad=0.0)
    fig.savefig(os.path.join(HERE, "fig6_horizon.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    for fn in (fig_frontier, fig_decomp, fig_steptime, fig_idle_segments,
               fig_loadtier, fig_horizon):
        fn()
        print("ok", fn.__name__)
