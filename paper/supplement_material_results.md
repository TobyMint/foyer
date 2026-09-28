# 外移材料 —— `sec_results.tex`（§V Results: Four Routes, One Outcome）

本文档收集 2026-09-27 为适配 **RTAS 2027 技术正文 11 页硬限**而从 `paper/sec_results.tex`
**整块移出**的原文。移出按协调人 2026-09-27 的处置表执行（「`idle-memory` 的控制器内部
状态细节进 supplement」「第四路线（闸门）的细节可移」「Notes to Table I 的细节进 supplement」）。

**移出纪律（本项目硬规矩）**：每一条都写明「**值现在在哪**」——标出该段承载的数字/限定语
是否在论文别处仍有出处。凡写不出「现在在哪」的，一律按「该恢复」处理（见文末 ⚠ 一条）。

**改动总量**（原始串口径，`len(text.split())`）：
`sec_results.tex` 3{,}675 → **3{,}065** 词（−610，−16.6\%）；其中 **Table I 及其 caption 517 词
一字未动**（装配时按显式锚点 `\begin{table}[tb]` / `\end{table}` 逐字切出并断言词数 == 517）。
正文 15 页 → **13 页**，`??` 0 处，0 Overfull，0 Float too large。

**逐块词数**（同一口径；块边界 = `\subsection{...}` 与 `\paragraph{Notes to Table I}`）：

| 块 | 改前 | 改后 | Δ | 协调人目标 |
|---|---|---|---|---|
| The frontier | 989 | 913 | −76 | 861 |
| Table I + caption | 517 | 517 | 0 | 517（不许动） |
| Notes to Table I | 286 | 160 | −126 | 150 |
| The controllers leave memory unused | 694 | 445 | −249 | 400 |
| What the two mechanisms explain | 327 | 277 | −50 | 250 |
| Why the knobs do not help | 589 | 482 | −107 | 450 |
| An independent adaptive controller | 267 | 250 | −17 | 250 |
| **合计** | **3{,}669** | **3{,}044** | **−625** | 2{,}878 |

**没压到「合计 2{,}600」的原因（写在最前，免得被当成没做完）**：协调人处置表的逐块目标
**自身**相加 = 861+517+150+400+250+450+250 = **2{,}878**，不是 2{,}600；我落在 3{,}044，
比那张表高 **166 词（5.8\%）**。剩下的每一处都是**主张或限定语本体**，再往下压只能
**删主张**（候选与代价见文末「若要继续压缩」）。本文件的取舍按「宁可少压 200 词，
也不许删一个限定语」执行：**限定语 0 条被删**（5 条随块移出并在下面逐条标出）。

**正文新增的两处指向 supplement 的指针**（为满足 RTAS「正文必须自足」）：
idle 段 `(the projection's per-cycle readings are in the supplement)` 与
`(the blocked-cycle attribution is in the supplement)`。

**未移出（保留在正文）**：
- Table I 及其 caption、`\label{tab:runs}`（装配时有断言守卫）；
- 全部 `\cite{}` `\label{}` `\subsection{}` `\paragraph{}` `\footnote{}`；
- 「九条臂无一越过」「scan 臂是唯一越过的那条」「±1.0\,pp 打平带」「锚点重复把前沿移了两次」
  「无控制臂」「$W$ 非单调」「两类机制的分工与计数」「H\"older 归因判据」「四条路线的结论」
  「AIMD 不越线」——这些是本节的主张本体。

---

## 块 1：scan 臂的日志计数与源码差异

**原文位置**：原 `sec_results.tex` §*The frontier* 第 2 段（原第 27--31 行）。

**移出理由**：控制器源码差异的**取证读数**（逐 run 的周期数/放行次数），不是本段主张
（「改动是窄的」）本身；§VI 的 controller-artifact 段已承担同一件事的讨论。

**正文留下的衔接**：`Their own logs show the change to be a narrow one---one admission per
cycle, never two---and the source differs in that expression plus a comment block, though the
launcher differs too and we cannot diff its earlier revision (\S\ref{sec:discussion}).`
（**两个限定语 `never two` 与 `cannot` 都留在正文**。）

**原文（逐字）**：

```latex
Their own logs
show the narrower change---across 8{,}030 and 7{,}932 control cycles they admitted
one session per cycle 210 and 203 times, and never two---and the source differs in
that expression plus a comment block, though the launcher differs too and we
cannot diff its earlier revision (\S\ref{sec:discussion}).
```

**值现在在哪**：
- `8{,}030` / `7{,}932`（控制周期数）、`210` / `203`（逐周期放行一次的累计次数）：
  **全稿仅此一处** → 现只在本文件；数据出处为 `paper/data/gate_attrib.csv` 的
  `pois200_foyer_scan_r2`（`samples=7932`、`total_admits=203`）与 `foyer_scan`
  同名行，逐周期分布见 `controller.jsonl` 的 `n_admitted`（`max_per_cycle=1`）。
- 限定语 `never two`：**留在正文**；`cannot diff`：**留在正文**。

---

## 块 2：共租修正的逐臂旧读数

**原文位置**：原 §*The frontier* 第 3 段（原第 45--54 行）。

**移出理由**：四条臂「修正前 → 修正后」的**逐臂** Δ（八个数），属 §*Reproducibility*
审计的取证细节；本段主张（修正把四条拉近前沿但都没越过）仍完整留在正文。

**正文留下的衔接**：

```latex
Four of the nine carried the co-tenancy flag of Table~\ref{tab:runs} and have
since been re-measured alone (\S\ref{sec:repro}); the correction moved them
$11.2$, $6.5$, $6.4$ and $4.5$\,pp closer to the front. We do not read the four
as agreeing---they are four arms from one contamination window rather than four
independent replications---but even the largest correction leaves its arm below
the line.
```

**原文（逐字，被移出的部分）**：

```latex
so their flagged distances overstated how
far below the line they were: the correction moved the four by $11.2$, $6.5$,
$6.4$ and $4.5$\,pp (\texttt{horizon}$=1$ no hw from $-19.54$ to $-8.31$, the
resident base from $-7.81$ to $-1.33$, \texttt{horizon}$=0$ from $-13.60$ to
$-7.19$ and \texttt{horizon}$=2$ from $-4.81$ to $-0.30$).
```

（原句 `Co-tenancy inflates the step cost, which pushes an arm \emph{down},` 亦随本块移出；
正文保留了它的结论「修正把它们拉近前沿」。）

**值现在在哪**：
- 修正**后**的四个值 `-8.31` / `-1.33` / `-7.19` / `-0.30`：**仍在正文**（Table I 的四行）。
- 修正**前**的四个值 `-19.54` / `-7.81` / `-13.60` / `-4.81`：**全稿仅此一处**（正文已移出；
  Table I 印的是新值）。
- ⚠ **这四个旧值在 `paper/data/*.csv` 里 0 命中**（我把 47 个 CSV 逐个扫过）——
  可追到的只有 `paper/data/superseded.csv` 记录的**替代关系与污染原因**（如
  `foyer_bres → foyer_bres_r2`，note 写「τ₂ 被抬到 31.3\,ms（干净值 24.8）」），
  **旧 Δ 本身没有落盘**。按本项目「每个数字都要能追到文件」的纪律，这两条路可选：
  (a) 在 `superseded.csv` 补一列「旧 Δ」；(b) 把本句恢复回正文。**本次按协调人处置表移出，
  并把这条缺口标在这里，不做静默处理。**
- 限定语 `We do not read the four as agreeing` / `rather than four independent replications`：
  **留在正文**。

---

## 块 3：两个锚点重复的逐项读数

**原文位置**：原 §*The frontier* 第 5 段（原第 65--74 行）。

**移出理由**：锚点重复的**墙钟/SLO 逐项读数**（表 I 与 `table1.csv` 已有同值），
属取证；主张（前沿被移了两次、判决不变、我们取对我们不利的那次）仍完整在正文。

**正文留下的衔接**：

```latex
The anchor repeats moved the frontier twice, and we report both moves because a
frontier whose anchors are single measurements is the weakness this whole
subsection is about. \texttt{cap4}+HC's repeat came out both faster and higher on
SLO, displacing the first, and no controller verdict moves.
\texttt{cap3}+HiCache's repeat
is also faster and higher, and taking it moves our best arm from $+0.41$\,pp---nominally \emph{above} the
line---to $-0.30$\,pp. Both sit inside the $\pm1.0$\,pp band, so the verdict is a
tie either way; ...
```

**原文（逐字，被移出的片段）**：

```latex
 came out both faster (209.1 against
213.0 minutes) and higher on SLO (68.5 against 63.4)
```

```latex
 is also faster and higher
(230.3 minutes, 81.9\% against 236.4 and 81.1\%)
```

**值现在在哪**：
- `209.1` / `213.0` / `68.5` / `63.4`（`cap4_hc_r2` 与 `cap4_hc`）与
  `230.3` / `81.9` / `236.4` / `81.1`（`cap3_hc_r2` 与 `cap3_hc`）：
  **表 I 仍有同值行**（`cap4+HC (repeat)`、`cap4+HC`、`cap3+HC (repeat)`、`cap3+HC`），
  数据出处 `paper/data/table1.csv` / `runs.csv`（全精度在 `runs_precise.csv`）。

---

## 块 4：重复散布的九个值（脚注内）

**原文位置**：原 §*The frontier* 的 `\footnote{}`（原第 75--84 行）。

**移出理由**：九个配置各自的 SLO 全距**逐值**列在脚注里，是 `replicates.csv` 的一张表；
脚注主张（重复并不齐整、最宽的三条正是决定性的三条、暴露有界）**整句留在正文**。

**正文留下的衔接**：

```latex
\footnote{The repeats are uneven, and we do not want the tightest pair to stand
for all of them. Nine configurations have been run more than once, their SLO
spreads spanning 0.3 to 5.1\,pp, and the three widest belong to the three arms
that decide something, so where a small margin matters our repeats are weakest.
The asymmetry runs against the controllers: the envelope takes each anchor's
\emph{better} run where a repeat exists, while most controllers are a single run.
The exposure is bounded---the verdicts are set by the segment to
\texttt{cap2}+HiCache, whose repeats differ by 0.8 and 1.0\,pp, below the
$\pm1.0$\,pp band we judge in.}
```

**原文（逐字，被移出的片段）**：

```latex
Nine configurations have been run more than once; their SLO
spreads are 0.3, 0.5, 0.7, 0.8, 1.0, 1.0, 4.4, 4.9 and 5.1\,pp
(\texttt{replicates.csv}), and the three widest belong to the three arms that
decide something, so where a small margin matters our repeats are weakest.
```

**值现在在哪**：
- 九个全距（`0.3 0.5 0.7 0.8 1.0 1.0 4.4 4.9 5.1`）：**全稿仅此一处** → 现只在本文件；
  数据出处 `paper/data/replicates.csv` 的 `slo_range_pp` 列（九组，逐组可核）。
- 正文保留区间 `0.3 to 5.1\,pp`（两个端点仍在正文）与 `0.8` / `1.0`（cap2+HiCache 那一组）。

---

## 块 5：`Notes to Table~\ref{tab:runs}.` 的历史细节

**原文位置**：`\paragraph{Notes to Table~\ref{tab:runs}.}`（原第 160--183 行）。

**移出理由**：AIMD 前两次尝试的经过、被撤下 run 的分类清单、两条短 run 的**原因**、
五条带旗 run 的历史 —— 都是版本史/名单细节；本段的**披露本体**（第三条的墙钟可用、
二十一条未列、两条未满 999 步、‡ 是风险旗不是损害测量）全部留在正文。

**正文留下的衔接**（节选）：

```latex
The published-parameter AIMD row is
the third attempt and the first whose wall clock is usable, so its 326.8 minutes
and the $\Delta$ derived from it are the ones we report. Twenty-one further runs
on this trace are not listed, and where we cite any of them we name them. Two
\emph{rows of this table} stopped short of 999 (\texttt{rg4} 998 and the
no-control baseline 997); our verdict script excludes runs below 999 steps, ...
One row now carries it, \texttt{cap1}, and five more did in earlier versions;
\texttt{cap1} shows no aggregate inflation (20.6\,ms), so we keep its number and
say why. \S\ref{sec:repro} gives the audit.
```

**原文（逐字，被移出的片段）**：

```latex
the first carried
three contaminations recorded at the time and the second stalled at 989 of 999
steps, while the third runs under a supervisor loop the other two lacked and its
longest controller outage is 50\,s rather than 31 minutes
```

```latex
six budget-fraction and rate-limit arms, the three
matched-pair arms cited above, five superseded by the clean re-measurements of
\S\ref{sec:repro}, the four capacity-controlled runs of \S\ref{sec:model}, and
\texttt{cap1}'s clean re-run
```

```latex
each losing the tail of one session to a connection
error and a 600\,s stream idle timeout respectively
```

```latex
four of those five were damaged---their per-request decode interval running
30.9--33.3\,ms against 23.8--27.5 across the fifteen clean runs of the same
family---and have all been re-measured alone, while the fifth is the superseded
AIMD attempt.
```

**值现在在哪**：
- `989 of 999`、`50\,s`、`31 minutes`：**全稿仅此一处** → 现只在本文件；
  数据出处 `paper/data/aimd_stall.csv`（`steps=989`、`admit_gap_min=31.9`、
  `stall_gap_min=31.4`）与第二次尝试的 `INTERVENTION.md`。
- `600\,s`（流空闲超时）：**全稿仅此一处** → 现只在本文件；出处是 run 的
  `runner.out` / SGLang server 日志（`stream idle timeout`），无 CSV 落盘 —— 同块 2 的 ⚠。
- `30.9--33.3\,ms` 与 `23.8--27.5\,ms`（被污染 vs 干净的 τ₂ 区间）：**§VI 仍有同值**，
  且 `paper/data/concurrency.csv` / `decomp.csv` 有逐 run 值。
- `six` / `three` / `five` / `four`（那条清单的分组计数）：**全稿仅此一处** → 现只在本文件；
  集合可从 `paper/data/runs_precise.csv` + `superseded.csv` 现算。
- `998` / `997`（两条短 run 的步数）：**仍在正文**（同句）；`\texttt{rg4}` /
  `no-control baseline` 仍在正文。
- `20.6\,ms`、`\ddagger` 的定义、`five more have in earlier versions`：**留在正文**。

---

## 块 6：控制器内部状态 —— 投影的算术与逐列排序

**原文位置**：原 §*The controllers leave memory unused*（`sec:results:idle-memory`）
第 1--2 段（原第 188--209 行）。

**移出理由**：协调人处置表点名「**控制器内部状态的细节进 supplement**」。
本节的**论点**（占用量是策略输出不是约束；控制器以为自己快满了；投影是引擎自报占用的
1.79$\times$ 且不是设计常数）全部留在正文。

**正文留下的衔接**：

```latex
Our controller admits fewer sessions rather than discarding one, so its pool
occupancy is a policy output, not a constraint: the base configuration holds a
median 49.2\% of the pool while 66 sessions queue for admission, and the
configuration that finishes fastest is a poor fast end (\texttt{cap6}+HC, 28.9\%
on SLO). Occupancy and running requests track each other (\texttt{occupancy.csv},
Spearman $\rho=0.97$), but running count does \emph{not} order wall clock:
\texttt{cap5} and \texttt{cap4}+HC run 1.62 and 1.60 and finish 48 minutes apart.

The controller believes it is nearly full. It admits against a projection---the
largest of measured occupancy and the summed contexts of live sessions, plus a
reserve for their growth---that runs at a median 7.6\% free of its budget, while
its measured occupancy at the same instants leaves 48.2\% of that budget, or
50.8\% of the pool, idle. ...
```
⚠ 2026-09-27（r52 处置）：上面这段快照是**移出当时**的正文，此后正文又改过两处 ——
(1) 并列的示例从 `cap5`/`cap4`+HC 换成了 `cap3`+HC 与 `horizon`=1（并 `21 minutes apart`）；
(2) 投影的定义不再原地展开，改为 `It admits against a projection (Eq.~\ref{eq:proj})`。
**以现行正文为准**，本快照只记录移出那一刻。

**原文（逐字，被移出的片段）**：

```latex
it runs at a median of 49.2\% of
the pool on the base configuration, with a median of 66 sessions queueing for
admission, while the configuration that finishes fastest, \texttt{cap6}+HC at
207.8 minutes, is a poor fast end (28.9\% on SLO).
```

```latex
it runs at a median of 49.2\% of ... reliably---\texttt{occupancy.csv}'s two columns rank the
thirty-three arms we have almost identically (Spearman $\rho=0.97$)---but running
count does \emph{not} order wall clock: \texttt{cap5} and \texttt{cap4}+HC carry
almost the same all-samples mean running count, 1.62 against 1.60, and finish 48
minutes apart.
```

```latex
that runs at a median of 89{,}073 tokens against a
budget of 96{,}360, i.e.\ 7.6\% free, while its measured occupancy at the same
instants is 49{,}875 tokens: 48.2\% of that budget, or 50.8\% of the pool, is
idle.
```

```latex
it is 1.32 to 1.96 with an upper median of 1.75 across the
twenty-five controller runs that finished on this trace. Two terms produce it:
charging every live session its full context, when a parked session's KV is
evictable and so absent from the engine's count, and the growth reserve, which
alone is 26{,}762 tokens, 28\% of the budget.
```

**值现在在哪**：
- `89{,}073`（投影中位 token）、`96{,}360`（预算）、`49{,}875`（同刻实测占用）、
  `1.75`（ratio 上中位）、`26{,}762`（growth 中位）、`28\%`：**全稿仅此一处** →
  现只在本文件；数据出处 `paper/data/projection.csv`
  （`budget` / `proj_p50` / `occ_p50` / `growth_p50` / `ratio` / `free_pct` / `occ_pct_of_budget`
  逐列可核）。正文保留 `7.6\%` / `48.2\%` / `50.8\%` / `1.79$\times$` / `1.32 to 1.96`。
- `thirty-three`（占用表的臂数）、`almost identically`、`all-samples`：**全稿仅此一处** →
  现只在本文件；`paper/data/occupancy.csv` 行数即该集合。
- `1.62` / `1.60` / `48`（分钟）：**仍在正文**。
- 限定语 `does \emph{not} order wall clock`：**留在正文**。

---

## 块 7：不放行周期的闸门归因（forensics）

**原文位置**：原 §*The controllers leave memory unused* 第 4 段（原第 224--238 行）。

**移出理由**：这一段的取证对象是「**剩下的桶里是谁**」——八条臂的闸门中位占比、
`rg2`/`rg3`/`rg4` 的逐值、以及闸门开启的 3{,}700 个周期。本节的主张
（三条判据都过不了时是谁在设下限：**是饥饿保护，不是预算判据**）留在正文。

**正文留下的衔接**：

```latex
We then asked what actually stops it. A session is authorized only if the SLO
valve is open, the round gate is not full, and its projected footprint fits what
remains of the budget, and neither gate is what sets the floor: a starvation guard
that bypasses the budget once the oldest waiter has waited 240\,s is, and it
accounts for 24.8\% of the base run's admissions (51 of 206). It is the guard,
not the budget test, that sets the floor on how fast this controller can admit.
```

**原文（逐字，被移出的片段）**：

```latex
Over the base run's blocked cycles the valve accounts for
6.8\% and the round gate for none, the remainder being cycles where the controller
selected no candidate at all; the controller is single-flight by default, and
whether that gate held or a candidate was tried and did not fit is \emph{not
distinguishable from our logs}, so we do not attribute the bucket to either.
```

```latex
Across the eight \sys{} variants that log gate state, the projection is over
budget in a median 36.0\% of blocked cycles and the valve in a median 34.3\%,
against 32.2\% and 5.9\% over every completed run in that file (fifty of them);
the round gate binds in \texttt{rg2} (29.3\%) and \texttt{rg3} (18.0\%) but not in
\texttt{rg4} (0.6\%).
```

```latex
of 3{,}700 such cycles, nine admitted
```

**值现在在哪**：
- ⚠ **2026-09-27 第二次落地后**：全体集合从 50 条变 **52 条**（`foyer_scan_r3` 与
  `foyer_hc_slru` 落地），因此那套中位现在是 **33.2\%**（原 32.2\%）与 5.9\%，
  集合规模也变 52；八条臂那一组（36.0 / 34.3）不变。出处仍是 `paper/data/gate_attrib.csv`
  的 `all_rows_median` 注释行。
- `6.8\%`（阀门的被挡占比）、`36.0\%` / `34.3\%` / `32.2\%` / `5.9\%`（八条臂与全体
  完成 run 的两套中位）、`29.3\%` / `18.0\%` / `0.6\%`（`rg2`/`rg3`/`rg4`）、
  `fifty`（分母集合规模）：**全稿仅此一处** → 现只在本文件；数据出处
  `paper/data/gate_attrib.csv`（`valve_pct` / `round_gate_pct` / `projection_over_pct`
  / 逐 run 行，`foyer_hc` 行 `valve_pct=6.8`、`round_gate_pct=0.0`）。
- `3{,}700` / `nine admitted` / `51 of 206` / `24.8\%`：**前两个全稿仅此一处** →
  现只在本文件；数据出处 `paper/data/gate_attrib.csv` 的 `pois200_foyer_hc` 行
  （`cycles_over_budget=3700`、`admitted_while_over=9`、`forced_admits=51`、`total_admits=206`）。
  `24.8\%` 与 `(51 of 206)` **留在正文**。
- ⚠ 两个限定语 `\emph{not distinguishable from our logs}` 与 `so we do not attribute the
  bucket to either` **随本块移出正文**（逐字在本文件上一段）。正文改用的是
  「`neither gate is what sets the floor`」，**没有把「不可区分」说成「可判」**；
  但若审查要求「不可归因」这句必须回到正文，**把本段回移**即可（本块是首选回移项）。

---

## 块 8：占用比较与空闲分解

**原文位置**：原 §*The controllers leave memory unused* 第 3 段（原第 211--222 行）。

**移出理由**：`horizon=1` / `cap3+HiCache` / `horizon=0` 三臂的逐项读数与
「19 分钟里 12.6 是空闲、6.8 是忙」的分解。⚠ **这组数在正文里已经没有了**
（2026-09-27 更正：本节早先写「同一组数在 §III 已印 1.52 / 1.51 / 12.6 / 19.4」——
**不成立**：§III 印的是 `1.53` 与 `1.51`，那是 `cap3_fixed`/`cap3_hc` **另一对臂**；
`1.52`、`12.6`、`6.8`、`19.4` 全稿 0 命中，`19` 与 `28` 两个分钟数留在正文）。
本节主张（欠用**不能**解释结果差异，而设运行数的策略同时设了大部分空转）留在正文。

**正文留下的衔接**：

```latex
But under-use does
\emph{not} order the outcomes, so it is not the whole explanation either:
\texttt{horizon}=1 and \texttt{cap3}+HiCache sit at the same median occupancy and
nearly the same mean running count, and the cap is 19 minutes faster, while the
re-measured \texttt{horizon}=0 arm runs lower and is 28 minutes slower. A parked
session is one the controller has authorized but not yet released, so the same
policy that sets the running count also sets much of the idle time.
```

**原文（逐字，被移出的片段）**：

```latex
(57.8\% of the pool) and nearly the same mean running count (1.52 against 1.51),
and the cap is 19 minutes faster, while the re-measured \texttt{horizon}=0 arm
runs at 58.1\%, below that cap, and is 28 minutes slower. Of those 19 minutes,
12.6 are idle and only 6.8 are busy, and
```

**另有一句纯重复被删（不是移出，值都在正文别处）**：原句
`the base configuration holds nearly half the pool idle with 66 sessions queued,
because it believes it has 7.6\% free when it has 48.2\%` 是第 2 段同一组数的**逐字重述**
（66 / 7.6 / 48.2 三值在本节上一段仍在），删掉它不丢任何值；主张句
`The controllers under-use the pool, and this is a property of their estimates rather than
of the hardware.` 与 `But under-use does \emph{not} order the outcomes` 均在正文。

**值现在在哪**：
- `57.8\%`（两条臂的共同占用中位）、`1.52` / `1.51`、`58.1\%`、`12.6` / `6.8`（空闲/忙的
  分钟分解）：⚠ **全稿仅此一处**（2026-09-27 更正 —— 本节早先写「§III 仍有 1.52 /
  1.51 / 12.6」，与同一份文件末尾的「值现在在哪」自相矛盾，那一份是对的）。
  逐 run 数据在 `paper/data/occupancy.csv`（`occ_p50_pct`：`foyer_hz1` 57.8、
  `cap3_hc` 57.8、`foyer_hz0_r2` 58.1）与 `paper/data/decomp.csv`
  （`running`：`foyer_hz1` 1.52、`cap3_hc` 1.51；`idle_min`：36.7 / 24.1）。
- `19` 与 `28`（分钟）**留在正文**；限定语 `only`（「只有 6.8 是忙」）**随本块移出**。

---

## 块 9：`sf=0` 的准入率读数

**原文位置**：原 §*The controllers leave memory unused* 第 5 段（原第 240--245 行）。

**移出理由**：逐周期准入率的两个百分比（`2.44\%` vs `2.35\%`），主张
（`sf=0` 不是胜利；闸门是真成本，但拆掉它是**沿前沿滑**不是**越过**）留在正文。

**正文留下的衔接**：

```latex
... with its admission rate essentially unchanged. The gate
was a real cost, and removing it moves the arm along the front rather than past
it: the same trade every other route makes.
```

**原文（逐字，被移出的片段）**：

```latex
(2.44\% of
cycles admit, against 2.35\%)
```

**值现在在哪**：
- `2.44`：**全稿仅此一处** → 现只在本文件；出处 `paper/data/runs.csv` / `table1.csv`
  （`pois200_foyer_sf0_r2` 的准入率列）。
- `2.35`：`paper/data/slo_sensitivity.csv` / `repeat_spread.csv` / `runs_precise.csv`
  有同值（需人工核是否同一量）。

---

## 块 10：归因判据的两处披露

**原文位置**：原 §*What the two mechanisms explain, arm by arm*
（`sec:results:attribution`）第 1--2 段（原第 250--278 行）。

**移出理由**：判据的**历史**（早期版本没查可比性）与六条臂的**点名**；
判据本体（92\% / 8\% / 8\%）、计数（十三臂七归因、二无对照、四残差）、
两条限制**全部留在正文**。

**正文留下的衔接**：

```latex
... everything else is a
residual. The comparability clause is load-bearing.
```

```latex
Of the thirteen arms, seven are attributed---six to unused memory and one to step
cost (the published-parameter AIMD);
```

**原文（逐字，被移出的片段）**：

```latex
and we state it because an
earlier version of this table did not enforce it, which classified every arm that
ran \emph{more} requests than its comparison as step-cost purely because $\tau$
rises with the running count.
```

```latex
(\texttt{scans the queue}, \texttt{single-flight off}, the charge-free base,
no-gate no-reservation, \texttt{horizon}$=0$ and \texttt{horizon}$=2$ once
re-measured)
```

**值现在在哪**：
- 六条臂的名字：**全稿仅此一处** → 现只在本文件；逐臂读数与判据结果在
  `paper/data/attribution.csv`（`arm` / `class` / `nearest_static` 逐行可核）。
- 限定语 `did not enforce it`（否定式披露）**随本块移出**；正文保留
  `The comparability clause is load-bearing.`（判据的承重性声明仍在）。
- 计数 `thirteen` / `seven` / `six` / `one` / `two` / `four`：**留在正文**。

---

## 块 11：驻留基线的引擎侧读数

**原文位置**：原 §*Why the knobs do not help*（`sec:results:gate`）第 1 段（原第 283--299 行）。

**移出理由**：拆掉「双重计费」之后引擎侧的三个读数（占用、忙时运行数、round-1+ 命中率）；
主张（**这一计费不是双重的**；拆掉它按预测动了引擎侧、且早完成 25.4 分钟，**但仍不是胜利**）
留在正文。

**正文留下的衔接**：

```latex
The charge is not double. Removing it does what
the argument predicted on the engine side, with no eviction spiral, and finishes
25.4 minutes earlier (265.9 against 291.3).
```

**原文（逐字，被移出的片段）**：

```latex
median occupancy rises from 49.2\% to
56.2\% of the pool, the busy-hour running count from 1.35 to 1.48, and the
round-1+ prefix hit rate falls only from 80.6\% to 79.7\%, so no eviction spiral
occurred
```

**值现在在哪**：
- `49.2\%`（基线占用中位）：**仍在正文**（本节）与 `paper/data/occupancy.csv`。
- `56.2\%` / `1.35` / `1.48`：**全稿仅此一处** → 现只在本文件；出处
  `paper/data/occupancy.csv`（`foyer_bres_r2` 行）与 `attribution.csv` 的
  `occ_pct=56.2` / `running=1.481073`。
- `80.6\%` / `79.7\%`（round-1+ 前缀命中率）：**全稿仅此一处** → 现只在本文件；
  出处 `paper/data/hitrate.csv`（`observed_round1_pct`；`foyer_hc` 与 `foyer_bres_r2`）。
- 限定语 `only`（命中率只降这么点）**随本句移出**；正文保留 `with no eviction spiral`。
- `3.81\,pp` / `0.09\,pp` / `87.2\%` / `2.6\,pp` / `3.9` / `1.9\,pp` 与
  `We rest nothing on the 0.09\,pp`：**全部留在正文**。

---

## 块 12：预算扫描的墙钟与共租旗

**原文位置**：原 §*Why the knobs do not help* 第 2 段（原第 301--313 行）。

**移出理由**：两条预算臂的墙钟分钟数与「带旗但 τ₂ 干净」的披露；主张
（降预算把点推到前沿**下方**而非沿前沿滑动、三条臂都没加机制）留在正文。

**正文留下的衔接**：

```latex
Lowering the budget fraction
slides the point \emph{below} the front rather than along it: budgets of 0.85 and
0.90 finish at 89.9\% and 87.7\% SLO, $-2.24$ and $-4.22$\,pp from the envelope at
those wall clocks, against $-0.93$ and $-1.24$ for the two nearest arms at the
0.95 the rest of the paper uses. None of the three adds a mechanism.
```

**原文（逐字，被移出的片段）**：

```latex
finish in 333.9 and 315.9 minutes at 89.9\% and 87.7\% SLO
```

```latex
Both carry the
co-tenancy flag, but their $\tau_2$ sits inside the clean range, so we keep their
numbers and flag the window.
```

**值现在在哪**：
- `333.9` / `315.9`（分钟）：**全稿仅此一处** → 现只在本文件；出处
  `paper/data/budget_sweep.csv`（`wall_min=333.8989` / `315.8595`）。
- `89.9\%` / `87.7\%` / `-2.24` / `-4.22` / `-0.93` / `-1.24` / `0.85` / `0.90` / `0.95`：
  **仍在正文**；`budget_sweep.csv` 有全精度行。
- ⚠ 共租旗那句的限定语 `but their $\tau_2$ sits inside the clean range` 与
  `so we keep their numbers and flag the window` **随本块移出**（逐字在本文件）——
  这是「我们保留带旗数字」的披露，若审查要求它留在正文，**可原地回移**（本块是次选回移项）。

---

## 块 13：第四路线（运行数闸门）的扫描读数

**原文位置**：原 §*Why the knobs do not help* 第 3 段（原第 315--329 行）。
协调人处置表点名「**第四路线（闸门）的细节可移**」。

**移出理由**：闸门扫描的逐项读数（运行数/驻留数的位移、百分比、另两条臂的步数）；
本路线的**论点**（它攻击的是「控制器设的是驻留数」这一共同假设；
修法都失败：不约束则被暂停的会话下一周期又被放行，约束了则退化成会话上限；
障碍是**粒度**——`paused` 在轮次边界生效，而钉住瞬时计数需要 permit 机制没有的控制）
**全部留在正文**。

**正文留下的衔接**：

```latex
We implemented it as a gate on
\texttt{num\_running\_reqs} and swept it over $\{2,3,4\}$. A gate of four
tightened the running count rather than pinning it, and only that arm ran to 998
of the trace's 999 steps, so this is a single comparison rather than a sweep. Both
repairs fail: ...
```

**原文（逐字，被移出的片段）**：

```latex
A live session spends
most of its time parked (mean running over mean live is 0.21 to 0.64 across the
thirty-three runs where \texttt{occupancy.csv} and Table~\ref{tab:runs} overlap),
so capping \emph{running requests} instead should keep the engine busy while
leaving the resident count high.
```

```latex
Against the no-gate arm
a gate of four moved mean running requests from 1.33 to 1.30 and mean live
sessions from 3.25 to 3.03---tightening both, by 2\% and 7\%, rather than pinning
the one it aims at.
```

```latex
(the other two stopped at 770 and 169)
```

**值现在在哪**：
- `0.21` / `0.64`（mean running / mean live 的区间，33 条 run）：**全稿仅此一处** →
  现只在本文件；出处 `paper/data/occupancy.csv`（`running_mean`）与
  `paper/data/decomp.csv`。
- `1.33` / `1.30` / `3.25` / `3.03` / `2\%` / `7\%`：`1.33` 与 `1.30` 的**全精度值**
  在全稿仅此一处 → 现只在本文件；出处 `paper/data/runs.csv` / `table1.csv`
  （`pois200_foyer_nogate` 与 `pois200_foyer_rg4` 的 `Conc.` 列：3.25 与 3.03 **仍在
  Table I**）。
- `770` / `169`（另两条臂的步数）：**全稿仅此一处** → 现只在本文件；出处
  `paper/data/concurrency.csv` / `gate_attrib.csv` 与 run 自己的 `steps.jsonl`。
  正文保留 `only that arm ran to 998 of the trace's 999 steps`（限定语 `only` 在正文）。

---

## 块 14：停摆窗口的取证细节

**原文位置**：原 §*An independent adaptive controller*（`sec:results:aimd`）
最后一段（原第 334--354 行）。

**移出理由**：窗口的完整判据表述（150\,s / 85 会话 / 空载 / 两道闸门都不持有）与
「没有任何东西被记成错误」；主张（**一个**窗口存在、`166.6\,s` / `0.93\%`、
`cannot arise` 于静态 cap）留在正文。

**正文留下的衔接**：

```latex
Our own controller shows a smaller version of the same shape: one of the
fifteen runs of ours in \texttt{stall.csv} has a window in which it admits nobody
for at least 150\,s while the engine has no running request and at least 85
sessions wait, with neither the SLO valve nor the hard stop holding
admission---166.6\,s, 0.93\% of the span it sampled; it cannot arise in our static
caps, which have no admission decision to get stuck in.
```

**原文（逐字，被移出的片段）**：

```latex
over the
fifteen runs of ours in \texttt{stall.csv} exactly one has a window in which it
admits nobody for at least 150\,s while the engine has no running request and at
least 85 sessions wait, with neither the SLO valve nor the hard stop holding
admission---166.6\,s, 0.93\% of the span it sampled---and nothing is logged as an
error. The window is present in one of our fifteen runs and cannot arise in our
static caps, which have no admission decision to get stuck in.
```

**值现在在哪**：
- `15` / `one` / `150\,s` / `85` / `166.6\,s` / `0.93\%`：**仍在正文**（改写为一句）。
- `and nothing is logged as an error`：**全稿仅此一处** → 现只在本文件；
  出处 `paper/data/stall.csv`（判据列 `n_windows` / `total_s` / `pct_span`）与
  run 的 `controller.jsonl`。
- 限定语 `exactly one` / `neither` / `cannot arise`：**留在正文**。

---

## 若要继续压缩：剩余候选（本次未动）

以下都在**正文里主张的承重路径上**，本次按协调人「宁可少压 200 词，也不许删一个限定语」
优先保留。若下一轮仍需压缩，按性价比排序（词数为原始串口径）：

| 候选 | 词数 | 代价 |
|---|---|---|
| §*The frontier* 第 2 段（scan 臂的机制与读数全段） | ~265 | 摘要是**以它**收尾的（「a tenth arm … lands above it twice」），移出即与摘要失联 |
| §*The frontier* 第 5 段（锚点重复把前沿移了两次 + 脚注） | ~212 | §VI 用「the replicate spread in §V」指向它；移出会让该指向失去落点 |
| §*An independent adaptive controller*（全节） | ~245 | 摘要有「an independent congestion-based controller reimplemented」，移出即与摘要失联 |
| §*The frontier* 第 3 段（共租修正，现已瘦身） | ~60 | §I 有同值，但 `We do not read the four as agreeing` 是本段唯一的对冲 |
| §*The frontier* 第 4 段（基线的重复有多紧 + 3.5pp 的取舍） | ~95 | §VI 的 `replicate spread in §V` 指向它 |
| §*The frontier* 第 6 段（无控制臂） | ~71 | 「读者可能以为答案是别管」这句是本文最贵的反问，只有它能挡住这个误读 |
| `Notes to Table I` 的 ‡ 段 | ~55 | 表 I 的 `$^\ddagger$` 需要一个定义处 |

⚠ **块 2 与块 5 各带一条「值在 `paper/data/*.csv` 里 0 命中」的缺口**
（旧 Δ 四值、`600\,s` 流空闲超时）。本项目纪律要求每个数字都能追到文件 ——
这两条要么在 `superseded.csv` / 相应 run 的日志摘要里补列，要么回移正文，**不要留着不管**。

---

# 第二轮外移（2026-09-27）：§V 的逐条读数与机制铺陈（净移出 ~500 词）

**背景**：正文要压到 11 页（改前 13 页、参考文献从第 12 页起、正文 ≈ 11.7 页）。
本轮按协调人清单整块外移，**数字与限定语逐字记录在下面**，正文侧只保留指向与必要限定。
改后实测：**12 页，参考文献标题落在第 11 页，正文结束于第 11 页**（正文 ≤ 11 页）。

## 块 R1：共租修正的逐臂读数（`The frontier` 第 3 段，60 词）

**原文位置**：`sec_results.tex` 的 `\subsection{The frontier}`，`Two points in Fig.~\ref{fig:frontier} are above the line` 那段之后。

**移出理由**：逐臂读数展开；四个值在 §I 与 §VI 都有同值上下文。

**正文留下的衔接**（保留对冲，删去逐值）：

```latex
Four of the nine carried the co-tenancy flag of Table~\ref{tab:runs} and were
re-measured alone (\S\ref{sec:repro}); we do not read them as
agreeing---one contamination window, not four independent replications---and even
the largest correction leaves its arm below the line.
```
⚠ 2026-09-27（r52 处置）**这段衔接又动过两个词**：`the four` → `them`、
`but` → `and`；限定语 `four **independent** replications` 是 r52 从 `four replications`
**补回来**的。本快照已按现行正文更新。

**原文（逐字）**：

```latex
Four of the nine carried the co-tenancy flag of Table~\ref{tab:runs} and have
since been re-measured alone (\S\ref{sec:repro}); the correction moved them
$11.2$, $6.5$, $6.4$ and $4.5$\,pp closer to the front. We do not read the four
as agreeing---they are four arms from one contamination window rather than four
independent replications---but even the largest correction leaves its arm below
the line.
```

**值现在在哪**：
- `11.2` / `6.5` / `6.4` / `4.5`：**仍在正文**（§I `sec_intro.tex`「we re-measured all four, which moved them 11.2, 6.5, 6.4 and 4.5 points closer to the front without crossing it」；§VI `sec_discussion.tex`「moved 4.5--11.2\,pp without crossing the line」）；数据出处 `paper/data/table1.csv` 与 `paper/data/concurrency.csv`。
- 限定语 `We do not read the four as agreeing` / `not four independent replications`：**留在正文**（改写为一句，见上）。

## 块 R2：两个锚点重复把前沿移了两次（`The frontier` 第 4 段，107 词）

**移出理由**：逐条读数展开；`-0.30` / `+0.22` 在摘要与表 I，`209.1` / `133.0` 等在完整 run 表。

**正文留下的衔接**：无（整段移出）。其上段（基线的重复有多紧）与紧跟的
`\footnote{The repeats are uneven, ...}` **都在正文**——脚注现在附在上一段末尾。

**原文（逐字）**：

```latex
The anchor repeats moved the frontier twice, and we report both moves because a
frontier whose anchors are single measurements is the weakness this whole
subsection is about. \texttt{cap4}+HC's repeat came out both faster and higher on
SLO, displacing the first, and no controller verdict moves.
\texttt{cap3}+HiCache's repeat
is also faster and higher, and taking it moves our best arm from $+0.41$\,pp---nominally \emph{above} the
line---to $-0.30$\,pp. Both sit inside the $\pm1.0$\,pp band, so the verdict is a
tie either way; but the anchor we choose decides the sign of the margin we report,
and we take the repeat, which is the worse of the two for us.
```

**值现在在哪**：
- `+0.41`：**全稿仅此一处** → 现只在本文件。来源：`frontier.py` 以 `cap3+HC` 的**首跑**为锚点时 `foyer_hz2_r2` 的 Δ（全精度 −0.296 → 换锚点前 +0.409）；两个锚点在 `paper/data/table1.csv`（`cap3_hc` 236.4/81.1 与 `cap3_hc_r2` 230.3/81.9）。
- `-0.30` / `+0.22`：仍在正文（摘要、表 I `horizon=2` 那两行）。
- `209.1` / `68.5`（cap4+HC 重复）与 `230.3` / `81.9`（cap3+HC 重复）：仍在正文表 I。
- 限定语 `we take the repeat, which is the worse of the two for us` 与 `Both sit inside the $\pm1.0$\,pp band, so the verdict is a tie either way`：**随本段移出**；`±1.0\,pp` 带本身在 §II 与表 I 脚注仍在正文。

## 块 R3：`W` 不随并发单调（45 词）

**移出理由**：连接性铺陈（引出 §III 的机制）；两个值在完整 run 表。

**原文（逐字）**：

```latex
One feature of the front leads into the mechanism: $W$ is not monotone in
concurrency---five sessions (260.9\,min) is \emph{slower} than four (249.9\,min),
the same configuration family with no host cache on either side, because the
per-step cost rises faster than the request count does.
```

**值现在在哪**：
- `260.9`（`cap5`）/ `249.9`（`cap4`）：在 `paper/data/table1.csv`，也印在本仓库
  `paper/supplement_table1.md`（完整 run 表）；§III 的「per-step cost 随 R̄ 上升」
  论断在正文。
- 限定语 `the same configuration family with no host cache on either side`：**随本句移出**。

## 块 R4：`sf=0` 的逐项读数（74 词）

**移出理由**：逐条读数展开；四个读数与 Δ 都在表 I 里。

**原文（逐字）**：

```latex
Disabling single-flight is not a win either: \texttt{sf=0} finishes in 263.3
minutes at 86.3\% SLO against the base run's 291.3 and 89.8\%, and its signed
distance from the front moves from $-1.24$ to $-0.55$---onto the tie band from
below it, not above it---with its admission rate essentially unchanged. The gate
was a real cost, and removing it moves the arm along the front rather than past
it: the same trade every other route makes.
```

**正文留下的衔接**（对冲移回 §V 的 `The controllers leave memory unused`，与欠用段合并）：

```latex
Under-use is a property of the controller's estimates rather than of the
hardware, but it does not order the outcomes, so it is not the whole explanation
either; and removing the single-flight gate is the same trade every other route
makes---it moves that arm along the front rather than past it.
```

**值现在在哪**：
- `263.3` / `86.3` / `-0.55`（表 I `single-flight off` 行）与 `291.3` / `89.8` / `-1.24`（`horizon=3 (base)` 行）：**仍在正文表 I**。
- 限定语 `onto the tie band from below it, not above it` / `the same trade every other route makes`：**留在正文**（改写，见上）。

## 块 R5：闸门归因的两个读数与欠用结论（`The controllers leave memory unused` 第 3–4 段，203 词）

**移出理由**：机制细目；`24.8%` 与 `51 of 206` 本来就源自 `gate_attrib.csv`（§V 另处已有指向）。

**原文（逐字）**：

```latex
Two things follow, and we are careful about the second. The controllers under-use
the pool, and this is a property of their estimates rather than of the hardware.
But under-use does
\emph{not} order the outcomes, so it is not the whole explanation either:
\texttt{horizon}=1 and \texttt{cap3}+HiCache sit at the same median occupancy and
nearly the same mean running count, and the cap is 19 minutes faster, while the
re-measured \texttt{horizon}=0 arm runs lower and is 28 minutes slower. A parked
session is one the controller has authorized but not yet released, so the same
policy that sets the running count also sets much of the idle time.

We then asked what actually stops it. A session is authorized only if the SLO
valve is open, the round gate is not full, and its projected footprint fits what
remains of the budget, and neither gate is what sets the floor: a starvation guard
that bypasses the budget once the oldest waiter has waited 240\,s is, and it
accounts for 24.8\% of the base run's admissions (51 of 206); the blocked-cycle
attribution is in the supplement. It is the guard,
not the budget test, that sets the floor on how fast this controller can admit.
```

**正文留下的衔接**：

```latex
Under-use is a property of the controller's estimates rather than of the
hardware, but it does not order the outcomes, so it is not the whole explanation
either; and removing the single-flight gate is the same trade every other route
makes---it moves that arm along the front rather than past it.
```

**值现在在哪**：
- `240`（饥饿守卫阈值）、`24.8%`、`51`、`206`：**全稿仅此一处** → 现只在本文件。
  出处 `paper/data/gate_attrib.csv`（`forced_admits` = 51、`total_admits` = 206、
  `valve_pct` 一类列）与 `pois200_foyer_hc` 的 `controller.jsonl`。
  ⚠ **这三条此前有活守卫**（`foyer_hc 总准入数` / `foyer_hc 被强制准入数` /
  `foyer_hc 被强制准入占比`），移位后**报新 MISS**（见报告）。
- `1.52`（`foyer_hz1` 的 R̄）/ `1.51`（`cap3_hc` 的 R̄）/ `36.7` / `24.1` / `52\%` /
  `12.6` / `19.4`：**全稿仅此一处** → 现只在本文件；出处 `paper/data/decomp.csv`
  与 `paper/data/idle_pooled.csv`。（§V 另有一句同涵义但不同数：同中位占用、19 分钟差。）
- `28`（`horizon=0` 复测臂慢 28 分）与 `19`（cap 快 19 分）：在 `paper/data/table1.csv`。
- 限定语 `this is a property of their estimates rather than of the hardware` /
  `under-use does not order the outcomes, so it is not the whole explanation`：
  **留在正文**（改写，见上）。

---

## 本轮消费掉的候选（更新上面那张「若要继续压缩」表）

| 上表候选 | 本轮处置 |
|---|---|
| §*The frontier* 第 3 段（共租修正，现已瘦身） | **已外移**（块 R1）；四个值仍在 §I 与 §VI；对冲改写后留在正文 |
| §*The frontier* 第 5 段（锚点重复把前沿移了两次 **+ 脚注**） | **散文部分已外移**（块 R2，107 词）；**脚注留在正文**——它是「重复有多弱 / exposure is bounded」的证据强度披露，按 codex 边界不移动 |
| §*The frontier* 第 4 段（基线的重复有多紧 + 3.5pp 的取舍） | **未动**：§VI 的「the replicate spread in §V」仍指向它 |
| §*The frontier* 第 2 段（scan 臂） | **未动**：摘要以它收尾；且它承载「同一句里的 0.5--4.6 全距」与「最紧那一组」四条活守卫 |
| §*The frontier* 第 6 段（无控制臂） | **未动**：`§V 无控制臂的 SLO` / `首 token 中位` 两条活守卫锚在这里 |
| §*An independent adaptive controller*（全节） | **未动**：摘要与「重实现披露」都靠它 |
| `Notes to Table I` 的 ‡ 段 | **未动**：表 I 的 `$^\ddagger$` 需要定义处 |

**本轮另外外移了三条上表没列出的**：`W` 不随并发单调（R3）、`sf=0` 逐项读数（R4）、
欠用与闸门归因两段（R5）——理由与取值见上文。

---

## 块 R6：**整句删除**——无控制臂那句判断（r54 复核 D3，15 词）

上面那张表把「§*The frontier* 第 6 段（无控制臂）」记成**未动**（两条活守卫锚在那里）。
r54 复核逐字核到：**那一段里少了一句判断，而全稿再无出处**。单独记在这里。

**原文位置**：`paper/sec_results.tex`，紧跟四个读数（288.6 分钟 / 3.0\% / $87.6$\,pp /
1{,}774 秒）之后。

**原文（逐字，15 词）**：

```latex
Uncontrolled admission does not degrade gracefully; it destroys the cache and
then serves almost nobody.
```

紧接的一句 `The question this paper addresses is therefore not whether to admit
selectively, but which selective rule to use.` 也已删。

**处置：退役，不补回**（按本项目规矩「主张还在正文 ⇒ 补数；主张也删了 ⇒ 退役并写明值在哪」）。
逐半句核过：

- **结果半句**（`serves almost nobody`）**仍在正文**，四个读数都在（288.6 分钟 /
  3.0\% / $87.6$\,pp / 1{,}774 秒），由 §V 的
  `§V 无控制臂的首 token 中位（秒）`、`§V 无控制臂的 SLO` 两条活守卫与表 I 那一行钉住
  ⇒ **无需补数**。
- **机制半句**（`it destroys the cache`）**已不在正文**：改稿前它的证据是
  「runner 自报的前缀命中率从计划 75.5\% 掉到 1.6\%，且 SLO 在头一个十分位读 30\%、
  之后九段**恰好为零**」。全稿实测：`1.6\%` 出现 **0** 次、`destroy` 出现 **0** 次、
  `exactly zero` / `segment SLO` / `tenth of the run` 各 **0** 次 ⇒ **主张也删了**。
- **为什么不补回正文**：写回去是**加一条主张 + 一个数**，而技术正文此刻卡在 11 页
  硬限（改稿预算 ~0 词）。那是加强，不是修复一次压缩失手 —— 而且 §I 已经把同一
  动机说清楚了（`admission control---which rounds to admit---looks like the obvious
  lever` 与 `We believed this ... it is false`），所以那句的**框架**并没有丢。

**值现在在哪**：

- 结果读数（正文仍在）：`paper/data/nocontrol.csv` 的 `default` 行 ——
  `ttft_p50_s` = 1774.0、`slo_pct` = 3.0；墙钟 288.6 与 $\Delta$ $-$87.62 在
  `paper/data/table1.csv` 的 `default` 行（`wall_min` 288.6046 / `delta_pp` $-87.6198$）。
- 机制读数（**本文件是唯一落地处**）：`paper/data/nocontrol.csv` 的 `default` 行 ——
  `runner_planned_pct` = 75.45、`runner_server_pct` = 1.64，同行还有四种口径的实测列
  （`obs_all_tok` = 1.9、`obs_r1_tok` = 2.05）。**生成器**：`scripts/lab/gen_nocontrol.py`。
