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

C_STATIC, C_STATIC_HC, C_FOYER, C_AIMD = "#4C72B0", "#55A868", "#C44E52", "#8172B3"


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

# ------------------------------------------------- 受同机争用影响的 run
def contested_runs():
    """同机争用审计里判 CONTESTED 的 run（短名），用于在图上打标记。

    为什么图 2/3 也要标：图 2 画的是 busy/idle 时长，而争用抬高 τ 会让 busy
    变长；图 3 画的直接就是步时间。所以这两张图里那几条 run 的柱子/标记
    本身就是被污染的读数，不标出来会让图比实际更干净（图 1 已先改过）。
    """
    import csv as _csv
    p = os.path.join(HERE, "..", "data", "concurrency.csv")
    try:
        return {r["run"].replace("pois200_", "")
                for r in _csv.DictReader(l for l in open(p) if not l.startswith("#"))
                if r["verdict"] == "CONTESTED"}
    except Exception:
        return set()


def fig_frontier():
    """C4：九条 Foyer 变体零条越过静态前沿。

    横轴墙钟、纵轴 SLO。方=静态 cap，三角=静态 cap+HiCache，圆=Foyer。
    折线是静态点的上左包络；**落在折线下方或线上 = 没有越过**——因为按时间片
    混合两个 cap 就能逼近线上任一点。
    """
    # 阈值放到 995：hz0/hz2/rg4 分别少跑 4/2/1 步，是真实的测量点，
    # 悄悄丢掉它们会让图 1 只有 6 条 Foyer 变体，而图注和正文都说 9 条。
    rows = [r for r in load("runs.csv") if r["tier"] == "200" and int(r["steps"]) >= 995]
    # default（不设任何准入控制）单独画，它不是 cap 也不是控制器，是「什么都不做」
    fig, ax = plt.subplots(figsize=(3.5, 2.9))
    front = sorted([(float(r["wall_min"]), float(r["slo_pct"]))
                    for r in rows if r["family"].startswith("static")])
    env, best = [], -1
    for w, s in front:
        if s > best:
            env.append((w, s)); best = s
    ax.plot(*zip(*env), "-", color="0.35", lw=1.0, zorder=1, label="static envelope")
    # 同机争用作废的 run 画成【空心】点：它们的墙钟/SLO 与其余各行不可比
    # （同机 >=4 条车道把逐请求 decode 间隔抬高 25~40%，见 paper/data/concurrency.csv
    # 与 §repro）。不标出来会让图 1 看上去比实际更干净 —— 审稿人 2026-09-24 指出。
    try:
        import csv, os as _os
        _cp = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "data", "concurrency.csv")
        bad = {r[list(r)[0]].replace("pois200_", "")
               for r in csv.DictReader(l for l in open(_cp) if not l.startswith("#"))
               if r["verdict"] == "CONTESTED"}
    except Exception:
        bad = set()
    for fam, c, mk, lab in [("static", C_STATIC, "s", "static cap"),
                            ("static_hc", C_STATIC_HC, "^", "static cap + HiCache"),
                            ("foyer", C_FOYER, "o", "Foyer"),
                            ("aimd", C_AIMD, "D", "Concur-style AIMD")]:
        sel = [r for r in rows if r["family"] == fam]
        xs = [float(r["wall_min"]) for r in sel]
        ys = [float(r["slo_pct"]) for r in sel]
        ax.scatter(xs, ys, c=c, marker=mk, s=24, zorder=3, label=lab,
                   edgecolors="white", linewidths=0.45)
        # 受污染的点再叠一层空心圈，颜色同族，只把填充挖掉
        bx = [float(r["wall_min"]) for r in sel if r["run"].replace("pois200_", "") in bad]
        by = [float(r["slo_pct"]) for r in sel if r["run"].replace("pois200_", "") in bad]
        if bx:
            ax.scatter(bx, by, facecolors="none", edgecolors=c, marker=mk, s=46,
                       zorder=4, linewidths=0.9)
    # 标注一律甩到点的外侧，引线短而直，不横穿别的点
    for txt, xy, xytext, ha in [
            ("cap4+HC",          (213.0, 63.4), (207, 49), "left"),
            ("cap3+HC",          (236.4, 81.1), (238, 71), "right"),
            # best Foyer 放到点的【正上方】：原来放在左下，与 cap3+HC 的引线交叉
            ("best Foyer\n(tie, below it)", (255.8, 84.8), (262, 95), "center")]:
        # cap4+HC 甩到右边：往左会让文字压住 y 轴的 "50" 刻度
        ax.annotate(txt, xy, xytext=xytext, ha=ha, va="center",
                    fontsize=6, color="0.15", linespacing=1.25,
                    arrowprops=dict(arrowstyle="-", lw=0.6, color="0.45",
                                    shrinkA=1.5, shrinkB=2.5))
    ax.set_xlabel("end-to-end wall clock (min)", labelpad=1)
    ax.set_ylabel("SLO attainment (\\%)")
    # 纵轴放到 0：不设任何准入控制的那条 run 落在 SLO 3%，把它切掉就等于
    # 藏起「不做控制的代价」——那正是本文问题的一半。
    ax.set_ylim(-2, 102); ax.set_xlim(188, 548)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    for r in rows:
        if r["run"] == "default":
            ax.annotate("no control", (288.6, 3.0), xytext=(0, 10),
                        textcoords="offset points", ha="center", fontsize=6,
                        color="0.15")
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
    _bad = contested_runs()
    ax.set_yticklabels([short(r["run"]) + ("$^\\ddagger$" if r["run"] in _bad else "")
                        for r in rows], fontsize=6.5)
    for i, r in enumerate(rows):
        if r["run"] in _bad:      # 受争用影响的柱子打斜线，与干净的一眼看得出
            ax.barh(i, float(r["busy_min"]) + float(r["idle_min"]), height=0.66,
                    color="none", edgecolor="0.25", hatch="////", lw=0.0, zorder=4)
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
    _bad = contested_runs()
    ax.set_yticks(y)
    ax.set_yticklabels([short(r["run"]) + ("$^\\ddagger$" if r["run"] in _bad else "")
                        for r in rows], fontsize=6.5)
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
    ax.annotate("median %.1f s" % med, (med, 50), xytext=(5, 5),
                textcoords="offset points", fontsize=6, color="0.15")
    ax.set_xscale("log")
    ax.set_xlim(4, 700); ax.set_ylim(0, 100)
    ax.text(4.6, 4, "5 s sampling floor", fontsize=6,
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




# ------------------------------------------------ 图 7：步时间对并发的弹性
def fig_cancel():
    """论文建设性贡献的一图版：ε = dlnτ/dlnR̄。

    ⚠ 横轴必须用 busy 条件均值（decomp.csv 的 running），不能用全时段均值。
    全时段均值含空转采样，等于 R̄_busy × busy 占比，会让 τ 系统性偏低一个
    busy 占比 —— 那正是 2026-09-23 之前论文里的错误，它把 ε 从 0.38 抬到
    0.57，看上去抵消得更厉害。

    两条测量都画：τ₁ 是模型自洽的（含 prefill 步），τ₂ 是逐请求 decode 间隔
    （不含 prefill）。两者之差是我们能构造的量，但它是一个【时间】比值，
    不是 prefill 的【步数】占比（chunked prefill 下两者不同）。

    **2026-09-24 更新**：原来只画无 HiCache 的五条静态 cap。但九条控制器臂全部
    开 HiCache，而 §IV 现在说「device-only 的悬崖在控制器自己的配置上不存在」——
    只画一条曲线会与正文矛盾。所以同时画 HiCache 的三条（pairB_cap2hc / cap3_hc /
    cap4_hc），让读者直接看到后者在控制器运行区间内没有悬崖。
    """
    import math
    rows = [r for r in load("decomp.csv") if r["step_back_ms"]]
    ids = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]
    rows = sorted([r for r in rows if r["run"] in ids],
                  key=lambda r: float(r["running"]))
    rb = [float(r["running"]) for r in rows]
    t1 = [float(r["step_back_ms"]) for r in rows]
    t2 = [float(r["step_perreq_ms"]) for r in rows]

    def fit(xs, ys):
        X = [math.log(a) for a in xs]; Y = [math.log(b) for b in ys]
        mx, my = sum(X) / len(X), sum(Y) / len(Y)
        sl = sum((a - mx) * (b - my) for a, b in zip(X, Y)) / sum((a - mx) ** 2 for a in X)
        r2 = 1 - sum((b - (my + sl * (a - mx))) ** 2 for a, b in zip(X, Y)) / \
            sum((b - my) ** 2 for b in Y)
        return sl, r2
    e2, r2v = fit(rb, t2)
    e1, _ = fit(rb, t1)

    # HiCache 三条：控制器臂实际运行的配置（§IV 的要点是它没有悬崖）
    hids = ["pairB_cap2hc", "cap3_hc", "cap4_hc"]
    hrows = sorted([r for r in load("decomp.csv") if r["run"] in hids],
                   key=lambda r: float(r["running"]))
    hrb = [float(r["running"]) for r in hrows]
    ht1 = [float(r["step_back_ms"]) for r in hrows]

    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    xs = [1.00 + i * 0.008 for i in range(110)]
    ax.plot(xs, [t2[0] * (x / rb[0]) ** e2 for x in xs], "--", color="0.5", lw=0.9,
            label="fit to $\\tau_2$: $\\varepsilon$=%.2f ($R^2$=%.2f)" % (e2, r2v))
    ax.plot(rb, t1, "o-", color=C_FOYER, ms=4, lw=1.0,
            label="model-consistent $\\tau_1$")
    ax.plot(rb, t2, "s-", color=C_STATIC, ms=4, lw=1.0,
            label="per-request $\\tau_2$")
    ax.plot(hrb, ht1, "^--", color=C_STATIC_HC, ms=4, lw=1.0,
            label="with HiCache (the controllers' config)")
    for r, x, y in zip(rows, rb, t1):
        ax.annotate(r["run"].replace("_fixed", ""), (x, y), xytext=(3, 4),
                    textcoords="offset points", fontsize=6, color="0.2")
    # 标注错开：第一条放右下、第二条放左下、第三条放右上，避开 cap 的标注
    hoff = [(4, -9), (-16, -9), (5, 4)]
    for (r, x, y), off in zip(zip(hrows, hrb, ht1), hoff):
        ax.annotate("+HC", (x, y), xytext=off, textcoords="offset points",
                    fontsize=6, color=C_STATIC_HC)
    ax.set_xlabel("mean running requests during busy time", labelpad=1)
    ax.set_ylabel("step time (ms)")
    ax.set_xlim(0.92, 1.98); ax.set_ylim(18, 40)
    legend_below(ax, ncol=1, y=-0.18)
    fig.savefig(os.path.join(HERE, "fig7_elasticity.pdf"))
    plt.close(fig)



if __name__ == "__main__":
    for fn in (fig_frontier, fig_decomp, fig_steptime, fig_idle_segments,
               fig_loadtier, fig_horizon, fig_cancel):
        fn()
        print("ok", fn.__name__)
