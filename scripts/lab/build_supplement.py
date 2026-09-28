#!/usr/bin/env python3
"""生成**英文** supplement（`supplement.tex`）—— RTAS 2027 投稿件的一部分。

## 为什么是「新写一份」而不是把 paper/*.md 合起来

那六份 .md 是**工作记录**：22,665 个汉字（对照 9,378 个英文词）、
含大量「这个值现在在哪」的记账，**不是给审稿人写的**，而且**是中文的**。
论文是英文、审稿人是国际的 ⇒ 中文 supplement 对他们**没有用**。

⇒ 正确做法：按**论文实际指向的 11 处**，写一份英文、面向审稿人的支撑材料。
判据（每条都必须有着落）：
  1 sec_xtrace:100   三次 A100 基线尝试 + 逐 run 读数
  2 sec_results:141  完整 run 表（含正文省略的 8 条静态 cap）
  3 sec_results:162  投影的逐周期读数
  4 sec_results:194  逐臂读数（attribution）
  5 sec_discussion:76 逐臂重推导（release 规则那条）
  6 sec_discussion:93 就绪时钟下逐臂的位移
  7 sec_discussion:130 那些脚本与数据文件的名字 + 五条独立复算线
  8 sec_discussion:157 控制器产物版本史
  9 sec_discussion:168 审计文件（共租取证）+ 七条撤回
 10 sec_model:244    逐 run 的 idle 分解 + 结构性补救
 11 sec_background:36 池子偏短的成因与它对可比性的影响

**只读仓库**（读 paper/data/*.csv 与 paper/supplement_table1.md），产物写 OUTDIR。
"""
import csv, json, os, re, sys

# ⚠⚠⚠ 2026-09-28（**实测事故，本形状的第三次**）：这三行原来是**写死的绝对路径**。
# 后果：在**沙箱里**（cwd=/tmp/rv65，paper/ 是副本）无参跑它，它照样写进**活树**的
# `paper/supplement.tex` —— 沙箱只挡「相对 / cwd 推出来的」写入，**挡不住写死的绝对路径**。
# （本次内容逐字节相同，只有 mtime 被打乱。）这与 CLAUDE.md 记过两次的
# 「审计脚本的无参兜底硬编码输出路径」是同一个形状。
# ⇒ 路径一律**从 `__file__` 推**：脚本住在哪棵树，就写哪棵树。
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(_ROOT, "paper", "data")
PAPER = os.path.join(_ROOT, "paper")
# ⚠⚠ 2026-09-27（r59 codex + 我自己的实测）：**这里原来硬编码 `/tmp/supp_en`** ——
# 于是「跑生成器」写的是 /tmp，而仓库里的 `paper/supplement.tex` **纹丝不动**，
# 接着编译的还是旧的那份 ⇒ **改了等于没改，而且看不出来**。
# （codex 原话：「脚本还将输入根目录写死为仓库绝对路径」。）
# ⇒ 默认写到**它该在的地方**（`paper/`），并允许用 argv[1] 覆盖。
OUT = sys.argv[1] if len(sys.argv) > 1 else PAPER

ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
       "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def esc(s):
    return "".join(ESC.get(c, c) for c in str(s))


def load(name):
    p = os.path.join(D, name)
    if not os.path.exists(p):
        return []
    rows = [l for l in open(p, encoding="utf-8") if not l.startswith("#")]
    return list(csv.DictReader(rows))


def table(rows, cols, headers=None, align=None):
    """rows = list of dict；cols = [(键, 表头)]。

    ⚠⚠ 2026-09-27（r59 中立复核 1）：**宽表会把最右列裁掉，而且不报错。**
    复核者实测：交付的 supplement 有 **4 处 Overfull**（305.4 / 97.8 / 113.7 / 45.8 pt），
    「The three baseline attempts」那张 14 列的表被切在 `occ mean pct` 之后 ——
    `566 of 566`、`147.5941` 这些**正文引用的读数**在成品 PDF 里**一个字都没有**。
    而**主论文那三条排版卫兵读的是 `main.log`，看不见 `supplement.log`**。
    ⇒ 判据：**列数 > 7 的表放进横向页**（A4 横排文本宽 ≈ 800pt vs 竖排 ≈ 450pt），
    并统一收紧列距。**不许靠「看起来还行」** —— 见下面 build 完的 Overfull 自检。
    """
    headers = headers or [h for _, h in cols]
    wide = len(cols) > 7
    out = []
    if wide:
        out.append(r"\begin{landscape}\begin{center}\footnotesize\setlength{\tabcolsep}{3pt}")
    else:
        out.append(r"\begin{center}\footnotesize\setlength{\tabcolsep}{4pt}")
    out += [r"\begin{tabular}{" + ("l" + "r" * (len(cols) - 1)) + "}", r"\toprule",
            " & ".join(headers) + r" \\", r"\midrule"]
    for r in rows:
        out.append(" & ".join(esc(r.get(k, "")) for k, _ in cols) + r" \\")
    out.append(r"\bottomrule")
    out.append(r"\end{tabular}" + (r"\end{center}\end{landscape}" if wide else r"\end{center}"))
    return "\n".join(out)


S = []          # 各节

# ---------------------------------------------------------------- S1 完整 run 表
md = open(os.path.join(PAPER, "supplement_table1.md"), encoding="utf-8").read()
blocks = re.findall(r"\\begin\{tabular\}.*?\\end\{tabular\}", md, re.S)
S.append(r"""\section{The full run table}

Table~I of the paper lists the rows the argument turns on; the table
below is the complete run table, including the eight static caps the paper omits
for space. Columns are the run, its wall clock, the mean running-request count
during busy time, occupancy, deadline satisfaction rate, and the signed distance
$\Delta$ from the static envelope at that wall clock. $\Delta>+1.0$\,pp is above
the line, $\Delta<-1.0$\,pp below it, and the band between is a tie.
""")
if blocks:
    # ⚠ 逐字嵌入的表里含 `\S\ref{sec:results:aimd}` —— 在**独立文档**里解析不到
    # （渲染成 `??`）。supplement 是单独编译的，跨文档引用一律写成正文里的节号。
    blk = blocks[0].replace(r"\S\ref{sec:results:aimd}", "\S V")
    S.append(blk)
else:
    S.append(r"\emph{(full table not found)}")

# ---------------------------------------------------------------- S2 逐臂归因
at = load("attribution.csv")
if at:
    cols = [(k, h) for k, h in [
        ("arm", "arm"), ("wall_min", "wall (min)"), ("nearest_static", "nearest static"),
        ("occ_pct", "occ. (\\%)"), ("Rbar_busy", "$\\overline{R}_{\\mathrm{busy}}$"),
        ("tau1_ms", "$\\tau_1$ (ms)"), ("static_occ_pct", "static occ. (\\%)"),
        ("static_tau1_ms", "static $\\tau_1$ (ms)"), ("verdict", "class")] if k in at[0]]
    S.append(r"""\section{Per-arm attribution}

Each controller arm is compared against the static run whose wall clock is
closest to it, not against the static \emph{front}: the classification describes
an arm relative to a wall-clock peer. The six unused-memory rows also run fewer
requests than their comparison, which describes what they did rather than
demonstrating that another choice would have won.
""" + table(at, cols))

# ---------------------------------------------------------------- S3 投影逐周期
pj = load("projection.csv")
if pj:
    cols = [(k, h) for k, h in [
        ("run", "run"), ("samples", "cycles"), ("budget", "budget"),
        ("proj_p50", "projection p50"), ("occ_p50", "occupancy p50"),
        ("ratio", "ratio")] if k in pj[0]]
    # ⚠⚠ 2026-09-27（r62 codex 复核 1）：**表是全表（57 行、跨多条 trace），
    # 而句子说的是「本 trace 上跑完的那 27 条控制器 run」—— 作用域比句子宽。**
    # 处置：**把属于那个集合的行标出来**（首列加 `*`），并在说明里交代。
    # 判据**照抄 `gen_projection.py` 的 `main` 组**（第 101-111 行）：
    #   ① `_tr(run)` 读 **`metadata.json` 的 `trace` 字段**并取 basename ——
    #      ⚠ **不是名字前缀**！我连写了三版按前缀筛的判据（先 `pois200_` 前缀、
    #      再加 NaN、再加 summary），算出 29/29/29，而正文是 **27**。
    #      根因是 `_tr` 用的是**元数据**，而我一直按**名字**猜。
    #      **这是本段第四次「按名字看起来像什么写判据」** —— 前三次在检查器的守卫里。
    #   ② `ratio == ratio`（排 NaN）；③ `_done`（`summary.json` 存在）。
    _RR = os.path.join(_ROOT, "results", "night")
    TRACE_MAIN = "replay_pois200_l04.csv"

    # ⚠⚠ 2026-09-27（r64 codex 复核 2）：**原来用 `x == x` 排 NaN —— 而 csv 读出来的
    # 是【字符串】，`"nan" == "nan"` 恒真** ⇒ 那个筛选对字符串**永远不生效**。
    # 复核者原话：「`ratio == ratio` 对字符串恒真，将来不能排除字面 `"nan"`」。
    def _notnan(x):
        try:
            return float(x) == float(x)
        except (TypeError, ValueError):
            return False

    def _tr(run):
        try:
            return os.path.basename(json.load(open(os.path.join(_RR, run, "metadata.json"))).get("trace") or "")
        except Exception:
            return "?"

    def _done(run):
        return os.path.exists(os.path.join(_RR, run, "summary.json"))

    _main_ids = {r.get("run", "") for r in pj
                 if _tr(r.get("run", "")) == TRACE_MAIN
                 and _notnan(r.get("ratio"))
                 and _done(r.get("run", ""))}
    print("  投影表：主 trace 且跑完的 = %d 行（正文说 27）" % len(_main_ids))
    S.append(r"""\section{The controller's occupancy projection}

The paper reports the ratio of the controller's projection to the occupancy the
engine reports, across the twenty-seven controller runs that finished on this
trace. The table below gives, per run, the median projection, the median
occupancy the engine reports, and their ratio across that run's cycles. It lists
every run in the file, which spans more than one trace; rows marked $\ast$ are
the ones on the paper's trace.
""" + table([dict(r, run=("* " if r.get("run") in _main_ids else "") + r.get("run", ""))
             for r in pj], cols))

# ---------------------------------------------------------------- S4 A100 + 三次基线
bl = load("a100_baseline.csv")
a1 = load("a100.csv")
S.append(r"""\section{The second accelerator}

\subsection{The three baseline attempts}
""")
if bl:
    S.append(table(bl, [(k, k.replace("_", " ")) for k in bl[0].keys()]))
S.append(r"""
There were three attempts in the sense that a server was started three times.
Only two produced readings, and they are the two rows above; the third was
abandoned before the trace started, so it contributes no numbers. The second
attempt is a reading of a contended host, not a baseline, and nothing in the
paper uses it; it is listed because withholding it would make the first attempt
look like the only one we made.

\subsection{Static sweep and the controller on the second accelerator}
""")
if a1:
    S.append(table(a1, [(k, k.replace("_", " ")) for k in a1[0].keys()][:9]))

# ---------------------------------------------------------------- S5 就绪时钟
aslo = load("arrival_slo.csv")
if aslo:
    S.append(r"""\section{The ready clock, per arm}

The paper reports the engine clock (first token, timed from the engine) as
primary, and notes that no arm moves from below the line to above it under the
ready clock. The per-arm shifts are below: the ready clock charges the door,
that is, it starts counting when a request is offered rather than when it is
admitted.
""" + table(aslo, [(k, k.replace("_", " ")) for k in aslo[0].keys()][:9]))

# ---------------------------------------------------------------- S5b 逐臂重推导
t1 = load("table1.csv")
if t1:
    ctr = [r for r in t1 if r.get("run", "").startswith(("foyer", "aimd"))]
    S.append(r"""\section{Per-arm re-derivation}

The paper's claim is not that admission control is useless but that the one arm
above the static envelope is a change to the \emph{release} rule, while every arm
that changes the \emph{admission} decision is not. The per-arm distances behind
that sentence are below; $\Delta$ is the signed distance from the static
envelope at the arm's own wall clock, so $\Delta>+1.0$\,pp is above the line and
$-1.0\le\Delta\le+1.0$ is the tie band. The three \texttt{scan} rows are the
same release-rule change run three times: two are above the line and the third
lands inside the band, which is why the paper reports it as two of three rather
than as a crossing.
""" + table(ctr, [(k, k.replace("_", " ")) for k in
                  ("run", "wall_min", "Rbar_busy", "slo_pct", "delta_pp", "verdict")
                  if k in t1[0]]))

# ⚠⚠ 2026-09-27：这个数原来**手写成 "fifteen"** —— 而正文（正确地）写 seventeen。
# 两处不一致，而且两个都**没有任何东西保证**。⇒ 改成**从数据算**，与检查器同口径：
# `reuse.csv` 的 family=hicache 且非 CONTESTED、名字属 Foyer 族、且 `steps.jsonl` **跑满 999 步**。
# （最后那条筛选是我第一版手工复算时漏掉的 —— 所以手算的数不可靠，必须让代码算。）
def _clean_family_n():
    _cc = {r["run"]: r for r in load("concurrency.csv")}
    n = 0
    for r in load("reuse.csv"):
        k = r["run"]
        if r["family"] != "hicache" or r["contested"] == "CONTESTED":
            continue
        if not (k.startswith("foyer_") or k.startswith("pairA_foyerhc")
                or k.startswith("pairB_foyerhc") or k == "foyfix_hc"):
            continue
        if not _cc.get("pois200_" + k):
            continue
        sp = os.path.join(_ROOT, "results", "night", "pois200_" + k, "steps.jsonl")
        if not os.path.exists(sp) or sum(1 for _ in open(sp)) != 999:
            continue
        n += 1
    return n

_N_CLEAN = _clean_family_n()

# ---------------------------------------------------------------- S6 共租审计
S.append(r"""\section{Co-tenancy on the measurement host}

An audit flags every run that overlapped three or more others for at least an
hour. Fourteen runs are flagged --- twelve of the main trace and two of the
second workload; the incidents that produced those windows also killed four runs
outright, and those four appear in no table of ours.

The flag is a risk marker, not a damage measurement. Engine-side counters
(running count, pool occupancy, evictions, recomputation) are indistinguishable
between flagged and clean runs, so the audit can only be run on the client-side
per-request decode interval $\tau_2$. Where damage is legible it is large: the
worst-affected arm reads $33.3$\,ms when flagged against $24.8$\,ms on a clean
re-run, while %s clean runs of the same controller family read
$23.8$--$27.5$\,ms.

Three within-run comparisons, each entirely inside one run, are the strongest
evidence we have that the effect is real: for \texttt{cap1}, the per-half-hour
median $\tau_2$ is $20.3$--$20.9$\,ms over the first five and a half hours and
$21.3/27.1/21.1$\,ms over the three and a half hours after two neighbours
start; for \texttt{t85} it is $29.8$\,ms in the half hour before a neighbour
leaves and $22.3$--$22.6$\,ms over the four and a half hours after; for
\texttt{rl99} it is $32.4$\,ms against $25.2/25.1$\,ms. Same run, same policy,
same trace --- what changes is who else is on the machine.

Volume columns do not see the damage: the one arm we have two readings for reuses
$0.6943$ of its prompt when flagged and $0.6904$ alone, both inside the
$0.4511$--$0.6981$ range of the twenty-eight host-tier runs we have two-use data
for, while its $\tau_2$ moves from $31.3$ to $24.8$\,ms. That is suggestive, not
proof: one arm is one comparison.
""" % _N_CLEAN)

# ---------------------------------------------------------------- S7 版本史
S.append(r"""\section{Controller artifact version history}

The runs record four distinct hashes of the controller module, and none of them
matches the copy in the repository. No single revision therefore reproduces every
number we report. The arms the audit flags are not a scattered subset: they are
\emph{all four} runs recorded under one of those copies, and a second small copy
does not break the tie --- so revision and co-tenancy cannot be separated by any
comparison in our data. We report the confound rather than resolve it. The
re-runs changed the contention windows and the controller revision together.

The copy most arms ran under is still on the measurement host, so its divergence
from the repository can be re-derived rather than trusted: it differs in two
places --- it runs single-flight on the first queue entry rather than scanning
the whole queue, and it writes the candidate's own context above the floor it
logs as \texttt{base}. The narrow experiment now exists and the paper reports it:
same copy, that one expression changed, and it is the arm that crosses the line.
Its own comment records what the expression removed: when the head of the queue
is too large to fit, it blocks every smaller session behind it while the engine
idles.

One reservation applies to that comparison: the harness scripts that launch the
runs are not identical --- the baseline repeats and the scan arm record a
different hash of it, as do the two \texttt{horizon}=2 runs and the two
single-flight-off runs (the scan arm's own repeat records the same one). Earlier
versions were overwritten in place, so we can neither diff them nor show the
launcher changed nothing else. The recorded parameters and build do match the
repository, and the controller source differs only in the expression and a
comment block named above.
""")

# ---------------------------------------------------------------- S8 七条撤回
S.append(r"""\section{The seven retractions, with their evidence}

Each entry names where it can be checked; several are checkable directly against
a data file, and one against a generator's own run-time assertion. The audit
files themselves are working records, not authorities.

\begin{enumerate}
\item \textbf{The denominator of the step cost.} The old rule divided $\tau$ by
the whole-run mean running count while multiplying by busy time. The two errors
cancelled, so the two measurement methods appeared to agree. The bias is exactly
the run's idle fraction --- $36.3\%$ for \texttt{cap1}. \texttt{decomp.csv}
carries the four columns that recompute it.
\item \textbf{A median-based reading of the tool wait.} The old conclusion rested
on a median of $0.34$\,s and concluded that sessions never leave the engine. The
demanded mean is $15.82$\,s, the maximum $300$\,s, and $18.0\%$ of the $799$
round transitions wait more than ten seconds; the controller's run measures
$16.85$\,s. \texttt{toolwait.csv} carries all three denominators.
\item \textbf{An oracle-monotonicity claim.} It rested on an arm later shown to be
implemented incorrectly, and that arm may not be cited. The rewrite was never
re-run, so the monotonicity is \emph{unmeasured}.
\item \textbf{Double charging in the accounting.} The old rule added
\texttt{pausing\_tokens} on top of \texttt{measured}, charging twice for sessions
already in the engine. It is falsified not by argument but by a log:
\texttt{measured} $97{,}180$ plus \texttt{pausing} $15{,}700$ is $112{,}880$,
above the pool of $101{,}432$, and the engine cannot hold more unreclaimable KV
than the pool.
\item \textbf{A monotone idle-rate claim.} The old text said the idle share falls
monotonically with concurrency. On the busy-conditional convention, the arm with
no gate and no reservation idles $20.7\%$ at $\overline{R}_{\mathrm{busy}}=1.68$
while \texttt{cap4} idles $10.4\%$ at $1.65$ --- more concurrency, less idle.
\item \textbf{A refutation that was itself refuted.} An early revision dismissed
the eviction-then-recompute mechanism with two checks that were each wrong: the
ratio of total prefill tokens to planned prefill is $1.00$ by construction,
because \texttt{prompt\_tokens\_total} includes the cached part, so it cannot
detect recomputation; and ``no withdrawals'' reported by the engine counts
mid-flight preemption of running requests, not radix eviction.
\item \textbf{An inverted audit predicate.} The stall audit required
\texttt{valve} to be true, while in the logs \texttt{valve} true means the valve
\emph{is} holding admissions --- so the windows it reported were the valve
working as designed. Measured inside one run, $0.5\%$ of cycles admit when the
valve is true against $9.8\%$ when it is false. Corrected, one arm has one
window, $166.6$\,s, $0.93\%$ of the sampling span. The direction is asserted at
run time by \texttt{gen\_stall.py}.
\end{enumerate}
""")

# ---------------------------------------------------------------- S9 idle 分解
dec = load("decomp.csv")
if dec:
    S.append(r"""\section{Per-run idle decomposition}

The paper reports that the remedy for idle time works and does not pay: it is
not what improves the criterion. The per-run decomposition behind that is below.
The identity is $\mathrm{span} = \mathrm{idle} + \mathrm{busy}$, not
$\mathrm{wall} = \mathrm{idle} + \mathrm{busy}$: the sampler starts before the
requests and stops after them, so the wall clock is short by an offset that
differs per arm.

The structural remedy --- giving the engine work to do during a wait --- is what
the single-flight-off arm tests; it reduces idle and does not move the criterion.
""" + table([r for r in dec if r.get("run")], [(k, k.replace("_", " "))
                                                for k in dec[0].keys()]))

# ---------------------------------------------------------------- S10 脚本与数据
S.append(r"""\section{Scripts, data files, and the five independent checks}

Every number in the paper has a row in one of the data files under
\texttt{paper/data/}. Front and signed distances are recomputed from the raw
per-step logs over a full-precision run table; the criterion is recomputed from
its own elasticity generator. Each data file is produced under
\texttt{scripts/lab/} from the raw per-run logs
(\texttt{steps.jsonl}, \texttt{summary.json}, \texttt{metadata.json},
\texttt{metrics.csv}, \texttt{controller.jsonl}, \texttt{admissions.jsonl}).
Two of the generators write two files each, and three files --- the co-tenancy
ledger and
the two completion-counted tables --- are carried rather than regenerated,
because their content depends on which runs had finished when they were
produced.

Five quantities the paper turns on are re-derived by five checks that share no
code with the generators, each reproducing the table it checks:

\begin{itemize}
\item front and signed distance (\texttt{independent\_frontier\_check.py});
\item the segmented elasticity (\texttt{independent\_elasticity\_check.py});
\item the per-arm attribution (\texttt{independent\_attribution\_check.py});
\item the busy/idle decomposition (\texttt{independent\_decomp\_check.py});
\item realized reuse against the trace's bound
(\texttt{independent\_realization\_check.py}).
\end{itemize}

\texttt{scripts/lab/regen\_all.sh} regenerates every data file from the raw logs
in a temporary copy of the tree and compares the result byte for byte against the
delivered files; it does not write to the delivered tree. Three files are carried
as frozen inputs rather than regenerated --- the co-tenancy ledger and two tables
whose content depends on which runs had finished when they were produced --- and
the script says so where it skips them.

The consistency checker runs several hundred assertions over the paper, the supplement and
the data files. Its exit status is the deliverable: every number quoted in the
text must be found, and a value that no longer matches its data file is a
failure.
""")

# ---------------------------------------------------------------- S11 池子偏短
S.append(r"""\section{Pool shortfall and comparability}

Every run is guarded: a pool that does not come out at $101{,}432\pm20$ voids the
run rather than recording it. The pool can come out short because the engine
rounds the KV pool down to a multiple of its page size and because a share of the
pool is reserved before the trace starts; a short pool is not a smaller
experiment but a different one, since occupancy is quoted as a share of the pool
and the admission decisions compare a projection against a budget derived from
it. On the second accelerator three runs came up off the nominal $983{,}728$ ---
$971{,}456$, $943{,}541$ and $983{,}697$ --- and none of the three affects the
column it is used for.
""")

# ---------------------------------------------------------------- 组装
tex = r"""\documentclass[10pt]{article}
\usepackage[a4paper,margin=1in]{geometry}
\usepackage{booktabs,array}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[hidelinks]{hyperref}
\usepackage{pdflscape}
\usepackage{longtable}
\usepackage{parskip}
% ⚠ 收官前实测有一条段落 Overfull（45.8pt，`\texttt{}` 长路径断不开）⇒ 允许松排。
\sloppy
\emergencystretch=2em
\newcommand{\sys}{Foyer}
\title{Supplement to\\``When Does Admission Control Pay?\\The Memory Tier Sets the Cost of Concurrency in Agentic LLM Serving''}
\author{Anonymous Submission}
\date{}
\begin{document}
\maketitle
\noindent\textbf{Scope.} This supplement carries the readings, the audit forensics,
the version history and the retraction record behind the paper. The paper is
self-contained: nothing here is needed to follow its argument, no claim rests on
material that appears only here, and nothing here extends the paper's claims.
\medskip
""" + "\n\n".join(S) + "\n\\end{document}\n"

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "supplement.tex"), "w", encoding="utf-8").write(tex)
print("wrote %s/supplement.tex  %d bytes" % (OUT, len(tex)))
# 匿名性自检
bad = [w for w in ("xbw", "Bowen", "github", "gitlab", "zenodo", "http") if w.lower() in tex.lower()]
print("匿名性自检:", "✅ 干净" if not bad else "⚠ 含 %s" % bad)
# ⚠ 编译后必须查 Overfull —— 这次被裁掉的列就是这么漏的（主论文的卫兵读 main.log，看不到这里）
print("下一步: cd %s && pdflatex supplement.tex (两遍)，然后" % OUT)
print("        grep -c Overfull supplement.log   # 必须为 0")
