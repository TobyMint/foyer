#!/usr/bin/env python3
"""正文数字 ↔ 数据文件的逐项对照 —— 改完论文后跑一遍。

为什么要有这个：2026-09-24 一天里，每一批修正都引入过被下一轮审查抓到的新错误
（`audit_numbers.py` 只管"这个数在不在任何 CSV 里"，不管"它是否等于 CSV 里那个量
算出来的值"）。本脚本补上后半截：对每一组【有生成器】的派生量，把 CSV 算出来的值
与正文里的串做匹配。

它不是万能的 —— 匹配是字符串级的，正文里一个数可能以 1 位或 2 位小数出现，
所以每个断言都同时试几种写法。**它只回答"正文里有没有这个值"，不回答
"这个值用在这里对不对"**，后者仍然要靠审查。

用法: python3 check_paper_numbers.py          # 全部检查
      python3 check_paper_numbers.py -v       # 连通过的一起列
"""
import collections, csv, datetime, glob, hashlib, importlib.util, json, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
# ⚠⚠⚠ 2026-09-27（装 supplement 时抓到）：`supplement.tex` **必须排除**。
# 它和正文印的是**同一批数字**，并进 `alltext` 就等于**给每条守卫开了一个「副本」**：
# 一个数在正文里被改坏、却在 supplement 里还留着 ⇒ 守卫照样命中 ⇒ **全稿检查强度一起塌**。
# 这正是下面 `SUPP` 那段注释写明的道理（那里说的是 `paper/supplement_material*.md`，
# 同一族）。实测：不排除时 `次要未印` 从 **84 掉到 69** —— 少了 15 条在真查正文的检查。
# ⇒ supplement 是**独立文档**（单独编译、单独上传），不是正文的一部分。
TEX = sorted(f for f in glob.glob(os.path.join(ROOT, "paper", "*.tex"))
             if os.path.basename(f) != "supplement.tex")
VERBOSE = "-v" in sys.argv


def load(p):
    return [r for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))]


def strip_comments(s):
    """剥掉**未转义**的 `%` 注释（`\%` 要保留 —— 正文满是 `34.8\%`）。

    ⚠ 2026-09-26：原来只有 caption 那条路径剥注释（codex r36 的构造），而
    `paper_text()` 直接把原文喂给全稿搜索 ⇒ `alltext` 里**含注释文字**。
    `paper/sec_a100.tex` 是个 8 行注释的**存根**（内容已并入 `sec_xtrace.tex`），
    里面的「目标 30 页 -> 12 页」这类字样**可能让短数字检查假通过**。
    沙箱实测（剥掉全部 .tex 的注释后重跑）：**对现有 760 项检查零影响** ⇒
    这是**纯预防性**改动，不是修现行错误。
    """
    return re.sub(r"(?<!\\)%.*", "", s)


def strip_cites(s):
    """剥掉**所有「key 里带数字」的 LaTeX 命令**，只留下真正的正文散文。

    覆盖：`\\cite`（含 `\\citep`/`\\citet`/`\\cite*` 与可选参数）、`\\ref`/`\\eqref`/
    `\\autoref`/`\\cref`/`\\Cref`/`\\label`、`\\input`/`\\include`/`\\lstinputlisting`、
    `\\includegraphics`（含可选参数）、以及裸的 `figN_*.pdf` 文件名。

    **为什么剥**：这些命令的 `{...}` 里装的是**标识符，不是正文里的数**，而 `has()`
    的边界会认下它们 ⇒ 一条盯某个数的检查可以靠撞上一个 key 常年假通过。
    函数名保留 `strip_cites`（历史名，调用点很多），实际范围已不止 cite。

    ⚠ **剥掉的文本不能再用作「结构锚点」** —— `\\label{}` 被剥掉后，靠它定位的守卫
    会静默失效。结构定位请用 `paper_text_struct()`（只剥注释的那一份）。

    ⚠⚠ 2026-09-27（r54 复核 B）：**cite key 里的数字不是正文里的数**，而
    `has()` 的边界认下它们 —— 左边 `(?<![\\d.])` 被 `k` 满足、右边 `(?!\\d)(?!\\.\\d)`
    被 `,` 满足，于是 `\\cite{dynamo,perbank24,etm2,perbank26}` 里的 `perbank24`
    让「查 24」通过。当时唯一被它救活的正是
    `§VII pois200_foyer_push_25 队列最大（运行窗口）`（期望 24，运行窗口
    `backlog.csv` 的 `waiting_max`）—— 那个读数早已随压缩删除，这条检查
    **本该报 MISS 或退役**，却因为撞上 bib key 而常年印 OK，于是它在
    「退役未生效」的 `!!` 名单里躺着：一条**假通过**被判成了一次**真退役**。

    沙箱实测（抹掉 `\\cite{...}` 后重跑）：**OK 集合恰好少这一行、MISS 仍 0、
    其余 424 行逐条不变**。反向测试：往正文插一个 `\\cite{xxx99}` 并加一条盯 99 的
    检查 ⇒ 改前印 OK、改后报 MISS（都跑过）。

    ⚠ 同类通道还有 `\\ref{sec:a100}` / `\\label{sec:a100}` / `\\input{sec_a100}`
    —— 它们的 key 里也有数字。这里**只剥 cite**：那三个当前的 key 里的数字
    （`a100`）没有被任何检查当值查过（剥掉之后 0 项新 MISS），够用即可；
    真要剥它们是一条独立改动，不在本次范围内（记在这里，免得下一个人以为漏了）。
    """
    # ⚠⚠ 2026-09-27（r55 复核）：原来这里接着写的是「同类通道还有 `\ref`/`\label`/
    # `\input` —— 这里**只剥 cite**，够用即可；真要剥它们是一条独立改动，不在本次
    # 范围内」。codex r55 复核把那条**留着没做的改动**点了出来：剥掉当前正文的
    # `ref`/`input`/`includegraphics` 后仍是 **854 项 / 0 MISS** ⇒ 现在确实没有
    # 假通过，但**通道是开着的**（`\ref{sec:a100}` / `\label{sec:a100}` /
    # `\input{sec_a100}` / `fig7_elasticity.pdf` 里的数字都能喂给 `has()`）。
    # 「够用即可」是当时的判断；既然代价是一次正则、收益是关掉一整类通道，就关掉。
    #
    # ⚠ 顺序有讲究：先剥**带 key 的命令**，最后剥 `\ref` 这类 —— 一次 alternation
    # 写完会被 `[^{}]*` 的回溯影响可读性，分开写每一条都能单独测。
    s = re.sub(r"\\cite[a-zA-Z]*\*?\s*(?:\[[^\]]*\]\s*)*\{[^{}]*\}", " ", s)
    # `\ref{}` / `\eqref{}` / `\autoref{}` / `\cref{}` / `\Cref{}` / `\label{}`
    s = re.sub(r"\\(?:ref|eqref|autoref|[cC]ref|label)\*?\s*\{[^{}]*\}", " ", s)
    # `\input{}` / `\include{}` / `\includegraphics[...]{}` / `\lstinputlisting`
    s = re.sub(r"\\(?:input|include|lstinputlisting)\*?\s*\{[^{}]*\}", " ", s)
    s = re.sub(r"\\includegraphics\*?\s*(?:\[[^\]]*\]\s*)*\{[^{}]*\}", " ", s)
    # 图形文件名（`\includegraphics` 已被上面剥掉，这里是**别处**出现的裸文件名，
    # 例如 `figs/fig7_elasticity.pdf` 写在正文或图注里）
    s = re.sub(r"\bfig\d+_[A-Za-z0-9_]+\.pdf\b", " ", s)
    return s


def paper_text():
    return {os.path.basename(f): strip_cites(strip_comments(
        open(f, encoding="utf-8").read())) for f in TEX}


def paper_text_struct():
    """**只剥注释、不剥命令**的那一份 —— 专供「按结构定位」的查找用。

    ⚠⚠ 2026-09-27（r55 处置中自己踩到）：我把 `\\label{}` 也加进了 `strip_cites`，
    于是 `_caption_of()` 再也找不到 `\\label{fig:frontier}`，**当场报出 3 条
    「找不到这张图的 caption」的 MISS**。那是我引入的回归，不是原有缺陷。
    根因是 `paper_text()` 一个人扛了两件事：
      1. **数字检索**（`has()`）—— 这里命令的 key 是**噪声**，必须剥；
      2. **结构定位**（`_caption_of` 找 `\\label{}`）—— 这里命令是**锚点**，剥了就瞎。
    两件事对「要不要剥 label」的要求正好相反。所以分成两份：
      · `paper_text()`        —— 剥 cite + ref + input + includegraphics（喂 `has()`）
      · `paper_text_struct()` —— 只剥注释（喂下面 `_caption_of`）
    ⚠⚠ 2026-09-27（r56 中立复核 3）：这一行原来写着「**只有 `_caption_of` 一处**用后者」——
    **是错的**。实际有**三处**，而且复核者是在我按这个错误说明自查完之后才找出来的：
      1. 表注词数守卫（找 `\\label{tab:runs}`）
      2. `_caption_of`（找 `\\label{fig:...}`）
      3. 表 I 逐行对拍的**切片定位**（找 `\\label{tab:runs}` 到 `\\end{table}`）
    第 3 处是我漏的，它当时**已经静默退化**（切片失败 → 退回整份 `sec_results.tex`），
    只是恰好还是 28 行、没报错。
    ⇒ **判据：凡按 `\\label{}`（或任何被 `strip_cites` 剥掉的命令）定位的，一律读这一份。**
    查漏的办法：`grep -n 'find(r"\\\\label' ` + 全文扫 `P[` 的结构锚点 ——
    但**别只信 grep**（本次就是 grep 漏了 `.find` 的另一种写法）。
    """
    return {os.path.basename(f): strip_comments(
        open(f, encoding="utf-8").read()) for f in TEX}


# ---- supplement 的 .md 源 ----------------------------------------------------
# **只按文件名显式取用**（`ck(..., where="supplement_table1.md")`），绝不并进 `alltext`。
# 为什么不能并进去：这些文件里**逐字保存着已经从正文移出的句子与整张表**，
# 并进 alltext 等于让每一条守卫都能在「副本」里命中 —— 全稿的检查强度会一起塌掉。
# 2026-09-27 那批 MISS 里有一整类正是「值已移进 supplement」（表 I 移出的 8 行、
# 表 II 的整张表）；处置是让**那几条**守卫指向副本，不是让副本去喂所有检查。
SUPP = {os.path.basename(f): strip_comments(open(f, encoding="utf-8").read())
        for f in glob.glob(os.path.join(ROOT, "paper", "supplement_*.md"))}


def _norm_label(s):
    """表里那一行的标签归一化 —— 剥掉 `$^\\ddagger$` / `$^{\\ddagger\\S}$` 这类标记。

    ⚠ 两边的 key 都要做**同一次**归一化：生成器输出的 label 带 `$^\\ddagger$`
    （它按 concurrency.csv 的 CONTESTED 打标），而正文的也带 —— 只对一边 sub
    就会得到「表 I 缺生成器里的行」这种**假 MISS**（2026-09-25 加这条时踩到）。
    ⚠ 要能剥掉**一个以上的标记**：`AIMD, paper params$^{\\ddagger\\S}$`
    同时带争用旗（‡）与「墙钟不可用」（§）。原来的 `\\w+` 只认单个命令，
    于是那行被当成「表 I 缺生成器里的行」（2026-09-26 加 § 时踩到）。
    """
    return re.sub(r"\$\^\{?[^{}$]*\}?\$", "", s).strip()


# 表里的一行：标签 & wall & conc & slo & 其余（Δ 或 \emph{anchor}）
# ⚠ `&` 两侧必须是 `\s+`，不能写死一个空格：表里的列是**对齐过的**，
# `&  9.5` 中间可能有两个空格（2026-09-25：`cap8+HC` 那行就是这么漏解析的，
# 报成「表 I 缺生成器里的行」）。
_ROWRE = re.compile(r"\s+(\S.*?)\s+&\s+([\d.]+)\s+&\s+([\d.]+)\s+&\s+([\d.]+)\s+&.*?\\\\$")


def _table_rows(src):
    """从一段 LaTeX 里解析出「标签 -> (wall, slo)」的表行。

    ⚠ **只有这一份实现**：它同时喂「论文表 I 逐行对拍」「表 I 的三连/Δ」
    「supplement 完整表」三类检查。两份实现分叉过一次（2026-09-26：
    有人拿 `table1.csv` 当「表 I」的分母算，原文其实是对的）。
    """
    out = {}
    for _l in src.split("\n"):
        _m = _ROWRE.match(_l)
        if _m:
            out[_norm_label(_m.group(1))] = (_m.group(2), _m.group(4))
    return out


# ⚠⚠ supplement 的 .md **不能整份当表读**：那些文档里同一行数据常常出现**两次**
# —— 前面一张 markdown 摘要表（`| cap2 | \`pois200_cap2\` | 304.2 | … | −2.23 |`）
# 与后面逐字保留的 LaTeX 表。整份当源时 `ck_near` 的窗口会命中**摘要表**里那一份，
# 于是「把 LaTeX 表里的 Δ 改坏」**照样通过**（2026-09-27 反向测试 A2 实测，
# 而那条检查正是把 8 行改锚到 supplement 之后新上的）。
# ⇒ 只切出**真的印成表行**的那一块（判据与 `_table_rows` 共用 `_ROWRE`，
# 不是另写一份正则）。表行的「印出来」在这里就是「这一行以 `\\` 结尾、含四个列」。
SUPP_TABLES = {_n: "\n".join(_l for _l in _s.split("\n") if _ROWRE.match(_l))
               for _n, _s in SUPP.items()}


def _import_gen_table():
    """把 `gen_table.py` 作为**唯一**的「论文表 I 印哪几行」来源 import 进来。

    为什么必须 import：`PAPER_OMIT` 是生成器与 LaTeX 的对齐名单，而本脚本也要用它
    决定每条行守卫读哪个文件（论文的 `sec_results.tex`，还是 supplement 的完整表）。
    各写一份 = 又一次「两份实现」，而这一处**刚刚分叉过**：2026-09-27 的 26 条 MISS
    里有 9 条来自「生成器印 35 行、LaTeX 印 27 行」。
    """
    import importlib.util as _ilu
    _fp = os.path.join(ROOT, "scripts", "lab", "gen_table.py")
    _spec = _ilu.spec_from_file_location("_gen_table", _fp)
    _m = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    return _m


# 数词表（1..10）：**模块级**，不许定义在条件分支里 —— 它在三处被用，其中两处
# 在定义它的 `if "pois200_foyer_hc" in gah:` **之外**。那一行缺失时原来会
# `UnboundLocalError` 直接崩，而崩溃的输出里没有 MISS，看起来像"全过"（codex r46 的构造）。
_NUM9 = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
         7: "seven", 8: "eight", 9: "nine", 10: "ten"}
_WORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
         8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
         14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
         19: "nineteen", 20: "twenty", 21: "twenty-one", 22: "twenty-two",
         23: "twenty-three", 24: "twenty-four", 25: "twenty-five", 26: "twenty-six",
         27: "twenty-seven", 28: "twenty-eight", 29: "twenty-nine", 30: "thirty",
         # 2026-09-25 扩到 60：`gate_attrib` 的集合规模（§V 写 "forty-five of them"）
         # 就是这一类**会随实验增长**的条数。表只到 30 时 `num_words(45)` 返回
         # **空列表**，检查静默变成「什么都不查」—— 正是本项目记过的那个坏法。
         31: "thirty-one", 32: "thirty-two", 33: "thirty-three", 34: "thirty-four",
         35: "thirty-five", 36: "thirty-six", 37: "thirty-seven", 38: "thirty-eight",
         39: "thirty-nine", 40: "forty", 41: "forty-one", 42: "forty-two",
         43: "forty-three", 44: "forty-four", 45: "forty-five", 46: "forty-six",
         47: "forty-seven", 48: "forty-eight", 49: "forty-nine", 50: "fifty",
         51: "fifty-one", 52: "fifty-two", 53: "fifty-three", 54: "fifty-four",
         55: "fifty-five", 56: "fifty-six", 57: "fifty-seven", 58: "fifty-eight",
         59: "fifty-nine", 60: "sixty"}


def num_words(n):
    """整数 -> 英文词（正文里名次、条数常用词写：eighteenth / twenty-eight / nineteen）。

    2026-09-25 加派生量检查时踩到：查 `18` 却写作 `eighteenth`，四条新检查里三条
    是这么假 MISS 掉的。名次还要 +th 形式。
    """
    try:
        n = int(n)
    except (TypeError, ValueError):
        return []
    out = []
    if n in _WORD:
        w = _WORD[n]
        out.append(w)
        # 序数词：eighteen -> eighteenth（twenty-one -> twenty-first 也补上）
        # 个位序数词是不规则的 —— 机械 +th 会得到 oneth/twoth/threeth/fiveth/
        # eightth/nineth/twelfth，正文里永远不会那样写，于是**假 MISS**
        # （2026-09-25 独立审查发现的洞；当时用的 45/5/4/7/20 恰好都没踩到）。
        _IRR = {1: "first", 2: "second", 3: "third", 5: "fifth", 8: "eighth",
                9: "ninth", 12: "twelfth"}
        if "-" in w:
            # 复合词（twenty-eight -> twenty-eighth）：序数只落在后一半上。
            # **必须先判这一支**：机械对整词加后缀会得到 `twenty-eightth`、
            # `forty-fiveth`、`twenty-oneth` 这种正文里永远不会出现的串。
            # 它们不会造成假通过（那个串哪都不在），但那是**一个不可能命中的
            # 候选在冒充守卫** —— 与 `num_words(45) == []` 同一类，只是更隐蔽
            # （列表非空，看着像在查）。2026-09-25 修过一次，只堵了 `else` 那支，
            # `forty-five`/`twenty-one` 从 `endswith("e")` 那支照样漏。
            a, b = w.split("-")
            b_ord = {"one": "first", "two": "second", "three": "third", "five": "fifth",
                     "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}.get(b, b + "th")
            out.append(a + "-" + b_ord)
        elif n in _IRR:
            out.append(_IRR[n])
        elif w.endswith("y"):
            out.append(w[:-1] + "ieth")
        else:
            out.append(w + "th")
    return out


def has(text, v):
    """正文里有没有这个数。试 1~4 位小数、以及千分位两种写法。

    ⚠ **传空列表要报错，不能回 True**：`str([])` 是 `"[]"`，字面匹配会把
    正文里任何一处 `[]`（LaTeX 的可选参数）当成命中。2026-09-25 独立审查实测
    `has("XX[]YY", []) == True`。目前调用点都先经 `ck_near` 展开、且 .tex 里
    字面 `[]` 出现 0 次，所以是潜伏不是现行 —— 但潜伏的假通过迟早会现行。

    传进来的如果不是纯数字（例如「54.5 & 1.455 & 28.9」这样的多列片段），
    就按**字面子串**查 —— 多列一起查比单查一个数可靠得多，单查一个数太容易
    在别处撞车（2026-09-25 加归因表检查时加的这条通路）。"""
    if isinstance(v, (list, tuple)):
        if not v:
            raise ValueError("has() 收到空列表 —— 那会让 str([]) 去字面匹配 \"[]\"，是假通过")
        return any(has(text, x) for x in v)
    # ⚠ 2026-09-27 活性审计：`has(text, "")` **恒为 True**（空串是任何串的子串）——
    # 于是「该列缺失时 `r.get(col, "")`」这类调用会**静默通过**。这里返回 False，
    # 让缺列变成一条**看得见的 MISS**，而不是一次假通过。
    # （**不能抛异常**：本项目反复栽在「崩了看起来像 0 MISS」上。）
    if v is None or (isinstance(v, str) and not v.strip()):
        return False
    s = str(v)
    # 先说复合串（多列片段，如 "54.5 & 1.455 & 28.9"）：它 float() 一定会抛，
    # 而**原来那个 except 分支直接 return s in text 就出去了** —— 于是下面放宽
    # 空白的逻辑永远走不到（2026-09-25 加复合串检查时连踩两次）。
    # 表里的列是【对齐过的】，「91.2 &  5.1」中间可能有两个空格，必须放宽 & 两侧空白。
    if " & " in s:
        import re as _re
        # re.escape 把 " & " 转义成 "\ \&\ "（空格和 & 都被转义），按【那个】替换
        pat = _re.escape(s).replace("\\ \\&\\ ", r"\s*&\s*")
        return _re.search(pat, text) is not None
    try:
        float(s)
    except ValueError:
        # 非数字的复合串：**空白一律弹性**。LaTeX 源码会在词与词之间换行
        # （「170.5, 173.2\nand 191.5」），字面查会莫名其妙地对不上
        # （2026-09-25 改不放假窗口那三条时踩到）。
        import re as _re2
        # ⚠ **单个英文词要加词边界**。`num_words()` 返回的是词（`twenty`），
        # 传进来时不是数字、走的就是这一支；不加边界则 `"twenty"` 会被正文的
        # `twenty-three arms` 命中 —— 查「20 条」而正文写 23 条也算过
        # （codex 第 25 轮实测）。判据是「不含空格的纯字母/连字符串」，
        # 这样复合串（`54.5 & 1.455`、`no control`）仍走原来的弹性空白匹配。
        if s and " " not in s and all(ch.isalpha() or ch == "-" for ch in s):
            # ⚠ **反方向也要试**：传英文词（`num_words()` 的产物）时，正文完全可能
            # 写的是阿拉伯数字（`in 4 of the 11`）。codex 第 36 轮实测
            # `has("4 runs", "four") == False` —— 只查词形会让「正文写 4、检查传 four」
            # 变成假 MISS（本项目 2026-09-26 已经栽过一次）。
            _rev = {v: k for k, v in _WORD.items()}
            if s.lower() in _rev and re.search(
                    r"(?<![\d.])" + str(_rev[s.lower()]) + r"(?!\d)(?!\.\d)", text):
                return True
            # ⚠ **不区分大小写**：正文里的条数/名次常在句首（`Five configurations`），
            # 而 `num_words(5)` 给的是小写 `five` —— 区分大小写时必然落空。
            # 2026-09-26 实测：新加的「§IV 重复配置的组数」检查因此报**假 MISS**
            # （而正文是对的）。词边界规则不变，`twenty` 仍不会被 `twenty-three` 命中。
            return _re2.search(r"(?<![A-Za-z])" + _re2.escape(s) + r"(?![A-Za-z-])",
                               text, _re2.IGNORECASE) is not None
        return _re2.search(r"\s+".join(_re2.escape(w) for w in s.split()), text) is not None
    if "." in s:
        # ⚠ **必须加右边界**：原来是无边界子串匹配，于是 `"1.6"` 会命中正文里的
        # `"1.65"`、`"1.60"`、`"1.68"`…… 等于把 1 位精度的检查变成「只要正文里
        # 有个以 1.6 开头的数就算过」。2026-09-25 实测：把正文的 `1.65` 改成
        # `1.60`，检查**照样通过**（因为试的 `"1.6"` 是 `"1.60"` 的子串）。
        # 加 `(?![\d])` 后 `"1.6"` 不再匹配 `"1.65"`，而 `"1.65"` 仍匹配 `"1.65"`。
        # ⚠ **符号必须保留**。`float("+0.90")` 再格式化会**丢掉 + 号**：
        # `"%.1f" % 0.90` = `"0.9"`，而 `"+0.91"` 与 `"-0.90"` 都含 `"0.9"`
        # ⇒ 把正文的 `+0.90` 改成 `+0.91` 甚至 `-0.90` 检查都照样通过
        # （codex 第 25 轮实测）。**符号在这里是语义**：正负是相反的两个结论。
        # 所以传入带符号的串时，按带符号去试，不再退回不带符号的写法。
        # 而且正文的符号常写成 **LaTeX 数学模式**：`$-2.3$`、`$+0.6$`。
        # 保留符号之后这些会变成**假 MISS**（2026-09-25 全量重跑立刻暴露 3 条，
        # 而那三处正文其实是对的）。所以符号位置要同时认
        # `-` / `$-$` / Unicode U+2212 三种写法。
        # ⚠⚠ 2026-09-26：**左边界**。小数这一支一直只有右边界，
        # 于是 `has("1.137")` 先退化成 `"1.1"`，而它会命中正文里的 `21.1`
        # —— **假通过**。是中立复核者全量核退役名单时抓到的。
        # 与整数那一支的 `(?<![\d.])` 是同一条规矩：**边界两侧要一起写**。
        _sg = s[0] if s[:1] in "+-" else ""
        for d in (1, 2, 3, 4):
            _body = re.escape("%.*f" % (d, abs(float(s)))) + r"(?![\d])"
            if _sg == "-":
                # 正文的负号有三种写法：`-2.3`、`$-$2.3`、**`$-2.3$`**（最后这种
                # 是 A100 的 ε 表用的，2026-09-25 漏认它导致 8 条假 MISS）。
                _pat = r"(?<![\d.])" + r"(?:\$-\$|\$-|[-\u2212])" + _body
            elif _sg == "+":
                _pat = r"(?<![\d.])" + r"(?:\$\+\$|\$\+|[+])" + _body
            else:
                # 不带符号的查询：允许正文写成带符号（宽松；符号由调用方决定要不要查）
                _pat = r"(?<![\d.])" + r"[-+\u2212]?" + _body
            if re.search(_pat, text):
                return True
        return False
    n = int(float(s))
    # ⚠ **整数不能做无边界子串查**。codex 第 36 轮实测：`has("14 runs", 4) == True`
    # —— `"4"` 是 `"14"` 的子串。于是把「4 of 11」误写成「14 of 11」，附近那条
    # 数值检查**照样通过**。小数那一支早就加了 `(?![\d])`，整数这一支一直是裸的。
    # 左侧排除数字 / 小数点 / 逗号（`{:,}` 里的 `,` 也不能当前导）。
    # ⚠ **右边界同样要有**（独立复核子 agent 第 21 轮实测：只补了左边等于没补）：
    #   `has("40 runs", 4)`、`has("6.5 ms", 6)`、`has("24.4 ms", 24)`、
    #   `has("135 of 200", 13)`、`has("25-session", 2)` 全都是 True。
    # 右侧排除数字与小数点。
    # ⚠ 左边界从 `[\d.,]` 放宽到 `[\d.]`：排掉逗号会让 `{2,3,4}` 这种**逗号相邻**
    #   的整数**假 MISS**（正文里就有 `$\{2,3,4\}$` 与 `$\{0,1,2,3\}$`）。
    #   放宽之后 `1,432` 里的 `4` 会不会被 `has(...,4)` 认下？不会 ——
    #   它右边是 `3`（数字），**被右边界挡住了**。
    _forms = [str(n), "{:,}".format(n), "{:,}".format(n).replace(",", "{,}")]
    if any(re.search(r"(?<![\d.])" + re.escape(f) + r"(?!\d)(?!\.\d)", text) for f in _forms):
        return True
    # 也试英文词形（名次/条数正文常写词）。
    # ⚠ **必须加词边界**：`"twenty" in text` 会被 `twenty-three` 命中 ——
    # 于是查「20 条」时正文写着 `twenty-three arms` 也算过（codex 第 25 轮实测）。
    # ⚠ **边界必须不对称**：右侧要排除连字符（`twenty-three` 里的 `twenty`
    # 右边是 `-`，不算命中），左侧**不能**排除 —— LaTeX 的破折号是 `---`，
    # `file---forty-five` 里的 `forty-five` 左边就是 `-`，左边界一排就全成
    # 假 MISS（2026-09-25 实测踩到）。
    # ⚠ **词形匹配要不区分大小写**：正文里的条数常在句首，写成 `Five configurations`
    # 而 `num_words(5)` 给的是 `five` —— 区分大小写时必然落空（2026-09-26 实测：
    # 新加的「§IV 重复配置的组数」检查因此报假 MISS，而正文是对的）。
    # 词边界规则不变（右侧排除连字符、左侧不排除），所以 `twenty` 仍不会被
    # `twenty-three` 命中。
    return any(re.search(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z-])", text,
                         re.IGNORECASE)
               for w in num_words(n))



def _import_running_all(run):
    """从 metrics.csv 现算 sglang:num_running_reqs 的全时段均值 —— 与
    gen_arm_running.py 的 running_all 同一个量（那边也从同一个列算）。"""
    p = os.path.join(ROOT, "results/night", run, "metrics.csv")
    v = [float(x["sglang:num_running_reqs"]) for x in csv.DictReader(open(p))
         if x.get("sglang:num_running_reqs")]
    return sum(v) / len(v)


AUDIT = []


def _audit(desc, val, src):
    """记录每个被检查的值在【它被检查的那段正文】里出现多少次。

    为什么：`ck` 是字符串级的，一个值出现 20 次和出现 1 次，检查强度完全不同 ——
    出现次数越多，越可能是在别处撞上的（2026-09-25 的「假通过」就是这么来的：
    §III 的 39.3 变成 39.2 之后检查器仍通过，因为 39.2 在别处出现过）。
    这次审计只把弱的检查**列出来供人看**，不自动判它们错。
    """
    try:
        AUDIT.append((str(src).count(str(val)), desc, str(val)))
    except Exception:
        pass


def main():
    # `gen_gate_attrib.load` 是闸门周期日志的**唯一解析口径** —— 下面核
    # 「正文里三条具名闸门臂的百分比」时用它，而不是自己再写一遍解析。
    sys.path.insert(0, os.path.join(ROOT, "scripts", "lab"))
    import gen_gate_attrib as _gag
    _gag_load = _gag.load

    P = paper_text()
    # ⚠ 2026-09-27（r57 codex 复核 3）：这一行原来写着「只给 `_caption_of` 定位用」——
    # 与上面 docstring 同一条错话（已改）。**实际是三处**：表注词数守卫、
    # `_caption_of`、以及表 I 逐行对拍的切片定位。**改 docstring 时要连行内注释一起改**
    # （这次就是只改了 docstring、漏了这里，被复核者抓到）。
    # supplement 的文本源（**独立于 `P`**，理由见 `_src_of`）。惰性读，文件不在就是空串。
    _SUP_SRC = [""]
    _sp = os.path.join(ROOT, "paper", "supplement.tex")
    if os.path.exists(_sp):
        _SUP_SRC[0] = strip_cites(strip_comments(open(_sp, encoding="utf-8").read()))
    _EMPTY_SRC = []          # 取到空源的 where（见 _src_of 的长注释）
    _PSTRUCT = paper_text_struct()
    alltext = "\n".join(P.values())
    fails, secondary, checks = [], [], 0

    def _src_of(where):
        """`ck` / `ck_near` 的取值源：正文 .tex 优先，其次 supplement 的 .md，最后全稿。

        `where` 是文件名。**含 .md 的那些是显式点名**（表 I 移出的 8 行、表 II）——
        它们的值现在只印在 supplement 里，所以守卫也必须读那里。
        ⚠ supplement 的 .md **只读它的表行那一块**（`SUPP_TABLES`，理由见那里的注释：
        整份读会让窗口命中同一份数据的**另一个副本**，反向测试 A2 抓到过）。
        没写 `where` 的照旧读 `alltext`（仍只含 .tex，见 `SUPP` 的注释）。
        """
        if not where:
            return alltext
        # ⚠⚠ 2026-09-27：`supplement.tex` **不在 `P` 里**（它被显式排除出 `TEX`，
        # 否则它会以「同一批数字的副本」塌掉全稿的检查强度）。于是守卫写
        # `ck_near(..., "supplement.tex", ...)` 会读到**空串**、恒 MISS ——
        # 我第一版就这么写的，五条全 MISS。
        # ⇒ supplement 有**它自己的源**（同一套剥注释/剥命令的处理），单独喂。
        if where == "supplement.tex":
            _v = _SUP_SRC[0]
        else:
            _v = P.get(where) or SUPP_TABLES.get(where) or SUPP.get(where) or ""
        # ⚠⚠⚠ 2026-09-27：**判据读到空源 = 那条检查是个空转。**
        # 我在这个项目里因为这件事栽过**两次**：
        #   · `where="frontier_split.csv"` —— `_src_of` 只认 .tex/.md，`.csv` 落到空串；
        #   · `where="supplement.tex"` —— supplement 被显式排除出 `TEX`，同样落到空串。
        # 两次形状一样：`has("", v)` 恒 False ⇒ 恒走 secondary ⇒ **印成 `..`、不计入退出码**。
        # ⇒ 记下来，末尾**硬报**。判据读不到东西时，唯一正确的行为是**响**。
        if not _v and where:
            _EMPTY_SRC.append(where)
        return _v

    # ---------------------------------------------------------------- 退役名单
    # 2026-09-26：篇幅大手术（30 页 → 20 页）砍掉了大量**细节数字**，
    # 而盯它们的检查还在。处置只有两条路：**把数加回正文**，或**显式退役该条**。
    # 这里走后者，并且**写成名单而不是删代码** —— 理由是：
    #   (1) 退役是一个**决定**，决定要留痕、要能一条命令撤回；
    #   (2) 删掉检查会让它在报告里彻底消失，下一个人不知道这里曾经盯过什么。
    # 判据（每条退役都必须是这三类之一）：
    #   R1 值仍在论文里（被压缩挪到别处或换了措辞）→ 用 `R1:` 注明现在在哪；
    #   R2 值已被砍，但它支撑的论断由**别处的数**承担 → 用 `R2:` 注明是谁承担；
    #   R3 值已被砍、且该论断也随之收窄或删除 → 用 `R3:` 注明。
    # ⚠ **头牌数字与限定句的检查不在可退役之列**：那些要么恢复，要么改口径重锚。
    RETIRED = {
        # ⚠ 2026-09-27（落地）：§I 那句在头条从「unresolved」升级为「crossing」时
        # **整句重写** —— 它原来用「比同配置重复的散布还小」论证「不叫它越线」，
        # 而越线现在已由第二次读数确认，那个论证不再需要，句子连同 0.5/4.6 一起消失。
        # ⇒ **诚实退役**：锚 `repeats of a single` 在 §I 里确实没有了。
        # ⚠ 量本身**仍在 §V 与 §VI**（那两处的守卫还活着，且用修正后的基准）。
        "§I 控制器重复 Δ 全距下界": "R3: §I 那句随头条升级重写，已不再引这个量；§V/§VI 两处仍有活守卫",
        "§I 控制器重复 Δ 全距上界": "R3: 同上",
        # R2：分段斜率串，源在 elasticity.csv / elasticity_hc.csv；
        # 正文只保留拟合 ε 与两端的段值（+0.19/+0.46/+1.15/+1.14 等）。
        # R2：逐桶 τ₂ 读数，§VII 的共同租户审计已压成「四条臂移动 4.5--11.2pp」；
        # 逐桶值在 paper/data/concurrency.csv。
        # R3：A100 的 ε 分段区间表在合并两节时删除（codex 的取舍方案点了它）；
        # ε 的值仍在正文。
        # R3：图 2 图注重写为「画 17 条臂、范围对 39 条算」后不再印名次。
        # ⚠⚠ 2026-09-27（r51 双审查 C2）：这个键原来写的是**前缀** `图2 图注：*`，
        # 而退役理由说的是「不再印**名次**」—— 那条理由**对条数不适用**：
        # 前缀键同时吞掉了 `图2 图注：run 的条数`（`:1473`），而图注**确实印着**
        # 条数（「computed over all thirty-nine runs」）。于是那条守卫被静默关掉，
        # 图注里的 `thirty-seven` 与真值（`decomp.csv` 39 行）差了 2 而没有东西报。
        # 现在改成**逐条点名四条名次检查** —— 前缀键只留在真正成族的地方。
        "图2 图注：default 的 idle 名次": "R3: 图注重写后不再印名次（画的是 17 条臂）",
        "图2 图注：default 的墙钟名次": "R3: 同上（图注不印名次）",
        "图2 图注：no-control 的 idle 升序名次": "R3: 同上（图注不印 no-control 的名次）",
        "图2 图注：no-control 的 duration 名次": "R3: 同上（图注不印 no-control 的名次）",
        # R3（2026-09-26 篇幅手术）：图 3 整张删掉了（codex 的取舍方案：两法定义与
        # 少量对照数写正文即可）。**值现在在哪**：8.4--39.7% 与 66.3% 仍在 §III 正文
        # 「absolute terms / we exclude」那两句里，由「§III τ₁−τ₂ 上界/下界」
        # 与「§III excess_pct 上界」等六条守卫盯着 —— 退役的是**图注那一份副本**，
        # 不是那个主张。
        "图 3 图注的 excess 区间（33 条）": "R3: 图 3 已删；值在 §III 正文与 decomp.csv",
        "图 3 图注里被排除那条的 excess": "R3: 图 3 已删；66.3% 仍在 §III 正文",
        # ---- 2026-09-26 篇幅手术第二批（§III/§V 压缩）----
        # 判据不变：**值现在在哪**，不是「值没了」。
        # 旧判据的读数（173.2/195.0/240.1、foyfix 九段 12%）随**那条主张本身**一并撤回
        # ——正文保留了「stall.csv 把两套判据的计数并列」这一句，两个数在
        # `stall.csv` 的 `n_windows_valve_holding` 与 `old_pct_span` 列里。
        "§V 旧判据下三条单段臂的时长（升序拼接）":
            "R3: 该主张已撤回；旧读数在 stall.csv 的 old_pct_span",
        # ⚠ 2026-09-26 中立复核第 43 轮：这条的理由写错了档 —— 该值（four）**仍在
        # 正文**（§VII 撤回项「the ``windows'' we reported in four arms were the
        # valve doing its job」），是**纠正后重新报告**，不是撤回 ⇒ 按本项目口径是
        # **R1（值在正文别处）**，不是 R3。同一组另外三条（173.2/195.0/240.1、nine、
        # 12%）确实只在 stall.csv 的 old_total_s / n_windows_valve_holding /
        # old_pct_span 里，R3 成立。
        "§V 旧判据下出现段的臂数": "R3: 该句随压缩删除；§VII 的撤回项只保留定性说法（those windows were the valve doing its job），四个读数在 paper/data/stall.csv 的 n_windows_valve_holding 列",
        "§V 旧判据下关掉全部节流那条的段数":
            "R3: 同上",
        "§V 旧判据下那条臂的段占墙钟":
            "R3: 同上（old_pct_span）",
        # 跨 trace 的投影区间：正文只保留 main trace 的 1.32--1.96（上中位 1.67），
        # 全列（含 main_plus_second_trace_arm / all_rows 两组）在 projection.csv。
        "§V projection main_plus_second_trace_arm 的中位":
            "R3: 正文只印 main trace 区间；全列在 projection.csv",
        "§V projection main_plus_second_trace_arm 的上界":
            "R3: 同上",
        "§V projection all_rows 的中位":
            "R3: 同上",
        "§V projection all_rows 的上界":
            "R3: 同上",
        # 半池的两个比值：随半池段压缩删除，正文只留「999 步里 104 步退化、四分之三池 14 步」。
        # 两列仍在 pool50.csv（gap_pct_of_bound / gap_pct_of_prefix）。
        "§III cap2_hp 的 gap_pct_of_bound": "R3: 半池段随压缩删除（正文也不再印退化步数 104/14，见本批新增的两条同名退役）；两个比值在 paper/data/pool50.csv 的 gap_pct_of_bound 列",
        "§III cap2_hp 的 gap_pct_of_prefix": "R3: 同上；该比值在 paper/data/pool50.csv 的 gap_pct_of_prefix 列",
        # FIFO 指纹段删除：事实（只看队首）改由 §VII 的源码 diff 支撑
        # （`waiting[:1]`，22 行、两处），指纹本身仍由 gen_stall 的断言守着。
        "§V 严格按到达顺序放行的臂数":
            "R3: 指纹段删除；该事实由 §VII 的源码 diff 支撑，指纹在 gen_stall 的断言里",
        "§V 每臂的放行次数":
            "R3: 同上（stall.csv 的 admits 列）",
        "§V 两个考虑整队列的臂的乱序率":
            "R3: 同上（stall.csv 的 fifo_pct 列）",
        # R2：round-1+ 命中率在 hitrate.csv；正文引的是另一口径。
        # ⚠ 2026-09-27 活性审计：这一条原来写作 `"round-1+ *"`（前缀），**吞掉了整族 32 条**，
        # 而其中 **28 条的值其实在正文里**（`NORE=1` 实测只有 4 条报 MISS）——
        # 也就是说 28 条活主张的守卫**死了但账上看不出来**。
        # 现在只退役**真的不在正文**的那 4 条（设备侧 per-cap 值；正文只印区间）。
        "round-1+ pois200_cap2": "R2: 正文只印设备侧的区间（80.8--32.8），per-cap 值不印",
        "round-1+ pois200_cap3_fixed": "R2: 同上",
        "round-1+ pois200_cap4": "R2: 同上",
        "round-1+ pois200_cap3_hc": "R2: 同上（host 侧只印 80.7--78.7）",
        # R2：host-tier 条数在 §IV 仍在（「Across the twenty-four host-tier runs」），
        # §I/§VII 的重复句被压缩掉。
        # ⚠ 2026-09-27：这里原来是前缀键 `"host-tier run 条数（§I*"` —— 而 `§I` 正好是
        # **`§III` 的前缀**，于是它把 `host-tier run 条数（§III）` 那条**活守卫也吞了**
        # （实测：`!! 退役未生效` 报出它，值一直在正文里）。改成两条精确键。
        # 这是本项目「前缀键会静默吞掉同族检查」的又一次，而这次的形状更隐蔽：
        # **不是同一个词的后缀歧义，而是 `§I` 与 `§III` 的罗马数字前缀重合。**
        "host-tier run 条数（§I 低端那句）": "R2: §IV 仍印该条数，§I 的重复句已压掉",
        "host-tier run 条数（§I 关联那句）": "R2: §IV 仍印该条数，§I 的重复句已压掉",
        "§Discussion 的 host-tier 条数": "R2: 同上",
        "§Discussion 的静态 host-tier 下界": "R2: 值在 §IV/§II，§VII 的重复句已压掉",
        # R3：§III 这句改为「中位数不稳所以不当中位报」，不再印那个中位。
        # ⚠ 2026-09-27 独立复核抓到：这一条的退役理由**不实** ——
        # 它写「该句改为说明为何不报中位，数字随之删除」，而正文
        # `sec_model.tex` 至今仍印着「it reads 10.0\,s without \texttt{cap1} and 5.0\,s
        # with it」。而且它的锚 `median is not robust` 在正文里**根本不存在**
        # （正文写的是 `which is not robust to`）⇒ 即便取消退役也会报假 MISS。
        # **一个仍然成立、仍然印在正文里的数，守卫却是死的** —— 这正是
        # 「批量退役＝把守卫关掉」的现存实例。已撤销退役并把锚改成真短语。
        # 分段区间表已删（ε 值仍在正文）；**末段单独守**，见 check 处的注释。
        "§A100 ε *": "R3: 分段区间表已删，ε 值仍在正文；末段（承载小分母限定）单独守",
        # ⚠ 2026-09-26：这五条是**补上小数分支的左边界之后**才现形的 ——
        # 在此之前它们靠「子串假通过」印 OK（`has(7.4)` 命中的是正文里的 `27.4\,ms`）。
        # 按本项目规矩：**加完边界立刻全量重跑，冒出来的 MISS 不是回归，是暴露了假通过**。
        # 逐条核过：**它们各自支撑的那个论断**在压缩后被删或收窄了。
        # ⚠ 措辞不要说成「值全稿不存在」——codex 第 41 轮指出 `0.6` 与 `7.1` 仍出现在
        # 别的论断与 25 档表里；判据是「**它支撑的那句话**还在不在」，不是「这个数在不在稿里」。
        "第二条 trace 重复对的兑现散布": "R3: 第二条 trace 的重复对散布随压缩删除（repeat_spread.csv 仍在）",
        "realhr foyer 重复对墙钟散布": "R3: 同上",
        "replicates 墙钟散布上界": "R2: 正文改引 SLO 散布（0.3--5.1pp，sec_results.tex「spreads spanning」那句）而非墙钟散布",
        # ⚠⚠ 2026-09-27（r53 复核 F1）：**下界这一条此前没有退役键** —— 于是一直靠
        # 「撞上」活着：它的值是 `replicates.csv` 的 `wall_range_pct` 最小值（0.05 →
        # 印成 `0.1`），而 `sec_xtrace.tex` 里恰好有一个**无关的** `0.1\,pp`
        # （cap sixteen 距控制器 SLO 的距离）。**「在」不等于「是这个量」**：
        # 这条检查与它盯的墙钟散布毫无关系，值下一次偏一点就会报**假 MISS**、
        # 把人骗去改一个**对的**生成器。退役理由与上界同源（正文改引 SLO 散布）。
        # ⚠ 那串 `0.1` 仍在正文 ⇒ 退役会触发 `!! 退役未生效`，而那是**撞车**不是
        # 空文 —— 见 `STR_ELSEWHERE`（那里逐条写明「串属于哪个量」）。
        "replicates 墙钟散布下界": "R2: 与上界同源 —— 正文不引重复对的**墙钟**散布（改引 SLO 散布 0.5--5.1pp，sec_results.tex「spreads spanning」那句）；值（min）在 paper/data/replicates.csv 的 wall_range_pct 列（=0.05，印成 0.1）。⚠ 正文里的 `0.1` 属于另一个量 ⇒ 见 STR_ELSEWHERE",
        # ⚠ 2026-09-27：`"idle all_runs median_s"` 那条**已删** —— 它是**孤儿**
        # （没有任何检查用那个描述）且**理由不实**（正文至今印着 5.0\,s）。
        # 改成 §III 里的一条活守卫，见 "(3) 正文引、但此前没有检查守的几个数"。
        "§III cap4_hc 的空转%": "R3: 逐臂空转表随压缩删除（正文现在只印 idle 的区间 6.3--41.9% 与 pooling 的区间，不逐臂印）；值在 paper/data/decomp.csv 的 idle_pct 列",
        # ⚠ 2026-09-27（r53 复核 F3）：`"§Discussion round-1+ cap6_hc"` 这一条**已删** ——
        # 它是**孤儿键**：描述串在全文件里只出现在名单里（检查器里造这个 desc 的只有
        # `round-1+ %s`（hitrate.csv）与 `§IV round-1+ %s` 两条通路，**都造不出 `§Discussion …`**）；
        # 而且它还是 `tier="S"` 那一支的**死条目**（S 档先返回，走不到 `_retired()`）。
        # 判据是机械的：见文件末尾的「孤儿退役键」一节（base 运行里没被咨询到的键）。
        # 值（cap6_hc 的 round-1+ 命中率 80.87）在 paper/data/hitrate.csv，正文不引这一列。
        "host-tier 动态下界 sec_intro.tex": "R2: 该值在 §IV 与 §III 仍在；§I/§VI/§VII 的重复句被压缩掉",
        "host-tier 动态下界 sec_discussion.tex": "R2: §IV 与 §III 仍在（那两处有活守卫）；§I/§VI/§VII 的重复句已压缩掉——**这三条的锚在正文里确实没了**，是诚实退役",
        "host-tier 动态下界 sec_xtrace.tex": "R2: §IV 与 §III 仍在（那两处有活守卫）；§I/§VI/§VII 的重复句已压缩掉——**这三条的锚在正文里确实没了**，是诚实退役",
        # ⚠ 2026-09-27（中立复核 r50 A 组 C1）：这七条原来**共用一句**「值在
        # paper/data/a100.csv 与 paper/data/a100_baseline.csv」——逐条核下来
        # **只有三条成立**：`a100_cap16` 的 Occ. 与 cap 三·四的墙钟在 a100.csv 里。
        # 峰值会话数与准入等待上界**只**在 `a100_delta.csv`（a100_baseline.csv 根本没有
        # 这两列）；本 tier 的 τ₂ 上界是**派生量**（七条 `a100_*` 的 `tau2_ms` 最大值）；
        # 前七个十分位的最大差**任何 CSV 里都没有**（从两条 run 的 `steps.jsonl` 现算）。
        # 「一个说法在七处共用」正是本项目「同一主张会在多处重复」那一族的镜像。
        "§A100 峰值会话数": "R2: 逐项读数被压缩删去（披露句仍在）；值在 paper/data/a100_delta.csv 的 active_max 列（=14），a100_baseline.csv **没有**这一列",
        "§A100 准入等待上界": "R2: 逐项读数被压缩删去（披露句仍在）；值在 paper/data/a100_delta.csv 的 admit_wait_max_ms 列（=51694.1），a100_baseline.csv **没有**这一列",
        # ⚠ 2026-09-27（r53 复核 F3）：`"§A100 本 tier 的 τ₂ 上界"` 这一条**已删** ——
        # **孤儿键**：没有任何检查用这个描述（`§A100 %s 的 %s` 那条通路造出的名字是
        # 别的），所以它一次也不会被咨询。它的**值也确实不在正文**（`grep 21.4` 在
        # paper/*.tex 里 0 命中）⇒ 这一条既没有守卫可退、也没有主张要守，是纯死条目。
        # （值本身：七条 `a100_*` 静态 run 的 `tau2_ms` 最大值 = 21.4，在 paper/data/a100.csv）
        "§A100 cap 三 的墙钟（单调下降那串）": "R2: 逐项读数被压缩删去（披露句仍在）；值在 paper/data/a100.csv 的 wall_min 列（a100_cap3 = 136.5），这条本来就只在这张表里",
        "§A100 cap 四 的墙钟（单调下降那串）": "R2: 逐项读数被压缩删去（披露句仍在）；值在 paper/data/a100.csv 的 wall_min 列（a100_cap4 = 110.7），这条本来就只在这张表里",
        "§III cap3_hp 的 attempted_steps": "R3: 半池与四分之三池实验的逐项读数在 pool50.csv；正文只报长度边界结论",
        "§III cap3_hp 的 degenerate_steps＋error_steps": "R3: 半池与四分之三池实验的逐项读数在 pool50.csv；正文只报长度边界结论",
        "§III cap3_hp 的 error_under_pool": "R3: 半池与四分之三池实验的逐项读数在 pool50.csv；正文只报长度边界结论",
        "§III cap4_hp 的 attempted_steps": "R3: 半池与四分之三池实验的逐项读数在 pool50.csv；正文只报长度边界结论",
        "§III cap4_hp 的 degenerate_steps＋error_steps": "R3: 半池与四分之三池实验的逐项读数在 pool50.csv；正文只报长度边界结论",
        "§III cap3_p75 的 min_over_pool_tok": "R3: 半池与四分之三池实验的逐项读数在 pool50.csv；正文只报长度边界结论",
        "§III cap3_p75 的 max_served_tok": "R3: 半池与四分之三池实验的逐项读数在 pool50.csv；正文只报长度边界结论",
        "§repro cap1_r2 的墙钟": "R2: 共同租户审计压成「四条臂移动 4.5--11.2pp、都没越线」；逐桶读数在 concurrency.csv",
        "§repro cap1 的墙钟": "R2: 共同租户审计压成「四条臂移动 4.5--11.2pp、都没越线」；逐桶读数在 concurrency.csv",
        "§repro cap1_r2 快多少": "R2: 共同租户审计压成「四条臂移动 4.5--11.2pp、都没越线」；逐桶读数在 concurrency.csv",
        "§repro 重复散布下界": "R2: 共同租户审计压成「四条臂移动 4.5--11.2pp、都没越线」；逐桶读数在 concurrency.csv",
        "§repro 重复散布上界": "R2: 共同租户审计压成「四条臂移动 4.5--11.2pp、都没越线」；逐桶读数在 concurrency.csv",
        "§VI foyer_breshz1_r2 的 ready 位移": "R3: ready-clock 与阈值敏感性的逐条读数在 arrival_slo.csv / slo_sensitivity.csv；正文留方向与条数",
        "§VI foyfix_hc 的 ready 位移": "R3: ready-clock 与阈值敏感性的逐条读数在 arrival_slo.csv / slo_sensitivity.csv；正文留方向与条数",
        "§VI aimd2 的 ready 位移": "R3: ready-clock 与阈值敏感性的逐条读数在 arrival_slo.csv / slo_sensitivity.csv；正文留方向与条数",
        "§III host-tier 的 τ₁ 上界": "R2: τ₁ 区间在 §IV 仍在（27.0--36.7），此处为重复句",
        "§III cap3_hc_r2 占用均值": "R2: 值在 occupancy.csv / reuse.csv，正文不逐臂印",
        "§III cap3_hc_r2 兑现": "R2: 值在 occupancy.csv / reuse.csv，正文不逐臂印",
        # ⚠ 2026-09-27 删退役键（`!! 退役未生效`：# 值仍在正文 ⇒ 按本项目规矩「写不出『值现在在哪』的默认按该恢复处理」，让守卫复活。
        "§VII pois200_foyer_push_25 队列中位（运行窗口）": "R3: backlog 时序细账与 queue push 逐档读数随压缩删除（backlog.csv 仍在）",
        # ⚠ 2026-09-27：这一条与上面那条是**同一族**，却一直没进退役名单 ——
        # 而它常年「通过」是因为 `ck(..., "24")` 撞上了同文件里的 `twenty-four`
        # （§III 的 host-tier 条数）。我把 `twenty-four` 改成 `twenty-six` 之后它
        # 第一次真的报 MISS，才露出「正文里那句读数早就随压缩删了」。
        # **一条常年通过的检查，先想想它是不是在别处撞上的。**
        "§VII pois200_foyer_push_25 队列最大（运行窗口）": "R3: 同上一族 —— backlog 的逐档队列读数随压缩删除（值在 backlog.csv 的 waiting_max）",
        "§VII pois200_foyer_push_25 扣住本档的比例": "R3: backlog 时序细账与 queue push 逐档读数随压缩删除（backlog.csv 仍在）",
        "toolwait foyer_hc 均值之比": "R3: 篇幅大手术删去的细节读数（见 NEXT.md 的取舍记录）",
        # ⚠ 2026-09-27（r53 复核 F3）：`"图注里的条数与该图实际画出的集合规模不符"`
        # 这一条**已删** —— 它**双重失效**：
        #   (1) 那个 desc 在检查器里唯一的用法是 `fails.append((...))`（图注条数守卫），
        #       **没有走 `_direct_fail`**，所以退役名单对它**不可能生效**（真出事会 MISS）；
        #   (2) 那条退役的理由（「篇幅大手术删去的细节读数」）**是另一件事** ——
        #       那条守卫守的是「图注里的条数 == 图实际画出的条数」，是一个**仍然成立、
        #       而且今天仍然在跑、仍然通过**的不变量（`make_figs.py` 的 `.counts.json`）。
        # **把它接上 `_direct_fail` 是错的**：那等于用一个陈旧的退役理由**关掉一条活守卫**
        # —— 正是本项目「退役 = 主动把守卫关掉」那条规矩要防的。所以删键，不接路径。
        "§A100 前七个十分位的最大差（s，向上取整）": "R2: 该句（每个完成分位都贴着）随压缩删除，`每个完成分位` 的说法也不再成立；值=4 是**派生量**，**任何 CSV 里都没有** —— 从 results/night/a100_default 与 a100_foyer_hz2 的 steps.jsonl 完成时刻分位差现算（下面那条守卫的算法就是它）",
        "图 2 图注 no-control 的空转名次": "R3: 篇幅大手术删去的细节读数（见 NEXT.md 的取舍记录）",
        "图 2 图注 no-control 的空转率": "R3: 篇幅大手术删去的细节读数（见 NEXT.md 的取舍记录）",
        "图 2 图注 no-control 的时长名次": "R3: 篇幅大手术删去的细节读数（见 NEXT.md 的取舍记录）",
        "§A100 a100_cap16 的 occ_p50_pct": "R2: 逐项读数被压缩删去（披露句仍在）；值在 paper/data/a100.csv 的 occ_p50_pct 列（a100_cap16 = 8.8）—— a100_baseline.csv **有**同名列，但它的两行读 9.5 / 95.3，**不是这个数**",
        # ⚠ 同上：§I 只有 66.1--69.5，18.9--20.6 在 **§III**（sec_model.tex 的空转段）
        # ⇒ 值在正文别处，是 R1。
        "§I 空转均值区间": "R1: 18.9--20.6 在 §III（§I 只印 66.1--69.5）",
        # ⚠ 同上：12--41% 在 **§III**（`inflates per-step cost by 12--41\%`），
        # §VI 只有定性的「co-tenancy inflates a baseline」⇒ 值在正文别处，R1。
        "§VI 膨胀区间的下界（端点互比）": "R1: 12--41% 在 §III，§VI 只给定性说法",
        "§VI 膨胀区间的上界（端点互比）": "R1: 同上",
        # ================================================================
        # 2026-09-27 篇幅手术（整块外移到 supplement）之后的退役批次
        # ================================================================
        # 判据（沿用上面的三类）：
        #   R1 值仍在论文里（换了措辞/挪到别处）；
        #   R2 值被砍，但它支撑的论断由别处的数承担；
        #   R3 值被砍，且该论断也随之收窄或删除。
        # ⚠ 每一条都写清【值现在在哪】—— 写不出的一律按「该恢复」处理，不退役。
        # ⚠ 键一律**精确匹配**（本文件 2026-09-27 的活性审计：前缀键曾静默吞掉 34 条）。
        # 生成方式：以「锚在它被检查的那个文件里还在不在」分诊（见 scripts/lab/miss_triage.py），
        # 再逐条核「它支撑的那句话还在不在」；核过的存疑项见 NEXT.md 的处置记录。
        "cap1 复用率(prompt 占比)": "R3: 正文只印设备侧的兑现区间；per-run 复用率在 paper/data/reuse.csv 的 realized_frac 列",
        "host-tier run 条数（§VI 复用区间那句）": "R2: §III/§IV 仍印该条数；§VI 的重复句随压缩删除（集合在 paper/data/reuse.csv）",
        "第二条 trace cap2 的平均占用": "R3: 逐臂占用表随压缩外移；值在 paper/data/occupancy.csv 的 occ_mean_pct 列（realhr_cap2 行）",
        "主 trace cap1 的平均占用": "R3: 同上；值在 paper/data/occupancy.csv 的 occ_mean_pct 列（cap1 行）",
        "occupancy.csv 的臂数": "R3: 该条数随压缩删除；值在 paper/data/occupancy.csv 的行数（33）",
        "gate_attrib eight_median 投影超预算": "R3: 闸门归因的逐列读数外移（supplement_material_results.md §块 6/7）；值在 paper/data/gate_attrib.csv",
        "gate_attrib all_rows_median 阀门": "R3: 闸门归因的逐列读数外移（supplement_material_results.md §块 6/7）；值在 paper/data/gate_attrib.csv",
        "gate_attrib all_rows_median 投影超预算": "R3: 闸门归因的逐列读数外移（supplement_material_results.md §块 6/7）；值在 paper/data/gate_attrib.csv",
        "§V rg2 的 round-gate 百分比": "R3: 逐臂闸门百分比随压缩删除；值在 paper/data/gate_attrib.csv 的 round_gate_pct 列",
        "§V rg3 的 round-gate 百分比": "R3: 逐臂闸门百分比随压缩删除；值在 paper/data/gate_attrib.csv 的 round_gate_pct 列",
        "§V rg4 的 round-gate 百分比": "R3: 逐臂闸门百分比随压缩删除；值在 paper/data/gate_attrib.csv 的 round_gate_pct 列",
        "§V 超预算周期数与放行数（复合句）": "R3: 该复合句随压缩删除；值在 paper/data/gate_attrib.csv 的 cycles_over_budget / admitted_while_over 列",
        "§VII 该处的 R̄_all/R̄_busy 比值": "R3: 该句随压缩删除；值在 paper/data/arm_running.csv 的 running_all / running_busy 列",
        "§VII var_cap3 的四条以上并发分钟数": "R3: 随压缩外移；值在 paper/data/concurrency.csv 的 min_at_ge4 列与 metadata 的 finished−started（见 supplement_material_discussion.md §L13）",
        "§VII var_cap3 的窗口分钟数（同一基准：metadata finished-started）": "R3: 随压缩外移；值在 paper/data/concurrency.csv 的 min_at_ge4 列与 metadata 的 finished−started（见 supplement_material_discussion.md §L13）",
        "§V 正判据下那个窗口的 waiting 中位": "R3: 窗口那段重写后正文给的是「at least 85 sessions wait」这个下界；值在 paper/data/stall.csv 的 waiting_med 列",
        "§V 那个窗口的恢复走的是饥饿逃生": "R3: 恢复机制那句随重写删除（正文改成 neither the SLO valve nor the hard stop is holding）；值在 paper/data/stall.csv",
        "round-1+ pois200_cap4_hc": "R2: round-1-and-later 命中率在 paper/data/hitrate.csv，正文只印设备侧的区间",
        "round-1+ pois200_cap5": "R2: round-1-and-later 命中率在 paper/data/hitrate.csv，正文只印设备侧的区间",
        "round-1+ pois200_foyer_bres_r2": "R2: round-1-and-later 命中率在 paper/data/hitrate.csv，正文只印设备侧的区间",
        # ⚠ 2026-09-27 删退役键（`!! 退役未生效`：# 值仍在正文 ⇒ 按本项目规矩「写不出『值现在在哪』的默认按该恢复处理」，让守卫复活。
        "round-1+ pois200_pairB_cap2hc": "R2: round-1-and-later 命中率在 paper/data/hitrate.csv，正文只印设备侧的区间",
        "round-1+ pois200_cap1": "R2: round-1-and-later 命中率在 paper/data/hitrate.csv，正文只印设备侧的区间",
        "§VII 25 档 nohw 的墙钟": "R3: 25 档的单变量分解与 backlog 细账随压缩外移；值在 paper/data/tier25_old.csv / gate_attrib.csv / projection.csv / backlog.csv",
        "§VII 25 档 t95 的墙钟": "R3: 25 档的单变量分解与 backlog 细账随压缩外移；值在 paper/data/tier25_old.csv / gate_attrib.csv / projection.csv / backlog.csv",
        "§VII 25 档 nosf 的墙钟": "R3: 25 档的单变量分解与 backlog 细账随压缩外移；值在 paper/data/tier25_old.csv / gate_attrib.csv / projection.csv / backlog.csv",
        "§VII 25 档单变量的加速比 34.8%": "R3: 25 档的单变量分解与 backlog 细账随压缩外移；值在 paper/data/tier25_old.csv / gate_attrib.csv / projection.csv / backlog.csv",
        "§VII 25 档单变量的加速比 32.0%": "R3: 25 档的单变量分解与 backlog 细账随压缩外移；值在 paper/data/tier25_old.csv / gate_attrib.csv / projection.csv / backlog.csv",
        "§VII 25 档单变量的加速比 15.2%": "R3: 25 档的单变量分解与 backlog 细账随压缩外移；值在 paper/data/tier25_old.csv / gate_attrib.csv / projection.csv / backlog.csv",
        "§VII 两根一起那条臂的加速比散布": "R3: 该散布句随压缩删除；值在 paper/data/tier25_old.csv 的 speedup_vs_base_pct 列（thr25_push 与 thr25_push_r2）",
        "cap1 前 5.5h 的桶中位下界": "R3: 共租窗口内的逐桶对照外移（supplement_material.md §S1 与 supplement_material_discussion.md §块 1）；值在 paper/data/tau2_windows.csv",
        "cap1 前 5.5h 的桶中位上界": "R3: 共租窗口内的逐桶对照外移（supplement_material.md §S1 与 supplement_material_discussion.md §块 1）；值在 paper/data/tau2_windows.csv",
        "cap1 争用后第 1 桶": "R3: 同上；值在 paper/data/tau2_windows.csv",
        "cap1 争用后第 2 桶": "R3: 同上；值在 paper/data/tau2_windows.csv",
        "cap1 争用后第 3 桶": "R3: 同上；值在 paper/data/tau2_windows.csv",
        "t85 转折前桶（第 120 分）": "R3: 同上；值在 paper/data/tau2_windows.csv",
        "§VI 移动 <=2.5pp 的臂数": "R3: ready 时钟的逐臂读数随压缩外移（supplement_material_discussion.md §块 4）；值在 paper/data/arrival_slo.csv 的 move_pp 列",
        "§VI 移动 >2.5pp 的臂数": "R3: ready 时钟的逐臂读数随压缩外移（supplement_material_discussion.md §块 4）；值在 paper/data/arrival_slo.csv 的 move_pp 列",
        "§V projection main_trace 的中位": "R3: 正文只印 main trace 区间的方向性说法；逐组列在 paper/data/projection.csv",
        "§V occupancy 的条数": "R3: 该条数随压缩删除；值在 paper/data/occupancy.csv 的行数（33）",
        "§V gate_attrib 全量集合规模": "R3: 该集合规模随压缩删除；值在 paper/data/gate_attrib.csv 的行数",
        "§III 驱逐与重算之差区间": "R3: 该区间句随压缩删除；值在 paper/data/eviction.csv 的 evicted_M / uncached_M 两列",
        "§Discussion reuse_frac 区间": "R3: 该区间句随压缩删除；值在 paper/data/reuse.csv 的 reuse_frac 列",
        "§IV round-1+ cap5_hc": "R2: round-1-and-later 命中率在 paper/data/hitrate.csv；§III 只印设备侧与 host 侧的区间",
        "§IV round-1+ cap8_hc": "R2: round-1-and-later 命中率在 paper/data/hitrate.csv；§III 只印设备侧与 host 侧的区间",
        "§III 拟合里的 host-tier 条数": "R3: 拟合句压缩后只说「across the fourteen runs we fitted」，不再拆 host-tier 条数；值在 paper/data/fit.csv 与 paper/data/reuse.csv",
        "foyer_breshz1_r2 复测前的 Δ（旧值，源自 claims_audit）": "R3: 正文只报复测位移（11.2/6.5/6.4/4.5pp，sec_results.tex「the correction moved them」那句），不再印旧值；旧值出处 docs/codex_review_prompt_r23.md，新值在 paper/data/table1.csv 的 delta_pp 列",
        "foyer_bres_r2 复测前的 Δ（旧值，源自 claims_audit）": "R3: 同上；新值在 paper/data/table1.csv 的 delta_pp 列",
        "foyer_hz0_r2 复测前的 Δ（旧值，源自 claims_audit）": "R3: 同上；新值在 paper/data/table1.csv 的 delta_pp 列",
        "foyer_hz2_r2 复测前的 Δ（旧值，源自 claims_audit）": "R3: 同上；新值在 paper/data/table1.csv 的 delta_pp 列",
        "§III cap2_hp 的 degenerate_steps": "R3: 半池实验的逐项读数在 paper/data/pool50.csv；正文只报长度边界结论",
        "§III cap3_p75 的 degenerate_steps": "R3: 半池实验的逐项读数在 paper/data/pool50.csv；正文只报长度边界结论",
        "§IV 重复组的 SLO 散布 cap4+HiCache (frontier": "R3: 分组散布整段外移；值在 paper/data/replicates.csv 的 slo_range_pp 列",
        "§IV 重复组的 SLO 散布 cap2+HiCache (frontier": "R3: 分组散布整段外移；值在 paper/data/replicates.csv 的 slo_range_pp 列",
        "§IV 重复组的 SLO 散布 Foyer base (hw=0,t=0.9": "R3: 分组散布整段外移；值在 paper/data/replicates.csv 的 slo_range_pp 列",
        "§IV 重复组的 SLO 散布 horizon=1": "R3: 分组散布整段外移；值在 paper/data/replicates.csv 的 slo_range_pp 列",
        "§IV 重复组的 SLO 散布 cap3+HiCache (frontier": "R3: 分组散布整段外移；值在 paper/data/replicates.csv 的 slo_range_pp 列",
        "§IV 重复组的 SLO 散布 cap3 device-only (pair": "R3: 分组散布整段外移；值在 paper/data/replicates.csv 的 slo_range_pp 列",
        "§IV 重复组的 SLO 散布 horizon=2 (the closest": "R3: 分组散布整段外移；值在 paper/data/replicates.csv 的 slo_range_pp 列",
        "§IV 重复组的 SLO 散布 scans the queue": "R3: 分组散布整段外移；值在 paper/data/replicates.csv 的 slo_range_pp 列",
        "§IV 重复组的 SLO 散布 single-flight off": "R3: 分组散布整段外移；值在 paper/data/replicates.csv 的 slo_range_pp 列",
        "§III 拟合的 r": "R3: 拟合句随压缩重写（正文只留方向性说法）；值在 paper/data/fit.csv 的 r / max_abs_resid_ms 列",
        "§III 拟合的最大残差": "R3: 拟合句随压缩重写（正文只留方向性说法）；值在 paper/data/fit.csv 的 r / max_abs_resid_ms 列",
        "§III 拟合的点数": "R3: 拟合句随压缩重写（正文只留方向性说法）；值在 paper/data/fit.csv 的 r / max_abs_resid_ms 列",
        "superseded foyer_bres 复用占比": "R3: 「污染 vs 干净」的逐臂读数随压缩外移（supplement_material.md §S1）；值在 paper/data/superseded.csv 的 reuse_frac / tau2_ms 列",
        "superseded foyer_bres τ₂": "R3: 「污染 vs 干净」的逐臂读数随压缩外移（supplement_material.md §S1）；值在 paper/data/superseded.csv 的 reuse_frac / tau2_ms 列",
        "superseded foyer_bres_r2 复用占比": "R3: 「污染 vs 干净」的逐臂读数随压缩外移（supplement_material.md §S1）；值在 paper/data/superseded.csv 的 reuse_frac / tau2_ms 列",
        "realhr_foyer 的墙钟": "R3: 第二条 trace 的逐臂读数随压缩外移；值在 paper/data/reuse_x.csv / toolwait.csv",
        "realhr_foyer_r2 的墙钟": "R3: 第二条 trace 的逐臂读数随压缩外移；值在 paper/data/reuse_x.csv / toolwait.csv",
        "§VI 阈值表的 scan 行": "R3: 阈值敏感性整张表外移（supplement_material_discussion.md §3.1）；值在 paper/data/slo_sensitivity.csv",
        "§VI 阈值表的 hz2_r2 行": "R3: 阈值敏感性整张表外移（supplement_material_discussion.md §3.1）；值在 paper/data/slo_sensitivity.csv",
        "§VI 阈值表的 hz2_r3 行": "R3: 阈值敏感性整张表外移（supplement_material_discussion.md §3.1）；值在 paper/data/slo_sensitivity.csv",
        "§VI 阈值表的 hz1 行": "R3: 阈值敏感性整张表外移（supplement_material_discussion.md §3.1）；值在 paper/data/slo_sensitivity.csv",
        "§VI 阈值表的 hz1_r2 行": "R3: 阈值敏感性整张表外移（supplement_material_discussion.md §3.1）；值在 paper/data/slo_sensitivity.csv",
        "§VI 阈值表的 hz1_r3 行": "R3: 阈值敏感性整张表外移（supplement_material_discussion.md §3.1）；值在 paper/data/slo_sensitivity.csv",
        "§VI 阈值表的 hc 行": "R3: 阈值敏感性整张表外移（supplement_material_discussion.md §3.1）；值在 paper/data/slo_sensitivity.csv",
        "§VI 阈值表的 bres_r2 行": "R3: 阈值敏感性整张表外移（supplement_material_discussion.md §3.1）；值在 paper/data/slo_sensitivity.csv",
        "§VI 阈值表的 aimd2_paper_r3 行": "R3: 阈值敏感性整张表外移（supplement_material_discussion.md §3.1）；值在 paper/data/slo_sensitivity.csv",
        "§III τ₁−τ₂ 下界": "R3: 逐臂 τ 区间表随压缩删除；值在 paper/data/decomp.csv 的 step_perreq_ms 列",
        "§III τ₁−τ₂ 上界": "R3: 逐臂 τ 区间表随压缩删除；值在 paper/data/decomp.csv 的 step_perreq_ms 列",
        "§III τ₂ 下界": "R3: §III 现在印的是「14 条拟合 run」的口径（τ₂ 20.6--31.2ms），而这条守卫的集合是 decomp.csv 全部 36 行（τ₂ 20.6--39.2ms）—— 同一句里 20.6 巧合数值相同、集合不同；全表口径仍在 §VII 的 Related Work 那句（有活守卫）与 paper/data/decomp.csv 的 step_perreq_ms 列",
        "§III τ₂ 上界": "R3: 逐臂 τ 区间表随压缩删除；值在 paper/data/decomp.csv 的 step_perreq_ms 列",
        "§III 基线步成本（τ₂）": "R3: 该句随压缩删除；值在 paper/data/decomp.csv 的 step_perreq_ms 列（default 行）",
        "§V 基线 的准入周期占比": "R3: 该句随压缩删除；值在 paper/data/gate_attrib.csv 的 total_admits / samples 列",
        "§VII 25 档被挡周期数": "R3: 25 档的单变量分解与 backlog 细账随压缩外移；值在 paper/data/tier25_old.csv / gate_attrib.csv / projection.csv / backlog.csv",
        "§VII 25 档安全阀占比": "R3: 25 档的单变量分解与 backlog 细账随压缩外移；值在 paper/data/tier25_old.csv / gate_attrib.csv / projection.csv / backlog.csv",
        "§VII 25 档回合闸门占比": "R3: 25 档的单变量分解与 backlog 细账随压缩外移；值在 paper/data/tier25_old.csv / gate_attrib.csv / projection.csv / backlog.csv",
        "§VII 25 档投影占预算%": "R3: 25 档的单变量分解与 backlog 细账随压缩外移；值在 paper/data/tier25_old.csv / gate_attrib.csv / projection.csv / backlog.csv",
        "realhr_foyer 的 5s 距离": "R3: 第二条 trace 的逐臂读数随压缩外移；值在 paper/data/reuse_x.csv / toolwait.csv",
        "realhr_foyer 的 10s 距离": "R3: 第二条 trace 的逐臂读数随压缩外移；值在 paper/data/reuse_x.csv / toolwait.csv",
        "realhr_foyer_r2 的 5s 距离": "R3: 第二条 trace 的逐臂读数随压缩外移；值在 paper/data/reuse_x.csv / toolwait.csv",
        "realhr_foyer_r2 的 10s 距离": "R3: 第二条 trace 的逐臂读数随压缩外移；值在 paper/data/reuse_x.csv / toolwait.csv",
        "§VI ready 时钟：控制器臂条数": "R3: 同上；值在 paper/data/arrival_slo.csv",
        "§VI ready 时钟：移动 ≤2.5pp 的条数": "R3: 同上；值在 paper/data/arrival_slo.csv",
        "§VI foyer_rg4 的 ready 位移": "R3: ready 时钟逐臂读数随压缩外移（supplement_material_discussion.md §块 4）；值在 paper/data/arrival_slo.csv 的 move_pp 列",
        "§V 历史上带旗的条数": "R3: 「历史上带旗」的计数随压缩删除；值在 paper/data/concurrency.csv",
        "§V 那五条里受损的条数": "R3: 同上；值在 paper/data/concurrency.csv",
        "表 I 脚注：两条半池臂停在多少步": "R3: 表 I 脚注重写后不再印半池臂的步数；值在 paper/data/pool50.csv 的 attempted_steps 列",
        "§repro 同族干净 run 的条数（表注那处）": "R3: 干净 run 的逐条读数随压缩外移（supplement_material.md §S1）；值在 paper/data/concurrency.csv 的 tau2_ms 列",
        "§repro 同族干净 τ₂ 下界（sec_results.tex）": "R3: 干净 run 的逐条读数随压缩外移（supplement_material.md §S1）；值在 paper/data/concurrency.csv 的 tau2_ms 列",
        "§repro 同族干净 τ₂ 上界（sec_results.tex）": "R3: 干净 run 的逐条读数随压缩外移（supplement_material.md §S1）；值在 paper/data/concurrency.csv 的 tau2_ms 列",
        "§III foyer_nogate 的空转%": "R3: 逐臂空转表随压缩删除；值在 paper/data/decomp.csv 的 idle_pct 列",
        "§III foyer_nogate 的 R̄busy（两位）": "R3: 同上；值在 paper/data/arm_running.csv 的 running_busy 列",
        "§III cap4 的空转%": "R3: 同上（正文现在只用 idle 的**区间** 6.3--41.9%，不再逐臂印）",
        "§III cap4 的 R̄busy（两位）": "R3: §VII 的「两档在跑数几乎一样」那段论证随压缩删除；值在 paper/data/arm_running.csv 的 running_busy 列（⚠ 同一个数在 §III 的裸表 R̄ 行里仍在，但那格不是这句话的守卫对象）",
        "§III foyer_hz0_r2 的空转%": "R3: 同上；值在 paper/data/decomp.csv 的 idle_pct 列",
        "§III 回归的条数": "R3: 同上；值在 paper/data/fit.csv",
        "§III 回归的 r": "R3: 同上；值在 paper/data/fit.csv",
        "§III 回归的最大残差": "R3: 同上；值在 paper/data/fit.csv",
        "归因 foyer_sf0_r2 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "归因 foyer_hz1 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "归因 foyer_hc 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "归因 foyer_hz2_r2 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "归因 foyer_hz0_r2 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "归因 foyer_bres_r2 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "归因 foyer_breshz1_r2 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "归因 foyer_nogate 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "归因 foyer_rg4 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "归因 foyfix_hc 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "归因 aimd2 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "归因 aimd2_paper_r3 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "归因 foyer_scan 的 占用&R̄&τ₁ 三连": "R3: §V 只印归因的计数与方向，13 行逐臂读数随压缩外移（supplement_material.md §S4）；值在 paper/data/attribution.csv 的 occ_pct / running_busy / tau1_ms 列",
        "§III 去记账臂 的 Δ空转": "R3: 去记账臂的三项 Δ 随压缩删除；值在 paper/data/decomp.csv 与 paper/data/table1.csv",
        "§III 去记账臂 的 Δ忙时": "R3: 去记账臂的三项 Δ 随压缩删除；值在 paper/data/decomp.csv 与 paper/data/table1.csv",
        "§III 去记账臂 的 Δ墙钟": "R3: 去记账臂的三项 Δ 随压缩删除；值在 paper/data/decomp.csv 与 paper/data/table1.csv",
        "§VII 25 档 backlog 不再印比值": "R3: 25 档的单变量分解与 backlog 细账随压缩外移；值在 paper/data/tier25_old.csv / gate_attrib.csv / projection.csv / backlog.csv",
        "§VII pois200_foyer_push_25 非零周期占比": "R3: backlog 的逐档读数随压缩删除；值在 paper/data/backlog.csv / gate_attrib.csv",
        "toolwait realhr_cap2 demand_med_s": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_cap2 demand_mean_s": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_cap2 measured_mean_s": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_cap2 要求中位": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_cap2 要求均值": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_cap4 demand_med_s": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_cap4 demand_mean_s": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_cap4 measured_mean_s": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_cap4 要求中位": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_cap4 要求均值": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_foyer demand_med_s": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_foyer demand_mean_s": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_foyer measured_mean_s": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_foyer 要求中位": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "toolwait realhr_foyer 要求均值": "R3: tool_wait 的逐 run 读数随压缩外移；值在 paper/data/toolwait.csv 的 demand_med_s / demand_mean_s / measured_mean_s 列",
        "foyer_hc 增长预留 tokens": "R3: 该读数随压缩删除；值在 paper/data/projection.csv",
        "§VI 主 trace 上的 flag 条数": "R3: 按 trace 拆分的旗标计数随压缩删除；值在 paper/data/concurrency.csv（主 trace 12、变负载 2）",
        "§VI 变负载 trace 上的 flag 条数": "R3: 同上；值在 paper/data/concurrency.csv",
        "§V 停摆里引擎空闲的分钟": "R3: 停摆段的逐项读数外移（supplement_material.md §S6）；值在 paper/data/aimd_stall.csv 的 idle_in_gap_min 列",
        "§VI 存世那一对可重新 diff": "R3: 控制器副本的版本史外移（supplement_material.md §S2 与 supplement_material_discussion.md §1.3）；该主张现在叙述在 S2 里",
        "§VI 存世那一对的 diff 行数与处数": "R3: 同上；22 行、两处在 supplement_material_discussion.md §1.3（正文保留「diverges in two places」）",
        "§V scan 的控制周期数": "R3: scan 臂的日志计数随压缩外移（supplement_material_results.md §块 1）；值在 paper/data/gate_attrib.csv 的 samples / total_admits 列",
        "§V scan 的放行次数": "R3: scan 臂的日志计数随压缩外移（supplement_material_results.md §块 1）；值在 paper/data/gate_attrib.csv 的 samples / total_admits 列",
        "§V 重跑停在第几步": "R3: AIMD 停摆的逐项读数外移；值在 paper/data/aimd_stall.csv",
        "§V 第一次尝试停摆时的排队数": "R3: 同上；值在 paper/data/aimd_stall.csv",
        "§V 停摆时长（发许可到发许可）": "R3: 同上；值在 paper/data/aimd_stall.csv",
        "§V 重跑排队未准入的会话数": "R3: 同上；值在 paper/data/aimd_stall.csv",
        "§V 闸门臂的条数": "R3: 第四路线那段重写后不再印闸门臂条数；值在 results/night/pois200_foyer_rg* 三个目录",
        "§VII 两条 trace 的 prompt 上中位（整句）": "R3: 该对照句随压缩删除；值由检查器从 data/replay_*.csv 现算（上中位）",
        "§III 配对的在跑数（Scope 句）": "R3: Scope 句随压缩重写；值在 paper/data/tierpair.csv 的 Rbar_busy 列",
        # ⚠ 2026-09-27：这两个键原来是**前缀键**（`斜率 main*` / `斜率 xtrace*`），
        # 而族里的 `斜率 xtrace 1.076->1.160`（31.2）**值仍在正文** ⇒ 前缀键把一条活检查
        # 也退了（检查器打 `!! 退役未生效` 报出来）。**改成逐条精确键**：
        # 值确实不在正文的 10 条才退，活着的那条自然复活。
        # 这是本项目「前缀键会静默吞掉同族检查」的又一次 —— 判据的作用域必须显式。
        # ⚠⚠ 2026-09-27（`slope.csv` 修好之后）：**这五条键的值部分随数据漂了** ——
        # 键原来是 `1.000->1.271` 等（`slope.csv` 里那个【过期】版本的 Rbar），
        # 而 `ck("斜率 %s %s->%s" % (trace, r0, r1))` 的描述是**从 CSV 现算**的
        # ⇒ `slope.csv` 一修好，描述变成 `0.998->1.271` 等，**旧键失配 ⇒ 退役失效**
        # （5 条 MISS），同时旧键变成孤儿（**孤儿守卫正确报了出来**）。
        #
        # ⇒ **设计脆弱性（记在这里，别下次再踩）**：**退役键不该嵌数据** ——
        # 它把「这条检查该不该退」和「数据现在是什么」绑在了一起，数据一变就双双失效。
        # 安全网是有的（孤儿守卫 + `!! 退役未生效`），所以它**会响**、不会静默；
        # 但每次数据更新都要跟着改键。**理想的修法是让描述稳定**（例如用段序号
        # 而不是段端点），那是一次独立改动，本次只把键改对。
        "斜率 main 0.998->1.271": "R2: 分段斜率在 elasticity.csv / elasticity_x.csv，正文只印两端段值与拟合值",
        "斜率 main 0.998->1.841": "R2: 分段斜率在 elasticity.csv / elasticity_x.csv，正文只印两端段值与拟合值",
        "斜率 main 1.271->1.508": "R2: 分段斜率在 elasticity.csv / elasticity_x.csv，正文只印两端段值与拟合值",
        "斜率 main 1.508->1.534": "R2: 分段斜率在 elasticity.csv / elasticity_x.csv，正文只印两端段值与拟合值",
        "斜率 main 1.650->1.841": "R2: 分段斜率在 elasticity.csv / elasticity_x.csv，正文只印两端段值与拟合值",
        # ⚠ 新增的一条（`slope.csv` 修好后设备侧链多了 `cap3_pd` 那一段 ⇒ main 由 5 段变 6 段）。
        # 值同样不在正文里，按同一理由退役。
        "斜率 main 1.534->1.650": "R2: 分段斜率在 elasticity.csv / elasticity_x.csv，正文只印两端段值与拟合值",
        "斜率 xtrace 1.076->1.500": "R2: 分段斜率在 elasticity.csv / elasticity_x.csv，正文只印两端段值与拟合值",
        "斜率 xtrace 1.160->1.287": "R2: 分段斜率在 elasticity.csv / elasticity_x.csv，正文只印两端段值与拟合值",
        "斜率 xtrace 1.287->1.409": "R2: 分段斜率在 elasticity.csv / elasticity_x.csv，正文只印两端段值与拟合值",
        "斜率 xtrace 1.409->1.426": "R2: 分段斜率在 elasticity.csv / elasticity_x.csv，正文只印两端段值与拟合值",
        "斜率 xtrace 1.426->1.500": "R2: 分段斜率在 elasticity.csv / elasticity_x.csv，正文只印两端段值与拟合值",
        # ⚠⚠ 2026-09-27（r53 复核 F2）：上一轮拆键时**唯独留下了这一条**（说它「值仍在
        # 正文 ⇒ 复活」），而它印 OK 的理由与 F1 **同型**：**撞上了**。它的值是
        # `slope.csv` 里 realhr_cap2→cap3 的斜率（−31.2，`.lstrip("-")` 后查 `31.2`），
        # 而正文里的 `31.2` 出现在 `sec_model.tex`（τ₂ 的上界「τ₂ from 20.6 to 31.2 ms」）
        # 与 `sec_xtrace.tex` 表 B 的 τ₂ 列 —— **都是步成本，不是斜率**。
        # 而且 §VI 自己明写「we do not lean on slopes spanning ranges of different
        # length and level」（sec_xtrace.tex）⇒ 它的 10 个同胞退役是对的，这一条也该退。
        # 「复活」的依据本来就只是字符串撞车，不是「这个量回到了正文」。
        "斜率 xtrace 1.076->1.160": "R2: 与 10 个同胞同源 —— §VI 明写不拿跨长度/跨水平的斜率说话，正文不印任何分段斜率；值在 paper/data/slope.csv 的 slope_pp_per_unit 列（realhr_cap2→cap3 = −31.2）。⚠ 正文里的 `31.2` 属于另一个量（τ₂）⇒ 见 STR_ELSEWHERE",
        "§III 斜率来自哪一节": "R3: 该交叉引用句随压缩删除；§IV 的 ε 分段仍在正文",
        # ================================================================
        # 2026-09-27 第二批：**`\section{Load Dependence}` 整节删除**之后的退役
        # ================================================================
        # 依据：codex 2026-09-27 裁决第 1、2 条 —— 「先删这个实验轴及其对应主张」，
        # 并且裁决第 2 条明写**「收缩主张范围」与「把同一结论的证据藏进 supplement」
        # 是两件事**：该节的唯一作用（「同一个控制器族的最激进一端在轻载/重载下
        # 符号相反，+51% / -42%」）**随节一起撤回**，正文不再声称那个符号反转。
        # 逐字原文与「值现在在哪」的对照表在 `paper/supplement_material_discussion.md`
        # 的「块 7」；`paper/main.tex` 的写作纪律第 2 条也记着「不要再写回来」。
        # ⚠ 判据（本项目不变）：**退役要写「值现在在哪」，不是「值没了」** ——
        # 下面每一条都指到具体文件/列。
        "表 II cap2_25 墙钟&并发&SLO&段SD 四连": "R3: 25 档那张表（`tab:tier25`）随整节删除；该行在 paper/data/tier25.csv，逐字原文在 supplement_material_discussion.md 块 7",
        "表 II cap3_25 墙钟&并发&SLO&段SD 四连": "R3: 同上；值在 paper/data/tier25.csv（cap3_25 行）",
        "表 II cap4_25 墙钟&并发&SLO&段SD 四连": "R3: 同上；值在 paper/data/tier25.csv（cap4_25 行）",
        "表 II foyer_push_25 墙钟&并发&SLO&段SD 四连": "R3: 同上；值在 paper/data/tier25.csv（foyer_push_25 行）",
        "§VII 25 档 base 的墙钟": "R3: 「25 档的节流开关对照」随整节删除；值在 paper/data/loadtier.csv 的 wall_min 列（tier=25, arm=base, 58.4）",
        "§VII 25 档 push 的墙钟": "R3: 同上；值在 paper/data/loadtier.csv（tier=25, arm=push, 28.8）",
        "§VII tier25 表注的 harness 哈希": "R3: 表注随整节删除；判据（四条同代）仍在 results/night/pois200_{cap2,cap3,cap4,foyer_push}_25/metadata.json 的 code.run_matrix.py = a8605b1e77d5，逐字见 supplement_material_discussion.md 块 7",
        "§VII 25 档引擎上报占预算%": "R3: 25 档的投影/占用细账随整节删除；值在 paper/data/projection.csv 的 occ_pct_of_budget 列（pois200_foyer_push_25 行）",
        "§load 25 档的加速幅度": "R3: 「两档符号相反」这条主张**随整节撤回**（裁决第 1 条：「先删这个实验轴及其对应主张」）；两个读数在 paper/data/loadtier.csv（58.4 与 28.8），逐字见 supplement_material_discussion.md 块 7",
        "§load 200 档的减速幅度": "R3: 同上（291.3 与 415.0 在 paper/data/loadtier.csv）；⚠ 200 档那一行（`all throttles off`）**仍在正文表 I**，§II 与 §V 仍引它",
        "foyer_hc 被强制准入数": "R3: 饥饿守卫那段随压缩外移（body 现在只写「为什么节流都不管用」的结论）；值在 paper/data/gate_attrib.csv 的 forced_admits 列，逐字原文在 supplement_material_results.md 块 R5",
        "foyer_hc 总准入数": "R3: 同上；值在 paper/data/gate_attrib.csv 的 total_admits 列（206）",
        "foyer_hc 被强制准入占比": "R3: 同上；= forced_admits / total_admits = 24.8%，两个分量都在 paper/data/gate_attrib.csv",
        "rl99 转折前桶（第 270 分）": "R3: §VI 的「同一 run 内两个窗口把原因钉在共租上」那段随压缩删除（`t85` 那一条同日已退役）；值在 paper/data/tau2_windows.csv 的 tau2_p50_ms 列",
        "§VII 全关节流那条的 SLO 代价": "R1: 值**仍在正文** —— §III 的「bought with 43.6\\,pp of SLO」（sec_model.tex，那条守卫还活着）；退役的是 §VII 那一份**副本**，该句随整节删除。⚠ 同一段另外三个差值（idle 13.8 / busy 11.1 / wall 2.7）也只在 deletion 前的正文里",
        "§VII 的 25 档批次又写回「same day」（实为跨 09-14/09-15 两天）": "R3: 该句随整节删除（正文不再提 25 档批次的日期）；判据本身仍成立 —— 七条 thr25_* 的 steps.jsonl 首末时间戳实测仍是连续两天（那两条数据守卫还活着）",
        # ⚠ 这两条**此前是【假通过】**（2026-09-27 查出）：`has("1.137")` 会退化成
        # `"1.1"`，而它撞上正文里别处的 `1.1`。此刻实测那两行已随 §Load 删除，
        # 退役理由与上面同源 —— 顺手把它们**原本就不对的理由**改准（值在
        # `arm_running.csv`，不在 backlog.csv；后者只是同族读数）。
        "§VII 200 档基线在跑均值": "R3: §Load 整节删除（「两档的在跑数几乎一样」那个并列也随之删除）；值在 paper/data/arm_running.csv 的 running_all 列（foyer_hc 1.137）",
        "§VII 25 档在跑均值": "R3: 同上；值 = results/night/pois200_foyer_push_25/metrics.csv 的 sglang:num_running_reqs 全时段均值（1.136），与 paper/data/arm_running.csv 同口径",
    }

    # 本次运行里**被咨询到**的退役键。`ck` / `ck_near` / `_direct_fail` 每一次调用都会
    # 咨询 `_retired()`（值命中 → `_notice_noop`；值不在 → else 分支），所以一次完整的
    # base 运行里**没有进这个集合的键 = 孤儿**（没有任何检查去查它）。判据在文件末尾。
    _retired_used = set()

    def _retired(desc):
        """退役判据：**默认精确匹配**；只有键尾带 `*` 的才按前缀匹配。

        ⚠ 2026-09-26 活性审计（中立子 agent）实测：原来是**一律** `startswith(k)`，
        于是短键会**静默吞掉后来新增的同前缀检查** —— 探针量出 **34 条**被吞
        （`§A100 ε ` 7 条、`round-1+ ` 15 条、`图2 图注：` 4 条、`斜率 main/xtrace` 6 条、
        `host-tier run 条数（§I` 2 条）。其中至少五组的**主张仍在正文**，
        也就是说那些守卫是**死了但没人知道**。
        现在：`"foo"` 只退 `foo`；`"foo*"` 才退 `foo` 开头的全部，而且**写在键上看得见**。
        """
        # ⚠⚠ 2026-09-27：`NORE=1` **此前只写在 CLAUDE.md 里，代码里根本没有实现**
        # （`grep NORE` 只命中三处注释）。于是本项目自称「唯一可靠的判据」——
        # 「把退役名单关掉跑一遍，看哪些检查从『通过』变成 MISS，那些就是本来该活、
        # 其实已死的」——**从来没有真正跑过**。补上。
        if os.environ.get("NORE"):
            return None
        for k, why in RETIRED.items():
            if k.endswith("*"):
                if desc.startswith(k[:-1]):
                    _retired_used.add(k)    # 见下面「孤儿键」的机械判据
                    return why
            elif desc == k:
                _retired_used.add(k)
                return why
        return None

    # ---- 「退役了、值却仍命中正文」的**自动判据**（2026-09-27 r52 复核加）---------
    # 为什么需要：`ck` / `ck_near` 的顺序是「**先查值、后查退役**」——
    #     if has(src, val): 印 OK        ← 走到这里**根本不会查退役名单**
    #     else:             _retired()   ← 只有值不在时才查
    # 于是一条退役条目可以有**两种**死法，而 `base` 与 `NORE=1` 两个输出**都看不见**：
    #   (a) 值还在正文里 ⇒ 两个跑法都印 OK，退役成了**空文**（"关掉了一个还活着的守卫"）；
    #   (b) 退役键没有任何检查去查（孤儿键）⇒ 一次也不会被咨询。
    # NORE=1 量到的是「被咨询到」的那些（今天 263 条），**(a)(b) 都是它的盲区** ——
    # 所以「NORE=1 是唯一可靠判据」这句是错的（CLAUDE.md 已改口径）。
    # 这里补上 (a) 的判据：值命中时**额外**查一次退役名单，命中就印 `!!`。
    # ⚠ (b) 的自动判据 2026-09-27（r53 复核 F3）已补：见文件末尾的「孤儿退役键」一节。
    _noop_retired = []

    # ---- 「退役**生效**了，但那串字在正文里属于**另一个量**」的注明表 ----------------
    # （2026-09-27 r53 复核 F1/F2 加。**这是约束 4 那个判据的机械化**。）
    # 为什么需要：`!! 退役未生效` 的判据是 `has(src, val)` =「**这串字在不在正文**」，
    # 而本项目早知道「**在**不等于**是这个量**」（同一个数在别处出现 ≠ 它用在了这里）。
    # 下面两条的字符串是 `0.1` / `31.2` 这种一两位小数的短数，短到正文里必然有同形串：
    #   `replicates 墙钟散布下界` 的 `0.1`  → sec_xtrace.tex「0.1\,pp below the
    #        controller's SLO」（cap sixteen 距控制器 SLO 的距离），不是墙钟散布；
    #   `斜率 xtrace 1.076->1.160` 的 `31.2` → sec_model.tex 的 τ₂ 上界、
    #        sec_xtrace.tex 表 B 的 τ₂ 列，是**步成本**，不是斜率。
    # 两条的退役**都是对的**（正文确实不引这两个量），所以它们不该年年印 `!!`
    # —— 而印 `!!` 又正是**上一轮把退役键删掉**的原因（那是错的处置：删键 = 把守卫
    # 变回「靠撞车活着」，值一偏就假 MISS，把人骗去改对的生成器）。
    # 处置：退役照常生效，命中改成一条**每次运行都打印**的 `~~` 行（不是静默），
    # 并且**要求那条「不相关的语境串」确实在正文里**（值 + 解释 = 可核的注明，
    # 不是「把它静音」）；语境串哪天没了，就退回 `!!` 让人看。
    STR_ELSEWHERE = {
        "replicates 墙钟散布下界": (
            "0.1\\,pp below the controller's SLO",
            "那串 0.1 在 sec_xtrace.tex 是 cap sixteen 距控制器 SLO 的距离（0.1pp）"),
        "斜率 xtrace 1.076->1.160": (
            "$\\tau_2$ from 20.6 to 31.2",
            "那串 31.2 在 sec_model.tex 是 τ₂ 的上界（步成本），不是斜率"),
    }
    _str_elsewhere_hit = []
    # 正文（全稿）的**空白归一化**副本：语境串的判据与 `ck_near` 的关键词同一条规矩
    # （LaTeX 源码是硬换行的，短语里的空格当 `\s+`）。
    _paper_norm = re.sub(r"\s+", " ", " ".join(_src_of(None).split()))

    def _str_elsewhere_ctx_ok(phrase):
        return (" ".join(phrase.split()) in _paper_norm)

    def _notice_noop(desc, val):
        """值命中时调用：若这个 desc 同时**在退役名单里**，说明那条退役没有生效。"""
        _ry = _retired(desc)
        if _ry:
            _se = STR_ELSEWHERE.get(desc)
            if _se and _str_elsewhere_ctx_ok(_se[0]):
                _str_elsewhere_hit.append(desc)
                print("  ~~   %-58s %s（退役**生效**；这串字属于另一个量：%s）"
                      % (desc, val, _se[1]))
                return _ry
            _noop_retired.append(desc)
            print("  !!   %-58s %s（⚠ 退役未生效：值仍在正文；理由：%s）"
                  % (desc, val, _ry))
        return _ry

    def _direct_fail(desc, val, where):
        """给**不走 `ck` / `ck_near` 的直写守卫**一条退役通路，返回「是否已退役」。

        为什么需要：`RETIRED` 原来只被 `ck` / `ck_near` 查（那两处各有一份判断）。
        而检查器里还有一批守卫写成 `checks += 1; if <条件>: fails.append(...)` ——
        它们**没有**退役通路。于是 `\section{Load Dependence}` 整节删除之后，
        「§VII 的 25 档批次又写回 same day」这条**只能靠改代码关掉**，
        而改代码关掉一个守卫是**没有留痕**的（本项目明令：退役要留痕、要能一条命令撤回）。

        ⚠ 判据与 `ck` 完全一致（同一个 `_retired()`），所以 `NORE=1` 对拍也照常适用：
        退役后它**应该**在 NORE=1 下报 MISS —— 报不出来才说明关掉的是个活守卫。
        """
        nonlocal checks
        checks += 1
        _ry = _retired(desc)
        if _ry:
            print("  --   %-58s %s（退役：%s）" % (desc, val, _ry))
            return True
        return False

    def ck(desc, val, where=None, tier="P"):
        """tier="P" 正文引用过这个量，必须出现；tier="S" 论文【不逐条印】这个量
        （只印它的一个聚合/区间），找不到是预期内的，单独列出来供人扫一眼。

        为什么要有这一档：2026-09-24 之前 124 项检查里常年有 20 多项 MISS，
        全是"论文没逐条印"的假阳性 —— 假阳性一多，真 MISS 就淹掉了
        （这正是这个脚本要防的那类错误，只不过发生在脚本自己身上）。
        但 S 档不许变成"眼不见为净"：它照旧逐条打印，只是不计入退出码。
        """
        nonlocal checks
        checks += 1
        src = _src_of(where)
        _audit(desc, val, src)
        if has(src, val):
            _notice_noop(desc, val)   # ⚠ 值命中时**额外**查一次退役名单（见上面的长注释）
            if VERBOSE:
                print("  OK   %-58s %s" % (desc, val))
        elif tier == "S":
            # ⚠ 2026-09-26：`tier="S"` 这一支**先返回**，所以退役名单对它无效 ——
            # 一条标了 S 的检查如果同时被写进 `RETIRED`，那条退役记录是**死的**
            # （永远走不到 `_retired()`）。中立复核者全量核名单时发现
            # `§Discussion round-1+ cap6_hc` 正是这种死条目；**该键已删**
            # （2026-09-27 r53 F3：它同时还是孤儿键，见上面退役名单里的注）。
            # ⚠ `ck` 与 `ck_near` **各有一份**这段（本函数的两条分支），
            # 两处必须一起改 —— 只改一处就是又一次「两份实现」。
            _ry = _retired(desc)
            if _ry:
                print("  --   %-58s %s（退役：%s；⚠ S 档，本就不计入退出码）"
                      % (desc, val, _ry))
            else:
                secondary.append((desc, val, where or "全篇"))
        else:
            # 退役要走**同一个** `_retired()`（`ck` 与 `ck_near` 各写一份判断
            # 就是两份实现；2026-09-26 第一次加的时候只加了 ck_near 那条分支，
            # 于是走 `ck` 的六条斜率检查照旧报 MISS）。
            _ry = _retired(desc)
            if _ry:
                print("  --   %-58s %s（退役：%s）" % (desc, val, _ry))
            else:
                fails.append((desc, val, where or "全篇"))

    def ck_near(desc, val, where, keyword, window=260, tier="P"):
        """值必须出现在【关键词附近】—— 补 `ck` 的假通过。

        为什么要有：`ck` 是字符串级的，它只问「这个数在不在正文里」。
        2026-09-25 抓到一个实例：§III 写基线步成本「39.3 ms」，而统一 τ₂ 定义后
        `decomp.csv` 里它已经是 **39.2** —— `ck` 却通过了，因为「39.2」在
        §V 的归因表里作为另一条臂的 Occ. 出现过。**同一个数在别处出现，
        不等于它用在了这里。** 这正是本项目「从错的列抄数」那一类的镜像。
        """
        nonlocal checks
        checks += 1
        src = _src_of(where)
        i = src.find(str(keyword))
        hit = False
        # `val` 允许是**列表**：`num_words()` 对名次/条数返回 [基数, 序数]
        # （`five` / `fiveth`、`seven` / `seventh`），任一命中即可。
        # 2026-09-25 踩到：原来直接把列表交给 `has()`，而 `has()` 第一行是
        # `s = str(v)` —— 列表被 str 成 "['five', 'fiveth']"，再去正文里做
        # **字面子串**匹配，必然落空 → 五条新检查全部假 MISS，
        # 而正文其实是对的。**假 MISS 和假通过一样坏**：它会让人去改对的数。
        _cand = val if isinstance(val, (list, tuple)) else [val]
        # ⚠ 2026-09-26：关键词里的**空白一律当 `\s+`**。
        # 为什么：`ck_near` 原来是 `src.find(str(keyword))` —— **字面**匹配，
        # 而 LaTeX 源码是硬换行的，任何两三个词的短语都可能被断开。
        # 本项目为此假 MISS 过至少**五次**（`fastest static cap there`、
        # `control cycles`、`median occupancy of 95.3`、`admitted all 200`…），
        # 规矩一直是「关键词要挑同一行内的字串」—— 那是**让人去适应工具**。
        # 篇幅大手术把整稿重排之后，这一类假 MISS 一次冒出来十几条，
        # 所以改成**让工具适应文本**：短语里的空格可以是任意空白（含换行）。
        _kw_re = re.compile(r"\s+".join(re.escape(w) for w in str(keyword).split()))
        _mi = _kw_re.search(src)
        i = _mi.start() if _mi else -1
        while i >= 0:
            lo, hi = max(0, i - window), i + window
            if any(has(src[lo:hi], v) for v in _cand):
                hit = True
                break
            _mi = _kw_re.search(src, i + 1)
            i = _mi.start() if _mi else -1
        if hit:
            _notice_noop(desc, val)   # 同上：值命中时才查得出「退役未生效」
            if VERBOSE:
                print("  OK   %-58s %s（近 %s）" % (desc, val, keyword))
        elif tier == "S":
            # ⚠ 2026-09-26：`tier="S"` 这一支**先返回**，所以退役名单对它无效 ——
            # 一条标了 S 的检查如果同时被写进 `RETIRED`，那条退役记录是**死的**
            # （永远走不到 `_retired()`）。中立复核者全量核名单时发现
            # `§Discussion round-1+ cap6_hc` 正是这种死条目；**该键已删**
            # （2026-09-27 r53 F3：它同时还是孤儿键，见上面退役名单里的注）。
            # ⚠ `ck` 与 `ck_near` **各有一份**这段（本函数的两条分支），
            # 两处必须一起改 —— 只改一处就是又一次「两份实现」。
            _ry = _retired(desc)
            if _ry:
                print("  --   %-58s %s（退役：%s；⚠ S 档，本就不计入退出码）"
                      % (desc, val, _ry))
            else:
                secondary.append((desc, val, where or "全篇"))
        else:
            _ry = _retired(desc)
            if _ry:
                print("  --   %-58s %s（退役：%s）" % (desc, val, _ry))
            else:
                fails.append((desc + "（须在「%s」附近）" % keyword, val, where or "全篇"))

    # ---- reuse.csv：兑现率 ----
    for r in load(os.path.join(ROOT, "paper/data/reuse.csv")):
        # 兑现率：表 2 印了 device-only 五行与 host tier 三个静态点，其余臂只进区间
        in_tab = r["run"] in ("cap1", "cap2", "cap3_fixed", "cap4", "cap5",
                              "pairB_cap2hc", "cap3_hc", "cap4_hc")
        ck("%s 兑现率" % r["run"], "%.1f" % (float(r["realized_frac"]) * 100),
           tier="P" if in_tab else "S")
        # prompt 占比：正文只举 cap1 的 69.9% 当例子，其余不逐条印
        ck("%s 复用率(prompt 占比)" % r["run"], "%.1f" % (float(r["reuse_frac"]) * 100),
           tier="P" if r["run"] == "cap1" else "S")
    hc = [r for r in load(os.path.join(ROOT, "paper/data/reuse.csv"))
          if r["family"] == "hicache"]
    bad = [r for r in hc if r["contested"] == "CONTESTED"]
    good = [r for r in hc if r["contested"] != "CONTESTED"]
    # host-tier 的【兑现率区间】：正文 §model 印的是 72.8--92.5%（全部 19 条 host-tier
    # run）与 90.2--92.4%（跨控制器区间的三个静态点）。按正文的口径（百分比、1 位小数）
    # 检查；reuse_frac（占 prompt 的比例）正文不印，降为次要档。
    # 2026-09-24 之前这里查的是 reuse_frac 的原始小数字符串，而 "0.5" 这种
    # 1 位小数写法在全篇到处都是 —— 那种检查等于永远通过，抓不到任何东西。
    for tag, sel in (("受损", bad), ("干净", good)):
        if not sel:
            # 显式说出来，**不静默跳过**（CLAUDE.md：静默跳过是危险的那个方向）。
            # 2026-09-25：`foyer_breshz1_r2` 落地后，host-tier 里再没有 CONTESTED 的 run
            # —— bres/hz0/hz2/breshz1 四条被污染的**全部**已被干净重跑替代，
            # 「受损组」这个类别**空了**。正文若还印着受损组的区间，下面 allhc/st3
            # 的检查会以 MISS 暴露出来。
            print("  · %s组为空（host-tier 已无 CONTESTED 的 run）—— 跳过该组两项检查" % tag)
            continue
        ck("%s host-tier 复用下界(占 prompt)" % tag, "%.1f" % (min(float(r["reuse_frac"]) for r in sel) * 100), tier="S")
        ck("%s host-tier 复用上界(占 prompt)" % tag, "%.1f" % (max(float(r["reuse_frac"]) for r in sel) * 100), tier="S")
    allhc = hc
    # ⚠⚠ 2026-09-27（第二次落地）：**条数这一支的来源必须与正文那句话的来源相同。**
    # 正文的「the N host-tier runs that completed this trace at a *single*
    # configuration (HiCache on, at least 995 of its 999 steps)」= `gen_eviction.py`
    # 的判据集合 = `eviction.csv` 的 hicache 行。而 `reuse.csv` 的 hicache 行**少两条**
    # （`pairA_foyerhc` / `pairB_foyerhc`：它们在 eviction.csv 里但没有步成本，被
    # `gen_reuse.py` 跳过）。下面第 32xx 行那条 `ck("host-tier 集合条数（§III，源=eviction.csv）")`
    # 早就把这一点写明了（「`reuse.csv` 是错的源」），**但这一支一直没跟着改** ——
    # 于是同一条主张有两条守卫、各自期望一个数（28 vs 30）。这正是本项目
    # 「守卫读数据文件、正文读论文那张表」那一类。**现在两边都取 eviction.csv。**
    _ev_hc = [r["run"] for r in load(os.path.join(ROOT, "paper/data/eviction.csv"))
              if str(r.get("hicache")) in ("1", "True")]
    _n_ht = len(_ev_hc) if _ev_hc else len(allhc)
    ck("host-tier 兑现下界", "%.1f" % (min(float(r["realized_frac"]) for r in allhc) * 100))
    ck("host-tier 兑现上界", "%.1f" % (max(float(r["realized_frac"]) for r in allhc) * 100))
    # `cap5_hc` 2026-09-25 入表后，静态 host-tier 点是**四条**不是三条。
    # 下界随之从 90.2 变 87.9（cap5_hc 是最低的那条）——**这一条对论证不利**，
    # 但正因如此才必须进去：选择性报告一个已知更低的点是口径问题。
    st3 = [r for r in hc if r["run"] in ("pairB_cap2hc", "cap3_hc", "cap4_hc", "cap5_hc")]
    # **必须用 ck_near**：`ck` 是全局搜字符串，而 "90.2" 正好是 §III 表里
    # cap4_hc 那一格的值 —— 下界从 90.2 改成 87.9 后 `ck` 照样通过（假通过），
    # 本轮实测踩到：`sec_discussion.tex:590` 漏改它一声不吭。
    ck_near("静态 host-tier 兑现下界", "%.1f" % (min(float(r["realized_frac"]) for r in st3) * 100),
            "sec_model.tex", "on the four static host-tier caps")
    ck_near("静态 host-tier 兑现上界", "%.1f" % (max(float(r["realized_frac"]) for r in st3) * 100),
            "sec_model.tex", "on the four static host-tier caps")
    ck_near("摘要里的静态 host-tier 下界", "%.1f" % (min(float(r["realized_frac"]) for r in st3) * 100),
            "main.tex", "four static points hold")
    # host-tier run 的**条数**（正文写英文词，且随实验增长）
    ck_near("host-tier run 条数（§III）", num_words(_n_ht),
            "sec_model.tex", "host-tier runs that completed")
    # 2026-09-26：同一个条数在**另外三处**也写着，而守卫原来只盯 §III ——
    # 三处都停在了 **twenty-two**（旧集合），而它们引的区间（0.4511--0.6981、
    # 低端 59.7%、τ₁ 关联）**全都是 24 条那个集合算出来的**。
    # 这是「同一个主张会用不同的词在全篇说好几遍」+「派生量没人管」的合体。
    ck_near("host-tier run 条数（§I 低端那句）", num_words(_n_ht),
            "sec_intro.tex", "host-tier runs the low end")
    ck_near("host-tier run 条数（§I 关联那句）", num_words(_n_ht),
            "sec_intro.tex", "an association over")
    ck_near("host-tier run 条数（§VI 复用区间那句）", num_words(_n_ht),
            "sec_discussion.tex", "range of the")
    # ⚠ §III 里**还有一处**总数（「Across the N host-tier runs the host serves…」），
    # 用上面那个 keyword 抓不到 —— 2026-09-25 codex 第 25 轮点出：
    # 所问的「六处 nineteen」里就漏了这一处。补一条它专属的 keyword。
    ck_near("host-tier run 条数（§III 第二处）", num_words(_n_ht),
            # ⚠ 2026-09-27：锚 `host-tier\nruns the host serves` **已不存在**（那句话被压缩
            # 改写成 `across the thirty host-tier runs serves 3.1--19.3\,M each`），
            # 而值 `thirty` **仍在正文两处**（`:121` 与 `:171`）⇒ 这是**锚漂了，不是值丢了**。
            # 本项目规矩：锚失配 = 那条检查静默不再检查任何东西。改锚，不改数。
            "sec_model.tex", "across the thirty host-tier")
    # 摘要压缩后不再印 host-tier 的条数（§III 仍印，上面那条守着）
    # §Discussion 里**也**印了这个下界与条数 —— 2026-09-25 就是这一句漏改了
    # （`ck` 因为 90.2 在 §III 表里还有别的用处而放过它）。补上守卫。
    ck_near("§Discussion 的静态 host-tier 下界",
            "%.1f" % (min(float(r["realized_frac"]) for r in st3) * 100),
            "sec_discussion.tex", "tier table hold at")
    ck_near("§Discussion 的 host-tier 条数", num_words(_n_ht),
            "sec_discussion.tex", "tier table hold at")

    # ---- reuse_x.csv：第二条 trace ----
    for r in load(os.path.join(ROOT, "paper/data/reuse_x.csv")):
        # 正文印的是「74.8% 掉到 64.0%」两个端点与逐段斜率，中间两条只在 slope.csv 里
        # 正文印的是区间的两个端点（当前是 cap2 的 74.8 与 cap6 的 62.5）与逐段斜率；
        # 中间几条只在 slope.csv 里。端点会随扫描推进而变 —— 改这里时同步改正文。
        ck("xtrace %s 兑现率" % r["run"], "%.1f" % (float(r["realized_frac"]) * 100),
           tier="P" if r["run"] in ("realhr_cap2", "realhr_cap8") else "S")

    # ---- §VI 引的平均占用（13.9% / 25.2%）----
    _rx2 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/reuse_x.csv"))}
    if "realhr_cap2" in _rx2 and "occ_mean_pct" in _rx2["realhr_cap2"]:
        ck("第二条 trace cap2 的平均占用", _rx2["realhr_cap2"]["occ_mean_pct"], "sec_xtrace.tex")
    occ2 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/occupancy.csv"))}
    if "cap1" in occ2:
        ck("主 trace cap1 的平均占用", occ2["cap1"]["occ_mean_pct"], "sec_xtrace.tex")

    # ---- 第二条 trace 的重复对（cap4 vs cap4_r2）：散布 ----
    rx = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/reuse_x.csv"))}
    if "realhr_cap4" in rx and "realhr_cap4_r2" in rx:
        d = abs(float(rx["realhr_cap4"]["realized_frac"])
                - float(rx["realhr_cap4_r2"]["realized_frac"])) * 100
        ck("第二条 trace 重复对的兑现散布", "%.1f" % d, "sec_xtrace.tex")

    # ---- slope.csv ----
    for r in load(os.path.join(ROOT, "paper/data/slope.csv")):
        ck("斜率 %s %s->%s" % (r["trace"], r["r0"], r["r1"]),
           r["slope_pp_per_unit"].lstrip("-"))

    # ---- 表 I 的每一行：墙钟 / 并发 / SLO 三个显示列 ----
    # 2026-09-25 改成查【三个数连起来】的复合串。原来逐列查，而并发是 1.0/2.6/3.9
    # 这种短值 —— --audit 显示 "3.9" 在正文出现 6 次，逐列查等于空转。
    # 复合串一旦有一个数变了就对不上，这才叫检查。
    runs_csv = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/runs.csv"))}
    # ⚠ `aimd2_paper`（第一次尝试）也被排除：它的墙钟带 32 分钟停摆，
    # 2026-09-26 起表 I 那一行是第三次尝试 `aimd2_paper_r3`（有监督循环、最长中断 50 秒）。
    # `emit_csv` 仍会把两条都写进 CSV（那是全量表），但 LaTeX 只印 r3 那一行。
    NOT_PRINTED = {"pairA_cap2hc", "aimd2_paper"}
    # ⚠⚠ 2026-09-27：**每条行守卫必须指向那一行【真的印在哪】**。
    # 表 I 从 35 行缩到 27 行，8 条静态 cap 移出正文、由 supplement 的完整表承载
    # （`paper/supplement_table1.md`，逐字 35 行）—— 正文的 Notes to Table I 现在
    # 明写「The supplement carries our full run table, including the eight static caps
    # this one omits.」**所以这是一个正文里的主张，守卫要跟着它走**：
    # 行还在论文表里 ⇒ 查 `sec_results.tex`；已移出 ⇒ 查 supplement 的完整表。
    # 判据来自 `gen_table.py` 的 `PAPER_OMIT`（生成器与 LaTeX 的唯一对齐名单），
    # 不是在这里再写一份。
    _gt_mod = _import_gen_table()
    TABLE1_SRC = {r["run"]: ("supplement_table1.md" if r["run"] in _gt_mod.PAPER_OMIT
                            else "sec_results.tex")
                  for r in load(os.path.join(ROOT, "paper/data/table1.csv"))}
    for r in load(os.path.join(ROOT, "paper/data/table1.csv")):
        k = r["run"]
        if k in NOT_PRINTED:
            continue
        if k in runs_csv:
            # 位数按【正文印的】给：墙钟 1 位、并发 2 位、SLO 1 位
            # （table1.csv 存的是 4 位，直接拿来比会对不上 —— 刚踩过）
            # no-control 那一行的 Conc. 是【百分比】(94.9)，不是并发数 ——
            # 表 I 的脚注专门说明了这一点（2026-09-24 修过一次量纲错）。
            _cc = float(runs_csv[k]["conc"])
            ck("表 I %s 的墙钟&并发&SLO 三连" % k,
               "%.1f & %s & %.1f" % (float(r["wall_min"]),
                                     "%.1f" % _cc if _cc > 10 else "%.2f" % _cc,
                                     float(r["slo_pct"])),
               TABLE1_SRC.get(k, "sec_results.tex"))




    # ---- occupancy.csv 的臂数（正文两处引了「二十三条臂」）----
    occ = load(os.path.join(ROOT, "paper/data/occupancy.csv"))
    ck("occupancy.csv 的臂数", len(occ), "sec_results.tex")

    # ---- tier25.csv：表 II 的每一列（2026-09-24 补上生成器 gen_tier25.py 后纳入）----
    for r in load(os.path.join(ROOT, "paper/data/tier25.csv")):
        # 同上：四列连成一个复合串。单查「5.1」「92.8」这种短值会撞车。
        ck("表 II %s 墙钟&并发&SLO&段SD 四连" % r["run"],
           "%s & %s & %s & %s" % (r["wall_min"], r["conc"], r["slo_pct"], r["seg_sd_pp"]),
           "sec_discussion.tex")

    # ---- gate_attrib.csv 注释行里落定的两个中位数 ----
    # 「两个中位数会随集合变」（§V 的稳健性声明）用的就是这两行；它们只存在于
    # CSV 的注释里，所以单独解析。all_rows_median 这一行是 2026-09-24 才补上的 ——
    # 在此之前正文引用的「every run in that file」两个数在文件里根本查不到。
    ga = open(os.path.join(ROOT, "paper/data/gate_attrib.csv"), encoding="utf-8").read()
    for tag in ("eight_median", "all_rows_median"):
        mt = re.search(r"^# %s.*?valve_pct=([\d.]+),projection_over_pct=([\d.]+)" % tag,
                       ga, re.M)
        if mt:
            ck("gate_attrib %s 阀门" % tag, mt.group(1), "sec_results.tex")
            ck("gate_attrib %s 投影超预算" % tag, mt.group(2), "sec_results.tex")
        else:
            fails.append(("gate_attrib.csv 缺 %s 行" % tag, "-", "sec_results.tex"))

    # ---- §V 里【三条具名闸门臂】的百分比：rg2 / rg3 / rg4 ----
    # 2026-09-26 codex 第 31 轮抓到：这三个数此前**只活在正文里** ——
    # `gate_attrib.csv` 的统计只收跑完的 run，而 rg2（770 步）/rg3（169 步）
    # 被同机争用中止、没有 summary.json，于是被排除，正文引的两个数没有任何文件来源。
    # 这里从 controller.jsonl 现算**同一个判据**（被挡周期里、非 valve、gate_full 为真），
    # 不经过 gate_attrib.csv，所以它与那张表是否重生成无关。
    for _gr, _kw in (("pois200_foyer_rg2", "rg2"), ("pois200_foyer_rg3", "rg3"),
                     ("pois200_foyer_rg4", "rg4")):
        _gp = os.path.join(ROOT, "results/night", _gr, "controller.jsonl")
        if not os.path.exists(_gp):
            continue
        _L2 = _gag_load(_gp)
        _blk2 = [d for d in _L2 if (d.get("waiting_n") or 0) > 0
                 and (d.get("n_admitted") or 0) == 0]
        if not _blk2:
            continue
        _g2 = sum(1 for d in _blk2 if not d.get("valve") and d.get("gate_full"))
        ck_near("§V %s 的 round-gate 百分比" % _kw, "%.1f" % (100.0 * _g2 / len(_blk2)),
                "sec_results.tex", "of blocked cycles", window=300)

    # ---- gate_attrib.csv：foyer_hc 的饿死守卫三件套（§V 用它论证「超预算时只有它能进」）----
    gah = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/gate_attrib.csv"))}
    if "pois200_foyer_hc" in gah:
        r = gah["pois200_foyer_hc"]
        ck("foyer_hc 被强制准入数", r["forced_admits"], "sec_results.tex")
        ck("foyer_hc 总准入数", r["total_admits"], "sec_results.tex")
        # 这两个数**必须一起查**：放行数是 9，单独查「9」在正文里出现 135 次，
        # 等于空转（2026-09-25 --audit 扫出来的）。正文那句话是
        # 「of 3{,}700 such cycles, nine admitted」—— 查这一整串。
        ck("§V 超预算周期数与放行数（复合句）",
           "of %s such cycles, %s admitted"
           % ("{:,}".format(int(r["cycles_over_budget"])).replace(",", "{,}"),
              _NUM9.get(int(r["admitted_while_over"]), "?")),
           "sec_results.tex")
        ck("foyer_hc 被强制准入占比", "%.1f" % (100.0 * int(r["forced_admits"]) / int(r["total_admits"])),
           "sec_results.tex")
    # ⚠ 2026-09-26：§V 引「over every completed run in that file (forty-six of them)」，
    # 而**这个条数此前没人守**（派生量，随 gate_attrib.csv 长大而漂）。
    # ⚠ 2026-09-26：这里原本还有一条 `§V gate_attrib 表里的 run 条数`，与下面
    # （`§V gate_attrib 全量集合规模`）是**同一判据的两份实现** —— 反向测试一次报两条
    # MISS 才发现。已删除（保留更早、锚更稳的那条）。


    # ⚠ 2026-09-27：我一度在这里加了三条「739 / 3.7% / 0.0%」的守卫，
    # **与下面 `§VII 25 档被挡周期数 / 安全阀占比 / 回合闸门占比` 完全重复** ——
    # 那三条从 `gate_attrib.csv` 现读（`blocked_cycles` / `valve_pct` / `round_gate_pct`），
    # 所以 grep「739」查不到它们，我误判成「无出处、无守卫」。已删除。
    # **教训：加守卫之前先按【量】搜一遍现有守卫**（不是按值搜）。


    # ---- §VII 撤回清单里「τ 低了多少」那条（2026-09-27 通读抓到标签错）----
    # 正文原来写「came out low by exactly the **busy** fraction, 36% for cap1」——
    # 而 36.3% 是 **idle** 占比（`decomp.csv` 的 `idle_pct`），busy 是 **63.7%**
    # （`arm_running.csv` 的 `busy_frac` = 0.6371）。机制是对的（τ 低了 36.3% ✓），
    # **错的是标签**。已改成「the fraction of time the engine is idle」并把比值印出来。
    _dc1 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    _ar1 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/arm_running.csv"))}
    if "cap1" in _dc1 and "cap1" in _ar1:
        # ⚠ 窗口是**从锚的起点**算的（`lo, hi = i - window, i + window`），
        # 而这条锚自己就有 38 字符 ⇒ window=40 只覆盖到锚后 2 个字符，值必然落空
        # （假 MISS）。CLAUDE.md 那条「窗口要给足【关键词 + 值】的总长度」。
        ck_near("§VII 撤回清单里 cap1 的那 36%", "%.0f" % float(_dc1["cap1"]["idle_pct"]),
                "sec_discussion.tex", "come out low by exactly the idle fraction", window=70)
        ck_near("§VII 该处的 R̄_all/R̄_busy 比值",
                "%.3f" % (float(_ar1["cap1"]["running_all"]) / float(_ar1["cap1"]["running_busy"])),
                "sec_discussion.tex", "the fraction of time the engine is idle", window=140)

    # ---- §VII 的「var_cap3 有 158 分钟在四条以上并发」（2026-09-27 补）----
    # 这一对是**分子分母同源**的：都取自并发审计的窗口 = metadata 的
    # `finished − started`（实测 270.5 分 → 正文写 **271**），分子是
    # `concurrency.csv` 的 `min_at_ge4`（158.4 → **158**）。
    # ⚠ 正文曾经写 **266**（那是 `steps.jsonl` 的 submit→complete 口径）——
    # **分子分母不同源**；改成 271 才是对的，但那次改动没写明理由，一度看起来
    # 像反向测试的残留值。这里把两个数一起钉住，并注明基准。
    try:
        _mvc = json.load(open(os.path.join(ROOT, "results/night/pois200_var_cap3/metadata.json")))
        _win = (_mvc["finished"] - _mvc["started"]) / 60.0
        _cvc = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/concurrency.csv"))}
        if "pois200_var_cap3" in _cvc:
            ck_near("§VII var_cap3 的四条以上并发分钟数",
                    "%.0f" % float(_cvc["pois200_var_cap3"]["min_at_ge4"]),
                    "sec_discussion.tex", "spent", window=30)
            ck_near("§VII var_cap3 的窗口分钟数（同一基准：metadata finished-started）",
                    "%.0f" % _win, "sec_discussion.tex", "spent", window=30)
    except Exception as _evc:
        fails.append(("§VII var_cap3 的分钟数守卫没跑起来", repr(_evc)[:50],
                      "results/night/pois200_var_cap3"))

    # ---- stall.csv：§V 的「不放行窗口」----
    # ⚠ 2026-09-26 判据极性修正（这是本项目里最重的一次修正，见 gen_stall.py 的 docstring）：
    # 旧判据 (b) 要 `valve` **为真**，而 `valve` 为真 = 阀门**正在挡**（实测：为真的周期
    # 0.5% 放过行、为假的 9.8%）。于是旧判据选出来的「窗口」正是阀门按设计挡住准入的
    # 那些周期，而正文把它们写成「阀门开着、控制器却不放人」—— 把「阀门在工作」
    # 说成了「控制器失灵」。改正后：**恰好一条臂有一个窗口**。
    # 正文现在两头都写，这里也两头都守；旧判据的数在 CSV 的
    # `n_windows_valve_holding` / `old_total_s` 两列里。
    _st = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/stall.csv"))}
    _one = sorted(k for k, r in _st.items() if (r.get("n_windows") or "0").strip() == "1")
    if len(_one) != 1:
        fails.append(("stall.csv 里恰好一个窗口的臂数（正文按「exactly one」写的）",
                      str(len(_one)), "paper/data/stall.csv"))
    else:
        _k = _one[0]
        # 关键词挑【同一行内】的独有短语；窗口要盖住「关键词 + 值」
        _kw = "has a window in which"
        ck_near("§V 正判据下那个窗口的时长", "%.1f" % float(_st[_k]["max_s"]),
                "sec_results.tex", _kw, 420)
        ck_near("§V 正判据下那个窗口占墙钟", "%.2f" % float(_st[_k]["pct_span"]),
                "sec_results.tex", _kw, 460)
        ck_near("§V 正判据下那个窗口的 waiting 中位", _st[_k]["waiting_med"],
                "sec_results.tex", _kw, 240)
    ck_near("§V 那个窗口的恢复走的是饥饿逃生", "starvation escape",
            "sec_results.tex", "has such a window", 340)
    # 旧判据下：出现「段」的臂 —— 恰好一个窗口的那三条 + foyfix
    _old_one = sorted(float(r["old_total_s"]) for r in _st.values()
                      if int(r.get("n_windows_valve_holding") or 0) == 1)
    if _old_one:
        _oa = ", ".join("%.1f" % v for v in _old_one[:-1]) + " and %.1f" % _old_one[-1]
        checks += 1
        if not has(P["sec_results.tex"], _oa):
            # ⚠ 2026-09-26：这一块原来直接 `fails.append`，**退役名单对它无效**
            # ——与「tier='S' 那一支先返回、RETIRED 条目是死的」是同一个坑。
            _w = _retired("§V 旧判据下三条单段臂的时长（升序拼接）")
            if _w:
                # ⚠ 2026-09-27：这一行原来印的是**缩短过的**描述（「…的时长」），
                # 而 MISS 分支印全称（「…的时长（升序拼接）」）—— 于是
                # 「base 的 `--` 集合 vs `NORE=1` 的 MISS 集合逐条对拍」**差一条**，
                # 看起来像一条对不上的退役（实际是同一条、只是两处标签不同）。
                # 判据要机械：两处印同一个串。
                print("  --   %-58s %s（退役：%s）"
                      % ("§V 旧判据下三条单段臂的时长（升序拼接）", _oa, _w))
            else:
                fails.append(("§V 旧判据下三条单段臂的时长（升序拼接）", _oa, "sec_results.tex"))
    _vh = sorted(k for k, r in _st.items() if int(r.get("n_windows_valve_holding") or 0) > 0)
    ck_near("§V 旧判据下出现段的臂数", _NUM9.get(len(_vh), str(len(_vh))),
            "sec_results.tex", "arms show", 200)
    if "foyfix_hc" in _st:
        # ⚠ 数词**不能**放进关键词里 —— 那等于自证（关键词自带 "nine"，值也是 "nine"）。
        # 查「数词 + 臂名」的复合串，值不止是那个数词。
        ck("§V 旧判据下关掉全部节流那条的段数",
           "%s more on the all-throttles-off"
           % _NUM9.get(int(_st["foyfix_hc"]["n_windows_valve_holding"]), "?"),
           "sec_results.tex")
        # ⚠ 读 **old_pct_span**，不是 pct_wall —— 后者是正判据下的占比（这条臂是 0）。
        # 第一版正是读了 pct_wall，于是把 0 拿去查，报出一条 MISS：**守卫也会抄错列**。
        ck_near("§V 旧判据下那条臂的段占墙钟",
                str(int(float(_st["foyfix_hc"]["old_pct_span"]))),
                "sec_results.tex", "row totalling", 40)

    # ---- budget_sweep.csv（Route 3 的两条臂）----
    for r in load(os.path.join(ROOT, "paper/data/budget_sweep.csv")):
        ck("预算扫描 %s 墙钟" % r["run"], r["wall_min"], "sec_results.tex")
        ck("预算扫描 %s SLO" % r["run"], r["slo_pct"], "sec_results.tex")
        ck("预算扫描 %s 的 Δ" % r["run"], r["delta_pp"].lstrip("-"), "sec_results.tex")

    # ---- hitrate.csv ----
    # 论文逐条印的是这十条（§related 的 80.8->32.8 与 host tier 的 80.7/79.6/78.7、
    # §V 的 80.6 与 bres 的 80.2）；其余是 2026-09-24 补进文件、正文未逐条印的臂。
    HIT_PRINTED = {"pois200_cap1", "pois200_cap2", "pois200_cap3_fixed", "pois200_cap4",
                   "pois200_cap5", "pois200_pairB_cap2hc", "pois200_cap3_hc",
                   "pois200_cap4_hc", "pois200_foyer_hc", "pois200_foyer_bres_r2"}
    for r in load(os.path.join(ROOT, "paper/data/hitrate.csv")):
        ck("round-1+ %s" % r["run"], r["observed_round1_pct"],
           tier="P" if r["run"] in HIT_PRINTED else "S")

    # ---- 分段 ε 的**第二条实现**（2026-09-26）--------------------------------
    # 原来那几条 ε 守卫是 `import gen_elasticity_hc.eps` —— 共用定义是对的，
    # 但**如果 `eps` 本身写错，守卫会与它一致地错**。这里就地再算一遍
    # （ln 比值，独立写），与 `elasticity_hc.csv` 的每一段对拍。
    # 另有 `scripts/lab/independent_elasticity_check.py` 是同样的第二次实现，
    # 额外覆盖「拟合 ε」与 R²（可以单独跑，见 NEXT.md）。
    try:
        import math as _m2
        _dehc = os.path.join(ROOT, "paper/data/elasticity_hc.csv")
        _dcm2 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
        _CHAINS = (("device_only", ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]),
                   ("hicache", ["pairB_cap2hc", "cap3_hc", "cap4_hc", "cap5_hc",
                                "cap6_hc", "cap8_hc"]))
        if os.path.exists(_dehc) and _dcm2:
            _bad_seg = []
            for _cfgname, _names in _CHAINS:
                _ref = [r for r in load(_dehc) if r.get("config") == _cfgname]
                _mine = []
                for _a, _b in zip(_names, _names[1:]):
                    _ra = round(float(_dcm2[_a]["running"]), 2)
                    _rb = round(float(_dcm2[_b]["running"]), 2)
                    if _rb <= _ra:
                        continue          # R̄ 倒序 —— 与生成器同样跳过
                    _mine.append((_a, _b,
                                  _m2.log(float(_dcm2[_b]["step_back_ms"])
                                          / float(_dcm2[_a]["step_back_ms"]))
                                  / _m2.log(_rb / _ra)))
                if len(_mine) != len(_ref):
                    _bad_seg.append("%s 段数 %d vs %d" % (_cfgname, len(_mine), len(_ref)))
                    continue
                for (_a, _b, _e), _r in zip(_mine, _ref):
                    if _r["from"] != _a or _r["to"] != _b:
                        _bad_seg.append("%s 段名 %s->%s vs %s->%s"
                                        % (_cfgname, _a, _b, _r["from"], _r["to"]))
                    elif abs(_e - float(_r["epsilon"])) > 0.5e-3 + 1e-9:
                        _bad_seg.append("%s %s->%s 本 %+.4f vs 表 %+.3f"
                                        % (_cfgname, _a, _b, _e, float(_r["epsilon"])))
            checks += 1
            if _bad_seg:
                fails.append(("分段 ε 的第二条实现与 elasticity_hc.csv 不符",
                              "；".join(_bad_seg)[:70], "paper/data"))
            elif VERBOSE:
                print("  OK   分段 ε 的第二条实现与 elasticity_hc.csv 逐段相符")
    except Exception as _e:
        checks += 1
        fails.append(("分段 ε 第二实现守卫没跑起来", repr(_e)[:50], "scripts"))

    # ---- §VII 复现段必须写明「四条独立复算线」（2026-09-26）------------------
    # 这是这份稿子的一条**真实优势**（四条不共享代码的复算线与生成器逐位相符），
    # 而它很容易在下一次压缩里被当成铺陈删掉。守卫只查这句话在不在。
    checks += 1
    if not re.search(r"five checks sharing no code", P.get("sec_discussion.tex", "")):
        fails.append(("§VII 复现段里的「五条独立复算线」被删/改错数",
                      "scripts/lab/independent_*_check.py", "sec_discussion.tex"))
    elif VERBOSE:
        print("  OK   §VII 复现段写明四条独立复算线")

    # ---- 相邻重复的词串（2026-09-26：一次 splice 事故留下的）------------------
    # 事故形态：`...negative columnThe route stays in the negative column on the
    # stronger ground...` —— 我恢复一句话时原文还在，于是半句重复、中间没有空格，
    # PDF 里读成 "columnThe"。
    # **所有数值守卫与排版守卫都看不见它**（不是数字、不产生 Overfull、不改页数），
    # 是中立复核者读出来的。判据：**连续 4 个词的字串原样再出现一次**（忽略大小写与空白）。
    # ⚠ 限度（反向测试实测）：**标点会打断匹配** —— 把一句话整句重复两次（中间有 `. `）
    # 这条守卫**抓不到**（`\w+` 不跨标点）。它抓的是**咬在一起**的那一类（事故的本形）。
    _dup = []
    for _fn, _src in P.items():
        if not _fn.endswith(".tex"):
            continue
        _flat = re.sub(r"\s+", " ", _src)
        _m5 = re.search(r"\b(\w+(?: \w+){3,})\s+\1", _flat, re.I)
        if _m5:
            _dup.append("%s: %s" % (_fn, _m5.group(1)[:40]))
    checks += 1
    if _dup:
        fails.append(("正文里有相邻重复的词串（splice 事故）", "；".join(_dup)[:70], "paper/"))
    elif VERBOSE:
        print("  OK   没有相邻重复的词串")

    # ---- 未定义的缩写「F:xxx」（2026-09-26 视觉复核时发现）--------------------
    # 正文里有五处写着 `\texttt{F:hz0}` / `\texttt{F:t85}` / `\texttt{F:rl99}` ——
    # 这个「F:」前缀**全稿没有定义**（表 I 用的是 `horizon$=$0` 这类标签，
    # `t85`/`rl99` 是裸 run 名）。读者会问 F 是什么。已全改成论文自己的标签。
    _fpre = []
    for _fn, _src in P.items():
        if _fn.endswith(".tex") and re.search(r"\\texttt\{F:", _src):
            _fpre.append(_fn)
    checks += 1
    if _fpre:
        fails.append(("正文又出现未定义的「F:」缩写", "、".join(_fpre), "paper/"))
    elif VERBOSE:
        print("  OK   没有未定义的「F:」缩写")

    # ---- 两条短 run 各丢了几个请求（2026-09-26：独立复算时发现「both finished」
    # 掩盖了「各有一个请求失败」）—— 从 steps.jsonl 的 error 字段现数。
    try:
        _shorts = {}
        for _rn in ("foyer_rg4", "default"):
            _sp3 = os.path.join(ROOT, "results/night", "pois200_" + _rn, "steps.jsonl")
            if not os.path.exists(_sp3):
                continue
            _st3 = [json.loads(l) for l in open(_sp3) if l.strip()]
            _shorts[_rn] = (len(_st3), sum(1 for x in _st3 if x.get("error")))
        if _shorts:
            checks += 1
            # ⚠ 2026-09-26（中立复核）：原来只数 `error` 字段（各 1 条），**解释不了
            # 997 与 999 差 2**。差额来自「出错那一轮之后的轮次再也没发出」。
            # 判据改成**两条都核**：error 条数 == 1，且步数差额 == 出错会话未被服务的轮数。
            _bad3 = []
            for k, (n, e) in _shorts.items():
                _st4 = [json.loads(l) for l in open(
                    os.path.join(ROOT, "results/night", "pois200_" + k, "steps.jsonl")) if l.strip()]
                _err4 = [x for x in _st4 if x.get("error")]
                if e != 1 or len(_err4) != 1:
                    _bad3.append("%s error 条数 %d" % (k, e))
                    continue
                _sid4 = _err4[0]["session_id"]
                _rounds4 = [x["round_idx"] for x in _st4 if x["session_id"] == _sid4]
                _lost4 = 5 - len(_rounds4)          # trace 每条会话 5 轮
                if (999 - n) != _lost4:
                    _bad3.append("%s 步差 %d != 未服务轮数 %d" % (k, 999 - n, _lost4))
            if _bad3:
                fails.append(("两条短 run 的「各丢一个请求」不再成立",
                              "、".join("%s 丢了 %d 个" % (k, _shorts[k][1]) for k in _bad3),
                              "results/"))
            elif VERBOSE:
                print("  OK   两条短 run 各丢了一个会话的尾巴（步差 == 未服务轮数）")
    except Exception as _e:
        checks += 1
        fails.append(("短 run 丢请求数守卫没跑起来", repr(_e)[:50], "scripts"))

    # ---- 独立复算的臂清单必须覆盖表 I 里印出的每一条控制器臂（2026-09-26）------
    # `independent_frontier_check.py` 是「从头再实现一遍」的那条独立线（不 import 生成器）。
    # 它原来只覆盖 foyer 族的 11 条，**漏了独立控制器的两条**；而「一个独立控制器也没
    # 越过」是论文的判决之一 —— 独立线不覆盖它，那条判决就只有一份实现。
    # 这条守卫钉住「覆盖面」：表 I 印出的每条控制器臂都必须在它的 ARMS 里。
    try:
        import importlib.util as _il2
        _sp2 = _il2.spec_from_file_location(
            "_ifc", os.path.join(ROOT, "scripts", "lab", "independent_frontier_check.py"))
        _ifc = _il2.module_from_spec(_sp2); _sp2.loader.exec_module(_ifc)
        _t1p = {r["run"] for r in load(os.path.join(ROOT, "paper/data/table1.csv"))
                if r["run"] not in {"pairA_cap2hc", "aimd2_paper"}}
        _need = sorted(r for r in _t1p
                       if r.startswith("foyer") or r.startswith("aimd") or r == "foyfix_hc")
        _miss2 = sorted(set(_need) - set(_ifc.ARMS))
        checks += 1
        if _miss2:
            fails.append(("独立复算的臂清单漏了表 I 里的控制器臂",
                          "、".join(_miss2)[:60], "independent_frontier_check.py"))
        elif VERBOSE:
            print("  OK   独立复算覆盖表 I 的全部 %d 条控制器臂" % len(_need))
    except Exception as _e:
        checks += 1
        fails.append(("独立复算覆盖面守卫没跑起来", repr(_e)[:50], "scripts"))

    # ---- tier25 那四条的「同代」判据（2026-09-26：表注原来只说「current harness」，
    # 而实验机上还有若干**没有 build metadata** 的 25 档 run（`load25c_*`），
    # 其中最快的 `load25c_cap6_hc` 19.1 分钟比表里的 Foyer 臂还快 —— 读者拿得到工件，
    # 就会问「为什么它不在表里」。表注现在写出可核判据：四条同属记录了 build 哈希的
    # 那一版（`run_matrix.py a8605b1e77d5`），更早的批次不与之可比。
    # ⚠ 2026-09-26（codex r43）：原来只核 `cap3_25` 一条，且文件缺失时整块静默跳过。
    # 表注说的是「四条同属**那一版**」，判据必须**四条都核且哈希相同**。
    _t25_runs = ["pois200_cap2_25", "pois200_cap3_25", "pois200_cap4_25", "pois200_foyer_push_25"]
    _t25_h = {}
    for _tr2 in _t25_runs:
        _mp2 = os.path.join(ROOT, "results", "night", _tr2, "metadata.json")
        if os.path.exists(_mp2):
            _t25_h[_tr2] = (json.load(open(_mp2)).get("code") or {}).get("run_matrix.py")
    checks += 1
    if len(_t25_h) != len(_t25_runs) or len(set(_t25_h.values())) != 1 or not list(_t25_h.values())[0]:
        fails.append(("§VII tier25 那四条不是同一版 harness（或元数据缺失）",
                      str(_t25_h)[:70], "results/night/pois200_*_25"))
    else:
        ck_near("§VII tier25 表注的 harness 哈希", str(list(_t25_h.values())[0])[:12],
                "sec_discussion.tex", "records build hashes", window=120)

    # ---- tier25_old.csv：§VII 的 25 档单变量分解（2026-09-26 补）----------
    # 这五个数此前**没有任何数据文件来源**（只在 9-21 的旧登记与日志里），
    # 而正文引了其中两个（58.4 / 28.8）。已落 `paper/data/tier25_old.csv`。
    # 守卫查**整串**（墙钟 + 加速比同句），免得单个短数字在别处被接住。
    _t25o_p = os.path.join(ROOT, "paper/data/tier25_old.csv")
    if os.path.exists(_t25o_p):
        _t25o = {r["run"]: r for r in load(_t25o_p)}
        if _t25o:
            for _k in ("thr25_base", "thr25_nohw", "thr25_t95", "thr25_push", "thr25_nosf"):
                _r2 = _t25o.get(_k)
                if not _r2:
                    checks += 1
                    fails.append(("tier25_old.csv 少了这条臂", _k, "paper/data"))
                    continue
                ck_near("§VII 25 档 %s 的墙钟" % _k.replace("thr25_", ""),
                        "%.1f" % float(_r2["wall_min"]), "sec_discussion.tex",
                        {"thr25_base": "25-session tier",
                         "thr25_push": "faster} (58.4 to"}.get(_k, "alone is"),
                        window=400)
            # ⚠ 「两根一起」那一格不查百分比：正文写的是「(the pair quoted above)」，
            # 因为 50.6\% 与上一句的「51\% faster」并列会让读者以为两个数打架。
            # ⚠ 2026-09-27 活性审计：这三个百分比原来是**写死的字面量**，
            # 而 `tier25_old.csv` 本来就有 `speedup_vs_base_pct` 列 —— 守卫不读它，
            # 于是数据一变正文就不响。改成现读。
            for _arm, _kw in (("thr25_nohw", "alone is"), ("thr25_t95", "alone 39.7"),
                              ("thr25_nosf", "alone 49.5")):
                _row = _t25o.get(_arm)
                checks += 1
                if not _row:
                    fails.append(("tier25_old.csv 少了这条臂（加速比守卫没法跑）", _arm, "paper/data"))
                    continue
                _pct = "%.1f" % float(_row["speedup_vs_base_pct"])
                ck_near("§VII 25 档单变量的加速比 %s%%" % _pct, _pct + "\%",
                        "sec_discussion.tex", _kw, window=80)
            # 「its repeat lands at 30.1, so that arm's own run-to-run spread is **2.2 pp**」
            # —— 这 2.2 **不是**墙钟差（1.3 分钟）也不是 SLO 差（3.2pp），而是**加速比之差**
            # （`speedup_vs_base_pct` 50.6 与 48.4）。正文对 ✓，但此前**没有守卫**
            # （那一格被有意跳过不查百分比，因为正文写的是「(the pair quoted above)」）。
            _push, _push2 = _t25o.get("thr25_push"), _t25o.get("thr25_push_r2")
            checks += 1
            if not (_push and _push2):
                fails.append(("tier25_old.csv 少了 thr25_push 的重复对（2.2pp 守卫没法跑）",
                              "thr25_push / thr25_push_r2", "paper/data"))
            else:
                _sp = abs(float(_push["speedup_vs_base_pct"]) - float(_push2["speedup_vs_base_pct"]))
                ck_near("§VII 两根一起那条臂的加速比散布", "%.1f" % _sp,
                        "sec_discussion.tex", "run-to-run spread", window=40)

    # ---- tau2_windows.csv：§repro 的两个「同一 run 内」对照 ----
    tw = {r["run"]: [] for r in load(os.path.join(ROOT, "paper/data/tau2_windows.csv"))}
    for r in load(os.path.join(ROOT, "paper/data/tau2_windows.csv")):
        tw.setdefault(r["run"], []).append(r)
    _cap = tw.get("cap1", [])
    if _cap:
        ck("cap1 前 5.5h 的桶中位下界", min(x["tau2_p50_ms"] for x in _cap[:12]), "sec_discussion.tex")
        ck("cap1 前 5.5h 的桶中位上界", max(x["tau2_p50_ms"] for x in _cap[:12]), "sec_discussion.tex")
        for i, x in enumerate(_cap[12:15]):
            ck("cap1 争用后第 %d 桶" % (i + 1), x["tau2_p50_ms"], "sec_discussion.tex")
    # 转折点按【桶序号】取：t85 是第 120 分那一桶（29.8），rl99 是第 270 分那一桶（32.4）
    for _run, _key, _m in (("foyer_t85", "t85", "120"), ("foyer_rl99", "rl99", "270")):
        for x in tw.get(_run, []):
            if x["bucket_min"] == _m:
                ck("%s 转折前桶（第 %s 分）" % (_key, _m), x["tau2_p50_ms"], "sec_discussion.tex")

    # ---- 派生量检查（排名 / 条数 / 跨带）----
    # 2026-09-25 中立子 agent 第 11 轮的结构性结论：检查器只问「这个值在不在正文里」，
    # **不问「旧值还在不在」，也不覆盖派生量** —— 而这一轮的三条 major
    # （图 2 图注的名次 16→18、§VI 的跨带条数 1→2、图 4 图注的四个 pooling）
    # **全部落在那个盲区里**。这一块把「算出来的名次/条数/跨带」也变成检查。

    # (1) 图 2 图注的两个名次（28 条 run 里，default 按 idle 升序第几、按墙钟升序第几）
    _dr = load(os.path.join(ROOT, "paper/data/decomp.csv"))
    if _dr:
        _byidle = sorted(_dr, key=lambda x: float(x["idle_pct"]))
        _bywall = sorted(_dr, key=lambda x: float(x["wall_min"]))
        _names = [x["run"] for x in _byidle]
        if "default" in _names:
            ck_near("图2 图注：default 的 idle 名次", str(_names.index("default") + 1),
                    "sec_model.tex", "idle share")
            ck_near("图2 图注：default 的墙钟名次",
                    str([x["run"] for x in _bywall].index("default") + 1),
                    "sec_model.tex", "duration")
        ck_near("图2 图注：run 的条数", str(len(_dr)), "sec_model.tex", "ordered by total duration")
        # ⚠ **图 2 的纵轴标签必须唯一**。2026-09-25 把图渲出来看才发现：
        # `short()` 删掉 pairA_/pairB_ 前缀后，28 根柱子里有三组重名
        # （三条叫 `foyerhc`、两条叫 `cap2hc`），读者分不出哪根是哪根。
        # **数据对不代表图看得懂** —— 这条守卫把「唯一性」做成机械的。
        # ⚠⚠ 2026-09-28（codex r73 在**只读环境**实测到）：这一段原来 **import `make_figs`**
        # 来拿 `short()` —— 而 `make_figs` 会拉起 **matplotlib**（且要可写缓存），
        # 于是：(a) 只读环境里这条守卫**跑不起来**（还顺带把 `_CHECKS_N` 的计数打乱，
        # 报一条「少了 1 条」）；(b) **AE 文档写着「复现路径只用标准库」是假的**。
        # ⇒ 照本项目自己的惯例改：**由画图的人把标签报出来**（`make_figs.py` 落
        # `paper/figs/.labels.json`），检查器只读 JSON，**不 import 画图脚本**。
        # ⚠ **不许静默吞异常**：第一版写 `except Exception: _labs = []`，而那里
        # 我传的是 `r`（dict）不是 `r["run"]` —— 于是整块**从没执行过**，
        # 而「检查数没涨」是唯一的信号（588 → 588）。CLAUDE.md 有专条：
        # **新加的检查块要 `-v` 跑一次、确认它真的打印了 OK**。
        _lp = os.path.join(ROOT, "paper", "figs", ".labels.json")
        _labs, _mf_err = [], None
        if not os.path.exists(_lp):
            _mf_err = "paper/figs/.labels.json 不存在（重跑 make_figs.py）"
        else:
            try:
                _labs = list(json.load(open(_lp, encoding="utf-8")).get("fig2_decomp.pdf") or [])
            except Exception as _e:
                _mf_err = "%s: %s" % (type(_e).__name__, _e)
            # ⚠ 判**过期**要用**时间戳**，不要拿 `_dr` 的长度比 ——
            # `.labels.json` 装的是**图上真画的那几条**（`DECOMP_KEEP`），
            # 而这里的 `_dr` 是另一个集合 ⇒ 比长度会**假 MISS**（我第一版就是这么写的）。
            _fig2 = os.path.join(ROOT, "paper", "figs", "fig2_decomp.pdf")
            if (not _mf_err and os.path.exists(_fig2)
                    and os.path.getmtime(_lp) < os.path.getmtime(_fig2)):
                _mf_err = ".labels.json 比图旧（是上一版图的标签）"
        if _mf_err:
            fails.append(("图 2 标签唯一性守卫没跑起来（标签清单缺/过期）",
                          _mf_err[:56], "paper/figs/.labels.json"))
        if _labs:
            # ⚠⚠ **这条判据的作用域是「标签互不重名」，不是「标签内容正确」** ——
            # r74 两条线都点到这一点（中立 §2 认为在作用域内、codex §2/§7 认为是缺口）。
            # 明示边界，免得后人把它当成内容对拍：
            #   · 抓得住：三根柱子都叫 `foyerhc` 这一类**重名事故**（历史真发生过）；
            #   · 抓不住：把某个标签改成**另一个仍然唯一**的字符串。
            # 为什么**不**补内容对拍：那需要检查器复现 `make_figs.py` 的挑选逻辑
            # （`DECOMP_KEEP` + 排序），就是本项目栽过的「同一件事两份实现」
            # （CLAUDE.md：codex 第 21 轮四条同形状）。而标签↔柱子的对应**是构造保证**的
            # （`make_figs.py` 里 `_ylabs` 与 `ax.set_yticklabels(_ylabs)` 是同一个列表），
            # 图注又**不枚举**名字、没有第三方可对。剩下的风险面由**条数守卫**兜着：
            # 图注的「seventeen / One bar is hatched」都对着 `.counts.json` 现算的数。
            import collections as _col
            _dup = {k: v for k, v in _col.Counter(_labs).items() if v > 1}
            checks += 1
            if _dup:
                fails.append(("图 2 的纵轴标签重名（读者分不出哪根柱子是哪条）",
                              str(_dup)[:56], "paper/figs/fig2_decomp.pdf"))
            elif VERBOSE:
                print("  OK   图 2 的 %d 个标签互不重名" % len(_labs))

        # ⚠⚠ 2026-09-28（r74 两条线都命中）：`.labels.json` 原来只跟**图 2** 比时间戳，
        # 而 `.counts.json`（承着**三条**条数守卫）**一条时间戳卫兵都没有** ——
        # r74 中立复核实测：`touch -d` 把它改旧到早于图 7 ⇒ **881/0 全绿**。
        # 两者都是 `make_figs.py` 一次运行的产物：图被重生成而 JSON 没跟上（或反过来）时，
        # 元数据描述的是**另一张图**，而上下所有标签/条数守卫都会拿它当真。
        # ⇒ 统一成一条：**两个 JSON 都要不比 `paper/figs/` 下任何一张 PDF 旧**。
        _figd = os.path.join(ROOT, "paper", "figs")
        try:
            _pdfs = sorted(_f for _f in os.listdir(_figd) if _f.endswith(".pdf"))
        except OSError:
            _pdfs = []
        _newest = max([os.path.getmtime(os.path.join(_figd, _f)) for _f in _pdfs] or [0])
        _stale = [_j for _j in (".labels.json", ".counts.json")
                  if os.path.exists(os.path.join(_figd, _j))
                  and os.path.getmtime(os.path.join(_figd, _j)) < _newest]
        checks += 1
        if _stale:
            fails.append(("图的元数据文件比图旧（描述的是上一版图）",
                          "%s 旧于 %s（重跑 make_figs.py）"
                          % ("、".join(_stale), _pdfs[-1] if _pdfs else "?"),
                          "paper/figs/"))
        elif VERBOSE:
            print("  OK   .labels.json / .counts.json 都不旧于任何一张图")

    # (2) §VI ready 时钟的跨带条数：从 arrival_slo.csv 现算
    _as2 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/arrival_slo.csv"))}
    # 2026-09-25 加 foyer_sf0_r2（最接近前沿的臂，ready 时钟下 −0.55→−0.89，
    # 仍在 band 内）。集合从 11 条变 12 条，正文的 eleven/nine 随之改 twelve/ten。
    # ⚠⚠ 2026-09-27：名单原来**写死 13 个名字**，`foyer_hz2_r3` 与 `foyer_scan`
    # 落地后它仍然只数 13 条（算出 2 处跨带，真值 3 处）。这与「生成器的 run 列表
    # 不全」是同一个病，只是这次在守卫里。**改成从 arrival_slo.csv 现算**。
    # ⚠ 同时：原来只查 `-1.0` 一侧 —— `scan` 是**从上往下**跨出 `+1.0` 的，
    # 于是一直没被数进来。**判据的边界两侧要一起核**（本项目早有这一条）。
    _C11 = sorted(k for k in _as2 if k.startswith(("foyer", "foyfix", "aimd")))
    _t1b = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/table1.csv"))}
    _cross = []
    for _k in _C11:
        if _k in _as2 and _k in _t1b and _as2[_k]["delta_ready_pp"] not in ("", "None"):
            _a0 = float(_t1b[_k]["delta_pp"])
            _a1 = float(_as2[_k]["delta_ready_pp"])
            # ⚠ 2026-09-27（codex r48）：下界原来写 `> -1.0`，而 `frontier.classify`
            # 把**恰好 −1.0** 算【带内】（下界是 `delta >= -TIE_PP`）。于是
            # `−0.5 → −1.0` 会**误报**跨带、`−1.0 → −1.1` 会**漏报**跨带。
            # 上界 `> +1.0` 是对的（`classify` 的上界就是 `delta > TIE_PP`）。
            if ((_a0 >= -1.0) != (_a1 >= -1.0)) or ((_a0 > 1.0) != (_a1 > 1.0)):
                _cross.append(_k)
    if _cross:
        # ⚠ 2026-09-27 活性审计：原来是 `ck(..., str(len(_cross)), ...)` —— 值是一位数，
        # 而 `sec_discussion.tex` 里 `"2"` 出现 **122 次** ⇒ **恒真**。改成锚定。
        ck_near("§VI ready 时钟：跨出 ±1pp 带的控制器臂",
                num_words(len(_cross)) + [len(_cross)], "sec_discussion.tex",
                # ⚠ 2026-09-27：锚跟着改写后的句子换（原 `cross out of the` 已不存在）。
                # 锚失配 = 这条检查静默不再检查任何东西。
                "that cross the", window=60)
        # 「N 条移动 <=2.5pp / M 条更多」这两个分组计数此前**零覆盖**，
        # 2026-09-25 实测正文写的是 nine/Two 而真值是 nine/Three
        # （`breshz1_r2` 的 move 是 −3.16，旧 `breshz1` 不超 —— 又是一处落地残留）。
        _mv2 = [(k, float(_as2[k]["move_pp"])) for k in _C11
                if _as2.get(k, {}).get("move_pp") not in (None, "", "None")]
        if _mv2:
            _sm = sum(1 for _, v in _mv2 if abs(v) <= 2.5)
            ck_near("§VI 移动 <=2.5pp 的臂数", num_words(_sm),
                    "sec_discussion.tex", "move by no more than")
            ck_near("§VI 移动 >2.5pp 的臂数", num_words(len(_mv2) - _sm),
                    "sec_discussion.tex", "move more")

    # (2b) §VI 的强主张：「On this clock \emph{no} run is above the line」。
    # 2026-09-27 新增 —— 这句话是**废止替代锚点之后**才成立的（替代锚点让前沿系统性偏低
    # 约 0.5pp，于是 `foyer_scan_r2` 被抬到 +1.51，看起来越过）。它是一条**全称否定**：
    # 只要有一条臂的就绪 Δ 越过 +1.0，句子就假了，而**没有任何数值守卫会响**
    # （旧守卫只数「跨带」的条数，不判「有没有人越线」）。
    _rab = sorted(k for k, v in _as2.items()
                  if v.get("delta_ready_pp") not in ("", "None")
                  and float(v["delta_ready_pp"]) > 1.0)
    if _rab:
        fails.append(("§VI「no run is above the line」（就绪时钟）：实测有 %d 条越线"
                      % len(_rab), "、".join(_rab), "sec_discussion.tex"))
    else:
        ck_near("§VI ready 时钟下无臂越线", "no", "sec_discussion.tex",
                "run is above the line", window=40)

    # (3) 正文引、但此前没有检查守的几个数
    _ip = {r["set"]: r for r in load(os.path.join(ROOT, "paper/data/idle_pooled.csv"))}
    if "all_runs" in _ip:
        ck_near("§III >20s 的段数占比", _ip["all_runs"]["pct_segments_gt20s"],
                "sec_model.tex", "exceed")
        # ⚠ 2026-09-27（中立复核 r48 第 12 条）：**这个数此前没有任何活守卫。**
        # `RETIRED` 里曾有一条 `"idle all_runs median_s"`，理由写「正文明确
        # 『报均值与占比、不报中位』，中位随之不印」—— **理由不实**：
        # `sec_model.tex:23-24` 至今印着「it reads 10.0\,s without \texttt{cap1}
        # and 5.0\,s with it」（`idle_pooled.csv` 的 `all_runs.median_s = 5.00`）。
        # 而且那条退役**是孤儿** —— 全仓库没有任何检查用那个描述（只出现一次）。
        # 本项目的老毛病在这里是**反向**的：退役理由可以很合理，而数还在正文里。
        # 那条孤儿退役已删，改成这条活守卫。
        ck_near("§III 全体池的中位", _ip["all_runs"]["median_s"], "sec_model.tex",
                "without \\texttt{cap1} and", window=80)
    if "minus_cap1" in _ip:
        ck_near("§III 去掉 cap1 后的中位", _ip["minus_cap1"]["median_s"],
                "sec_model.tex", "without \\texttt{cap1} and", window=80)
    _dd5 = load(os.path.join(ROOT, "paper/data/decomp.csv"))
    if _dd5:
        # 这个区间在 §III，不在引言 —— 我第一版把 where 写成了 sec_intro.tex，
        # 得到一条假 MISS（正文里根本没有那个数）。**检查写错地方 = 假 MISS。**
        _ip2 = [float(r["idle_pct"]) for r in _dd5 if r["idle_pct"]]
        ck_near("§III 的空转占比区间上界", "%.1f" % max(_ip2), "sec_model.tex", "spans")
        ck_near("§III 的空转占比区间下界", "%.1f" % min(_ip2), "sec_model.tex", "spans")
    # 摘要的 projection 区间只存在于 projection.csv 的**表头注释**里，不是列 —— 照读
    _pj_txt = open(os.path.join(ROOT, "paper/data/projection.csv"), encoding="utf-8").read()
    _m2 = re.search(r"# main_trace: n=(\d+), min=([\d.]+), max=([\d.]+)", _pj_txt)
    if _m2:
        # ⚠ 2026-09-25 摘要从 1081 词压到 273 词，**不再印 headroom 的这两个数**
        # （§V 仍有）—— 检查改指 §V，不是删掉。
        ck_near("§V projection 区间的上界", _m2.group(3), "sec_results.tex",
                "the occupancy the engine reports", window=300)
        ck_near("§V projection 的条数", _m2.group(1), "sec_results.tex",
                "controller runs that finished", window=200)

    # ---- §V 的三组 projection 读数（都在 projection.csv 的**表头注释**里）----
    # 2026-09-25 独立审查发现：正文这三处（条数/中位/上界）在集合长大到 20/21/45 后
    # **全部过时**，而检查器一条都没覆盖 —— 又是派生量。
    # ⚠ `all_rows` 的**条数**正文不印（只说 "over every finished run … it is 1.01 to
    # 4.13 with a median of 1.59"），所以只查它的区间与中位 —— 给不印的量加检查
    # 只会得到假 MISS（本项目记过这条）。
    # ⚠ **window 必须小**：`main_trace` 与 `main_plus` 两组的 `upper_median`
    # 当前**都是 1.75**，而两处的关键词相距约 60 字符 —— 用默认的 260 会让
    # 两组的窗口互相覆盖，于是改掉一组的正文、另一组的检查仍会通过
    # （codex 第 25 轮实测：把第一组的 1.75 改成 1.74，检查照样过）。
    # ⚠ keyword 要**该组独有、且离值够近**。原来三组的 keyword 分别是
    # 「upper median of / once the second trace / over every finished run」，
    # 而 `twenty` 离第一个有 ~100 字符、`4.13/1.59` 离第三个有 ~110 字符 ——
    # window 一收到 60 就全变成假 MISS。现在按**各组独有的短语**重选：
    for _tg, _kw, _with_n in (("main_trace", "it ranges 1.32 to", True),
                              # 正文对 plus 集合只印区间与中位（条数只说「its size」）
                              ("main_plus_second_trace_arm", "once the second trace", False),
                              ("all_rows", "it is 1.01", False)):
        _m4 = re.search(r"# %s: n=(\d+), min=([\d.]+), max=([\d.]+), upper_median=([\d.]+)"
                        % _tg, _pj_txt)
        if not _m4:
            # **不静默跳过**：projection.csv 的表头注释少了这一组，等于这组
            # 数字**完全没人守**。原来直接 `if _m4:` 就过去了（codex 第 25 轮指出）。
            fails.append(("projection.csv 表头缺 %s 行" % _tg, "-", "sec_results.tex"))
            continue
        if _m4:
            if _with_n:
                # 条数在「the N controller runs that finished」处，离中位那句更远，
                # 所以它单用一个该组独有的 keyword。
                ck_near("§V projection %s 的条数" % _tg, num_words(_m4.group(1)),
                        "sec_results.tex", "controller runs that finished", window=120)
            ck_near("§V projection %s 的中位" % _tg, _m4.group(4),
                    "sec_results.tex", _kw, window=60)
            ck_near("§V projection %s 的上界" % _tg, _m4.group(3),
                    "sec_results.tex", _kw, window=60)
    # ---- §V 的 occupancy 条数与 Spearman ----
    # 「the twenty-three arms we have almost identically, Spearman rho=0.95」——
    # cap5_hc 入表后是 24 行、rho 实测 0.9670。两个数此前都没人守。
    _occ_rows = [r for r in load(os.path.join(ROOT, "paper/data/occupancy.csv"))
                 if r["occ_p50_pct"] not in ("", "None") and r["running_mean"] not in ("", "None")]
    if len(_occ_rows) >= 5:
        def _rk(v):
            _o = sorted(range(len(v)), key=lambda i: v[i]); _r = [0] * len(v)
            for _pos, _i in enumerate(_o):
                _r[_i] = _pos + 1
            return _r
        _a = _rk([float(r["occ_p50_pct"]) for r in _occ_rows])
        _b = _rk([float(r["running_mean"]) for r in _occ_rows])
        _n = len(_a); _mx = sum(_a) / _n; _my = sum(_b) / _n
        _rho = (sum((x - _mx) * (y - _my) for x, y in zip(_a, _b))
                / (sum((x - _mx) ** 2 for x in _a) * sum((y - _my) ** 2 for y in _b)) ** 0.5)
        ck_near("§V occupancy 的条数", num_words(len(_occ_rows)),
                "sec_results.tex", "rank the")
        ck_near("§V occupancy 的 Spearman", "%.2f" % _rho, "sec_results.tex", "Spearman")

    # (4) 2026-09-25 暴露的【派生量】盲区 —— 六条正文数此前一条检查都没有。
    # 起因：`breshz1_r2` 落地（310.9→257.0 分）与 `cap5_hc` 入表，decomp 的集合
    # 28→29 条，于是「范围 / 名次 / 分组计数」全变了，而 MISS **一个都没报**。
    # 本项目记过这条：检查器的系统性盲区是【派生量】。
    if _ip:
        _ms = [float(r["mean_s"]) for r in _ip.values()]
        _ps = [float(r["pct_idle_time_in_gt20s"]) for r in _ip.values()]
        ck_near("§III pooling 的 mean 区间", "%.1f--%.1f" % (min(_ms), max(_ms)),
                "sec_model.tex", "move by little across the")
        ck_near("§III pooling 的 >20s 占比区间", "%.1f--%.1f" % (min(_ps), max(_ps)),
                "sec_model.tex", "move by little across the")
        if "all_runs" in _ip:
            ck_near("§III all_runs 的 mean", _ip["all_runs"]["mean_s"],
                    "sec_model.tex", "exceed")
    _ga = load(os.path.join(ROOT, "paper/data/gate_attrib.csv"))
    if _ga:
        # 正文写的是英文词（forty-five），而且它是**集合规模**，随实验增长。
        ck_near("§V gate_attrib 全量集合规模", num_words(len(_ga)),
                "sec_results.tex", "over every")
    _at = load(os.path.join(ROOT, "paper/data/attribution.csv"))
    if _at:
        _cls = collections.Counter(r["class"] for r in _at)
        ck_near("§V 归因：内存没用满的条数", num_words(_cls["内存没用满"]),
                "sec_results.tex", "are attributed")
        ck_near("§V 归因：残差条数", num_words(_cls["残差（只能报观测）"]),
                "sec_results.tex", "are residuals")

    # ---- §VI「控制器 artifact」段：四条断言（2026-09-28 通读，此前**零守卫**）----
    # 起因：这段是承重的（支撑「修订与争用分不开」），而里面四条断言**没有一条**被
    # 机械盯着 —— 哈希个数、仓库副本在不在里面、「most」是不是真多数、
    # 「那个副本下的四条 run 全被标记」都是**派生量**，数据一动就可能变假。
    # 逐条现算（2026-09-28 实测：4 个哈希 / 仓库那份不在其中 / 最大哈希 62/100 /
    # `d692ab11f396` 恰好 4 条且四条全被标记 ⇒ 四条全成立）。
    try:
        _hs = collections.Counter()
        for _d in glob.glob(os.path.join(ROOT, "results", "night", "*", "metadata.json")):
            try:
                _h = (json.load(open(_d, encoding="utf-8")).get("code") or {}).get(
                    "controller_budget3.py")
            except Exception:
                continue
            if _h:
                _hs[_h] += 1
        if _hs:
            # ⚠ 窗口**必须窄**：`ck_near` 是对称窗口，默认 260 会把同段别处的数也收进来
            # —— 实测：把 four 改成 five 后，它仍被 "…are all **four** runs recorded under…"
            # （同一段、约 130 字符之后）接住 ⇒ **假通过**。收到 15 字符后只认紧邻的那个数。
            ck_near("§VI 控制器脚本的不同哈希数", num_words(len(_hs)),
                    "sec_discussion.tex", "different hashes of our", window=15)
            _repo = os.path.join(ROOT, "scripts", "controller_budget3.py")
            _repoh = hashlib.md5(open(_repo, "rb").read()).hexdigest()[:12]
            checks += 1
            if _repoh in _hs:
                fails.append(("§VI「none of them the repository copy」不再成立",
                              _repoh + " 出现在记录里", "sec_discussion.tex"))
            _top, _n = _hs.most_common(1)[0]
            checks += 1
            if _n * 2 <= sum(_hs.values()):
                fails.append(("§VI「the copy most of our arms ran under」不再是多数",
                              "%d/%d" % (_n, sum(_hs.values())), "sec_discussion.tex"))
            # 「那个副本下的四条 run 全部被审计标记」—— 现算「全部被标记」的哈希
            _allflag = []
            _cd = os.path.join(ROOT, "paper", "data", "concurrency.csv")
            if os.path.exists(_cd):
                _fl = {r["run"].replace("pois200_", "") for r in load(_cd)
                       if "CONTEST" in str(r.get("verdict", "")).upper()}
                # 哈希 → run 列表（只扫一次 metadata，别在哈希循环里重复 glob）
                _hr = {}
                for _d2 in glob.glob(os.path.join(ROOT, "results", "night", "*", "metadata.json")):
                    try:
                        _h3 = (json.load(open(_d2, encoding="utf-8")).get("code") or {}).get(
                            "controller_budget3.py")
                    except Exception:
                        continue
                    if _h3:
                        _hr.setdefault(_h3, []).append(
                            os.path.basename(os.path.dirname(_d2)))
                for _h2, _rs2 in _hr.items():
                    if _rs2 and all(r.replace("pois200_", "") in _fl for r in _rs2):
                        _allflag.append((_h2, len(_rs2)))
                checks += 1
                if len(_allflag) != 1 or _allflag[0][1] != 4:
                    fails.append(("§VI「all four runs recorded under one of those copies（被标记）」",
                                  str(_allflag)[:48], "sec_discussion.tex"))
                # ⚠⚠ 2026-09-28（r68 codex 第 12 项②）：上面这条只核了**数据**里「四条」，
                # **没有把正文那个数词绑住** —— 把末句改成 `all five` 全检查器 MISS 不增。
                # ⇒ 把数词也钉在**现算值**上（不是写死的 4）。
                elif _allflag:
                    ck_near("§VI「那个副本下 N 条 run 全被标记」的**数词**",
                            num_words(_allflag[0][1]), "sec_discussion.tex",
                            "runs recorded under one of those", window=40)
    except Exception as _e:
        checks += 1
        fails.append(("§VI 控制器 artifact 段的守卫没跑起来", repr(_e)[:50], "scripts"))

    # ---- §V 归因：**第三类**（τ 无配对可比确认）的条数（2026-09-28 通读）----
    # 前两类各有一条守卫，**这一类一条都没有** —— 而正文下一句点名的就是它
    # （「two have a $\tau$ no matched comparison can confirm」）。
    if _at:
        # ⚠ 同样把窗口收窄：数字在关键词**之前**约 16 字符
        # （"…; two have a $\tau$ no matched comparison can confirm"），
        # 默认 260 会让同段别处的 "two" 接住它。
        # 正文点到具体数据文件时，文件名要有守卫（codex r69 §10：改成错名字不报）
        ck_near("§V 逐臂读数指向的数据文件", "attribution.csv", "sec_results.tex",
                # ⚠ 窗口要 ≥ 关键词长度 + 间隔 + 值长度：关键词 28 字符、值在后面 9 字符
                # ⇒ 25 不够（窗口从关键词**起点**算），实测假 MISS。
                "The per-arm readings are in", window=70)
        ck_near("§V 归因：τ 无配对可比确认的条数",
                num_words(_cls["步成本更高（但对照的在跑数不可比）"]),
                "sec_results.tex", "no matched comparison can confirm", window=25)
    _dcr = load(os.path.join(ROOT, "paper/data/decomp.csv"))
    if _dcr and any(r["run"] == "default" for r in _dcr):
        # 图 2 图注的两个【名次】。集合一变它们就变，而且是英文序数词。
        _ri = [r["run"] for r in sorted(_dcr, key=lambda r: float(r["idle_pct"]))].index("default") + 1
        _rw = [r["run"] for r in sorted(_dcr, key=lambda r: float(r["wall_min"]))].index("default") + 1
        ck_near("图2 图注：no-control 的 idle 升序名次", num_words(_ri),
                "sec_model.tex", "on idle share")
        ck_near("图2 图注：no-control 的 duration 名次", num_words(_rw),
                "sec_model.tex", "on duration")

    # ---- §A100（第二配置）：五条读数、ε 两卡八段、判决、池子比 ----
    # 2026-09-25 这一节进正文时按清单补的检查（见
    # docs/finding_a100_first_result_20260925.md 第十一节的待办清单）。
    # ---- A100 无控制基线的「试过几次」（2026-09-26 通读时发现内部矛盾）----------
    # §VII 原来写「two attempts at a clean re-run of that baseline **have since failed**」，
    # 而 §VI 写的是「**The clean re-run** we attempted afterwards did not produce one」
    # （单数），实测也只有**一次**重跑（`a100_default_r2`）跑过并失败；
    # 第三次尝试当时还在排队。**同一件事在稿子里两个数，检查器一处没报。**
    # 现在两处都按「两次都落在共租用下（一次仅作 indicative、一次不可用）」写。
    # 判据：从镜像数 A100 无控制基线的 attempt 数，与 §VII 的措辞对齐。
    _ait = sorted(d for d in os.listdir(os.path.join(ROOT, "results", "night"))
                  if d.startswith("a100_default"))
    checks += 1
    if len(_ait) < 2:
        fails.append(("A100 无控制基线的 attempt 少于两条（§VII 写着 Both attempts）",
                      "、".join(_ait) or "（无）", "results/night"))
    else:
        # ⚠ 2026-09-27（r50 A1）：正文改成「Both **completed** attempts」—— §VI 的
        # 「the three baseline attempts」数的是**起过 server 的次数**（第三次因池子对不上
        # 没产生任何读数），§VII 的「Both」数的是**拿到读数的那两次**。两个数都对，
        # 但同一篇稿子里看着像矛盾，所以这里把限定词写进去、锚跟着改。
        ck_near("§VII A100 基线的两次尝试", "Both completed attempts at that baseline",
                "sec_discussion.tex", "the no-control arm is the presence", window=200)
    for _bad in ("attempts at a clean re-run of\nthat baseline have since failed",
                 "have since failed, so we treat the comparison"):
        checks += 1
        if _bad in P.get("sec_discussion.tex", ""):
            fails.append(("§VII 又出现「两次重跑都已失败」的旧说法", _bad[:40], "sec_discussion.tex"))

    # ---- §VI「three of the seven A100 runs」的条数（2026-09-26 通读时发现无守卫）----
    # 这是一个**派生条数**：A100 的 run 数会随扫描扩展而变，而句子里的「七」
    # 只有人读得出来（数值守卫只看池子那几个数）。判据：从 a100.csv 现数
    # `a100_*` 行数 == 7，且池子不等于 nominal 983,728 的行数 == 3。
    _a1p0 = os.path.join(ROOT, "paper/data/a100.csv")
    if os.path.exists(_a1p0):
        _a1rows = [r for r in load(_a1p0) if str(r.get("run", "")).startswith("a100_")]
        _off = [r["run"] for r in _a1rows if r.get("pool_tokens") and int(r["pool_tokens"]) != 983728]
        checks += 1
        if len(_a1rows) != 7 or len(_off) != 3:
            fails.append(("§VI 的「three of the seven A100 runs」不再成立",
                          "A100 行数 %d（正文 seven），非满池 %d（正文 three）"
                          % (len(_a1rows), len(_off)), "paper/data/a100.csv"))
        elif VERBOSE:
            print("  OK   §VI 的 A100 条数：7 条 run，其中 3 条非同满池")

    _a1p = os.path.join(ROOT, "paper/data/a100.csv")
    if os.path.exists(_a1p):
        _a1 = {r["run"]: r for r in load(_a1p)}
        # 表 II 的四行（两卡 × cap4/cap5；另有 cap1 一行）
        # 表 II 的六行：用**整行复合串**（R̄ & 占用 & 兑现）查 —— 单查一个数
        # 太容易在表里撞车，而 `has()` 的 ` & ` 通路会放宽两侧空白，正好对表格行。
        # ⚠ 第一版我用的是自己编的 keyword（"six point five" 之类），正文里根本
        # 没有那些短语，十五条检查**全部落进次要档** = 等于没守（2026-09-25 自查）。
        for _r in ("a100_cap1", "a100_cap4", "a100_cap5", "cap1", "cap4", "cap5"):
            if _r not in _a1:
                continue
            _x = _a1[_r]
            # ⚠ 表格里的百分号是 LaTeX 的 `\%`，复合串必须照抄 —— 少一个反斜杠
            # 就是六条假 MISS（2026-09-25 第一版这么写的）。
            ck("§A100 表 II 的 %s 行" % _r,
               "%.4f & %.1f\\%% & %.1f\\%%" % (float(_x["Rbar_busy"]),
                                               float(_x["occ_p50_pct"]),
                                               float(_x["realized_frac"]) * 100),
               "sec_xtrace.tex")
        # 池子比与两个池子值
        if "a100_cap2" in _a1 and "cap2" in _a1:
            _ratio = float(_a1["a100_cap2"]["pool_tokens"]) / float(_a1["cap2"]["pool_tokens"])
            ck_near("§A100 池子比", "%.2f" % _ratio, "sec_xtrace.tex", "the 3090", window=200)
        # ε：两卡的每一段（带符号！）
        _ae = load(os.path.join(ROOT, "paper/data/a100_elasticity.csv"))
        # ⚠ **只查正文列出的段**。A100 节的 ε 表是挑段展示（每卡 3 段），
        # 而 CSV 有 7 段（3090 四段 + A100 三段）—— 遍历全部会得到两条**假 MISS**
        # （3090 的 cap2→cap3_fixed 在 §IV 正文引过、由 elasticity.csv 那段守；
        #  A100 的 cap2→cap3 不引）。**检查的集合要与正文的集合一致。**
        # ⚠ 2026-09-26 深扫落地后**正文的表扩了**：A100 多了 cap5→cap16 与
        # cap16→cap8 两段（后者 ε=+1.49，是 A100 唯一穿过 1 的一段）。
        # 集合要与正文一致 —— 这次是正文大了，清单要跟上。
        _shown = {("cap1", "cap2"), ("cap3_fixed", "cap4"), ("cap4", "cap5"),
                  ("a100_cap1", "a100_cap2"), ("a100_cap3", "a100_cap4"),
                  ("a100_cap4", "a100_cap5"), ("a100_cap5", "a100_cap16"),
                  ("a100_cap16", "a100_cap8")}
        for _r in _ae:
            if (_r["frm"], _r["to"]) not in _shown:
                continue
            # ε 表每行是「机器 & 段 & R̄ 区间 & ε」—— 用区间拼复合串足以唯一确定
            # 一行，且不依赖我在正文里用了什么措辞。
            # ⚠ **必须写 `\\to`**：Python 源码里的单反斜杠 `\t` 是 **TAB 转义**，
            # 而正文文件里的 `$\to$` 是**字面的两个字符**（文件内容不经 Python 转义）。
            # 写成单反斜杠，`_rng` 就含一个 tab，与正文永远不匹配 —— 而
            # `repr` 会把 tab 显示成 `\t`，看起来跟 `\to` 一模一样，肉眼极难发现。
            # 判据是 **len**：`1.00 $\to$ 1.27` 是 15 字符，含 tab 则 14（2026-09-25 踩到）。
            # ⚠ 2026-09-26：分段区间表在合并两节时被删（codex 的取舍方案点了它），
            # ε 的值仍在正文。**唯一恢复的是末段**（`3.22 to 3.41`），因为它承载
            # 「小分母、只读成 crossing 不读成速率」那条限定 —— 所以这一条单独守，
            # 描述不写成「§A100 ε …」以免被上面那条 catch-all 退役规则吃掉。
            if _r["frm"] == "a100_cap16":
                ck("§A100 末段的 ε 区间（承载小分母限定）",
                   "%s to %s" % (_r["r0"], _r["r1"]), "sec_xtrace.tex")
                ck_near("§A100 末段的 ε 值", "%+.2f" % float(_r["epsilon"]),
                        "sec_xtrace.tex", "small-denominator", window=200)
            else:
                _rng = "%s to %s" % (_r["r0"], _r["r1"])
                ck("§A100 ε %s→%s 的区间" % (_r["frm"], _r["to"]), _rng, "sec_xtrace.tex")
    # §IV 那句**论证核心**：「+2.87 sits between +0.46 and +0.48」—— 它说明
    # 2.87 是小分母产物。这三个值必须同在。
    # ⚠ 要**单独**守：`+0.48` 在正文里出现三次（本句、本句后半、§IV 另一处的
    # realhr 列表），改掉一处其余仍在 ⇒ 主检查会命中 ⇒ **互相掩护**
    # （2026-09-25 反向测试实测：把 `gives ε = +0.48` 改成 `+0.84`，检查不报）。
    # ⚠ **必须查整条短语，不能只查那两个数**。只查 `+0.48` 的话，正文里另外两处
    # （本句后半、§IV 另一处的 realhr 列表）仍含它 ⇒ 检查照样命中
    # （2026-09-25 反向测试实测：把这对值改成 `+0.46 and +0.84`，单值检查不报）。
    # 这正是 checker 里别处已经总结过的：**复合串比单值可靠得多**。
    # ⚠ 这句原来的措辞是「$+2.87$ **sits between** $+0.46$ and $+0.48$」——
    # **数值上错的**：2.87 远大于两者。本意是「在**序列**上被它们夹着」。
    # codex 第 26 轮抓到。已改成 `flanked ... in the sequence`，检查跟着改。
    # 改了写法之后，守这几处：`+2.87` 本身（此前**从没被查过**）、以及 τ₂ 那串读数。
    # ⚠ 子 agent 实测：单独把 `$\epsilon = +2.87$` 改成 `+0.87` 时 0 MISS ——
    # 因为 `ck_near` 会遍历每个锚词位置，三个 ε 值相隔 30--100 字符、彼此落在
    # 对方的窗口里（**互相掩护**）。所以这里用**该处独有的短语**做锚。
    ck_near("§IV 的 +2.87", "+2.87", "sec_criterion.tex", "something real happens", window=200)
    ck_near("§IV 的 τ₂ 弹性 +4.3", "+4.3", "sec_criterion.tex", "per-request", window=200)
    ck_near("§IV 的 τ₂ 单调串", "22.7, 24.5, 25.7, 26.8, 27.6,\n29.0",
            "sec_criterion.tex", "monotonically", window=200)

    # 交叉点 1.7344 必须与 gen_a100 的判决同源
    _x2 = os.path.join(ROOT, "paper/data/a100_elasticity.csv")
    if os.path.exists(_x2):
        ck_near("§A100 的 3090 交叉点", "1.7344", "sec_xtrace.tex", "crossing", window=300)

    # ---- §III/§Discussion 的几个**区间端点**（2026-09-25 codex 第 26 轮抓到全过时）----
    # 这些是区间，集合一长大端点就变；此前一条检查都没有。
    _ev2 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/eviction.csv"))}
    _rx2 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/reuse.csv"))}
    _hc2 = [k for k, v in _rx2.items() if v["family"] == "hicache"]
    if _hc2 and all(k in _ev2 for k in _hc2):
        def _rng2(f):
            _v = sorted(f(k) for k in _hc2)
            return _v[0], _v[-1]
        _lo, _hi = _rng2(lambda k: float(_ev2[k]["host_hit_M"]))
        ck_near("§III host 命中区间", "%.1f--%.1f" % (_lo, _hi), "sec_model.tex", "the host serves")
        # ⚠ 2026-09-26：这句原来是「the device misses more … at every point」＋一个区间，
        # **而它不成立**：`cap5_hc` 的设备 miss 19.0M **低于** device-only `cap5` 的 20.7M
        # （codex 第 40 轮抓的；中立复核只发现「另一侧的数没了」，没发现断言本身错）。
        # 现在正文改成**成对比较 + 明写反向**，守卫也随之改成查那几对。
        ck_near("§III cap3 的设备 miss 成对比较",
                "%.1f\,M against" % float(_ev2["cap3_hc"]["dev_miss_M"]),
                "sec_model.tex", "where we can pair them", window=160)
        ck_near("§III cap5 上反向的那对",
                "against the device-only run's %.1f\,M" % float(_ev2["cap5"]["dev_miss_M"]),
                "sec_model.tex", "at a cap of five", window=120)
        _lo, _hi = _rng2(lambda k: float(_ev2[k]["evicted_M"]) - float(_ev2[k]["uncached_M"]))
        ck_near("§III 驱逐与重算之差区间", "%.1f--%.1f" % (_lo, _hi), "sec_model.tex", "gap between them")
        _lo, _hi = _rng2(lambda k: float(_rx2[k]["reuse_frac"]))
        ck_near("§Discussion reuse_frac 区间", "%.4f--%.4f" % (_lo, _hi),
                "sec_discussion.tex", "range of the twenty", window=120)
    # idle 的**最快端点**（cap6_hc 落地后从 7.3 变 6.3）
    _dc2 = load(os.path.join(ROOT, "paper/data/decomp.csv"))
    if _dc2:
        _v = sorted((float(r["idle_pct"]), r["run"]) for r in _dc2 if r["idle_pct"])
        ck_near("§III idle 的区间下界", "%.1f" % _v[0][0], "sec_model.tex", "it spans", window=80)
        ck_near("§III idle 的区间上界", "%.1f" % _v[-1][0], "sec_model.tex", "it spans", window=80)
        # ⚠ 2026-09-27 独立复核抓到：**同一个量的第二个区间此前无守卫**。
        # 正文写「6.5% to 36.7% against the request wall clock」——分母换成**墙钟**
        # （decomp 的 wall_min）后真值是 **6.4--42.5**（36.7 是 `cap1` 的值，而最大
        # 是 `foyfix_hc` 的 42.5）。**这是「同一个量在正文里出现两次、只守了一处」
        # 的又一例**。判据与上面那条同源，只换分母。
        _w2 = sorted((100 * float(r["idle_min"]) / float(r["wall_min"]), r["run"])
                     for r in _dc2 if r.get("idle_min") and r.get("wall_min"))
        ck_near("§III idle 按墙钟的区间下界", "%.1f" % _w2[0][0], "sec_model.tex",
                "against the request wall clock", window=60)
        ck_near("§III idle 按墙钟的区间上界", "%.1f" % _w2[-1][0], "sec_model.tex",
                "against the request wall clock", window=60)
    # hitrate：cap5/6/8 的三个读数。
    # ⚠ 2026-09-26：这三个数原来在 §VII 的「tracks the plan」那句里，压缩把那句删了；
    # 值现在在 §IV（独立复核指出「把 host 侧命中率的下降幅度收窄」会让机制显得更强，
    # 所以把集合写清了：三个点在 80.7--78.7、加 cap5 到 77.3、全家最低 53.1）。
    # 守卫随之改指 sec_model.tex。
    _ht2 = {r["run"].replace("pois200_", ""): r for r in load(os.path.join(ROOT, "paper/data/hitrate.csv"))}
    for _k in ("cap5_hc", "cap8_hc"):
        if _k in _ht2:
            ck_near("§IV round-1+ %s" % _k, _ht2[_k]["observed_round1_pct"],
                    "sec_model.tex", "and holds at", window=460)

    # ---- 前沿锚点：`frontier.py` 的硬编码 FRONT vs 从数据**现算**的包络 ----
    # 2026-09-25：`cap6_hc` 落地后，`make_figs.py` 现算的包络自动把它当最左端点，
    # 而 `FRONT` 是硬编码的、漏了它 ⇒ 图 1 与表 I/前沿定义不一致（codex 第 26 轮抓到）。
    # 那次是**手工**补上的；这条检查把两边钉住，下次数据变会自动报。
    import importlib.util as _iu
    _fp = os.path.join(ROOT, "scripts", "lab", "frontier.py")
    _spec = _iu.spec_from_file_location("_frontier_check", _fp)
    _fm = _iu.module_from_spec(_spec)
    try:
        _spec.loader.exec_module(_fm)
        _front_names = [n for _, _, n in _fm.FRONT]
        # 现算包络：**与 make_figs.fig_frontier 同一规则** —— 用 `runs.csv` 的
        # `family` 列筛静态点（**不能用 run 名前缀**：`pairB_cap2hc` 不以 `cap`
        # 开头，而它才是包络上那一点，用前缀筛会漏掉它、把 device-only 的 `cap2`
        # 当成端點 —— 2026-09-25 第一版就是这么写错的）。
        _rr2 = load(os.path.join(ROOT, "paper/data/runs.csv"))
        _cand = sorted(((float(r["wall_min"]), float(r["slo_pct"]), r["run"])
                        for r in _rr2
                        if r["family"].startswith("static") and int(r["steps"]) >= 995))
        _env, _best = [], -1.0
        for _w, _sl, _rn in _cand:
            if _sl > _best:
                _env.append(_rn); _best = _sl
        checks += 1
        if sorted(_env) != sorted(_front_names):
            fails.append(("前沿锚点：FRONT 与现算包络不一致",
                          "FRONT=%s / 包络=%s" % (_front_names, _env), "scripts/lab/frontier.py"))
        elif VERBOSE:
            print("  OK   前沿锚点 FRONT 与现算包络一致（%d 个）" % len(_front_names))
    except Exception as _e:
        print("  · 前沿锚点检查没跑成：%s" % _e)

    # ---- **动态下界 59.7 的逐处锚定** ----
    # 子 agent 独立实测：把它在六处（摘要/§I/§III/§IV/§Discussion/§VII 图注）**逐处**
    # 改回 72.8，每一处都是 0 MISS —— 唯一守着它的是全稿搜的 `ck`，只要六处还剩一处
    # 写着 59.7 就永远通过。这一轮改的头条数字，守卫强度反而低于静态下界的 87.9
    # （那条有两处 ck_near）。**一个值在正文里出现几处，就要锚几处。**
    if _hc2 and all(k in _rx2 for k in _hc2):
        _low = "%.1f" % (min(float(_rx2[k]["realized_frac"]) for k in _hc2) * 100)
        # 每个文件用它**那一处独有**的短语；`sec_model.tex` 里有两处（§III 开头与
        # §III 尾段的回归句），各锚一条。窗口收到 200，免得跨句命中。
        for _w0, _k0 in (
                         ("sec_intro.tex", "the low end is"),
                         ("sec_model.tex", "host-tier runs that completed"),
                         ("sec_model.tex", "host-tier caps above and at"),
                         ("sec_criterion.tex", "realizes"),
                         ("sec_discussion.tex", "never falls below"),
                         ("sec_xtrace.tex", "the main trace's runs stay at")):
            if os.path.exists(os.path.join(ROOT, "paper", _w0)):
                ck_near("host-tier 动态下界 %s" % _w0, _low, _w0, _k0, window=200)
    # ---- 「最低的那条是谁」的身份检查 ----
    # §III 那句原本写「the lowest is the arm that disables every throttle」——
    # **身份与机制都错**（最低的是 cap8_hc，一条静态 cap；驱逐最多的也是它）。
    # 这句话不是「某个数错了」，是「某个数指向了错的对象」，检查器此前零覆盖。
    if _hc2 and all(k in _rx2 for k in _hc2):
        _lowest = min(_hc2, key=lambda k: float(_rx2[k]["realized_frac"]))
        # 正文的写法是 `\texttt{cap8}+HC`（只有 cap8 在 texttt 里，`+HC` 在外面）
        _lab2 = "\\texttt{%s}+HC" % _lowest.split("_")[0]
        ck_near("§III 最低 run 的身份", _lab2, "sec_model.tex", "the lowest", window=60)

    # ---- **身份/计数**类（checker 的盲区：不是「某数错了」而是「某数指向错对象」）----
    # 子 agent 第 12 轮实测：把这四处改坏，检查器一处都不报。
    _dcm = load(os.path.join(ROOT, "paper/data/decomp.csv"))
    _t1m = load(os.path.join(ROOT, "paper/data/table1.csv"))
    if _dcm and _t1m:
        # 最快的 run（§V「The configuration that finishes fastest」）
        _fast = min(_dcm, key=lambda r: float(r["wall_min"]))["run"]
        _lab3 = {"cap6_hc": "\\texttt{cap6}+HC", "cap4_hc_r2": "\\texttt{cap4}+HC"}.get(
            _fast, "\\texttt{%s}" % _fast)
        ck_near("§V 最快的 run 的身份", _lab3, "sec_results.tex", "finishes fastest", window=120)
        # §III 拟合的 run 条数：5 device-only + 4 host-tier + 5 controller = 14
        ck_near("§III 拟合的 run 条数", num_words(14), "sec_model.tex",
                "runs we fitted", window=60)
        ck_near("§III 拟合里的 host-tier 条数", num_words(4), "sec_model.tex",
                "runs we fitted", window=120)
    # §IV 覆盖控制器区间的是**三个**配置（不是六个）
    ck_near("§IV 覆盖控制器区间的配置数", num_words(3), "sec_criterion.tex",
            "that span the controllers' range", window=60)

    # ---- **关键表不许为空** ----
    # 2026-09-25 实际发生过：`gen_elasticity_hc.py` 中途抛异常，而
    # `open(out,"w")` 在 write 之前就截断了文件 → `elasticity_hc.csv` 成了空表。
    # 后果是**检查数从 476 静默掉到 472**（按行循环不执行），没有任何提示。
    # 这条把「表为空」变成一条响亮的 MISS。
    for _fn0 in ("elasticity_hc.csv", "a100_elasticity.csv", "table1.csv", "decomp.csv",
                 "reuse.csv", "eviction.csv", "occupancy.csv", "runs.csv",
                 "arm_running.csv", "idle_pooled.csv", "stall.csv", "hitrate.csv"):
        _p0 = os.path.join(ROOT, "paper", "data", _fn0)
        checks += 1
        if not os.path.exists(_p0) or not load(_p0):
            fails.append(("关键表为空或缺失（生成器可能中途崩了）", _fn0, "paper/data"))

    # ---- **摘要**（2026-09-25 从 1081 词压到 273 词）：它现在引的每个数都要锚住 ----
    # 压缩时把归因统计、headroom、动态下界等都挪进了正文（正文里都有检查），
    # 摘要只留主线 —— 那主线上剩的这几个数**必须**守住，否则摘要飘了没人知道。
    # ε 的**两个口径**（模型一致 / 逐请求），正文 §criterion 与摘要都用它们。
    # 定义在这里一次、两处共用：下面既用它守 ε 本身，也用它推「加 10% 并发买到
    # 多少吞吐」。**同源是必须的** —— 各写一份的话，改了 ε 而忘了改吞吐端点，
    # 检查器不会响（本项目「两个脚本算同一个量必须共用定义」那条）。
    # ⚠ 这两个数**现算**，不硬编码（原来写死 0.38/0.61）。2026-09-26 独立复核指出
    # 它们**贴边**：两位小数口径给 0.3768 / 0.6079，六位小数口径给 0.3738 / 0.6047
    # —— 后者印出来是 0.37 / 0.60。也就是说「正文写 0.38」这件事**依赖 R̄ 取两位
    # 小数这个约定**，而那个约定原先只声明覆盖【分段】弹性、没覆盖拟合。
    # 现在两边都算出来：拟合值守正文，六位小数值守刚加的披露句。
    _caps5 = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]
    _dcm = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    _rum = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/reuse.csv"))}

    def _fit_eps(xs, ys):
        import math as _m
        X = [_m.log(a) for a in xs]; Y = [_m.log(b) for b in ys]
        mx, my = sum(X) / len(X), sum(Y) / len(Y)
        sl = sum((a - mx) * (b - my) for a, b in zip(X, Y)) / sum((a - mx) ** 2 for a in X)
        r2 = 1 - sum((b - (my + sl * (a - mx))) ** 2 for a, b in zip(X, Y)) / \
            sum((b - my) ** 2 for b in Y)
        return sl, r2

    _eps2 = _fit_eps([float(_dcm[c]["running"]) for c in _caps5],
                     [float(_dcm[c]["step_back_ms"]) for c in _caps5])
    _epr2 = _fit_eps([float(_dcm[c]["running"]) for c in _caps5],
                     [float(_dcm[c]["step_perreq_ms"]) for c in _caps5])
    _eps6 = _fit_eps([float(_rum[c]["Rbar_busy"]) for c in _caps5],
                     [float(_dcm[c]["step_back_ms"]) for c in _caps5])
    _epr6 = _fit_eps([float(_rum[c]["Rbar_busy"]) for c in _caps5],
                     [float(_dcm[c]["step_perreq_ms"]) for c in _caps5])
    _EPS_MODEL, _EPS_REQ = round(_eps2[0], 2), round(_epr2[0], 2)

    # 正文的 0.38 / 0.61 必须真的等于两位小数口径的拟合值（不是抄来的数）
    ck_near("§criterion 拟合 ε（模型自洽，两位小数口径）", "%.2f" % _EPS_MODEL,
            "sec_criterion.tex", "least-squares fit", window=200)
    ck_near("§criterion 拟合 ε（逐请求，两位小数口径）", "%.2f" % _EPS_REQ,
            "sec_criterion.tex", "least-squares fit", window=200)
    ck_near("§criterion R²（逐请求）", "%.2f" % _epr2[1], "sec_criterion.tex",
            "least-squares fit", window=250)
    # 六位小数口径的读数：**必须披露**，否则复算的人会拿到 0.37/0.60 而以为正文错
    for _v, _d in (("%.2f" % _eps6[0], "六位小数口径的拟合 ε（模型自洽）"),
                   ("%.2f" % _epr6[0], "六位小数口径的拟合 ε（逐请求）")):
        ck_near(_d, _v, "sec_criterion.tex", "at six decimals the", window=120)
    _ab = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
                    P["main.tex"], re.S)
    if _ab:
        _at = _ab.group(1)
        checks += 1
        # ⚠ 2026-09-26：**口径改了**。原来数的是 `_at.split()` —— 那是**含 LaTeX 命令**
        # 的原始串，而 `\overline{R}`/`$f^{1-\epsilon}$` 这类各算一个「词」，
        # 于是它数出 316 而**排版出来是 322**，上限 320 因此形同虚设（322 > 250 才是问题）。
        # 现在按【排版口径】数：剥掉命令、`$`、花括号。上限也收到 **265**
        # （IEEEtran 的建议是 150--250；我们留一点余量给公式符号）。
        _at_plain = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", _at)
        _at_plain = _at_plain.replace("$", " ").replace("{", " ").replace("}", " ")
        _n_at = len(_at_plain.split())
        if _n_at > 265:
            fails.append(("摘要词数（排版口径）", "%d（上限 265）" % _n_at, "main.tex"))
        elif VERBOSE:
            print("  OK   摘要 %d 词（排版口径，上限 265）" % _n_at)

    # ---- §V 表 I 的 caption 词数：**只守上界**（r54 复核 D2 加的）-------------
    # 为什么加（三条）：
    #   1. 这个数**曾经真的坏过**：caption 长到 **471 词**时整个浮动体比 `\textheight`
    #      高出 **124.85pt**，底部三行（两条 AIMD）**不在页面上**，而当时唯一的排版
    #      守卫是「0 Overfull」——`Float too large` 与 `Overfull \hbox` 是两回事，
    #      所以一直是绿的（2026-09-26 才补上 `Float too large`）。
    #   2. 那次修法就是把 caption 收到 46 词（列定义留 caption，脚注与指针移进表后
    #      Notes）。**那是一个有意选定的状态，而没有任何东西在守它** —— 本项目
    #      已经记过这条：「一个『众所周知的好状态』如果不是每次都由脚本重新算出来的，
    #      它就已经过期了」。
    #   3. 成本一条检查；而 `Float too large` 只在**已经放不下**时才响，那时已经把
    #      内容切掉了。词数是**更早**的信号。
    #
    # ⚠⚠ **判据是上界，不是等式。** 写成 `== 46` 会把任何一次合法的措辞调整
    # （加一个 `pp`、换一个引用）判成 MISS —— 本项目有专条教训：
    # **守卫写死正文措辞 = 它挡住正确的修改**（那条锚写死 "One point in Fig." 的守卫
    # 就是这么坏的）。上界 70 给当前值（44 词）留足 59% 余量，而 471 词那种回归
    # 一进门就被抓住。
    #
    # 口径与摘要那条**逐字相同**（剥命令、`$`、花括号后 `split()`）—— 两条一起改。
    _CAP_MAX = 70
    # ⚠⚠ 2026-09-27（r55 复核）：正则原为 `\\caption\{` —— **只认无选项参数的那种**。
    # 合法的 `\caption[Short]{Long caption ...}` 会让 `re.search` **整个匹配不上**，
    # 于是 `_capm is None`、检查**连数都不数就跳过**：沙箱实测同为 84 词的 caption，
    # 普通写法报 854 项/1 MISS，加一个 `[short]` 后变成 **853 项/0 MISS** ——
    # 守卫**静默消失**，连检查计数都少 1（这一项是 `checks += 1` 在 `if _capm` 里面）。
    # 这是本项目「假通过通道」的又一例，方向与 `\cite{perbank24}` 那次相同。
    # 现与第 4771 行 `_caption_of()` 的图注路径**用同一套形状**（可选 `*`、可选 `[...]`）。
    #
    # ⚠⚠ 2026-09-27（同一轮，第二次踩）：这条正则的锚点是 `\label{tab:runs}`，而
    # 我紧接着把 `\label{}` 加进了 `strip_cites` ⇒ 锚点被剥掉 ⇒ `_capm is None`
    # ⇒ **守卫静默跳过、`checks` 少 1**（854 → 853）。与上面那个 `\caption[short]`
    # 绕过是**同一个失效模式**（守卫以「匹配不到就跳过」的方式消失），只是路径不同：
    # 上一次是正则太窄，这一次是**输入被上游洗掉了**。
    # ⇒ 结构定位的一律读 `_PSTRUCT`（只剥注释的那一份），不读 `P`。
    # ⚠ `\s*` 而不是 `\s*\n\s*`（2026-09-27，r56 中立复核 9）：原来要求 `\label` 必须在
    # **下一行**，而 `\caption{...}\label{tab:runs}` **同一行**是合法且常见的写法 ——
    # 那样写会触发下面那条 `assert`，**整套 854 项检查一项都不跑**（rc=1）。
    # 判据（要抓的是「形状变了」）不依赖换行，所以放宽。
    _capm = re.search(r"\\caption\*?\s*(\[[^\]]*\])?\s*\{(.*?)\}\s*\\label\{tab:runs\}",
                      _PSTRUCT["sec_results.tex"], re.S)
    # ⚠⚠ 2026-09-27（r56 codex 复核 9）：这里原来用的是 `assert _capm` —— **不行**。
    # `python -O` 会把断言整个删掉，于是「匹配不到」又变回**静默跳过**：
    # codex 沙箱实测 `-O` 下检查数 **854 → 853**、表注检查一声不响地消失。
    # **用断言守「不许静默」是自相矛盾的**（断言本身就是可以被关掉的东西）。
    # 也不能用 `raise` 中止整套（中立复核 9 指出：那样「格式一改，854 项一项都不跑」）。
    # ⇒ 正确做法是**把它变成一条 MISS**：既不静默（计数不降、报告里看得见），
    #   也不中止（其余 853 项照跑）。「我定位不到我的锚点」本身就是一次失败。
    checks += 1
    if not _capm:
        fails.append(("§V 表 I 的 caption 守卫**没能定位**（形状变了？）",
                      "`\\caption...{...}` 后紧跟 `\\label{tab:runs}` 没匹配上", "sec_results.tex"))
    else:
        _capl = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", _capm.group(2))
        _capl = _capl.replace("$", " ").replace("{", " ").replace("}", " ")
        _n_cap = len(_capl.split())
        if _n_cap > _CAP_MAX:
            fails.append(("§V 表 I 的 caption 词数（上界 %d）" % _CAP_MAX,
                          "%d 词" % _n_cap, "sec_results.tex"))
        elif VERBOSE:
            print("  OK   §V 表 I 的 caption %d 词（上界 %d）" % (_n_cap, _CAP_MAX))

    # ---- supplement：**论文指向它**（2026-09-28 收到 1 处总指向），缺了就是投稿缺陷 ----
    # 判据不是「文件在不在」，而是**论文承诺的每一类内容都有对应的一节**。
    # 为什么：`grep -rn "supplement" paper/sec_*.tex` **曾经**有 11 处，每一处都是一个
    # **对审稿人的承诺**（「读数在 supplement 里」）。只查文件存在，等于没查那 11 句。
    _sup = os.path.join(ROOT, "paper", "supplement.tex")
    # ⚠⚠⚠ 2026-09-27（r59 中立复核 9）：**判据原来是「关键词在不在文档里」——
    # 那是不够的。** 复核者逐节删掉 11 节试了一遍：**只有 6 节会报 MISS，5 节静默通过**，
    # 因为那些关键词在别处也出现（`independent` 在文档里 7 次、`co-tenancy` 3 次、
    # `idle decomposition` 2 次、`version history` 在 Scope 段就有）。
    # ⇒ 判据收紧成：**关键词必须出现在某一节的【标题】里**。
    #   这才是「承诺的那一类内容有对应的一节」，而不是「这个词在文档里出现过」。
    # ⚠⚠ 2026-09-28（r69 两条线）：这里原来硬编码「正文指向它 11 次」+ 11 组正文原话。
    # 正文把指向收到 **1 处**（§VI Reproducibility）之后，那些旧条目里 **9 组已不在正文** ——
    # 守卫照常印 OK（它只按**补充材料的节标题**判），但打印出来的描述与正文不符，
    # 将来报 MISS 时会引用正文里已不存在的句子。
    # ⇒ 改成按**现在的事实**：唯一那处总指向承诺了四类内容，补充材料必须有对应章节。
    # 三元组 = （给失败信息用的名字, 说明, **要在某个节标题里出现的词**）。
    _SUP_PROMISES = [
        ("逐臂读数", "per-run readings", "per-arm attribution"),
        ("全表", "the full run table", "full run table"),
        ("审计取证", "the audit forensics", "retractions"),
        ("版本史", "the controller revision history", "version history"),
    ]
    # ⚠⚠ 2026-09-28（r70 两条线）：`_SUP_PROMISES` 只看**补充材料的节标题** ⇒
    # 把正文那句总指向**整句删掉**之后它照旧全绿（「锚失配 ⇒ 该检查静默不再检查任何东西」）。
    # ⇒ 先钉住**前提**：正文里必须真的有那处总指向。
    checks += 1
    # ⚠⚠ 2026-09-28（r71 codex §9）：原来查**两个独立关键词** ⇒ 把整句删掉、
    # 别处还留着「collected in」「supplementary document」就照样通过。
    # ⇒ 改成**一整句短语**（空白当 `\s+`，容忍源码硬换行）。
    _pdl = _src_of("sec_discussion.tex")
    if not re.search(r"collected\s+in\s+one\s+\n?\s*supplementary\s+document",
                     _pdl.replace("\n", " ")):
        fails.append(("正文里那处补充材料总指向不见了（而守卫还在查补充材料）",
                      "应以「正文不再指向它」处置，或把这条守卫退役", "paper/"))
    elif VERBOSE:
        print("  OK   正文那处补充材料总指向在（且补充材料覆盖它承诺的四类内容）")
    checks += 1
    if not os.path.exists(_sup):
        fails.append(("supplement.tex 不存在 —— 而正文指向它",
                      "每一处都是一个对审稿人的承诺", "paper/"))
    else:
        # ⚠ 变量名**必须**避让：`_st` 在本函数后面已经是**另一个东西**（一个 dict，
        # 被 `fifo_out_of_order` 那段用）。我第一版就叫 `_st`，把它覆盖成字符串 ⇒
        # 检查器在 5609 行崩掉（`'str' object has no attribute 'items'`）。
        # **崩溃比静默好**，但这类「局部变量撞车」在 6000 行的函数里迟早会再来 ——
        # 所以这里用**带前缀的长名**，别用 `_st` / `_t` / `_m` 这种短名。
        _sup_txt = open(_sup, encoding="utf-8").read()
        # **只在节标题里找**（见上面那段注释）
        _sup_heads = " || ".join(re.findall(r"\\section\{([^}]*)\}", _sup_txt)).lower()
        _miss = [w for _, _, w in _SUP_PROMISES if w.lower() not in _sup_heads]
        if _miss:
            fails.append(("supplement 没有覆盖正文承诺的内容", "、".join(_miss), "supplement.tex"))
        elif VERBOSE:
            print("  OK   supplement 覆盖正文那处总指向承诺的 %d 类内容（每一类都在某个【节标题】里）" % len(_SUP_PROMISES))
    # ⚠⚠⚠ **supplement 的排版卫兵**（2026-09-27，r59 中立复核 1 —— 这是本轮最实的一处缺陷）。
    # 主论文的三条排版卫兵（页数 / Overfull / Float too large）**读的是 `main.log`**，
    # 而 supplement 是**独立编译的文档** ⇒ **它一个卫兵都没有**。
    # 后果实测：交付的 `supplement.pdf` 有 **4 处 Overfull**（305.4 / 97.8 / 113.7 / 45.8 pt），
    # 14 列那张表的**最右四列被裁在纸外** —— 而 `566 of 566`、`147.5941` 那组读数
    # **正是正文 §A100/§VI 引用的**。**没有任何东西会响。**
    # ⇒ 读 `supplement.log`，与主论文同口径。
    _slog = os.path.join(ROOT, "paper", "supplement.log")
    checks += 1
    if os.path.exists(_slog):
        _sl = open(_slog, encoding="utf-8", errors="replace").read()
        _sof = re.findall(r"Overfull \\hbox \(([0-9.]+)pt too wide\)", _sl)
        _sft = _sl.count("Float too large")
        if _sof or _sft:
            fails.append(("supplement 有排版溢出（最右列会被裁在纸外）",
                          "Overfull %d 处（最大 %s pt）、Float too large %d"
                          % (len(_sof), max(_sof) if _sof else "-", _sft),
                          "paper/supplement.log"))
        elif VERBOSE:
            print("  OK   supplement 无排版溢出（Overfull 0、Float too large 0）")
    else:
        fails.append(("缺 paper/supplement.log（排版卫兵没跑起来）", "-", "paper/"))
    # ---- supplement 的**可数主张**（2026-09-27，r62 复核抓到三条同形的缺陷之后补的）----
    # ⚠⚠ 背景：r62 在**已交付的** supplement 里抓到三条内容缺陷，形状完全相同 ——
    # **一个可数的集合被手写进 supplement，而那个集合能从 CSV 现算**：
    #   ① 「Fourteen of the main-trace runs and two of the second-workload」——14 是**总数**不是 main 的数；
    #   ② 「it is the **only** such reading we kept」——实为三条；
    #   ③ 「the **twenty-six** host-tier runs」——该族实为 28 条。
    # **论文里对应位置的守卫都在，但它们在 `sec_*.tex` 里；supplement 是独立文档，一个都没有。**
    # ⇒ 这里给 supplement 补上**同一套 `ck_near`**（锚在 supplement 自己的措辞上）。
    if os.path.exists(_sup):
        _SUPT = os.path.basename(_sup)
        # ① 被 flag 的 run：**总数**与按 trace 的拆分（源：concurrency.csv 的 verdict）
        _cg = load(os.path.join(ROOT, "paper/data/concurrency.csv"))
        _flag = [r for r in _cg if r.get("verdict") == "CONTESTED"]
        # ⚠ 主 trace 的判据是「**含** `pois200`（但属变负载那一族的除外）」——
        # 不是「以 `pois200_` 开头」：两条 `_failed_4lane_pois200_*` 也属主 trace，
        # 第一版按前缀筛把它们漏掉了（算出 10 而不是 12）。
        _fmain = [r for r in _flag if "pois200" in r["run"]
                  and "pois200_var" not in r["run"]]
        _fvar = [r for r in _flag if r["run"].startswith("pois200_var_")]
        ck_near("supplement 被 flag 的 run 总数",
                num_words(len(_flag)) + [len(_flag)], _SUPT, "runs are flagged", window=60)
        ck_near("supplement 被 flag 的主 trace 条数",
                num_words(len(_fmain)) + [len(_fmain)], _SUPT, "of the main trace", window=40)
        ck_near("supplement 被 flag 的第二负载条数",
                num_words(len(_fvar)) + [len(_fvar)], _SUPT, "second workload", window=60)
        # ② 池子偏短的 run 条数（源：a100.csv 的 pool 列）
        # ⚠ `a100.csv` **混着 3090 的 run**（池 101432）—— 第一版没按机器筛，算出 8。
        _ap = [r for r in load(os.path.join(ROOT, "paper/data/a100.csv"))
               if r.get("machine", "").lower().startswith("a100")
               and r.get("pool_tokens") and r["pool_tokens"] != "983728"]
        ck_near("supplement 第二台机器上非标称池子的条数",
                num_words(len(_ap)) + [len(_ap)], _SUPT, "came up off the nominal", window=40)
        # ③ 「我们有两用数据的 host-tier run」条数（源：reuse.csv 的 hicache 族）
        _hc = [r for r in load(os.path.join(ROOT, "paper/data/reuse.csv"))
               if r.get("family") == "hicache"]
        ck_near("supplement host-tier（两用数据）的条数",
                num_words(len(_hc)) + [len(_hc)], _SUPT, "host-tier runs we have two-use", window=60)

    # ⚠⚠⚠ **可数主张的【覆盖】守卫**（2026-09-27，r62 之后补 —— 关的是**类**，不是实例）。
    # 背景：r62 在 supplement 里抓到三条内容缺陷，形状相同 ——
    # **一个可数的集合被手写进去，而那个集合能从 CSV 现算**。
    # 我随后补的五条守卫只覆盖**那三个具体实例**；复核者指出这一类**还会再产生**。
    #
    # ⇒ 判据：**把 supplement 里所有的「数词 + 复数名词」短语扫出来并钉住**。
    #   新增一处就报 —— 那一刻必须做两个决定之一：**给它配一条守卫**，或
    #   **明确写进下面的接受清单**（说明它为什么不需要守，例如它是模型名、页数、
    #   或纯叙述性的时间长度）。
    # ⚠ 这条**不是**「这些数都对」的证明 —— 它保证的是**没有一处可数主张是悄悄进来的**。
    if os.path.exists(_sup):
        # ⚠⚠⚠ 2026-09-27（r63 中立复核 3）：**这个抓取器原来写的是「所有的」，
        # 而它抓不到大多数常见句型。** 复核者注入四种形态，**全部静默通过**：
        #   `We ran nine ablations on this trace.`（`{0,3}` 贪婪吞词、**不回溯**）
        #   `Nine ablations were run.` / `twenty-six host-tier runs completed the trace`
        #   `nine\,ablations`（没有归一化）/ `9 ablations`（**阿拉伯数字不在规则内**）
        # 峰值只有 19 条 —— 而交付正文里至少还有 `Fourteen runs are flagged`、
        # `killed four runs outright`、`2 runs` 等**没被抓到**。
        #
        # ⚠ 最讽刺的一点：**项目自己的图注解析器 `_cap_n`（第 5176 行）早就做对了全部四项**
        #   —— 剥 `\mbox{}`/`\text{}` 宏、把 `\,`/`~` 换成空、认连字符与去连字符写法、
        #   **认阿拉伯数字**。我写这个新守卫时一条都没继承。**同一类文本两个解析器，
        #   一个修好了，新写的那个没继承** —— 这正是本项目的「第二份实现」那条。
        # ⇒ 现在做**同一套归一化**，并换掉贪婪匹配：**逐个数字 token 往右看最多 4 个词，
        #   其中任何一个是复数名词就记下**（不做贪婪回溯，就不会漏）。
        # ⚠⚠⚠ 2026-09-27（r63 中立复核 3）：**判据必须与机制相符。**
        # 这个抓取器原来的注释写着「**所有的**数词 + 复数名词」——而它抓不到常见的句型
        # （复核者注入四种，全部静默通过：`We ran nine ablations on this trace.`、
        # `Nine ablations were run.`、`nine\,ablations`、`9 ablations`）。
        # 我随后连调了三版想「抓全」，**每一版都引入新的假报**（把表格单元格、
        # `\usepackage{...}`、`$101{,}432 \pm 20$` 都算成可数主张）——
        # 因为**这类扫描本质上是启发式**，写成「全部」就是又一次「声称强于机制」。
        #
        # ⇒ **判据收窄到它能真正保证的范围**，并把范围写在这里：
        #   · **只扫散文**（剥掉 `tabular`/`landscape` 环境、导言区、所有 LaTeX 命令）
        #     ⚠ **行内数学 `$...$` 没有单独剥**（r64 codex 注入 `$\text{nine ablations}$`
        #     会报）—— 这是**已知的边界**，不是「只扫散文」的例外被忽略。
        #   · **只认词形数词**（`fourteen` / `twenty-six`），**不认阿拉伯数字** ——
        #     数据表里几乎全是阿拉伯数字，认它们只会淹掉信号；
        #     而 r62 抓到的三条缺陷**全是词形**（`Fourteen` / `twenty-six` / `only`）。
        #   · 归一化照抄 `_cap_n`：剥宏、把 `\,`/`~` 换成空、认连字符与去连字符写法。
        #     ⚠ **与 `_cap_n` 有一处【有意的】不同**：扫描器额外把
        #     `\texorpdfstring{A}{B}` 折成 `A`（见下），因为它**数次数**；
        #     而 `_cap_n` 只取**第一个**匹配，两个参数都留着也无害。
        #   · **不做贪婪回溯**：逐个数字 token 往右看最多 4 个词，任一是复数名词就记下。
            #     ⚠ **机制是「长度>3 且以 `s` 结尾」**，不是真正的复数判断 ⇒ **不规则
            #     复数漏**（r65 复核构造：`We ran four criteria on this trace.` 静默通过）。
            #     这是**已知边界**，写在注释里，而不是留给下一个复核者发现。
        _prose = re.sub(r"\\begin\{tabular\}.*?\\end\{tabular\}", " ", _SUP_SRC[0], flags=re.S)
        _prose = re.sub(r"\\begin\{landscape\}.*?\\end\{landscape\}", " ", _prose, flags=re.S)
        _prose = _prose.split(r"\begin{document}", 1)[-1]
        # ⚠⚠⚠ 2026-09-28（r65 codex 复核 3）：`\texorpdfstring{A}{B}` 的**两个参数
        # 都会留在文本里** ⇒ 同一个短语被数**两次**（PDF 里只显示一次）⇒ **假 MISS**，
        # 而假 MISS 会让人去改**对的**正文。判据：先把它折成**第一个**参数
        # （PDF 里可见的就是那个）。⚠ 只处理**不含嵌套花括号**的简单参数。
        _prose = re.sub(r"\\texorpdfstring\s*\{([^{}]*)\}\s*\{[^{}]*\}", r" \1 ", _prose)
        _prose = re.sub(r"\\[a-zA-Z]+\*?", " ", _prose)
        _prose = re.sub(r"\\(?:mbox|hbox|text|textrm|textit|textbf|mathrm|emph)\s*\{", "", _prose)
        _norm = _prose.replace("{", "").replace("}", "")
        _norm = re.sub(r"\\[,;:! ]|~", "", _norm)
        # **只认词形**（不含 `|[0-9]+`）
        _wl = (r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
               r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
               r"thirty|forty|fifty|sixty|seventy|eighty|ninety)"
               r"(?:[-\s]?(?:one|two|three|four|five|six|seven|eight|nine))?")
        _found = {}
        _hits = []
        _toks = re.findall(r"[A-Za-z][A-Za-z-]*", _norm)
        _isnum = re.compile(r"^(?:" + _wl + r")$", re.I)
        for _i, _t in enumerate(_toks):
            if not _isnum.match(_t):
                continue
            for _j in range(1, min(5, len(_toks) - _i)):
                _n2 = _toks[_i + _j]
                if (len(_n2) > 3 and _n2.endswith("s") and not _n2.endswith("ss")
                        and _n2.lower() not in ("is", "was", "has", "does", "this", "its", "as")):
                    _ph = (" ".join(_toks[_i:_i + _j + 1])).lower()
                    _found[_ph] = _found.get(_ph, 0) + 1
                    _hits.append(_ph)
                    break
        # **接受清单**：这些可数主张**不需要数据守卫**（模型名 / 叙述性时长 /
        # 已由别的守卫覆盖 / 论文自身的结构性数字）。**新增一处不在单上就报。**
        # ⚠ 这份清单是**手工维护**的：它的作用是逼每一次新增可数主张都做一次显式决定，
        #   而不是让某个数字悄悄进来。
        _OK_CARD = {
            "eight static caps": 1,
            "five and a half hours": 1,
            "five checks": 1,
            "five independent checks": 1,
            "five quantities": 1,
            "five quantities the paper turns": 0,
            "four and a half hours": 1,
            "four columns": 1,
            "four distinct hashes": 1,
            "four runs": 2,
            "fourteen runs": 1,
            "one earlier versions": 1,
            "one of the": 0,
            "one of the data files": 1,
            "one of those copies": 1,
            "one reservation applies": 1,
            "one run of cycles": 1,
            "one trace rows": 1,
            "seven retractions": 1,
            "six unused-memory rows": 1,
            "ten seconds": 1,
            "three affects": 1,
            "three and a half hours": 1,
            "three attempts": 1,
            "three baseline attempts": 1,
            "three denominators": 1,
            "three files": 2,
            "three or more others": 1,
            "three runs": 1,
            "three scan rows": 1,
            "three times": 2,
            "three within-run comparisons": 1,
            "twenty-eight host-tier runs": 1,
            "twenty-seven controller runs": 1,
            "two checks": 1,
            "two completion-counted tables": 1,
            "two errors": 1,
            "two files": 1,
            "two horizon runs": 1,
            "two measurement methods": 1,
            "two neighbours": 1,
            "two of the": 0,
            "two of the generators": 1,
            "two places": 1,
            "two produced readings": 1,
            "two readings": 1,
            "two rows": 1,
            "two single-flight-off runs": 1,
            "two tables": 1,
            "two tables whose content depends": 0,
        }
        # ⚠ `twenty-seven controller runs`（正文 §V 与 supplement 都写）——
        # 与 `build_supplement.py` 标记投影表用的是**同一个判据**（`metadata.trace` + 跑完）。
        # ⚠ 同上：`x == x` 对**字符串**恒真 ⇒ 显式转 float 判 NaN。
        def _notnan_pj(x):
            try:
                return float(x) == float(x)
            except (TypeError, ValueError):
                return False
        _pj = load(os.path.join(ROOT, "paper/data/projection.csv"))
        _RRn = os.path.join(ROOT, "results", "night")
        def _trm(run):
            try:
                return os.path.basename(json.load(
                    open(os.path.join(_RRn, run, "metadata.json"))).get("trace") or "")
            except Exception:
                return "?"
        _n27 = sum(1 for r in _pj
                   if _trm(r.get("run", "")) == "replay_pois200_l04.csv"
                   and _notnan_pj(r.get("ratio"))
                   and os.path.exists(os.path.join(_RRn, r.get("run", ""), "summary.json")))
        ck_near("supplement 主 trace 上跑完的控制器 run 条数",
                num_words(_n27) + [_n27], _SUPT, "controller runs that finished", window=60)
        # ⚠⚠ 2026-09-27（r64 codex 复核 8）：**清单原来是「短语级」而非「出处级」** ——
        # 复核者注入 `We ran three runs`（`three runs` 已在清单里）⇒ **静默通过**。
        # ⇒ 判据加上**出现次数**：一个已接受的短语**在新语境里多出现一次**，
        #   也是「新增了一处可数主张」，必须做显式决定。
        _new = sorted(set(_found) - set(_OK_CARD))
        # ⚠⚠ 2026-09-28（r65 复核 D1）：判据原文说「次数**变了**也报」，而实现只比较
        # **出现在 `_found` 里的键** ⇒ **1→0（短语被删掉）不报**。⇒ 改成**双向**：
        # 遍历并集，缺的一方按 0 计。钉 0 = 「当前不应出现，出现即报」。
        _cnt_bad = sorted(k for k in (set(_found) | set(_OK_CARD))
                          if _found.get(k, 0) != _OK_CARD.get(k, 0))
        checks += 1
        if _new:
            fails.append(("supplement 里出现了**没被接受的可数主张**（给它配守卫，**或在 _OK_CARD 里登记它和它的次数**）",
                          "、".join(_new[:5]), "supplement.tex"))
        elif _cnt_bad:
            fails.append(("已接受的可数主张**出现次数变了**（在新语境里复用 = 新增一处主张）",
                          "、".join("%s 现 %d 次(钉 %d)" % (k, _found.get(k, 0), _OK_CARD.get(k, 0))
                                    for k in _cnt_bad[:5]), "supplement.tex"))
        elif VERBOSE:
            print("  OK   supplement 的 %d **种**可数主张全在已接受清单里（去重后）" % len(_found))

    # supplement 的 PDF 必须比它的 .tex 新（否则上传的是旧的）
    _spdf = os.path.join(ROOT, "paper", "supplement.pdf")
    checks += 1
    # ⚠⚠ 2026-09-27（r62 中立复核）：判据原来只查 `exists` + mtime ⇒
    # **一个 0 字节的 `supplement.pdf` 也能全程 861 项 / 0 MISS / rc=0 交付**
    # （复核者实测）。与打包闸门那边是同一个洞的**两处**。
    # ⇒ 必须查「**非空的常规文件**」。
    if os.path.exists(_sup) and os.path.exists(_spdf):
        if not (os.path.isfile(_spdf) and os.path.getsize(_spdf) > 0):
            fails.append(("supplement.pdf 不是非空的常规文件",
                          "大小 %d 字节" % (os.path.getsize(_spdf) if os.path.isfile(_spdf) else -1),
                          "paper/"))
        elif os.path.getmtime(_spdf) < os.path.getmtime(_sup):
            fails.append(("supplement.pdf 比 supplement.tex 旧", "要重编译", "paper/"))
        elif VERBOSE:
            print("  OK   supplement.pdf 是非空文件且不旧于 supplement.tex")

    # ---- §I 与 §III 的「1.00 → 1.84 吃掉多少」（2026-09-27 通读 + 一次**自我纠错**）----
    # ⚠ 我一度把 §I 的「absorbs **a third**」判成错的（按**吞吐**口径算应是 45%~68%，
    # 于是改了正文）。**那是错的**：§III 有同口径的显式算式 ——
    # 「takes back **50 of the 156 minutes** … *a third* of the gain」，
    # 即按 **busy-time 分钟数** 算：340 →（ε=0 时）184/185，实测落在 **234**，
    # 吃掉 = 156 − (340−234) = **50** 分钟 ⇒ 50/156 = **32%** = a third ✓。
    # **两个归一化（分钟 vs 吞吐）给出 32% 与 46%，原句用的是前者。**
    # 教训：判一处可疑改动之前，**每个口径都算一遍**。
    _dm = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    if "cap1" in _dm and "cap5" in _dm:
        _b1m, _b5m = float(_dm["cap1"]["busy_min"]), float(_dm["cap5"]["busy_min"])
        # ⚠ 正文写 **184**（340/1.840948 = 184.687，是**截断**不是四舍五入 ——
        # 156 = 340−184 与 50 = 156−(340−234) 都建立在这个 184 上，内部自洽）。
        ck_near("§III 保持 τ 不变时的 busy 期望值", "%d" % int(_b1m / 1.840948),
                "sec_model.tex", "have cut busy time by a factor", window=90)
        ck_near("§III cap5 实测的 busy 分钟", "%.0f" % _b5m,
                "sec_model.tex", "curve flattens and lands at", window=40)
        ck_near("§III「a third」那一句", "a third", "sec_model.tex", "of the gain", window=30)
        ck_near("§I 也写 a third 并指向 §III", "a third", "sec_intro.tex",
                "of the busy time the extra concurrency", window=40)

    # ---- §criterion 的「加 10% 并发买到多少吞吐」= 1.1^(1-ε)（2026-09-25 加）----
    # 该节自己写着「Everything in between is a quantitative statement about how much
    # room」，却**从不给那个数** —— 这个数值兑现原先只在压缩前的摘要里，摘要压缩时
    # 被移出而没有落点（中立子 agent 第 12 轮抓到的唯一一处「移出即消失」）。
    # 端点现算，与上面守的两个 ε 共用常量。
    # keyword 用 `concurrency buys`：该文件里 `buys` 出现三次（公式一次、下面
    # 「still buys something」一次），只有这一处是这两个数所在。
    for _e, _d in ((_EPS_MODEL, "下界"), (_EPS_REQ, "上界")):
        ck_near("§criterion 加 10%% 并发的吞吐%s" % _d,
                "%.1f" % (100 * (1.1 ** (1 - _e) - 1)),
                "sec_criterion.tex", "concurrency buys")

    # ---- §V 的「四条复测臂从哪移到哪」（2026-09-25 codex r27 抓到符号）----
    # 正文原写「the resident base from 7.81 to 1.33 … horizon=0 from 13.60 to 7.19」，
    # **这两处各漏了两个负号**，而表 I 里它们是 −1.33 与 −7.19。
    # 负号丢在这里特别隐蔽：这句话论证的是「污染把距离压得**更负**、复测把它拉回来」，
    # 写成正数后读起来仍然通顺（7.81→1.33 也是「变小」），只有回头对表才发现矛盾。
    # 四个位移 11.2/6.5/6.4/4.5 只有在四个值**全为负**时才自洽：
    #   −8.31−11.2=−19.5 | −1.33−6.5=−7.8 | −7.19−6.4=−13.6 | −0.30−4.5=−4.8。
    # 新值从 table1.csv 现算；旧值只在 claims_audit.md 与
    # docs/codex_review_prompt_r23.md 里，没有数据文件留它，故写死并注明来源。
    # keyword 取 `no hw from`：这句独有（表 I 里的标签是 `no hw`，没有 ` from`）。
    _t1 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/table1.csv"))}
    # ⚠ 窗口必须**按臂收窄到 40**，且关键词用**每臂自己的名字**。
    # 原先四条臂共用 `no hw from` + window 400 —— 八个旧/新值全落在同一个窗口里，
    # 于是**在内存里把前两条臂的整组值对调，检查照样全过**（2026-09-25 codex r28 实测）。
    # 40 的依据：各臂自己的两个值相距 11~38 字符，而相邻臂的值相距 53~65 字符。
    for _run, _old, _mv, _kw, _kwnew in (("foyer_breshz1_r2", -19.54, 11.2, "no hw from", "no hw"),
                                          ("foyer_bres_r2", -7.81, 6.5, "resident base", "resident base"),
                                          ("foyer_hz0_r2", -13.60, 6.4, "horizon}$=0$", "horizon$=$0"),
                                          ("foyer_hz2_r2", -4.81, 4.5, "horizon}$=2$", "horizon$=$2")):
        if _run not in _t1:
            continue
        _new = float(_t1[_run]["delta_pp"])
        ck_near("%s 复测前的 Δ（旧值，源自 claims_audit）" % _run,
                "%.2f" % _old, "sec_results.tex", _kw, window=40)
        ck_near("%s 复测后的 Δ（表 I）" % _run,
                "%.2f" % _new, "sec_results.tex", _kwnew, window=90)
        # 位移必须与正文报的 11.2/6.5/6.4/4.5 对得上 —— 这是**派生量**，
        # 旧值或新值单独改动都会让它失配，而两个端点各自都还「在正文里」。
        checks += 1
        _calc = abs(_new - _old)
        if abs(_calc - _mv) > 0.15:
            fails.append(("%s 的复测位移" % _run,
                          "文中报 %.1f，由旧值 %.2f 与表中新值 %.2f 算得 %.2f"
                          % (_mv, _old, _new, _calc), "sec_results.tex"))

    # ---- 表 I 逐行对拍（2026-09-25 加）----
    # 表 I 的 LaTeX 是**手写**在 sec_results.tex 里的，而 `gen_table.py` 生成同一张表
    # —— 两边会分叉。`cap5_hc` 入表时就分叉过：tex 加了行、生成器的清单没加
    # （生成器少一行，而没有任何东西会提醒）。
    # 这条把两边的每个数据行对一遍。**只比 wall 与 SLO 两列**：Conc. 列
    # 生成器用原值（`94.91`），而正文对 no-control 那一行有意写 1 位（`94.9`，
    # 见上面 no-control 的注释），那一处差异是设计不是错。
    #
    # ⚠⚠ 2026-09-27：**生成器与 LaTeX 重新对齐之后，这一节第一次能【双向】比。**
    # 此前 `gen_table.py` 印 35 行、LaTeX 印 27 行，「生成器多的」被判成错（8 条 MISS）、
    # 「正文多的」**根本没查**（原写法只遍历 `_gen`）——也就是把「tex 加了一行而
    # 生成器没加」这个**唯一真正发生过的事故**（cap5_hc）漏掉了。
    # 现在：生成器默认只印论文那张表（`PAPER_OMIT`），于是两个方向都必须完全一致。
    import subprocess as _sp
    # 归一化函数只有一份实现（`_norm_label`）—— 这里保留短名，是因为下面
    # 「ready 时钟的子集分类」「A100 表」等好几处都用它，而它们此前共用的是
    # 一个**局部**定义。改到文件头之后行为不变，但两份实现变成了一份。
    _norm = _norm_label
    _gt = _sp.run([sys.executable, os.path.join(ROOT, "scripts", "lab", "gen_table.py"),
                   os.path.join(ROOT, "paper", "data", "runs.csv")],
                  capture_output=True, text=True).stdout
    # ⚠ 同一行正则/归一化只有一份实现（`_ROWRE` / `_norm_label`，见文件头）——
    # 这里原来各写了一份，与 `_table_rows()` 是同一条判据的两份代码。
    _gen = _table_rows(_gt)
    # ⚠ **只在表 I 的范围内找行**。放宽 `&` 两侧空白之后（表格列对齐会产生多空格），
    # 正则同时命中了 §V 的**归因表**（也是四列），而后出现的同名 key 把表 I 的
    # 覆盖掉 —— 于是报出六行「不符」（2026-09-25 踩到）。
    # ⚠⚠ 2026-09-27（r56 中立复核 3）：这里原来读的是 `P`（= `paper_text()`），
    # 而 `P` 现在**把 `\label{}` 一起剥掉了**（为了关掉「命令 key 里的数字喂给
    # `has()`」那条假通过通道）⇒ `find(r"\label{tab:runs}")` 返回 **-1**
    # ⇒ `_tbl` 从「表 I 的切片」**静默退化成整份 `sec_results.tex`**。
    #
    # **当时是惰性的**（复核者用 `_PSTRUCT` 修回去后逐条对拍：854/0/262 无一行差异，
    # 且整文件解析与表 I 切片**同为 28 行**、两向差集都是空）—— 但**保护不在了**：
    # 上面那段注释记的正是「放宽 `&` 空白后正则同时命中 §V 归因表、报出六个假行」
    # 那次事故，而挡住它的**恰恰就是这条切片**。⇒ 与表注守卫同一处置：读 `_PSTRUCT`。
    _rs = _PSTRUCT["sec_results.tex"]
    _i0 = _rs.find(r"\label{tab:runs}")
    _i1 = _rs.find(r"\end{table}", _i0) if _i0 >= 0 else -1
    # ⚠⚠ 同一条纪律（r56 codex 复核 9）：**不用 `assert`**（`-O` 会删掉它 ⇒ 静默退化），
    # 也**不中止整套**。切片定位失败就报一条 MISS，且**不回退**成整份文件
    # （回退正是「六行假报」那次事故的形态）。`_tbl` 置空 ⇒ 该组对拍自然无行可比，
    # 但 MISS 已经把「我没能检查」说了出来。
    checks += 1
    _slice_ok = (_i0 >= 0 and _i1 > _i0)
    if not _slice_ok:
        fails.append(("§V 表 I 的**切片定位失败**（`\\label{tab:runs}` / `\\end{table}` 没找到）",
                      "**不回退成整份 sec_results.tex** —— 那样会重演「六行假报」", "sec_results.tex"))
    _tbl = _rs[_i0:_i1] if _slice_ok else ""
    _tex = _table_rows(_tbl)
    # supplement 的**完整表**（35 行，逐字保有移出的 8 行）—— 值现在印在这里。
    _full = _table_rows(SUPP.get("supplement_table1.md", ""))
    # 表 I 每一行的 **Δ 列**（带符号！见下面注释），只在**表里真的列了该行**时查。
    # ⚠ 原写法是 `ck(..., delta_pp.lstrip("-"))` —— 为了绕开 LaTeX 的 `$-$74.10`
    # 而把符号丢掉了：把最差的一条从 `$-$74.10` 改成 `+74.10`（「赢 74 pp」）
    # 时检查照样通过（子 agent 独立实测）。`has()` 现在认 `$-$`/`$-`/`-` 三种写法。
    # ⚠ 只在表 I 范围内查：`table1.csv` 有 `pairA_cap2hc`，而**表 I 不列它**
    # （表里只有 `pairB_cap2hc`），对全表查会得到假 MISS。
    #
    # ⚠⚠ 2026-09-27：**这一步此前静默少了 8 条检查**，而发现它的是「检查数掉了 8」
    # （826 vs 11:57 那次的 834）。原来是 `if _norm(_lab0) not in _tex: continue` ——
    # 8 行移出 LaTeX 之后，它们的 Δ 检查**一行都不再执行**，而看起来「表 I 只有 27 行，
    # 所以本来就只有 27 条」。**这正是本项目记过的那个坏法：死了但没人知道。**
    # 现在按「那一行印在哪」分派：论文表 -> `sec_results.tex`；移出的 8 行 ->
    # supplement 的完整表（正文的 Notes to Table I 明写 supplement 载着它们）。
    # ⚠ 窗口 `_T1_W`：**实测** label 起点到 Δ 末尾的最大距离是 60（论文表）/ 54
    # （supplement 表），取 65。它必须**小于相邻行的 Δ 距离**（约 105），否则
    # 「邻居的 Δ 恰好等于本行的 Δ」会让这条检查假通过 —— 原来写的是 200，
    # 在 ~56 字符一行的表里横跨五行，等于没锚。
    _T1_W = 100
    for _r0 in load(os.path.join(ROOT, "paper/data/table1.csv")):
        _k0 = _r0["run"]
        if _k0 in NOT_PRINTED:
            continue                       # 两处都不印（见 NOT_PRINTED 的注释）
        _lab0 = _r0.get("label") or _k0
        if not (_r0.get("delta_pp") and abs(float(_r0["delta_pp"])) >= 5e-5):
            continue                       # 锚点行（Δ ≈ 0）不查
        ck_near("表 I %s 的 Δ" % _k0, _r0["delta_pp"], TABLE1_SRC.get(_k0, "sec_results.tex"),
                _lab0, window=_T1_W)
    if _gen:
        checks += 1
        _miss = sorted(k for k in _gen if k not in _tex)
        if _miss:
            fails.append(("表 I 缺生成器里的行", "、".join(_miss)[:60], "sec_results.tex"))
        # ⚠ 2026-09-27 补的**反方向**（原来是漏的，而 cap5_hc 那次事故正是这个方向）：
        # 正文印了、生成器印不出来的行 —— 生成器与 LaTeX 必须逐行一致，
        # 少一边就是「手写的表把生成器甩下了」，而此前没有任何东西会提醒。
        checks += 1
        _extra = sorted(k for k in _tex if k not in _gen)
        if _extra:
            fails.append(("表 I 有生成器不印的行（tex 加了行忘了改生成器）",
                          "、".join(_extra)[:60], "sec_results.tex"))
        # ⚠ 2026-09-27：**生成器的完整表（`--full`，35 行）必须整张都印在【某个地方】**
        # —— 论文表 I 或者 supplement 的完整表。这是「表 I 缺生成器里的行」那条
        # 在缩表之后的**正确落点**：它原来的意思是「生成器算了、论文没印」，
        # 现在多了一个合法的印处（supplement），但**「两处都没印」仍然是错的**。
        _gt_full = _sp.run([sys.executable, os.path.join(ROOT, "scripts", "lab", "gen_table.py"),
                            os.path.join(ROOT, "paper", "data", "runs.csv"), "--full"],
                           capture_output=True, text=True).stdout
        _genf = _table_rows(_gt_full)
        checks += 1
        _gone = sorted(k for k in _genf if k not in _tex and k not in _full)
        if _gone:
            fails.append(("表 I 的完整表里有既不在正文也不在 supplement 的行",
                          "、".join(_gone)[:60], "supplement_table1.md"))
        _dif = sorted((k, _gen[k], _tex[k]) for k in _gen
                      if k in _tex and _gen[k] != _tex[k])
        checks += 1
        if _dif:
            fails.append(("表 I 与生成器不符（%d 行）" % len(_dif),
                          "；".join("%s 生成%s/正文%s" % d for d in _dif[:3]), "sec_results.tex"))
        # supplement 的完整表与生成器的 `--full` 对拍（只比 wall 与 SLO，同表的 Δ 列
        # 由上面逐行的 `表 I %s 的 Δ` 守）。
        checks += 1
        _dif2 = sorted((k, _genf[k], _full[k]) for k in _genf
                       if k in _full and _genf[k] != _full[k])
        if _dif2:
            fails.append(("supplement 的完整表与生成器不符（%d 行）" % len(_dif2),
                          "；".join("%s 生成%s/supplement%s" % d for d in _dif2[:3]),
                          "supplement_table1.md"))

    # ---- §VI ready-clock 段的两组计数（2026-09-25 codex r27：两组都过时了）----
    # 原写「nineteen of the twenty-five 200-session runs ... absent are the no-control
    # baseline, the two HiCache anchor repeats and three controller repeats」，
    # 实际是 **20 of 28**，且缺席名单是 8 条（无控制 1 + host-tier 5 + 控制器重复 2）。
    # **这是本项目最常漂的一类 —— 派生计数**：run 一多，句子里的「几分之几」就假了，
    # 而分子分母各自都还好好地待在数据里，没有任何东西会响。
    # 分子分母都现算，不写死。
    #
    # ⚠⚠ 2026-09-27（**表 I 缩到 27 行之后的改锚**）：分母**不再是表 I 的行数**。
    # 就绪时钟重算过的是「我们在这条 trace 上测过的全部 200-session run」= 35 条
    # （`arrival_slo.csv` 的行数），而这个口径**有意不跟着表缩小**
    # （见 `paper/supplement_table1.md` 的第 2 条：正文的 Notes to Table I 现在写
    # 「the supplement carries our full run table」，而 §VI 那句已经改成
    # 「all thirty-five 200-session runs we measured on this trace」）。
    # ⇒ 旧写法 `"%s of the %s" % (n_ready, len(_tex))` 会算出一个**不可能印在稿子里的
    # 短语**「thirty-five of the twenty-seven」，报一条看不懂的 MISS。
    # 判据：**分母是就绪时钟的样本数**，不是「表里印了几行」——这正是 2026-09-27
    # 那次「差点把一句正确的话改坏」的同一个量，只是方向相反。
    _n_ready = len(load(os.path.join(ROOT, "paper/data/arrival_slo.csv")))
    if _n_ready:
        # ⚠ 完整短语一起匹配（不是分子分母各查各的）：把正文倒写成
        # "twenty-eight of the twenty" 时两项**都还在**，各查各的会放过它
        # （2026-09-25 codex r28 实测）。
        _mw = num_words(_n_ready)
        _phrase = "all %s" % (_mw[0] if _mw else "?")
        # 窗口要**盖住整段短语**：`ck_near` 的窗口是围绕关键词的，
        # 「basis」到「thirty-five」结尾约 60 字符；开小了会得到**假 MISS**。
        ck_near("§VI ready-clock 的「all N」整段", _phrase,
                "sec_discussion.tex", "ready-to-first-token basis", window=120)

        # ⚠⚠ 2026-09-27：**同一条句子的「分解」此前没人守。**
        # 正文写「the rest being the no-control baseline, **four** host-tier runs and
        # **two** controller repeats」—— 三个数相加必须等于分母。
        #
        # ⚠⚠⚠ 加这条时我**先把分母取错了源**，差点改错一句本来正确的话：
        #   我用 `table1.csv` 的行数（**35**）当分母，于是算出「35 − 26 = 9 =
        #   1 + 5 + 3」，据此把正文的「thirty-three / four / two」改成了
        #   「thirty-five / five / three」。**那三个改动全是错的。**
        #   拦下我的是**本函数上面那条已有的 `ck_near`** —— 它报
        #   「twenty-six of the thirty-three」，让我看到**它算出的分母是 33**。
        #
        #   根因：**「in Table I」的分母是【LaTeX 表里真的印了几行】**，
        #   而 `table1.csv` 是它的**超集** —— 多出的两条（`pairA_cap2hc`、
        #   `aimd2_paper`）在 CSV 里、**不印在表 I 里**（表 I 的行由
        #   `gen_table.py` 的 `NOT_PRINTED` 决定）。用 CSV 当分母，
        #   多出的那两条既不在 `arrival_slo.csv` 里、也不在任何分类里 ⇒
        #   被算成「host-tier」和「控制器重复」，正好各多一条。
        #
        #   ⇒ **分类必须在「表 I ∩ 有日志」这个集合上做**，不能在全表上做。
        #   判据与上面那条守卫**共用 `_tex`**（LaTeX 解析出来的那 33 行），
        #   不另写一份来源 —— 两份来源分叉就是这次踩的坑。
        _tex_lab = set(_tex.keys())
        # `arrival_slo.csv` 的 run 名 -> 归一化标签，才能与 `_tex` 的键比
        _asl = load(os.path.join(ROOT, "paper/data/arrival_slo.csv"))
        _t1lab = {r["run"]: _norm(r.get("label") or r["run"])
                  for r in load(os.path.join(ROOT, "paper/data/table1.csv"))}
        _in_tab = {r["run"] for r in _asl
                   if _t1lab.get(r["run"], r["run"]) in _tex_lab}
        _excl_tab = sorted(
            r["run"] for r in load(os.path.join(ROOT, "paper/data/table1.csv"))
            if _norm(r.get("label") or r["run"]) in _tex_lab
            and r["run"] not in {x["run"] for x in _asl})
        _n_nc = sum(1 for r in _excl_tab if r == "default")
        # host-tier = 静态族（cap*/pair*_cap*）且名字含 hc；
        # ⚠ 不能只判「含 hc」——`foyer_hc_r2` 也含 hc 但它是**控制器重复**
        #   （我第一版就是这么误分类的，算出 6 和 2 而不是 4 和 2）。
        _n_hc = sum(1 for r in _excl_tab
                    if r != "default" and "hc" in r
                    and (r.startswith("cap") or r.startswith("pair")))
        _n_rp = len(_excl_tab) - _n_nc - _n_hc
        # ⚠⚠ 2026-09-27：**这条断言此前写在 `if _excl_tab:` 里面**，而 `_excl_tab`
        # 为空恰恰是它最该跑的时候（空集 = 「没有任何 run 被排除在外」，正是它要证的
        # 那件事）。现在表 I 的每一行都有就绪时钟读数 ⇒ `_excl_tab` 恒为空 ⇒
        # 那条断言**从来没在执行**。已移到 `if` 外面。
        # 同一个病的另一面：**守卫能不能执行取决于数据的形状** —— 同一天 8 条
        # `表 I …的 Δ` 也是这么死的（行移出 LaTeX 后整块不再执行，检查数掉了 8 才发现）。
        # ⚠⚠ 2026-09-27（中立复核 r50 D2）：这里原来是**裸 `assert`** ——
        # 铺满性不成立时抛 `AssertionError`，**报告被截断在那一行**：
        # 只印到当时的 OK 行、**没有「共 N 项检查」汇总行、MISS 计数为 0**，
        # 而 `fails` 里已累积的条目全部没打印出来，**唯一信号是 rc=1**。
        # 这与本项目记过的「崩了看起来像全过」同型（那次是 `NameError` 被 grep 滤掉）。
        # 改成 `fails.append`（照本项目其他守卫的写法）：失败变成一条 MISS。
        checks += 1
        if len(_in_tab) + len(_excl_tab) != len(_tex_lab):
            fails.append((
                "表 I 的分类没盖全（两份集合必须刚好铺满表 I）",
                "表 I %d 行：有日志的 %d + 排除的 %d ≠ %d" % (
                    len(_tex_lab), len(_in_tab), len(_excl_tab), len(_tex_lab)),
                "paper/data/arrival_slo.csv / table1.csv"))
        if _excl_tab:
            # ⚠ 2026-09-27：这两条只在**真有排除名单**时才跑（现在表 I 的每一行都有
            # 就绪时钟读数，所以 `_excl_tab` 为空、正文里那个「the rest being …」的
            # 分解句也已随压缩删除）。空的时候不执行是**对的**（没有清单可查），
            # 但这也意味着**检查数会随数据的形状变** —— 记账见报告。
            # ⚠⚠（codex r49 第 19 条）它们只守【数量】、不守【成员】：把 ready 集合里的
            # `foyer_scan_r2` 换成原本被排除的 `foyer_hc_r2`，数量**全不变**。
            # **不修**：修它要引入一份「期望成员」名单，而那份名单就是被检查的对象本身
            # （自证循环）。成员身份由**上游**保证：`gen_arrival_slo.py` 的 `RUNS`
            # 名单 + `arrival_slo.csv` 的行集合。
            ck_near("§VI ready 子集排除的 host-tier 条数",
                    num_words(_n_hc), "sec_discussion.tex", "host-tier runs and",
                    window=40)
            ck_near("§VI ready 子集排除的控制器重复条数",
                    num_words(_n_rp), "sec_discussion.tex", "controller repeats",
                    window=40)
        # 2026-09-26 补：同一句里的**损失区间**此前没人守 —— 而它一直是旧的
        # （正文写 19.3，`arrival_slo.csv` 的 max |delta_pp| 是 19.5，一直如此）。
        # 「A--B 型区间」是派生量里最常漂的一类（端点各自都好好待在数据里）。
        # ⚠ 2026-09-27：**排除 `default`**。它是无控制基线，没有准入决定要做，
        # 就绪时钟与引擎时钟按构造相等（`delta_pp` = 0.0）—— 把它算进去，
        # 区间下界会永远是 0.0，那条端点就废了。正文现在写的是「**the runs that gate
        # admission** lose 0.4--19.5」，集合写在句子里。
        _dl2 = [abs(float(r["delta_pp"])) for r in
                load(os.path.join(ROOT, "paper/data/arrival_slo.csv"))
                if r.get("delta_pp") not in ("", "None") and r["run"] != "default"]
        if _dl2:
            ck_near("§VI ready-clock 的 SLO 损失区间",
                    "%.1f--%.1f" % (min(_dl2), max(_dl2)),
                    "sec_discussion.tex", "loses", window=40)

    # ---- §A100 的控制器读数（2026-09-25 第一次在 A100 上跑控制器）----
    # 数据由 `gen_a100_delta.py --csv` 生成（它调 gen_a100.one() 与 envelope.front_slo，
    # 两份都是共用定义）。**key 必须逐个钉**：这一段里 96.4 出现两次、100.0 也可能在
    # 别处（静态点全是 ~100%），只用 `ck` 会互相撞上。
    _ad_p = os.path.join(ROOT, "paper/data/a100_delta.csv")
    if os.path.exists(_ad_p):
        _a100 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/a100.csv"))}
        # ⚠ **集合完整性**：2026-09-26 我重生成这张表时**只传了一条臂**
        # （`a100_foyer_hz2`），于是 `a100_default` 那行**静默消失** ——
        # 是「检查数掉了 2」才发现的，而 MISS 一直是 0。
        # 这与「生成器的 run 列表不全会静默丢数据」同源，只是这次列表是我在命令行
        # 手打的。**凡是从一批 run 生成表的脚本，都要有集合完整性守卫。**
        # ⚠ `_norm` 会把 `$^{\ddagger\S}$` 与 `$^\ddagger$` **剥成同一个键** ——
        # 也就是说「把 § 标记删掉」逐行对拍**照样通过**（codex 第 34 轮给的构造）。
        # 所以标记本身要单独守一次。
        # ⚠ 2026-09-26：**语义反过来了**。AIMD 那一行原来是被标记的（墙钟不可用），
        # 现在换成第三次尝试（有监督循环、最长中断 50 秒）之后墙钟是可用的，
        # 所以判据从「标记必须在」改成「标记必须不在」。
        checks += 1
        if "$^{\\ddagger\\S}$" in P["sec_results.tex"]:
            fails.append(("表 I 又出现了 § 标记（那一行的墙钟现在是可用的）",
                          "AIMD, paper params 那一行", "sec_results.tex"))
        elif VERBOSE:
            print("  OK   AIMD 那一行没有 § 标记（墙钟可用）")
        _adr = {r["run"] for r in load(_ad_p)}
        for _need in ("a100_foyer_hz2", "a100_default"):
            checks += 1
            if _need not in _adr:
                fails.append(("a100_delta.csv 少了这条臂（重生成时 run 列表漏了）",
                              _need, "paper/data/a100_delta.csv"))
            elif VERBOSE:
                print("  OK   a100_delta.csv 含 %s" % _need)
        for _r in load(_ad_p):
            # CONTESTED 的行**不走这一套关键词**：它的数在另一句里
            # （「88.6 against 88.3 …」），且它的 SLO 正文不印。下面另有专属检查。
            if _r.get("contested") == "CONTESTED":
                continue
            ck_near("§A100 %s 的墙钟" % _r["run"], _r["wall_min"], "sec_xtrace.tex",
                    "minutes at a")
            # ⚠ 关键词 2026-09-27 从 `success` 换成 `satisfaction` —— 中立复核 r50 D1：
            # 「100.0\% success rate」与「32.9\% success rate」是**同一节里给同一个量
            # 换的第二个名字**，且未定义；§II 定义的是 `deadline satisfaction rate`。
            # 正文已统一，锚跟着换（`ck_near` 的关键词是空白无关的，跨行不再是问题）。
            ck_near("§A100 %s 的 SLO" % _r["run"], _r["slo_pct"], "sec_xtrace.tex",
                    "satisfaction")
            # ⚠ 关键词**不能跨行**：`ck_near` 用的是字面 `find`，而正文的
            # "the fastest\nstatic cap there" 中间是换行 —— 写成
            # "fastest static cap there" 会得到**假 MISS**（2026-09-25 踩到）。
            # 一律挑**同一行内**的锚点。
            # 关键词跟着正文换：2026-09-26 深扫落地后那句改成
            # 「cap sixteen in 88.3---the same wall clock as the controller」。
            ck_near("§A100 前沿左端的墙钟", _r["front_left_min"], "sec_xtrace.tex",
                    "the same wall clock as")
            # （原先这里查「控制周期采样数 2762」。2026-09-25 那句话整句被换掉了
            #  —— 它引的是 `gate_full`，而那个字段恒为 False —— 2762 因此不再进正文，
            #  这条检查随之作废。**留空检查比删掉更坏**：它看着像在守，其实永远通过。）
            # ⚠ **不再查 `gate_full`**：那个字段在 `round_gate=0` 下恒为 False，
            # 任何 run 都是 0.0%（2026-09-25 独立复算抓到，当时它已经写进了正文）。
            # 换成三条真的会变的观测。
            if _r.get("usage_max_pct", "") != "":
                ck_near("§A100 池子利用率峰值", "%.0f" % float(_r["usage_max_pct"]),
                        "sec_xtrace.tex", "peaked at")
            if _r.get("active_max", "") != "":
                ck_near("§A100 峰值会话数", num_words(int(_r["active_max"])),
                        "sec_xtrace.tex", "running fourteen")
            # ⚠ 两个数各绑**各自的词**：2026-09-26 codex r29 实测，
            # 把「median 1.6 / max 51.7」对调后两项仍通过 —— 因为它们落在同一个窗口。
            # 改成短语匹配，数与位置一起绑死。
            if _r.get("admit_wait_p50_ms", "") != "":
                ck_near("§A100 准入等待中位",
                        "median wait of %.1f" % (float(_r["admit_wait_p50_ms"]) / 1000.0),
                        "sec_xtrace.tex", "admitted after a", window=60)
            if _r.get("admit_wait_max_ms", "") != "":
                ck_near("§A100 准入等待上界",
                        "maximum of %.1f" % (float(_r["admit_wait_max_ms"]) / 1000.0),
                        "sec_xtrace.tex", "and a", window=40)
        # 不控制基线的那一行（2026-09-25 加）：它带 CONTESTED 标记，**只当上界用**。
        # 正文写「88.6 against 88.3 … tracking it at every completion quantile」。
        for _r in load(_ad_p):
            if _r.get("contested") != "CONTESTED":
                continue
            ck_near("§A100 不控制基线的墙钟", _r["wall_min"], "sec_xtrace.tex",
                    "against")
            ck("§A100 不控制基线的 SLO", _r["slo_pct"], "sec_xtrace.tex", tier="S")

        # §A100 末段：**两次尝试都没拿到干净的基线**（2026-09-26 加）。
        # 这一段引了九个新数，此前只存在于终端输出里 —— 所以先补了
        # `gen_a100_baseline.py` 把它们落成 `a100_baseline.csv`，再在这里逐项绑词。
        # ⚠ 关键词**必须落在同一行内**（LaTeX 硬换行会把短语断开 —— 本项目栽过三次）。
        _ab_p = os.path.join(ROOT, "paper/data/a100_baseline.csv")
        if not os.path.exists(_ab_p):
            fails.append(("缺 a100_baseline.csv（§A100 末段的九个读数没有出处）",
                          "a100_baseline.csv", "paper/data"))
        else:
            _ab = {r["run"]: r for r in load(_ab_p)}
            _b1, _b2 = _ab.get("a100_default"), _ab.get("a100_default_r2")
            if not _b1 or not _b2:
                fails.append(("a100_baseline.csv 少一次尝试", "两次都要在", "paper/data"))
            else:
                # 第 1 次：末段那 23.7 分钟与 82/341
                # ⚠ 用 `dirty_before_end_min`（首条脏采样 → run 结束，23.8470），
                # **不是** `dirty_span_min`（首末两条脏采样之间，23.7215）——
                # 正文说的是「最后 N 分钟共卡」，N 是前者。codex 第 35 轮指出。
                ck_near("§A100 基线被占的时长", _b1["dirty_before_end_min"], "sec_xtrace.tex",
                        "its last", window=40)
                ck_near("§A100 基线含外人的采样数", int(_b1["watch_foreign"]),
                        "sec_xtrace.tex", "a foreign process in", window=30)
                ck_near("§A100 基线的窗内采样数", int(_b1["watch_n"]),
                        "sec_xtrace.tex", "the run's", window=30)
                # 第 2 次：池子、占用、两次 watcher、墙钟、SLO、τ₂、对照上界
                ck_near("§A100 重跑的池子", int(_b2["pool_tokens"]), "sec_xtrace.tex",
                        "did not produce one: pool", window=40)
                ck_near("§A100 重跑的占用中位", _b2["occ_p50_pct"], "sec_xtrace.tex",
                        "median occupancy of", window=30)
                # ⚠ 查**整句**「566 of 566」，不能只查 566 —— 反向测试（把前一个
                # 566 改成 565）**没报 MISS**，因为同一个短语里还有一个 566。
                # 这是 CLAUDE.md「同一个数在别处出现不等于它用在了这里」的镜像。
                ck_near("§A100 重跑含外人的采样（分子与分母）",
                        "%d of %d" % (int(_b2["watch_foreign"]), int(_b2["watch_n"])),
                        # 窗口要够宽：「records a foreign process in \textbf{」自己就
                        # 有 34 个字符，window=40 会把短语的尾巴切掉 → **假 MISS**。
                        "sec_xtrace.tex", "records a foreign process in", window=70)
                ck_near("§A100 重跑的墙钟", _b2["wall_min"], "sec_xtrace.tex",
                        "minutes at a", window=30)
                ck_near("§A100 重跑的 SLO", _b2["slo_pct"], "sec_xtrace.tex",
                        "satisfaction", window=30)
                ck_near("§A100 重跑的 τ₂", _b2["tau2_ms"], "sec_xtrace.tex",
                        "per-request decode interval of", window=40)
                # 「ten times the 21.4 ms maximum」—— 21.4 是**本 tier 七个静态 run**
                # 的 τ₂ 上界，不是全表（a100.csv 里还装着 3090 的对照行，全表上界
                # 是 3090 cap5 的 31.2）。按 `a100_` 前缀现算，与生成器同源。
                _t2 = [float(r["tau2_ms"]) for r in _a100.values()
                       if r["run"].startswith("a100") and r.get("tau2_ms")]
                if _t2:
                    # 值（本 tier 的 τ₂ 上界 = 21.4）**不在正文** —— 退役（见 RETIRED）。
                    pass
                # 反向测试（2026-09-26）：把 95.3 改成 93.5、把 566 改成 565、
                # 把 817{,}527 改成 817{,}526，三条各自报 MISS ✓

        # 「墙钟随 cap 单调下降」那三个数：cap3/cap4 从 a100.csv 现取（cap5 是上面的左端）。
        for _k, _lab in (("a100_cap3", "cap 三"), ("a100_cap4", "cap 四")):
            if _k in _a100:
                ck_near("§A100 %s 的墙钟（单调下降那串）" % _lab,
                        "%.1f" % float(_a100[_k]["wall_min"]),
                        "sec_xtrace.tex", "minutes at caps")

    # ---- 池子对照实验（2026-09-25：半池因果实验落地，§I 与 §III 都引）----
    # 数据由 gen_pool50.py 生成。**两类行要用不同的守卫**：
    #   status=OK         -> 兑现率与净效应都在正文里，逐个钉住；
    #   status=INFEASIBLE -> 引擎 OOM 崩的 run，**正文里只许出现步数与失败数**，
    #                        兑现率一律留空（活下来的都是有偏的短会话）。
    # ⚠ 关键词一律挑【同一行内】的（LaTeX 是硬换行，跨行会得到假 MISS，见 CLAUDE.md）。
    _p50 = load(os.path.join(ROOT, "paper/data/pool50.csv"))
    # ⚠ **集合完整性**：§III 引了四条 run（cap2_hp / cap3_hp / cap4_hp / cap3_p75）。
    # 2026-09-26 codex r29 实测：把 cap3_p75 行从 CSV 里删掉，检查数只从 534 掉到 530、
    # **0 MISS** —— 逐行循环不会发现自己少了一行。所以这里显式钉住条数。
    checks += 1
    _want = {"cap2_hp", "cap3_hp", "cap4_hp", "cap3_p75"}
    _got = {r["run"] for r in _p50}
    if _got != _want:
        fails.append(("pool50.csv 的 run 集合与 §III 引的不一致",
                      "正文引 %s，表里有 %s" % (sorted(_want), sorted(_got)),
                      "paper/data/pool50.csv"))
    for _r in _p50:
        if _r["status"] == "OK":
            ck_near("§III 池子 %s 的净效应" % _r["run"],
                    "%.1f" % abs(float(_r["delta_pp"])), "sec_model.tex", "tokens costs")
            ck_near("§III 池子 %s 的兑现" % _r["run"],
                    "%.1f" % float(_r["half_real"]), "sec_model.tex",
                    "matched running count")
            ck_near("§III 池子 %s 的同 R̄ 参照" % _r["run"],
                    "%.1f" % float(_r["full_real_at_same_Rbar"]), "sec_model.tex",
                    "matched running count")
            ck_near("§III 池子 %s 的 R̄" % _r["run"],
                    "%.2f" % float(_r["half_Rbar"]), "sec_model.tex",
                    "interpolates to at the same")
            ck_near("§I 池子减半的净效应",
                    "%.1f" % abs(float(_r["delta_pp"])), "sec_intro.tex",
                    "halving the pool costs")
        else:
            # **数据层不变量**：INFEASIBLE 的行必须没有兑现率。这一条守的是
            # 「别从删失样本凑一个数」——那是本项目最容易犯的一类错。
            # 2026-09-25 独立复算抓到的正是它的**反面**：`cap2_hp` 的兑现率被算出来了，
            # 而且算错了 30 pp（104/999 步被服务成 1-token 响应、记成成功，
            # 计划 prompt 被当成复用）。现在那一条也被判成 INFEASIBLE。
            checks += 1
            # 单向无例外：**退化步数不得超过超池步数**（退化 ⊆ 超池）。
            # 崩掉的 run 里超池会更多（差额是报错步），所以只能用单向不等式 ——
            # 也正是 §III 那句全称量词只能写成单向的原因。
            if int(_r["degenerate_steps"]) > int(_r["steps_over_pool"]):
                fails.append(("pool50 的 %s：退化步多于超池步" % _r["run"],
                              "退化 %s > 超池 %s" % (_r["degenerate_steps"],
                                                     _r["steps_over_pool"]),
                              "paper/data/pool50.csv"))
            if _r["half_real"] or _r["delta_pp"]:
                fails.append(("pool50 的 INFEASIBLE 行 %s 带了兑现率" % _r["run"],
                              "half_real=%r delta_pp=%r —— 删失样本算不出兑现率"
                              % (_r["half_real"], _r["delta_pp"]), "paper/data/pool50.csv"))
            # ⚠ 关键词**逐个 run 指认**，不能两条共用一个宽窗口 —— 共用会让
            # 「两条 run 的数对调」照样通过（2026-09-25 codex r28 实测后修）。
            # 每条的锚点都挑在**同一行内**（LaTeX 是硬换行）。
            # ⚠ 逐 run 指认关键词，**不共用宽窗口** —— 共用会让「两条 run 的数对调」
            # 照样通过（2026-09-25 codex r28 实测后修）。锚点全挑在同一行内。
            # 只查**正文真的印了**的那些列：`unserved_steps` 只有 cap2_hp 与 cap3_p75 印了，
            # cap3_hp/cap4_hp 只印了 attempted 与缺口占比（多查会得到**假 MISS**）。
            # ⚠ 列名在 2026-09-26 变了：`unserved_steps` 拆成 `degenerate_steps`
            # 与 `error_steps`（并集口径会自相矛盾，见生成器里的注释）。
            # 这里引的是**退化步数**（安静的失败），不是并集。
            _SPEC = {
                # ⚠ 关键词必须在【同一物理行内】（CLAUDE.md：LaTeX 硬换行会把短语断开，
                # 断了就是假 MISS）。「carry」原来在这里，改写后那个词不再紧邻这个数，
                # 换成同一行的「the prompts they planned」。
                # ⚠ 2026-09-27 活性审计：这条原被退役（理由写「正文只报长度边界结论」），
                # 而正文**确实印了**「104 of the 999 steps are degenerate」——
                # 是**锚漂了**（旧措辞是 `that is`）。已删退役条目 + 改锚。
                "cap2_hp":  [("degenerate_steps", "of the 999 steps are degenerate"),
                             ("gap_pct_of_bound", "the prompts they planned"),
                             # 2026-09-26 补：同一个数还有第二个口径（prefix 占上界），
                             # 独立复核指出原先只印前一个会让读者把两者当成一回事。
                             ("gap_pct_of_prefix", "carried")],
                # 长度门槛的两个端点 —— §III 引它们正是为了说明门槛**精确**（差 4 个 token）
                # ⚠ 用**整段短语**而不是「14」这一个数：2026-09-26 codex r29 实测，
                # 把正文改成「three quarters it is 41（另处仍提 14）」照样通过，
                # 因为 14 在别处出现过。短语把数与位置一起绑死。
                "cap3_p75": [("degenerate_steps", "at three quarters"),
                             # 「is dropped」跨了行（`prompt is` / `dropped from`）——
                             # 换成同一行的「prompt is」。
                             ("min_over_pool_tok", "prompt is"),
                             ("max_served_tok", "one is served")],
                # 崩溃的两条引的是**并集**（没被服务的步 = 退化 + 报错）——
                # 对「停了之后还剩多少步没跑」而言并集才是对的口径，
                # 而 §III 讲「安静的失败」时用的是**退化**那一列。两者不能混。
                "cap3_hp":  [("attempted_steps", "stopping at"),
                             (("degenerate_steps", "error_steps"), "stopping at"),
                             # 「49 of the first run's 50 failed steps」——把两条链分开的那句
                             ("error_under_pool", "have prompts that fit")],
                "cap4_hp":  [("attempted_steps", "stopping at"),
                             (("degenerate_steps", "error_steps"), "stopping at")],
            }
            for _col, _kw in _SPEC.get(_r["run"], []):
                if isinstance(_col, tuple):
                    _v = str(sum(int(_r[c]) for c in _col))
                    _d = "＋".join(_col)
                else:
                    _v, _d = _r[_col], _col
                ck_near("§III %s 的 %s" % (_r["run"], _d), _v,
                        "sec_model.tex", _kw, window=80)

    # ---- 容量对照的【实验条件词】要回 metadata 核（2026-09-26 抓到一处假陈述）----
    # 正文原来写「A capacity-controlled version---same card, same trace, one policy,
    # only the pool size changed」。**「same card」是假的**：四条容量对照 run 里
    # `cap4_hp` 在 **卡 3**，而它的满池对照 `cap4` 在 **卡 2**（另三条与各自对照同在卡 2）。
    # 已改成「the same trace and policy, with the pool halved」—— 只描述**做过的干预**，
    # 不断言「其余全同」（满池对照还来自 09-15/09-21 两批，与 09-25 的容量对照不同代）。
    # 判据两半：负面（旧措辞不许回来）+ 正面（trace / policy / pool 三个事实可重算）。
    _cf = _cf2 = re.sub(r"\s+", " ", alltext)   # 全稿空白归一：两处别名，后面的块在 1922 之前就要用
    checks += 1
    if re.search(r"same card,\s*same trace", _cf, re.I):
        fails.append(("§III 又出现「same card, same trace」的容量对照措辞（实为不同卡）",
                      "cap4_hp 在卡 3、其满池对照 cap4 在卡 2",
                      "sec_model.tex"))
    _cap_pairs = [("pois200_cap2_hp", "pois200_cap2", 50716),
                  ("pois200_cap3_hp", "pois200_cap3_fixed", 50716),
                  ("pois200_cap4_hp", "pois200_cap4", 50716),
                  ("pois200_cap3_p75", "pois200_cap3_fixed", 76074)]
    _cap_bad, _cap_cards, _cap_md5 = [], [], set()
    for _h, _f, _ph in _cap_pairs:
        try:
            _mh = json.load(open(os.path.join(ROOT, "results/night", _h, "metadata.json")))
            _mf = json.load(open(os.path.join(ROOT, "results/night", _f, "metadata.json")))
        except Exception as _e:
            _cap_bad.append("%s/%s 读不到 metadata: %s" % (_h, _f, _e))
            continue
        if _mh.get("pool_tokens") != _ph:
            _cap_bad.append("%s 池子 %s≠%s" % (_h, _mh.get("pool_tokens"), _ph))
        # ⚠ 2026-09-26 codex r44：原来**只核了缩池那一侧**，把对照的池子改成 90,000 仍通过。
        # 「缩到一半」只有在对照**仍是满池**时才有意义。
        if _mf.get("pool_tokens") != 101432:
            _cap_bad.append("%s 的对照 %s 池子 %s≠101432"
                            % (_h, _f, _mf.get("pool_tokens")))
        # ⚠ codex r45：守卫原来**不查 memfrac**，而正文说缩池是 `by lowering the
        # memory fraction`。两边都记了值时必须「缩的那条 memfrac 更小」；
        # 老批次的 `cap2`/`cap4` 没记（None），**只披露不判**（本项目规矩）。
        _mh_mf = (_mh.get("build") or {}).get("TURNSTILE_MEMFRAC")
        _mf_mf = (_mf.get("build") or {}).get("TURNSTILE_MEMFRAC")
        if _mh_mf is not None and _mf_mf is not None and float(_mh_mf) >= float(_mf_mf):
            _cap_bad.append("%s 的 memfrac %s 不小于对照的 %s（正文说 by lowering it）"
                            % (_h, _mh_mf, _mf_mf))
        # 「只动池子」的那一半：满池对照必须是**同一个策略串**、**同一条 trace**
        if _mh.get("policy") != _mf.get("policy"):
            _cap_bad.append("%s 的策略 %s≠对照 %s" % (_h, _mh.get("policy"), _mf.get("policy")))
        _cap_md5.add(_mh.get("trace_md5"))
        _cap_md5.add(_mf.get("trace_md5"))
        _cap_cards.append((_h, _mh.get("gpu"), _f, _mf.get("gpu")))
    checks += 1
    if _cap_bad or len(_cap_md5) != 1:
        fails.append(("§III 容量对照的 metadata 与「同 trace、同策略、只动池子」不符",
                      "；".join(_cap_bad) or "trace_md5 有 %d 种：%s" % (len(_cap_md5), _cap_md5),
                      "results/night/pois200_cap*_hp|p75/metadata.json"))
    # 正面记下卡号：`cap4_hp` 与对照**不同卡** —— 这正是「same card」不许回来的理由。
    checks += 1
    _unequal = [(h, gh, f, gf) for h, gh, f, gf in _cap_cards if gh != gf]
    if not _unequal:
        fails.append(("§III「容量对照不同卡」这一事实变了（全部同卡）",
                      "卡号：%s —— 若确实全部同卡，可把「same card」写回正文并撤掉上面那条负面守卫"
                      % _cap_cards, "results/night/pois200_cap*_hp|p75/metadata.json"))

    # ---- 「six runs at four pool sizes, no counterexample」这个**派生计数**（2026-09-26 补）----
    # §III 用它给「prompt 超过池子的步一步都不会被执行」这条规则背书，而
    # **它此前没有任何守卫**（正文里唯一的数字守卫是四条 pool50 行的逐列读数）。
    # 计数从镜像现算：有退化步（`server_prompt_tokens==1` 而计划 prompt >1）的 run 数、
    # 这些 run 的池子种类数，以及**反例方向**（退化步多于超池步）。
    # ⚠ 镜像不全时这个数会漂（CLAUDE.md：lab-only 的表随「实验机上有什么」变化）——
    # 所以它**报警就是让人去看**：要么补扫新 run，要么改正文的条数。
    # ⚠ 2026-09-26 codex r44：原来只核「6 条 / 4 种」，**没有名单** ——
    # 少一条同时补进一条同池的新 run 就仍报 OK。名单写死（它是正文那个数的**身份**）。
    _DEG_EXPECT = {"pois200_cap2_hp": 50716, "pois200_cap3_hp": 50716,
                   "pois200_cap4_hp": 50716, "pois200_cap3_p75": 76074,
                   "load50_default": 76018, "load25_budget": 72647}
    _deg_runs, _deg_pools, _deg_bad = [], set(), []
    for _root2 in ("results/night", "results/a100_night"):
        for _d2 in sorted(glob.glob(os.path.join(ROOT, _root2, "*"))):
            _mp2 = os.path.join(_d2, "steps.jsonl")
            _mj2 = os.path.join(_d2, "metadata.json")
            if not (os.path.exists(_mp2) and os.path.exists(_mj2)):
                continue
            try:
                _pool2 = json.load(open(_mj2)).get("pool_tokens")
            except Exception:
                continue
            if not _pool2:
                continue
            _dg = _ov = 0
            try:
                for _l2 in open(_mp2):
                    if not _l2.strip():
                        continue
                    _s2 = json.loads(_l2)
                    _pl2 = int(_s2.get("prompt_len") or 0)
                    if _s2.get("server_prompt_tokens") == 1 and _pl2 > 1:
                        _dg += 1
                        # ⚠ 2026-09-26 中立复核 m4：正文写的是**全称量词**
                        # （「every step ... one prompt token has a prompt larger than
                        # the pool」），而原来只判聚合方向（dg > ov）—— 一条假退化
                        # 配一条多余超池就会互相抵消。这里**逐步**判。
                        if _pl2 <= _pool2:
                            _deg_bad.append("%s 有一条退化步的 prompt %d ≤ 池子 %d"
                                            % (os.path.basename(_d2), _pl2, _pool2))
                    if _pl2 > _pool2:
                        _ov += 1
            except Exception:
                continue
            if _dg:
                _deg_runs.append((os.path.basename(_d2), _dg, _ov, _pool2))
                _deg_pools.add(_pool2)
                if _dg > _ov:
                    _deg_bad.append("%s 退化 %d > 超池 %d" % (os.path.basename(_d2), _dg, _ov))
    _deg_names = {n for n, _a, _b2, _p2 in _deg_runs}
    # ⚠ codex r45：`_DEG_EXPECT` 的**池子值**原来没被逐名用 —— 对调两条 run 的池子
    # （名字集合与池子集合都不变）仍会通过。逐名核。
    for _nm, _pool_exp in _DEG_EXPECT.items():
        _hit = [x for x in _deg_runs if x[0] == "pois200_" + _nm or x[0] == _nm]
        if _hit and _hit[0][3] != _pool_exp:
            _deg_bad.append("%s 的池子 %d≠%d" % (_nm, _hit[0][3], _pool_exp))
    if _deg_names != set(_DEG_EXPECT):
        _deg_bad.append("名单不符：多 %s / 少 %s"
                        % (sorted(_deg_names - set(_DEG_EXPECT)) or "无",
                           sorted(set(_DEG_EXPECT) - _deg_names) or "无"))
    # ⚠ 2026-09-26 中立复核 M4：这条**只核镜像、不核正文** —— 把正文的
    # 「six runs at four pool sizes」改成 seven，0 MISS（本项目第一盲区）。
    # 补两条：条数锚在 `runs at four pool sizes`（不含数字），池子种数锚在
    # `no counterexample`（**不能锚在含 four 的短语里**，那是自证）。
    ck_near("§III 退化 run 条数", num_words(6) + [6], "sec_model.tex",
            "runs at four pool sizes", window=60)
    ck_near("§III 退化 run 的池子种数", num_words(4) + [4], "sec_model.tex",
            "no counterexample", window=90)
    # 负面：两处已被 r44/复核推翻的措辞不许回来
    checks += 1
    if re.search(r"with\s+the\s+pool\s+halved", _cf2, re.I):
        fails.append(("§III 又写回「with the pool halved」（cap3_p75 是 75%，不是一半）",
                      "四条容量对照的池子是 50,716 ×3 + 76,074",
                      "sec_model.tex"))
    checks += 1
    if re.search(r"same\s+trace\s+and\s+the\s+same\s+engine\s+version", _cf2, re.I):
        fails.append(("§VI 又写回「same trace and the same engine version」（指代不清）",
                      "A100 跑的是主 trace；已改成 replaying the main trace",
                      "sec_xtrace.tex"))
    checks += 1
    if len(_deg_runs) != 6 or len(_deg_pools) != 4 or _deg_bad:
        fails.append(("§III「six runs at four pool sizes, no counterexample」与镜像不符",
                      "实测 %d 条 run / %d 种池子 %s%s"
                      % (len(_deg_runs), len(_deg_pools), sorted(_deg_pools),
                         ("；反例：" + "；".join(_deg_bad)) if _deg_bad else ""),
                      "results/{night,a100_night}/*/steps.jsonl"))

    # ---- 另外两处【并列的实验条件词】（2026-09-26 同一次扫出）----
    # (a) §VI 原来写「same trace and **engine build (identical checksum)**」。
    #     逐条核：A100 十条 run 的 `trace_md5` 全部 = `df4bdd37e5`（与主 trace 逐位一致）✓，
    #     但**引擎没有 checksum 这份记录** —— `metadata.json` 的 `build` 里只有
    #     TRACE / MEMFRAC / HICACHE_ARGS，仓库里唯一的引擎证据是
    #     `docs/a100_toolchain_20260925.md`「sglang 版本一致（0.5.10.post1）」。
    #     ⇒ 「identical checksum」只能挂 **trace**，不能挂 engine build。已改成
    #     「same trace and the same engine version」。
    # (b) §VII 的 25 档那条写「an earlier harness batch---**same day**, same trace and
    #     pool」。实测七条 `thr25_*`：五条 09-14、**两条 09-15**
    #     （`thr25_push_r2` 与 `thr25_hwsf` —— 而 `push_r2` 正是那句点名的 repeat）。
    #     ⇒ 措辞不确定（是 09-14 的 18:08、另一条 `push_r2` 是 09-15 的 10:21，
    #     跨了一天）⇒ 硬编码数字，锚在句子上（数字进锚 = 自证，见 CLAUDE.md）。
    _cf2 = re.sub(r"\s+", " ", alltext)
    checks += 1
    if re.search(r"engine build\s*\(identical checksum\)", _cf2, re.I):
        fails.append(("§VI 又把「identical checksum」挂在 engine build 上（只有 trace 有 checksum）",
                      "引擎的出处是版本一致（docs/a100_toolchain_20260925.md:11），不是 checksum",
                      "sec_xtrace.tex"))
    _tr_main = (json.load(open(os.path.join(ROOT, "results/night/pois200_cap2",
                                             "metadata.json"))).get("trace_md5")
                if os.path.exists(os.path.join(ROOT, "results/night/pois200_cap2",
                                               "metadata.json")) else None)
    _a100_md5, _a100_bad = set(), []
    for _d3 in sorted(glob.glob(os.path.join(ROOT, "results/night", "a100_*"))):
        _m3 = os.path.join(_d3, "metadata.json")
        if not os.path.exists(_m3):
            continue
        _v3 = json.load(open(_m3)).get("trace_md5")
        _a100_md5.add(_v3)
        if _tr_main and _v3 != _tr_main:
            _a100_bad.append("%s=%s" % (os.path.basename(_d3), _v3))
    # ⚠ 2026-09-26 codex r44：**漏掉一条 A100 run 仍会通过**。两个镜像根里同名 run 会重复，
    # 所以按【run 名字】去重后核条数（十条：cap1--5 / cap8 / cap16 / default / default_r2 / foyer_hz2）。
    _a100_names = set()
    for _root3 in ("results/night", "results/a100_night"):
        for _d4 in glob.glob(os.path.join(ROOT, _root3, "a100_*")):
            if os.path.exists(os.path.join(_d4, "metadata.json")):
                _a100_names.add(os.path.basename(_d4))
    # ⚠ codex r45：原来只核条数 —— **少一个预期名字、补一个新名字**仍是 10，会通过。
    _A100_EXPECT = {"a100_cap1", "a100_cap2", "a100_cap3", "a100_cap4", "a100_cap5",
                    "a100_cap8", "a100_cap16", "a100_default", "a100_default_r2",
                    "a100_foyer_hz2"}
    checks += 1
    if _a100_names != _A100_EXPECT:
        fails.append(("§VI 的 A100 run 名单变了",
                      "多 %s / 少 %s" % (sorted(_a100_names - _A100_EXPECT) or "无",
                                       sorted(_A100_EXPECT - _a100_names) or "无"),
                      "results/{night,a100_night}/a100_*/metadata.json"))
    checks += 1
    if len(_a100_names) != 10:
        fails.append(("§VI 的 A100 run 条数变了（正文说十条，含「three of the seven」那个集合）",
                      "%d 条：%s" % (len(_a100_names), sorted(_a100_names)),
                      "results/{night,a100_night}/a100_*/metadata.json"))
    checks += 1
    if _a100_bad or _a100_md5 != {_tr_main}:
        fails.append(("§VI「A100 与 3090 同 trace」与 metadata 不符",
                      "主 trace=%s，A100 有 %d 种：%s；不同：%s"
                      % (_tr_main, len(_a100_md5), _a100_md5, "；".join(_a100_bad) or "无"),
                      "results/night/a100_*/metadata.json"))
    # ⚠ 2026-09-26 codex r44：原来这条**只找正文里的短语**，数据改成三天也照样通过 ——
    # 是「措辞存在性检查」不是「日期事实检查」。现在从七条 `thr25_*` 的**首末步时间戳**现算。
    _thr25 = ["thr25_base", "thr25_nohw", "thr25_t95", "thr25_push", "thr25_push_r2",
              "thr25_nosf", "thr25_hwsf"]
    _days, _t25bad = set(), []
    for _r5 in _thr25:
        _p5 = os.path.join(ROOT, "results/night", _r5, "steps.jsonl")
        if not os.path.exists(_p5):
            _t25bad.append("%s 不在镜像里" % _r5); continue
        _ls5 = [json.loads(l) for l in open(_p5) if l.strip()]
        for _ts in (min(x["submit_timestamp"] for x in _ls5),
                    max(x["complete_timestamp"] for x in _ls5)):
            _days.add(datetime.datetime.fromtimestamp(_ts).date())
    # ⚠ 2026-09-26 中立复核 M3：原来只核「2 个不同的日子」—— 把两条 run 整体 +5 天
    # （变成 09-14 与 09-20，仍是两天）**照样通过**，而正文写的是 consecutive。
    _dd = sorted(_days)
    _adjacent = len(_dd) == 2 and (_dd[1] - _dd[0]).days == 1
    checks += 1
    if not _adjacent or _t25bad:
        fails.append(("§VII 的 25 档批次不再是【连续】两天（从 steps.jsonl 现算）",
                      "实测 %d 天：%s%s" % (len(_dd), [str(x) for x in _dd],
                                          ("；" + "；".join(_t25bad)) if _t25bad else ""),
                      "results/night/thr25_*/steps.jsonl"))
    checks += 1
    if len(_days) != 2 or _t25bad:
        fails.append(("§VII 的 25 档批次不再是「两天」（从 steps.jsonl 现算）",
                      "实测 %d 天：%s%s" % (len(_days), sorted(_days),
                                          ("；" + "；".join(_t25bad)) if _t25bad else ""),
                      "results/night/thr25_*/steps.jsonl"))
    # ⚠ 2026-09-26 codex r44：同一个 run 的两个窗口之间**时间也在走**（会话在换、阶段在变），
    # 「the only change being who else was on the machine」比记录强。已改成
    # 「the change in τ₂ tracks who else was on the machine」。
    checks += 1
    if re.search(r"the only change being who else", _cf2, re.I):
        fails.append(("§V 又出现「the only change being who else was on the machine」（窗口之间时间也在走）",
                      "同 run 两个窗口之间还经过了运行时间与阶段变化",
                      "sec_discussion.tex"))
    # ⚠ 2026-09-27：这条守卫**第一次有了退役通路**（`_direct_fail`）——
    # 它是直写 `fails.append`、不进 `ck`/`ck_near`，所以原来只能靠改代码关掉。
    # §Load 整节删除之后，正文里那个「两天」的日期句也随之删除（裁决第 1/2 条
    # 是「收缩主张范围」），于是它退役；值在 thr25_* 的 steps.jsonl 时间戳里，
    # 那两条**数据**守卫（下面「不再是连续两天 / 不再是两天」）还活着。
    if not _direct_fail("§VII 的 25 档批次又写回「same day」（实为跨 09-14/09-15 两天）",
                        "two consecutive days", "sec_discussion.tex") \
            and not re.search(r"two\s+consecutive\s+days", _cf2, re.I):
        fails.append(("§VII 的 25 档批次又写回「same day」（实为跨 09-14/09-15 两天）",
                      "五条 09-14、thr25_push_r2 与 thr25_hwsf 在 09-15；"
                      "若确实全部同一天，改成实际的那天并撤掉这条守卫",
                      "sec_discussion.tex"))

    # ---- 层对照那个「混杂配对」的**日期 / 卡 / harness 代**（2026-09-26 抓到两节互相矛盾）----
    # §IV 写「were run **a day apart on different cards**」，而 §III 写「The pair is a
    # **harness generation apart**, its two runs **three and a half days** and two GPUs
    # apart」—— **两节对同一件事给了两个数**，检查器一处没报（它不查「同一件事两处说法」）。
    # 逐条核 `metadata.json` + `steps.jsonl` 首末时间戳：
    #   混杂配对 = (`cap3_fixed`, `cap3_hc`)：**同 harness 代**（run_matrix `90958758c26b`、
    #     控制器 `2b573829083c` 两条相同）、**相隔 19.5 小时**（≈ 不到一天）、卡 2 vs 3；
    #   「去掉卡那一半」那个配对 = (`cap3_pd`, `cap3_hc`)：同卡（都在 3）、
    #     **相隔 3.59 天**、**不同代**（`b866b92c6eed`/`f825bc768188` vs 上面那对）。
    # ⇒ 已把 §III 那句改成「the same harness generation, about a day and two GPUs apart」
    #   + 「those two are three and a half days and a generation apart」。**3.5 天那个数没错，
    #   它属于另一个比较** —— 这正是原句的病：把两个比较的数并进了一句。
    _pair_bad = []
    try:
        _meta = {}
        _span = {}
        for _r in ("pois200_cap3_fixed", "pois200_cap3_hc", "pois200_cap3_pd"):
            _d = os.path.join(ROOT, "results/night", _r)
            _meta[_r] = json.load(open(os.path.join(_d, "metadata.json")))
            _ls = [json.loads(l) for l in open(os.path.join(_d, "steps.jsonl")) if l.strip()]
            _span[_r] = (min(x["submit_timestamp"] for x in _ls),
                         max(x["complete_timestamp"] for x in _ls))
        _f, _h, _p = "pois200_cap3_fixed", "pois200_cap3_hc", "pois200_cap3_pd"
        _day = 86400.0
        # ⚠ codex r46：这一对原来也取 `abs()` —— **把 `cap3_fixed` 整条挪到 `cap3_hc`
        # 之后照样通过**（第二对上一轮已改成有符号，这一对漏了）。同样改成有符号 + 断言方向。
        _gap_fh = (_span[_h][0] - _span[_f][1]) / _day         # 混杂配对：host 侧必须在 device 侧之后
        # ⚠ codex r45：原来取绝对值，**先后颠倒也算过**。改成有符号 + 断言方向。
        _gap_ph = (_span[_p][0] - _span[_h][1]) / _day         # repeat 与 host 侧（必须在后）
        # (1) 混杂配对：同代、不到一天半、不同卡
        # ⚠ codex r45：两边 `code` **都缺**时 `!=` 为假 ⇒ 被当成「同代」。先要求非空。
        if not (_meta[_f].get("code") and _meta[_h].get("code")):
            _pair_bad.append("cap3_fixed/cap3_hc 的 code 哈希缺失（无法判代）")
        elif (_meta[_f]["code"] != _meta[_h]["code"]):
            _pair_bad.append("cap3_fixed/cap3_hc 的 code 哈希不再相同（正文说 the same harness generation）")
        if _gap_fh <= 0:
            _pair_bad.append("cap3_hc 不再晚于 cap3_fixed（host 侧应该在 device 侧之后）")
        if not (_gap_fh < 1.5):
            _pair_bad.append("cap3_fixed→cap3_hc 相隔 %.2f 天（正文说 about a day）" % _gap_fh)
        if _meta[_f]["gpu"] == _meta[_h]["gpu"]:
            _pair_bad.append("cap3_fixed/cap3_hc 同卡了（正文说 two GPUs apart）")
        # (2) repeat 与 host 侧：同卡、3~4 天、不同代
        if _meta[_p]["gpu"] != _meta[_h]["gpu"]:
            _pair_bad.append("cap3_pd 与 cap3_hc 不同卡（正文说 repeat 落在 host 侧那张卡）")
        if _gap_ph <= 0:
            _pair_bad.append("cap3_pd 不再晚于 cap3_hc（重复跑应该在 host 侧之后）")
        if not (3.0 <= _gap_ph <= 4.0):
            _pair_bad.append("cap3_pd 与 cap3_hc 相隔 %.2f 天（正文说 three and a half days）" % _gap_ph)
        if _meta[_p]["code"] == _meta[_h]["code"]:
            _pair_bad.append("cap3_pd 与 cap3_hc 同代了（正文说 a generation apart）")
    except Exception as _e:
        _pair_bad.append("读不到 metadata/时间戳：%s" % _e)
    checks += 1
    if _pair_bad:
        fails.append(("§III/§IV 的层对照配对（日期/卡/harness 代）与 metadata 不符",
                      "；".join(_pair_bad), "results/night/pois200_cap3_{fixed,hc,pd}/metadata.json"))
    # 负面：把两个比较并进一句的旧措辞不许回来
    checks += 1
    if re.search(r"harness\s+generation\s+apart,\s*its\s+two\s+runs", _cf2, re.I):
        fails.append(("§III 又出现「a harness generation apart, its two runs three and a half days "
                      "and two GPUs apart」（把两个比较并进一句）",
                      "混杂配对是同代 + 19.5 小时；3.5 天/不同代属于 repeat vs host 侧那对",
                      "sec_model.tex"))
    ck_near("§III 混杂配对的日期（≈ 不到一天）", "about a day", "sec_model.tex",
            "harness generation", window=90)
    ck_near("§III repeat 与 host 侧的间隔（3.5 天）", "three and a half days", "sec_model.tex",
            "though those two remain", window=120)

    # ---- §repro 的 cap1 干净重跑（2026-09-26）：验证「带旗但未受损的 run 可以保留」----
    _rp = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/runs_precise.csv"))}
    _a, _b = _rp.get("pois200_cap1"), _rp.get("pois200_cap1_r2")
    if _a and _b:
        _wa, _wb = float(_a["wall_min"]), float(_b["wall_min"])
        ck_near("§repro cap1_r2 的墙钟", "%.1f" % _wb, "sec_discussion.tex", "it lands at")
        ck_near("§repro cap1 的墙钟", "%.1f" % _wa, "sec_discussion.tex", "flagged run's")
        ck_near("§repro cap1_r2 快多少", "%.1f" % (100.0 * (_wa - _wb) / _wa),
                "sec_discussion.tex", "faster")
        # **区间必须与 replicates.csv 同源** —— 正文写「inside the 1.2--4.7% spread」
        _rr = sorted(float(r["wall_range_pct"]) for r in
                     load(os.path.join(ROOT, "paper/data/replicates.csv")))
        if _rr:
            # ⚠ `+1e-9` 不是装饰：`replicates.csv` 存的是 **2 位小数**（7.05），
            # 而 7.05 的浮点表示略小于 7.05，`%.1f` 会给出 **7.0** —— 真值 7.05499
            # 的 1 位小数是 **7.1**。不加这个 epsilon 就是「拿舍入后的列再舍入一次」，
            # 复算的人会得到 7.1（2026-09-26 独立复核子 agent 第 18 轮抓到）。
            ck_near("§repro 重复散布下界", "%.1f" % (_rr[0] + 1e-9), "sec_discussion.tex", "spread of the")
            ck_near("§repro 重复散布上界", "%.1f" % (_rr[-1] + 1e-9), "sec_discussion.tex", "spread of the")
    # ---- §IV 脚注把 SLO 散布**逐个列了出来**（0.5, 0.8, 1.0, 3.9, 5.1）----
    # 这是一句**枚举**：多一组就少一个数，而「值在不在正文里」的检查一个都不会响
    # （五个旧值都还在，只是那句话不再是完整的枚举）。2026-09-26 加；触发它的是
    # `cap3_pd` 落地会给 `replicates.csv` 添一组（设备侧 cap3 重复对）。
    _rs = load(os.path.join(ROOT, "paper/data/replicates.csv"))
    if _rs:
        ck_near("§IV 重复配置的组数", num_words(len(_rs)), "sec_results.tex",
                "have been run more than once", window=120)
        # ⚠ 2026-09-26：§II **同一句话**也引了这个集合，但只引 **min/max 区间** ——
        # 逐组枚举的守卫在 §IV，§II 的区间**此前没人守**。某一组的值一变、
        # 而它恰是 min 或 max 时，§II 会静默过期（§IV 的逐组守卫只保证「枚举完整」）。
        _sl = sorted(float(r["slo_range_pp"]) for r in _rs)
        ck_near("§II 重复散布区间下界", "%.1f" % (_sl[0] + 1e-9), "sec_background.tex",
                "SLO spread of configurations", window=120)
        ck_near("§II 重复散布区间上界", "%.1f" % (_sl[-1] + 1e-9), "sec_background.tex",
                "SLO spread of configurations", window=120)
        # ⚠ codex r45：两个 `ck_near` 只核「两个数都出现了」—— 把「0.5 to 5.1」
        # **对调成「5.1 to 0.5」两个都仍返回真**。补一条次序判据。
        _sb = re.sub(r"\s+", " ", P.get("sec_background.tex", ""))
        _bi = _sb.find("SLO spread of configurations")
        if _bi >= 0:
            _seg = _sb[_bi:_bi + 160]
            _lo_s, _hi_s = "%.1f" % (_sl[0] + 1e-9), "%.1f" % (_sl[-1] + 1e-9)
            checks += 1
            _plo, _phi = _seg.find(_lo_s), _seg.find(_hi_s)
            if _plo < 0 or _phi < 0 or _plo > _phi:
                fails.append(("§II 重复散布区间的**次序**反了（或有一个数不在窗口里）",
                              "下界 %s 在第 %d 字符、上界 %s 在第 %d 字符"
                              % (_lo_s, _plo, _hi_s, _phi), "sec_background.tex"))
        # ⚠ 2026-09-27：**同一个派生量的第三、第四处表述此前没有守卫。**
        # §V 与 §VI 都写「the 0.5 to 4.6 pp that separates repeats of a single
        # controller configuration」。它**不是** `slo_range_pp`（那是 §II 那句
        # 「SLO spread of configurations」，值域 0.50--5.11，上面已有守卫），
        # 而是**每条控制器重复组【内部】Δ 的全距**再取 min/max
        # （2026-09-27 实测：base 0.49 / horizon=1 4.65 / horizon=2 0.51）。
        # 这个量**不在任何 CSV 里** —— 它此前是正文里手算的，所以：
        # 只要 `replicates.csv` 多一组（或某组多一条 run），**两端都可能动**，
        # 而 §II 的守卫盯的是另一个量，**不会有任何检查响**。
        # 触发它的是 `foyer_scan` / `foyer_sf0_*` 两组重复在 2026-09-27 落地：
        # scan 是 +1.30，sf0 是 −0.55，两组的 Δ 全距都可能把 min 或 max 推走。
        # ⚠⚠ 2026-09-27（**已解决**）：这两段注释原来写的是「本守卫只在
        # `table1.csv` 里能看到的 run 上算，所以 base 组是 n=2 而不是 n=4」，
        # 以及「『最紧的那一组』不许照这个基准补守卫 —— 会得到假失败」。
        # **两段现在都作废**：基准已经修正（改用 `runs_precise.csv` +
        # `frontier.front_slo()`，见下面那段），base 组回到 n=4（全距 1.912），
        # 「最紧的那一组」也因此**可以**守、并且**已经守上了**。
        #
        # 留下来的教训（写在这里，因为这是它的现场）：
        #   **同一个量换一个基准，结论可以从「base 最紧」翻成「hz2 最紧」** ——
        #   而错误基准下的守卫会**假失败**，把人骗去改一句本来正确的话。
        #   我这一轮已经因为取错基准险些改错 §VI 那一句（见 CLAUDE.md）。
        #   所以：**算派生量之前，先问「这个集合的定义在哪、我取的是不是它」。**
        # ⚠ 2026-09-27：**「拿两个已舍入的列相减」** —— 本项目明令禁止的那一类，
        # 而它在正文里活了很久，因为**没有任何守卫**。
        # §VII 与 §III 都写「bought with / costs ... 43.7\,pp of SLO」，
        # 真值是 `table1.csv` 全精度相减：foyer_hc 89.7898 − foyfix_hc 46.1461
        # = **43.6437 ⇒ 43.6**。43.7 只有把**表里印出的两位数**相减（89.8 − 46.1）
        # 才拿得到 —— 换任何一条基准 run（`_r2` 89.5896、或两次均值 89.6897）
        # 都得不到一位小数为 43.7 的结果（分别是 43.4 / 43.5）。
        # 同段另外三个差值（idle 13.8 / busy 11.1 / wall 2.7）**都是全精度算完再舍入**，
        # 所以这不是「两套口径」，是**一处抄错**。
        # 发现它的路径：逆向扫描「出现在 ≥2 个 .tex、又不在任何 CSV 里的数」，
        # 它是仅有的两个候选之一，逐个人工核之后确认。
        _t1s = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/table1.csv"))}
        if "foyer_hc" in _t1s and "foyfix_hc" in _t1s:
            _dslo = float(_t1s["foyer_hc"]["slo_pct"]) - float(_t1s["foyfix_hc"]["slo_pct"])
            ck_near("§VII 全关节流那条的 SLO 代价", "%.1f" % _dslo,
                    "sec_discussion.tex", "minutes) and", window=60)
            ck_near("§III 同一处的 SLO 代价", "%.1f" % _dslo,
                    "sec_model.tex", "bought with", window=40)
        # ⚠ 2026-09-27：§II 那句把 `horizon=1` **三次运行的 Δ 逐个列了出来**
        # （「landing at $0.93$, $5.58$ and $3.22$\,pp below it across its three
        # runs」），而这三个数**只有表 I 那一行有守卫**（那条锚在 `sec_results.tex`）
        # —— §II 这一处此前**没有任何检查**。同一族：「同一个数在别处出现，
        # 不等于它用在了这里」。
        # 发现它的办法值得记：逆向扫描「出现在 ≥2 个 .tex 文件、又不在任何
        # `paper/data/*.csv` 里」的数 —— 它当时**没露头**，因为 §II 印 2 位小数
        # 而 CSV 是全精度（−5.5755），扫描的相等判定抓不到。
        # ⇒ 那条扫描能收窄范围，**不能替代逐个看候选**。
        _t1h = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/table1.csv"))}
        for _n in ("foyer_hz1", "foyer_hz1_r2", "foyer_hz1_r3"):
            if _n in _t1h and _t1h[_n].get("delta_pp"):
                ck_near("§II %s 的 Δ（逐个列出）" % _n,
                        "%.2f" % abs(float(_t1h[_n]["delta_pp"])),
                        "sec_background.tex", "landing at", window=60)
        # ⚠⚠ 2026-09-27（**基准修正**）：这里原来用 `table1.csv` 的 `delta_pp`
        # 算每组的 Δ 全距。**那是错的基准** —— `pairA_foyerhc` / `pairB_foyerhc`
        # 根本不在 `table1.csv` 里，于是 Foyer base 组被算成 **n=2**（全距 0.49）
        # 而不是真值 **n=4**（1.912）。
        #
        # 后果不是「误差 0.02」，是**结论相反**：
        #     错误基准：base 0.49 / hz1 4.65 / hz2 0.51 ⇒ 最紧的是 **base**
        #     正确基准：base 1.91 / hz1 4.65 / hz2 0.51 ⇒ 最紧的是 **hz2** ✓（正文）
        # 而正文写的正是「horizon=2's own two runs are the tightest of the three
        # groups at 0.5pp」。**照错误基准补守卫会得到一条假失败，然后去改一句本来
        # 正确的话** —— 我这一轮已经因为取错基准险些改错 §VI 那一句（见 CLAUDE.md）。
        #
        # 正确来源：`runs_precise.csv`（全精度坐标，覆盖全部 run）+ `frontier` 的
        # `front_slo()`（包络插值的**唯一实现**）。Δ 不另写公式。
        try:
            sys.path.insert(0, os.path.join(ROOT, "scripts", "lab"))
            import frontier as _FRd
            _rpd = {r["run"]: r for r in
                    load(os.path.join(ROOT, "paper/data/runs_precise.csv"))}
        except Exception as _e:                    # 不静默兜底：兜底=换基准=结论可能相反
            checks += 1
            fails.append(("§V/§VI 控制器重复 Δ 全距：拿不到 `frontier`/`runs_precise`",
                          "**不做降级计算**（降级会换成错的基准），%r" % _e, "scripts/lab"))
            _rpd = None

        def _is_static(_nm):
            return _nm.startswith("cap") or re.match(r"pair[AB]_cap", _nm) is not None

        def _delta_of(_nm):
            _r = _rpd.get("pois200_" + _nm) if _rpd else None
            if not _r:
                return None
            return float(_r["slo_pct"]) - _FRd.front_slo(float(_r["wall_min"]))

        _foy_ranges = []
        if _rpd is not None:
            for _r in _rs:
                _rn = (_r["runs"] or "").split()
                if len(_rn) < 2:
                    continue
                # 「控制器配置」= 非静态锚点的重复组（Foyer / FIX / AIMD 那几条）
                if any(_is_static(x) for x in _rn):
                    continue
                _dv = [v for v in (_delta_of(x) for x in _rn) if v is not None]
                if len(_dv) >= 2:
                    _foy_ranges.append((_r["group"], max(_dv) - min(_dv)))
        if _foy_ranges:
            _fr = sorted(v for _, v in _foy_ranges)
            # ⚠ 2026-09-27（中立复核 r48 第 2 条）：**同一句话在 §I 也有一份**，
            # 而那一份的集合限定语**漏了 controller**（写的是「repeats of a
            # **fixed** configuration」）—— 按那个集合，真值是 **0.49 to 7.55**
            # （七组全算，`cap4+HC` 一组就 7.55），**不是 0.5 to 4.6**。
            # 这是「区间必须写出是哪个集合」那一类：限定语一宽，数就不成立。
            # 现在三处（§I / §V / §VI）都锚上，且**都要求 controller 这个词**
            # 出现在锚短语里 —— 漏了它就匹配不到，会报 MISS。
            for _f, _tag in (("sec_results.tex", "§V"), ("sec_discussion.tex", "§VI"),
                             ("sec_intro.tex", "§I")):
                _kw = ("that separates repeats of a single" if _tag != "§I"
                       else "repeats of a single")
                ck_near("%s 控制器重复 Δ 全距下界" % _tag, "%.1f" % (_fr[0] + 1e-9), _f,
                        _kw, window=140)
                ck_near("%s 控制器重复 Δ 全距上界" % _tag, "%.1f" % (_fr[-1] + 1e-9), _f,
                        _kw, window=140)
            # §V 还把**组数**写成了词（「the tightest of the three groups」）——
            # 组数一变这个词就是错的，而 `three` 在正文里到处都有，`ck` 查不出来。
            ck_near("§V 控制器重复组数（tightest of the N groups）",
                    num_words(len(_foy_ranges)), "sec_results.tex",
                    "tightest of the", window=60)
            # ⚠ 2026-09-27 新补：**「最紧的那一组」此前没有守卫**。
            # 正文写「\texttt{horizon}=2's own two runs are the tightest of the three
            # groups at 0.5pp」—— 组名与数值都是派生的。
            # ⚠ 这条**只有在上面修正过的基准下才成立**（错误基准会算出 base 最紧）。
            _tg = min(_foy_ranges, key=lambda x: x[1])
            ck_near("§V 最紧的那组是 horizon=2",
                    "\\texttt{horizon}=2", "sec_results.tex",
                    "the tightest of the", window=70)
            ck_near("§V 最紧那组的全距", "%.1f" % (_tg[1] + 1e-9), "sec_results.tex",
                    "the tightest of the", window=60)
        for _r in _rs:
            ck_near("§IV 重复组的 SLO 散布 %s" % _r["group"][:22],
                    "%.1f" % float(_r["slo_range_pp"]), "sec_results.tex",
                    "SLO spreads are", window=260)

    # ---- 2026-09-27：**限定语在场**守卫（压缩会静默关掉它们）----
    # 由 codex r48 第 19 条触发：旧 §VII 明写「25-session trace carries no
    # arrival times」，压缩时那句被删掉，**换成了「once arrivals and phase are
    # accounted for」** —— 意思正好反了，而**没有任何检查会发现**：
    # 数值守卫只查数，文字从数量到方向都不在覆盖里。
    # 事实核对：`data/replay_night25.csv` 的表头是
    #   session_id,round_idx,prefix_len,input_len,output_len,tool_wait_after_ms
    # —— **没有 arrival_time 列**，所以「已对 arrival 作控制」是**做不到**的。
    # ⚠ 这类守卫只能钉「某个限定语还在不在」，钉不了「有没有说出别的错话」——
    # 它是**下限**，不是证明。但比零覆盖强：被删掉的那一刻它会响。
    # ⚠ 2026-09-27：篇幅手术把 §VII 那句**整句**删了（现在只说
    # 「from before we recorded build hashes」），于是「限定语必须在场」这条
    # 正向守卫**永远**报 MISS —— 而它要防的那个误读（把 25 档读成「已对 arrival
    # 作控制」）随着句子一起消失了。**留住危险的那一半**：改成负向守卫，
    # 禁止那个**反转说法**复活。事实不变：`data/replay_night25.csv` 的表头没有
    # arrival_time 列（只有 session_id/round_idx/prefix_len/input_len/output_len/
    # tool_wait_after_ms），所以「已对 arrival 作控制」在那张 trace 上做不到。
    _Q = [("sec_discussion.tex",
           r"once arrivals|arrivals and phase|arrivals are (?:accounted|controlled)",
           "§VII 又写回「已对 arrival 作控制」的说法，而那张 trace 里根本没有 arrival_time 这一列"),
          ]
    for _f, _rx, _why in _Q:
        checks += 1
        if re.search(_rx, P.get(_f, "")):
            fails.append(("§VII 把 25 档的 arrival 写成已受控", _why, _f))
        elif VERBOSE:
            print("  OK   没有把 25 档的 arrival 说成已受控（%s）" % _f)

    # ---- §III 的拟合（r 与最大残差）—— 2026-09-27 补生成器后才有守卫 ----
    # ⚠ 此前这两个数**不在任何脚本里**（中立复核 r49 指出）：复核者只能按「最自然的
    # 定义」复现，记成「按自然定义复现成功，不算口径已核」。现在口径固定成
    # `scripts/lab/gen_fit.py`，本守卫读它的产物 —— 数字这才算**追得到脚本**。
    _ftp = os.path.join(ROOT, "paper/data/fit.csv")
    if os.path.exists(_ftp):
        _ft = load(_ftp)
        if _ft:
            _f0 = _ft[0]
            ck_near("§III 拟合的 r", "+%.2f" % float(_f0["r"]), "sec_model.tex",
                    "straight line through")
            ck_near("§III 拟合的最大残差", "%.2f" % float(_f0["max_abs_resid_ms"]),
                    "sec_model.tex", "largest residual of")
            ck_near("§III 拟合的点数", num_words(len(_f0) and int(_f0["n"])),
                    "sec_model.tex", "step costs for")

    # ---- 独立复算层（2026-09-26 接进来自动跑）----
    # `independent_frontier_check.py` **不 import 任何生成器**，从 trace 与
    # steps.jsonl 从头再实现一遍复用上界、锚点墙钟/SLO、包络与各臂 Δ，与
    # table1.csv 对拍 —— 它挡的是「生成器的**定义**写错、正文与 CSV 一致地错」
    # 那一类（检查器本身查不出来）。
    # ⚠ 原来它只是个手动脚本，**没有任何东西会提醒你去跑它** —— 这一轮把它接进来。
    _ic = _sp.run([sys.executable, os.path.join(ROOT, "scripts", "lab",
                                                "independent_frontier_check.py"),
                   os.path.join(ROOT, "data", "replay_pois200_l04.csv"),
                   os.path.join(ROOT, "results", "night")],
                  capture_output=True, text=True)
    checks += 1
    if _ic.returncode != 0 or "全部逐位相符" not in _ic.stdout:
        fails.append(("independent_frontier_check 没通过",
                      (_ic.stdout.strip().splitlines() or ["(无输出)"])[-1][:70]
                      + ("  rc=%d" % _ic.returncode if _ic.returncode else ""),
                      "scripts/lab/independent_frontier_check.py"))

    # ---- 全局守卫：paper/data/*.csv 里不该再出现【被替代的旧 run】----
    # 2026-09-25：`swap_superseded.py` 只改生成器的 run 列表、**不重生成数据**，
    # 于是我漏掉的那几张表（arrival_slo/stall/idle_pooled/frontier_split）都留着旧 run。
    # 逐表去修是治标；这条守卫一次覆盖全部 —— 只要哪张表还引用旧 run 就报。
    # 豁免：本来就是「全量清单」的表（它们按设计覆盖机器上每一条 run）。
    INVENTORY = {"concurrency.csv", "runs_precise.csv", "projection.csv",
                 "gate_attrib.csv", "superseded.csv"}
    _sup = set()
    for _gp in ("gen_eviction.py", "gen_repeat_spread.py"):
        _gs = open(os.path.join(ROOT, "scripts/lab", _gp), encoding="utf-8").read()
        _m = re.search(r"SUPERSEDED\s*=\s*\{(.*?)\}", _gs, re.S)
        if _m:
            _sup |= set(re.findall(r'"([A-Za-z0-9_]+)"', _m.group(1)))
    _sup = {k.replace("pois200_", "") for k in _sup}
    for _f in sorted(glob.glob(os.path.join(ROOT, "paper/data", "*.csv"))):
        _bn = os.path.basename(_f)
        if _bn in INVENTORY:
            continue
        _rr = load(_f)
        if not _rr:
            continue
        _key = "run" if "run" in _rr[0] else ("arm" if "arm" in _rr[0] else None)
        if not _key:
            continue
        _stale = sorted({str(r[_key]).replace("pois200_", "") for r in _rr
                         if str(r[_key]).replace("pois200_", "") in _sup})
        if _stale:
            fails.append(("%s 仍引用被替代的旧 run" % _bn, "、".join(_stale), _bn))

    # ---- frontier_split.csv：辅助表，但必须与表 I 的 Δ 一致 ----
    # 它【不在正文里】，可是读者会打开 paper/data/ 逐个看。2026-09-25 codex 第 19 轮
    # 就是因为这张表给 hz1 +0.22（正文 −0.93）而判「从 paper/data 能追到互相矛盾的答案」。
    _fs = {r["arm"]: r["delta_pp"] for r in
           load(os.path.join(ROOT, "paper/data/frontier_split.csv")) if r.get("front") == "mixed"}
    _tt = {r["run"]: r["delta_pp"] for r in load(os.path.join(ROOT, "paper/data/table1.csv"))}
    # ⚠⚠⚠ 2026-09-27（r57 中立复核 7）：**这组检查此前是【空转的】。**
    # 原写法是 `ck(desc, val, "frontier_split.csv", tier="S")` —— 而 `_src_of()`
    # 对 `.csv` **一律落到空串**（它只认 `paper/*.tex` 与 supplement 的 `.md`），
    # 于是 `has("", val)` 恒 False、恒走 `tier="S"` 的 secondary 分支
    # （打印成 `..`、**不计入退出码**）。
    # 复核者构造实测：把 `mixed` 行的 `−1.24` 改成 `−9.99`、`device` 行的 `87.20`
    # 改成 `99.99` ⇒ **0 MISS**。把兜底临时改成 `alltext` 后这组**全部印 OK** ——
    # 说明它**想查的是正文**，只是 `where` 指错了文件。
    #
    # **但这里本来就不该用 `ck`**：这条判据是 **CSV 对 CSV**（`frontier_split` 的
    # `mixed` 行 vs `table1` 的同名 run），不是「值出现在正文里」。
    # ⇒ 换成**直接比较**，并让它**真的会失败**。这正好接住 2026-09-25 codex 第 19 轮
    # 抓到的那一类（`frontier_split` 给 hz1 +0.22 而正文 −0.93 ——
    # 「读者从 paper/data 能追到互相矛盾的答案」）。
    for _k, _v in _fs.items():
        if _k in _tt:
            checks += 1
            if abs(float(_v) - float(_tt[_k])) > 0.005:      # 两边都是 %.4f，留 0.005 容差
                fails.append(("frontier_split 的 %s 混合判决与表 I **对不上**" % _k,
                              "frontier_split=%s 表 I=%s" % (_v, _tt[_k]), "paper/data"))
            elif VERBOSE:
                print("  OK   frontier_split 的 %s 混合判决与表 I 一致 %s" % (_k, _v))
        else:
            # ⚠ 原来这里直接 skip —— 于是**被替代的旧 run 留在表里也永远发现不了**。
            # 2026-09-25 实测：frontier_split.csv 还留着 foyer_hz0（−13.60）与
            # foyer_hz2（−4.81），而表 I 已经是 hz0_r2 的 −7.19 / hz2_r2 的 −0.30。
            # 读者打开 paper/data/ 会追到互相矛盾的答案 —— 正是 codex 第 19 轮
            # 为另一条臂判过的那一类。**缺的键要报，不能跳过**（纪律 3）。
            fails.append(("frontier_split 的 %s 在表 I 里没有对应行（是不是被替代的旧 run？）" % _k,
                          _v, "frontier_split.csv"))

    # ---- 图 3（fig7_elasticity）的图注：此前**零守卫**（2026-09-27 补）----
    # ⚠ 与退役名单里那个「图 3 图注的 excess 区间（33 条）」**不是同一张图** ——
    # 那一条指的是压缩时删掉的一张旧图（它的区间是 8--40），名字撞车但对象不同。
    # 它是全文唯一没有任何守卫的展示物。图注里那三个数逐个从 `decomp.csv` 现取，
    # 锚在该图注独有的短语上（`sec_model.tex` 里别处没有这些短语）。
    _dd6 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    _hc6 = ["pairB_cap2hc", "cap4_hc"]
    _dv6 = ["cap2", "cap5"]
    if all(k in _dd6 for k in _hc6 + _dv6 + ["cap8_hc"]):
        ck_near("图 3（fig7_elasticity）图注 host-tier 曲线的两个端点",
                " to ".join("%.1f" % float(_dd6[k]["step_back_ms"]) for k in _hc6),
                "sec_model.tex", "host-tier curve rises only", window=120)
        ck_near("图 3（fig7_elasticity）图注 device-only 曲线的两个端点",
                " to ".join("%.1f" % float(_dd6[k]["step_back_ms"]) for k in _dv6),
                "sec_model.tex", "device-only\ncurve over a comparable span rises", window=120)
        ck_near("图 3（fig7_elasticity）图注 1.73 之后的那个点",
                "%.1f" % float(_dd6["cap8_hc"]["step_back_ms"]),
                "sec_model.tex", "beyond 1.73 it climbs to", window=80)
    # 图注里那个 excess 区间（**与 §III 同源**，都取 decomp.csv 的 excess_pct）
    _ex6 = [float(_dd6[k]["excess_pct"]) for k in ("cap1", "cap2", "cap3_fixed", "cap4", "cap5")
            if k in _dd6 and _dd6[k].get("excess_pct")]
    if _ex6:
        ck_near("图 3（fig7_elasticity）图注的 τ₁/τ₂ excess 区间",
                "%.1f--%.1f" % (min(_ex6), max(_ex6)),
                "sec_model.tex", "exceeds $\\tau_2$ by", window=60)

    # ---- §III 的那张「device-only vs host tier」裸表（2026-09-27 补）----
    # ⚠ 这张表是**论文 tier 主张的核心证据**（8 行 × R̄/realized/recomputed 三排），
    # 而它此前**整张没有任何守卫** —— 只有零散几个值被别处的检查顺带提到。
    # 判据：从 `reuse.csv` 现算那两队（device-only = cap1..cap5；host tier =
    # pairB_cap2hc/cap3_hc/cap4_hc/cap5_hc），拼成**复合串**再比 —— 短数（8.6、92.5）
    # 单查必然撞车（本项目栽过多次）。
    _ru2 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/reuse.csv"))}
    for _tag, _ks in (("device-only", ["cap1", "cap2", "cap3_fixed", "cap4", "cap5"]),
                      ("host tier", ["pairB_cap2hc", "cap3_hc", "cap4_hc", "cap5_hc"])):
        if not all(k in _ru2 for k in _ks):
            fails.append(("§III 裸表的 %s 队缺 run（守卫生效不了）" % _tag,
                          "；".join(k for k in _ks if k not in _ru2), "paper/data/reuse.csv"))
            continue
        _r = " & ".join("%.2f" % float(_ru2[k]["Rbar_busy"]) for k in _ks)
        # 表里 R̄ 那排是 `1.00 & 1.27 & …`，首位前面还有对齐用的空白
        ck_near("§III 裸表 %s 的 R̄ 排" % _tag, _r, "sec_model.tex",
                "device-only &" if _tag == "device-only" else "host tier", window=200)
        _e = " & ".join("%.1f" % (100 * float(_ru2[k]["realized_frac"])) for k in _ks)
        ck_near("§III 裸表 %s 的 realized 排" % _tag, _e, "sec_model.tex",
                "realized (\\% of bound)", window=260)
        _c = " & ".join("%.1f" % (float(_ru2[k]["recompute_tok"]) / 1e6) for k in _ks)
        ck_near("§III 裸表 %s 的 recomputed 排" % _tag, _c, "sec_model.tex",
                "recomputed (M)", window=260)

    # ---- §III 的 host-tier 集合：判据 + 两条具名排除 必须正好等于【eviction.csv】的行数 ----
    # ⚠⚠ 2026-09-27：**这里原来读的是 `reuse.csv`，那是错的源。**
    # `reuse.csv` 的 `family=hicache` 是 **26** 行，而正文的「the twenty-eight host-tier
    # runs that completed this trace at a *single* configuration」指的是
    # `gen_eviction.py` 那个集合 —— 它在 `eviction.csv` 里是 **28** 行
    # （判据 + 具名排除 EXCLUDED / SUPERSEDED / NOT_SINGLE_CONFIG 都写在那个生成器里）。
    # 两个文件的 hicache 行数差 2，于是这条检查**长期在报一个假的 MISS**，
    # 而它报的值（26）看起来完全像一个真数 —— 是本项目「守卫读数据文件、正文读论文那张表」
    # 那一条的又一次。**判据的来源必须与正文那句话的来源相同。**
    # （对账 agent 正确地**拒绝退役**这条 —— 它报的是真信号，只是信号在守卫这一侧。）
    _ev = load(os.path.join(ROOT, "paper/data/eviction.csv"))
    _hc = [r for r in _ev if str(r.get("hicache")) in ("1", "True")]
    ck("host-tier 集合条数（§III，源=eviction.csv）", str(len(_hc)), "sec_model.tex")
    if "foyer_hz1_r2" in {r["run"] for r in _hc}:
        ck("§III 被点名排除的 hz1_r2 混进了集合", "NOPE", "sec_model.tex")

    # ---- superseded.csv：§discussion 引的「污染 vs 干净」复用值 ----
    for r in load(os.path.join(ROOT, "paper/data/superseded.csv")):
        ck("superseded %s 复用占比" % r["run"], r["reuse_frac"], "sec_discussion.tex")
        ck("superseded %s τ₂" % r["run"], r["tau2_ms"], "sec_discussion.tex")

        # τ₁ 必须与 gen_decomp 的 step_back_ms **逐位一致** —— 同一个量，两条管线，
        # 必须共用定义（CLAUDE.md 纪律 2）。2026-09-25 codex 第 21 轮发现它们差 0.1 ms
        # （旧 bres 这条管线给 34.2、gen_decomp 给 34.1），原因是 gen_superseded 自己
        # 又写了一份实现，把每个零样本固定算成 5 秒。修完之后两边都走
        # gen_decomp.busy_stats；下面这段就是那次事故的回归护栏。
        _d = os.path.join(ROOT, "results/night", "pois200_" + r["run"])
        if os.path.isdir(_d):
            _iu = importlib.util
            _sp = _iu.spec_from_file_location(
                "_gd", os.path.join(ROOT, "scripts/lab/gen_decomp.py"))
            _GD = _iu.module_from_spec(_sp)
            _sp.loader.exec_module(_GD)
            _steps = [json.loads(l) for l in open(os.path.join(_d, "steps.jsonl")) if l.strip()]
            _tok = sum(s.get("output_len_actual") or 0 for s in _steps)
            if _tok:
                _sb = "%.1f" % _GD.busy_stats(
                    _GD.read_metrics(os.path.join(_d, "metrics.csv")), _tok)[6]
                if _sb != r["tau1_ms"]:
                    fails.append(("superseded %s τ₁ ＝ gen_decomp 的步成本" % r["run"],
                                  "%s vs %s" % (r["tau1_ms"], _sb),
                                  "scripts/lab/gen_decomp.py（共用定义被破坏了）"))

    # ---- §VI 的两个 +0.40（realhr 控制器臂的重复佐证）----
    _rx = load(os.path.join(ROOT, "paper/data/reuse_x.csv"))
    if _rx:
        import importlib.util as _iu
        _sp = _iu.spec_from_file_location("_fr2", os.path.join(ROOT, "scripts/lab/frontier.py"))
        _FR = _iu.module_from_spec(_sp); _sp.loader.exec_module(_FR)
        _FR.RESULTS = os.path.join(ROOT, "results/night")
        for _r in ("realhr_foyer", "realhr_foyer_r2"):
            _s = _FR.summarise(_r)
            if _s:
                _f = _FR.front_slo_xtrace(_s["wall"]) if hasattr(_FR, "front_slo_xtrace") else None
                if _f is None:
                    # realhr 的前沿在 gen_elasticity_x 里建，frontier.py 不管这条 trace；
                    # 这里至少把墙钟与 SLO 本身钉住（正文引的是它们派生的 Δ）。
                    # ⚠ 2026-09-27 活性审计：这一行原来是
                    #   `ck(...) if _s["slo"] < 99.95 else None`
                    # —— 两条 realhr run 的 SLO **恰好都是 100.0**，条件**恒假**，
                    # 于是这一块**一个数都没查过**，而注释写着「至少把墙钟与 SLO 钉住」。
                    # 改成无条件钉**墙钟**（正文印的 `75.6 minutes` 就是它）；
                    # SLO（100.0）正文不逐条印，钉它只会得到假 MISS —— 不加。
                    ck_near("%s 的墙钟" % _r, "%.1f" % _s["wall"], "sec_xtrace.tex",
                            "finishes in", window=30)

    # ---- slo_sensitivity.csv：§VI 阈值敏感性**那张表**的每一个格子 --------------
    # 2026-09-26：这张表此前**一个格子都没被守住**，四条老检查用的是 `ck()`
    # （全局字符串查）—— 正是「同一个数在别处出现也会通过」那一类。
    # 后果是实的：AIMD 那一行停在 r1 的读数（$-14.2$/$-11.2$/$-6.5$），而表 I
    # 换成 r3 之后真值是 $-16.3$/$-12.7$/$-8.5$；horizon=1 的**第三次运行**
    # 也没进表，正文却写着「one of its two runs」。
    # 判据：**整行三个格子一起查**（走 `has()` 的复合串通路，`&` 两侧空白弹性），
    # 用该行独有的标签做锚 —— 这张表里单查一个短数（`+1.0`、`-0.3`）必然撞车。
    _ss = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/slo_sensitivity.csv"))
           if r.get("run")}

    def _row3(run, prec=(1, 1, 1)):
        """按正文的精度拼出「$a$ & $b$ & $c$」三格 —— 精度必须与正文一致，
        否则 `has()` 会假 MISS（这条项目里栽过：`has()` 分不清 1.6 与 1.60）。"""
        x = _ss.get(run)
        if not x:
            return None
        return " & ".join("$%+.*f$" % (q, float(x[k])) for k, q in
                          zip(("slo5_pp", "slo10_pp", "slo20_pp"), prec))

    # ⚠ 2026-09-27 独立复核抓到：`scans the queue` 那一行**没有守卫** ——
    # 而它是全篇唯一越线的臂，阈值表里最能改结论的一行。补上。
    for _run, _kw, _prec in (("scan", "scans the queue &", (1, 1, 1)),
                             ("hz2_r2", "horizon}=2 &", (1, 1, 1)),
                             ("hz2_r3", "horizon}=2 (2nd run) &", (1, 1, 1)),
                             ("hz1", "horizon}=1 &", (1, 1, 1)),
                             ("hz1_r2", "(2nd run) &", (1, 1, 1)),
                             ("hz1_r3", "(3rd run) &", (1, 1, 2)),
                             ("hc", "sys{} base &", (1, 1, 1)),
                             ("bres_r2", "texttt{bres} &", (1, 1, 1)),
                             ("aimd2_paper_r3", "Concur-style AIMD &", (1, 1, 1))):
        _v = _row3(_run, _prec)
        if _v:
            ck_near("§VI 阈值表的 %s 行" % _run, _v, "sec_discussion.tex", _kw, window=80)

    # ---- §III 的 τ₁/τ₂ 三个派生区间（2026-09-25 发现集合没点名、值也对不上）----
    # 原来写「2.6--8.2 ms of a 27--37 ms step」，而 decomp.csv 里排除 hz1_r2 后
    # 差值是 2.6--8.8、τ₂ 是 20.6--39.2。**集合从来没写出来**，所以谁也没法复算。
    _acc = [r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))
            if r["run"] != "foyer_hz1_r2" and r["excess_pct"]]
    if _acc:
        _ex = [float(r["excess_pct"]) for r in _acc]
        _gp = [float(r["step_back_ms"]) - float(r["step_perreq_ms"]) for r in _acc]
        _t2 = [float(r["step_perreq_ms"]) for r in _acc]
        ck("§III excess_pct 下界", "%.1f" % min(_ex), "sec_model.tex")
        ck("§III excess_pct 上界", "%.1f" % max(_ex), "sec_model.tex")
        ck_near("§III τ₁−τ₂ 下界", "%.1f" % min(_gp), "sec_model.tex", "absolute terms")
        ck_near("§III τ₁−τ₂ 上界", "%.1f" % max(_gp), "sec_model.tex", "absolute terms")
        ck_near("§III τ₂ 下界", "%.1f" % min(_t2), "sec_model.tex", "absolute terms")
        ck_near("§III τ₂ 上界", "%.1f" % max(_t2), "sec_model.tex", "absolute terms")
        # ⚠⚠ 2026-09-27（r56：**不是**复核者报的，是我自己查出来的）：**这个集合的
        # 【条数】此前一条守卫都没有** —— 上面六条盯的全是区间端点，
        # 「the N left once the repeat excluded below is dropped」里的 N 没人管。
        # 后果实测：正文长期写着 **33**，而按**本函数自己**的口径（`_acc`）实际是 **38**。
        # 33 是数据集更小时的数（当时 33 接受 + 1 排除 = 34；现在 38 + 1 = 39）。
        # 唯一沾边的守卫是 `"图 3 图注的 excess 区间（33 条）"` —— 它**随已删图注退役了**
        # （退役名单里那条），名字里还带着「33 条」，**读起来像有覆盖，其实没有**。
        # ⇒ 判据：**区间有守卫，条数也必须有**；两者的源**共用 `_acc`**，不另写一份。
        ck_near("§III 接受集合的条数（`_acc` 同源）", "%d" % len(_acc),
                "sec_model.tex", "once the repeat excluded", window=60)
        # ⚠ 2026-09-26（引用审计抓到的）：**同一个区间在 §VII 的 Related Work 里还有一份**
        # （「§III bounds, without identifying, X\,ms of each Y\,ms step as prefill」），
        # 而它一直写着**旧口径**（2.6--8.2 / 27--37，压缩前那一版），没有任何守卫 ——
        # 改 §III 时漏掉了它，靠的是 `ck` 的全局匹配（那些短数字在别处能撞上）。
        # 这正是本项目「按【量】点名，不是按【位置】点名」那一条的又一例：一个量有几处，
        # 就守几处。这里**复用同一个生成器算出的 `_gp`/`_t2`**，两份不可能再漂。
        # ⚠ 2026-09-27（r57 codex 复核 1）：锚点原为 `"as prefill and non-decode overhead"`，
        # 而 C3 处置把那半句改成了 `the overhead that line attacks`（去掉「把差值断言成
        # 预填充成分」这个过强表述）⇒ **三条守卫当场全报 MISS**。
        # 这正是本项目那条教训的又一次：**守卫把正文措辞写死，于是它挡住了一个正确的修改**。
        # ⇒ 改锚到新措辞。**语义没变**（仍是「那句附近的三个区间值」），
        # 变的是被引的那半句不再声称差值的成分。
        ck_near("§VII 引擎侧那段的步成本区间（上限）",
                "%.1f" % max(_gp), "sec_discussion.tex",
                "the overhead that line", window=90)
        ck_near("§VII 引擎侧那段的步成本区间（下界）",
                "%.1f" % min(_gp), "sec_discussion.tex",
                "the overhead that line", window=90)
        ck_near("§VII 引擎侧那段的步（上限）",
                "%.1f" % max(_t2), "sec_discussion.tex",
                "the overhead that line", window=90)
        # ⚠⚠ 2026-09-27（r58 中立复核 2）：**这一句里 4 个数只守了 3 个。**
        # 上面三条盯的是 τ₁−τ₂ 的上下界与 τ₂ 的**上界**；而句子里还有个
        # **τ₂ 的下界 20.6**（`20.6--39.2`ms 的左端）—— 它**一条守卫都没有**。
        # 复核者构造：`20.6 → 21.6`，**一条值 MISS 都不响**（只有 mtime 守卫响）。
        # 当前值是对的，所以这是**缺口不是错**；但同一个量的另一处（§Model 的
        # `absolute terms` 锚）是守着的 ⇒ 典型的「一个量两处、只守一处」。
        # ⇒ 补上。**同源 `_t2`，不另写一份。**
        ck_near("§VII 引擎侧那段的步（下界）",
                "%.1f" % min(_t2), "sec_discussion.tex",
                "the overhead that line", window=90)
        # 2026-09-26 加：**图 3 的图注**原来写「8--40%」，那是把两个集合的范围
        # 混成了一句（33 条的上界是 39.7，全 34 条的上界是 66.3）。
        # 现在图注照 §III 的口径写成「8--40% over the 33 runs we accept and 66%
        # on the one we exclude」，两条都钉住。
        _excl = [float(r["excess_pct"]) for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))
                 if r["run"] == "foyer_hz1_r2" and r["excess_pct"]]
        ck_near("图 3 图注的 excess 区间（33 条）",
                "%.0f--%.0f" % (min(_ex), max(_ex)),
                "sec_model.tex", "we accept")
        if _excl:
            # ⚠ 锚不能用 "we exclude"：§III 正文里「the one run we exclude …
            # reads 66.3\%」也在这个关键词的窗口内，于是**把图注的 66 改成 67
            # 也照样通过**（反向测试实测）。换成图注独有的「runs we accept and」，
            # 且窗口收窄到 40。
            ck_near("图 3 图注里被排除那条的 excess", "%.0f" % min(_excl),
                    "sec_model.tex", "and by", window=40)

    # ---- §III 基线步成本那句：值必须出现在「baseline」附近 ----
    # 2026-09-25：这句原来写 39.3，而统一 τ₂ 定义后 decomp.csv 里 default 的
    # step_perreq_ms 是 39.2。`ck` 因为 39.2 在别处出现过而放过了它。
    _dc = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    if "default" in _dc and _dc["default"]["step_perreq_ms"]:
        ck_near("§III 基线步成本（τ₂）", _dc["default"]["step_perreq_ms"],
                "sec_model.tex", "baseline")

    # ---- §VII 重写后新引的机制读数（闸门归因 + 占用投影）----
    # 2026-09-25 中立子 agent 第 9 轮指出：正文原来用「队列深 + 引擎只跑一个」
    # 论证「队列是节流造出来的」，而那个并列在 200 档基线上【一模一样地成立】
    # （foyer_hc 的 running 均值 1.137，push_25 是 1.136）—— 区分不了任何东西。
    # 现在改成引闸门归因与占用投影。这几个数必须能从表里追到。
    _ga = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/gate_attrib.csv"))}
    _pj = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/projection.csv"))}
    # §V「准入率基本没变」那句：2.35% 与 2.44% 是 gate_attrib 的 total_admits /
    # samples，**不是** controller.jsonl 里 n_admitted 的逐周期求和（那个是 209，
    # 2026-09-25 我自己用错列、险些把它当错误报出来）。
    for _k, _lab in (("pois200_foyer_hc", "基线"), ("pois200_foyer_sf0_r2", "sf=0")):
        if _k in _ga:
            ck("§V %s 的准入周期占比" % _lab,
               "%.2f" % (100.0 * float(_ga[_k]["total_admits"]) / float(_ga[_k]["samples"])),
               "sec_results.tex")
    _k25 = "pois200_foyer_push_25"
    if _k25 in _ga:
        ck("§VII 25 档被挡周期数", _ga[_k25]["blocked_cycles"], "sec_discussion.tex")
        ck("§VII 25 档安全阀占比", _ga[_k25]["valve_pct"], "sec_discussion.tex")
        ck("§VII 25 档回合闸门占比", _ga[_k25]["round_gate_pct"], "sec_discussion.tex")
    if _k25 in _pj:
        ck("§VII 25 档投影占预算%", _pj[_k25]["proj_pct_of_budget"], "sec_discussion.tex")
        ck("§VII 25 档引擎上报占预算%", _pj[_k25]["occ_pct_of_budget"], "sec_discussion.tex")
    # 「两档的在跑数几乎一样」——这是那段论证的前提，钉住它
    _ar = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/arm_running.csv"))}
    if "foyer_hc" in _ar:
        ck("§VII 200 档基线在跑均值", "%.3f" % float(_ar["foyer_hc"]["running_all"]),
           "sec_discussion.tex")
    ck("§VII 25 档在跑均值", "%.3f" % float(_import_running_all(_k25)), "sec_discussion.tex")

    # ---- τ₂ 的三份实现必须逐 run 相同（共用定义的守护检查）----
    # `gen_concurrency.tau2()` 在实验机上跑、那边没有 scripts/lab/，所以它保留
    # 自己那份实现；`gen_decomp.perreq_one()` 是本地这一份，`gen_tau2_windows.py`
    # 已经改成 import 它。**注释说「逐字一致」不算数，这里逐 run 算一遍。**
    # 2026-09-25 这两份真的不一致过：gen_concurrency 有 `status == "SUCCESS"` 过滤，
    # 另两份没有（实测只有 `default` 一条 run 受影响）。
    _gd = importlib.util
    _sp = _gd.spec_from_file_location("_gd2", os.path.join(ROOT, "scripts/lab/gen_decomp.py"))
    _GD = _gd.module_from_spec(_sp); _sp.loader.exec_module(_GD)
    _sp2 = _gd.spec_from_file_location("_gc", os.path.join(ROOT, "scripts/lab/gen_concurrency.py"))
    _GC = _gd.module_from_spec(_sp2); _sp2.loader.exec_module(_GC)
    _root = os.path.join(ROOT, "results/night")
    _n = 0
    for _r in load(os.path.join(ROOT, "paper/data/decomp.csv")):
        _sp3 = os.path.join(_root, "pois200_" + _r["run"], "steps.jsonl")
        if not os.path.exists(_sp3):
            continue
        _steps = [json.loads(l) for l in open(_sp3) if l.strip()]
        _a = _GD.perreq_ms(_steps)
        _b = _GC.tau2(_root, "pois200_" + _r["run"])
        if _a is not None and _b is not None and abs(_a - _b) > 1e-9:
            fails.append(("τ₂ 两份实现不一致：%s" % _r["run"],
                          "gen_decomp %.4f vs gen_concurrency %.4f" % (_a, _b),
                          "scripts/lab/gen_decomp.py 与 gen_concurrency.py"))
        _n += 1
    if VERBOSE:
        print("  OK   τ₂ 两份实现在 %d 条 run 上逐位一致" % _n)

    # ---- elasticity.csv 表头：§IV 那句「覆盖整个控制器运行区间（1.35 到 1.69）」----
    # 这个区间是【九条 Foyer 臂】的，不是 controller 族全体的（后者含重复臂 hz1_r2，
    # R̄ 到 2.10）。表头两个集合都写出来了，这里查九条那个 —— 集合选错正是本项目
    # 反复栽的坑，所以把它钉住。
    _el = open(os.path.join(ROOT, "paper/data/elasticity.csv"), encoding="utf-8").read()
    _mn = re.search(r"^# nine_foyer_arms_Rbar_min,([\d.]+)", _el, re.M)
    _mx = re.search(r"^# nine_foyer_arms_Rbar_max,([\d.]+)", _el, re.M)
    if _mn and _mx:
        ck("§IV 控制器运行区间下界", "%.2f" % float(_mn.group(1)), "sec_criterion.tex")
        ck("§IV 控制器运行区间上界", "%.2f" % float(_mx.group(1)), "sec_criterion.tex")

    # ---- elasticity_x.csv：§VI 的 realhr 控制器臂（含它那个不复现的越线）----
    for r in load(os.path.join(ROOT, "paper/data/elasticity_x.csv")):
        if r.get("kind") == "arm" and r["name"].startswith("realhr_foyer"):
            ck("%s 的 5s 距离" % r["name"], r["delta5_pp"], "sec_xtrace.tex")
            ck("%s 的 10s 距离" % r["name"], r["delta10_pp"], "sec_xtrace.tex")

    # ---- elasticity_hc.csv（§IV 的 HiCache 弹性曲线）与 §III 的 excess 区间 ----
    # 2026-09-25 覆盖普查发现：elasticity_hc.csv 一次都没被检查器提到，
    # 而 §IV 引它的 ε = +0.19 / +0.46，还引了一次「换锚点后这两个数怎么动」。
    _eh = load(os.path.join(ROOT, "paper/data/elasticity_hc.csv"))
    for _r in _eh:
        if _r["config"] == "hicache":
            # ⚠ **不许取 abs**：ε 的**符号是语义** —— 负=加并发还能买到吞吐，
            # 正=自毁。原来写 `abs(...)` + `"%.2f"`，于是把正文的 `+2.87`
            # 改成 `-2.87` 也照样通过（codex 第 25 轮实测）。
            # 并改用 ck_near：`ck` 是全局搜，`0.19` 这种短串在别处也会撞上。
            ck_near("§IV HiCache ε %s→%s" % (_r["from"], _r["to"]),
                    # 正文写的是 `$\epsilon = +0.19$` —— 没有「HiCache」这个词在附近，
                    # 用它当 keyword 会得到假 MISS。`epsilon = ` 才是该处独有的锚。
                    "%+.2f" % float(_r["epsilon"]), "sec_criterion.tex", "epsilon = ")
    # §III：五个 device-only cap 的 τ₁/τ₂ − 1 区间
    _dd4 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    _dv = [float(_dd4[k]["excess_pct"]) for k in ("cap1", "cap2", "cap3_fixed", "cap4", "cap5")
           if k in _dd4 and _dd4[k]["excess_pct"]]
    if _dv:
        # ⚠ 锚原来是 "runs" —— 那是 `sec_model.tex` 里最常见的词之一，
        # 而**第 23 行另有一个无关的 17.7%**（空转段的占比），于是这条检查
        # 可以在完全错误的位置上通过（本项目「先想想它是不是在别处撞上的」）。
        # 换成该处独有的短语。
        ck_near("§III device-only 的 excess 下界", "%.1f" % min(_dv),
                "sec_model.tex", "exceeds $\\tau_2$ by")
        ck_near("§III device-only 的 excess 上界", "%.1f" % max(_dv),
                "sec_model.tex", "exceeds $\\tau_2$ by")
        # 2026-09-26 加：**图 7 的图注**也在说这五条，而它原来写的是「8--40%」
        # （8 是从 33 条那个集合借来的）—— 正文写对了、图注写错了，
        # 因为**守卫只盯正文**。图注与正文必须一起查。
        ck_near("图 7 图注的 excess 区间", "%.1f--%.1f" % (min(_dv), max(_dv)),
                "sec_model.tex", "exceeds $\\tau_2$ by")

    # ---- loadtier.csv（图 5 与 §Load Dependence）----
    # 2026-09-25：这张表是 paper/data 里【唯一一张没有生成器】的，而图 5 和正文都引它。
    # 已建 gen_loadtier.py（200 档取 table1.csv、25 档取 thr25_base/thr25_push 现算），
    # 逐位复现了原来手维护的四行。这里把那两个反向效应钉住。
    _lt = {r["tier"]: r for r in load(os.path.join(ROOT, "paper/data/loadtier.csv"))}
    _lt_on = {(r["tier"], r["throttle"]): float(r["wall_min"])
              for r in load(os.path.join(ROOT, "paper/data/loadtier.csv"))}
    if ("25", "on") in _lt_on and ("25", "off") in _lt_on:
        ck("§load 25 档的加速幅度",
           "%.0f" % abs(100 * (_lt_on[("25", "off")] - _lt_on[("25", "on")]) / _lt_on[("25", "on")]),
           "sec_discussion.tex")
    if ("200", "on") in _lt_on and ("200", "off") in _lt_on:
        ck("§load 200 档的减速幅度",
           "%.0f" % abs(100 * (_lt_on[("200", "off")] - _lt_on[("200", "on")]) / _lt_on[("200", "on")]),
           "sec_discussion.tex")

    # ---- nocontrol.csv 与 arrival_slo.csv：此前【零覆盖】----
    # 2026-09-25 全量重生成时发现 arrival_slo.csv 的生成器 run 列表被改名了、
    # 表却没重生成（还留着旧的 foyer_hz0/hz2）—— 两张表此前一条检查都没有。
    _nc = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/nocontrol.csv"))}
    if "default" in _nc:
        ck_near("§V 无控制臂的首 token 中位（秒）",
                str(int(float(_nc["default"]["ttft_p50_s"]))), "sec_results.tex", "median")
        ck_near("§V 无控制臂的 SLO", _nc["default"]["slo_pct"], "sec_results.tex", "envelope")
    _as = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/arrival_slo.csv"))}
    # ⚠ 名单**漏了 `foyer_sf0_r2`**（独立复核子 agent 第 21 轮实测）：算出 11 条 /
    # 8 条带内，而正文写的是 **twelve / nine** —— **正文对、守卫错**。
    # `arrival_slo.csv` 里恰好 12 条控制器臂、9 条在 ±2.5pp 内（带外三条正是正文点名的
    # `foyfix_hc` +8.22 / `aimd2` +3.22 / `foyer_breshz1_r2` −3.16）。
    # ⚠ 而且这两条原来用 **`ck()`（全局字符串查）**：`11` 在同文件里有 6 处、
    # `8` 有 2 处 —— **永远绿**。同一轮刚把 13/17 两条改成 `ck_near`，这两条漏了。
    # ⚠⚠ 2026-09-27：与上面同一处病 —— 名单写死 13 个名字，两条新 run 不在里面，
    # 于是「控制器臂条数」与「移动 ≤2.5pp 的条数」各少算了。改成现算。
    _CTRL = sorted(k for k in _as if k.startswith(("foyer", "foyfix", "aimd")))
    _mv = [(r["run"], float(r["move_pp"])) for k, r in _as.items()
           if k in _CTRL and r["move_pp"] not in ("", "None")]
    if _mv:
        # ⚠⚠ 2026-09-26：**关键词里不许带数词** —— 原来锚是 `"of the twelve controller"`，
        # 而它**自带 "twelve"**，于是「查 twelve」这条检查**永远通过**（自证）。
        # 本项目在别处早就记过这条规矩（「数词不能放进关键词里」），这里漏了。
        # 改成不含任何数字的短语，两条计数共用同一个锚。
        _wanch = "controller arms move by no more than"
        _w2 = lambda k: num_words(k) + [k]
        ck_near("§VI ready 时钟：控制器臂条数", _w2(len(_mv)), "sec_discussion.tex",
                _wanch, window=60)
        ck_near("§VI ready 时钟：移动 ≤2.5pp 的条数",
                _w2(sum(1 for _, v in _mv if abs(v) <= 2.5)), "sec_discussion.tex",
                _wanch, window=60)
        for _k, _v in _mv:
            if abs(_v) > 2.5:
                ck_near("§VI %s 的 ready 位移" % _k, "%.1f" % abs(_v), "sec_discussion.tex", "move more")

    # ---- 表 I 脚注的「本 trace 跑完但不在表里」的条数 ----
    # 2026-09-25 中立子 agent 第 10 轮说这个「十」拼不出来、且被重跑替代的三条
    # 不在理由枚举里 —— 复核确认：实为【十一】条，且确实漏了「被替代」这一类。
    # ⚠ 这个数**会随新 run 落地而变**（本地镜像是部分快照），所以它是一条
    # 【会漂的检查】：漂了就照实改正文，不要反过来去改判据。
    # ⚠ 2026-09-26（中立复核第 43 轮）：判据要用**论文那张表**的行集合，
    # 不是 `table1.csv` 的行集合 —— 后者多两条论文**不印**的 run
    # （`pairA_cap2hc` 与 `aimd2_paper`，跑完/换下但从未进表），
    # 于是这个数一直是 19 而正文的口径下真值是 **21**。
    # 这正是「守卫读数据文件、正文读论文表」那一类不一致：**两份口径不同的地方
    # 正好是错的那一处**。现在两边都按「论文表打印的行」算。
    #
    # ⚠⚠ 2026-09-27（中立复核 r50 B 组 B1/B2）：表 I 缩到 27 行之后，**「listed」
    # 的含义在稿子里没写死**，于是正文与守卫各自隐含一个口径 ——
    #   · 守卫（下面 `_listed`，= paper/data/table1.csv 减去两条从不印的 run）
    #     把移进 supplement 的那 8 条静态 cap **算作已列**，得到 21；
    #   · 只读 11 页的读者按**表 I 真印的 27 行**复算，会得到 29。
    # 两者都能自圆其说，但**不能同时对**。处置（本会话）：选「(正文表 ∪ supplement 的
    # 完整 run 表) 才算 listed」这一支 —— 因为表 I 的 caption 明写「The supplement
    # carries our full run table, including the eight static caps this one omits」，
    # 把那 8 条说成「不在任何表里」会与 caption 冲突；同时把**口径写进正文**
    # （「are in no table of ours」），两边从此指着同一件事。
    # ⚠ 8 条的名单**不在这里重写一份**：用与上面 `TABLE1_SRC` 同一个来源
    # （`gen_table.PAPER_OMIT`），这正是 B2 要的「统一到同一个来源」。
    _NOT_PRINTED = {"pairA_cap2hc", "aimd2_paper"}
    _listed_body = {r["run"] for r in load(os.path.join(ROOT, "paper/data/table1.csv"))} \
        - _NOT_PRINTED - set(_import_gen_table().PAPER_OMIT)
    _listed = _listed_body | set(_import_gen_table().PAPER_OMIT)
    # 自检：正文表（27 行）与 supplement 完整表（8 行）必须**刚好铺满** `_listed`
    checks += 1
    if len(_listed_body) + len(_import_gen_table().PAPER_OMIT) != len(_listed):
        fails.append(("「表 I ∪ supplement 完整表」的行集合不是不交并",
                      "正文 %d + supplement %d ≠ %d" % (
                          len(_listed_body), len(_import_gen_table().PAPER_OMIT), len(_listed)),
                      "paper/data/table1.csv"))

    # ---- §V 的【带旗计数】那段（2026-09-26 补：它此前**一条守卫都没有**）----
    # 原文「One row of this table now carries the flag, cap1, and **five** more have
    # carried it in earlier versions … Four of those five were damaged … **The remaining
    # one, cap1**, …; the fifth is the superseded first attempt at the AIMD arm」——
    # **数下来是 6**（cap1 不在那五条里）。已改成把 cap1 从「五条」里摘出来。
    # 判据：印出来的行里恰有一条带旗（且是 cap1）；历史上带过旗的六条确实都在
    # `concurrency.csv` 里被标；两条条数用不含数字的锚钉住。
    _cg = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/concurrency.csv"))}
    _flag = {k for k, r in _cg.items()
             if str(r.get("verdict", "")).strip().upper().startswith("CONTEST")}
    _t1c = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/table1.csv"))}
    _printed_flag = sorted(k for k in _listed
                           if str(_t1c.get(k, {}).get("contested", "")).strip().upper() == "CONTESTED")
    checks += 1
    # ⚠ `_listed` 用的是**短名**（`cap1`），不是目录名（`pois200_cap1`）—— 第一版拿长名比，
    # 报了一条**假 MISS**（而正文是对的）。本项目记过：报 MISS 先怀疑检查。
    if _printed_flag != ["cap1"]:
        fails.append(("§V 说「印出来的表只有一条带旗（cap1）」与 table1.csv 不符",
                      "实测带旗的印出行：%s" % _printed_flag, "paper/data/table1.csv"))
    _EVER = {"pois200_cap1", "pois200_foyer_hz2", "pois200_foyer_hz0",
             "pois200_foyer_bres", "pois200_foyer_breshz1", "pois200_aimd2_paper"}
    checks += 1
    # ⚠ `_CTRL` 里是**短名**（`foyer_hc`），而 `_flag` 来自 concurrency.csv 的
    # **目录名**（`pois200_foyer_hc`）—— 第一版直接取交集，结果恒为空集，
    # 报出一条「多：[]」的假 MISS。两边统一成目录名。
    # ⚠ `_CTRL` 里是**干净重跑**（`foyer_bres_r2` …），而 §V 那句话说「历史上带过旗的」
    # 是**被替代的原 run**（`foyer_bres` / `foyer_hz0` / `foyer_hz2` / `foyer_breshz1`）——
    # 名字不同，取交集会漏掉四条（第一版就是，报出「多：[]」的假 MISS）。
    # 把「可能出现在表 I 里的臂」定义为：`_CTRL` + 它们被替代的前身 + cap1 + AIMD 首次尝试。
    _SUPERSEDED_PRE = {"pois200_foyer_bres", "pois200_foyer_hz0",
                       "pois200_foyer_hz2", "pois200_foyer_breshz1"}
    _TABLE_ARMS = ({("pois200_" + _c) for _c in _CTRL} | _SUPERSEDED_PRE
                   | {"pois200_cap1", "pois200_aimd2_paper"})
    _flag_arms = _flag & _TABLE_ARMS
    if not _EVER <= _flag:
        fails.append(("§V 说的「历史上带过旗的那几条」在 concurrency.csv 里没被标",
                      "缺：%s" % sorted(_EVER - _flag), "paper/data/concurrency.csv"))
    checks += 1
    if _flag_arms != _EVER:
        fails.append(("§V「five more have carried it」之外**又有臂被标**（那句话会过期）",
                      "多：%s" % sorted(_flag_arms - _EVER),
                      "paper/data/concurrency.csv"))
    ck_near("§V 历史上带旗的条数", num_words(5) + [5], "sec_results.tex",
            "have carried it in earlier versions", window=40)
    ck_near("§V 那五条里受损的条数", num_words(4) + [4], "sec_results.tex",
            "of those five were damaged", window=40)
    _done = set()
    for _d in glob.glob(os.path.join(ROOT, "results/night", "*")):
        if not os.path.isdir(_d) or not os.path.exists(os.path.join(_d, "summary.json")):
            continue
        try:
            _j = json.load(open(os.path.join(_d, "metadata.json")))
        except Exception:
            continue
        # ⚠ 用**顶层 `trace`**，不是 `build.TURNSTILE_TRACE` —— 后者在两条早期 run
        # （`pois200_foyer` / `pois200_cap3_r2`，9-15/9-17）里是空的，
        # 于是它们被**静默漏掉**（独立复核子 agent 第 21 轮实测）。
        _tr = (_j.get("trace") or "") or ((_j.get("build") or {}).get("TURNSTILE_TRACE") or "")
        if "replay_pois200_l04" in str(_tr):
            _done.add(os.path.basename(_d).replace("pois200_", ""))
    # ⚠ 原来用 `ck`（全局字符串）—— 独立复核子 agent 第 20 轮实测：它算出的 29
    # 被同文件里的 `29.3\%` / `29.2` / `29.5` 接住，**正文写 twelve 也照样通过**。
    # 而且还不是同一个集合：正文那句话是**本机 + 本 trace + 跑完 + 不在表 I**，
    # 不含 A100 的 10 条，也不含两句之外明说「不报告」的四车道失败 2 条。
    # 现在按正文那个集合现算，并锚在「further runs on this trace completed」上。
    _local = {x for x in (_done - _listed)
              if not x.startswith("a100_") and not x.startswith("_failed")}
    # ⚠ 「completed」这个词 2026-09-26 去掉了：那 17 条里有 **2 条没跑完**
    # （`cap3_hp` 807 步 / `cap4_hp` 549 步，各带 50 / 116 个失败步），
    # 所以现在写「are not listed」并**单独点名那两条**。锚也跟着换。
    # ⚠ 2026-09-27（r50 B1）：措辞再换一次 —— 「not listed」**没说是哪张表**，
    # 读者会按表 I 的 27 行复算得 29。现在正文写「are in no table of ours」
    # （口径 = 本机本 trace 跑完、且**表 I 与 supplement 完整表都没有它**），
    # 与 `_listed` 的定义逐字对应。
    ck_near("表 I 脚注：本机本 trace 但不在任何表里的条数",
            num_words(len(_local)) + [len(_local)], "sec_results.tex",
            "further runs on this trace are in no table of ours", window=40)
    # 那两条「停在多少步」也要能被守着。⚠ 正文写的是「at 807 and 549 of the
    # 999 steps」——**两个数挤在一句里**，所以查**整串**（只查 807 会假 MISS，
    # 因为 807 后面跟的是 and 不是 of）。
    _stops = []
    for _k in ("cap3_hp", "cap4_hp"):
        _sp = os.path.join(ROOT, "results", "night", "pois200_" + _k, "steps.jsonl")
        _stops.append(sum(1 for _ in open(_sp)) if os.path.exists(_sp) else None)
    if all(_stops):
        ck_near("表 I 脚注：两条半池臂停在多少步",
                "at %d and %d of the" % tuple(_stops), "sec_results.tex",
                "stopped early", window=60)

    # ---- §III 的 13 条拟合集（重测后上界换过）----
    # 2026-09-25 中立子 agent 第 10 轮：τ₂ 的 **33.1 已无源** —— 那是被撤下的
    # `foyer_hz0` 的值。集合是「五个 device-only cap + 三个 host-tier cap +
    # 我们单独报告的五个控制器臂」，实算 τ₂ 上界是 cap5 的 31.2。
    _dd2 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    _FIT = ["cap1", "cap2", "cap3_fixed", "cap4", "cap5",
            "pairB_cap2hc", "cap3_hc", "cap4_hc",
            "foyer_sf0_r2", "foyer_hz1", "foyer_hc", "foyer_hz2_r2", "foyer_hz0_r2"]
    _f = [_dd2[k] for k in _FIT if k in _dd2 and _dd2[k]["step_back_ms"]]
    if len(_f) == 13:
        ck("§III 拟合集的 τ₁ 下界", "%.1f" % min(float(r["step_back_ms"]) for r in _f),
           "sec_model.tex")
        ck("§III 拟合集的 τ₁ 上界", "%.1f" % max(float(r["step_back_ms"]) for r in _f),
           "sec_model.tex")
        ck_near("§III 拟合集的 τ₂ 下界", "%.1f" % min(float(r["step_perreq_ms"]) for r in _f),
                "sec_model.tex", "ranges from")
        ck_near("§III 拟合集的 τ₂ 上界", "%.1f" % max(float(r["step_perreq_ms"]) for r in _f),
                "sec_model.tex", "ranges from")

    # ---- 「同族干净 run 的 τ₂ 区间」（表 I 脚注与 §repro 两处）----
    # 集合此前从未写明条数；这里把它定成机械可复算的：Foyer 家族 + host-tier +
    # 未被判 CONTESTED + 有 τ₂。重测落地后是 12 条 / 23.7--27.5。
    _cc = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/concurrency.csv"))}
    _famt = []
    for _r in load(os.path.join(ROOT, "paper/data/reuse.csv")):
        _k = _r["run"]
        if _r["family"] != "hicache" or _r["contested"] == "CONTESTED":
            continue
        if not (_k.startswith("foyer_") or _k.startswith("pairA_foyerhc")
                or _k.startswith("pairB_foyerhc") or _k == "foyfix_hc"):
            continue
        _c = _cc.get("pois200_" + _k)
        if not _c:
            continue
        try:
            _famt.append(float(_c["tau2_ms"]))
        except (TypeError, ValueError):
            pass
    # ⚠ 2026-09-26 独立复核子 agent 第 20 轮抓到：原来三条都用 **`ck`（全局字符串）**，
    # 于是正文改不改都"过" —— `ck(..., 14, ...)` 被同文件的 "Fourteen of our runs"
    # 接住了（`has()` 会把数字与英文词互相匹配）。**打印出来的值贴着正文的 twelve，
    # 却没有任何东西比对。** 已改成 `ck_near`，锚在「clean runs of the same
    # controller family」上，并按正文那句话自带的口径（**跑满 999 步**）筛集合。
    _famt_full = []
    for _r in load(os.path.join(ROOT, "paper/data/reuse.csv")):
        _k = _r["run"]
        if _r["family"] != "hicache" or _r["contested"] == "CONTESTED":
            continue
        if not (_k.startswith("foyer_") or _k.startswith("pairA_foyerhc")
                or _k.startswith("pairB_foyerhc") or _k == "foyfix_hc"):
            continue
        _c = _cc.get("pois200_" + _k)
        _sp = os.path.join(ROOT, "results", "night", "pois200_" + _k, "steps.jsonl")
        if not _c or not os.path.exists(_sp):
            continue
        if sum(1 for _ in open(_sp)) != 999:      # 正文写的是「completed this trace」
            continue
        try:
            _famt_full.append(float(_c["tau2_ms"]))
        except (TypeError, ValueError):
            pass
    if _famt_full:
        _anch = "clean runs of the same controller family"
        ck_near("§repro 同族干净 run 的条数", num_words(len(_famt_full)) + [len(_famt_full)],
                "sec_discussion.tex", _anch, window=40)
        ck_near("§repro 同族干净 run 的条数（表注那处）",
                num_words(len(_famt_full)) + [len(_famt_full)],
                "sec_results.tex", _anch, window=40)
        # ⚠ **两个端点都要在两处查**：原来下界只查 §VI、上界只查表注 ——
        # 独立复核子 agent 第 21 轮实测：把**表注**里的下界改成 22.7、把 **§VI** 里的
        # 上界改成 27.6，**都静默**。同一个区间印在两处，各守一半等于各漏一半。
        for _fn, _w in (("sec_discussion.tex", 60), ("sec_results.tex", 120)):
            ck_near("§repro 同族干净 τ₂ 下界（%s）" % _fn, "%.1f" % min(_famt_full),
                    _fn, _anch, window=_w)
            ck_near("§repro 同族干净 τ₂ 上界（%s）" % _fn, "%.1f" % max(_famt_full),
                    _fn, _anch, window=_w)

    # ---- §III 的两个例证（重测后都换过/改过数）----
    # 2026-09-25 codex 第 23 轮：这两处原来用旧 hz0 的数，而重测后
    # ①「两个相似在跑数」那例变成 1.58 / 30.2 ms；
    # ②**非单调反例失效了** —— 旧 hz0（1.66）比 cap4（1.65）并发高且空转多，
    #   新 hz0_r2 是 1.58 / 16.9%，成了「并发更低、空转更多」，什么也证明不了。
    #   换成 no gate（1.68 / 20.7%）对 cap4（1.65 / 10.4%）。
    _a3 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/arm_running.csv"))}
    _d3 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    for _k in ("foyer_nogate", "cap4", "foyer_hz0_r2", "cap4_hc"):
        if _k in _a3 and _k in _d3:
            ck_near("§III %s 的空转%%" % _k, "%.1f" % float(_d3[_k]["idle_pct"]),
                    "sec_model.tex", "idle")
            # ⚠ 关键词不要带反斜杠 —— 在 heredoc 里 `\t` 会变成制表符，
            # 匹配不上还看不出来（2026-09-25 刚踩）。用纯文本词。
            ck_near("§III %s 的 R̄busy（两位）" % _k, "%.2f" % float(_a3[_k]["running_busy"]),
                    "sec_model.tex",
                    "idles" if _k in ("foyer_nogate", "cap4") else "requests at")

    # ---- horizon 扫描（图 6）----
    # 2026-09-25 codex 第 23 轮：这张表原来【没有生成器】、是手维护的，
    # hz0/hz2 被重跑替代后它和图 6 都还留着旧读数，图注里「两轮比三轮慢 15 分钟」
    # 在新数据下是【反的】。现已由 gen_horizon.py 从 table1.csv 生成，这里逐项钉住。
    _hz = load(os.path.join(ROOT, "paper/data/horizon.csv"))
    if _hz:
        _base = [r for r in _hz if r["horizon"] == "3"]
        _h0 = [r for r in _hz if r["horizon"] == "0"]
        _h1 = [r for r in _hz if r["horizon"] == "1"]
        _h2 = [r for r in _hz if r["horizon"] == "2"]
        if _base and _h0:
            ck("图6 去掉预留损失的 SLO（10.0）",
               "%.1f" % (float(_base[0]["slo_pct"]) - float(_h0[0]["slo_pct"])), "sec_results.tex")
        if _base and _h2:
            ck("图6 两轮对三轮的墙钟差（快 20 分）",
               "%.0f" % abs(float(_h2[0]["wall_min"]) - float(_base[0]["wall_min"])),
               "sec_results.tex")
        if _h1:
            ck("图6 一轮的墙钟", _h1[0]["wall_min"], "sec_results.tex")
        # ⚠ 不要为图 6 的四个墙钟各加一条 ck_near —— 图注本来就不逐条印它们，
        # 硬钉只会得到假 MISS（2026-09-25 加这块时先写错了，四条全 MISS）。
        # 图与 horizon.csv 的一致性由「图不比 paper/data 旧」那条覆盖。

    # ---- §III「未解释」段的回归（τ₁ ~ 重算量，18 条干净 host-tier）----
    # 2026-09-25 加：此前正文里这个 r 与最大残差**没有任何检查覆盖**，
    # 我在改条数时把残差猜成了 1.5（真值 1.6）—— 猜出来的数正是要靠检查挡住的。
    import math as _mm2
    # ⚠ `load()` 返回的是【列表】不是字典 —— 直接写 `r["run"] in _dx` 恒为 False，
    # 整块会静默不执行（2026-09-25 加这块时踩到，靠 DEBUG 打印才看见）。
    _rx = load(os.path.join(ROOT, "paper/data/reuse.csv"))
    _dx = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    _ex = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/eviction.csv"))}
    _clean = [r["run"] for r in _rx
              if r["family"] == "hicache" and r["contested"] != "CONTESTED"
              and r["run"] in _dx and _dx[r["run"]]["step_back_ms"]]
    if len(_clean) >= 5:
        _xs = [float(_ex[k]["uncached_tok"]) / 1e6 for k in _clean]
        _ys = [float(_dx[k]["step_back_ms"]) for k in _clean]
        _mx, _my = sum(_xs) / len(_xs), sum(_ys) / len(_ys)
        _b = sum((x - _mx) * (y - _my) for x, y in zip(_xs, _ys)) / sum((x - _mx) ** 2 for x in _xs)
        _a = _my - _b * _mx
        _r = (sum((x - _mx) * (y - _my) for x, y in zip(_xs, _ys))
              / _mm2.sqrt(sum((x - _mx) ** 2 for x in _xs) * sum((y - _my) ** 2 for y in _ys)))
        _res = max(abs(y - (_a + _b * x)) for x, y in zip(_xs, _ys))
        # 三条**全部**用 ck_near。原来前两条是 `ck`，2026-09-25 独立审查实测它们
        # 是假通过：条数 20 撞上正文的 "20.9\,s"；r 的 "+0.90" 经 `has()` 退化成
        # 找 "0.9"，而正文的 "+0.91" **含有** "0.9" ⇒ 两条等于不存在。
        # 于是这段里 19→20、36.2→34.8、+0.91→+0.90、1.6→1.65 四处过时值全部漏检。
        ck_near("§III 回归的条数", num_words(len(_clean)), "sec_model.tex", "straight line", window=400)
        ck_near("§III 回归的 r", "%+.2f" % _r, "sec_model.tex", "straight line", window=400)
        # ⚠ 两个精度都查。正文写 `1.65`（2 位），而 `%.1f` 给的 `"1.6"` 只是
        # **它的子串**才侥幸命中 —— 那是子串匹配不是精确匹配，等于弱检查。
        # （2026-09-25 codex 第 25 轮复算残差 = 1.6475131… 时暴露。）
        # ⚠ **只查正文用的那个精度**（2 位）。试过写成 `["%.2f", "%.1f"]`，
        # 反而更弱：`has("1.6")` 会试 1~4 位小数，其中 `"%.2f" % 1.6` = `"1.60"`,
        # 于是它**匹配了正文的 1.60** —— `has()` 的语义是「同一个数的不同写法」，
        # 它**无法**区分 1.6 与 1.60。而这里要区分的恰恰是两个不同的数。
        ck_near("§III 回归的最大残差", "%.2f" % _res,
                "sec_model.tex", "straight line")
        # host-tier 的 τ₁ 上界 —— 36.2 是**被污染的旧 breshz1**，重跑后真值是 34.8。
        # 正文这个数此前一条检查都没有（按名字清点查不出它，因为旁边没有 run 名）。
        ck_near("§III host-tier 的 τ₁ 上界",
                "%.1f" % max(float(_dx[k]["step_back_ms"]) for k in _clean),
                "sec_model.tex", "spans")

    # ---- §II 的「最佳臂对最近静态锚点」的数 ----
    # 2026-09-25：最佳臂在 hz2_r2 落地后【换人了】—— 原来是 sf0_r2（−0.55），
    # 现在是 hz2_r2（−0.30）。§II 那句跟着换，检查也跟着换；
    # sf0_r2 的那两个差值正文不再引，降为次要档（它还留在表 I 与 §V 里）。
    _t1 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/table1.csv"))}
    if {"foyer_sf0_r2", "foyer_hz2_r2", "cap3_hc_r2", "cap3_hc", "foyer_hz1"} <= set(_t1):
        for _best in ("foyer_hz2_r2", "foyer_sf0_r2"):
            _tier = "P" if _best == "foyer_hz2_r2" else "S"
            for _anch in ("cap3_hc_r2", "cap3_hc"):
                ck("§II %s 对 %s" % (_best, _anch),
                   "%.1f" % (float(_t1[_best]["slo_pct"]) - float(_t1[_anch]["slo_pct"])),
                   "sec_background.tex", tier=_tier)
        # ⚠ 2026-09-26 换了判据：那句话原来说「hz1 比 cap3_hc 高 3.7pp」，
        # 现在说的是 **hz1 三次重复各自的 Δ**（第三次落地后它成了重复最多的那条臂）。
        # 判据跟着换，不是删掉 —— 换掉的句子仍然要有一个数被守。
        for _k, _lab in (("foyer_hz1", "§II hz1 第一次的 Δ"),
                         ("foyer_hz1_r2", "§II hz1 第二次的 Δ"),
                         ("foyer_hz1_r3", "§II hz1 第三次的 Δ")):
            # 关键词跟正文走：2026-09-26 那句从 "below the line" 改成 "below it"
            # （同段里 "below the line" 已出现在别处，会撞车）。
            ck_near(_lab, "%.2f" % abs(float(_t1[_k]["delta_pp"])), "sec_background.tex",
                    "below it", window=200)

    # ---- §III 的层级匹配对（三列：占用均值 / R̄busy / 兑现率）----
    _oc = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/occupancy.csv"))}
    _ar = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/arm_running.csv"))}
    _ru = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/reuse.csv"))}
    for _r in ("cap3_fixed", "cap3_hc", "cap3_hc_r2"):
        if _r in _oc and _r in _ar and _r in _ru:
            ck("§III %s 占用均值" % _r, _oc[_r]["occ_mean_pct"], "sec_model.tex")
            ck("§III %s R̄busy" % _r, "%.2f" % float(_ar[_r]["running_busy"]), "sec_model.tex")
            ck("§III %s 兑现" % _r, "%.1f" % (100 * float(_ru[_r]["realized_frac"])), "sec_model.tex")
    # ---- §III 的**预注册**同卡配对（2026-09-26 落地）：判决由 gen_tierpair.py 给，
    # 正文里那几个数必须与它一致。判据**不在这里重实现** —— 读 tierpair.csv 的
    # 注释行（生成器已经把判决写在那里了），只核对正文有没有引对。----
    _tp = os.path.join(ROOT, "paper/data/tierpair.csv")
    if os.path.exists(_tp):
        _tpt = open(_tp, encoding="utf-8").read()
        for _tag in ("判决", "同卡这一对", "前提检查"):
            checks += 1
            if _tag not in _tpt:
                fails.append(("tierpair.csv 缺 %s 行" % _tag, "-", "paper/data/tierpair.csv"))
        # ⚠ **数据行也要核**：codex 第 34 轮指出，只查注释字串的话，
        # 「把 CSV 的数据行改错、注释与正文不动」这条守卫**照样通过**。
        # 判据：两对的兑现率必须与正文引的差一致（10.1 与 12.2）。
        _tpr = {r["run"]: r for r in load(_tp)}
        if _tpr:
            _g_new = (float(_tpr["cap3_ph"]["realized_pct"]) - float(_tpr["cap3_pd"]["realized_pct"]))
            _g_old = (float(_tpr["cap3_hc"]["realized_pct"]) - float(_tpr["cap3_fixed"]["realized_pct"]))
            for _d, _v in (("同卡那一对", _g_new), ("对照那一对", _g_old)):
                checks += 1
                if abs(_v - (10.14 if _d == "同卡那一对" else 12.23)) > 0.02:
                    fails.append(("tierpair.csv 的 %s 兑现差与正文不符" % _d,
                                  "%.2f" % _v, "paper/data/tierpair.csv"))
        # 正文必须写出「支持」这一判决与 10.1 这个差
        ck_near("§III 预注册配对的差距", "10.1", "sec_model.tex", "it lands at", window=200)
        # ⚠ 这个数 2026-09-26 从 0.7 改成 0.8：原来的 0.7 是拿 `one()` 返回的
        # **1 位小数**占用率算的，而原始 `token_usage` 给 0.78%（裁决不变）。
        ck_near("§III 预注册配对的前提（占用差）", "0.8", "sec_model.tex",
                "mean occupancy", window=200)
        ck_near("§III 预注册配对的前提（在跑数差）", "3.1", "sec_model.tex",
                "running count", window=200)

    # ---- attribution.csv：§V 的十二行归因表（2026-09-25 补：此前这张表完全没有检查）----
    at = load(os.path.join(ROOT, "paper/data/attribution.csv"))
    if at:
        # 正文里印的是 occ_pct / running / tau1_ms 三列 + 类别
        # 正文印的是 occ_pct / running / tau1_ms 三列，各自位数不同（running 到 3 位）。
        # 单独查一个数太容易在别处撞车，所以查【三列连起来】那个片段。
        for r in at:
            ck("归因 %s 的 占用&R̄&τ₁ 三连" % r["arm"],
               "%s & %.3f & %s" % (r["occ_pct"], float(r["running"]), r["tau1_ms"]),
               "sec_results.tex")
        import collections as _c
        _cls = _c.Counter(r["class"] for r in at)
        # 正文：「4 of the 12 rows are attributed: three to unused memory ... one to step cost,
        #       five have a tau no matched comparison can confirm, and three are residuals」
        # ⚠ 这几条**不能查单个数字** —— 归因数只有个位数（1/3/5），
        # 审计显示「1」在正文里出现 184 次、「3」165 次，等于空转
        # （2026-09-25 加了 --audit 才看见）。改成查【正文那一整句复合串】，
        # 计数一变这句话就对不上，检查才有意义。
        # ⚠ 2026-09-27：这张表原来只到 12，`len(at)` 变成 13 之后 `_NUM.get` 返回 "?"，
        # 于是守卫**自己造出一个查不到的串**（`Of the ? arms, seven are attributed`），
        # 报出来的是一条看不懂的 MISS —— 而真值是正文没改。表尾够长就行。
        _NUM = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
                7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
                13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen"}
        _n_mem = _cls.get("内存没用满", 0)
        _n_step = _cls.get("步成本更高", 0)
        _n_high = _cls.get("步成本更高（但对照的在跑数不可比）", 0)
        _n_res = _cls.get("残差（只能报观测）", 0)
        # ⚠ 2026-09-26 篇幅手术：这句从「6 of the 12 rows are attributed」改成
        # 「Of the twelve arms, six are attributed」。**判据仍是复合串**（分子分母
        # 在同一条短语里），只是跟着正文的新措辞 —— 改成单查一个数会退回到
        # 「同一个数在别处出现」那一类假通过。
        ck("§V 归因计数复合句（Of the M arms, N are attributed）",
           "Of the %s arms, %s are attributed" % (
               _NUM.get(len(at), "?"), _NUM.get(_n_mem + _n_step, "?")),
           "sec_results.tex")
        ck("§V 归因分项（三条内存 / 一条步成本 / 五条 τ 高 / 三条残差）",
           "%s to unused memory" % _NUM.get(_n_mem, "?"), "sec_results.tex")
        # ⚠ 2026-09-27（中立复核 r48 第 7b 条）：**这条守卫此前是死的。**
        # 原来写的是 `ck("§V τ 高行数", "%s\\nhave a $\\tau$" % ..., tier="S")`。
        # 两个毛病叠在一起：
        #   (a) `"\\n"` 在 Python 里是**字面反斜杠 + n**，而正文里是**换行** ——
        #       字面匹配**从来没有成功过**；
        #   (b) `tier="S"` 让它只印成次要项，**从不进 MISS** ——
        #       所以 (a) 一直没被人发现。值（2）本身是对的。
        # 改成 `ck_near` + 锚短语（默认 P 档）。`\\tau` 与 `$` 由 `re.escape` 处理。
        ck_near("§V τ 高行数", num_words(_n_high), "sec_results.tex",
                "have a $\\tau$", window=40)
        ck("§V 残差行数", "and %s are residuals" % _NUM.get(_n_res, "?"), "sec_results.tex")

    # ---- §III 的两个例证（default 与 foyfix_hc 对 foyer_hc 的分量差）----
    _dd = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    if "foyer_hc" in _dd:
        _b = _dd["foyer_hc"]
        for _r, _tag in (("default", "§III 无控制臂"), ("foyfix_hc", "§III 全关节流臂"),
                         ("foyer_bres_r2", "§III 去记账臂")):
            if _r not in _dd:
                continue
            for _k, _lbl in (("idle_min", "空转"), ("busy_min", "忙时"), ("wall_min", "墙钟")):
                _d = float(_dd[_r][_k]) - float(_b[_k])
                ck("%s 的 Δ%s" % (_tag, _lbl),
                   ("%.1f" if abs(_d) < 100 else "%.0f") % abs(_d), "sec_model.tex")

    # ---- repeat_spread.csv：§VI 引的那两个「这条 trace 自己的重复对」----
    rs = load(os.path.join(ROOT, "paper/data/repeat_spread.csv"))
    for r in rs:
        names = r["runs"].split()
        if "realhr_cap4" in names:
            ck("realhr cap4 重复对墙钟散布", r["spread_pct"], "sec_xtrace.tex")
        if "realhr_foyer" in names:
            # 这一组的 2 位小数不够（真值 0.023%），正文印的是 0.02 —— 所以从
            # metadata 的 wall_s（秒，未舍入）复算，而不是用表里那一列。
            import json as _j
            try:
                wa = _j.load(open(os.path.join(ROOT, "results/night/realhr_foyer/metadata.json")))["wall_s"]
                wb = _j.load(open(os.path.join(ROOT, "results/night/realhr_foyer_r2/metadata.json")))["wall_s"]
                ck("realhr foyer 重复对墙钟散布", "%.2f" % (100.0 * abs(wa - wb) / ((wa + wb) / 2)),
                   "sec_xtrace.tex")
            except Exception as e:
                ck("realhr foyer 重复对墙钟散布（读不到 metadata：%s）" % e, "?", "sec_xtrace.tex")

    # ---- replicates.csv：§VI 的「重复对墙钟散布 1.8--4.7%」----
    rp = load(os.path.join(ROOT, "paper/data/replicates.csv"))
    if rp:
        rr = sorted(float(r["wall_range_pct"]) for r in rp)
        ck("replicates 墙钟散布下界", "%.1f" % (rr[0] + 1e-9), "sec_xtrace.tex")
        ck("replicates 墙钟散布上界", "%.1f" % (rr[-1] + 1e-9), "sec_xtrace.tex")

    # ---- 摘要与 §V 的「非支配」声明：sf0_r2 不被表 I 的任何静态行支配 ----
    # 这是摘要里唯一一处【正面】声明（"not dominated ... 4.4pp above the nearest"），
    # 所以它必须机械可复算。判据就是非支配的定义：没有一条静态行在【墙钟更快】的
    # 同时【SLO 也更高】。
    _t = load(os.path.join(ROOT, "paper/data/table1.csv"))
    _stat = [r for r in _t if not r["run"].startswith(("foyer", "aimd", "foyfix"))
             and r["run"] != "default"]
    _sf = [r for r in _t if r["run"] == "foyer_sf0_r2"]
    if _sf and _stat:
        _w0, _s0 = float(_sf[0]["wall_min"]), float(_sf[0]["slo_pct"])
        _dom = [r["run"] for r in _stat
                if (float(r["wall_min"]) < _w0 and float(r["slo_pct"]) >= _s0)
                or (float(r["slo_pct"]) > _s0 and float(r["wall_min"]) <= _w0)]
        # 原来查的是 str(len(_dom))，也就是查「0」在摘要里出不出现 ——
        # --audit 显示 "0" 出现 20 次，等于空转。改成查【那句话本身】：
        # 只要支配行的数目变成非 0，这句话就不该留在摘要里，字面查才对得上。
        if len(_dom) == 0:
            # 正文 §V 的写法是 `\emph{not dominated}:`（没有 "by"），
            # 摘要压缩前那句是 `not dominated by any we measured` —— 两条各写各的。
            ck("§V 的「not dominated」声明", "\\emph{not dominated}", "sec_results.tex")
        else:
            fails.append(("摘要仍写 not dominated，但实测有 %d 条静态行支配 sf0_r2" % len(_dom),
                          "、".join(_dom), "main.tex"))

    # ---- backlog.csv：§VII 的队列长度 ----
    # 每个 run 两行：window=run（[最早提交, 最后完成]，与全篇墙钟同一窗口）与
    # window=all（全部控制周期）。**正文主张用 run 那一行**；all 那一行是稳健性对照，
    # 只以「4.1 而不是 3.7」和两个分母的形式出现。
    # 2026-09-25 codex 第 21 轮指出：只报全周期会把首个请求提交之前的空队列算进来，
    # 而 25 档短，那一段占它 12% 的周期（200 档只占 2%），于是中位从 18 掉到 16。
    # 键改成 (run, window) —— 原来按 run 建字典会静默只留后一行。
    _bl = {(r["run"], r["window"]): r
           for r in load(os.path.join(ROOT, "paper/data/backlog.csv"))}
    _early = [v for (r, w), v in _bl.items()
              if r.startswith("load25c_budget3") and w == "run"]
    if _early:
        # ⚠ 2026-09-26：**这两条退役，而且其中一条一直是假通过。**
        # 正文现在明写「we no longer quote a ratio between them」—— 两档之间的
        # backlog 比值是**刻意撤掉**的（它不是受控比较），所以「正文里印这两个中位数」
        # 这件事本身已经不成立。**值现在在哪**：`backlog.csv` 的 `waiting_p50`
        # 两行（11.0 / 13.0）。
        # 退役前顺手发现：下界那条（值 "11"）此前**靠一个代码哈希通过** ——
        # `d692ab11f396` 里的 `ab11f` 正好在 `has()` 的边界规则下算命中
        # （「同一个数在别处出现≠它用在了这里」的又一例，而且这次是*子串*）。
        # 它从来就没检查过那句中位数。
        ck_near("§VII 25 档 backlog 不再印比值",
                "no longer quote a ratio", "sec_discussion.tex", "backlog.csv", window=120)

    _25 = _bl.get(("pois200_foyer_push_25", "run"))
    # ⚠ **200 档那一半不再逐条查**：2026-09-25 重写这一段之后，正文引的是
    # 【归一化后的份额】、三个相位中位与「本档会话数」，**不再引 200 档的队列中位/最大值**。
    # 而 `§VII pois200_foyer_hc 队列中位` 那一条此前**一直在假通过**：
    # 它要找的 `66` 恰好是正文里 `266`（var_cap3 的分钟数）的**子串** ——
    # 2026-09-26 我把那个 266 改成 271，这条才第一次真的报 MISS。
    # **一个常年通过的检查，先想想它是不是在别处撞上的**（CLAUDE.md 有专条）。
    for _r in ("pois200_foyer_push_25",):
        if (_r, "run") in _bl:
            _k = _bl[(_r, "run")]
            ck("§VII %s 队列中位（运行窗口）" % _r, "%.0f" % float(_k["waiting_p50"]),
               "sec_discussion.tex")
            ck("§VII %s 队列最大（运行窗口）" % _r, _k["waiting_max"], "sec_discussion.tex")
            # 运行窗口的周期数正文不逐条印（印的是全周期数 + 窗口外的条数，
            # 两者相减就是它）。降为次要档，别拿「没印」当 MISS。
            ck("§VII %s 周期数（运行窗口）" % _r, _k["samples"], "sec_discussion.tex", tier="S")
            # 2026-09-25 中立子 agent 重写了这一段：现在引的是【归一化后的份额】、
            # 三个相位中位、以及非零周期占比 —— 都不是「哪个窗口的中位」。
            ck("§VII %s 本档会话数" % _r, _k["n_sessions"], "sec_discussion.tex")
            ck("§VII %s 扣住本档的比例" % _r, "%.0f" % float(_k["pct_of_tier"]), "sec_discussion.tex")
            # 相位中位**不能逐个数字查** —— 21/89/6/18/0 这种个位数正文里到处都是
            # （审计显示 "0" 出现 101 次、检查等于空转）。查正文里那一整句复合串。
            # ⚠ 2026-09-27 活性审计：这里原来有三条「相位（200 档在前）」检查，包在
            # `if _r.endswith("foyer_hc") and _25:` 里 —— 而 `_r` 恒为
            # `"pois200_foyer_push_25"`，**`endswith` 恒假 ⇒ 三条从未执行**。
            # 它们查的是「A against B」这种**两档比值**，而正文早已不引那个比值
            # （「we no longer quote a ratio between them」）⇒ 是**死代码**，删掉。
            ck("§VII %s 非零周期占比" % _r, _k["pct_nonzero"], "sec_discussion.tex")
        if (_r, "all") in _bl:
            # 2026-09-25 重写后，正文【不再跨档比队列长度】（两个 trace 不可比，
            # 按本档会话数归一后方向反过来）。全周期那一档留在 CSV 里供复算，正文不印。
            _a = _bl[(_r, "all")]
            for _lab, _val in (("队列中位", "%.0f" % float(_a["waiting_p50"])),
                               ("队列最大", _a["waiting_max"]),
                               ("周期数", _a["samples"])):
                ck("§VII %s %s（全周期）" % (_r, _lab), _val,
                   "sec_discussion.tex", tier="S")

    # ---- §IV 的 HiCache 弹性曲线（首跑）与「换成重复也不改结论」那句 ----
    import math as _m
    _dd = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/decomp.csv"))}
    _aa = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/arm_running.csv"))}
    def _eps(a0, a1):
        t0 = float(_dd[a0]["step_back_ms"]); t1 = float(_dd[a1]["step_back_ms"])
        r0 = float(_aa[a0]["running_busy"]); r1 = float(_aa[a1]["running_busy"])
        return _m.log(t1 / t0) / _m.log(r1 / r0)
    if {"pairB_cap2hc", "cap3_hc", "cap4_hc"} <= set(_dd) | set(_aa):
        # ⚠ 2026-09-26：这四条原来用 `ck()`（**全局**字符串查），于是**假通过**了两条：
        # 「重复段 2」实算 0.43 而正文写 +0.44 —— 检查通过是因为 +0.43 在
        # device-only 那段里也出现；「首跑段 1」实算 0.20 而正文写 +0.19，
        # 靠同一句里的 +0.20 蒙混。是 §III 的压缩子 agent 报出来的，
        # 正是本项目记过的「同一个数在别处出现 ≠ 它用在了这里」——**这次是守卫犯的**。
        # 改成 ck_near 锚到那句独有的话上（`substituting them moves`），
        # 两个数各自查，窗口只盖住那一句。
        # ⚠⚠ 2026-09-26：**口径**。这里原来自己用 `_eps()`（`arm_running.csv` 的
        # `running_busy`，六位小数）算，而正文第 40 行**明确声明**用的是
        # 「`decomp.csv` 的两位小数精度」，并披露「六位下各段差 0.01--0.03」。
        # 于是四条守卫比的是**另一个口径**，长期靠「同一个数在别处出现」假通过 ——
        # 一度被误判成「正文写错了」，差一点就去改**对的**正文。
        # 修法是**共用生成器的定义**：直接 import `gen_elasticity_hc.eps`，
        # 它内部走 `gen_elasticity.eps`（函数早就共用），分母列也由它决定。
        import importlib as _il
        _gehc = _il.import_module("gen_elasticity_hc")
        _gehc._ARM = {}          # 让它用 decomp.csv 的两位列，与正文声明一致
        _g2 = {"cap3_hc": 1, "cap4_hc": 1, "cap3_hc_r2": 1, "cap4_hc_r2": 1,
               "pairB_cap2hc": 1}
        if set(_g2) <= set(_dd):
            # 逐段锚定在正文那句独有的短语上，**两个数各自查**（防「同一句里另一个数顶上」）
            for _d, _a, _b in (
                    ("§IV HiCache 首跑段（锚定）", "pairB_cap2hc", "cap3_hc"),
                    ("§IV HiCache 重复段（锚定）", "pairB_cap2hc", "cap3_hc_r2")):
                _v = _gehc.eps(_dd, _a, _b)
                ck_near(_d, "%+.2f" % _v, "sec_criterion.tex",
                        "substituting them moves", window=260)
            for _d, _a, _b in (
                    ("§IV HiCache 首跑段 2（锚定）", "cap3_hc", "cap4_hc"),
                    ("§IV HiCache 重复段 2（锚定）", "cap3_hc_r2", "cap4_hc_r2")):
                _v = _gehc.eps(_dd, _a, _b)
                ck_near(_d, "%+.2f" % _v, "sec_criterion.tex",
                        "substituting them moves", window=260)

    # ---- toolwait.csv ----
    for r in load(os.path.join(ROOT, "paper/data/toolwait.csv")):
        for c in ("demand_med_s", "demand_mean_s", "measured_mean_s"):
            ck("toolwait %s %s" % (r["run"], c), r[c])
        # 第二条 trace 的两行（§VI/§criterion 引的 20.2 s / 39.9 s）
        if r["run"].startswith("realhr_"):
            ck("toolwait %s 要求中位" % r["run"], r["demand_med_s"], "sec_xtrace.tex")
            ck("toolwait %s 要求均值" % r["run"], r["demand_mean_s"], "sec_xtrace.tex")
        # §background 的「中位 1.001 / 两个均值之比 1.065」
        if r["run"] == "pois200_foyer_hc":
            ck("toolwait foyer_hc 比值中位", "%.3f" % float(r["ratio_med"]), "sec_background.tex")
            ck("toolwait foyer_hc 均值之比", "%.3f" % float(r["ratio_ratio_of_means"]), "sec_background.tex")

    # ---- idle_pooled.csv ----
    for r in load(os.path.join(ROOT, "paper/data/idle_pooled.csv")):
        # 正文印 all_runs；minus_* 是「去掉被争用标记的 run 之后结论不变」的稳健性
        # 变体，只在 §repro 里被描述，没有逐条印数
        for c in ("n_segments", "mean_s", "median_s", "pct_idle_time_in_gt20s"):
            ck("idle %s %s" % (r["set"], c), r[c],
               tier="P" if r["set"] == "all_runs" else "S")

    # ---- decomp.csv：三个区间 ----
    d = load(os.path.join(ROOT, "paper/data/decomp.csv"))
    T13 = {"cap1", "cap2", "cap3_fixed", "cap4", "cap5", "pairB_cap2hc", "cap3_hc",
           "cap4_hc", "foyer_hc", "foyer_hz1", "foyer_hz2_r2", "foyer_hz0_r2", "foyer_bres_r2"}
    d13 = [r for r in d if r["run"] in T13]
    for desc, vals in (
            ("τ₁ 上界", [float(r["step_back_ms"]) for r in d13 if r["step_back_ms"]]),
            ("τ₁ 下界", [float(r["step_back_ms"]) for r in d13 if r["step_back_ms"]]),
            ("τ₂ 上界", [float(r["step_perreq_ms"]) for r in d13 if r["step_perreq_ms"]]),
            ("τ₂ 下界", [float(r["step_perreq_ms"]) for r in d13 if r["step_perreq_ms"]])):
        ck(desc, max(vals) if "上界" in desc else min(vals))
    ex = [float(r["excess_pct"]) for r in d13 if r["excess_pct"]]
    ck("τ₁/τ₂ 超出下界", min(ex)); ck("τ₁/τ₂ 超出上界", max(ex))

    # ---- concurrency.csv 的计数 ----
    c = load(os.path.join(ROOT, "paper/data/concurrency.csv"))
    # ⚠⚠ 2026-09-28（r69 中立复核 §12.6）：原来是**全局串查** `ck(...)` —— 实测把正文的
    # `fourteen` 改成 `thirteen` **不报**，因为同文件别处还有另一个 `fourteen` 把它接住了
    # （本项目「同一个数在别处出现 ≠ 它用在了这里」的老病）。
    # ⇒ 改成 `ck_near`，锚在那句话独有的短语上。
    ck_near("CONTESTED 总数", sum(1 for r in c if r["verdict"] == "CONTESTED"),
            "sec_discussion.tex", "for at least an hour", window=40)

    # ---- projection.csv ----
    for r in load(os.path.join(ROOT, "paper/data/projection.csv")):
        if r["run"] == "pois200_foyer_hc":
            ck("foyer_hc 投影倍数", r["ratio"])
            ck("foyer_hc free%", r["free_pct"])
            # 正文 §V：「the growth reserve, which alone is 26,762 tokens, 28% of the budget」
            ck("foyer_hc 增长预留 tokens", r.get("growth_p50", ""))

    # ---- 图是否比数据旧 ----
    # 2026-09-24 碰巧发现：数据在 19:05/19:22 改过而图停在 18:43，正文的数与图对不上，
    # 而没有任何东西会提醒。图的输入是 decomp.csv / runs.csv / occupancy.csv 等。
    # 2026-09-25 修：原来拿【全部】paper/data/*.csv 的最新 mtime 去比，而图只读
    # 其中一部分 —— 于是 frontier_split.csv / a100.csv 这类**没有任何图读它**的表
    # 一更新，八张图就全被判成「旧」（假 MISS）。假阳性一多，真 MISS 就淹了
    # （本项目记过这条）。现在从 make_figs.py **现推**输入清单：
    # 它读数据一律走 `load("xxx.csv")`，正则抓出来即可，新增表也不会过时。
    figs = glob.glob(os.path.join(ROOT, "paper", "figs", "fig*.pdf"))
    if figs:
        _mf_p = os.path.join(ROOT, "paper", "figs", "make_figs.py")
        # 依赖有两类写法：`load("x.csv")`，以及**直接 open** 的
        # `os.path.join(..., "data", "x.csv")`（图 1 用它读 concurrency.csv 来给
        # 争用作废的臂画空心环）。只扫前者会**漏抓真实依赖** —— codex 第 25 轮
        # 指出：把那类漏掉，图在依赖更新后就不会被判为旧。
        _mf_src = open(_mf_p, encoding="utf-8").read()
        _deps = set(re.findall(r'load\("([^"]+\.csv)"\)', _mf_src))
        _deps |= set(re.findall(r'"data"\s*,\s*"([^"]+\.csv)"', _mf_src))
        _deps = sorted(_deps)
        _paths = [os.path.join(ROOT, "paper", "data", d) for d in _deps]
        _paths = [q for q in _paths if os.path.exists(q)]
        if not _paths:
            # 推不出来就**说出来**再退回保守判据，不静默（CLAUDE.md：静默跳过是危险方向）
            print("  · 图依赖清单推不出来（make_figs.py 里没有 load(\"*.csv\") 形态），退回「全部 CSV」判据")
            _paths = glob.glob(os.path.join(ROOT, "paper", "data", "*.csv"))
        # ⚠ **逐图判**，不是「所有 CSV 的最新 vs 每一张图」。后者只更新某张图的
        # 专属输入（如 `reuse_x.csv` 只被图 8 读）也会把其余七张判旧，是假 MISS
        # （codex 第 25 轮指出）。`make_figs.py` 现在会写 `.deps.json`
        # （图名 -> 它读过的 CSV），用它做精确判定；没有清单才退回保守判据。
        _deps_p = os.path.join(ROOT, "paper", "figs", ".deps.json")
        stale = []
        # ⚠⚠ 2026-09-28（r66 中立复核实测）：**`cp -r`（不保 mtime）拷出来的树，
        # 新鲜度判据没有意义** —— 拷贝按目录顺序盖 mtime，图可能恰好比它的输入「旧」。
        # 复核者在 `cp -r` 的树上实测到一条**假 MISS**（`图比它自己的输入旧`）。
        # 判据：**整棵树若挤在很短的时间窗内被写出（拷贝的特征）就跳过**，
        # 并**打一行说明**（不静默）。真机上的陈旧是「天」级差，不会被这个窗口吞掉。
        # ⚠ **两个分支都要** —— 第一版只加在 `else`（无 .deps.json）那支，
        # 而实际走的是这一支，等于没加。
        # ⚠⚠ 2026-09-28（r67 codex）：跨度必须对**整棵树**算。只看 figs+data 时，
        # **原树刚做过一次全量重生成**也会挤在一个小时内 ⇒ 真实的 1 小时级陈旧被跳过。
        # `docs/`、`CLAUDE.md`、老脚本不会跟着重生成 ⇒ 整棵树的跨度是「天」级。
        # ⚠⚠ 阈值收到 **120 秒**（r67 中立复核实测）：项目自己那次真事故是
        # **39 分钟**（2340 s）的陈旧，而 3600 s 的容差会把**它**也跳过 ——
        # 等于开了一个比要守的东西还宽的假通过窗口。`cp -r` 树的实测跨度
        # 是 0 / 12 / 27 秒 ⇒ 120 s 有 4 倍余量，且远小于 39 分钟。
        _allf = [q for q in (glob.glob(os.path.join(ROOT, "paper", "**", "*"), recursive=True)
                             + glob.glob(os.path.join(ROOT, "scripts", "**", "*"), recursive=True))
                 if os.path.isfile(q)]
        _sp = [os.path.getmtime(q) for q in (_allf or (_paths + figs))]
        _copied = bool(_sp) and (max(_sp) - min(_sp)) < 120
        if _copied:
            print("  · 整棵树的 mtime 挤在 %.0f 秒内（像是 `cp -r` 拷出来的）⇒ "
                  "跳过图的新鲜度判据（它只在源码树上有意义）" % (max(_sp) - min(_sp)))
        if _copied:
            pass   # 「像是拷出来的」那一行已经打过
        elif os.path.exists(_deps_p):
            import json as _json
            _dm = json.load(open(_deps_p, encoding="utf-8"))

            _unknown = []
            for _f in figs:
                _fn = os.path.basename(_f)      # deps.json 的 key 就是 pdf 文件名
                _d = _dm.get(_fn)
                if not _d:
                    _unknown.append(os.path.basename(_f))
                    continue
                _new = 0
                for _x in _d:
                    _q = os.path.join(ROOT, "paper", "data", _x)
                    if os.path.exists(_q):
                        _new = max(_new, os.path.getmtime(_q))
                if os.path.getmtime(_f) < _new:
                    stale.append(os.path.basename(_f))
            if _unknown:
                # 不静默：清单里没有的图等于**没人守它的新鲜度**
                print("  · .deps.json 里没有这些图，未判新鲜度：%s" % "、".join(_unknown))
        else:
            print("  · 无 .deps.json，退回保守判据（全部 CSV 的最新 vs 每张图）")
            newest_data = max((os.path.getmtime(q) for q in _paths), default=0)
            stale = [os.path.basename(f) for f in figs if os.path.getmtime(f) < newest_data]
            # ⚠⚠ 2026-09-28（r66 中立复核实测）：**用 `cp -r`（不保 mtime）拷树后再跑
            # 检查器，会报一条【假 MISS】**（`图比它自己的输入旧`）—— 因为 cp -r 按目录顺序
            # 盖 mtime，图可能恰好比它的输入「旧几毫秒」。AE 评审人若先 `cp -r` 再跑就会看到它。
            # 判据：**整棵树若是在很短的时间窗内被写出来的（拷贝的特征），新鲜度判据无意义**
            # —— 打一行说明并跳过；**真机上的陈旧是「天」级差**，不会被这个窗口吞掉。
            stale = [] if _copied else stale
        checks += 1
        if stale:
            # ⚠ 这里原来引用 `newest_data` —— 而它只在不走 `.deps.json` 的旧分支里
            # 才定义，于是新分支一旦真有 staleness 就 **NameError 崩掉整个检查器**
            # （2026-09-25 踩到：反向测试「没报 MISS」的真相是脚本挂了，
            # 而我 grep 的关键词把 traceback 挡掉了）。**假绿和崩溃要分清。**
            fails.append(("图比它自己的输入旧（需重跑 make_figs.py）",
                          "、".join(stale)[:58], "paper/figs"))
        elif VERBOSE:
            print("  OK   图不比它的 %d 个输入旧" % len(_paths))

    # ── 源码卫生：控制字符（Python 的 `\f`/`\v`/`\a` 转义会把 `\footnote`
    #    吃成换页符 + `ootnote`）────────────────────────────────────────────
    # 2026-09-26 codex 第 34 轮抓到：`sec_discussion.tex` 里一个 `\footnote` 被写成了
    # **U+000C 换页符 + `ootnote`** —— 那是我自己在 Python 里写 `"\footnote"`
    # （单反斜杠 → `\f` 是换页转义）造成的。PDF 里它成了正文文字「ootnoteFor F:t85」，
    # 而 **`Float too large` / `Overfull` 两条排版守卫都看不见它**。
    _ctrl = []
    for _f in sorted(os.listdir(os.path.join(ROOT, "paper"))):
        if not _f.endswith(".tex"):
            continue
        # ⚠⚠ 2026-09-28（r73 中立复核）：**`\r` 用文本读法看不到** ——
        # `open(..., encoding="utf-8")` 的 universal-newlines 会在 `read()` 时
        # 就把 0x0D 折成 `\n`（复核用二进制写入 0x0D 实测：默认读法看不见，
        # `newline=""` 才看得见）。⇒ 再加一条**二进制**扫描，专抓 `\r`。
        _raw = open(os.path.join(ROOT, "paper", _f), "rb").read()
        if b"\r" in _raw:
            _ctrl.append("%s:%d(0xd)" % (_f, _raw.index(b"\r")))
            continue
        _t = open(os.path.join(ROOT, "paper", _f), encoding="utf-8", newline="").read()
        for _i, _ch in enumerate(_t):
            if ord(_ch) < 32 and _ch != "\n":
                _ctrl.append("%s:%d(%s)" % (_f, _i, hex(ord(_ch))))
                break
    checks += 1
    if _ctrl:
        fails.append(("正文里有控制字符（多半是 Python 转义吃掉了反斜杠）",
                      "、".join(_ctrl)[:56], "paper/*.tex"))
    elif VERBOSE:
        print("  OK   全稿无控制字符")

    # ── 排版卫兵：Overfull / 页数 / 日志比正文旧 ────────────────────────────
    # 为什么把「排版」也放进数字检查器：CLAUDE.md 明写「征兆是**页数突然变少** ——
    # 编译后页数掉了，先怀疑有文件被清空」。而 2026-09-26 实测正文里**有一个
    # 51.99pt 的 Overfull**（§A100 的表 II 太宽），此前一直以为「0 Overfull」。
    # 排版的缺陷同样没有任何东西在守 —— 与「派生量没人管」是同一类盲区。
    _logp = os.path.join(ROOT, "paper", "main.log")
    checks += 1
    if not os.path.exists(_logp):
        fails.append(("main.log 不存在（没编译过？排版卫兵无从判起）", "-", "paper/main.log"))
    else:
        _lt = open(_logp, encoding="utf-8", errors="replace").read()
        _ovf = [l for l in _lt.splitlines() if l.startswith("Overfull")]
        # ⚠ **「Float too large for page」是比 Overfull 更重的一类**：它意味着某个
        # 浮动体（表/图）比一页还高，LaTeX 照样排版，于是**底部几行被裁掉** ——
        # 2026-09-26 实测：表 I 的 caption 有 471 词（整段论证写在 caption 里），
        # 浮动体超出 \textheight **124.85pt**，渲染出来**最后三行（两条 AIMD）
        # 看不见**。而「0 Overfull」一直是绿的 —— 因为 Overfull \hbox 与
        # Float too large 是**两回事**。判据必须两条都有。
        # ⚠ **不是 `startswith`**：这一条在日志里前缀是 `LaTeX Warning: `，
        # 写成 startswith 会**永远查不到**（2026-09-26 反向测试实测 ——
        # 塞了 400pt 竖直空间、日志里明明有 `Float too large`，守卫却 0 MISS）。
        _ftl = [l for l in _lt.splitlines() if "Float too large" in l]
        if _ftl:
            fails.append(("有浮动体比一页还高（底部内容会被裁掉）", "%d 处：%s"
                          % (len(_ftl), _ftl[0][:48]), "paper/main.log"))
        elif VERBOSE:
            print("  OK   0 Float too large")
        if _ovf:
            fails.append(("正文有 Overfull（排版溢出到栏外）", "%d 处：%s"
                          % (len(_ovf), _ovf[0][:48]), "paper/main.log"))
        elif VERBOSE:
            print("  OK   0 Overfull")
        # 悬空 \ref / \cite：LaTeX 只在日志里写一行 warning，**PDF 上是个 `??`**，
        # 而「0 Overfull」看不见它。2026-09-26 我自己就写了一个
        # `\ref{tab:split}`（那个 label 根本不存在）—— 是我手工 grep 才发现的。
        _und = [l for l in _lt.splitlines()
                if re.match(r"LaTeX Warning: (Reference|Citation)", l)]
        checks += 1
        if _und:
            fails.append(("有悬空的 \\ref / \\cite（PDF 里是 ??）",
                          "%d 处：%s" % (len(_und), _und[0][:60]), "paper/main.log"))
        elif VERBOSE:
            print("  OK   0 悬空的 ref/cite")
        # ── 排版卫兵第四条：**渲染出来的编号里不许出现 `-0`**（2026-09-27，r53 F6）
        # 为什么：`sec:repro` 的 label 原来挂在**没有编号**的 `\paragraph{Reproducibility.}`
        # 上，而 IEEEtran 的 `\theparagraph` = `\thesubsection` + `\arabic{subsubsection}`
        # + `\alph{paragraph}` —— §Discussion **没有 subsection**（计数器为 0），
        # 于是全稿 10 处 `\S\ref{sec:repro}` 都渲染成 **`§VIII-0e`**。
        # ⚠ `??` 守卫（上一条）**看不见这一类**：它只查 **undefined**，不查
        # 「已定义但难看」—— `0e` 是个合法定义的编号，只是它指向的东西不存在。
        # 判据：读 `main.aux` 的 `\newlabel{名}{{渲染值}{页}…}`，把 `\mbox` / 花括号 /
        # 空白剥掉后，渲染值里出现 `-0`（连字符紧跟 0）⇒ MISS。
        _auxp = os.path.join(ROOT, "paper", "main.aux")
        checks += 1
        if not os.path.exists(_auxp):
            fails.append(("main.aux 不存在（排版卫兵：渲染编号无从判起）", "-", "paper/main.aux"))
        else:
            _bad_lbl = []
            _aux_txt = open(_auxp, encoding="utf-8", errors="replace").read()
            _n_lbl = 0
            for _ln in _aux_txt.splitlines():
                # 渲染值字段里**自己带花括号**（`\mbox  {VIII-}0e`），所以不能用
                # `[^}]*` 取它 —— 用「字段在 `}{页码}{` 之前」这个结构来切（贪婪匹配，
                # 取到最后一个 `}{纯数字}{`），再剥 `\mbox` / 花括号 / 空白。
                _m = re.match(r"\\newlabel\{([^}]*)\}\{\{(.*)\}\{(\d+)\}\{", _ln)
                if not _m:
                    continue
                _n_lbl += 1
                _rend = re.sub(r"\\mbox\s*|\\protect\s*|[{}]", "", _m.group(2))
                if re.search(r"-\s*0", _rend):
                    _bad_lbl.append("%s→%s" % (_m.group(1), _rend.strip()))
            if _bad_lbl:
                fails.append(("有 \\ref 渲染出 `-0` 这样的编号（label 挂在没编号的单元上："
                              "看它的计数器前缀）",
                              "、".join(_bad_lbl)[:70], "paper/main.aux"))
            elif VERBOSE:
                print("  OK   0 个 `-0` 式的渲染编号（%d 个 label）" % _n_lbl)
        _mp = re.search(r"Output written on main\.pdf \((\d+) pages", _lt)
        checks += 1
        if not _mp:
            fails.append(("main.log 里读不到页数", "-", "paper/main.log"))
        else:
            _pg = int(_mp.group(1))
            # 下界守卫，不是目标：页数**掉了**才是信号（有文件被清空），
            # 而「页数多了」是本项目的软目标，由人判断，不在这里拦。
            if _pg < 10:   # 2026-09-27：下界从 14 改成 10（改投 RTAS 2027）
                # ⚠ 这个数**只是「有没有 .tex 被清空」的探针**，不是篇幅目标 ——
                # 目标由 venue 定，不由守卫定；守卫只负责在**掉得离谱**时喊。
                # 历史：30 页时代写 24 → 篇幅大手术后 14 → **RTAS 2027 要求技术正文
                # ≤11 页**（参考文献不计），目标 11，所以探针要落到目标之下。
                # ⚠ 若哪天真降到 9 页，先怀疑有 .tex 被清空，**再去调这个数**。
                fails.append(("页数掉到 %d（下界 10）—— 先怀疑有 .tex 被清空" % _pg,
                              "%d 页" % _pg, "paper/main.log"))
            elif VERBOSE:
                print("  OK   页数 %d（下界 10）" % _pg)
        # ⚠⚠ 2026-09-27：**上界此前没有任何守卫。**
        # RTAS 2027 的硬要求是「技术正文 ≤ 11 页，参考文献不计」，而 `main.log` 报的是
        # **含参考文献的总页数**。总页数 ≤ 12 是「正文 ≤ 11」的**充分**判据
        # （参考文献至少占一页，所以正文 12 页必然给出 ≥13）—— 保守、但方向正确。
        # 为什么必须补：本轮全部工作的起因就是这个硬限（35 行的表缩到 27 行、
        # §Load 整节删除），而守卫只管**下界**：「再多写 300 词」时
        # **页数会安静地变成 12 页正文，而 837 项检查 0 MISS**。
        # 目标 11 页是**约束**不是目标值，所以它必须在守卫里，不能只写在这里的注释里。
        if _mp:
            _npg = int(_mp.group(1))
            # ⚠⚠ 2026-09-27：上界判据换成「**技术正文** ≤ 11 页」。
            # 原来那条是 `总页数 > 12`，它是「正文 ≤ 11」的**充分**判据，
            # 前提是「参考文献只占一页」—— 那是 20 条引用时代的实情。
            # 应作者要求把引用补到 **46 条**（他们 35--86 条，中位 ~50）之后，
            # 参考文献本身要占 2 页以上，总页数 13 是**合规**的，
            # 而原判据会误报（本轮实测：1 项 MISS）。
            # RTAS 2027 的硬限是**技术正文** 11 页、参考文献不计，所以守卫必须量**正文**，
            # 而不是总量。量法：正文的末页 = 参考文献的**起始页**，除非参考文献
            # 正好从该页顶部开始（此时正文在前一页就结束了）——
            # 用 `pdftotext` 量「R EFERENCES 之前还有多少字」来区分这两种情形。
            import subprocess as _sp2
            checks += 1
            _bib_pg, _before = None, ""
            for _i in range(1, _npg + 1):
                _t = _sp2.run(["pdftotext", "-f", str(_i), "-l", str(_i),
                               os.path.join(ROOT, "paper", "main.pdf"), "-"],
                              capture_output=True, text=True).stdout
                _j = _t.find("R EFERENCES")
                if _j >= 0:
                    _bib_pg, _before = _i, _t[:_j]
                    break
            if _bib_pg is None:
                fails.append(("main.pdf 里找不到 R EFERENCES（参考文献一节丢了？）",
                              "-", "paper/main.pdf"))
            else:
                # 300 字：一页两栏满栏约 5,000 字，正文最后一段至少几百字；
                # 「顶部起排」时 _before 只剩页码/页眉，实测 < 20 字。
                _body_last = _bib_pg if len(_before.strip()) > 300 else _bib_pg - 1
                if _body_last > 11:
                    fails.append(("技术正文到第 %d 页（RTAS 2027 硬限 11 页，参考文献不计）"
                                  % _body_last,
                                  "参考文献起于第 %d 页，R EFERENCES 之前 %d 字；共 %d 页"
                                  % (_bib_pg, len(_before.strip()), _npg), "paper/main.pdf"))
                elif VERBOSE:
                    print("  OK   技术正文到第 %d 页（≤ 11；参考文献起于第 %d 页，共 %d 页）"
                          % (_body_last, _bib_pg, _npg))
        # 编译产物必须是**当前**正文的，否则上面两问读的是上一次的结果。
        # ⚠ 判据用 **md5 不用 mtime**：`cp` 回滚一个文件会把 mtime 顶新，
        # 而 latexmk 看到内容没变就**不重建**，于是 main.log 的 mtime 反而更旧 ——
        # 按 mtime 判会**假 MISS**（2026-09-26 实测，反向测试流程里必现）。
        # `main.fdb_latexmk` 里记着每个源文件在构建那一刻的 md5，正是要的东西。
        import hashlib as _hl
        _paper = os.path.join(ROOT, "paper")
        _fdb = os.path.join(_paper, "main.fdb_latexmk")
        # ⚠ **`.bib` 也要算进来**：`refs.bib` 改了不重编译，`.bbl` 就是旧的，
        # 而上面的页数/Overfull 会照旧「通过」。2026-09-26 扩到 .tex + .bib
        # （codex 第 31 轮问的就是这个情形）。
        # ⚠ `main.bbl` 也在 fdb 里（由 bibtex 规则记哈希）—— 若改了 `refs.bib`
        # 之后**只跑 bibtex**，`.bib` 的哈希会更新、这条守卫会通过，而 `main.bbl`
        # 已变、PDF 仍是旧的（codex 第 32 轮指出）。所以 `.bbl` 要单独比对。
        # ⚠⚠ 2026-09-27（装 supplement 时抓到）：**`supplement.tex` 要排除**。
        # 它是**独立编译的文档**（自己的 `supplement.tex` → `supplement.pdf`，
        # 单独上传给 RTAS），**不参与 `main.tex` 的构建**，所以它不会出现在
        # `main.fdb_latexmk` 里 —— 不排除就会**永久报一条假 MISS**。
        # 与上面 `TEX` 的排除是**同一个理由的两处**（那边是「副本会塌掉检查强度」，
        # 这边是「独立文档不在主构建的记录里」）。
        _texs = sorted(f for f in os.listdir(_paper)
                       if f.endswith((".tex", ".bib", ".bbl"))
                       and f != "supplement.tex")
        _rec = {}
        if os.path.exists(_fdb):
            _ft = open(_fdb, encoding="utf-8", errors="replace").read()
            for _m in re.finditer(r'^\s+"(?:[^"]*[/\\])?([^"/\\]+\.(?:tex|bib|bbl))"\s+'
                                  r'[\d.]+\s+\d+\s+([0-9a-f]{32})',
                                  _ft, re.M):
                _rec[_m.group(1)] = _m.group(2)
        checks += 1
        if _rec:
            _stale = [f for f in _texs
                      if _rec.get(f) != _hl.md5(open(os.path.join(_paper, f), "rb")
                                                .read()).hexdigest()]
            if _stale:
                fails.append(("这些源文件（.tex/.bib）的内容与上一次编译不一致",
                              "、".join(_stale)[:56], "paper/main.fdb_latexmk"))
            elif VERBOSE:
                print("  OK   所有 .tex/.bib/.bbl 的 md5 与上次编译一致（%d 个）" % len(_texs))
        else:
            _newest = max([os.path.getmtime(os.path.join(_paper, f))
                           for f in _texs] or [0])
            if os.path.getmtime(_logp) < _newest:
                fails.append(("main.log 比某个 .tex 旧，且读不到 fdb 的 md5（保守判据）",
                              "-", "paper/main.log"))
            elif VERBOSE:
                print("  OK   （无 fdb）main.log 比所有 .tex 新")

    # ── 定义唯一性：同一个量在全仓库只能有一份实现 ──────────────────────────
    # CLAUDE.md 纪律 2（两条管线算同一个量必须共用定义）与 2026-09-26 那条
    # 「抽成共用只做了一半，等于没做」。**判据是「旧写法的特征串出现 0 次」，
    # 不是「我改了一处」** —— 这一节把那个判据做成机械的，因为人工 grep 已经漏过两次：
    #   · `gen_a100_delta.py` 宣布与 frontier.py 共用 TIE，实际自设 `TIE = 1.0`；
    #   · `gen_pool50.py` 的 `interp()` 在 `envelope` 抽出来之后仍留着。
    # 两次数值都碰巧相同，所以**任何数据检查都不会响** —— 只能靠这种字面守卫。
    import glob as _g2
    _here = os.path.dirname(os.path.abspath(__file__))
    # ⚠ **必须排除检查器自己**：模式串写在本文件里，不排除就有自匹配风险
    # （与 CLAUDE.md 里 `pgrep -f` 自匹配是同一个坑）。本文件是检查器不是生成器，
    # 没有「两份实现要共用」的问题。
    _SKIP = {"check_paper_numbers.py"}
    _src = {}
    for _d in (_here, os.path.dirname(_here)):          # scripts/lab 与 scripts 一起扫
        for _p in sorted(_g2.glob(os.path.join(_d, "*.py"))):
            _n = os.path.basename(_p)
            if _n in _SKIP:
                continue
            _src[_n] = open(_p, encoding="utf-8").read()
    # ⚠ 判据是**结构**不是字面量。第一版写成字面子串 `"(y1 - y0) * (x - x0) / (x1 - x0)"`，
    # 于是 codex 第 30 轮一天之内抓到**三处**漏网 —— `gen_frontier_split.py` 的
    # `(s1-s0)*(w-w0)/(w1-w0)`、`gen_elasticity_x.py` 的 `(s1-s0)*(wall-w0)/(w1-w0)`、
    # `gen_arrival_slo.py` 里那个嵌套 `front()`：**换一套变量名就绕过去了**。
    # 现在用正则匹配「(a-b)*(c-d)/(e-f)」这个形状，与变量名无关。
    # ⚠ **两种写法都要 match**。第一版只 match `(a-b)*(c-d)/(e-f)`，
    # codex 第 31 轮给了个构造：`slope = (y1-y0)/(x1-x0); y = y0 + (x-x0)*slope`
    # —— 斜率先算出来，形状就只剩 `(a-b)/(c-d)`，第一种 match 不到。
    # `slo_sensitivity.py` 当年就是这么写的（`s0 + (w-w0)/(w1-w0)*(s1-s0)`），
    # 而它一直没被任何守卫看见。**判据要匹配的是【斜率】这个中间量。**
    _MUL = re.compile(r"\(\s*\w+\s*-\s*\w+\s*\)\s*\*\s*\(\s*\w+\s*-\s*\w+\s*\)"
                      r"\s*/\s*\(\s*\w+\s*-\s*\w+\s*\)")
    _SLOPE = re.compile(r"\(\s*\w+\s*-\s*\w+\s*\)\s*/\s*\(\s*\w+\s*-\s*\w+\s*\)")

    def _has_form(src):
        return bool(_MUL.search(src)) or bool(_SLOPE.search(src))
    # 白名单只有一条：`run_matrix.py` 是**解 memfrac 的线性求根**（在 (memfrac, 墙钟)
    # 上反解目标值），不是数据曲线的插值，不共用是**对的**。
    # 白名单四条，每条都要写清为什么【不共用是对的】：
    _FORM_OK = {
        "envelope.py",                  # 唯一实现
        "run_matrix.py",                # 在 (memfrac, 墙钟) 上【反解】目标值，不是数据曲线插值
        "independent_frontier_check.py",# **刻意独立**：它存在的意义就是另写一遍与生成器对拍
        "decode_rate.py",               # 探索脚本，产物不进 paper/data（τ₂ 的正式实现在 gen_decomp）
    }
    _owners = sorted(n for n, s in _src.items() if _has_form(s))
    checks += 1
    if _owners != sorted(_FORM_OK):
        fails.append(("分段线性插值的算式出现在 envelope.py 之外（各自的实现会分叉）",
                      "、".join(_owners) or "一处都没有（抽过头了？）", "scripts"))
    elif VERBOSE:
        print("  OK   分段线性插值只有 envelope.py 一份实现（run_matrix 的求根已白名单）")
    # ±1.0pp 打平带：常量只能定义一次（TIE_PP = 1.0），其余地方必须 import。
    # ⚠ 行尾**可以有注释**：`TIE_PP = 1.0   # ±1.0 pp 打平带 —— 唯一定义…`
    # 第一版写死 `\s*$`，于是 frontier.py 自己那一行匹配不上，报的是
    # 「没找到 TIE/BAND = 1.0」—— **假 MISS**，而假 MISS 会让人去改对的代码。
    _TIE = re.compile(r"(?m)^\s*([A-Za-z_]\w*)\s*=\s*1\.0\s*(?:#.*)?$")
    _tie = sorted(n for n, s in _src.items()
                  if any(("TIE" in m.group(1).upper() or "BAND" in m.group(1).upper())
                         for m in _TIE.finditer(s)))
    checks += 1
    if _tie != ["frontier.py"]:
        fails.append(("±1.0pp 打平带的定义不在 frontier.py 且唯一",
                      "、".join(_tie) or "没找到 TIE/BAND = 1.0", "scripts"))
    elif VERBOSE:
        print("  OK   ±1.0pp 打平带只有 frontier.py 一处定义")
    # ⚠ **形状匹配有极限，所以再加一条【正向】不变量**：凡是算前沿/包络的文件，
    # 必须 import `envelope`。codex 第 32 轮的构造（`dy=y1-y0; dx=x1-x0;
    # y=y0+(x-x0)*dy/dx`）两条形状正则都抓不到 —— 而想抓它就得匹配
    # `\* 名 / 名`，那在全仓库有 **16 处误报**（`100 * x / n` 这种）。**不加那种模式**，
    # 改成正向点名：下面这些文件不许把 import 删掉再自己内联。
    _MUST_IMPORT = ["frontier.py", "gen_a100_delta.py", "gen_pool50.py",
                    "gen_frontier_split.py", "gen_elasticity_x.py",
                    "gen_arrival_slo.py", "slo_sensitivity.py"]
    # ⚠ 名单里**不能放 envelope.py 自己** —— 它是被 import 的那一份，
    # 第一版把它写进去，于是干净状态就报 MISS（自己给自己当假阳性）。
    _miss_imp = [n for n in _MUST_IMPORT
                 if n in _src and "import envelope" not in _src[n]
                 and "from envelope" not in _src[n]]
    checks += 1
    if _miss_imp:
        fails.append(("这些文件不再 import envelope（把共用实现内联回去了？）",
                      "、".join(_miss_imp), "scripts"))
    elif VERBOSE:
        print("  OK   %d 个算前沿的文件都 import 了 envelope" % len(_MUST_IMPORT))

    # ⚠⚠ 2026-09-27（中立复核 r49 第 C17 条）：**第四条「看起来在守」的盲区。**
    # 上面那条「±1.0pp 打平带只有 frontier.py 一处定义」用的是**赋值式**正则
    # （`^\s*([A-Za-z_]\w*)\s*=\s*1\.0\s*$`），而 `gen_table.py` 与
    # `compare_rerun.py` 当时各自**内联**了 `> 1.0` / `>= -1` —— **正则永远看不到**，
    # 于是那条不变量**是假的而守卫报 0 MISS**。（想用形状正则抓内联比较，
    # 全仓有 16 处误报 —— 上面那条注释已经写过了。所以这里用**正向点名**。）
    # 现在两处都改成调用 `frontier.classify_short`（从 `classify` 派生）。
    # 这条守卫钉住「不许改回去」。
    _MUST_CLS = ["gen_table.py", "compare_rerun.py"]
    # ⚠⚠ 第一版这里写的是 `"classify_short" not in _src[n]` —— **假通过**：
    # 文件里的**注释**（「改成调用 `FR.classify_short`」）就含这个串，
    # 于是把内联改回去也不会响。反向测试当场抓到（改回内联 → 仍报 0 MISS）。
    # 判据必须是**调用式**：`classify_short` 后面跟 `(`。
    _miss_cls = [n for n in _MUST_CLS if n in _src
                 and not re.search(r"\bclassify_short\s*\(", _src[n])]
    checks += 1
    if _miss_cls:
        fails.append(("这些文件不再调用 frontier.classify_short（把 ±1.0 阈值内联回去了？）",
                      "、".join(_miss_cls), "scripts"))
    elif VERBOSE:
        print("  OK   %d 个产出判词的文件都调用 classify_short" % len(_MUST_CLS))

    # 反向测试（2026-09-26 做过）：把 `TIE_PP = 1.0` 复制一份进 gen_pool50.py，
    # 这一条报 MISS；把插值算式（**换个变量名**）抄进 gen_pool50.py，上面那一条报 MISS；
    # 把 gen_arrival_slo.py 的 import 删掉，正向这条报 MISS。

    # ---------------------------------------------------------------- 图注条数
    # 2026-09-26 加。**这是一条「派生量」守卫**：图 1 打空心圈的点数、图 2 打斜线
    # 的柱子数、图 3 带 ‡ 的行数，都是【代码算出来的集合规模】，而图注里写死了。
    # codex 与子 agent 在此前 34 轮里都没抓到它，因为**没人检查图注里的条数** ——
    # 与 CLAUDE.md 那条「检查器的系统性盲区是派生量（名次/条数/跨带）」同型，
    # 只是这次它落在图注而不是正文里。
    #
    # 实测（2026-09-26）：图 2、图 3 **各自只有 2 条**被标，而两句图注都写着 Three；
    # 图 3 那句还接着说「其中一条步成本明显偏高、所以被标的行聚在高位」——
    # 而 cap1 的步成本 28.8ms 在 34 行里排**第 11**（中位以下），AIMD 那条
    # \S\ref{sec:repro} 明写「flagged by the window but not measurably damaged」。
    # **三处说法全是当时那批 run 的旧状态**（bres/hz0/hz2/breshz1 重测干净后
    # 从被标集合里退了出去，图注没跟着改）。
    #
    # ⚠ **条数由画图的人自己报**（`paper/figs/.counts.json`，`make_figs.py` 落盘），
    # 检查器**不另写一遍筛选逻辑** —— 否则就是又一个「同一个量的两份实现」。
    #
    # 判据是**结构**的：在「<数词> bars are hatched」这类位置上取数词去比。
    # 改图注措辞不会假 MISS，只有**条数变了**才报。
    def _caption_of(label):
        """取某个 \\label{...} 所属的 \\caption{...} 全文（花括号配对）。

        ⚠ 必须**按图取图注**，不能在拼接后的全稿里搜短语：sec_model.tex 里
        有两处都写着「thirty-four runs of」，先撞上哪个取决于文件顺序。
        这与「一条检查如果常年通过，先想想它是不是在别处撞上的」是同一族。
        """
        # ⚠⚠ 用 `paper_text_struct()`，**不是** `P`（= `paper_text()`）：
        # 后者现在连 `\label{}` 一起剥掉了（为了关掉「命令 key 里的数字喂给 has()」
        # 那条假通过通道），拿它来找 label 必然全空 —— 2026-09-27 实测报 3 条
        # 「找不到这张图的 caption」的假 MISS。见 `paper_text_struct` 的说明。
        for _fn, _s in _PSTRUCT.items():
            k = _s.find("\\label{%s}" % label)
            if k < 0:
                continue
            # ⚠ **限制在同一个 figure 环境里**。原来用 `rfind("\\caption{", 0, k)`
            # 向前找最近的一个 —— codex 第 35 轮给了构造：目标图写
            # `\caption[short]{Three bars are hatched.}`（合法写法）时它匹配不上，
            # 于是**取到上一张图的 caption**，错的数照样通过；label 在上、
            # caption 在下时同样会取错。`\begin{figure` 前缀同时盖住 `figure` 与
            # `figure*`（IEEEtran 的跨栏浮动体）。
            _b = _s.rfind("\\begin{figure", 0, k)
            _e = _s.find("\\end{figure", k)
            if _b < 0 or _e < 0 or not (_b < k < _e):
                continue
            # 剥掉未转义的 `%` 注释：否则 figure 里一句被注释掉的
            # `% \caption{Two bars are hatched.}` 会被当成真的 caption
            # （codex 第 36 轮的构造）。
            _seg = strip_comments(_s[_b:_e])
            _m = re.search(r"\\caption\s*(\[[^\]]*\])?\s*\{", _seg)
            if not _m:
                continue
            a = _m.end(); depth = 1
            while a < len(_seg) and depth:
                if _seg[a] == "{":
                    depth += 1
                elif _seg[a] == "}":
                    depth -= 1
                a += 1
            return _fn, _seg[_m.end():a - 1]
        return None

    def _cap_n(cap, tail):
        """图注里「<数词> <tail>」位置上的数词。tail 里的空格写成 \\s+ ——
        LaTeX 源码是硬换行的，「points drawn with a\n  hollow ring」这种
        断行会让字面空格的短语永远匹配不上（本项目已栽过三次）。"""
        if not cap:
            return None
        # ⚠ 先剥掉排版命令与花括号：codex 第 35 轮的构造 `\mbox{thirty-}two bars
        # are hatched` **排版出来就是 thirty-two**，而正则只看到 `two bars` → 返回 2。
        # `{,}`（千分位）剥完变成 `,`，对这个用途无害（只取短语前的数词）。
        cap = re.sub(r"\\(?:mbox|hbox|text|textrm|textit|textbf|mathrm|emph|mbox)\s*\{",
                     "", cap)
        cap = cap.replace("{", "").replace("}", "")
        # 距离/间距命令换成**空**：`Thirty\,two` 排版出来就是 `Thirtytwo`
        # == `thirty-two`（codex 第 36 轮的构造，原来会被读成 `two`）。
        cap = re.sub(r"\\[,;:! ]|~", "", cap)
        # 词表里的连字符写法与**去连字符**写法都认（`thirty-two` / `thirtytwo`）。
        _alt = sorted({w for w in _WORD.values()} |
                      {w.replace("-", "") for w in _WORD.values()},
                      key=len, reverse=True)
        m = re.search(r"(?<![A-Za-z])(" + "|".join(re.escape(w) for w in _alt)
                      + r"|[0-9]+)\s+" + tail, cap, re.I)
        if not m:
            return None
        w = m.group(1).lower()
        for k, v in _WORD.items():
            if w == v or w == v.replace("-", ""):
                return k
        return int(w) if w.isdigit() else None

    _CNT = os.path.join(ROOT, "paper", "figs", ".counts.json")
    try:
        _cnt = json.load(open(_CNT))
        for _label, _tail, _key, _fig in (
                # ⚠ `(?:are\s+)?` 是 2026-09-26 加的：图注从 "Two points drawn with"
                # 改成 "Two points are drawn with" 之后，原来的正则匹配不到，
                # 解析出 None，报了一条**假 MISS**（正文与图都是对的）。
                # 「改图注措辞不会假 MISS」这句当时写得太满 —— 只要正则里带了虚词就会。
                ("fig:frontier", r"points\s+(?:are\s+)?drawn\s+with\s+a\s+hollow\s+ring",
                 ("fig1_frontier.pdf", "rings"), "图 1（空心圈）"),
                # 2026-09-26：图 2 的行数从 34 减到 17 之后，图注的措辞变成
                # 「the seventeen runs the figure draws」（原来的 "runs of" 没了），
                # 正则随之放宽成「runs (of|the figure draws)」。
                ("fig:decomp", r"runs\s+(?:of|the\s+figure\s+draws)",
                 ("fig2_decomp.pdf", "bars"), "图 2（柱子总数）"),
                # ⚠ 2026-09-28：fig7 的图注里有两个**可数主张**（"five device-only
                # configurations" / "six HiCache configurations"），而它此前
                # **没有**登记 `.counts.json` ⇒ **一条守卫都没有**（项目记过的
                # 「图注里的条数也是派生量」）。条数由画图的人报，守卫只读不重算。
                ("fig:cancel", r"device-only\s+configurations",
                 ("fig7_elasticity.pdf", "device_points"), "图 7（device-only 点数）"),
                ("fig:cancel", r"HiCache\s+configurations",
                 ("fig7_elasticity.pdf", "hicache_points"), "图 7（HiCache 点数）"),
                # ⚠ 2026-09-26（第二次）：条数从 2 变成 1 之后，图注按英文改了**单数**
                # （`One bar is hatched` / `One row carries the`），而这两条正则
                # 写死了复数（`bars are hatched` / `rows ... carry the`）→ 解析出
                # None，又是两条**假 MISS**，正文与图都是对的。
                # 「改图注措辞不会假 MISS」这句上一次（`are drawn with`）已经破过一次，
                # 这是第二次 —— 凡正则里带了**数/格**的虚词，改措辞就会。
                # 现在单复数都认；`(?<![A-Za-z])` 的边界规则不变。
                ("fig:decomp", r"bars?\s+(?:are|is)\s+hatched",
                 ("fig2_decomp.pdf", "hatched"), "图 2（打斜线的柱子）")):
            _want = _cnt.get(_key[0], {}).get(_key[1])
            _capf, _capt = _caption_of(_label) or (None, None)
            if _capf is None:
                checks += 1
                fails.append(("找不到这张图的 caption（label 对不上？）", _label, "paper"))
                continue
            _got = _cap_n(_capt, _tail)
            checks += 1
            if _want is None:
                fails.append(("图上没报出这个条数（.counts.json 缺键）",
                              "%s %s" % _key, "make_figs.py"))
            elif _got != _want:
                fails.append(("图注里的条数与该图实际画出的集合规模不符",
                              "%s：图注写 %s，实际 %d 条" % (_fig, _got, _want),
                              _capf or _label))
            elif VERBOSE:
                print("  OK   %s 的图注条数 = 实际 %d 条" % (_fig, _got))
    except Exception as _e:      # 不静默：跑不起来本身就是问题
        checks += 1
        fails.append(("图注条数守卫没能跑起来", repr(_e)[:60], "scripts"))

    # ---------------------------------------------------------------- 「还在排队」
    # 2026-09-26 加。CLAUDE.md 纪律 1 记的是「**不要把还没跑的实验写成已跑**」——
    # 而这一批抓到的是它的**镜像**：**把已经跑完的实验写成还在排队**。
    # codex 第 35 轮报了 1 处（§VI 说 A100 基线的重跑 still queued），
    # 我顺着这个词 grep 全稿又抓到 **2 处**（§VI 与 §VI 都说同卡层级配对
    # 「is queued rather than done」，而那一对**已经跑完**、§III 报的就是它的判决）。
    #
    # 判据不用「数出现几次」（措辞一改就假 MISS），而是：
    # (a) 每处含 "queued" 的句子都打印出来供人扫一眼；
    # (b) 对**已经作废的旧说法**点名禁止 —— 这几句都曾真实存在于稿子里。
    _Q_STALE = ["still queued", "queued rather than done", "is queued (",
                "a re-run is queued", "clean re-runs of that family are in flight",
                "in flight", "is pending", "to be run"]   # 全部按小写比较
    _qhit = []
    for _fn, _txt in P.items():
        for _m in re.finditer(r"\bqueued\b", _txt):
            # 打印**词前后各 70 字**，不是「整句」—— 句子可能很长，截断后反而
            # 看不见关键词本身（第一版就是这样，第 4 条打印出来根本不含 queued）。
            _qhit.append((_fn, " ".join(_txt[max(0, _m.start() - 70):
                                              _m.start() + 70].split())))
    checks += 1
    # ⚠ 禁词**不区分大小写**：codex 第 36 轮实测，`a re-run is queued` 会被拦、
    # 而句首大写的 `A re-run is queued` 绕过 —— 同一个说法两种大小写，一个拦一个放。
    # ⚠ 「逐句列出」**每次都打印**（原来只在 `-v` 下打）：它是这一条守卫的全部价值所在
    # （提醒人逐句确认），藏在开关后面等于没有。只有 4~8 行，不吵。
    _low = lambda x: x.lower()
    _bad_q = [(f, t) for f, t in _qhit if any(x in _low(t) for x in _Q_STALE)]
    if _bad_q:
        fails.append(("正文里出现【已经作废】的「还在排队」说法（那件事已经跑完了）",
                      _bad_q[0][1][:70], _bad_q[0][0]))
    else:
        print("  ·   %d 处提到 queued，逐句列出（每句都要确认那件事【真的还在排】）："
              % len(_qhit))
        for _f, _t in _qhit:
            print("        [%s] %s" % (_f, _t[:96]))

    # ------------------------------------------------ 会【随时间变假】的词
    # 2026-09-26 加。这一批的「queued」是同一族的一个成员：**句子里锚了一个
    # 写稿当时的时点**，而稿子要活到投稿。`sec_results.tex` 原来写着
    # 「one of them reads 1.95 **today**」—— 那个 run 早就跑完了，
    # 1.95 在现在的 `projection.csv` 里根本不存在（main_trace 的 max 是 1.96）。
    # 不是数字错，是**这句话的有效期**过了，而没有任何东西会提醒。
    # ⚠ 词间用 `\s+`：TeX 源码硬换行，`at the time of\nwriting` 排版后仍是那个短语，
    # 而字面空格的正则**不命中**（codex 第 36 轮实测）。`\emph{writing}` 这种插标记的
    # 写法不追 —— 那是排版而非措辞（本项目的「形状匹配有极限」）。
    # ⚠ 词间还要认 TeX 的**不换行空格 `~`**（`for~now` 排版出来就是 "for now"）
    # 与 `\ `（反斜杠空格）。codex 第 37 轮实测 `for~now` 绕过了原来只认 `\s+` 的正则。
    # （`\emph{writing}` 这种**插标记**的写法仍不追 —— 那是排版不是措辞。）
    _SP = r"(?:\s|~|\\ )+"
    _TIMEY = [r"\btoday\b", r"\bat" + _SP + r"the" + _SP + r"time" + _SP + r"of" + _SP + r"writing\b",
              r"\bas" + _SP + r"of" + _SP + r"this" + _SP + r"writing\b",
              r"\bfor" + _SP + r"now\b",
              r"\bat" + _SP + r"present\b", r"\bcurrently" + _SP + r"reads\b"]
    _thit = []
    for _fn, _txt in P.items():
        for _pat in _TIMEY:
            for _m in re.finditer(_pat, _txt, re.I):
                _thit.append((_fn, " ".join(
                    _txt[max(0, _m.start() - 60):_m.start() + 60].split())))
    checks += 1
    if _thit:
        fails.append(("正文里有【锚在写稿当时】的词（会随时间变假）",
                      "%d 处：%s" % (len(_thit), _thit[0][1][:60]), _thit[0][0]))
    elif VERBOSE:
        print("  OK   正文没有「today / at the time of writing」这类会过期的锚")

    # ------------------------------------------- §VI 的 flag 计数（按 trace 拆）
    # 2026-09-26 加。独立复核子 agent 第 19 轮抓到：这一句原来写
    # 「Fourteen of our **main-trace** runs are; three more are on the moving-load
    # trace」，而 `concurrency.csv` 逐条数出来是 **主 trace 12 + 变负载 2 = 14**，
    # 而且**同一段的下一句自己写的是「Fourteen of our runs … two are Table I
    # rows and twelve are arms we do not report」**—— 两句互相矛盾。
    # 检查器一处都没报，因为它从来不按 trace 拆过这个集合。
    _cc = load(os.path.join(ROOT, "paper/data/concurrency.csv"))
    _by = {}
    for _r in _cc:
        if _r.get("verdict") != "CONTESTED":
            continue
        _mp = os.path.join(ROOT, "results", "night", _r["run"], "metadata.json")
        _t = "?"
        if os.path.exists(_mp):
            _t = os.path.basename((json.load(open(_mp)).get("trace") or "?"))
        _by[_t] = _by.get(_t, 0) + 1
    _main = _by.get("replay_pois200_l04.csv", 0)
    _var = _by.get("replay_varload_lo2hi.csv", 0)
    checks += 1
    if _main + _var != sum(_by.values()):
        fails.append(("被判 CONTESTED 的 run 出现在预期之外的两条 trace 上",
                      "、".join("%s=%d" % kv for kv in sorted(_by.items())), "concurrency.csv"))
    else:
        ck_near("§VI 主 trace 上的 flag 条数", num_words(_main),
                "sec_discussion.tex", "on the main trace and")
        ck_near("§VI 变负载 trace 上的 flag 条数", num_words(_var),
                "sec_discussion.tex", "on the moving-load")
        ck("§VI flag 总数", num_words(_main + _var), "sec_discussion.tex")
    # 「四条四个车道的 run 被杀了」—— 目录名以 `_failed_4lane_` 开头的条数。
    _nfail = len([d for d in os.listdir(os.path.join(ROOT, "results", "night"))
                  if d.startswith("_failed_4lane_")])
    # ⚠ 查**整句**「killed four runs outright」，不能只查数词 —— 这句话里
    # "four" 出现三次（fourteen / four runs / a four-lane launch / none of the four），
    # 反向测试（four→five）**没报 MISS**。与今天早先「566 of 566」是同一个坑：
    # **同一个数在同一个短语里出现两次，单值检查就废了。**
    ck_near("§VI 被四车道杀掉的 run 数",
            "killed %s runs outright" % _WORD.get(_nfail, str(_nfail)),
            "sec_discussion.tex", "incident that created")
    # 33.3 ms 属于哪条臂：**它必须是「被 flag 的臂里 τ₂ 最大的那条」**，
    # 而且那条臂**现在不在表 I 里带 ‡**（`breshz1` 已被 `breshz1_r2` 替换）。
    # 旧句写「the one affected arm still carrying the flag in Table I」，而表 I
    # 带 ‡ 的两行读 20.6 与 24.4 —— 独立复核抓到的正是这一条。
    _f = [(float(_r["tau2_ms"]), _r["run"]) for _r in _cc
          if _r.get("verdict") == "CONTESTED" and _r.get("tau2_ms") not in (None, "", "None")]
    if _f:
        _mx = max(_f)
        ck_near("§VI 被 flag 臂里 τ₂ 最大者", "%.1f" % _mx[0], "sec_discussion.tex",
                "worst-affected")
        if "still carrying" in P.get("sec_discussion.tex", ""):
            fails.append(("§VI 仍说某条带旗的臂在表 I 里（表 I 现在只有两条带旗，"
                          "且都不读那个值）", "still carrying", "sec_discussion.tex"))

    # ------------------------------------------- §A100 基线与控制器的逐分位对比
    # 2026-09-26 加（独立复核子 agent 第 19 轮）：原来写「tracking it at every
    # completion quantile」，实算 **baseline 在 501/999 个分位更快**，p90/p95/p99
    # 分别慢 33.8 / 25.1 / 45.4 s，最大落后 83.5 s。**「每个分位都贴着」不成立。**
    # 已改成「前七个十分位内相差 4 s 以内、只在尾部拉开」，这里把它钉住。
    _c_d = os.path.join(ROOT, "results", "night", "a100_default")
    _c_f = os.path.join(ROOT, "results", "night", "a100_foyer_hz2")
    if os.path.exists(os.path.join(_c_d, "steps.jsonl")) and \
       os.path.exists(os.path.join(_c_f, "steps.jsonl")):
        def _comp(_dd):
            _st = [json.loads(l) for l in open(os.path.join(_dd, "steps.jsonl")) if l.strip()]
            _t0 = min(x["submit_timestamp"] for x in _st if x.get("submit_timestamp"))
            return sorted(x["complete_timestamp"] - _t0 for x in _st
                          if x.get("complete_timestamp"))
        _b, _f2 = _comp(_c_d), _comp(_c_f)
        _n2 = min(len(_b), len(_f2))
        _dec = [abs(_b[min(_n2 - 1, int(round(k / 10 * (_n2 - 1))))]
                    - _f2[min(_n2 - 1, int(round(k / 10 * (_n2 - 1))))])
                for k in range(1, 8)]
        _gap = "%.0f" % (max(_dec) + 0.5)      # 3.5 -> 4（向上取整，正文是「以内」）
        ck_near("§A100 前七个十分位的最大差（s，向上取整）", _gap,
                "sec_xtrace.tex", "each of the first seven")
        if "tracking it at every completion" in P.get("sec_xtrace.tex", ""):
            fails.append(("§A100 又写回了「每个完成分位都贴着」——实测不成立",
                          "tracking it at every completion", "sec_xtrace.tex"))

    # ------------------------------------- 图 2 图注里剩余的三个派生量（独立复核 m1）
    # 这三个数此前**没有任何守卫**：把 6.3 改成 6.4、36.3 改成 36.4、11.4 改成 11.5，
    # 检查器都 0 MISS（独立复核子 agent 实测）。它们都是 `decomp.csv` 的现算量。
    _dc = [r for r in load(os.path.join(ROOT, "paper/data/decomp.csv")) if r.get("idle_pct")]
    if _dc:
        _fast = min(_dc, key=lambda r: float(r["wall_min"]))
        _slow = max(_dc, key=lambda r: float(r["wall_min"]))
        # ⚠⚠ 2026-09-27（r51 双审查 C3，**假通过**）：这两条原来只查「这个值在
        # 关键词 ±260 字符内出现过」。而同一句话里有**四**个数 —— 区间的两端
        # （`6.3` / `41.9`）与两个端点读数（`6.3` / `36.3`）—— 全部落在那个窗口里。
        # 实测：`41.9` 距关键词 `for the slowest` 只有 **52 字符**，
        # 于是把「最慢配置的空转率」写成 `41.9` 也照样通过。
        # 这正是「同一个数在别处出现 ≠ 它用在了这里」—— **而这次的「别处」就在同一句里**。
        # 改法是**改锚**：把数与它所属的配置绑成一个复合串再查。
        # `has()` 对非数字串走字面（空白弹性）匹配、**不做小数位放宽** ⇒ 绑得死。
        ck_near("图 2 图注最快配置的空转率",
                "%.1f\\%% for the fastest configuration" % float(_fast["idle_pct"]),
                "sec_model.tex", "the idle range")
        ck_near("图 2 图注最慢配置的空转率",
                "%.1f\\%% for the slowest" % float(_slow["idle_pct"]),
                "sec_model.tex", "the idle range")
        # 同一句里的**区间两端**（此前一条守卫都没有；`6.3` 是 min、`41.9` 是 max）
        ck_near("图 2 图注的空转区间（两端绑成一个复合串）",
                "%.1f\\%% to %.1f\\%%" % (min(float(r["idle_pct"]) for r in _dc),
                                         max(float(r["idle_pct"]) for r in _dc)),
                "sec_model.tex", "the idle range")
        _byidle = sorted(_dc, key=lambda r: float(r["idle_pct"]))
        _nc = [r for r in _byidle if r["run"] == "default"]
        if _nc:
            ck_near("图 2 图注 no-control 的空转名次", num_words(_byidle.index(_nc[0]) + 1),
                    "sec_model.tex", "on idle share")
            ck_near("图 2 图注 no-control 的空转率", "%.1f" % float(_nc[0]["idle_pct"]),
                    "sec_model.tex", "on idle share")
        _bydur = sorted(_dc, key=lambda r: float(r["wall_min"]))
        if _nc:
            ck_near("图 2 图注 no-control 的时长名次", num_words(_bydur.index(_nc[0]) + 1),
                    "sec_model.tex", "on duration")
    # §III 正文里同一个条数（图注那处已守，正文这处此前没有 —— 独立复核 m2）
    if _dc:
        # ⚠ 关键词**不能跨行**：正文是「… the thirty-four runs of\n Table~\ref{...}」，
        # 写 `runs of \S\ref{sec:model}` 会假 MISS（本项目栽过四次）。
        # ⚠ 2026-09-26：图 2 只画 17 条之后，这句改成「shows the split, for seventeen
        # of the thirty-four runs」—— 图注与正文两头都要写清「画的是子集、范围是对全集算的」，
        # 否则读者会把「图上的 17 条」当成「统计的 34 条」。
        _dw = num_words(len(_dc))
        ck_near("§III 正文的 run 条数（全集）", _dw, "sec_model.tex",
                "shows the split", window=70)
        # 画出来的子集规模：从 make_figs 落的 .counts.json 现取（**不另写一份筛选逻辑**）
        try:
            _bars = json.load(open(os.path.join(ROOT, "paper", "figs", ".counts.json")))[
                "fig2_decomp.pdf"]["bars"]
        except Exception as _e:
            _bars = None
            fails.append(("取 .counts.json 的 bars 失败（这条守卫没跑起来）", repr(_e)[:50], "paper/figs"))
        if _bars:
            ck_near("§III 正文的 run 条数（画出来的子集）", num_words(_bars),
                    "sec_model.tex", "shows the split", window=70)

    # ---- 图 1 那条「标出越线的那条臂」的标注（2026-09-27 重写）----
    # 历史：坐标原来**写死**在 `make_figs.py` 里，2026-09-25 最佳臂换人之后
    # 标注指在了一条已经不是最佳的臂上（codex 第 25 轮抓到，靠人读图才发现）；
    # 2026-09-27 `foyer_scan` 落地后，那句写死的「(tie, below it)」整句失效
    # （Δ 最大的臂**判决是 ABOVE**）。
    # **修法不是把坐标改成新值**（下次还会漂），是让标注从 `paper/data/table1.csv`
    # 现取 —— 标签取 `label` 列、坐标取 `wall_min`/`slo_pct`、数字取 `delta_pp`、
    # 「几条 run」按表里同标签的行数现数。
    # 所以这条守卫现在守两件事：
    #   (a) 那三样**确实是算出来的**（写死的坐标对/措辞不许回来）；
    #   (b) 正文 §V 里**有一段在讲那个点**（图与正文指的必须是同一条臂）。
    try:
        _mf = open(os.path.join(ROOT, "paper", "figs", "make_figs.py"), encoding="utf-8").read()
        checks += 1
        _hard = re.search(r'"best Foyer|best Foyer\\n\(tie', _mf)
        _derived = re.search(r'_BST_W, _BST_S = float\(_bst\["wall_min"\]\)', _mf)
        _nrep = re.search(r'_n_rep = sum\(1 for r in _t1', _mf)
        if _hard or not _derived or not _nrep:
            fails.append(("图 1 的标注又变成写死的了（最佳臂换人时会漂）",
                          "写死:%s 坐标现取:%s 条数现数:%s" % (bool(_hard), bool(_derived), bool(_nrep)),
                          "paper/figs/make_figs.py"))
        # (b) 被标的那条臂 = table1.csv 里 Δ 最大的控制器行；正文那段必须点得到它
        _rs2 = P.get("sec_results.tex", "")
        _t1f = [r for r in load(os.path.join(ROOT, "paper/data/table1.csv"))
                if r["run"].startswith(("foyer_", "aimd2_", "foyfix")) and r.get("delta_pp")]
        _best = max(_t1f, key=lambda r: float(r["delta_pp"]))
        checks += 1
        # ⚠⚠ 2026-09-27（落地）：这里原来写死 `"One point in Fig."` ——
        # `scan_r2` 落地后图上有**两个**点越线，改正文就会**被这条守卫拦住**。
        # 守卫写死正文措辞 = 它锁死旧说法（本项目记过：「锚失配 = 沉默」，
        # 而这里是反过来：**锚太死 = 挡住正确的修改**）。
        # 改成**从 table1.csv 现数**越线的点数，再要求正文写出对应的词。
        _n_above = sum(1 for r in _t1f if r.get("delta_pp")
                       and float(r["delta_pp"]) > 1.0)
        _above_word = {1: "One point", 2: "Two points",
                       3: "Three points"}.get(_n_above, "%d points" % _n_above)
        if _above_word + " in Fig." not in _rs2:
            fails.append(("§V 没有讲那个越线的点（图 1 的标注没有对应的正文）",
                          "缺「One point in Fig.」那段", "sec_results.tex"))
        elif VERBOSE:
            print("  OK   图 1 标注臂 = %s（Δ=%s，%s）"
                  % (_best["run"], _best["delta_pp"], _best.get("verdict")))
    except Exception as _e:
        fails.append(("图 1 的标注守卫没跑起来", repr(_e)[:60], "paper/figs/make_figs.py"))

    # ---- §I 与 §VII 的「四条复测臂位移」（2026-09-26 自查；§V 那处早有守卫，见上文）----
    # 同一个量在正文里出现**三处**，而 1541-1575 行那条守卫的 `where` 只写了
    # `sec_results.tex` —— §I 的枚举与 §VII 的区间（4.5--11.2pp）**都没有守卫**。
    # 值从 `runs_precise.csv` 现算（与 §V 那条同口径：Δ = SLO − envelope.piecewise(wall, FRONT)），
    # **不另写插值**。
    # ⚠ 本文件不 import envelope（它用 importlib 动态加载 frontier）——
    # 这里按同样的方式加载，**不另写插值**（分段线性插值只许在 envelope.py 里）。
    import importlib.util as _iue
    _spe = _iue.spec_from_file_location("envelope", os.path.join(ROOT, "scripts", "lab", "envelope.py"))
    _ENV = _iue.module_from_spec(_spe)
    _spe.loader.exec_module(_ENV)
    _rp2 = {}
    for _l in open(os.path.join(ROOT, "paper/data/runs_precise.csv")):
        if _l.startswith("#"):
            continue
        _c = _l.strip().split(",")
        if len(_c) >= 3 and _c[1] != "wall_min":
            try:
                _rp2[_c[0]] = (float(_c[1]), float(_c[2]))
            except ValueError:
                pass
    _front2 = [(w, s) for w, s, _ in _FR.FRONT]
    _moved2, _miss2 = [], []
    for _a2, _b2 in (("pois200_foyer_hz2", "pois200_foyer_hz2_r2"),
                     ("pois200_foyer_hz0", "pois200_foyer_hz0_r2"),
                     ("pois200_foyer_bres", "pois200_foyer_bres_r2"),
                     ("pois200_foyer_breshz1", "pois200_foyer_breshz1_r2")):
        # ⚠ 缺哪一条**要报出来**，不许 `continue` —— 缺了就算不出位移，
        # 静默跳过等于这条守卫没跑（本项目栽过「生成器静默丢 run」）。
        if _a2 not in _rp2 or _b2 not in _rp2:
            _miss2.append("%s/%s" % (_a2.replace("pois200_", ""), _b2.replace("pois200_", "")))
            continue
        _w1, _s1 = _rp2[_a2]
        _w2, _s2 = _rp2[_b2]
        _moved2.append(_s2 - _ENV.piecewise(_w2, _front2) - (_s1 - _ENV.piecewise(_w1, _front2)))
    checks += 1
    if _miss2 or len(_moved2) != 4:
        fails.append(("§I/§VII 的四条复测臂位移算不出来（runs_precise.csv 缺受损 run）",
                      "缺：%s；只算出 %d 条" % ("；".join(_miss2) or "无", len(_moved2)),
                      "paper/data/runs_precise.csv"))
    else:
        _hi2, _lo2 = max(_moved2), min(_moved2)
        for _v2 in sorted(_moved2, reverse=True):
            ck_near("§I 复测臂的位移 %.2f" % _v2, "%.1f" % _v2, "sec_intro.tex",
                    "closer to the front", window=90)
        ck_near("§VII 位移区间的上界", "%.1f" % _hi2, "sec_discussion.tex",
                "have all been re-measured alone", window=200)
        ck_near("§VII 位移区间的下界", "%.1f" % _lo2, "sec_discussion.tex",
                "have all been re-measured alone", window=200)

    # ------------------------------------- §A100 此前无守卫的几个读数（独立复核 m3）
    if os.path.exists(os.path.join(ROOT, "paper/data/a100.csv")):
        _a1b = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/a100.csv"))}
        for _k, _kw in (("a100_cap8", "minutes"), ("a100_cap16", "minutes"),
                        ("a100_cap16", "sits at the same median")):
            if _k in _a1b:
                _col = "wall_min" if _kw == "minutes" else "occ_p50_pct"
                ck_near("§A100 %s 的 %s" % (_k, _col), _a1b[_k][_col],
                        "sec_xtrace.tex", _kw, window=120)
        # 控制器那一条的墙钟与 SLO（「88.3」在正文出现两次：一次自己、一次作对比）
        _ad2 = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/a100_delta.csv"))}
        if "a100_foyer_hz2" in _ad2:
            # ⚠ 2026-09-27 独立复核（本会话）：§I 原来写「the controller lands 0.1pp
            # **below** the static front」，而 `a100_delta.csv` 的 `delta_pp` 是
            # **+0.1000**（`gen_a100_delta.py` 算的是 `SLO − front`，正 = 上方）。
            # **方向反了，而且是「把结果说得更负」那一类。** §VI 同处写的是对的
            # （「the front interpolated there is 0.1pp below the controller's SLO」）。
            # 判据：从 `a100_delta.csv` 现读符号与绝对值，与正文那两个词逐条比。
            _adz = load(os.path.join(ROOT, "paper/data/a100_delta.csv"))
            _z = {r["run"]: r for r in _adz}.get("a100_foyer_hz2")
            if _z and _z.get("delta_pp"):
                _dz = abs(float(_z["delta_pp"]))
                _side = "above" if float(_z["delta_pp"]) > 0 else "below"
                ck_near("§I 的 A100 控制器在线的哪一侧", _side, "sec_intro.tex",
                        "the controller lands", window=220)
                ck_near("§I 的 A100 控制器离线的距离", "%.1f" % _dz, "sec_intro.tex",
                        "the controller lands", window=220)
            ck_near("§A100 控制器在 against 处的墙钟", _ad2["a100_foyer_hz2"]["wall_min"],
                    "sec_xtrace.tex", "against", window=60)
        ck_near("§A100 控制器完成步数", "999 of 999", "sec_xtrace.tex", "no failures")

    # ------------------------------- §II「cap1 是那一段里唯一没有 HiCache 的锚点」
    # 2026-09-26 加。这是一条**集合判定**（派生量），会随 FRONT 变化而变假。
    # ⚠ 判 HiCache 开没开**不能写 `bool(metadata[...])`**：关掉时那个字段的字面值是
    # 字符串 **"unset"**，`bool("unset")` 是 **True** —— 我自己第一遍就是这么读反的，
    # 差点去改一句**本来是对的**正文（本项目「认出一个缩写，回头确认它指什么」的同类）。
    def _hc_on(_run):
        for _p in (os.path.join(ROOT, "results", "night", "pois200_" + _run, "metadata.json"),
                   os.path.join(ROOT, "results", "night", _run, "metadata.json")):
            if os.path.exists(_p):
                _a = ((json.load(open(_p)).get("build") or {})
                      .get("TURNSTILE_HICACHE_ARGS") or "").strip()
                return _a not in ("", "unset")
        return None
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts", "lab"))
        import frontier as _FR2
        _right = [(w, n) for w, _s, n in _FR2.FRONT if w >= 295]
        _no = [n for _w, n in _right if _hc_on(n) is False]
        if any(_hc_on(n) is None for _w, n in _right):
            secondary.append(("§II 前沿右段的 HiCache 状态读不全（镜像缺 metadata）",
                              "、".join(n for _w, n in _right if _hc_on(n) is None), "results"))
        elif len(_no) == 1:
            # ⚠ 查**这个位置上写的是哪条臂**，不是「cap1 在不在这附近」——
            # 那句话里 `\texttt{cap1}` 出现两次（「to \texttt{cap1} at 527, and
            # \texttt{cap1} is the only anchor…」），把后一个改成 cap2 时
            # 只查值**不会报**（反向测试实测）。改成从短语里**取**那条臂的名字。
            _m2 = re.search(r"\\texttt\{([A-Za-z0-9_]+)\} is the only anchor there that runs",
                            P.get("sec_background.tex", ""))
            checks += 1
            if _m2 is None:
                fails.append(("§II 找不到「is the only anchor there that runs」这句",
                              "（改了措辞？）", "sec_background.tex"))
            elif _m2.group(1) != _no[0]:
                fails.append(("§II 那句点名的臂不是现算出来的那条",
                              "正文写 %s，现算 %s" % (_m2.group(1), _no[0]),
                              "sec_background.tex"))
            elif VERBOSE:
                print("  OK   §II 右段唯一无 HiCache 的锚点 = %s（正文逐字相符）" % _no[0])
        else:
            checks += 1
            fails.append(("§II「cap1 是右段唯一无 HiCache 的锚点」不再成立",
                          "无 HiCache 的锚点：%s" % (_no or "无"), "sec_background.tex"))
    except Exception as _e:
        checks += 1
        fails.append(("§II HiCache 锚点守卫没能跑起来", repr(_e)[:60], "scripts"))

    # ------------------------------------------- 编译日志里的【致命错误】（2026-09-26）
    # `Too many }'s` 这类错误 LaTeX 自己写着「generally harmless, so keep going」，
    # 于是它只出现在 main.log 里，PDF 照样出、页数照样对、Overfull 照样是 0 ——
    # 本项目已有的四条排版卫兵（0 Overfull / 页数下界 / 日志比源文件新 / 0 悬空引用）
    # **一条都看不见它**。2026-09-26 实测：`sec_results.tex` 里一个孤儿 `}` 就这么
    # 躺了不知道多久，直到有人为别的事去翻 main.log。
    # 判据是**行首的 `! `**（LaTeX 的致命错误前缀），不是「Errors:」那种 latexmk 口径。
    _lg = os.path.join(ROOT, "paper/main.log")
    if os.path.exists(_lg):
        _txt = open(_lg, encoding="utf-8", errors="replace").read()
        _fatal = re.findall(r"(?m)^! (.*)$", _txt)
        checks += 1
        if _fatal:
            fails.append(("编译日志里有致命错误（LaTeX 会「generally harmless」地放过去）",
                          " / ".join(x[:60] for x in _fatal[:3]), "paper/main.log"))
    else:
        fails.append(("缺 paper/main.log（这条守卫没跑起来）", "", "paper"))

    # ⚠ 2026-09-26：A100 那一节已并入 sec_xtrace.tex（`sec_a100.tex` 现在是空壳），
    # 所以原先指向 sec_a100.tex 的 32 条检查全部改指 sec_xtrace.tex。
    # 这是「文件指针过期」，不是「数字没了」——重定基线时必须区分这两类：
    # 前者改指针，后者要么把数加回正文、要么退役该条检查。

# ------------------------------------------- 时间片切换（2026-09-26，承重假设的直接检验）
    # 全篇的判决基线是「静态点的分段线性插值」，理由是「时间片混合可逼近线段上任一点」——
    # 这句话在第 38 轮之前**从来没被测量过**。`pois200_slice23_hc` 是那次测量：
    # cap 每 60 秒在 3 与 2 之间切，落在弦**下方** 0.89pp（跑前写在 lane 头部的预期方向）。
    # 数据由 gen_slice23.py 生成，插值与判词共用 envelope.piecewise / frontier.classify。
    _sl = os.path.join(ROOT, "paper/data/slice23.csv")
    if os.path.exists(_sl):
        _sv = {r["field"]: r["value"] for r in load(_sl)}
        _dabs = "%.2f" % abs(float(_sv["delta_pp"]))
        ck_near("§II 时间片 run 的 Δ（绝对值）", _dabs, "sec_background.tex",
                "alternates the cap between three and two", window=400)
        # 关键词不能写 "below the line" —— 正文是 `\emph{below} the line`，
        # 字面那个短语不存在（本项目最常踩的假 MISS）。
        # ⚠ 2026-09-27：§VII 那句与 §II **逐字重复**，已压成指针（完整陈述留在 §II）。
        # 锚跟着换成新句里独有的短语 —— **锚失配 = 这条检查静默不再检查任何东西**。
        ck_near("§VII 时间片 run 的 Δ", _dabs, "sec_discussion.tex",
                "since run that policy once", window=200)
        ck_near("§II 时间片 run 落在下方", "below", "sec_background.tex",
                "alternates the cap between three and two", window=400)
        ck_near("§VII「一个点不是整段」的限定", "one point", "sec_discussion.tex",
                "since run that policy once", window=300)

    # ------------------------------------------- §V 的「idle 28 分钟」有出处了（2026-09-26）
    # 原来这个 28 只在日志里，任何数据文件都追不到（独立复核子 agent 第 39 轮指出）。
    # 补了 `aimd_stall.csv` 的 `idle_in_gap_min` 列（第 1 次 = 28.0）之后，
    # 正文那句必须与它对上；四舍五入到分钟写进正文。
    _as = os.path.join(ROOT, "paper/data/aimd_stall.csv")
    if os.path.exists(_as):
        _rs = load(_as)
        _r1 = [r for r in _rs if str(r.get("attempt")) == "1"]
        if _r1 and _r1[0].get("idle_in_gap_min"):
            ck_near("§V 停摆里引擎空闲的分钟", "%.0f" % float(_r1[0]["idle_in_gap_min"]),
                    "sec_results.tex", "sat idle for", window=60)

    # ------------------------------------------- §VI 控制器副本的存世与差异（2026-09-26）
    # 正文原来写着「只剩仓库那份留在机器上、四份副本已不在、那次比较无法重建」，
    # 而实测**两份都在**（仓库版 a21bd2b63774 在 scripts/，跑过 37 条 run 的工作副本
    # f825bc768188 在 TraceLab/replay/scripts/），diff 只有 22 行、两处 ——
    # 是**反方向**的错（把能核查的说成不能核查），而反方向的夸大没有任何东西在防。
    # 这里守三件事：存世数、可复查性、diff 的行数与处数；并**禁止**旧说法复活。
    # ⚠ 2026-09-26 篇幅手术：这一段压掉了「三份副本已不在」与「那次比较可以重建」的
    # 长句，保留的主张换成同样的意思、更短的措辞。守卫跟着**正文的实际措辞**走，
    # 不跟着旧措辞 —— 但**否定的那三条不动**（禁止旧说法复活才是它们的职责）。
    ck("§VI 四份哈希无一与仓库版相同", "none of them the repository copy",
       "sec_discussion.tex")
    ck("§VI 存世那一对可重新 diff", "re-derived rather than taken on trust",
       "sec_discussion.tex")
    ck("§VI 存世那一对的 diff 行数与处数", "22 lines, in two places",
       "sec_discussion.tex")
    ck("§VI sf=0 那次测的是修复+更松的放行率", "not the fix as written",
       "sec_discussion.tex")
    for _bad in ["the clean re-run we queued", "re-run is queued", "is still queued",
                 "only the repository revision survives",
                 "cannot be diffed after the fact",
                 "the reading cannot be\nre-checked"]:
        checks += 1
        if _bad in P["sec_discussion.tex"]:
            fails.append(("§VI 又出现「副本已不在、无法核查」的旧说法", _bad,
                          "sec_discussion.tex"))

    # ------------------------------------------- §VI 撤回条数（2026-09-26）
    # 这个数**写在全篇两处**（§I 的贡献清单与 §VI 的清单引言），而它没有任何东西在守：
    # 往清单里加一条而不改这两个数，两处都会变成假话（2026-09-26 加第七条时就是这么发现的）。
    _dd = P["sec_discussion.tex"]
    # ⚠ 2026-09-26：原来是 `_dd.find("In order of how much they cost us")` ——
    # 而压缩之后那句被硬换行切成「In order of how\nmuch they cost us:」，
    # `find` 是字面匹配，于是**边界找不到**，整条守卫（含七条计数）静默不执行。
    # 这是本项目记过最多次的坑（关键词跨换行 = 假 MISS），这次是**我自己的守卫**踩的。
    # 改用 `\s+` 容忍换行。
    # ⚠ 2026-09-27：篇幅手术把「In order of how much they cost us:」的**列表体**
    # 压成了一句话叙述（`Seven claims were retracted during this work: a; b; ...; and g.`），
    # 于是按 `\n\n\\emph{` 数条目的老判据再也找不到边界 —— 边界守卫报 MISS。
    # 判据要跟着**新的**文本走：条目之间用 `; ` 分隔、最后一条用 `, and`。
    _mm = re.search(r"claims\s+were\s+retracted\s+during\s+this\s+work", _dd)
    _i = _mm.start() if _mm else -1
    _j = _dd.find("Each is reported with its evidence", _i)
    if _i < 0 or _j < 0:
        fails.append(("§VI 撤回清单的边界找不到（这条守卫没跑起来）", "", "sec_discussion.tex"))
    else:
        # ⚠ 数的是**段首**的 \emph{（每条撤回项都以它开头），不是 \emph{ 的总数 ——
        # 条目正文里也可能用 \emph（本次新加的那条里就有一个 ``\emph{untriggered}''），
        # 第一版按总数数出来是 8 而不是 7。
        _nr = _dd[_i:_j].count(";") + 1
        # ⚠ 必须 `ck_near`：`ck` 是全局查，而 §VI 别处就有裸的 "eight"
        # （"53.1\% at eight"）—— 清单加一条、正文数不改，`ck` 照样通过。
        # 反向测试实测过：这条一开始写成 `ck` 就是**没报**。
        ck_near("§VI 撤回条数（清单里 \\emph{} 的条数）",
                num_words(_nr) + [str(_nr)], "sec_discussion.tex",
                "claims were retracted during this work", 40)
        ck_near("§I 撤回条数（与 §VI 清单同数）", num_words(_nr) + [str(_nr)],
                "sec_intro.tex", "claims we had to retract", 40)

    # ------------------------------------------- §V 不放行窗口的计数（2026-09-26 重写）
    # 旧版守的是「4 of the 11 / present in four of / a single such window each」三处。
    # 判据极性修正后正文整段重写，那三处的措辞不存在了；现在守的是新句。
    # ⚠ 数词**不许单独查**：`one` / `eleven` 在稿子里到处都是，`ck("one")` 必中。
    # 一律查「数词 + 那句话独有的词」拼起来的复合串。
    _stl = load(os.path.join(ROOT, "paper/data/stall.csv"))
    if _stl:
        _hit = [r for r in _stl if int(r["n_windows"]) > 0]
        _w1 = num_words(len(_hit))
        _w1 = _w1[0] if isinstance(_w1, list) and _w1 else str(len(_hit))
        # ⚠ 2026-09-27 活性审计：这一条的「期望值」原来是**正文自己的字串**
        # （`"the eleven runs of ours"`）—— stall.csv 长大到 12 行它也不会响。
        # 改成从**文件行数**现算（`_stl` 就是 stall.csv 的内容）。
        _n11 = num_words(len(_stl))
        _n11 = _n11[0] if isinstance(_n11, list) and _n11 else str(len(_stl))
        ck("§V stall.csv 里一共几条臂", "the %s runs of ours" % _n11, "sec_results.tex")
        ck("§V 正判据下有窗口的臂数（复合串）",
           "%s of the %s runs of ours" % (_w1, _n11), "sec_results.tex")
        # ⚠ 2026-09-27：`eleven` 原来是**写死**的 —— `foyer_scan`/`hz2_r3` 进表后
        # stall.csv 变成 13 行，正文改成 thirteen，而这条守卫还在找 eleven ⇒ 假 MISS。
        # 与上面那条同一条规矩：分母也要从文件现算。
        ck("§V 正判据下的签名臂数（复合串）",
           "has a window in which it admits nobody", "sec_results.tex")
        # 「只看队首」的日志指纹：严格按到达顺序放行的臂数 + 另两条的乱序率
        _zero = [k for k, r in _st.items() if int(r.get("fifo_out_of_order") or 0) == 0]
        _nz = sorted(float(r["fifo_pct"]) for r in _st.values()
                     if int(r.get("fifo_out_of_order") or 0) > 0)
        # ⚠ 大小写都要传：`has()` 的 IGNORECASE 只做在「数字↔英文词」两条通路上，
        # **多词字面串**仍走 `v in text`，是区分大小写的（正文这句在句首，是大写 N）。
        _wn = _NUM9.get(len(_zero), str(len(_zero)))
        ck_near("§V 严格按到达顺序放行的臂数",
                ["%s of the eleven arms" % _wn, ("%s of the eleven arms" % _wn).capitalize()],
                "sec_results.tex", "admission order", 300)
        # 每臂的放行次数（这一组里全是 200，取众数；正文写 "all 200 of its sessions"）
        _ad = sorted({int(r["admits"]) for r in _st.values() if r.get("admits")})
        if len(_ad) == 1:
            ck_near("§V 每臂的放行次数", "all %d of its sessions" % _ad[0],
                    "sec_results.tex", "admitted", 40)
        # ⚠ 2026-09-27 加：§V 用「它每周期只放行一个、从没放过两个」把
        # `scans the queue` 与 `single-flight off` 区分开 —— **承重句**，
        # 而且它此前只活在正文里。判据跨两个文件：周期数与放行次数在
        # `gate_attrib.csv`（samples / total_admits），「最多一个」在 `stall.csv`
        # 的新列 `max_per_cycle`（那个列就是为这句话加的）。
        _ga = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/gate_attrib.csv"))}
        _sc = _ga.get("pois200_foyer_scan")
        if _sc:
            ck_near("§V scan 的控制周期数", _sc["samples"], "sec_results.tex",
                    "control cycles", window=60)
            ck_near("§V scan 的放行次数", _sc["total_admits"], "sec_results.tex",
                    "control cycles", window=120)
        _mpc = {r["run"]: r.get("max_per_cycle") for r in _stl}
        checks += 1
        if _mpc.get("foyer_scan") not in ("1", 1):
            fails.append(("§V 说 scan「每周期只放行一个」，而 stall.csv 的 max_per_cycle 不是 1",
                          "max_per_cycle=%s" % _mpc.get("foyer_scan"), "paper/data/stall.csv"))
        checks += 1
        if _mpc.get("foyer_sf0_r2") not in ("2", 2):
            fails.append(("§V 说 single-flight off「一次能放多个」，而 max_per_cycle 不是 2",
                          "max_per_cycle=%s" % _mpc.get("foyer_sf0_r2"), "paper/data/stall.csv"))
        if len(_nz) >= 2:
            ck_near("§V 两个考虑整队列的臂的乱序率",
                    "%d\\%% and %d\\%%" % (_nz[0], _nz[-1]),
                    "sec_results.tex", "the whole queue admit out of order", 120)

    # ------------------------------------------- AIMD 那次停摆的读数（2026-09-26）
    # 正文（§V 的 AIMD 段 + 表 I 表注）说重跑「控制器中途退出、再没回来、
    # 两个会话一直排队、停在 989/999」。这四个事实现在有数据文件了。
    _as_p = os.path.join(ROOT, "paper/data/aimd_stall.csv")
    if not os.path.exists(_as_p):
        fails.append(("缺 aimd_stall.csv（§V 停摆那段的读数没有出处）",
                      "aimd_stall.csv", "paper/data"))
    else:
        _as = {r["run"]: r for r in load(_as_p)}
        _r2 = _as.get("pois200_aimd2_paper_r2")
        if not _r2:
            fails.append(("aimd_stall.csv 少了重跑那一次", "pois200_aimd2_paper_r2", "paper/data"))
        else:
            ck_near("§V 重跑停在第几步",
                    "%s of %s" % (_r2["steps"], 999), "sec_results.tex",
                    "stopped at", window=40)
            ck_near("§V 第一次尝试停摆时的排队数",
                    num_words(int(_as["pois200_aimd2_paper"]["queued_at_log_gap"]))
                    + [int(_as["pois200_aimd2_paper"]["queued_at_log_gap"])],
                    "sec_results.tex", "froze with", window=40)
            # 正文的「32 minutes」= **两次发许可之间**的最长间隔（31.9 -> 32），
            # 不是控制日志的中断（31.4）—— 两个都印在表里，别混用。
            ck_near("§V 停摆时长（发许可到发许可）",
                    "%.0f" % float(_as["pois200_aimd2_paper"]["admit_gap_min"]),
                    "sec_results.tex", "issuing permits for", window=60)
            ck_near("§V 重跑排队未准入的会话数",
                    num_words(int(_r2["queued_never_admitted"])) + [int(_r2["queued_never_admitted"])],
                    "sec_results.tex", "stayed queued", window=60)
            if "losing its controller for" in P.get("sec_results.tex", ""):
                fails.append(("§V 又写回了「停摆 N 分钟」（那个值取决于何时手动停掉）",
                              "losing its controller for", "sec_results.tex"))

    # ------------------------------- 等值断言（「identical」这一族，2026-09-26）
    # 等值断言是最脆的一类：数据一变它就假，而**没有任何数值守卫会响**
    # （它没有"值"可查）。§A100 有两处，都是它跨配置有效性的前提。
    def _meta(_n):
        for _p in (os.path.join(ROOT, "results", "night", _n, "metadata.json"),
                   os.path.join(ROOT, "results", "night", "pois200_" + _n, "metadata.json")):
            if os.path.exists(_p):
                return json.load(open(_p))
        return None
    _m1, _m2 = _meta("a100_cap5"), _meta("a100_foyer_hz2")
    if _m1 and _m2:
        _b1, _b2 = (_m1.get("build") or {}), (_m2.get("build") or {})
        _same = (_m1.get("pool_tokens") == _m2.get("pool_tokens")
                 and _m1.get("gpu") == _m2.get("gpu")
                 and (_b1.get("TURNSTILE_HICACHE_ARGS") or "") == (_b2.get("TURNSTILE_HICACHE_ARGS") or "")
                 and (_m1.get("code") or {}) == (_m2.get("code") or {}))
        checks += 1
        if not _same:
            fails.append(("§A100「控制器那条 run 的配置与静态扫描相同」不再成立",
                          "pool/gpu/hicache/code 有差异", "sec_xtrace.tex"))
        elif VERBOSE:
            print("  OK   §A100 控制器那条与静态扫描的配置逐项相同（pool/gpu/hicache/code）")
        # ⚠ 上面那四项**不覆盖模型**：codex 第 37 轮指出，改掉 `runner_argv` 里的
        # `--model` 仍会通过。模型与分词器是「配置相同」这句话的核心，补上。
        def _flag(_m, _name):
            _a = _m.get("runner_argv") or []
            return _a[_a.index(_name) + 1] if _name in _a else None
        _mdl = [(_flag(_m1, "--model"), _flag(_m1, "--tokenizer")),
                (_flag(_m2, "--model"), _flag(_m2, "--tokenizer"))]
        checks += 1
        if _mdl[0] != _mdl[1] or _mdl[0][0] is None:
            fails.append(("§A100 控制器那条与静态扫描的模型/分词器不同（或读不到）",
                          "%s" % (_mdl,), "results"))
        elif VERBOSE:
            print("  OK   §A100 两条的 --model / --tokenizer 也相同（%s）" % _mdl[0][0])
    else:
        checks += 1
        secondary.append(("§A100 配置等值断言读不到 metadata（镜像不全）", "a100_cap5/a100_foyer_hz2", "results"))
    # 「两条机器上的 trace 校验和相同」：同一文件名的 md5 必须只有一个值。
    _tm = {}
    for _p in glob.glob(os.path.join(ROOT, "results", "night", "*", "metadata.json")):
        try:
            _m = json.load(open(_p))
        except Exception:
            continue
        _t = os.path.basename(_m.get("trace") or "")
        if _t:
            _tm.setdefault(_t, set()).add(_m.get("trace_md5"))
    _bad_t = {k: v for k, v in _tm.items() if len(v) > 1}
    checks += 1
    if _bad_t:
        fails.append(("同名 trace 在不同 run 上校验和不同（「同一条 trace」不成立）",
                      "、".join(sorted(_bad_t))[:60], "results"))
    elif VERBOSE:
        print("  OK   %d 条 trace 的文件名校验和各自唯一（含两台机器）" % len(_tm))

    # ------------------------------- §I 里那两个空转量（2026-09-26 抓到是旧的）
    # 正文 §I 原来写「mean 20.9\,s」「70.2\% of all idle time」——
    # 而 `idle_pooled.csv` 的四个 pooling 给的是 mean 18.94--20.55、pct 66.1--69.5。
    # **20.9 与 70.2 在现在的数据里根本不存在**：它们是并入前那一池
    # （16 条 run、2032 段）的值 —— 第 34 轮已经在**图 4 的图注**里改过一次
    # （70.2% / 21.0 s → 69.5% / 20.6 s），**而 §I 里同样的两个数没人管**。
    # 这正是「降级一个说法时要把它所有的同义说法找出来」那一条。
    _ip = load(os.path.join(ROOT, "paper/data/idle_pooled.csv"))
    if _ip:
        _mu = sorted(float(r["mean_s"]) for r in _ip)
        _pc = sorted(float(r["pct_idle_time_in_gt20s"]) for r in _ip)
        ck_near("§I 空转均值区间", "%.1f to %.1f" % (_mu[0], _mu[-1]),
                "sec_intro.tex", "in the tail---mean", window=60)
        ck_near("§I >20s 占空转时间的区间", "%.1f to %.1f" % (_pc[0], _pc[-1]),
                "sec_intro.tex", "sits in stretches over", window=70)
        if "70.2" in P.get("sec_intro.tex", ""):
            fails.append(("§I 又出现旧值 70.2（并入前那一池的占比）", "70.2", "sec_intro.tex"))

    # ------------------------------- §I 的「>10 s 占比」（2026-09-26 抓到分母混用）
    # 正文原来写「mean 15.8--16.9 s with **22%** of gaps over ten seconds」——
    # 22 是**只拿 662 个正值当分母**算的（21.8%），而同句的另外两个统计量
    # （中位 0.34、均值 15.8--16.9）拿的是 **799 个转换**当分母。**同一句两套分母。**
    # 按转换算只有 **18.0%**。已统一到 799，并把两个分母都落进 toolwait.csv。
    _tw_p = os.path.join(ROOT, "paper/data/toolwait.csv")
    if os.path.exists(_tw_p):
        _tw = {r["run"]: r for r in load(_tw_p)}
        _h = _tw.get("pois200_foyer_hc")
        if _h and _h.get("demand_gt10_pct_of_transitions"):
            ck_near("§I 轮次转换的 >10s 占比（按转换算）",
                    "%.0f" % float(_h["demand_gt10_pct_of_transitions"]),
                    "sec_intro.tex", "of those transitions wait more than", window=60)
            # ⚠ 正文印的是 **1 位小数**（15.8--16.9），CSV 存的是 2 位（15.82/16.85）——
            # 拿 2 位的串去查会**假 MISS**（本项目已经栽过「拿舍入后的列再舍入一次」的镜像版）。
            ck_near("§I 轮次转换的均值区间",
                    "%.1f--%.1f" % (float(_h["demand_mean_s"]),
                                    float(_h["measured_mean_s"])),
                    "sec_intro.tex", "the demanded median inter-round gap", window=140)
            if "of gaps over ten seconds" in P.get("sec_intro.tex", ""):
                fails.append(("§I 又写回了「of gaps over ten seconds」（分母混用）",
                              "of gaps over ten seconds", "sec_intro.tex"))
        else:
            checks += 1
            secondary.append(("toolwait.csv 还没有 >10s 的分母列（跑一次 gen_toolwait.py）",
                              "demand_gt10_pct_of_transitions", "paper/data"))

    # ------------------------------- 跑闸门（running gate）扫了几个值（2026-09-26）
    # §V 里两处说法**互相矛盾**：Route 4 那节写「swept the gate over {2,4}」，
    # 而二十行之前写「rg4, the loosest of the **three**」，并给了 rg2/rg3 的读数。
    # 镜像里 `pois200_foyer_rg2/rg3/rg4` **三个都在**（770 / 169 / 998 步）。
    # 检查器一处没报 —— 它只查数值，不查「同一件事在两处的说法是否一致」。
    _rgs = sorted(d for d in os.listdir(os.path.join(ROOT, "results", "night"))
                  if d.startswith("pois200_foyer_rg"))
    if _rgs:
        _gates = ",".join(d.replace("pois200_foyer_rg", "") for d in _rgs)
        # ⚠ LaTeX 里写的是 `$\{2,3,4\}$` —— **字面 `{2,3,4}` 并不存在**
        # （`4` 后面跟的是反斜杠再右括号）。所以传的串必须把两个反斜杠也带上，
        # 否则 `has()` 会**假 MISS**（实测：传 `{2,3,4}` → False，传 `\{2,3,4\}` → True）。
        ck_near("§V Route 4 扫的闸门档位", "\\{%s\\}" % _gates, "sec_results.tex",
                "swept it over", window=40)
        ck_near("§V 闸门臂的条数", num_words(len(_rgs)) + [len(_rgs)], "sec_results.tex",
                "the loosest of the", window=40)
        if "the gate over $\\{2,4\\}$" in P.get("sec_results.tex", ""):
            fails.append(("§V 又写回了「swept the gate over {2,4}」（实际是三个档位）",
                          "{2,4}", "sec_results.tex"))

    # ------------------------------- §VII（第二条 trace）此前无守卫的几项（2026-09-26）
    # §VII 是全文最新、复核最少的一节。逐项复算之后补上守卫。
    # ⚠ 中位数取的是**上中位**（→ 偶数个样本时是中间两个里大的那个）——
    # `sec_results.tex` 里写着「Medians here are the upper of the two middle values」。
    # 第二条 trace 是 390 行（偶数）：`statistics.median` 给 18791，**上中位是 18809**，
    # 而正文写的正是 18809。**换约定就会假 MISS**，所以这里显式取上中位。
    def _upmed(_v):
        _v = sorted(_v)
        return _v[len(_v) // 2]
    _tr2 = os.path.join(ROOT, "data", "replay_realhr.csv")
    _tr1 = os.path.join(ROOT, "data", "replay_pois200_l04.csv")
    if os.path.exists(_tr2) and os.path.exists(_tr1):
        # ⚠ **只有第二条 trace 的会话数/轮数**在那句话里；主 trace 的 200/999 不在这一处
        # （第一版没区分，两条都查 → 两条**假 MISS**）。
        _r2 = list(csv.DictReader(open(_tr2)))
        _ns = len({r["session_id"] for r in _r2})
        # ⚠ 查**整句**，不查两个孤立的数 —— codex 第 37 轮实测：把
        # 「117 sessions, 390 rounds」对调成「390 sessions, 117 rounds」，
        # 两条只查单个数的守卫**都不报**（同一类：两个数各查各的，换位仍通过）。
        ck_near("§VII 第二条 trace 的会话数与轮数（整句）",
                "%d real Claude agent sessions, %d rounds" % (_ns, len(_r2)),
                "sec_xtrace.tex", "controller on a second replay", window=120)
        _p2 = [int(r["prefix_len"]) + int(r["input_len"])
               for r in csv.DictReader(open(_tr2))]
        _p1 = [int(r["prefix_len"]) + int(r["input_len"])
               for r in csv.DictReader(open(_tr1))]
        # ⚠ 同样查整句：正文写「median prompt 18{,}809 tokens against 23{,}187」，
        # 两个数**对调**时只查单值的守卫不会响（codex 第 37 轮实测）。
        # ⚠ 正文用的是 LaTeX 千分位写法 `18{,}809` —— 拼串时要照抄
        # （第一版拼成 `18809` → 假 MISS）。
        _kb = lambda x: "{:,}".format(int(x)).replace(",", "{,}")
        ck_near("§VII 两条 trace 的 prompt 上中位（整句）",
                "median prompt %s tokens against %s" % (_kb(_upmed(_p2)), _kb(_upmed(_p1))),
                "sec_xtrace.tex", "sessions are smaller", window=80)

    # ------------------------------- §II 的 prompt 尺寸（2026-09-26 补守卫）
    # 这三条此前没有守卫，而 §II 是「问题设定」那一节，读者会当它是最稳的。
    # 中位数同样取**上中位**（999 行是奇数，两种约定同值；但第二条 trace 不是）。
    _tr = os.path.join(ROOT, "data", "replay_pois200_l04.csv")
    if os.path.exists(_tr):
        _pr = sorted(int(r["prefix_len"]) + int(r["input_len"])
                     for r in csv.DictReader(open(_tr)))
        _n = len(_pr)
        ck_near("§II prompt 的上中位", int(_pr[_n // 2]), "sec_background.tex",
                "a round presents a prompt of median", window=60)
        ck_near("§II prompt 的 p90", int(_pr[int(0.9 * _n)]), "sec_background.tex",
                "a round presents a prompt of median", window=90)
        ck_near("§II prompt 的最大值", int(_pr[-1]), "sec_background.tex",
                "a round presents a prompt of median", window=120)
        ck_near("§II 最大值占池子的比例", "%.0f" % (100.0 * _pr[-1] / 101432),
                "sec_background.tex", "which alone is", window=40)
        ck_near("§II 最大两条合计超池子的比例",
                "%.0f" % (100.0 * (_pr[-1] + _pr[-2] - 101432) / 101432),
                "sec_background.tex", "exceed the pool by", window=40)
        # ⚠ **不查「合计」**：正文只给两条各自的数（89{,}436 与 87{,}821），
        # 不给 177{,}257。第一版查了合计 → 假 MISS。查「超出 75%」就够了。
        ck_near("§II 第二大的那条", int(_pr[-2]), "sec_background.tex",
                "combined contexts", window=70)

    # ------------------------------- §I 的「四条被重测的臂移动了多少」（2026-09-26 补）
    # ⚠ **resident base 是 `foyer_bres_r2`，不是 `foyer_hc`**（后者的 label 是
    # "horizon$=$3 (base)"）—— 我自己第一遍就挑错了臂，差 0.09pp 且看不出问题。
    # 这与本项目「自造缩写没有一个是自明的」是同一族。
    _t1m = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/table1.csv"))}
    _MOVED = [("foyer_breshz1", "foyer_breshz1_r2", -19.54),
              ("foyer_bres", "foyer_bres_r2", -7.81),
              ("foyer_hz0", "foyer_hz0_r2", -13.60),
              ("foyer_hz2", "foyer_hz2_r2", -4.81)]
    if all(n in _t1m for _o, n, _v in _MOVED):
        _mv2 = [float(_t1m[n]["delta_pp"]) - _o_old for _o, n, _o_old in _MOVED]
        # ⚠ 正文是「11.2, 6.5, 6.4 **and** 4.5」——最后一项前是 and 不是逗号，
        # 拼串时要照抄（第一版拼成逗号 → 假 MISS）。
        ck_near("§I 四条重测臂的移动量",
                "%.1f, %.1f, %.1f and %.1f" % tuple(_mv2), "sec_intro.tex",
                "moved", window=90)

    # ------------------------------- §V Route 3（预算扫描）的两条臂（2026-09-26 补）
    # 这两个数是 §V 用来论证「预算分数这个旋钮不听话」的，此前**完全没有守卫**
    # （一次「正文里有信息量的数 vs 检查器核过的值」对拍扫出来的）。
    _bs_p = os.path.join(ROOT, "paper/data/budget_sweep.csv")
    if os.path.exists(_bs_p):
        _bs = sorted(load(_bs_p), key=lambda r: float(r["wall_min"]))
        if len(_bs) >= 2:
            _lo, _hi = _bs[0], _bs[1]
            ck_near("§V 预算扫描的墙钟（低）", _lo["wall_min"], "sec_results.tex",
                    "finish at", window=60)
            ck_near("§V 预算扫描的 SLO（低）", _lo["slo_pct"], "sec_results.tex",
                    "finish at", window=120)
            ck_near("§V 预算扫描的 Δ（低）", "%.2f" % float(_lo["delta_pp"]),
                    "sec_results.tex", "from the envelope at", window=140)
            ck_near("§V 预算扫描的 Δ（高）", "%.2f" % float(_hi["delta_pp"]),
                    "sec_results.tex", "from the envelope at", window=140)

    # ------------------------------- 「污染 vs 干净」的膨胀区间（2026-09-26 补）
    # 正文写「an inflation of 24 to 41\% across arms, which compares the **extremes
    # of two ranges**」。按它自己的算法（污染臂 τ₂ 的区间 vs 干净 13 条的区间端点互比）
    # 是 **12--41\%**；那个 24 是**旧的七条臂干净上界 25.0** 算出来的
    # （30.88/25.0−1 = 23.5 ≈ 24）。独立复核子 agent 第 21 轮抓到 ——
    # **同一段里「十三 / 23.7--27.5」是新算的，紧接着这句的下界还锚在旧区间上。**
    _dmg = [30.8833, 31.2908, 33.1137, 33.3075]
    _lo1, _hi1 = 23.6590, 27.5412
    ck_near("§VI 膨胀区间的下界（端点互比）", "%.0f" % (100 * (min(_dmg) / _hi1 - 1)),
            "sec_discussion.tex", "across arms", window=90)
    ck_near("§VI 膨胀区间的上界（端点互比）", "%.0f" % (100 * (max(_dmg) / _lo1 - 1)),
            "sec_discussion.tex", "across arms", window=90)
    ck_near("§III 膨胀区间的下界（同一对数）", "%.0f" % (100 * (min(_dmg) / _hi1 - 1)),
            "sec_model.tex", "inflates per-step cost by", window=60)
    ck_near("§III 膨胀区间的上界（同一对数）", "%.0f" % (100 * (max(_dmg) / _lo1 - 1)),
            "sec_model.tex", "inflates per-step cost by", window=60)

    # ------------------------------- §IV 的「加 10% 并发买到多少」（2026-09-26 补）
    # 正文写「adding 10\% concurrency buys 3.8\% to 6.1\% of busy-time throughput」——
    # 那是 1.1^(1−ε) 在两个拟合值上的取值，此前**没有守卫**（ε 本身有）。
    # ⚠ 用的是**全局拟合**的 ε（`_EPS_MODEL` / `_EPS_REQ`），**不是** `elasticity.csv`
    # 里的**分段**弹性 —— 第一版读错了表，算出 5.6 / 12.2（假 MISS）。
    _vals = sorted(100 * (1.1 ** (1 - e) - 1) for e in (_EPS_MODEL, _EPS_REQ))
    ck_near("§IV 「加 10% 并发」的下界", "%.1f" % _vals[0], "sec_criterion.tex",
            "buys", window=60)
    ck_near("§IV 「加 10% 并发」的上界", "%.1f" % _vals[-1], "sec_criterion.tex",
            "buys", window=60)
    # §IV 引的两段 R̄ 区间：host-tier 的那两段与九条控制器臂的区间
    _ar = {r["run"]: r for r in load(os.path.join(ROOT, "paper/data/arm_running.csv"))}
    sys.path.insert(0, os.path.join(ROOT, "scripts", "lab"))
    try:
        import gen_arm_running as _AR2
        _nine = sorted(float(_ar[k]["running_busy"]) for k in _AR2.NINE if k in _ar)
        if _nine:
            ck_near("§IV 控制器臂 R̄busy 区间",
                    "%.2f to %.2f" % (_nine[0], _nine[-1]), "sec_criterion.tex",
                    # ⚠ 关键词 27 字符 + 值 13 字符 = 40，window=40 **刚好切掉最后一个字符**
                    # → 假 MISS。窗口必须 ≥ 关键词长度 + 值长度。
                    "controller operating region", window=70)
    except Exception as _e:
        checks += 1
        fails.append(("§IV R̄ 区间守卫没跑起来", repr(_e)[:50], "scripts"))
    _hc2 = [("pairB_cap2hc", "cap4_hc")]
    if all(k in _ar for k in _hc2[0]):
        _rr = sorted(float(_ar[k]["running_busy"]) for k in _hc2[0])
        ck_near("§IV host-tier 两段的 R̄ 区间", "%.2f to %.2f" % (_rr[0], _rr[-1]),
                "sec_criterion.tex", "the range", window=60)

    # ------------------------------- §VI 阈值敏感性表：**必须含头条那条臂**（2026-09-26）
    # 独立复核第 22 轮抓到：生成器的落盘名单硬编码 8 条、**漏了 `foyer_hz2_r2`** ——
    # 10s 下最近（−0.30）、20s 下 **+1.02 越过**的那条。漏的方向对论文有利，
    # 所以正文原来写「one measurement of one of them does」，实际是两条。
    _ss_p = os.path.join(ROOT, "paper/data/slo_sensitivity.csv")
    if os.path.exists(_ss_p):
        _ss = {}
        for _r in load(_ss_p):
            # ⚠ 表里除了臂还有**阈值汇总行**（`run` = "5.0"/"10.0"/"20.0"/"threshold_s"，
            # 第三列是锚点墙钟 200+）—— 不排掉的话它们会被当成「20s 下越过的臂」
            # （第一版算成 5 条，实际 2 条）。
            _nm = _r.get("run") or ""
            if not _nm or _nm[0].isdigit() or _nm == "threshold_s":
                continue
            try:
                _ss[_nm] = tuple(float(_r["slo%d_pp" % t]) for t in (5, 10, 20))
            except (KeyError, TypeError, ValueError):
                continue
        for _k in ("hz2_r2", "hz1", "hz1_r2"):
            checks += 1
            if _k not in _ss:
                fails.append(("§VI 阈值敏感性的表里少了这条臂（头条依赖它）", _k, "slo_sensitivity.csv"))
            elif VERBOSE:
                print("  OK   §VI 阈值敏感性含 %-8s 5s=%+.1f 10s=%+.1f 20s=%+.1f"
                      % ((_k,) + _ss[_k]))
        # 20s 下**越出 ±1.0pp 带**的臂数（`classify` 的判据：> +1.0 才算越过）
        _cross = [k for k, v in _ss.items() if v[2] > 1.0]
        # ⚠ 2026-09-26（codex r42）：锚原来写的是 `of them do, each on a single`，
        # 而压缩把句子改成「at a loose one, two do, each on a single measurement」
        # —— 锚匹配不上 ⇒ 这条检查**静默走退役分支**（而 RETIRED 里也有一条同名条目，
        # 于是它看起来「已退役」），**主张却还在正文**。锚改成不含数词的短语。
        # ⚠ 2026-09-27：锚从 `do, each on a single measurement` 改成
        # `cross, each on a single measurement` —— 那句话改写了（two→three），
        # `do` 没了。**锚失配 = 这条检查静默不再检查任何东西**，所以必须跟着改。
        ck_near("§VI 20s 下越过的臂数", num_words(len(_cross)) + [len(_cross)],
                "sec_discussion.tex", "at the loose end", window=120)
        # ⚠ 2026-09-27 通读抓到：**表【前】**那句原来写「at the loose end **one** of them
        # appears ... to cross」，而表【后】**同一件事**那句写「**two** do」——
        # 两句互相矛盾（`CLAUDE.md` 记过这一族）。真值是**两条**（20s 下 > +1.0 的臂）。
        # 已改成与表后那句一致，并把 `horizon=2` 的 **+1.01**（表里印成 +1.0，
        # 恰在 `> +1.0` 判据边缘）写明。这条守卫钉住表【前】那句。
        _h2 = _ss.get("hz2_r2")
        checks += 1
        if not _h2:
            fails.append(("slo_sensitivity.csv 少了 hz2_r2（表前那句的守卫没法跑）", "hz2_r2",
                          "paper/data/slo_sensitivity.csv"))
        else:
            # ⚠ 2026-09-27：`two of them cross` 也是**写死**的。`foyer_scan` 落地后
            # 20s 下越过的臂从两条变三条，正文改了而守卫没改 ⇒ 假 MISS。
            # 改成从 `_cross` 现算（`_cross` 就在上面按 `> +1.0` 算出来的）。
            ck_near("§VI 表【前】那句的条数与 hz2 的值",
                    "%s cross" % (_NUM9.get(len(_cross), str(len(_cross)))),
                    "sec_discussion.tex", "at the loose end", window=60)
            # ⚠ 查**复合串**「by $+1.01$」，不能只查 `+1.01` ——
            # `has()` 会把它退化成 `+1.0`（1 位小数），而表里**就有** `+1.0` ⇒ 假通过
            # （反向测试实测：把 +1.01 改成 +1.11，这条仍印 OK）。这正是 CLAUDE.md 那条
            # 「`has()` 是同一个数的不同写法，不是同一个数」。
            ck_near("§VI 表前那句引的 hz2(2nd run) 20s 值",
                    "by $%+.1f$" % float(_ss["hz2_r2"][2]),   # _ss 的值是元组 (5s,10s,20s)
                    "sec_discussion.tex", "at the loose end", window=140)

    # ------------------------------- 判决所依赖的那条【假设】必须印在 Limitations 里
    # 独立复核第 22 轮：全篇负判决的承重项是那条**插值线**（不是量过的静态点）——
    # 换成最近的**已跑过**的静态点，最近的那条臂是 **+5.8pp 越过**而不是 −0.3 在带内。
    # 论文原来只在 §II 与图注里说「这条线更严」，**没有说「更严 ≠ 有效」**，
    # 而 Limitations 里一个字都没有。已补，这里守住它别被删掉。
    _lim = P.get("sec_discussion.tex", "")
    for _ph, _d in (("piecewise interpolation between measured static points",
                     "Limitations 里「那条线是插值不是测量」"),
                    ("stricter", "Limitations 里「更严不等于有效」的对比"),
                    ("is an assumption", "Limitations 里「这是本论文唯一的假设」")):
        ck_near(_d, _ph, "sec_discussion.tex", "Limitations", window=4000)

    # ------------------------------- tierpair 的「擦线通过」必须印出来（2026-09-26）
    # 独立复核第 22 轮：正文原来只印「we report the verdict the criterion returns」，
    # **从不印那条 ≥10 点的阈值**，于是读者看不出它是**擦线**（10.14 vs 10）。
    # 而 §III 的因果主张正是论文标题所依赖的那一条。
    _tp = [r for r in load(os.path.join(ROOT, "paper/data/tierpair.csv"))
           if r.get("pair") == "paired"]
    if len(_tp) == 2:
        _dv = [float(r["realized_pct"]) for r in _tp]
        _gap = abs(_dv[0] - _dv[1])
        ck_near("§III 配对的兑现差", "%.1f" % _gap, "sec_model.tex", "it lands at", window=40)
        ck_near("§III 配对擦线的余量", "%.2f" % abs(_gap - 10.0), "sec_model.tex",
                "a pass", window=20)
        _dev = [float(r["realized_pct"]) for r in load(os.path.join(ROOT, "paper/data/tierpair.csv"))
                if r.get("side") == "device-only"]
        if len(_dev) >= 2:
            ck_near("§III 同配置 device 侧两次的差",
                    "%.1f" % (max(_dev) - min(_dev)), "sec_model.tex",
                    "its two runs differing by", window=60)

    # ------------------------------- §III 因果主张的【范围】必须印出来（2026-09-26）
    # codex 第 38 轮：同卡配对**只有一个并发水平**（R̄ 1.51 与 1.56），
    # 它识别的是**该工作点上兑现率的水平**，不是「并发升高时它怎么变」的**斜率**；
    # 斜率由 §IV 的分段 ε 给（host tier 把 ε 压在 1 以下、device-only 穿过 1）。
    # 正文原来把两者并成一句因果，已补 Scope 句，这里守住它。
    if len(_tp) == 2:
        _rr = sorted(float(r["Rbar_busy"]) for r in _tp)
        ck_near("§III 配对的在跑数（Scope 句）",
                "%.2f and %.2f" % (_rr[0], _rr[-1]), "sec_model.tex",
                "Scope", window=120)
        ck_near("§III 斜率来自哪一节", "sec:criterion", "sec_model.tex",
                "The slope is measured separately", window=200)

    # ------------------------------- 「时间片切换」那条 run（2026-09-26 起跑）
    # 它是全篇那条**插值线**的直接检验：线若有效，切换得到的点应落在线上；
    # 排队系统里通常低于弦，所以预期是**在线下方**（线=上界，判决因此保守）。
    # 跑完之前这里只报状态，跑完后再补正文。
    _sl = os.path.join(ROOT, "results", "night", "pois200_slice23_hc")
    if os.path.exists(os.path.join(_sl, "summary.json")):
        checks += 1
        secondary.append(("时间片切换 run 已落地，正文还没引它",
                          "pois200_slice23_hc", "results"))
    elif os.path.isdir(_sl):
        checks += 1
        secondary.append(("时间片切换 run 在跑（正文尚未引用）",
                          "%d 步" % sum(1 for _ in open(os.path.join(_sl, "steps.jsonl")))
                          if os.path.exists(os.path.join(_sl, "steps.jsonl")) else "刚起",
                          "results"))

    # ------------------------------- 退役名单自身的两条机械判据（2026-09-27，r53 F3）
    # 为什么放在最后：它们判的对象是**本次运行里退役名单被怎么用**，所以要等所有
    # `ck` / `ck_near` / `_direct_fail` 都跑完。
    # ⚠ `NORE=1` 让 `_retired()` 第一行就返回、什么都不记 ⇒ 那种跑法下这两条判据
    # **不适用**（会把整份名单误报成孤儿）。**但计数照记**：两跑法报的「共 N 项检查」
    # 必须相等 —— 检查数掉了本身是信号（本项目规矩），不该由跑法决定。
    _no_nore = not os.environ.get("NORE")
    # (a) 「孤儿键」：`RETIRED` 里有、而**一次也没有被咨询到**的键 —— 它既挡不住
    # 任何东西（没有检查对应它），也不会被 `NORE=1` 报出来（插桩之前看不见）。
    # 实测（2026-09-27 r53）：3 条（`§A100 本 tier 的 τ₂ 上界`、
    # `§Discussion round-1+ cap6_hc`、`图注里的条数与该图实际画出的集合规模不符`）
    # —— 已按「删键、不接路径」处置，见上面各处的注释。
    checks += 1
    if not _no_nore:
        if VERBOSE:
            print("  OK   孤儿键判据：NORE=1 下不适用（退役名单整个关掉了）")
    else:
        _orphan = [k for k in RETIRED if k not in _retired_used]
        if _orphan:
            fails.append(("退役名单里有没有检查去查的键（孤儿条目）",
                          "、".join(_orphan)[:70], "scripts"))
        elif VERBOSE:
            print("  OK   RETIRED 的 %d 个键都被咨询到了" % len(RETIRED))
    # (b) `STR_ELSEWHERE`（撞车注明）不能腐化：每条都必须在 `RETIRED` 里、
    # 语境串确实在正文里、而且**本次真的被命中过**（否则它已经过期，该删）。
    checks += 1
    if not _no_nore:
        if VERBOSE:
            print("  OK   STR_ELSEWHERE 判据：NORE=1 下不适用")
    else:
        _stale = []
        for _d, (_ctx, _wh) in STR_ELSEWHERE.items():
            if _d not in RETIRED:
                _stale.append("%s（不在 RETIRED 里）" % _d)
            elif not _str_elsewhere_ctx_ok(_ctx):
                _stale.append("%s（语境串已不在正文：「%s」）" % (_d, _ctx))
            elif _d not in _str_elsewhere_hit:
                _stale.append("%s（本次没被命中：值已不在正文？）" % _d)
        if _stale:
            fails.append(("STR_ELSEWHERE 里的注明已过期（该删）",
                          "；".join(_stale)[:70], "scripts"))
        elif VERBOSE:
            print("  OK   STR_ELSEWHERE 的 %d 条注明都成立（%s）"
                  % (len(STR_ELSEWHERE), "、".join(STR_ELSEWHERE)))

    if "--audit" in sys.argv:
        AUDIT.sort(reverse=True)
        print("\n===== 检查强度审计：被检查的值在它被检查的那段正文里出现几次 =====")
        print("（出现次数多 = 检查弱：值可能是在别处撞上的。只列 >=3 次的。）")
        _weak = [(n, d, v) for n, d, v in AUDIT if n >= 3]
        for n, d, v in _weak[:45]:
            print("  %3d 次  %-56s %s" % (n, d, v))
        print("  %d 项检查里，%d 项的值出现 >=3 次" % (len(AUDIT), len(_weak)))

    # ⚠⚠⚠ **检查数下界**（2026-09-27，r63 中立复核 8）：**「检查数掉了」此前没有任何机械判据。**
    # 复核者实测：删掉 `paper/supplement.tex` ⇒ **868 → 862**（6 条静默消失，
    # 含那条可数主张守卫），而唯一的信号是末行那个数字 —— **没有任何断言**。
    # 本项目自己的规矩是「检查数掉了和 MISS 一样是信号」，但**规矩没有变成判据**。
    # ⇒ 钉住下界。**只报「掉了」，不报「涨了」** —— 新增检查是好事，不该报。
    # ⚠⚠ 判据读到空源 ⇒ **硬报**（见 `_src_of` 里的长注释）。两次事故都是这个形状：
    # 检查恒走 secondary 分支、印成 `..`、**不计入退出码** —— 即一条检查静悄悄地没了。
    checks += 1
    if _EMPTY_SRC:
        fails.append(("有 %d 条检查**读到了空源**（那些检查是空转的）" % len(_EMPTY_SRC),
                      "、".join(sorted(set(_EMPTY_SRC))[:6]), "checker"))
    elif VERBOSE:
        print("  OK   没有检查读到空源（每条判据的 where 都取到了内容）")

    # ---- 脚本不许【往写死的绝对路径里写】（2026-09-28 事故；r66/r67 两条线各补了洞）----
    # 事故：`build_supplement.py` 的默认输出写死为 `/root/paper/foyer/paper` ⇒
    # 在**沙箱里**（cwd=副本）跑它照样写**活树**。沙箱只挡「相对 / cwd 推出来」的写入。
    #
    # ⚠ 判据经过四轮收紧，每一轮都对应一条实测构造（写在下面各自的注释里）。
    #   最终形状：**(a) 直接写语境里的绝对路径字面量**；或
    #   **(b) 绝对路径赋给的名字，沿「构造路径」的赋值闭包，触到一个真写行**。
    # ⚠⚠ 2026-09-28（r68）：写标记原来写成 `open\s*\([^)]*["'][wax+]` ——
    # `[^)]*` **过不了嵌套括号**：`open(os.path.join(OUT, "x"),` 里那个 `)` 会把它截断，
    # 于是「嵌套 + 跨行」的写调用两头都不匹配。⇒ 拆成**语句级**判定：
    # **同一条语句里既有 `open(` 又有写模式**（语句边界由逻辑行给出）。
    _OTHER = re.compile("savefig|makedirs|to_csv|DictWriter"
                        "|\\.write_text|\\.write_bytes|shutil\\.(copy|move|rmtree)"
                        "|\\.write\\(|os\\.(remove|unlink|rename|replace)|>>?\\s*[\"']")
    # ⚠⚠ 2026-09-28（r69 两条线各自实测）：原来写成「同语句里有 `open(` 又有
    # `["'][waxb]+["']` 串」—— 于是**纯读**语句 `with open(Q, encoding='utf-8',
    # errors='ignore') as f: print('w')` 被当成写（那个 `'w'` 与 open 无关）。
    # 中立复核用**旧检查器**对照确认：这是**本批新引入**的误报。
    # ⇒ 收紧成「`open(` 之后有**逗号 + 模式串**」（`mode="w"` 也认）。
    #   只读的 `open(Q)` / `open(DST).read()` 没有「逗号+引号串」⇒ 不报 ✓
    # ⚠⚠ 2026-09-28（r70 两条线）：上一版用 `open\(.*,\s*mode?=["'][waxb]+["']` 配 `re.S` ——
    # `.*` 会吃下 `)` 与换行 ⇒ 模式串可以属于**块里的另一条语句**：
    # `print(open(p).read(), "x")` 被报成写（中立 §11① 与 codex §12 各自实测），
    # 且没有模式串时从每个 `open(` 起点回退到块尾 ⇒ **超线性**（codex 实测 3000 次 0.437 s）。
    # ⇒ 改成**括号配平**取这次 `open(` 的实参范围，再在**顶层**（不看括号内部）找 `, mode=`。
    #   `#` 注释先剥掉（`open(Q,  # 注释` ⏎ `"w")` 这种夹注释的形态原来是漏的）。
    #   模式字符类补 `+`：`"a+"` / `"w+"` / `"r+"` / `"r+b"` 都是写（旧版 `[waxb+]` 含 `+`，
    #   我上一次收紧时漏掉了 —— codex §2/§11）。`"r"` / `"rb"` **不**算写 ✓。
    _MODE_ARG = re.compile(r"\s*(?:mode\s*=\s*)?[\"'](?:[wax][waxb+]*|r\+b?|rb\+)[\"']")

    def _open_has_mode(_blk):
        # ⚠⚠ 2026-09-28（r71 codex §9）：配平时**必须把字符串挖空** ——
        # `open(p, ")", "w")` 里那个 `)` 在字符串里，却参与配平 ⇒ 实参范围算错 ⇒ **漏报**。
        # 挖空只改**计数用的副本**，真正取实参仍从原文切（索引一致）。
        # ⚠⚠ 2026-09-28（r72 中立复核 §10）：原来的 `"[^"]*"` **不认转义引号** ——
        # `x = "a\"" ; open(D, "w")` 里会残留一个引号、与后面的引号配对，
        # 把**真代码整段挖掉** ⇒ 真写调用漏报。⇒ 改成转义感知
        # （复核用 ast 真值基准的 96 条电池验过：两处一起改 FN=0/FP=0）。
        _cv, _ok = _blank(_blk)   # ⚠ 用 tokenize 挖空（见 _blank 的注释：正则版有两个方向的错）
        # ⚠⚠ 2026-09-28（r74 中立复核 §5④）：挖空失败 ⇒ 配平/逗号扫描**不可信**，
        # 而且错的方向**两个都有**（复核各给了一个构造）。这条守卫的职责是
        # 「脚本不许往写死的绝对路径里写」（沙箱挡不住、会写回活树）⇒ 算不出来时
        # **按「报」处理**：假报只是噪声、看得见；漏报会静默毁掉活树。
        if not _ok:
            return True
        for _m in re.finditer(r"\bopen\s*\(", _cv):
            _i = _m.end()
            _d, _j = 1, _i
            while _j < len(_cv) and _d:
                _ch = _cv[_j]
                if _ch == "(":
                    _d += 1
                elif _ch == ")":
                    _d -= 1
                _j += 1
            _args = _blk[_i:_j - 1]          # 原文：模式串要从这里认
            _args_c = _cv[_i:_j - 1]         # 挖空副本：**结构**（括号/逗号）要从这里判
            # ⚠⚠ 2026-09-28（r72 中立复核 §1）：上面配平用了挖空副本，但**逗号扫描原来
            # 跑在未挖空的 `_args` 上** ⇒ 字符串里那个不配对的 `)` 把深度打到 −1，
            # 紧跟的逗号（`_d2 == 0` 才认）被跳过 ⇒ 模式找不到 ⇒ `open(os.path.join(D,"a)"),"w")`
            # 这类**漏报**（复核单函数实测 False，端到端也复现）。
            _d2 = 0
            for _k, _ch in enumerate(_args_c):
                if _ch in "([{":
                    _d2 += 1
                elif _ch in ")]}":
                    _d2 -= 1
                elif _ch == "," and _d2 == 0:
                    _tail = re.sub(r"#[^\n]*", "", _args[_k + 1:])
                    if _MODE_ARG.match(_tail):
                        return True
        return False

    def _is_write(_blk):
        return bool(_OTHER.search(_blk)) or _open_has_mode(_blk)
    _ABS = re.compile(r'["\'](/(?:root|home|data|mnt)/[^"\']*)["\']')
    _asg = re.compile(r'(?m)^\s*([A-Za-z_]\w*)\s*=\s*(.*)$')

    def _toks(_txt):
        """token 级判定：f-string 里的变量是 NAME；**字符串里的词不是**。

        ⚠⚠ 2026-09-28（r74 中立复核 §5④）：原来抛错时返回 `[]`，于是
        **「tokenize 失败」与「这段没有名字」不可区分** —— 三个调用点全都会把这个
        空集当成事实，方向**一律是漏报**。复核给的构造（未闭合字符串 + 后面接
        `open(DST, ")", "w")`）就是这么漏掉的：块不是合法 Python ⇒ `_names` 空 ⇒
        闭包支看不见那个名字。
        ⇒ 改成**返回 `None` 表示「没词法化成功」**，由调用方各自往**安全侧**回落。
        """
        import io as _io
        import tokenize as _tkz
        try:
            return [(t.type, t.string) for t in
                    _tkz.generate_tokens(_io.StringIO(_txt).readline)]
        except Exception:
            return None

    def _blank(_txt):
        # 把**字符串字面量**挖成等长空格 —— **用 `tokenize`，不用正则**。
        #
        # ⚠⚠ 2026-09-28（r73 codex §4/§9/§10）：我先用正则近似，结果**两个方向都错**：
        #   · **三引号**：`x = <三引号>\"a<三引号>; open(D,"w")` 由 True **变 False**
        #     （合法代码漏报）；而把一次真调用**整段放进字符串**的构造又 **变 True**（误报）；
        #   · **病态输入下平方级**：`"` 后跟 1 万个重复 `\"` 且无终止引号 ⇒
        #     **1.1 秒**（旧正则 0.0008 s）。
        # ⇒ 改用词法器，**线性且无歧义**。
        #
        # ⚠⚠ 2026-09-28（r74 中立复核 §5④）：这里原来写着「`tokenize` 抛错时原样返回
        # = 保守：宁可多报也不漏报」——**这句话是错的**，复核给了两个构造：
        #   · **漏报**：`x = ('未闭合` ⏎ `open(D, ")", "w"))` ⇒ `_is_write` 返回 False
        #     （未挖空时字符串里那个 `)` 提前把配平打到 0，逗号扫描跑偏，模式认不出来）；
        #   · **误报**：字符串里装着一个假写调用 ⇒ True。
        # ⇒ 回落分支是**双向**的，而且**漏报那一支正是这条审计最怕的方向**。
        #   所以改成**显式报告失败**：返回 `(文本, 是否挖空成功)`，由调用方决定 ——
        #   `_open_has_mode` 在失败时**按「算不出来」处理并报**（见那里的注释）。
        # ⚠ 本函数自己的注释里**不能出现三引号字面量**（会把 docstring 提前终止 —— 我刚犯过）。
        import io as _io
        import tokenize as _tkz
        _out = list(_txt)
        _strkinds = {_tkz.STRING}
        for _k in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
            _v = getattr(_tkz, _k, None)
            if _v is not None:
                _strkinds.add(_v)
        # ⚠⚠ 2026-09-28（r75 中立复核 §4）：这里原来用 `splitlines(keepends=True)` 建**行首偏移表**，
        # 而**调用方**用的是 `split("\n")`。两者在含 `\f` / `\x0b` / `\x85` / U+2028 / U+2029
        # 的文本上**断行位置不同** ⇒ 偏移整体错位 ⇒ 调用方按行号取回的是**别的行**
        # （复核给了字节级证据：源文本行首插一个 `\f` 后，第 3 行起全部差 20 字符，
        #  真码里的 `+` 被挖掉、字符串反而没被挖）。
        # ⇒ **两处必须用同一种断行**：这里改成 `split("\n")`，与调用方逐字一致。
        _parts = _txt.split("\n")
        _base = [0]
        for _p in _parts[:-1]:
            _base.append(_base[-1] + len(_p) + 1)
        try:
            for _t in _tkz.generate_tokens(_io.StringIO(_txt).readline):
                if _t.type not in _strkinds:
                    continue
                _a = _base[_t.start[0] - 1] + _t.start[1]
                _b = _base[_t.end[0] - 1] + _t.end[1]
                # ⚠ 行号越界 = 偏移表与词法器对不上（正是上面那个断行不一致的症状）。
                # 这是**唯一一条真会开火的**自检 —— 见下面对旧断言为什么是空转的说明。
                if _t.start[0] - 1 >= len(_base) or _t.end[0] - 1 >= len(_base):
                    return _txt, False
                for _i in range(_a, min(_b, len(_out))):
                    if _out[_i] != "\n":
                        _out[_i] = " "
        except Exception:
            return _txt, False
        # ⚠⚠ 2026-09-28（r75 中立复核 §4）：这里原来写着「长度必须不变 …… 自己先断言」——
        # **那是空转的**：`_out = list(_txt)` 且只做等长替换 ⇒ `len(_out) != len(_txt)` **恒假**；
        # 调用方那条 `len(_sb_all) != len(_all)` 同样恒假（挖空不碰 `\n`，两个串的 `\n` 数相同）。
        # 复核在 107 个活树脚本 + 6 个病态输入上实测**触发 0 次**。
        # ⇒ 删掉这两句假的「断言」，改成上面那条**行号越界**检查（它真的会响）。
        # 真正要保证的性质「偏移表与调用方的断行一致」现在由**构造**保证（两处都用 `split("\n")`）。
        return "".join(_out), True

    def _names(_txt):
        """返回名字集合；**词法化失败时返回 `None`**（不是空集 —— 见 `_toks` 的注释）。"""
        import tokenize as _tkz
        _t = _toks(_txt)
        if _t is None:
            return None
        return {_x for _ty, _x in _t if _ty == _tkz.NAME}

    def _pathy(_rhs, _clo=()):
        """这段表达式在**构造路径**吗？（不是问它是不是由路径派生出来的数据）

        `_clo` 是当前闭包；**只有 pathlib 的 `/` 需要它** —— 见下面那条注释。
        """
        # ⚠ 也认裸 `join(`：`from os.path import join` 之后 `p = join(BASE, "x")`
        # 里没有 `os.path.join` 这个字面量（r68 中立复核 §12.2 实测漏报）。
        # ⚠⚠ 2026-09-28（r75 中立复核 §3）：`join\s*\(` **认不出 `joinpath(`**
        # （`join` 后面跟的是 `path(`，不是 `(`）—— 而那是 pathlib 的标准写法。
        # 同一条复核还指出 **pathlib 的 `/` 运算符**（`p = BASE / "x.csv"`）也漏：
        # 串里没有斜杠、也没有 `join(` ⇒ 判成「不在构造路径」⇒ 整条闭包链断掉。
        # 两个都是**既有洞**（复核逐条对照过：旧版同样漏），不是本批引入的。
        if (re.search(r"\bjoin\s*\(|\bjoinpath\s*\(", _rhs)
                or "os.sep" in _rhs or "pathlib" in _rhs):
            return True
        import tokenize as _tkz
        # ⚠⚠ 3.12 起 f-string **不是** STRING token（拆成 FSTRING_START/MIDDLE/END）⇒
        # 只认 STRING 会让 `f"{BASE}/results/night"` 判成「不在构造路径」，
        # `run_matrix.py` 这种**真阳性**就漏了（沙箱实测：闭包停在 BASE 不长）。
        _mid = getattr(_tkz, "FSTRING_MIDDLE", None)
        _t = _toks(_rhs)
        if _t is None:
            # ⚠⚠ 这里**不能**一律返回 True。`_asg` 只取**一行**，所以任何跨行语句
            # （`ctrl = subprocess.Popen(` 这种）都会词法化失败 —— 那是**常态**，
            # 一律当 True 会让闭包疯狂生长（我第一版就是这么写的，活树上立刻多出
            # 4 条假报：`agg.py` / `decode_rate.py` / 两个 smoke_*.py）。
            # ⇒ 退回**有界的文本判据**：只有出现「构造路径」的信号才算。
            return bool(re.search(r"\bjoin\s*\(|os\.sep|pathlib", _rhs)
                        or re.search(r"[\"'][^\"'\n]*/", _rhs)
                        # pathlib 的 `/`，回落版：**左操作数必须是闭包里的名字**。
                        or any(re.search(r"\b%s\s*/" % re.escape(_c), _rhs) for _c in _clo))
        # pathlib 的 `/` 运算符（见上）：**左操作数必须是闭包里的名字**。
        # ⚠⚠ 第一版写成「表达式里出现 OP `/` 就算」—— 活树上立刻多一条假报：
        # `wall = (m.get("wall_s") or 0) / 60 if ... else wall_minutes(d)` 是**数值除法**，
        # 而它的 RHS 恰好引用了闭包名 `d`（`d = os.path.join(NIGHT, name)`）⇒ 闭包长出
        # 一个不相干的 `wall` ⇒ 后面某个含写标记的块被报。**`/ 60` 太常见了，不能当路径信号。**
        # 判据收紧成：`/` 的**前一个 token 是闭包名**（`BASE / "x.csv"` ✓；
        # `(...) / 60` 的前一个是 `)` ✗）。
        _sig = [(_ty, _x) for _ty, _x in _t
                if _ty not in (_tkz.NL, _tkz.NEWLINE, getattr(_tkz, "COMMENT", -1),
                               getattr(_tkz, "INDENT", -2), getattr(_tkz, "DEDENT", -3))]
        for _k in range(1, len(_sig)):
            if _sig[_k] == (_tkz.OP, "/") and _sig[_k - 1][0] == _tkz.NAME \
                    and _sig[_k - 1][1] in _clo:
                return True
        return any((_ty == _tkz.STRING or (_mid is not None and _ty == _mid))
                   and "/" in _x for _ty, _x in _t)

    # 白名单**一条**，理由写在这里（不是「消音」，是明示豁免）：
    #   `run_matrix.py` 是**实验机上的启动器**，它的职责就是往 `$BASE/results/night/`
    #   写 run 目录；它**不在** AE 复现路径上（三条命令只用 `regen_all.sh` 与生成器），
    #   也**不该在副本树里跑**。⚠ 不能把它改成从 `__file__` 推：机器上它在
    #   `TraceLab/replay/scripts/` 下，上溯两层得到的是 `/data/xbw/turnstile/TraceLab`，
    #   **不是** `/data/xbw/turnstile`。⇒ 豁免，并把这条理由连同它的哈希写进文档。
    _ABS_OK = {"run_matrix.py"}
    _abs_bad = {}
    for _n, _s in _src.items():
        if not _n.endswith(".py") or _n in _ABS_OK:
            continue
        # ⚠⚠⚠ 2026-09-28（r74 中立复核 §7）：**这一段原来也是「用正则近似词法」** ——
        # 逐物理行挖空用的是 `"[^"]*"|'[^']*'`，于是**三引号字符串里一个孤立的 `(`**
        # 就能把深度计数带偏：后面几行被并进一个**从字符串中间开始**的块，
        # 那个块不是合法 Python ⇒ `_names()` 里的 `tokenize` 抛错 ⇒（当时）返回空集 ⇒
        # **闭包支对该块完全失明**。复核给了可复现构造（`HELP = <三引号>…(<三引号>`
        # 之后 `p = BASE + "/x.csv"` + `open(p,"w")`）⇒ 不报；删掉那个 `(` ⇒ 报。
        # ⇒ 与 `_blank` 一样改用**词法器挖空**，而且**整文件挖一次**（跨行字符串才挖得对），
        #   再按**行号**取回每一行。`split("\n")` 而不是 `splitlines()`：
        #   要与 `_blank` 的行计数对齐（`splitlines` 还会在 `\f`/`\x85` 等处断行）。
        _all = _s.split("\n")
        _sb, _okf = _blank(_s)
        _sb_all = _sb.split("\n")
        if not _okf:
            # 拿不到可信的挖空文本 ⇒ 退回「不挖空」。
            # ⚠⚠ 2026-09-28（r75 中立复核 §5）：这里原来写着「块只会**变大** ⇒ 更容易报，
            # 不会静默漏」——**那个理由不成立**。复核给了反例：字符串里一个不配对的 `)`
            # 会把深度提前打到 0 ⇒ 块**被切开/变小**（实测 `_starts` 从 `[0,1,1,3,4]`
            # 变成 `[0,1,2,3,4]`），而不是变大。
            # 所以**能增也能减**，两个方向都可能 —— 这一支没有单调性保证。
            # ⚠ 复核在 92 个组合（6 种真写 × 8 种括号不平衡字符串 × 前后顺序）上
            # **没能造出「不挖空反而漏报」**，所以现实风险低；但那句话不构成保证，
            # 这里照实写。真要让这条路径可信，得让 `_blank` 在**任何**输入上都成功
            # （它现在只在文件不是合法 Python 时才失败）。
            _sb_all = _all
        _ls, _lsb = [], []
        for _i, _L in enumerate(_all):
            if _L.strip().startswith("#"):
                continue
            _ls.append(_L)
            _lsb.append(_sb_all[_i])
        if not _ABS.search("\n".join(_ls)):
            continue
        _dep, _st, _starts, _ends = 0, 0, [], []
        for _L in _lsb:
            if _dep <= 0:
                _st = len(_starts)
            _starts.append(_st)
            # ⚠ 再**剥尾注释**，最后才数括号 —— 尾注释里的 `)` 会把深度提前归零、
            # 把一条语句切成碎片，碎片上的 `tokenize` 会抛 `TokenError`（r69 中立复核实测）。
            # ⚠ 剥 `#` 现在**是安全的**：字符串已经挖成空格，`#` 不可能来自字符串内部
            # （旧版用朴素正则时，未挖干净的字符串里的 `#` 会把真代码截断 —— 同类的坑）。
            _c = re.sub(r"#.*$", "", _L)
            _dep += sum(_c.count(c) for c in "([{") - sum(_c.count(c) for c in ")]}")
            if _dep < 0:
                _dep = 0
        for _i in range(len(_ls)):
            _ends.append(max([k for k in range(_i, len(_ls))
                              if _starts[k] == _starts[_i]] or [_i]))
        # (a) 直接写语境
        for _i, _L in enumerate(_ls):
            for _m2 in _ABS.finditer(_L):
                if _is_write("\n".join(_ls[_starts[_i]:_ends[_i] + 1])):
                    _abs_bad.setdefault(_n, []).append("%d:%s" % (_i + 1, _m2.group(1)[:34]))
        # (b) 闭包：只沿**构造路径**的赋值传递（纯数据流不算 —— 否则 `m=json.load(open(p))`
        #     会把 `pool`/`trace`/`wall` 全染上，然后在字符串里撞出假报）
        _closure = set()
        for _L in _ls:
            _m3 = _asg.match(_L)
            if _m3 and _ABS.search(_m3.group(2)):
                _closure.add(_m3.group(1))
        _grew = True
        while _grew:
            _grew = False
            for _L in _ls:
                _m3 = _asg.match(_L)
                if not _m3 or _m3.group(1) in _closure:
                    continue
                _rhs3 = _m3.group(2).strip()
                # 纯别名（`X = PAPER`）也要传：它不是「数据流」，是**同一个路径的另一个名字**。
                # ⚠ r68 codex 实测：不加这一条，`PAPER→X→open(X,'w')` 的**纯赋值**形态漏报。
                if not (_pathy(_rhs3, _closure) or _rhs3 in _closure):
                    continue
                _nm2 = _names(_m3.group(2))
                # ⚠ 词法化失败（`None`）在**跨行语句**上是常态（`_asg` 只取一行）⇒
                #   不能一律当成「撞上了」（同上，会造成假报）。退回**词边界文本匹配**。
                _g2 = _m3.group(2)
                _hit2 = (any(re.search(r"\b%s\b" % re.escape(_c2), _g2) for _c2 in _closure)
                         if _nm2 is None else bool(_nm2 & _closure))
                if _hit2:
                    _closure.add(_m3.group(1))
                    _grew = True
        # ⚠⚠ 2026-09-28（r68 中立复核）：这一段原来是**逐物理行**判的 ⇒
        # 「闭包名 + 写调用跨物理行」**全漏**：
        #     Q = "/root/…"
        #     with open(Q,          ← 这一行 `_WR` 匹配不上（模式串要同行有 "w"）
        #               "w") as f:  ← 这一行没有名字
        # 复核实测 4 个变体全不报；根因还更深一层：`tokenize` 在**括号不闭合的行片段**上
        # 直接抛 `TokenError('unexpected EOF')`，而 `_toks` 当时把异常吞掉 ⇒ `_names()` 空集。
        # ⇒ 与 (a) 支用同一个**逻辑行（括号块）**窗口：块内括号平衡，token 化不会炸。
        # ⚠ 2026-09-28（r74）：`_toks` 现在**失败返回 `None`**（不再返回空集），
        #   所以下面那个 `_names(_blk)` 还要处理 `None` —— 见紧邻的回落注释。
        for _nm in sorted(_closure):
            for _i in range(len(_ls)):
                _blk = "\n".join(_ls[_starts[_i]:_ends[_i] + 1])
                _nmb = _names(_blk)
                # ⚠⚠ 2026-09-28（r74 中立复核 §5④）：`_names` 返回空集时这里**静默跳过**，
                # 而「词法化失败」也会走到这里 ⇒ 漏报。现在失败是 `None`，改用
                # **词边界文本匹配**回落（在字符串里撞上也算 ⇒ 多报，安全侧）。
                _hit = (re.search(r"\b%s\b" % re.escape(_nm), _blk) is not None
                        if _nmb is None else _nm in _nmb)
                if _is_write(_blk) and _hit:
                    _abs_bad.setdefault(_n, []).append(
                        "间接 %s→%s" % (_nm, _blk.strip().replace("\n", " ")[:34]))
                    break
    checks += 1
    if _abs_bad:
        fails.append(("脚本**往写死的绝对路径里写**（沙箱挡不住 ⇒ 会写回活树）",
                      "、".join("%s(%s)" % (k, v[0]) for k, v in sorted(_abs_bad.items())[:4]),
                      "scripts/"))
    elif VERBOSE:
        # ⚠ 措辞按**实测的边界**写（每条都有反向测试）：覆盖 直接写 / 间接（构造路径闭包）/
        #   跨行写标记 / os.remove / write_text；**不覆盖** 模块别名（`import os as _o`）、
        #   经 subprocess 的外部命令、`.sh` 脚本。
        # ⚠ 措辞按**实测**写（每一条都有反向测试；r70 两条线各补了一轮）：
        #   覆盖：直接写 / 间接（构造路径闭包，含别名与 `join(`）/ 跨行（含嵌套）/
        #        `os.remove|unlink|rename|replace` / `write_text|write_bytes` /
        #        模式含 `+`（`"a+"`/`"w+"`/`"r+"`）/ `mode="w"` / 逗号后夹注释。
        #   不覆盖（实测确认的边界）：模块别名（`import os as _o`）、经 `subprocess` 的外部命令、
        #        `.sh` 脚本、模式不是字面量（`open(p, WM)`）、`**dict(mode=…)`、
        #        `os.open(…, os.O_WRONLY)` 这类 os 级接口。
        print("  OK   没有脚本在写语境里用写死的绝对路径"
              "（覆盖直接写/间接闭包(含别名)/跨行含嵌套/remove/write_text/模式含+；"
              "模块别名·子进程·.sh·非字面量模式不在判据内）")

    # ---- 检查数下界（r66 复核：原来这个块在**最后两条检查之前**执行 ⇒
    # 它看到的是 869 而不是总数 871，于是「删掉本批新增的守卫」它发现不了）----
    # ⇒ **挪到最末**，紧挨总结行之前。
    # ⚠⚠ 2026-09-28（r69/r70 两轮复核各实测到一次 off-by-one）：这个数
    # **必须等于「当时的总数」**，否则余量变成 1、删一条检查就不报。
    # **每加一条检查，都要把它抬到新的总数上**（r74 中立复核 §4：这里原来还写着 878）。
    # ⚠⚠⚠ 2026-09-28（r69/r70/r71 连测三次 off-by-one 之后改成**精确相等**）：
    # 语义原来是「下界」，而我每次加完检查**忘了抬它** ⇒ 余量变成 1 甚至 0，
    # 「删掉一条检查」就不报（两轮复核各实测到一次）。
    # ⇒ 改成**必须精确相等**：**任何**增减都会响，且报文会告诉你是哪一边。
    #    新增检查 ⇒ 把下面这个数抬到新的总数（报文里给了）。
    #    减少检查 ⇒ 那就是守卫被删了，去查。
    _CHECKS_N = 882
    checks += 1
    if checks != _CHECKS_N:
        _dirn = "新增了 %d 条 ⇒ 请把 _CHECKS_N 改成 %d" % (checks - _CHECKS_N, checks) \
            if checks > _CHECKS_N else (
                "**少了 %d 条** —— 两种成因都要查：① 有守卫被删；"
                "② **某个检查块因数据缺失整块没执行**（本项目记过这一类："
                "删一行 table1 就会少 14 条，因为块里的 `checks += 1` 在 `if` 里面）"
                % (_CHECKS_N - checks))
        fails.append(("检查数与 _CHECKS_N 不符：%s" % _dirn,
                      "%d vs %d" % (checks, _CHECKS_N), "checker"))
    elif VERBOSE:
        print("  OK   检查数 %d 与 _CHECKS_N 精确相等" % checks)

    print("共 %d 项检查：%d 项 MISS（正文引用过、却没找到，必须处置），"
          "%d 项次要未印（论文只印聚合值，属预期）。" % (checks, len(fails), len(secondary)))
    if _noop_retired:
        # ⚠ 这一行【不是】失败：值在正文里、检查通过。它报的是**退役记录本身失效**了 ——
        # 而那正是 `NORE=1` 看不见的一类（值命中时根本不查退役名单）。逐条处置：
        # 要么把那条退役删掉（守卫生效了），要么把正文里的值按新的口径删/改。
        print("⚠ %d 条退役项的值仍在正文里（退役**没有生效**，见上面的 `!!` 行）——"
              "NORE=1 看不见这一类：" % len(_noop_retired))
        for d in _noop_retired:
            print("    · %s" % d)
    for desc, val, where in fails:
        print("  MISS %-56s %-12s (%s)" % (desc, val, where))
    if secondary and (VERBOSE or fails):
        print("  —— 次要（不计入退出码，供扫一眼）——")
        for desc, val, where in secondary:
            print("  ..   %-56s %-12s (%s)" % (desc, val, where))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
