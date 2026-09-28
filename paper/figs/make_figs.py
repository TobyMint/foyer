#!/usr/bin/env python3
"""生成论文用的图（PDF，IEEE 尺寸）。

数据全部来自 ../data/*.csv，那些文件由 scripts/lab/gen_decomp.py 与
run_summary.py 从实验机的原始日志导出。

用法:  python3 make_figs.py

排版纪律（2026-09-27 按 RTAS 2026 录用稿重做之后定下的）：
  1. **图例一律在坐标轴【上方】**，横向排、不占版面。参考稿 24 篇里没有一张
     把图例甩到坐标区下方 —— 下方那条图例按高度算会吃掉整图 1/4
     （本稿 2026-09-27 之前就是这样，作者的原话是「看得我两眼一黑」）。
  2. **不要满铺网格**，留一条**极淡的单向**网格（只横或只纵），见 `GRID` / `grid_x` /
     `grid_y`。参考稿那批里两种都有：PerBank（Best Student Paper）的 Fig. 3 是**单向横向**、
     ETM² 的 Fig. 6--8 是满铺 —— 所以「单向浅灰」不是自创风格。
     ⚠ 2026-09-27（codex r54 复核）：这一行原来写「+ alpha 0.5 的浅灰」，
     **与代码不符**（`GRID` 里没有 alpha，浅是靠 `color="0.90"` 本身）。
     说法已按代码写实；**网格本身保留** —— 三张图里那条横向网格承载读数
     （图 1 的 20pp 档、图 2/图 7 对坐标），删掉是纯风格改动、换不来证据强度。
  3. 线宽统一：边框 0.6、刻度 0.6、数据线 0.9、拟合线 0.8 虚线。混用会让实线
     看起来比同宽的虚线粗一倍。
  4. 记号要小（散点 s≈15、线图 ms≈3.2），且**形状本身带信息**（方/三角/圆/菱/叉）
     —— 灰度打印或色觉异常时仍分得开。配色经 dataviz 校验器 all-pairs 通过
     （见 PALETTE 那一段的注释）。
  5. 标注一律甩到点的外侧，引线短而直，不横穿别的点，也不许画到坐标轴外面。
     这三条由 `assert_inside()` 机械检查（文字包围盒 + 压点 + 文字互相重叠）。
  6. 图在 `\\includegraphics[width=\\columnwidth]` 下按 3.5in 渲染，所以**出图
     宽度要接近 3.5in** —— 出小了 LaTeX 会放大（字号跟着变大，图反而更挤），
     出大了会缩小（字号变小）。每张图的 `_check_width()` 会打印实测宽度。
"""
import csv, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


# ------------------------------------------------------------------ 字型
# 参考稿（RTAS 2026 的 24 篇，含 Best Paper ZeroSwap / Best Student Paper
# PerBank）的结果图**全部**用 Helvetica 类无衬线体，与图注同族。
# matplotlib 默认的 DejaVu Sans 明显更宽更重：同一句话在 3.5in 单栏里要宽出
# 一成半，标注因此更容易撞在一起。URW 的 Nimbus Sans 是 Helvetica 的度量兼容
# 克隆，随 texlive 的 urw-base35 发行，与 LaTeX 的 \sf 同源。
#
# ⚠ 那四个 .otf 的 OS/2 表里**没有**记录 weight/slant（实测四个文件
# `FontProperties(fname=...)` 都报 "weight normal / style normal"），所以
# matplotlib **分不出** NimbusSans-Bold / -Italic —— 注册了也选不中。
# 因此本文件只注册 Regular，并且**不使用粗体与斜体字重**；数学模式走
# `mathtext.default="regular"`（直立体），与参考稿的记号风格一致。
_SANS = "DejaVu Sans"          # 兜底：注册失败时用它，图照样能出
def _register_sans():
    global _SANS
    # ⚠ 只收 .otf/.ttf —— matplotlib 的 FreeType 打不开 URW 的 .t1（Type1），
    # `addfont` 会抛 `FT_Open_Face ... unknown file format`。**每个文件单独
    # try**：一次失败不许把已经注册成功的那几个一起丢掉（第一版就是这么退回去的）。
    cands = ["/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf",
             "/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.ttf"]
    try:
        from matplotlib import font_manager as _fm
        for p in cands:
            if not os.path.exists(p):
                continue
            try:
                _fm.fontManager.addfont(p)
            except Exception as _e:
                print("note: addfont(%s) 失败（%r）" % (p, _e), file=sys.stderr)
        if any(f.name == "Nimbus Sans" for f in _fm.fontManager.ttflist):
            _SANS = "Nimbus Sans"
        else:
            print("note: Nimbus Sans 不在字体表里，退回 %s" % _SANS, file=sys.stderr)
    except Exception as _e:            # 不静默，但也不让画图失败
        print("note: Nimbus Sans 没注册上（%r），退回 %s" % (_e, _SANS),
              file=sys.stderr)
_register_sans()

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": [_SANS],
    "font.size": 7, "axes.labelsize": 7.2, "axes.titlesize": 7.2,
    "legend.fontsize": 6.2, "xtick.labelsize": 6.3, "ytick.labelsize": 6.3,
    # ⚠ `axes.grid` 默认 **False**：满铺网格是「草稿感」最大的来源。
    # 需要基准线的图自己开**单向**网格（见 `grid_x` / `grid_y`）。
    "axes.grid": False,
    "axes.linewidth": 0.6, "axes.edgecolor": "0.25", "axes.labelcolor": "0.15",
    "xtick.color": "0.25", "ytick.color": "0.25",
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.minor.width": 0.5, "ytick.minor.width": 0.5,
    "xtick.major.size": 2.2, "ytick.major.size": 2.2,
    "xtick.minor.size": 1.2, "ytick.minor.size": 1.2,
    "xtick.direction": "out", "ytick.direction": "out",
    "lines.linewidth": 0.9, "lines.markersize": 3.2,
    "lines.dash_capstyle": "butt",
    "legend.frameon": False, "legend.handlelength": 1.35,
    "legend.handletextpad": 0.38, "legend.columnspacing": 1.1,
    "legend.labelspacing": 0.30, "legend.borderaxespad": 0.0,
    "legend.borderpad": 0.0,
    "hatch.linewidth": 0.4,
    "text.color": "0.15",
    "mathtext.fontset": "custom", "mathtext.default": "regular",
    "mathtext.rm": _SANS, "mathtext.it": _SANS, "mathtext.bf": _SANS,
    "mathtext.fallback": "stixsans",
    "figure.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.012,
})

# **单向**网格（只横或只纵），`color="0.90"` 的浅灰 + `lw=0.4`（比数据线的 0.9 细一半），
# `zorder=0` + `set_axisbelow(True)` 压在数据下方。**没有 alpha** —— 浅是靠颜色本身，
# 不是叠加出来的（2026-09-27 codex r54 指出头部的注释写着「alpha 0.5」而这里是写实值，
# 已改注释，不改行为）。
GRID = dict(color="0.90", lw=0.4, zorder=0.0)
def grid_x(ax):
    ax.grid(True, axis="x", **GRID); ax.set_axisbelow(True)
def grid_y(ax):
    ax.grid(True, axis="y", **GRID); ax.set_axisbelow(True)

# 配色：经 dataviz 校验器（scripts/validate_palette.js --pairs all，light 面）
# 全部 PASS —— 最差一对 CVD ΔE 8.6（红↔绿，deutan）、最差一对常视 ΔE 16.8、
# 四色对底面对比度全 ≥3:1。散点图要按 all-pairs 过，所以这四个是挑过的。
# **形状同时带信息**（方/三角/圆/菱），红绿那一对靠形状分得开。
C_STATIC, C_STATIC_HC, C_FOYER, C_AIMD = "#2a78d6", "#17936a", "#e34948", "#9c5aa0"
C_INK, C_MUTE = "0.15", "0.42"
# 图 2 的两段：蓝（有活干）+ 琥珀（空转）。空转是本文要说的事，所以给它暖色。
C_BUSY, C_IDLE = "#2a78d6", "#e08a2e"


# 每张图画完把「它读了哪些数据文件」记下来（见 __main__ 的 _CUR）。
# 为什么：`check_paper_numbers.py` 的「图比数据旧」判据原来拿**全部** CSV 的
# 最新 mtime 去比**每一张**图 —— 于是只更新某张图的专属输入（如 `reuse_x.csv`）
# 也会把其余七张判成旧，是**假 MISS**（codex 第 25 轮指出）。有了这份清单，
# 每张图只跟自己的输入比。
DEPS = {}
_CUR = [None]
# 每张图【画了几条、标了几条】—— 图注里的条数是派生量，必须由画图的人报出来，
# 不能让 check_paper_numbers.py 另写一遍同样的筛选逻辑（那就是第二份实现）。
COUNTS = {}
# 图上的**文字标签**（图 2 的纵轴）—— 同样由画图的人报出来，
# 检查器读它、**不 import 本脚本**：`import make_figs` 会拉起 matplotlib，
# 而 AE 文档写着「复现路径只用标准库」（codex 在只读环境实测到这条依赖）。
LABELS = {}
# 出图宽度记账：`\includegraphics[width=\columnwidth]` 的目标是 3.5in。
# 出小了 LaTeX 放大（字号跟着变大），出大了缩小（字号变小），两者都会让
# 「按 7pt 排的版」在纸面上不是 7pt。超界就报出来。
WIDTH_LO, WIDTH_HI = 3.36, 3.62

# ⚠⚠ 2026-09-27（r56 处置中发现）：**matplotlib 会在 PDF 里写 `/CreationDate`**，
# 于是**同一份代码跑两次，图的字节不同**（渲染像素完全一致 —— 中立复核说的
# 「md5 相同」指的是渲染结果，我当时读成了字节）。
# 后果：任何「重生成后逐字节对拍」的流程（AE 的 `regen_all.sh`、未来的自己）
# 都会**假失败**。钉掉它：`CreationDate: None` ⇒ matplotlib 不写该字段，字节可复现。
# （实测：不设时两次跑字节不同；设了之后两次跑字节相同。）
_META = {"CreationDate": None}


def load(name):
    if _CUR[0]:
        DEPS.setdefault(_CUR[0], set()).add(name)
    with open(os.path.join(DATA, name)) as f:
        rows = [l for l in f if not l.startswith("#")]
    return list(csv.DictReader(rows))


def short(run):
    """pois200_foyer_hz1 -> F:hz1。图上位置紧张，统一缩写。

    ⚠ 缩写必须【唯一】。原来把 pairA_/pairB_ 前缀整个删掉，于是
    `pairA_cap2hc` / `pairB_cap2hc` 都变成 "cap2hc"，`foyer_hc` /
    `pairA_foyerhc` / `pairB_foyerhc` 三条都变成 "foyerhc" —— 图 2 有 28 根柱子
    却有 3 组重名，读者分不出哪根是哪条（2026-09-25 把图渲出来看才发现的，
    此前只核对过数据没看过图）。现在保留配对的前缀。

    ⚠ `check_paper_numbers.py` 会 import 本文件并调用 `short()` 做图 2 标签
    唯一性守卫 —— **改签名或改名会让那条守卫静默失效**（它会报「导入失败」）。
    """
    s = run.replace("pois200_", "")
    s = s.replace("pairA_", "A:").replace("pairB_", "B:")
    return s.replace("foyer_", "F:").replace("_fixed", "")


def legend_above(ax, ncol=2, pad=0.035, center=False, **kw):
    """图例放坐标轴【上方】，横向排。

    为什么不在下方（2026-09-27 改）：参考稿（RTAS 2026）没有一张把图例甩到
    坐标区下方 —— 那会吃掉整图约 1/4 的高度，而图在 `width=\\columnwidth`
    下高度是死的，代价全从绘图区里扣。上方一行/两行只花掉 6--8%。

    ⚠ matplotlib 的 `ncol` 是**按列**填充的（它把 handles 顺序切成 ncol 段，
    每段自上而下填一列）。传 handles 的顺序要按这个来排，否则读起来会错行。
    """
    x = 0.5 if center else 0.0
    return ax.legend(loc="lower center" if center else "lower left",
                     bbox_to_anchor=(x, 1.0 + pad),
                     ncol=ncol, frameon=False, borderaxespad=0.0,
                     borderpad=0.0, **kw)


def _check_width(pdf):
    """量出出图宽度（inch），超出 [WIDTH_LO, WIDTH_HI] 就报出来。

    为什么要：`savefig.bbox="tight"` 把空白裁掉之后，图的实际宽度由**内容**
    决定（y 轴标签有多长、图例有几列），与 `figsize` 只是间接相关。而
    `\\includegraphics[width=\\columnwidth]` 会把它缩放到 3.5in —— 差 10%
    就意味着纸面上的字号差 10%。此前图 1 是 3.19in（被放大 1.10×，8pt 排的
    字在纸上成了 8.8pt），图 2 是 3.50in。这条只是**报告**，不中断画图。
    """
    try:
        import re as _re
        raw = open(pdf, "rb").read()
        m = _re.search(rb"/MediaBox\s*\[([^\]]*)\]", raw)
        p = [float(v) for v in m.group(1).split()]
        w = (p[2] - p[0]) / 72.0
        tag = "ok " if WIDTH_LO <= w <= WIDTH_HI else "!! "
        print("   %s%s 出图宽 %.2f in（目标 3.5，%s）"
              % (tag, os.path.basename(pdf), w,
                 "会被 LaTeX 缩放 %.2f×" % (3.5 / w)))
    except Exception as _e:
        print("   ?? 量不出 %s 的宽度（%r）" % (pdf, _e), file=sys.stderr)


# ------------------------------------------------- 受同机争用影响的 run
def contested_runs():
    """同机争用审计里判 CONTESTED 的 run（短名），用于在图上打标记。

    为什么三张图都要标：图 1 画的是 SLO 与墙钟，图 2 画的是 busy/idle 时长，
    而争用抬高 τ 会让 busy 变长。不标出来会让图比实际更干净。

    ⚠ 2026-09-26：**这必须是三张图共用的那一份**。图 1 原来自己内联了一份同样的
    读取（连 DEPS 记账都是手写的），两份实现一旦分叉，就会出现「图 1 说两条、
    图 2 说三条」而没有任何东西报错。已统一到这里；图 1 那份内联删除。
    """
    import csv as _csv
    p = os.path.join(HERE, "..", "data", "concurrency.csv")
    if _CUR[0]:
        DEPS.setdefault(_CUR[0], set()).add("concurrency.csv")   # 没走 load()，手动记
    try:
        return {r["run"].replace("pois200_", "")
                for r in _csv.DictReader(l for l in open(p) if not l.startswith("#"))
                if r["verdict"] == "CONTESTED"}
    except Exception as _e:
        # **不静默**（原图 1 内联版就是这么写的，抽出来时保留）：读不到就等于
        # 「没有臂被标脏」，图会看上去比实际干净 —— 那正是这几张图要防的事。
        print("!! contested_runs(): 读不到 concurrency.csv（%s），争用标记将缺失" % _e,
              file=sys.stderr)
        return set()


def assert_inside(ax, tag):
    """**所有画上去的东西都必须在坐标轴范围之内** —— 不满足就报错，不静默裁掉。

    为什么要有（2026-09-26）：图 3 的 `xlim` 是 (13, 39)，而 `default` 的反向
    步成本是 **42.5 ms**、`foyer_hz1_r2` 是 **41.6** —— matplotlib 对超出范围的
    散点**直接不画**，图上看不出少了什么，**而那个 `default` 正是图注在说的
    一条 run**。

    2026-09-27 补的三类（都是「渲到 300dpi 裁到局部才看得见」的接触级缺陷）：
      (a) 文字**包围盒**越出坐标区（锚点在里、字在外面 —— 图 1 的
          `scans the queue` 原来就是这样，压着上边框、左端越过 y 轴）；
      (b) 标注**压住散点**（图 1 的 `cap3+HC`/`cap4+HC` 各压住一颗绿三角）；
      (c) 新增：**两段标注互相重叠**（一排直接标签最容易撞在一起）。
    """
    # ⚠⚠ 2026-09-27（r54 复核 C）：**这个函数里所有的 pt↔px 换算都以
    # `figure.dpi == 200` 为前提**（`text-covers-marker` 的 1.5pt 边距、
    # `leader-passes-marker` 的 2.5pt / 6pt 阈值，都是先乘 `dpi/72` 再用）。
    # dpi 一改，阈值的**含义**就变了（而那些阈值是写死在注释里的 pt），
    # 所以这里把它钉住，而不是让它随 rcParams 漂。
    assert ax.figure.dpi == 200, (
        "figure.dpi 是 %r，不是 200 —— 本函数里所有 pt 阈值都是按 200dpi 换算的，"
        "改了 dpi 就得同时改换算（否则阈值含义静默变化）" % (ax.figure.dpi,))
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    lo_x, hi_x = min(x0, x1), max(x0, x1)
    lo_y, hi_y = min(y0, y1), max(y0, y1)
    bad = []
    for ln in ax.lines:
        for x, y in zip(ln.get_xdata(), ln.get_ydata()):
            if not (lo_x <= x <= hi_x) or not (lo_y <= y <= hi_y):
                bad.append(("line", round(float(x), 2), round(float(y), 2))); break
    for c in ax.collections:
        off = c.get_offsets()
        if off is None or not len(off):
            continue
        for x, y in off:
            if not (lo_x <= x <= hi_x) or not (lo_y <= y <= hi_y):
                bad.append(("scatter", round(float(x), 2), round(float(y), 2))); break
    # 文字标注同样会被裁掉（轴外的 text 不显示）。`ax.texts` 的坐标是**数据坐标**，
    # 带 `textcoords="offset points"` 的那种锚点也在数据坐标里，所以这一条成立。
    boxes = []          # (显示坐标包围盒, 文字) —— 给 (c) 用
    _LMIN = []          # (最小间距pt, 文字) —— 给第五类的「实测最小值」用
    _EMIN = []          # (轴框留白pt, 边, 文字) —— 给第六类
    for t in ax.texts:
        # ⚠ `Annotation.get_position()` 在 `textcoords="offset points"` 下报的是
        # **偏移量**（例如 `(0, 10)`），不是数据坐标 —— 拿它去比必然假报。
        # 有 `xy` 的就是 Annotation，比它的**数据坐标锚点**；其余比 `get_position()`。
        x, y = getattr(t, "xy", None) or t.get_position()
        if not (lo_x <= x <= hi_x) or not (lo_y <= y <= hi_y):
            bad.append(("text", round(float(x), 2), round(float(y), 2)))
            continue
        # ⚠⚠ 只比锚点是不够的：锚点在里、**文字包围盒**在外面照样是画出了绘图区。
        # （渲染包围盒要一个 renderer；`fig.canvas.draw()` 一次即可。）
        try:
            fig = ax.figure
            fig.canvas.draw()
            # ⚠⚠ **必须用 `Text.get_window_extent`（非绑定调用），不能用
            # `t.get_window_extent()`。** `Annotation.get_window_extent` 把**箭头**
            # 也算进包围盒 —— 于是框会从文字一直横跨到箭头尖，沿途的散点全被判成
            # 「被文字压住」（2026-09-27 实测：一条 40 个单位的箭头让 6 个正常
            # 标注全部误报）。`Text.get_window_extent(t, renderer=...)` 只给文字。
            from matplotlib.text import Text as _MText
            bb = _MText.get_window_extent(t, renderer=fig.canvas.get_renderer())
            inv = ax.transData.inverted()
            (bx0, by0), (bx1, by1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
            # 容差 0.5 个数据单位太小、1 个 pt 又随图尺寸变；用轴跨度的 0.3%
            tx = 0.003 * (hi_x - lo_x); ty = 0.003 * (hi_y - lo_y)
            if (min(bx0, bx1) < lo_x - tx or max(bx0, bx1) > hi_x + tx
                    or min(by0, by1) < lo_y - ty or max(by0, by1) > hi_y + ty):
                bad.append(("text-bbox", t.get_text()[:24].replace("\n", " "),
                            round(min(bx0, bx1), 1), round(max(bx0, bx1), 1),
                            round(min(by0, by1), 1), round(max(by0, by1), 1)))
            boxes.append((bb, t.get_text()[:20].replace("\n", " ")))
            # ⚠⚠⚠ **第六类：包围盒没出轴，但离轴框太近**。2026-09-27（codex r54 复核 E）加。
            #
            # 为什么必须单独有一类：上面那条 `text-bbox` 用的是**容差**（轴跨度的 0.3%），
            # 它只问「有没有超出这么多」—— 于是「几乎贴住边框」与「有充裕边距」在它眼里
            # 是同一件事。实测：图 2 的 `36%` 右缘在 xlim 外 **0.21 单位（0.07pt）**，
            # 落在 1.725 单位的容差里 ⇒ **全绿**，而 300dpi 渲出来它是贴着右边框的。
            #
            # 判据：包围盒四边都要离轴框 ≥ `_EDGE_PT`（pt；按 `dpi/72` 换成显示单位，
            # 与 `_COVER` / `_R` 同一套换算）。
            #
            # ⚠⚠ 2026-09-27（r55 中立复核 F4）：下限 2.0 的**理由里那两个「修完」值是错的** ——
            # 原文写「图 1 的 `scans the queue`（修完 **2.2pt**）与图 2 的 `36%`（修完 3.1pt）」。
            # 实量（我独立重量）：图 1 上边 **3.08pt**、图 2 右边 **3.10pt**（这个对）。
            # ⇒ 2.0 这个下限**仍然成立**（3.08 > 2.0），但**理由里手写的数不能信**。
            # 与第五类同一处置：**实测最小值由下面统一打印**，不写进注释。
            _EDGE_PT = 2.0
            _EDGE = _EDGE_PT * fig.dpi / 72.0
            _axb = ax.get_window_extent()
            _g = {"左": bb.x0 - _axb.x0, "右": _axb.x1 - bb.x1,
                  "下": bb.y0 - _axb.y0, "上": _axb.y1 - bb.y1}
            _worst = min(_g, key=lambda _k: _g[_k])
            if _g[_worst] < _EDGE:
                bad.append(("text-too-close-to-frame",
                            t.get_text()[:24].replace("\n", " "),
                            "%s边框留白 %.2fpt（下限 %.1fpt）"
                            % (_worst, _g[_worst] * 72.0 / fig.dpi, _EDGE_PT)))
            _EMIN.append((_g[_worst] * 72.0 / fig.dpi, _worst,
                          t.get_text()[:20].replace("\n", " ")))
            # ⚠⚠ **标注压住了散点**。判据：散点中心落在文字包围盒**内部**
            # （留 1.5pt 边距，免得把「标签就贴在自己那个点旁边」的正常排布误报）。
            # ⚠ 2026-09-27（r54 复核 C）：那个 1.5 是 **pt**，而这里比的是**显示坐标**
            # （`figure.dpi` 的像素）—— 原来直接写 `1.5`，有效边距因此是 0.54pt。
            # 现在按 `dpi/72` 换算，注释写的就是真的。
            _COVER_PT = 1.5
            _COVER = _COVER_PT * fig.dpi / 72.0
            for _c in ax.collections:
                _off = _c.get_offsets()
                if _off is None or not len(_off):
                    continue
                for _x, _y in _off:
                    _px, _py = ax.transData.transform((float(_x), float(_y)))
                    if (bb.x0 + _COVER <= _px <= bb.x1 - _COVER
                            and bb.y0 + _COVER <= _py <= bb.y1 - _COVER):
                        bad.append(("text-covers-marker",
                                    t.get_text()[:24].replace("\n", " "),
                                    round(float(_x), 2), round(float(_y), 2)))
                        break
            # ⚠⚠⚠ **第五类：文字包围盒压住了【数据线】**。2026-09-27（r54 复核 A）加。
            #
            # 为什么必须单独有一类：上面四类**一条都看不见它** ——
            # 「出轴」比的是锚点与文字框，「压点」只看 `ax.collections` 的散点，
            # 「引线擦点」只看 Annotation 的箭头，而**一条 `ax.plot` 的折线**
            # 既不是散点、不是文字、也不是引线。于是图 7 的 `cap2`/`cap3`/`cap4`
            # 三个标签被红色 τ₁ 线穿过时，四条断言**全绿**。
            #
            # 判据：把每条线的每一段**加密采样**（步长 ≤ 1 显示单位 = 0.36pt），
            # 量每个采样点到**文字包围盒矩形**的距离，取全局最小。
            #
            # ⚠⚠ 2026-09-27（r55 复核）：**原判据是「采样点是否落在框内」——
            # 纯相交测试，一个边距都不管。** 后果实测：一条距框 0.5pt 的线
            # **照样通过**，而正文/注释里写的却是「最小间距 ≥1.5pt」——
            # **声称强于机制**，正是本项目反复栽的那一类。
            # 更早的实例：图 1 的 `cap3+HC` 框右下角离 `static envelope` **只有
            # 0.37pt**（线在框外 0.30 数据单位 ⇒ 不相交 ⇒ 旧判据全绿），
            # 而图 7 那三个标签是按 1.5pt 标准摆的 —— **同一张图里两套标准**。
            #
            # 现在改成**真阈值**：最小距离 < `_LINE_PT` 就报，并把实测值印进消息，
            # 让记录里的数字由守卫产生，而不是靠谁手写。
            # 采样步长 0.36pt ⇒ 对「框外 0.36pt 以内」的擦边仍可能少报一点点，
            # 但**方向是安全的**（宁可漏报 0.3pt，不可虚报 1.5pt）。
            #
            # ⚠ 线的**顶点本身就是它的记号**（`ax.plot(...,"o-")` 的圆点不在
            # `ax.collections` 里），所以「标签压住了自己那个圆点」这类缺陷也由
            # 这一条接住 —— 顶点必被采样到（每段都从 `_j=0` 起）。
            _LINE_PT = 1.5
            _LINE_MIN = _LINE_PT * ax.figure.dpi / 72.0
            _nearest, _nearline = None, None
            for _ln in ax.lines:
                _lx, _ly = _ln.get_xdata(), _ln.get_ydata()
                for _k in range(len(_lx) - 1):
                    _sx0, _sy0 = ax.transData.transform((float(_lx[_k]), float(_ly[_k])))
                    _sx1, _sy1 = ax.transData.transform(
                        (float(_lx[_k + 1]), float(_ly[_k + 1])))
                    _step = max(2, int(((_sx1 - _sx0) ** 2 + (_sy1 - _sy0) ** 2) ** 0.5) + 1)
                    for _j in range(_step + 1):
                        _u = _j / float(_step)
                        _sx = _sx0 + _u * (_sx1 - _sx0)
                        _sy = _sy0 + _u * (_sy1 - _sy0)
                        # 点到**矩形**的距离（框内为 0，框外为正）——
                        # 分轴取超出量再取模，比写「线段 vs 矩形」的解析相交稳。
                        _dd = ((max(bb.x0 - _sx, 0.0, _sx - bb.x1)) ** 2
                               + (max(bb.y0 - _sy, 0.0, _sy - bb.y1)) ** 2) ** 0.5
                        if _nearest is None or _dd < _nearest:
                            _nearest, _nearline = _dd, _ln.get_label()
            if _nearest is not None and _nearest < _LINE_MIN:
                bad.append(("text-overlaps-line",
                            t.get_text()[:24].replace("\n", " "),
                            "线 %r 距框仅 %.2fpt（下限 %.1fpt）"
                            % (_nearline, _nearest * 72.0 / ax.figure.dpi, _LINE_PT)))
            _LMIN.append((_nearest * 72.0 / ax.figure.dpi if _nearest is not None else None,
                          t.get_text()[:20].replace("\n", " ")))
        except Exception as _e:      # 拿不到 renderer 时不静默放过，报出来
            bad.append(("text-bbox 取不到（%r）" % _e, t.get_text()[:24], 0, 0, 0, 0))
    # (c) 两段标注互相重叠 —— 一排直接标签（「cap1」「cap2」+「+HC」）最容易撞。
    # 判据取**交集面积 > 1pt²**（纯擦边不算，那种在两行文字间很常见）。
    for _i in range(len(boxes)):
        for _j in range(_i + 1, len(boxes)):
            _a, _b = boxes[_i][0], boxes[_j][0]
            _ov = (min(_a.x1, _b.x1) - max(_a.x0, _b.x0))
            _oh = (min(_a.y1, _b.y1) - max(_a.y0, _b.y0))
            if _ov > 1.0 and _oh > 1.0:
                bad.append(("text-overlaps-text", boxes[_i][1], boxes[_j][1],
                            round(_ov, 1), round(_oh, 1)))
    # (d) **引线横穿别的点**。2026-09-27 加：上面 (b) 只查「文字框里有没有点」，
    # 而图 1 那条 `scans the queue` 的引线**从一颗红点边上 2.3pt 处擦过去** ——
    # 文字框是干净的，缺陷全在引线上。判据是点到**线段**的距离，阈值 2.5pt。
    #
    # ⚠ 两个必须有的豁免，否则这条守卫全是假报：
    #   1. **箭头尖附近 6pt 内的点不算** —— 引线的端点本来就钉在它要指的地方，
    #      而图 1 那个簇里三颗点彼此只差 1--3pt（`cap3_ph` 与 `cap3_hc` 只差
    #      1.6pt、`foyer_hz2_r2` 离 `foyer_scan_r3` 只有 3pt），「指着簇」必然
    #      「擦过簇里的点」。6pt 之外才是真正意义上的「横穿别的点」。
    #   2. `FancyArrowPatch.get_path()` 的**最后一个顶点是 CLOSEPOLY 的 `(0,0)`
    #      哨兵**（实测 7 个顶点，末位就是原点）—— 取 `vertices[-1]` 会把引线
    #      算成「从文字到画布左下角」，于是**每一颗点**都落在它旁边。
    #      正解：尾端取 `[0]`，尖端取**离 `xy` 最近的顶点**，先滤掉 `(0,0)`。
    try:
        from matplotlib.text import Annotation as _Ann
        # ⚠⚠ 2026-09-27（r54 复核 C）：**这两个数原来是 pt，却被直接拿去和
        # 显示坐标（`figure.dpi` 的像素）比**。200dpi 下有效阈值因此是
        # **0.90pt / 2.16pt**，而上面注释写的是 2.5pt / 6pt —— 差 2.78×，
        # 也就是说这条判据**比它自己声称的松了将近三倍**，而且是静默的
        # （阈值越小越松：擦过 1pt 的引线它不报）。
        # 现在把 pt 乘上 `dpi/72` 换成显示单位；`figure.dpi` 由函数开头那条
        # 断言钉住。改完**复核过一次全量**：三张图都没有新的 `leader-passes-marker`。
        #
        # ⚠⚠ 2026-09-27（r55 中立复核 F5）：这里原来接着写「`_TIP_FREE` 从 2.16pt
        # 放宽到 6pt **抵掉了** `_R` 收紧的那部分」—— **净结果对（无回归），但说法
        # 掩盖了机制**。复核者实测：放宽豁免确实把图 1 的两颗点移出了本类的视野
        # （`foyer_scan` 距箭头尖 2.5--6pt、`foyer_sf0_r2` 同段；把 `_TIP_FREE` 退回
        # 2.16pt 而 `_R` 保持 2.5pt，图 1 就会开火）。真正起作用的是**放宽豁免半径**，
        # 不是「两者抵消」。之所以仍判定无回归：**修前的组合（`_R`=2.5px、`_TIP`=6px）
        # 同样不开火** ⇒ 净效果与修前一致。留着这段是因为它会影响下一次调这两个数的人：
        # **把 `_TIP_FREE` 调小会立刻在 fig1 上开火**，那不是新缺陷，是这条豁免本来就在挡的。
        _R_PT, _TIP_FREE_PT = 2.5, 6.0
        _R, _TIP_FREE = _R_PT * ax.figure.dpi / 72.0, _TIP_FREE_PT * ax.figure.dpi / 72.0
        for t in ax.texts:
            if not isinstance(t, _Ann) or getattr(t, "arrow_patch", None) is None:
                continue
            _ap = t.arrow_patch
            _v = _ap.get_transform().transform_path(_ap.get_path()).vertices
            if len(_v) < 2:
                continue
            _tx, _ty = ax.transData.transform(tuple(t.xy))
            _cand = [(float(a), float(b)) for a, b in _v
                     if abs(float(a)) > 1e-6 or abs(float(b)) > 1e-6]
            if len(_cand) < 2:
                continue
            _tail = _cand[0]
            _tip = min(_cand, key=lambda q: (q[0] - _tx) ** 2 + (q[1] - _ty) ** 2)
            (px0, py0), (px1, py1) = _tail, _tip
            _dx, _dy = px1 - px0, py1 - py0
            _L2 = _dx * _dx + _dy * _dy
            if _L2 <= 1e-9:
                continue
            for _c in ax.collections:
                _off = _c.get_offsets()
                if _off is None or not len(_off):
                    continue
                for _x, _y in _off:
                    _mx, _my = ax.transData.transform((float(_x), float(_y)))
                    if ((_mx - _tx) ** 2 + (_my - _ty) ** 2) ** 0.5 < _TIP_FREE:
                        continue
                    _u = ((_mx - px0) * _dx + (_my - py0) * _dy) / _L2
                    _u = 0.0 if _u < 0 else (1.0 if _u > 1 else _u)
                    _qx, _qy = px0 + _u * _dx, py0 + _u * _dy
                    if ((_mx - _qx) ** 2 + (_my - _qy) ** 2) ** 0.5 < _R:
                        bad.append(("leader-passes-marker",
                                    t.get_text()[:24].replace("\n", " "),
                                    round(float(_x), 2), round(float(_y), 2)))
    except Exception as _e:
        bad.append(("leader-passes-marker 取不到（%r）" % _e, "", 0, 0, 0, 0))
    if bad:
        raise SystemExit(
            "!! %s：有 %d 个元素画在坐标轴外／压在别的元素上"
            "（xlim=(%s, %s), ylim=(%s, %s)）：%s\n"
            "   matplotlib 对越界元素【静默不画】—— 改坐标轴范围或标注位置，别改数据。"
            % (tag, len(bad), x0, x1, y0, y1, bad[:6]))
    # 第五类的**实测最小值**：印出来，好让文档里的数字由守卫产生而不是手写
    # （2026-09-27 r55：我手写的「4.0/6.0/5.9pt」被 codex 复算成 2.41/2.18/2.14，
    # 我自己重量也是 2.42/2.18/2.15 —— **手写的那份是错的**。这类数字一律让代码印。）
    _lm = sorted([x for x in _LMIN if x[0] is not None])
    if _lm:
        print("     第五类实测最小间距：%s" % "，".join(
            "%s %.2fpt" % (t, d) for d, t in _lm[:3]))
    _em = sorted([x for x in _EMIN if x[0] is not None])
    if _em:
        print("     第六类实测最小留白：%s" % "，".join(
            "%s%s %.2fpt" % (t, k, d) for d, k, t in _em[:3]))


# ---------------------------------------------------------------- 图 1：前沿

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
    fig, ax = plt.subplots(figsize=(3.64, 2.62))
    fig.subplots_adjust(left=0.145, right=0.995, bottom=0.155, top=0.845)
    front = sorted([(float(r["wall_min"]), float(r["slo_pct"]))
                    for r in rows if r["family"].startswith("static")])
    env, best = [], -1
    for w, s in front:
        if s > best:
            env.append((w, s)); best = s
    # 包络线：中性灰、细。它不是一条「系列」，是一条**判据**，所以不给颜色。
    ln_env, = ax.plot(*zip(*env), "-", color="0.30", lw=0.9, zorder=1,
                      label="static envelope")
    # 同机争用作废的 run 画成【空心】点：它们的墙钟/SLO 与其余各行不可比
    # （同机 >=4 条车道把逐请求 decode 间隔抬高 25~40%，见 paper/data/concurrency.csv
    # 与 §repro）。不标出来会让图 1 看上去比实际更干净 —— 审稿人 2026-09-24 指出。
    # ⚠ 2026-09-26：**改成共用的 `contested_runs()`**，不再内联第二份读取。
    bad = contested_runs()
    # ⚠ `default`（不设任何准入控制）在 runs.csv 里也归在 static 族，但它**不是**
    # 一个静态 cap：画成方框会让读者以为那是一个 cap。单独画成叉。
    NOCTRL = {"default"}   # runs.csv 里的 run 名
    # ⚠ 圈数**在真正画圈的那一行累加**，不另外数一遍 `rows` ——
    # 数一遍 `rows` 与 scatter 是两份实现，scatter 哪天不跑了计数照样报 2。
    n_ring = 0
    handles = {}
    for fam, c, mk, lab in [("static", C_STATIC, "s", "static caps"),
                            ("static_hc", C_STATIC_HC, "^", "static caps + HiCache"),
                            ("foyer", C_FOYER, "o", "Foyer"),
                            ("aimd", C_AIMD, "D", "AIMD (Concur)"),
                            ("noctrl", C_MUTE, "x", "no control")]:
        if fam == "noctrl":
            sel = [r for r in rows if r["run"].replace("pois200_", "") in NOCTRL]
        else:
            sel = [r for r in rows if r["family"] == fam
                   and r["run"].replace("pois200_", "") not in NOCTRL]
        xs = [float(r["wall_min"]) for r in sel]
        ys = [float(r["slo_pct"]) for r in sel]
        # `x` 是**空心**记号，没有 face 可描白边 —— 传 edgecolors 会被忽略并告警
        # （2026-09-27 实测），所以两条分支分开写。
        _st = dict(s=15, zorder=3, linewidths=0.35)
        if mk == "x":
            h = ax.scatter(xs, ys, c=c, marker=mk, **_st)
        else:
            h = ax.scatter(xs, ys, c=c, marker=mk, edgecolors="white", **_st)
        handles[lab] = h
        # 受污染的点再叠一层空心圈，颜色同族，只把填充挖掉
        bx = [float(r["wall_min"]) for r in sel if r["run"].replace("pois200_", "") in bad]
        by = [float(r["slo_pct"]) for r in sel if r["run"].replace("pois200_", "") in bad]
        if bx:
            ax.scatter(bx, by, facecolors="none", edgecolors=c, marker=mk, s=30,
                       zorder=4, linewidths=0.8)
            n_ring += len(bx)
    COUNTS["fig1_frontier.pdf"] = {"points": len(rows), "rings": n_ring}
    # 图 1 那条「标出最好的一条控制器臂」的标注 —— 全部从 `table1.csv` 现取
    # （Δ 最大的控制器行 = 正文 §V 说的那条；坐标与标签都跟着表走，不写死）。
    with open(os.path.join(HERE, "..", "data", "table1.csv"), encoding="utf-8") as _f:
        _t1 = [r for r in csv.DictReader(l for l in _f if not l.startswith("#"))]
    _bst = max((r for r in _t1
                if r["run"].startswith(("foyer_", "aimd2_", "foyfix")) and r.get("delta_pp")),
               key=lambda r: float(r["delta_pp"]))
    _BST_W, _BST_S = float(_bst["wall_min"]), float(_bst["slo_pct"])
    # 标签用表 I 那一列（去掉 LaTeX 的 `$`），数字用表里的 Δ。
    # ⚠ 「几条 run」也**现数**，不写死 —— 这条臂现在没有重复，将来有了，
    # 标签必须自己变（写死的「one run」会变成一句假话，而且没人会响）。
    # ⚠⚠ 2026-09-27（落地后看图抓到）：**按 label【前缀】数会把重复漏掉。**
    # 第二次运行的 label 自带「(2nd run)」，于是 `startswith(自己的 label)`
    # 只数到它自己 —— 图上印成「scans the queue (2nd run) (+2.2 pp, **one run**)」，
    # 而那条配置**有两次读数**。改为：先把 label 里的运行后缀剥掉，
    # 再按**配置名**计数。
    import re as _re2
    def _cfg(_lab):
        return _re2.sub(r"\s*\((?:2nd|3rd|repeat)[^)]*\)\s*$", "", (_lab or "")).strip()
    # ⚠ **变量名不许改**：`check_paper_numbers.py` 会拿正则
    # `_n_rep = sum\(1 for r in _t1` 扫这个文件，确认「几条 run」是**现数的**
    # 而不是写死的（历史：写死过「(tie, below it)」，最佳臂换人之后整句失效，
    # 2026-09-25 靠人读图才发现）。改名会让那条守卫报 MISS。
    _n_rep = sum(1 for r in _t1 if _cfg(r.get("label")) == _cfg(_bst["label"]))
    _NREP = {1: "one", 2: "two", 3: "three"}.get(_n_rep, "%d" % _n_rep)
    # ⚠ 2026-09-27：`\,` 必须落在**数学模式里面**。原来写的是 `"$%+.1f$\\,pp"` ——
    # matplotlib 会把 `$...$` 当 mathtext，而 `\,` 在它**外面**，于是**原样印出
    # 一个反斜杠加逗号**（`(+1.3\,pp, one run)`）。这是一个每个读者都会看到的
    # 排版缺陷，而 `.counts.json` 只报条数、不报文字 —— **没有任何守卫看得见它**。
    # 同一条也适用于 `\%`：它只在 `$...$` 里才是转义（图 1 的 y 轴标签原来就
    # 原样印着 `SLO attainment (\%)`，是 `pdftotext` 整张图核出来的）。
    _cfg_deltas = sorted(float(r["delta_pp"]) for r in _t1
                         if _cfg(r.get("label")) == _cfg(_bst["label"])
                         and r.get("delta_pp"))
    # ⚠⚠ 2026-09-27（重做时的实测结论，别再试回去）：**这条标注只能是「一行、
    # 只有臂名」**，Δ 值不进图。三个理由，都是量出来的：
    #   1. 簇的正上方清开两侧的点之后只剩约 100 个数据单位宽（5.9pt、轴宽 3.09in），
    #      而「scans the queue, three runs」这种两行框量出来要 130--140 个单位；
    #   2. 往右下放（那片区域是空的）也不行 —— 从右下进簇的引线必然从
    #      `foyer_hz1_r3`(274.4, 85.3) 与 `pairB_cap2hc`(295.0, 91.6) 身上擦过去
    #      （实测 0.8--1.5pt），而 `pairB_cap2hc` 本身就是包络的锚点，
    #      引线会与包络糊在一起；
    #   3. 从右边的空白区进则是一条 1.2in 的长引线 —— 那正是这一版要去掉的
    #      「草稿感」（参考稿的结果图里没有任何一条超过 0.4in 的引线）。
    # Δ 值在表 I 的三行里（`scans the queue` 及其两次重复）、并在 §I 与 §VI 的
    # 正文里各出现一次，不靠这张图承载。这是**展示取舍**，不是删数据：
    # 图仍然画满 38 个点、2 个空心圈（`.counts.json` 里逐条落着）。
    # 下面那段派生量与打印留着 —— 它是「图里那条标注指的是表 I 里的一族行」
    # 这条的**对照**：族里每一行都得有 Δ，少了就报错、并把读数印进运行日志。
    if len(_cfg_deltas) != _n_rep or not _cfg_deltas:
        raise SystemExit(
            "!! 图 1 的标注臂 %s 在 table1.csv 里有 %d 行、其中只有 %d 行有 Δ —— "
            "图里那条标注指的是这**一族**行，族里每一行都该有一个读数。"
            % (_cfg(_bst["label"]), _n_rep, len(_cfg_deltas)))
    print("   图 1 标注臂 %s：表 I 里 %s 行，Δ = %s"
          % (_cfg(_bst["label"]), _NREP,
             ", ".join("%+.2f" % d for d in _cfg_deltas)))
    # 两行：臂名 + 「几条 run」。⚠ 这一行**必须**留着 —— 图上写着「three runs」
    # 就等于把「这条标注指的是表 I 里的一族行」说出来；和 Δ 一样，它在表 I 与
    # §I/§VI 里也有，图上再印一次是**给读图的人**的。
    _BST_TXT = "%s\n%s runs" % (_cfg(_bst["label"]).replace("$", ""), _NREP)
    # 两条静态+HiCache 标签的坐标是手写常数，而它们指的是 `table1.csv` 里某一行
    # —— 那一行**会变**（重复落地就变过一次：`cap4_hc_r2` 209.1/68.5 顶掉了
    # `cap4_hc` 213.0/63.4）。数据一变，标注会**静默指向空白**，而
    # `assert_inside` 只查「在不在轴内」，查不出「指向的那个点在不在那儿」。
    # 下面把它钉回表里：坐标必须等于表里某一行（容差 0.05），否则报错。
    _ann_fix = {"cap4+HC": (213.0, 63.4), "cap3+HC": (236.4, 81.1)}
    for _lab, (_ax, _ay) in _ann_fix.items():
        _hit = [r["run"] for r in _t1
                if abs(float(r["wall_min"]) - _ax) < 0.05
                and abs(float(r["slo_pct"]) - _ay) < 0.05]
        if not _hit:
            raise SystemExit(
                "!! 图 1 的 %s 标注坐标 (%.1f, %.1f) 在 table1.csv 里**找不到对应的行** —— "
                "数据变了而坐标没跟上。" % (_lab, _ax, _ay))
    ax.set_xlabel("end-to-end wall clock (min)")
    ax.set_ylabel("SLO attainment (%)")
    # 纵轴放到 0：不设任何准入控制的那条 run 落在 SLO 3%，把它切掉就等于
    # 藏起「不做控制的代价」——那正是本文问题的一半。
    # ⚠ 上界 104 → **106**（2026-09-27，codex r54 复核 E）：`scans the queue` 那条
    # 两行标注的包围盒顶到 103.3，离上边框只剩 **0.85pt** —— 而它下面最近的点
    # （`foyer_scan_r2`，88.89）要求至少留 1.5pt，两者在当前高度里**放不下**
    # （12.62 + 1.38 + 1.5 > 104 − 88.89）。加 2 个单位的顶空之后同一条标注
    # 由 `assert_inside` 第 6 类守着。
    #
    # ⚠⚠ 2026-09-27（r55 中立复核 F4）：这句原来接着写「上下各得 3.65pt / 2.38pt」——
    # **两个数都不是这条标注的**。实量（守卫自己印）：`scans the queue` 上边 **3.08pt**；
    # 而 3.65pt 是 **`cap3+HC` 的左边距**（张冠李戴）；2.38pt 在三张图上**根本不存在**
    # （图 1 的最小留白就是那 3.08pt）。**结论不受影响**（3.08 > 2.0 下限），
    # 但又一次说明这类「实测值」写进注释就会漂。⇒ 一律读守卫每次构建印的那一行。
    ax.set_ylim(-3, 106); ax.set_xlim(188, 548)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    grid_y(ax)
    # 三条短标注。**引线短、端点钉在点上、文字不横穿别的点** —— 四条都由
    # `assert_inside` 在下面机械检查（文字包围盒 / 压点 / 文字互压 / 引线擦点）。
    #  - `no control`：贴在叉的右边（右侧一片空），不用引线。
    #  - `cap3+HC` / `cap4+HC`：左侧那块空区，引线横着走一小段。
    #  - 头条那条（scan）：**只有臂名、一行**，摆在簇的正上方，引线近乎垂直落下来。
    #    （为什么没有 Δ 值：见上面 `_BST_TXT` 的注释。）
    for r in rows:
        if r["run"] == "default":
            ax.annotate("no control", (288.6, 3.0), xytext=(5, 0.5),
                        textcoords="offset points", ha="left", va="center",
                        fontsize=6, color=C_INK)
    for txt, xy, xytext, ha in [
            # `cap3+HC`：坐标在 (236.4, 81.1)。正上方的空区（x 192--240 / y 88--96
            # 里没有任何点）。
            #
            # ⚠⚠ 2026-09-27（r55 复核，我自量 + codex 复算吻合）：y 原为 **86.0**，
            # 而这里原来接着写的是「包络在那一带还在 81.9 以下」—— **那句话对框的
            # 右端是错的**。框在数据坐标里是 x 193.90..234.10 / y 82.79..89.21，
            # 右缘伸到 234.1，而包络线在那里已经爬到 **82.49**：
            # 最近点 (234.20, 82.49) 距框右下角**只有 0.37pt**（0.13mm）——
            # 渲到 600dpi 看得见「C」和斜线几乎并在一起。
            # 当时的 `assert_inside` **结构上看不见它**：第 5 类只判「线采样点是否
            # 落在框内」，而 82.49 在框外 0.30 个数据单位 ⇒ 不相交 ⇒ 四类全绿。
            # 新位置 87.6 由「框到所有线段最小间距 ≥1.5pt 且其余守卫不报」机械搜出，
            # 实测 **2.21pt**；y=88.0 会与 `scans the queue` 相撞（重叠 49.9×2.1px）。
            ("cap3+HC", (236.4, 81.1), (214, 87.6), "center"),
            # `cap4+HC`：坐标在 (213.0, 63.4)，右下 x 219--262 / y 59--68 是空白。
            ("cap4+HC", (213.0, 63.4), (220, 63.0), "left"),
            (_BST_TXT, (_BST_W, _BST_S), (240, 97.0), "center")]:
        ax.annotate(txt, xy, xytext=xytext, ha=ha, va="center",
                    fontsize=5.9, color=C_INK, linespacing=1.3,
                    arrowprops=dict(arrowstyle="-|>", mutation_scale=4,
                                    lw=0.55, color="0.45",
                                    shrinkA=1.5, shrinkB=1.5))
    # 图例在**上方**：3 列 2 行。`ncol` 是按列填充的，所以 handles 的顺序
    # 按「列」给：col1=(static caps, AIMD)，col2=(HiCache, envelope)，
    # col3=(Foyer, no control)。
    legend_above(ax, ncol=3, handles=[handles["static caps"], handles["AIMD (Concur)"],
                                      handles["static caps + HiCache"], ln_env,
                                      handles["Foyer"], handles["no control"]],
                 labels=["static caps", "AIMD (Concur)", "static caps + HiCache",
                         "static envelope", "Foyer", "no control"],
                 handletextpad=0.35, columnspacing=0.9, labelspacing=0.24)
    assert_inside(ax, "fig1_frontier.pdf")
    _p = os.path.join(HERE, "fig1_frontier.pdf")
    fig.savefig(_p, metadata=_META); plt.close(fig); _check_width(_p)


# ------------------------------------------------------- 图 2：墙钟两段分解
# 图 2 只画正文【点名】的那些臂。34 行挤在一张单栏图里，行高只有 6.5pt，
# 标签成对重叠、连百分比也在撞（2026-09-26 作者渲图后指出）。
# ⚠ 图的**范围**（6.3%–41.9%）仍然是对**全部 39 条**算的，图注里写明这一点 ——
# 画出来的是子集，报出来的不是，两者混起来就是「图的集合与正文的集合不一致」。
DECOMP_KEEP = [
    ("default", "no control"), ("cap1", "cap1"), ("cap2", "cap2"),
    ("cap3_fixed", "cap3"), ("cap4", "cap4"), ("cap5", "cap5"),
    ("pairB_cap2hc", "cap2+HC"), ("cap3_hc_r2", "cap3+HC"),
    ("cap4_hc_r2", "cap4+HC"), ("cap6_hc", "cap6+HC"), ("cap8_hc", "cap8+HC"),
    ("foyer_hc", "base"), ("foyer_sf0_r2", "sf=0"), ("foyer_hz1", "horizon=1"),
    ("foyer_hz2_r2", "horizon=2"), ("foyfix_hc", "all throttles off"),
    ("aimd2_paper_r3", "AIMD (paper)"),
]


def _lab_of(run):
    """图 2/图 3 共用的可读标签 —— 两处各写一份必然分叉（本项目记过这条）。"""
    return {k: v for k, v in DECOMP_KEEP}.get(run, short(run))


def fig_decomp():
    """C1/C3：墙钟 = 有效工作 + 空转；空转 6.3%–41.9%（39 条 run，2026-09-26 现算）。

    柱长是【采样跨度】span（busy+idle 精确等于它），不是 run_summary 的墙钟；
    两者差约 6 分钟，是采样器比第一个请求早启动造成的，已在图注里说明。

    只画 DECOMP_KEEP 里的臂（见那里的注释）；缺一条直接报错，不静默少画。
    """
    _all = {r["run"]: r for r in load("decomp.csv") if r["idle_pct"]}
    _miss = [k for k, _ in DECOMP_KEEP if k not in _all]
    if _miss:
        raise SystemExit("!! fig2 要画的臂不在 decomp.csv 里：%s" % _miss)
    rows = sorted((_all[k] for k, _ in DECOMP_KEEP), key=lambda r: float(r["wall_min"]))
    _lab = {k: _lab_of(k) for k, _ in DECOMP_KEEP}
    y = range(len(rows))
    busy = [float(r["busy_min"]) for r in rows]
    idle = [float(r["idle_min"]) for r in rows]
    fig, ax = plt.subplots(figsize=(3.47, 3.30))
    fig.subplots_adjust(left=0.205, right=0.995, bottom=0.125, top=0.945)
    # 堆叠的两段之间留一道白缝（`edgecolors="white"`）：不留的话蓝与琥珀直接
    # 相接，在 0.9pt 的细柱上会互相渗色，读者看不出分界在哪。
    ax.barh(y, busy, color=C_BUSY, label="busy (engine running)", height=0.66,
            edgecolor="white", linewidth=0.5)
    ax.barh(y, idle, left=busy, color=C_IDLE,
            label="idle (no request in flight)", height=0.66,
            edgecolor="white", linewidth=0.5)
    ax.set_yticks(list(y))
    _bad = contested_runs()
    # ⚠ `\ddagger` **不**走数学模式：Nimbus Sans 的 OS/2 表没有字重记录（见头部），
    # 数学模式的自定义字体栈对它不保险；直接用 Unicode `‡`，走字体回退链。
    _ylabs = [_lab[r["run"]] + (" ‡" if r["run"] in _bad else "") for r in rows]
    ax.set_yticklabels(_ylabs)
    LABELS["fig2_decomp.pdf"] = list(_ylabs)
    # ⚠ 计数与打斜线**在同一分支里**：分开写就是两份实现，斜线哪天不画了计数照样报数。
    _n_hatch = 0
    for i, r in enumerate(rows):
        if r["run"] in _bad:      # 受争用影响的柱子打斜线，与干净的一眼看得出
            ax.barh(i, float(r["busy_min"]) + float(r["idle_min"]), height=0.66,
                    color="none", edgecolor="0.50", hatch="//", lw=0.0, zorder=4)
            _n_hatch += 1
    ax.invert_yaxis()
    ax.set_xlabel("sampled span (min)")
    # ⚠⚠ 2026-09-27（codex r54 复核 E）：`xlim` 原来是 **575**，而「最长柱子 + 标注」
    # **量出来**是 **575.21** 个单位 —— 那条 `36%`（`cap1`）的右缘**已经在边框外面
    # 0.07pt**，也就是「几乎贴住右边框」而不是「有充裕边距」。
    # 旧注释写的是「527.4 + 7 + 三个字符 ≈ 557，575 收得住」—— 那是**估计**，
    # 而估计的字宽比真值小（本项目记过：估计只能用来**加**检查，不能用来撤检查）。
    # 现在按 `assert_inside` 量出的包围盒定 xlim：585 给那条标注留 **3.1pt**。
    ax.set_xlim(0, 585)
    # 空转百分比【一律标在柱端外侧】，墨色（不用白字压在色块上 —— 压在琥珀色上
    # 的白字在灰度打印时会糊掉，而这条柱子里有一条还叠着斜线）。
    # 留白由 `assert_inside` 的第 6 类（`text-too-close-to-frame`）机械守着：任何标注的
    # 包围盒离轴框不足 2pt 就报错 —— 改 `xlim` / 改字号的都要过它。
    for i, r in enumerate(rows):
        _end = float(r["busy_min"]) + float(r["idle_min"])
        ax.text(_end + 7, i, "%.0f%%" % float(r["idle_pct"]), va="center",
                ha="left", fontsize=6.0, color=C_INK)
    COUNTS["fig2_decomp.pdf"] = {"bars": len(rows), "hatched": _n_hatch}
    grid_x(ax)
    legend_above(ax, ncol=2, handles=[plt.Rectangle((0, 0), 1, 1, color=C_BUSY),
                                      plt.Rectangle((0, 0), 1, 1, color=C_IDLE)],
                 labels=["busy (engine running)", "idle (no request in flight)"],
                 columnspacing=1.4, center=True)
    assert_inside(ax, "fig2_decomp.pdf")
    _p = os.path.join(HERE, "fig2_decomp.pdf")
    fig.savefig(_p, metadata=_META); plt.close(fig); _check_width(_p)


# --------------------------------------------------- 图 3：步时间的两个测量
def fig_steptime():
    """C2：步时间由两个【独立】方法测到，且两者给出一致的排序。

    这张图**不在**默认生成的三张里（见 `__main__`），函数保留是为了随时能
    恢复；样式已跟着 2026-09-27 重做的那一套走。
    """
    # ⚠ 与图 2 同因：34 行挤在单栏图里标签成对重叠（2026-09-26 作者看图后指出）。
    # 只画正文点名的那批臂；缺一条直接报错，不静默少画。
    _all = {r["run"]: r for r in load("decomp.csv") if r["step_back_ms"]}
    _miss = [k for k, _ in DECOMP_KEEP if k not in _all]
    if _miss:
        raise SystemExit("!! fig3 要画的臂不在 decomp.csv 里：%s" % _miss)
    rows = [_all[k] for k, _ in DECOMP_KEEP]
    rows.sort(key=lambda r: float(r["step_back_ms"]))
    y = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(3.3, 3.3))
    fig.subplots_adjust(left=0.16, right=0.995, bottom=0.145, top=0.90)
    for i, r in enumerate(rows):
        a, b = float(r["step_back_ms"]), float(r["step_perreq_ms"])
        ax.plot([b, a], [i, i], "-", color="0.80", lw=0.8, zorder=1)
    ax.scatter([float(r["step_back_ms"]) for r in rows], y, marker="o", s=15,
               facecolors="none", edgecolors=C_FOYER, linewidths=0.9, zorder=3,
               label="back-derived (busy $\\times$ conc / tokens)")
    ax.scatter([float(r["step_perreq_ms"]) for r in rows], y, marker="x", s=14,
               color=C_STATIC, linewidths=0.9, zorder=3,
               label="per-request (independent)")
    _bad = contested_runs()
    ax.set_yticks(y)
    # ⚠ ‡ 是**写进 y 轴标签**的，计数就在生成标签的那一步累加 —— 分开写是两份实现。
    _labs, _n_mark = [], 0
    for r in rows:
        if r["run"] in _bad:
            _labs.append(_lab_of(r["run"]) + " ‡")
            _n_mark += 1
        else:
            _labs.append(_lab_of(r["run"]))
    ax.set_yticklabels(_labs)
    ax.invert_yaxis()
    ax.set_xlabel("step time (ms)")
    # 上界必须盖住 42.5（default 的反向步成本）—— 原来是 39，于是 `default` 与
    # `foyer_hz1_r2` 的圆点被**静默裁掉**，而 `default` 正是图注在说的一条 run。
    # 下界 13 是为了让 16.2 的「读一遍权重」虚线留在图里。
    ax.set_xlim(13, 45)
    ax.axvline(16.2, ls=(0, (1, 1.6)), lw=0.8, color="0.45")
    # 放左下角：最上面几行的 × 标记会一直伸到 x≈24，文字摆在顶部会撞上
    ax.text(16.9, len(rows) - 0.55, "weights-read floor\n(15.2 GB / 936 GB/s)",
            fontsize=5.9, color=C_MUTE, va="bottom", linespacing=1.3)
    COUNTS["fig3_steptime.pdf"] = {"rows": len(rows), "marked": _n_mark}
    grid_x(ax)
    legend_above(ax, ncol=1)
    assert_inside(ax, "fig3_steptime.pdf")
    _p = os.path.join(HERE, "fig3_steptime.pdf")
    fig.savefig(_p, metadata=_META); plt.close(fig); _check_width(_p)


# ------------------------------------------------ 图 4：空转率 vs 墙钟
def fig_idle_segments():
    """C3 的直接证据：空转段【很长】，和 tool wait 同量级。

    画的是生存函数 P(空闲段 > x)。**不在**默认生成的三张里（见 `__main__`）。
    """
    rows = load("idle_seg_raw.csv")
    d = sorted(float(r["duration_s"]) for r in rows)
    n = len(d)
    ys = [100.0 * (n - i) / n for i in range(n)]
    fig, ax = plt.subplots(figsize=(3.3, 2.4))
    fig.subplots_adjust(left=0.145, right=0.995, bottom=0.165, top=0.965)
    ax.step(d, ys, where="post", color=C_STATIC, lw=0.9)
    for x, lab, ty in [(16.85, "mean tool wait\n16.85 s", 97),
                       (60.0, "1 min", 76)]:
        ax.axvline(x, ls=(0, (1, 1.6)), lw=0.8, color="0.45")
        ax.text(x * 1.07, ty, lab, fontsize=5.9, color=C_MUTE, va="top",
                linespacing=1.3)
    med = d[n // 2]
    ax.plot([med], [50], "o", ms=3.2, color=C_FOYER, zorder=4)
    ax.annotate("median %.1f s" % med, (med, 50), xytext=(5, 5),
                textcoords="offset points", fontsize=5.9, color=C_INK)
    ax.set_xscale("log")
    ax.set_xlim(4, 700); ax.set_ylim(0, 100)
    ax.text(4.6, 4, "5 s sampling floor", fontsize=5.9,
            color=C_MUTE, linespacing=1.3)
    ax.set_xlabel("duration of an idle stretch (s, log scale)")
    # ⚠ `\%` 不是 matplotlib 的转义 —— 它只在 `$...$` 数学模式里才是。
    # 写在数学模式外，pdf 上就原样印出一个反斜杠加百分号（`pdftotext` 能验）。
    ax.set_ylabel("% of stretches longer than $x$")
    assert_inside(ax, "fig4_idle_segments.pdf")
    fig.savefig(os.path.join(HERE, "fig4_idle_segments.pdf"), metadata=_META)
    plt.close(fig)


# ------------------------------------------------------ 图 5：负载两端反转
def fig_loadtier():
    """C6：同一个节流开关，低载是纯负担、高载是承重的。

    ⚠ 25 档那两根柱子来自旧 harness，与 200 档不同代——图里必须标出来。
    **不在**默认生成的三张里（见 `__main__`）。
    """
    rows = load("loadtier.csv")
    fig, axes = plt.subplots(1, 2, figsize=(3.3, 2.4))
    fig.subplots_adjust(left=0.115, right=0.995, bottom=0.20, top=0.90,
                        wspace=0.35)
    for ax, tier in zip(axes, ["25", "200"]):
        sub = [r for r in rows if r["tier"] == tier]
        on = float([r for r in sub if r["throttle"] == "on"][0]["wall_min"])
        off = float([r for r in sub if r["throttle"] == "off"][0]["wall_min"])
        ax.bar([0, 1], [on, off], color=[C_BUSY, C_IDLE], width=0.62,
               edgecolor="white", linewidth=0.5)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["throttle\nON", "OFF"])
        ax.set_title("%s sessions" % tier, pad=3)
        if tier == "25":
            ax.set_ylabel("wall clock (min)")
        top = max(on, off)
        ax.set_ylim(0, top * 1.30)
        ax.text(0.5, top * 1.06, "%+.0f%%" % ((off - on) / on * 100),
                ha="center", va="bottom", fontsize=7.5, color=C_INK)
        ax.set_xlim(-0.55, 1.55)
        if tier == "25":
            ax.set_xlabel("harness: earlier revision", fontsize=5.9, color=C_MUTE,
                          labelpad=2)
        assert_inside(ax, "fig5_loadtier.pdf")
    fig.savefig(os.path.join(HERE, "fig5_loadtier.pdf"), metadata=_META)
    plt.close(fig)


# ------------------------------------------------------------ 图 6：horizon
def fig_horizon():
    """C5 之一：增长预留的扫描。不是单调的——h=0 打崩 SLO，h=2 比 h=3 还慢。

    ⚠ 这张图有**两个 y 轴**，而 dataviz 的纪律是「一张图一个纵轴」。它不在论文
    的三张图里（见 `__main__`），所以这里只做字号/线宽对齐，没有重画成两张。
    """
    rows = sorted(load("horizon.csv"), key=lambda r: int(r["horizon"]))
    h = [int(r["horizon"]) for r in rows]
    fig, ax = plt.subplots(figsize=(3.3, 2.4))
    fig.subplots_adjust(left=0.145, right=0.855, bottom=0.19, top=0.965)
    l1, = ax.plot(h, [float(r["wall_min"]) for r in rows], "o-", color=C_FOYER,
                  ms=3.2, lw=0.9, label="wall clock (left)")
    ax.set_xlabel("growth reserve (horizon rounds)")
    ax.set_ylabel("wall clock (min)")
    ax.set_xticks(h); ax.set_xlim(-0.3, 3.3)
    ax2 = ax.twinx()
    l2, = ax2.plot(h, [float(r["slo_pct"]) for r in rows], "s--", color=C_STATIC,
                   ms=3.2, lw=0.9, label="SLO (right)")
    ax2.set_ylabel("SLO (%)")
    ax2.grid(False)
    ax2.set_ylim(70, 95)
    ax2.set_yticklabels(["%.0f%%" % v for v in ax2.get_yticks()])
    legend_above(ax, ncol=2, handles=[l1, l2], labels=["wall clock (left)",
                                                       "SLO (right)"])
    # ⚠ 图 6 有**两个 y 轴**：SLO 那条画在 `ax2` 上，只查 `ax` 会漏掉它
    # （`assert_inside` 读的是各自轴的 `xlim`/`ylim`）。
    assert_inside(ax, "fig6_horizon.pdf")
    assert_inside(ax2, "fig6_horizon.pdf (右轴 SLO)")
    fig.savefig(os.path.join(HERE, "fig6_horizon.pdf"), metadata=_META)
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

    # HiCache 静态点：控制器臂实际运行的配置（§IV 的要点是它没有悬崖）。
    # ⚠ 2026-09-25：`cap5_hc` 入表后这里是**四条**。漏掉它会让图上看不到
    # §IV 新讨论的第三段（codex 第 25 轮指出：正文写了四配置三段，图只画三点）。
    # 2026-09-25 再加 `cap6_hc` / `cap8_hc`：§IV 现在讨论**六**个 HiCache 配置。
    hids = ["pairB_cap2hc", "cap3_hc", "cap4_hc", "cap5_hc", "cap6_hc", "cap8_hc"]
    hrows = sorted([r for r in load("decomp.csv") if r["run"] in hids],
                   key=lambda r: float(r["running"]))

    # ⚠ 2026-09-28：图注里的两个条数是**可数主张**（"five device-only" / "six HiCache"），
    # 而 fig7 此前**没有**在 `.counts.json` 里登记 ⇒ 那两个数**一条守卫都没有**
    # （正是项目记过的「图注里的条数也是派生量」）。由画图的人自己报出来。
    COUNTS["fig7_elasticity.pdf"] = {"device_points": len(rows), "hicache_points": len(hrows)}
    hrb = [float(r["running"]) for r in hrows]
    ht1 = [float(r["step_back_ms"]) for r in hrows]

    fig, ax = plt.subplots(figsize=(3.66, 2.72))
    fig.subplots_adjust(left=0.135, right=0.995, bottom=0.145, top=0.855)
    xs = [1.00 + i * 0.008 for i in range(110)]
    # 拟合线：中性灰虚线。它是**判据**不是系列，颜色留给三条测量。
    ln_fit, = ax.plot(xs, [t2[0] * (x / rb[0]) ** e2 for x in xs], "--",
                      color="0.45", lw=0.8,
                      label="fit to $\\tau_2$: $\\varepsilon$=%.2f ($R^2$=%.2f)"
                            % (e2, r2v))
    ln_t1, = ax.plot(rb, t1, "o-", color=C_FOYER, ms=3.2, lw=0.9,
                     label="model-consistent $\\tau_1$")
    ln_t2, = ax.plot(rb, t2, "s-", color=C_STATIC, ms=3.2, lw=0.9,
                     label="per-request $\\tau_2$")
    ln_hc, = ax.plot(hrb, ht1, "^--", color=C_STATIC_HC, ms=3.2, lw=0.9,
                     label="with HiCache (the controllers' config)")
    # ⚠⚠ 2026-09-27：**六个 `+HC` 点标签全部去掉**。原来每个绿三角旁边都挂一个
    # 「+HC」（那是为了修「后三条没有标注、读者以为只有三个 HiCache 配置」而加的），
    # 但实测**六个都放不下**：红 τ₁ 线与灰拟合线之间的带只有 1--3 个数据单位高，
    # 而 5.9pt 的一行字就有 7 个单位；摆到下面必然压在灰色拟合线上，摆到上面
    # 必然压住红线或 `cap2`/`cap3` 的标签。参考稿的做法是**不逐点标注** ——
    # 绿色虚线加图例里的「with HiCache (the controllers' config)」已经把这六个点
    # 归成一组，x 轴（在跑数）又能定出每一个是哪条。**一致性**也回来了：
    # 不存在「前三个有标签、后三个没有」。
    #
    # 只留 device-only 那五个点的名字（它们与表 I 的 `cap1`--`cap5` 行一一对应）。
    # 偏移逐个手摆；两边的条数由下面那条断言钉死 —— `zip` 按短的截断，
    # 数据长了一条而偏移没长，图上就少几个标注而**没有任何东西会报错**。
    #
    # ⚠⚠ 2026-09-27（r54 复核 A）：**`cap2`/`cap3`/`cap4` 三个偏移原来是反的**。
    # 手写的理由写的是「右上是 cap4 与红线」「右上被红线占着」，于是把标签往**左上**
    # 挪 —— 而红线（model-consistent τ₁）是**从左下往右上爬**的：`cap3`→`cap4` 与
    # `cap4`→`cap5` 两段在显示坐标里斜率 **0.64 pt/px**（32°），一段 13pt 宽的标签
    # 沿横轴就爬升 8pt，左上的位置正好落在它的路径上。三个标签的文字包围盒里分别
    # 有 5 / 7 / 3 个线采样点（densify 到 0.25pt），300dpi 下红线正切过字形。
    # 当时的 `assert_inside` 有 4 类检查，**没有一类是「文字 vs 数据线」**，
    # 所以四条断言全绿也看不见它（已补第 5 类，见 `assert_inside`）。
    #
    # ⚠⚠⚠ 2026-09-27（r55 中立复核 F3）：这一段原来写着「新位置由『包围盒到所有线段
    # 的最小间距 ≥ 1.5pt』**机械搜出来**」，并把 cap3/cap4 的实测值写成 **6.0pt**。
    # **两处都不准**，根因由复核者查到（工具源码仍在 `/tmp/probe/`）：
    #   · `/tmp/probe/joint7.py:73` 的判据是 `if c <= 1.5`，而 `c` 是**显示坐标
    #     （200dpi 的像素）** ⇒ 实际执行的是 **1.5px = 0.54pt**，不是 1.5pt。
    #     （与本文件第 5 项修掉的 pt/px 混用是**同一类错**，只是那次在守卫里、
    #     这次在选择工具里。）
    #   · `/tmp/probe/verify7.py:113` 自己印的是「**可行组合 0 个**」——
    #     即机械搜索在它自己的判据下**一个都没选出来**。最终这三对偏移是
    #     **人从候选表里挑的**，再由该脚本第二段逐条复算确认。
    # 实际位置仍成立（三个标签实测 2.15 / 2.18 / 2.42pt，都 > 1.5pt），且现已由
    # 第 5 类的**真 1.5pt 阈值**守着 —— 但「机械搜出来」这个说法不准确，**不许再写**。
    #
    # 位置与理由（人工挑 + 复算确认）：
    #   cap2 往上抬到 +8pt —— 红线在它右侧以 0.25pt/px 爬升，抬够就整段在框下方；
    #        再往左/下都不行（左下方是 `pairB_cap2hc` 那颗绿三角）。
    #   cap3 / cap4 把框整体挪到点的**左侧**（dx=-16 使框右缘仍离点 3pt）——
    #        红线在它们左边是**往下走**的，于是框在它上方。
    # ⚠ 「实测最小间距」见每次构建时第 5 类自己印的那一行（2026-09-27 起）。
    doff = [(3, 4),     # cap1  (1.00, 28.8) 右上（左侧是 y 轴）
            (3, 8),     # cap2  (1.27, 27.4) 右上（抬到红线上方；下方是绿三角）
            (-16, 3),   # cap3  (1.53, 29.7) 框在点左侧（右边是上爬的红线）
            (-16, 2),   # cap4  (1.65, 32.4) 框在点左侧（同上）
            (2, 5)]     # cap5  (1.84, 36.7) 右上（上面是坐标区上沿）
    assert len(doff) == len(rows), (
        "device-only 标注偏移 %d 个、点 %d 个 —— `zip` 会静默截断，"
        "图上少标几个谁也不报错" % (len(doff), len(rows)))
    for r, x, y, off in zip(rows, rb, t1, doff):
        ax.annotate(r["run"].replace("_fixed", ""), (x, y), xytext=off,
                    textcoords="offset points", fontsize=5.9, color=C_INK)
    # ⚠ `hids` 现在是**六**条（2026-09-25 从 3 条长上来的）。它们不再逐点标注，
    # 但这条断言要留着：哪天子集写错（少一条 HiCache 配置），绿色曲线会静默
    # 少画一个点，而图注里的「six HiCache configurations」没人对得上。
    assert len(hrows) == 6, "HiCache 子集应当是 6 条，现在是 %d 条" % len(hrows)
    ax.set_xlabel("mean running requests during busy time")
    ax.set_ylabel("step time (ms)")
    ax.set_xlim(0.92, 1.98); ax.set_ylim(17, 40)
    grid_y(ax)
    # 图例在**上方**，2 列 2 行（4 条）。按列填：col1=(fit, τ2)，col2=(τ1, +HC)。
    legend_above(ax, ncol=2, handles=[ln_fit, ln_t2, ln_t1, ln_hc],
                 labels=["fit to $\\tau_2$: $\\varepsilon$=%.2f ($R^2$=%.2f)"
                         % (e2, r2v),
                         "per-request $\\tau_2$",
                         "model-consistent $\\tau_1$",
                         "with HiCache (the controllers' config)"],
                 columnspacing=1.2, labelspacing=0.24, center=True)
    assert_inside(ax, "fig7_elasticity.pdf")
    _p = os.path.join(HERE, "fig7_elasticity.pdf")
    fig.savefig(_p, metadata=_META); plt.close(fig); _check_width(_p)


def fig_transfer():
    """两条 trace 的「兑现率 vs 在跑数」—— §VI 的迁移主张就画在这一张上。

    **不在**默认生成的三张里（见 `__main__`）；样式已跟着重做的那一套走。
    """
    fig, ax = plt.subplots(figsize=(3.3, 2.4))
    fig.subplots_adjust(left=0.145, right=0.995, bottom=0.17, top=0.945)
    main_dev = load("reuse.csv")
    xt = load("reuse_x.csv")
    md = sorted([r for r in main_dev if r["family"] == "device_only"],
                key=lambda r: float(r["Rbar_busy"]))
    mh = sorted([r for r in main_dev if r["family"] == "hicache"],
                key=lambda r: float(r["Rbar_busy"]))
    x = sorted(xt, key=lambda r: float(r["Rbar_busy"]))
    ax.plot([float(r["Rbar_busy"]) for r in md],
            [100 * float(r["realized_frac"]) for r in md],
            "s-", color=C_STATIC, ms=3.2, lw=0.9, label="main trace, device-only")
    ax.plot([float(r["Rbar_busy"]) for r in mh],
            [100 * float(r["realized_frac"]) for r in mh],
            "^", color=C_STATIC_HC, ms=3.2, lw=0,
            label="main trace, with a host tier")
    ax.plot([float(r["Rbar_busy"]) for r in x],
            [100 * float(r["realized_frac"]) for r in x],
            "o-", color=C_FOYER, ms=3.2, lw=0.9, label="second trace, device-only")
    for lbl, sel in (("cap1", md[:1]), ("cap5", md[-1:]),
                     ("cap2", x[:1]), ("cap8", x[-1:])):
        r = sel[0]
        ax.annotate(lbl, (float(r["Rbar_busy"]), 100 * float(r["realized_frac"])),
                    xytext=(4, 3), textcoords="offset points", fontsize=5.9,
                    color=C_INK)
    ax.set_xlabel("mean running requests during busy time")
    # ⚠ `\%` 同上：必须在数学模式里，否则 pdf 上原样印反斜杠。
    ax.set_ylabel("realization (% of that trace's reuse bound)")
    ax.set_xlim(0.9, 1.95); ax.set_ylim(30, 98)
    legend_above(ax, ncol=1)
    assert_inside(ax, "fig8_transfer.pdf")
    fig.savefig(os.path.join(HERE, "fig8_transfer.pdf"), metadata=_META)
    plt.close(fig)


if __name__ == "__main__":
    import json
    # ⚠ key 用**输出的 pdf 文件名**，不用函数名 —— 图 7 的函数叫 `fig_cancel`
    # 而文件叫 `fig7_elasticity.pdf`，靠函数名反推映射会漏掉它（2026-09-25 踩到）。
    # ⚠ 2026-09-26 篇幅手术：论文只留三张图（fig1 前沿、fig2 忙闲分解、fig7 弹性）。
    # 被删的五张（fig3 步时间两法 / fig4 idle 段 / fig5 负载层级 / fig6 horizon /
    # fig8 转移）**函数都还在**，只是不再默认生成 —— 要恢复就把它们加回本列表，
    # 并把正文里的 \ref 与图注一并恢复（正文现在不引它们）。
    for fn, _pdf in ((fig_frontier, "fig1_frontier.pdf"), (fig_decomp, "fig2_decomp.pdf"),
                     (fig_cancel, "fig7_elasticity.pdf")):
        _CUR[0] = _pdf
        fn()
        print("ok", fn.__name__, "->", _pdf)
    _CUR[0] = None
    with open(os.path.join(HERE, ".labels.json"), "w") as _f:
        json.dump({k: list(v) for k, v in LABELS.items()}, _f, indent=1)
    with open(os.path.join(HERE, ".deps.json"), "w") as _f:
        json.dump({k: sorted(v) for k, v in DEPS.items()}, _f, indent=1)
    print("deps:", {k: len(v) for k, v in sorted(DEPS.items())})
    with open(os.path.join(HERE, ".counts.json"), "w") as _f:
        json.dump(COUNTS, _f, indent=1, sort_keys=True)
    print("counts:", COUNTS)
