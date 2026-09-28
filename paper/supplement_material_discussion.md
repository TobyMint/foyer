# 外移材料 —— `sec_discussion.tex`（§Related Work / §Discussion / §Conclusion）

本文档收集 2026-09-27 为适配 **RTAS 2027 技术正文 11 页硬限**，从
`paper/sec_discussion.tex` **整块移出**的原文。移出范围经协调人 2026-09-27 裁决
（六个块、按优先级）授权。

⚠ `\section{Load Dependence}` **一个字未动**（协调人已另行处理；改前改后均为 514 词）。
⚠ **2026-09-27 追加更新（在本文档写成之后）**：`\section{Load Dependence}` 已按
codex 2026-09-27 裁决第 1、2 条**整节删除**（含 `tab:tier25` 与「aggressive end 在
轻载/重载下符号相反」这条主张），逐字原文见**本文档末尾「块 7」**。上面那句
「一个字未动」、下面表格里的「§Load Dependence（未动）| 514 | 514 | 0」一行，
以及「`\section{Load Dependence}` 段逐字相同」一句，都只描述**本文档写作当时**的状态，
现已作废 —— 留在这里是为了让数字账（3375 → 2709）仍然可复算。

**移出纪律（本项目硬规矩）**：每一条都写明「**值现在在哪**」—— 标出该段承载的数字
是否在论文别处仍有出处。凡写不出「现在在哪」的，一律按「该恢复」处理。

**词数账**（排版口径，与 `check_paper_numbers.py` 的摘要守卫同口径）：

| 块 | 改前 | 改后 | Δ |
|---|---|---|---|
| §Load Dependence（未动） | 514 | 514 | 0 |
| §Related Work | 315 | 297 | −18 |
| §Discussion | 2113 | 1477 | −636 |
| §Conclusion | 433 | 421 | −12 |
| **合计** | **3375** | **2709** | **−666** |

本文档逐字收录 26 个移出单元、**610 词**（含一张**整表**：阈值敏感性表，123 词）。
其余 **56 词** 是**逐句改写的措辞**（不是外移）—— 因此总账是 −666，而本文档逐字收录的是 610。

**未移出（明示保留）**：
- 每一条局限的**主张与限定语**（10 条）全部留在正文，只移读数（见块 2）；
- `\emph{Seven claims were retracted ...}`（七条撤回清单）：`sec_intro.tex` 有
  「we report the seven claims we had to retract」指向它，移出会使该指代悬空；
- `\paragraph{Why published gains do not reappear.}`（173 词）：不在裁决清单内；
- §Conclusion 与 §Related Work 的**主张与全部限定语**：§Related Work 零外移；
  §Conclusion 只外移一个 6 词的同义重述从句；
- 全部 `\cite{}` / `\ref{}` / `\label{}` / `\paragraph{}` / `\section{}`：**逐命令计数实测**，
  一个未丢 —— `\cite` 10→10、`\ref` 22→22、`\label` 5→5、
  `\paragraph` 6→6、`\section` 4→4（§Related Work 的 18 个 cite key 全部在场）；
  `\section{Load Dependence}` 段**逐字相同**（3284 字节）。

**机械自查（本文件的判据）**：本文档中每一段「原文（逐字）」在改后的
`sec_discussion.tex` 里 **0 命中**（26/26 命中本文档）。复算脚本：
`/tmp/extract_moved.py`。

---

## 块 1：§Reproducibility 的取证细节（5 单元 / 143 词）

**原文位置**：原 `\paragraph{Reproducibility.}` 的 `\emph{Co-tenancy ...}` 与
`\emph{The controller artifact.}` 两小段。

**移出理由**：协调人裁决「正文只留：审计存在、14 条被标记、4 条被杀、标记是风险提示
不是损害测量、τ₂ 的关键读数、四条已重测且无受损行残留、版本混杂的陈述」，其余外移。
**注**：协调人点名的「共租审计的**窗内对照**」（cap1 的 20.3--20.9 → 21.3/27.1/21.1、
t85 的 29.8 → 22.3--22.6、rl99 的 32.4 → 25.2/25.1）**在本次改稿之前就已经外移**
（见 `supplement_material.md` S1），因此本文档不再收录。

**正文留下的衔接**（改后仍在正文）：`An audit flags every run that overlapped three or
more others for at least an hour: fourteen are, and the incident that created those
windows killed four runs outright, none of which appears in our tables. ... We state
the confound rather than a resolution: the recorded parameters and build do match the
repository, but the copy most of our arms ran under diverges in two places, so
§\ref{sec:results:idle-memory} tests the fix plus a looser admission rate, not
the fix as written, and the launcher hashes are ones we can neither diff nor certify.
The supplement gives the version history.`

### 1.6 Artifact 说明：正文 §Reproducibility 原来点名的那些文件

**背景**：作者反馈「一般来说论文中不会给出具体的代码文件的名字吧？一般都是给一些
伪代码这样啊」。正文 §Reproducibility 原来逐字点名 `scripts/lab/frontier.py`、
`scripts/lab/gen\_table.py`、`gen\_elasticity` 两个脚本、`paper/data/`，本节把它们
**移出正文**（正文改成功能描述：「recomputed from the raw per-step logs over a
full-precision run table」「its own elasticity generator」「one of our data files」），
并在正文里留了一句指向本节的指针（"The supplement names those scripts and data files"）。
**「每个数字可追溯」这条没有丢** —— 追溯路径（功能 ↔ 实现文件 ↔ **逐条输入**的对照表）
现在放在**主 supplement `paper/supplement_material.md` §S9**。

> ⚠⚠ **2026-09-27（codex r54 复核 C/D）**：这张表原来只在本文件里（外移工作记录），
> 而本文件是**工作记录**、不是投稿附件 —— 审稿人按正文那句
> *The supplement names those scripts and data files* 去找**找不到**。
> 已**整表移进 `supplement_material.md` §S9**，本处**只留指针、不复制**：
> 两份表一定分叉（本项目「口径一致不能写在注释里」是同一条）。
> 同一轮还补齐了表里三处漏项（`gen_table.py` 的必需输入 `runs.csv`、
> 弹性脚本的 `arm_running.csv`、`frontier.py` 的硬编码锚点）—— 逐条走实现读的文件，
> 不看 docstring 摘要。

**仍然留在正文里的**：7 处 `\texttt{*.csv}` 数据文件指针（`decomp.csv` / `reuse.csv` /
`occupancy.csv` / `attribution.csv` / `stall.csv` / `slice23.csv`）。它们是**数据**指针
不是**代码**指针，而且是「这个数是哪来的」的定位手段，所以按作者反馈的原意保留。

### 1.1 审计集合的 12 + 2 拆分

**原文位置**：`\emph{Co-tenancy on the measurement host.}` 首句。

**移出理由**：集合口径的细节；正文保留「fourteen are」与四条被杀。

**原文（逐字，11 词）**：

```latex
twelve on the main trace and two on the moving-load one
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 数据出处（整块）：`paper/data/concurrency.csv`。

### 1.2 「窗口可查」那句

**移出理由**：披露做法本身保留在正文（「we keep the flag on the one undamaged row
rather than quietly dropping it」），理由从句外移。

**原文（逐字，12 词）**：

```latex
so a reader can see which window each number was measured in.
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 数据出处（整块）：`paper/data/concurrency.csv`。

### 1.3 控制器副本与仓库的差异（22 行、两处 + 单飞 + `base`）

**移出理由**：协调人裁决只留「版本混杂的陈述」。正文保留了对这一块的点名衔接
（「the copy most of our arms ran under diverges in two places」）。

**原文（逐字，42 词）**：

```latex
is still on the machine, and its divergence from the repository is 22 lines in two places: it runs single-flight on \texttt{waiting[:1]} where the repository copy scans the queue, and writes the candidate's own context over the floor the log calls \texttt{base}.
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 此单元是**源码差异**的取证，出处是两份 `controller_budget3.py` 的 diff（22 行、两处），不是数据文件。
- 数据出处（整块）：`paper/data/（无 CSV；两份源码 diff：`scripts/controller_budget3.py` vs 实验机工作副本）`。

### 1.4 launcher 哈希：不同代、已就地覆盖、既不能 diff 也不能证明

**移出理由**：协调人裁决只留版本混杂的陈述；正文保留了「the launcher hashes are ones
we can neither diff nor certify」这一限定语。

**原文（逐字，65 词）**：

```latex
A wider caveat covers the comparison the paper turns on: the harness script that launches a run is not the same across it---the base's repeat and the scan arm record different hashes of it, as do the pairs of \texttt{horizon}=2 and \texttt{single-flight off} runs---and the earlier revisions were overwritten in place, so we can neither diff them nor certify that the launcher changed nothing else.
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 数据出处（整块）：`paper/data/runs.csv（`code` 字段记录的 harness 哈希）`。

### 1.5 控制器源码差异那一处（+ 注释块）

**移出理由**：与 1.3 同源（原文的 1.4 已因「回填」撤单）；正文保留了「the recorded parameters and build do match
the repository」这一半披露。

**原文（逐字，13 词）**：

```latex
the controller source differs by the one expression above plus a comment block.
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 数据出处（整块）：`paper/data/（无 CSV；两份源码 diff）`。

---

## 块 2：§Limitations 的读数（16 单元 / 228 词）

**原文位置**：原 `\paragraph{Limitations.}`（632 词）。

**移出理由**：协调人裁决「每一条局限都要保留（负结果论文的信任基础），但每条压到一句」。
**主张与限定语全部留在正文**（改后 **375 词**、6 句），移出的是**支撑读数**。

**正文留下的衔接**（改后仍在正文）：条目式的六句 —— 一条 7B 模型 / 只重复了九个配置 /
**front 是插值不是实测策略** / 池子只有约四个会话 / 负载平稳单一 / 下一步；每一句都带着
原有的限定语（`we could not get clean`、`not a measured policy`、`stricter is not the
same as valid`、`we cannot exclude`、`would not by itself establish`、`may not hold`、
`indicative only`、`not the quality of the choice`、`gives us no result`、`not evidence
that adaptivity pays`、`unusable as controls`）。

### L1 no-control 行

**原文（逐字，5 词）**：

```latex
is that tier's no-control baseline
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 该行是 A100 那一档「没拿干净」的那一条 —— **行名本身**外移，正文保留了「one row there we could not get clean」。
- 数据出处（整块）：`paper/data/a100.csv`。

### L2 承重框句

**原文（逐字，13 词）**：

```latex
One boundary is load-bearing enough to state here and not only in \S\ref{sec:bg}:
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 框句本身外移；`\S\ref{sec:bg}` 指向**已回填**（改后为「not a measured policy (\S\ref{sec:bg})」）—— 实测 `\ref{}` 全局 **22 处 → 22 处**，`\ref{sec:bg}` **4 处一处未少**。
- 数据出处（整块）：无数据文件（源码 diff / 叙述 / 措辞）。

### L3 更严的对照读数

**原文（逐字，32 词）**：

```latex
the closest controller's two runs sit $+5.8$ and $+6.8$\,pp \emph{above} the nearest static \emph{anchor below them in wall clock}, where the line they are judged against puts them at $-0.3$ and $+0.2$\,pp---
```

**值现在在哪**：
- `5.8`：该值在 sec_background.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/gate_attrib.csv`。
- `6.8`：该值在 sec_background.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/gate_attrib.csv`。
- `-0.3`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/arrival_slo.csv`。
- `0.2`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/gate_attrib.csv`。
- 这 4 个数由「换成最近**已跑过**的静态锚点」重算得到，处置记录见 `docs/finding_review_r48_disposition_20260927.md`。
- 数据出处（整块）：`paper/data/runs_precise.csv`。

### L4a 分时切片的理由

**原文（逐字，11 词）**：

```latex
time-slicing two caps approximates any point on the segment between them,
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 插值为何可以当基线的**理由**（时间片可逼近线段上任意点）。
- 数据出处（整块）：`paper/data/slice23.csv`。

### L4b 「线是上界」那句

**原文（逐字，14 词）**：

```latex
and it is the direction that makes the line an \emph{upper} bound on switching
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 限定语「the line is an \emph{upper} bound on switching」随本单元外移。同句的「$0.89$\,pp 下方 / tie band / one point」已**回填**到正文（因为 `check_paper_numbers.py` 有三条守卫针对它：`§VII 时间片 run 的 Δ`、`§VII「一个点不是整段」的限定`、`§II 时间片 run 在下方`）。
- 数据出处（整块）：`paper/data/slice23.csv`。

### L5 9.7x 池与快一线

**原文（逐字，29 词）**：

```latex
at $9.7\times$ the pool the tier mechanism behaves as the premise predicts, and the controller clears the static sweep there by a hair rather than by its admission decisions
```

**值现在在哪**：
- `9.7`：该值在 sec_xtrace.tex、main.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/projection.csv`。
- 限定语「by a hair rather than by its admission decisions」随本单元外移（**这句话本身是一处限定**，请见本文末「离 2,300 还差多少（需要协调人裁决）」）。
- 数据出处（整块）：`paper/data/projection.csv / wall_split.csv`。

### L6 两次尝试的状态

**原文（逐字，12 词）**：

```latex
(the first used only as indicative, the second unusable and not reported)
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 「the first used only as indicative, the second unusable and not reported」——`indicative` 这一限定语**仍在正文**。
- 数据出处（整块）：`paper/data/a100_baseline.csv`。

### L7 共租抬高基线

**原文（逐字，9 词）**：

```latex
: co-tenancy inflates a baseline rather than flattering it.
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 解释性从句（「共租抬高基线而不是美化它」）；正文保留了 `indicative`。
- 数据出处（整块）：无数据文件（源码 diff / 叙述 / 措辞）。

### L8 变负载 trace 设计

**原文（逐字，16 词）**：

```latex
a trace whose load moves mid-run, with a static cap on each tier and a switcher
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 实验设计描述（动负载 + 每档静态 cap + 切换器）。
- 数据出处（整块）：无数据文件（源码 diff / 叙述 / 措辞）。

### L9 出乎意料的原因

**原文（逐字，16 词）**：

```latex
for a reason we have to state plainly because it is not the one we expected.
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 「for a reason we have to state plainly because it is not the one we expected」是**叙述**，不是限定。
- 数据出处（整块）：无数据文件（源码 diff / 叙述 / 措辞）。

### L10 static 模式不写队列事件

**原文（逐字，12 词）**：

```latex
in static-cap mode the runner admits immediately and writes no queue events,
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 根因（static 模式下 runner 立即放行、不写队列事件）。
- 数据出处（整块）：`paper/data/stall.csv`。

### L11 基线领先量 14.2--14.9

**原文（逐字，7 词）**：

```latex
(14.2 to 14.9 minutes, one per run)
```

**值现在在哪**：
- `14.2`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/decomp.csv`。
- `14.9`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- 「14.2 to 14.9 minutes, one per run」是**证据**；正文保留了「the run-to-run spread of one configuration and not evidence that adaptivity pays」。
- 数据出处（整块）：`paper/data/decomp.csv`。

### L12 重建未重跑

**原文（逐字，12 词）**：

```latex
we rebuilt and offline-validated the signal but have not re-run the experiment.
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 状态句（信号已重建并离线验证、实验未重跑）；⚠ 属本项目「时点词」一类，若将来重跑，此处与本文件都要更新。
- 数据出处（整块）：无数据文件（源码 diff / 叙述 / 措辞）。

### L13 var_cap3 158/271

**原文（逐字，20 词）**：

```latex
\texttt{var\_cap3} spent 158 of its 271 minutes at four or more concurrent instances and \texttt{var\_cap2} is flagged as a watch---
```

**值现在在哪**：
- `158`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `271`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/gate_attrib.csv`。
- 「两次尝试的基线不可用」的**证据**；正文保留了「the baselines are unusable as controls」。
- 数据出处（整块）：`paper/data/gate_attrib.csv`。

### L14 诚实立场句

**原文（逐字，20 词）**：

```latex
the honest position is that the variable-load case is measured and unusable, and the switched version of it is unmeasured.
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 「the variable-load case is measured and unusable, and the switched version of it is unmeasured」——**同一状态在 §Conclusion 仍有出处**（「is measured but not usable ... we report it as open rather than as a result」）。
- 数据出处（整块）：无数据文件（源码 diff / 叙述 / 措辞）。

---

## 块 3：§The threshold —— 阈值敏感性表与逐臂读数（3 单元 / 165 词）

**原文位置**：原 `\paragraph{The threshold decides the verdict, and we report that.}`
（429 词，含一张 `\begin{center}` 裸表）。

**移出理由**：协调人裁决「保留结论与关键数，敏感性分析的细节可移」。**整张表**（11 行 ×
5/10/20 s 三档）连同隔行读数外移；**结论与关键数留在正文**：

- 「the ordering of the static caps does not change, but where the controllers sit does」；
- 「at the loose end five cross」（五个越线的臂名 + 各自余量）；
- 「at the strict threshold ... above the line on **both** of its runs, by **+1.30** and
  **+2.16** pp，against the **0.5 to 4.6** pp that separates repeats of a single
  controller configuration」；
- 「the only arm above the line at all three thresholds and the only one whose repeat
  confirms it」；
- 「Three of the five that cross at the loose end are single measurements their own
  repeats contradict」；
- 「neither a verdict on admission control nor a single-run anomaly」+ 「We state the
  conditional version in the abstract」。

**正文留下的衔接**：原句「this **table** is where the condition bites」改为
「this is where the condition bites」（表外移后指代消失），并在段末加
「the per-arm re-derivation is in the supplement」。

**⚠ 表无 `\label`**：它原本是 `\begin{center}` 裸表，全稿没有任何 `\ref` 指向它，
外移**不产生悬空引用**（实测编译：0 undefined reference）。

### 3.1 整张阈值敏感性表（123 词）

**移出理由**：它就是「敏感性分析的细节」（逐臂 × 三档）。

**整张表由 `paper/data/slo_sensitivity.csv` 生成**：CSV 存多位小数、表按 1 位小数印，所以下面逐值扫描会出现「见备注（非数据文件）」—— **不是没出处**，是精度不同（本项目记过：`has()` 分不清 `1.6` 与 `1.60`）。

**原文（逐字，123 词）**：

```latex
\begin{center} \small \setlength{\tabcolsep}{4pt} \begin{tabular}{lrrr} \toprule SLO threshold & 5\,s & 10\,s & 20\,s \\ \midrule scans the queue & $-0.9$ & $+1.3$ & $+1.4$ \\ scans the queue (2nd run) & $+1.2$ & $+2.2$ & $+2.4$ \\ \texttt{horizon}=2 & $-1.7$ & $-0.3$ & $+1.0$ \\ \texttt{horizon}=2 (2nd run) & $-1.1$ & $+0.2$ & $+0.5$ \\ \texttt{horizon}=1 & $-2.8$ & $-0.9$ & $+1.5$ \\ \texttt{horizon}=1 (2nd run) & $-6.8$ & $-5.6$ & $-2.3$ \\ \texttt{horizon}=1 (3rd run) & $-7.0$ & $-3.2$ & $-0.03$ \\ \sys{} base & $-2.3$ & $-1.2$ & $+0.6$ \\ \texttt{bres} & $-3.6$ & $-1.3$ & $+0.3$ \\ single-flight off (2nd run) & $-2.6$ & $+0.1$ & $+2.0$ \\ Concur-style AIMD & $-16.2$ & $-12.7$ & $-8.5$ \\ \bottomrule \end{tabular} \end{center}
```

**值现在在哪**：
- `-0.9`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `1.3`：该值在 main.tex、sec_discussion.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/decomp.csv`。
- `1.4`：该值在 sec_discussion.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/decomp.csv`。
- `1.2`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/gate_attrib.csv`。
- `2.2`：该值在 main.tex、sec_discussion.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/nocontrol.csv`。
- `2.4`：该值在 sec_model.tex、sec_discussion.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/gate_attrib.csv`。
- `-1.7`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-0.3`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/arrival_slo.csv`。
- `1.0`：该值在 sec_intro.tex、sec_criterion.tex、sec_xtrace.tex、sec_background.tex、sec_results.tex、sec_discussion.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/decomp.csv`。
- `-1.1`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `0.2`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/gate_attrib.csv`。
- `0.5`：该值在 sec_results.tex、sec_discussion.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/gate_attrib.csv`。
- `-2.8`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-0.9`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `1.5`：该值在 sec_criterion.tex、sec_discussion.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/gate_attrib.csv`。
- `-6.8`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-5.6`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-2.3`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-7.0`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-3.2`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-0.03`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-2.3`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-1.2`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/arrival_slo.csv`。
- `0.6`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/gate_attrib.csv`。
- `-3.6`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-1.3`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/arrival_slo.csv`。
- `0.3`：该值在 sec_background.tex、sec_results.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/replicates.csv`。
- `-2.6`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `0.1`：该值在 sec_intro.tex、sec_xtrace.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/elasticity_x.csv`。
- `2.0`：该值在 sec_discussion.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/gate_attrib.csv`。
- `-16.2`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-12.7`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-8.5`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- CSV 存多位小数、正文印 1 位 —— 因此本文件按**正文精度**照抄，复算请看 CSV 原值。
- 表的三个列头（`5\,s` / `10\,s` / `20\,s`）与行名（`scans the queue`、`horizon}=2` 等）是 `check_paper_numbers.py` 的 §VI 阈值表守卫（9 条）的锚点 —— 表外移后这 9 条守卫会静默失锚，**需要把守卫指向本文件或退役**（见文末「守卫影响」）。
- 数据出处（整块）：`paper/data/slo_sensitivity.csv`。

### 3.2 越带余量 1.16 / 0.30

**移出理由**：「the crossing reproduces」这一结论留在正文，余量读数外移。

**原文（逐字，15 词）**：

```latex
the repeat clearing the band by $1.16$\,pp where the first run cleared it by $0.30$.
```

**值现在在哪**：
- `1.16`：该值在 sec_results.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/elasticity_x.csv`。
- `0.30`：该值在 sec_intro.tex、sec_background.tex、main.tex、sec_results.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/frontier_split.csv`。
- 数据出处（整块）：`paper/data/slo_sensitivity.csv + repeats.csv（带内散布）`。

### 3.3 三条重复的读数（+1.49 / −0.03 / +0.49 / +0.98）

**移出理由**：正文保留了结论（「Three of the five ... are single measurements their own
repeats contradict」），逐条读数外移。

**原文（逐字，27 词）**：

```latex
\texttt{horizon}$=1$'s repeats come in at $-2.3$, below the band, and $-0.03$, inside it; \texttt{horizon}$=2$'s at $+0.49$, inside it too; and \texttt{single-flight off}'s pair at $+0.98$, inside it.
```

**值现在在哪**：
- `-2.3`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `-0.03`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `0.49`：⚠ **改后全稿仅出现在本文件**；数据出处 见备注（非数据文件）。
- `0.98`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/elasticity_x.csv`。
- 数据出处（整块）：`paper/data/slo_sensitivity.csv`。

---

## 块 4：§The SLO metric —— 逐臂位移（2 单元 / 68 词）

**原文位置**：原 `\paragraph{The SLO metric excludes the controller's own cost, and we
checked.}`（285 词）。

**移出理由**：协调人裁决「保留结论（两种时钟下的判决方向），细节可移」。

**正文留下的衔接**（改后仍在正文）：口径（runner 从**提交引擎**起算 → 许可等待不可见）+
「all thirty-five 200-session runs ... on a ready-to-first-token basis」+ 「The correction
is large---every run that gates admission loses **0.4--19.5** pp of SLO, the tightest caps
queueing the hardest---but the direction of the verdict does **not** change」+ 「on this
clock **no** run is above the line」+ 「We do not claim the verdict is unchanged under
every SLO definition」+ 「the ready clock is the stricter of the two」+ 指向 supplement 的衔接。

### 4.1 十五 / 十九分组与四条更大的移动

**原文位置**：`\paragraph{The SLO metric ...}` 中段。

**原文（逐字，29 词）**：

```latex
fifteen of the nineteen controller arms move by no more than 2.5\,pp, the four that move more ($2.7$, $2.7$, $3.8$ and $8.2$\,pp) all stay below the front either way,
```

**值现在在哪**：
- `2.5`：该值在 sec_intro.tex、sec_background.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/replicates.csv`。
- `2.7`：该值在 sec_model.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/wall_split.csv`。
- `2.7`：该值在 sec_model.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/wall_split.csv`。
- `3.8`：该值在 sec_criterion.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/elasticity_x.csv`。
- `8.2`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/runs.csv`。
- ⚠ 这两条是 `check_paper_numbers.py` 的守卫 `§VI 移动 <=2.5pp 的臂数` 与
`§VI 移动 >2.5pp 的臂数` 的**锚点**（`move by no more than` / `move more`）—— 本单元外移后
这两条守卫会静默失锚（见文末「守卫影响」）。
- 数据出处（整块）：`paper/data/arrival_slo.csv（`move_pp` 列）`。

### 4.2 六条臂的 before→after

**移出理由**：逐臂位移的「细节」；正文保留了「the six that cross the ±1.0 pp band all
move toward the negative」。

**原文（逐字，39 词）**：

```latex
\texttt{horizon}=1 from $-0.93$ to $-1.88$, \texttt{horizon}=2 from $-0.30$ to $-1.89$ and its second run from $+0.22$ to $-1.25$, the queue-scanning arm from $+1.30$ to $-0.56$ and its repeat from $+2.16$ to $+0.96$, and \texttt{single-flight off} from $-0.55$ to $-1.43$.
```

**值现在在哪**：
- `-0.93`：该值在 sec_results.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/arrival_slo.csv`。
- `-1.88`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/arrival_slo.csv`。
- `-0.30`：该值在 sec_intro.tex、sec_background.tex、main.tex、sec_results.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/frontier_split.csv`。
- `-1.89`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/arrival_slo.csv`。
- `0.22`：该值在 sec_intro.tex、sec_background.tex、main.tex、sec_results.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/occupancy.csv`。
- `-1.25`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/elasticity_x.csv`。
- `1.30`：该值在 sec_results.tex、sec_discussion.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 见备注（非数据文件）。
- `-0.56`：该值在 sec_results.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/arrival_slo.csv`。
- `2.16`：该值在 sec_results.tex、sec_discussion.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/arrival_slo.csv`。
- `0.96`：该值在 sec_results.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/occupancy.csv`。
- `-0.55`：该值在 sec_results.tex 也出现（⚠ **是否同一量需人工核** —— 本项目有「同一个数在别处出现 ≠ 它用在了这里」的前科）；数据出处 `paper/data/arrival_slo.csv`。
- `-1.43`：⚠ **改后全稿仅出现在本文件**；数据出处 `paper/data/arrival_slo.csv`。
- 数据出处（整块）：`paper/data/arrival_slo.csv（`delta_ready_pp` 列，与 `table1.csv` 的 `delta_pp` 对照）`。

---

## 块 5：§Conclusion（433 → 421 词；1 单元 / 6 词）

**原文位置**：`\section{Conclusion}`。

**移出理由**：协调人裁决「压到 ~330，但不许删任何限定」。**本次只压措辞，没有读数外移**，
落在 **421 词**（不是 330）—— 差额见文末「离 2,300 还差多少」。

**逐条核对的两个方向都做过**：改后仍带全部限定语 —— `none of the nine variants we built
does`、`the strictest of the two baselines we could have used`、`and we say which`、
`a change to the release rule rather than to the admission decision`、`it is not the
binding one`、`They did not lose where concurrency was expensive, though that is not the
same as showing they could have won elsewhere`、`What we can say is narrower than what
we set out to say`、`neither dominated by any static point we measured nor dominating
one`、`an association ... rather than an intervention`、`returns no realization figure at
all`、`survive in direction and neither in level`、`measured but not usable`、`we report it
as open rather than as a result`。

**起草时的两处自我纠正（都已回填）**：第一处，
「admission policy sets how many requests are in flight, the per-step cost rises with
that number, and **the product is the wall clock**」压缩成两个分句 —— 那会把
「cancellation」的第三项（乘积）删掉，**已改回逐字原样**；第二处，「our **two-part** decomposition」一度被压成「our decomposition」—— `two-part` 是 `sec_intro.tex` 贡献清单里的**定义术语**（「We give a two-part decomposition of the wall clock」），**已改回**。

**唯一外移的从句**（C1）：它是 ε<1 的**同义重述**，不是新主张；同一推论由正文的「the elasticity staying below one across the operating range」直接承载。### 5.1 ε<1 的同义重述

**原文（逐字，6 词）**：

```latex
so added concurrency was still cheap.
```

**值现在在哪**：
- 本单元不含数字（纯限定语/衔接）。
- 数据出处（整块）：`paper/data/decomp.csv / elasticity.csv`。

---

## 块 6：§Related Work（315 → 297 词；**无读数外移**）

**原文位置**：`\paragraph{Related work.}` + `\emph{Realized} prefix reuse ...` 两段。

**移出理由**：协调人裁决「**保留全部 `\cite`**（一个都不能少），论述压紧」。
**9 个 cite key 全部在原位**（`talaria` `continuum` `thunderagent` `concur` `mori` /
`yu2022orca` `kwon2023pagedattention` `sarathi` `distserve` `mooncake` /
`yu2025pensieve` `gao2024cachedattention` `sun2024llumnix` `wu2026fastserve` /
`lin2024parrot` `wang2026xperf` / `zheng2024sglang` / `wang2025kvcachewild`），
**没有整块外移**，只有措辞压缩（−18 词）。

---

## 未移出但同属候选的两块

1. **`\paragraph{Why published gains do not reappear.}`（173 词）**：不在协调人裁决清单内，
   未动。它与 §Related Work 首句、§Model 的机制段有重叠，理论上可压 ~50 词。
2. **`\emph{Seven claims were retracted ...}`（110 词）**：`sec_intro.tex` 的
   「we report the seven claims we had to retract」指向它，且 `supplement_material.md`
   的 S3 明示「正文保留清单与一句话理由」，故未动。

## 离 2,300 还差多少（需要协调人裁决）

改后 **2709** 词（排版口径，改前 3375，−666）。距 2,300 目标还差 **409 词**。
剩余的可压空间**不在「读数」而在「主张与限定语」**，逐项如下（我没有动，因为协调人明示
「宁可少压 200 词，也不许删一个限定语」）：

| 候选 | 可压 | 代价 |
|---|---|---|
| `Why published gains ...`（173 → ~120） | ~50 | 与 §Related Work/§Model 重叠的复述 |
| `Seven claims ...`（110 → ~90） | ~20 | 撤回清单的措辞（内容不可删） |
| §Conclusion（421 → ~350） | ~70 | 要么删机制从句（但 `two-part decomposition` 是 `sec_intro` 贡献条所依赖的说法），要么删 1.79× 那个数 |
| §Limitations（375 → ~330） | ~45 | 只能压连接词，限定语不可动 |
| §Threshold 的五个越线臂名与余量（~55） | ~40 | 会让「五条越线」只剩一个计数 |
| §Related Work 剩下的论述（297 → ~270） | ~25 | 只能压连接词，cite 与限定语不可动 |

## 守卫影响（本次改稿**没有**改 `check_paper_numbers.py` —— 协调人限定只许改两个文件）

压缩会**静默关掉**锚在本节原文上的守卫（本项目已记过：「压缩会静默关掉守卫 —— 锚失配 =
那条检查不再检查任何东西」）。**实测对拍**（同一时刻、同一检查器、只换
`sec_discussion.tex` 一个文件）：

| | 总 MISS | 其中本文件 |
|---|---|---|
| 改前（`/tmp/sec_discussion.bak`） | 189 | 37 |
| 改后 | 207 | 55 |
| **净增** | **+18** | **+18** |

其他文件的 MISS 数**逐项相同**（`sec_results` 70 / `sec_model` 38 / `sec_xtrace` 26 / 全篇 17），说明这 18 条全由本次外移造成。
逐条点名（已写进上文各单元）：

| 失锚守卫 | 条数 | 原因 |
|---|---|---|
| `§VI 阈值表的 <run> 行`（scan / hz1 / hz1_r2 / hz1_r3 / hz2_r2 / hz2_r3 / hc / bres_r2 / aimd2_paper_r3） | 9 | 整张表外移（块 3.1）—— 建议把这 9 条改指向本文件 |
| `§VI 移动 <=2.5pp / >2.5pp 的臂数`、`§VI ready 时钟：控制器臂条数`、`§VI foyer_rg4 的 ready 位移` | 5 | 单元 4.1 外移（锚 `move by no more than` / `move more`） |
| `§VI 主 trace 上的 flag 条数`、`§VI 变负载 trace 上的 flag 条数` | 2 | 单元 1.1（12 + 2 拆分）外移 |
| `§VII var_cap3 的四条以上并发分钟数 / 窗口分钟数`（158 / 271） | 2 | 单元 L13 外移 |

**已经抢回来的守卫**（起草时一度失锚，重读守卫后**把原句回填或改回原措辞**）：

| 守卫 | 结果 |
|---|---|
| `§VI sf=0 那次测的是修复+更松的放行率`（`not the fix as written`） | ✓ 改回原措辞后复活 |
| `Limitations 里「这是本论文唯一的假设」`（`is an assumption`） | ✓ 句子回填后复活 |
| `§VII A100 基线的两次尝试`（`Both attempts at that baseline`） | ✓ 改成句首后复活 |
| `§VII 时间片 run 的 Δ`（0.89）与 `§VII「一个点不是整段」的限定` | ✓ 读数与限定语回填后复活 |
| `§VI ready 时钟：跨出 ±1pp 带的臂数` / `§VI ready 时钟下无臂越线` / `§VI 表【前】那句` | ✓ 一直在正文（未受影响） |

⚠ **另一类请注意**：检查器的 MISS 总数**本身会随时间漂移** —— 同一份
`sec_discussion.tex`（改前那份）在 11:03 跑出 **149** 项 MISS，在 11:5x 跑出 **189** 项。所以上表用的是
**同一时刻的 A/B 对拍**，不是两次历史跑的差。（这一类漂移本项目记过：「lab-only 的表会随
「实验机上有什么」漂移」「在跑的 run 会漏进」。）

### 一条未动但会亮的排版守卫

`这些源文件（.tex/.bib）的内容与上一次编译不一致` 会报 —— 因为本次按协调人要求用
**独立 outdir** 编译（`latexmk -outdir=/tmp/build`），树内的 `main.log` / `main.fdb_latexmk`
因此比 `.tex` 旧。在树内重编一次就消失（与本次改稿无关）。


---

## 块 7：整节删除 —— `\section{Load Dependence}`（502 词，连带 `tab:tier25`）

**原文位置**：`paper/sec_discussion.tex` 的 `\section{Load Dependence}\label{sec:load}`，
在本稿里是 §Related Work **之前**的一整节（含一张表）。

**删除理由（codex 2026-09-27 裁决第 1、2 条）**：这是**收缩主张范围**，不是「把证据藏进
supplement」。该节的唯一作用是主张「同一个控制器族的最激进一端在轻载与重载下符号相反
（+51% / −42%）」，而本项目 2026-09-26 自己核出**那两档动的不是同一个开关**
（200 档换了控制器并关掉 sf/sg；25 档的 target 从默认 0.75 改成 0.95）。
裁决要求：**连同定义、图表引用和讨论一起删**，并且不再声称那个符号反转。

**同批一并删掉的三处指向**（不删就会留下 `??` 或悬空所指）：

1. `sec_discussion.tex` §Limitations：「so `\S\ref{sec:load}` says what to expect when
   conditions differ, not what happens while they change」→
   「so we **cannot** say what happens while they change」（限定语加强，不是削弱）；
2. `sec_discussion.tex` §Conclusion：「The regime in which adaptivity should have paid …
   **is the light tier** …（`\S\ref{sec:load}`）」整句删除；
3. `sec_intro.tex` 贡献条：「We characterize when adaptivity *could* have paid …
   **worth $+51\%$ at 25 sessions and costs $-42\%$ at 200**（`\S\ref{sec:load}`）」
   整条删除（贡献从 5 条变 4 条）。

**值现在在哪**（一个数都没丢）：

| 被删的数 | 现在在哪 |
|---|---|
| 25 档四臂（32.4/1.95/92.8/11.0、24.2/2.77/91.2/5.1、23.6/3.39/79.2/21.4、27.6/2.47/92.8/7.1） | `paper/data/tier25.csv`（`gen_tier25.py` 生成） |
| 节流开关两档对照（58.4/95.2 与 28.8/92.8；291.3/89.8 与 415.0/46.1） | `paper/data/loadtier.csv`（`gen_loadtier.py` 生成） |
| 单变量分解 | `paper/data/tier25_old.csv`（`gen_tier25_old.py`，旧 harness，不可直比） |
| backlog 分析 | `paper/data/backlog.csv` |
| 本条主张在本项目的审计记录 | `paper/claims_audit.md` 的 C6/C7 两节（含「两档不是同一个开关」的复核） |
| 200 档全关臂那一行（415.0 / 2.58 / 46.1 / −47.10） | **仍在正文** Table I 的 `all throttles off` 行，且 §II 与 §V 仍引它 |

**正文保留、未受影响的限定**：§Limitations 里「The load is stationary, single-tenant and
single-SLO」以及「the experiment that would settle that gives us no result —— *the
switcher never fired*」两句**原样保留**（后者说的是变负载实验，不是 25 档）。

## 整节逐字原文（改前）

```latex
\section{Load Dependence}
\label{sec:load}

Adaptivity pays when conditions \emph{change}, and one stationary trace is where
a static cap should be near-optimal---the obvious objection to a negative result.
We agree, and test the weaker thing, two constant-load tiers.

The family's aggressive end reverses across tiers: on the 25-session tier a \sys{}
arm with the high-water off and a red line at 0.95 runs \emph{51\% faster} (58.4 to
28.8 minutes) for 2.4\,pp of SLO than the same controller at its default red line
of 0.75; on the 200-session tier an arm with three throttles off---and a
\emph{different} controller---costs 42\% (291.3 to 415.0 minutes) and 43.6\,pp of
SLO. The direction reverses, both effects around 40--50\%, but \emph{these are not
the same intervention on the two tiers}: light moves two knobs on one controller,
heavy swaps the controller and turns single-flight and the starvation guard off
too. The 25-session numbers come from an earlier harness batch---two consecutive
days, the same trace and pool, from before we recorded build hashes---and we never
ran the all-throttles-off arm on that tier under the current revision, so the
reversal is a direction across two harness generations, not a same-generation
paired comparison. Our same-generation measurement, Table~\ref{tab:tier25}, does
not contain that arm. The single-knob decomposition and the per-arm readings are in
the supplement.

\begin{table}[tb]
  \caption{The 25-session tier, all four arms from the harness revision
  that records build hashes (\texttt{run\_matrix.py}
  \texttt{a8605b1e77d5}); earlier 25-session batches are not comparable with
  these four. The segment SD here is over six segments, not the ten
  Table~\ref{tab:runs} uses, so the two tables' SD columns are not
  comparable.}
  \label{tab:tier25}
  \centering
  \small
  \setlength{\tabcolsep}{4pt}
  \begin{tabular}{lrrrr}
  \toprule
  Policy & Wall (min) & Conc. & SLO (\%) & Seg.\ SD (pp) \\
  \midrule
  cap2 & 32.4 & 1.95 & 92.8 & 11.0 \\
  cap3 & 24.2 & 2.77 & 91.2 & 5.1 \\
  cap4 & 23.6 & 3.39 & 79.2 & 21.4 \\
  \sys{} & 27.6 & 2.47 & 92.8 & 7.1 \\
  \bottomrule
  \end{tabular}
\end{table}

Where adaptive control should win it is a trade, not a defeat: \sys{} finishes in
27.6 minutes at 92.8\% SLO and \texttt{cap3} in 24.2 minutes at 91.2\%, so \sys{}
sits $+0.9$\,pp above the same-generation envelope while the static cap of three is
12\% faster and gives up 1.6\,pp of SLO---neither dominates the other. $+0.9$\,pp
is against a straight-line interpolation between static points, not a switching
policy on \emph{that} tier (we ran one on the main trace, \S\ref{sec:bg}), so the
defensible statement is that \sys{} is not dominated by any static point we
measured here---not that it beats what a static mix could achieve. Two scales stay
apart: $+0.9$\,pp on a tier of 125 requests is about one request, the $7.1$\,pp
spread in Table~\ref{tab:tier25} is across segments \emph{within} a run, not
run-to-run. We defend the weaker claim: on the low-load tier the controller is not
worse, and the aggressive end of this family is worth $+51\%$ there and costs
$-42\%$ at high load. The backlog analysis that follows from this tier, and why raw
queue length does not order the two tiers, is in the supplement.
```
---

# 第二轮外移（2026-09-27）：§VI 的两处复述（净移出 ~60 词）

**背景**：正文压到 11 页；改后实测 **12 页、参考文献标题在第 11 页、正文结束于第 11 页**。

## 块 D1：五条复算线点名的五个量（45 词）

**原文位置**：`sec_discussion.tex` 的 `\paragraph{Reproducibility.}`。

**移出理由**：codex 对 supplement 边界的裁定明写「五条复算流程可放 supplement」。
正文保留「五条互为独立的复算线、与生成器逐位相符」这一主张。

**原文（逐字）**：

```latex
and five quantities this paper turns on---the busy/idle split, the front and
signed distances, the realization accounting, the elasticities, the arm-by-arm
attribution---are re-derived by five checks sharing no code with the generators,
each reproducing the table it checks.
```

**正文留下的衔接**：

```latex
Every number has a row in \texttt{paper/data/}, and five quantities this paper turns
on are re-derived by five checks sharing no code with the generators, each
reproducing the table it checks. The supplement carries those checks, the audit
forensics, the per-arm numbers and the controller revision history.
```

**值现在在哪**：本块**不含读数**。**五条独立复算线**在
`scripts/lab/independent_frontier_check.py`、`independent_elasticity_check.py`、
`independent_attribution_check.py` 等（本仓库 `CLAUDE.md` 列了三条独立线）。
⚠ `check_paper_numbers.py` 有一条守卫只查字面短语 `five checks sharing no code`
落在 `sec_discussion.tex` 的**同一行**内；改写时若断行会让它报**假 MISS**（本轮踩过一次，已折回一行）。

## 块 D2：`We state the conditional version in the abstract`（15 词）

**原文位置**：`sec_discussion.tex` 的 `\paragraph{The threshold decides the verdict, and we report that.}` 末句。

**移出理由**：纯复述（抽象里本来就写着条件版本，且本段自己已给出 `+1.30` / `+2.16` 与
`0.5` 到 `4.6`）；保留 supplement 指向。

**原文（逐字）**：

```latex
We state the
conditional version in the abstract; the per-arm re-derivation is in the
supplement.
```

**正文留下的衔接**：

```latex
The per-arm
re-derivation is in the supplement.
```

**值现在在哪**：本块**不含读数**。条件版本仍在**摘要**（正文第 1 页）。
