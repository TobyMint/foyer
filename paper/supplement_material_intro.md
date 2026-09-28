# 外移材料 —— `sec_intro.tex`（§I）、`sec_background.tex`（§II）、`sec_criterion.tex`（§IV）

本文档收集 2026-09-27 为适配 **RTAS 2027 技术正文 11 页硬限**而从
`paper/sec_intro.tex`、`paper/sec_background.tex`、`paper/sec_criterion.tex`
**整块移出**的 15 段原文（合计 **492 词**，排版口径）。
移出经协调人 2026-09-27 裁决（「整个 topic 移出正文」）授权。

**移出纪律（本项目硬规矩）**：每一条都写明「**值现在在哪**」—— 标出该段承载的数字/限定语
是否在论文别处仍有出处。凡写不出「现在在哪」的，一律按「该恢复」处理。

**未移出（明示保留）**：

- **`What we do not claim` 整块**（§I，157 词）—— 负结果论文的边界声明；
- **判据定义的全部基座**（§IV）：`eq:elasticity`（ε = dlnτ/dlnR̄）、`1.1^(1−ε)` 含义
  （「加 10% 并发只买到 3.8%~6.1%」）、拟合指数 vs 分段拟合（0.61 / 0.38 / R²=0.89）、
  四个 device-only 段值（−0.21 / +0.43 / +1.15 / +1.14）、四个 HiCache 段值
  （+0.19 / +0.46 / +2.87 / +0.48）、判据的循环性披露（τ₁ 由 W_busy 导出）；
- **`\eqref{eq:busy}` / `eq:proj` / `fig:frontier` 及其 caption / `tab:runs` 的引用**；
- **被判据守卫钉住的句子**（见每块「值现在在哪」里标 `⚠守卫` 的条目）。

**论文正文保留的指向**：移出后，三个文件在这些位置保留了指向本节其余部分/补充材料的最小
衔接句（见每块的「正文留下的衔接」）。

---

## 一、`sec_intro.tex`（§I）移出 5 块，204 词

### 块 I-1：前言的假设句（scheduler 看得到剩余空间就该赢）

**原文位置**：原 `sec_intro.tex` 第 1 段末（原第 10–12 行）。

**移出理由**：这是对 §II 控制器设计的**预告**；紧跟其后的「We believed this, built a
controller that does exactly that」已经把同一件事说清楚，而 §II 的 `eq:proj` 是它的实现。

**正文留下的衔接**：
```
obvious lever: the KV pool is the binding resource
\cite{kwon2023pagedattention}, a single large session can occupy most of it, and
sessions are heterogeneous.
```
（下一段 `We believed this, built a controller that does exactly that …` 的 `this` 仍指
「admission control look like the obvious lever」。）

**原文（逐字）**：

```latex
If a scheduler can see how much of the pool a
candidate will need and how much room is left, surely it should beat a fixed
number.
```

**值现在在哪**：
- 无数字。
- 限定语 `surely`：随本段移出。
- 该假设的实现（`$\Pi + n \le B$`）**仍在正文** §II 的 `eq:proj`。

---

### 块 I-2：第十条臂的三处读数与「改了放行规则」的结论

> ⚠⚠ **2026-09-27（r51 双审查）：这一块里的「原文」是【历史原文】，不是现行结论。**
> 它写于**两次读数**的时代（`scan` + `scan_r2`，都越线），下面那句
> 「That is a crossing---the only arm we ran that beats the envelope twice」**已经过期**：
> 第三次读数 `pois200_foyer_scan_r3` = **+0.2948（带内）**，头条已按跑前预注册的分支 (b)
> 退回**运行层面** —— 现行说法是「**三次里两次越线，第三次在带内**，
> **不是可复现的越线**」。**不要把这个代码块当成现行正文引用。**
> 现行状态见 `paper/claims_audit.md` 的 C4。

**原文位置**：原 `sec_intro.tex` §*What we measured* 第 4 句（原第 29–32 行）。

**移出理由**：§V 与摘要各自**完整**给出这条臂（读数、判决、改动内容）；§I 只需指出
「还有一条臂在线上方、且它的重复也一样」并给出指向。

**正文留下的衔接**（保留的压缩句，**`One further arm lands above it` 这个事实留在正文**，
第十条臂因此没有从 §I 消失）：
```latex
One further arm lands above
it, and so does its repeat---the same controller revision, one expression
changed (\S\ref{sec:results}).
```

**原文（逐字）**：

```latex
One further arm lands above
it, and so does its repeat: the same controller revision as the base's repeat,
with a single expression changed, measures $+1.30$ and $+2.16$\,pp. That is a crossing---the only arm we
ran that beats the envelope twice---by changing the \emph{release} rule, not the
admission decision (\S\ref{sec:results}).
```

**值现在在哪**：
- `+1.30` / `+2.16`：**仍在正文** —— 摘要（`main.tex`「lands above it twice, by $1.3$ and
  $2.2$\,pp」）、`sec_results.tex:32`（「The two measure $+1.30$ and $+2.16$\,pp, clearing
  the band by $0.30$ and $1.16$\,pp」）、表 I 两行（`sec_results.tex:136-137`）、
  `sec_discussion.tex:133`、结论（`sec_discussion.tex:283`）。
- `the only arm we ran that beats the envelope twice`：**⚠ 已作废**（第三次读数在带内）。
  现行说法是**运行层面**的「三次里两次越线」，见 `paper/claims_audit.md` C4 与
  `sec_results.tex` / `sec_discussion.tex` / 摘要。
- `changing the \emph{release} rule, not the admission decision`：摘要与 `sec_results.tex` 仍在。
- 数据出处：`paper/data/table1.csv`（**`foyer_scan` / `foyer_scan_r2` / `foyer_scan_r3` 三行**）。
- ⚠ `\S\ref{sec:results}` 这个指向**仍在正文**（保留的压缩句里带着）。

---

### 块 I-3：设备侧兑现曲线与 host tier 的对照（`realization is where the tier enters:` 之后）

**原文位置**：原 `sec_intro.tex` §*Why* 第 2 段后半（原第 67–72 行）。

**移出理由**：这是 §III 的核心读数整段预告（§III 有同一组数，含 tier 表）；§I 保留
「reuse 的上界」与「兑现由 tier 决定」两个论断，把曲线本身交给 §III。

**正文留下的衔接**：
```latex
Prefix \emph{reuse}
is bounded by the workload---75.5\% of the prompt tokens here, a bound no
configuration we ran reaches---and realization is where the tier enters
(\S\ref{sec:model}).
```

**原文（逐字）**：

```latex
device-only, it falls from 92.5\% at $\overline{R}_{\text{busy}}$ 1.00 to 36.4\%
at 1.84, the shortfall appearing as recomputation (8.6\,M to 20.7\,M tokens),
while with a host tier in front of it the decline disappears over the running
counts our controllers occupy, and the arm that disables every throttle still
realizes 72.8\% where the nearest device-only point manages 60.7\%.
```

**值现在在哪**：
- `92.5` / `36.4`：**仍在正文** —— 摘要（`main.tex:47`）、§III 的 tier 表
  （`sec_model.tex:159`）与 `sec_model.tex:169`、§VII（`sec_xtrace.tex:15`）。
- `1.00` / `1.84`：§III 与 §IV 仍在（§IV 的 `1.00 to 1.84` 有守卫）。
- `8.6\,M` / `20.7\,M`（重算量）：§III 的 tier 表（`sec_model.tex:160`）仍在。
- ⚠ `72.8`（`foyfix_hc` 的兑现率）：**全稿仅此一处 → 现只在本文件**；
  数据出处 `paper/data/reuse.csv` 的 `foyfix_hc` 行（`realized_frac = 0.7280`），
  同族读数见 `sec_model.tex:160` 与 `sec_model.tex:171` 的区间（59.7--92.5\%）。
- ⚠ `60.7`：**仍在正文**（`sec_model.tex:159` 的 tier 表 `cap4` 一列；`sec_xtrace.tex:59`），
  但「72.8 vs 60.7 这个对照」本身**全稿仅此一处 → 现只在本文件**。
- 限定语 `a bound no configuration we ran reaches`：**留在正文**（在衔接句里）。

---

### 块 I-4：空转段落的收尾（「只看中位会得出没有空转」）

**原文位置**：原 `sec_intro.tex` §*Why* 第 3 段末（原第 80–82 行）。

**移出理由**：这是修辞式的收尾，其论断（空转是结构性、可追回的）由同段首句
「The idle component is structural rather than a control failure」与 §III/§V 承载。

**正文留下的衔接**：该段以 `…with 18\% of those transitions wait more than ten seconds.`
收尾，首句的 `structural rather than a control failure` 就是本段的论点。

**原文（逐字）**：

```latex
A controller that reads only the
median concludes, as we initially did, that there is no idle time to recover.
There is.
```

**值现在在哪**：
- 无数字。
- `as we initially did`（自我披露）随本段移出；同义的披露见 §III 的
  「两个同 R̄ 配置的空转差」与 §V 的空转段。
- ⚠ §I 的四个空转读数（`66.1 to 69.5\%`、`0.34\,s`、`15.8--16.9\,s`、`18\%`）**全部留在正文**，
  且四个都有活守卫（`sits in stretches over` / `the demanded median inter-round gap` /
  `of those transitions wait more than`）。

---

### 块 I-5：贡献条 4 的低载/高载预告

**原文位置**：原 `sec_intro.tex` §*Contributions* 第 4 条末（原第 112–117 行）。

**移出理由**：这正是「贡献清单预告后文」的一例 —— 两句都在 §VI 的低载段里**完整**出现
（含 `+0.9`、`not worse, not a win`、`inside the band we call a tie` 三个限定语）。

**正文留下的衔接**：
```latex
  \item We characterize when adaptivity \emph{could} have paid, and show that
        our workload is not that case: the aggressive end of this controller
        family is worth $+51\%$ at 25 sessions and costs $-42\%$ at 200
        (\S\ref{sec:load})---a direction reversal across two harness
        generations that do not move the same knobs.
```

**原文（逐字）**：

```latex
On the low-load tier the
        controller is \emph{not} worse---same-generation measurements put it
        $+0.9$\,pp above the line---so we report \emph{not worse}, not a win;
        on the high-load tier its best configuration sits inside the band we call
        a tie on both runs.
```

**值现在在哪**：
- `+0.9`：**仍在正文** —— `sec_discussion.tex:49`（「sits $+0.9$\,pp above the
  same-generation envelope」）、`:50`、`:55`。
- `not worse, not a win`：**仍在正文** `sec_discussion.tex:58-59`（「We defend the weaker
  claim: on the low-load tier the controller is not worse」）。
- `sits inside the band we call a tie`（高载档）：打平带本身**留在正文** —— §II 的定义句
  `\emph{on} it---a tie, not a win`（`sec_background.tex`）与 §V 的
  `both inside our $\pm1.0$\,pp band` 仍在。
- `+51\%` / `-42\%`（同一条里的另两个数）：**留在正文**（§I 与 §VI 都在）。
- 限定语 `\emph{not} worse` / `not a win` / `same-generation`：随本块移出，
  **但同义限定语在 §VI 正文里仍在**（上两条）。

---

## 二、`sec_background.tex`（§II）移出 6 块，163 词

### 块 II-1：池子守卫的「为什么」（另一个租户占卡 / SGLang 按空闲显存定池）

**原文位置**：原 `sec_background.tex` §*Engine and the binding constraint*（原第 35–38 行）。

**移出理由**：守卫的**规则**（`101{,}432 \pm 20`）留在正文；移出的是它**为什么可能触发**
与**短池为什么不可比**这两句方法论说明（属取证细节，且规则本身在 `scripts/lab/run_matrix.py`
里是可重算的常量）。

**正文留下的衔接**：
```latex
Every run is guarded: a pool that does not come out at $101{,}432 \pm 20$
voids the run rather than recording it (why the pool can come out short, and
what a short pool does to comparability, is in the supplement).
```

**原文（逐字）**：

```latex
Every run is guarded: if the pool does not come out at $101{,}432 \pm 20$---which
happens when another tenant holds memory on the card---the run is aborted rather
than recorded, because SGLang sizes the pool from free memory at startup and a
shrunken pool silently produces incomparable numbers.
```

**值现在在哪**：
- `101{,}432 \pm 20`：**仍在正文**（衔接句逐字保留）。
- `101{,}432`：§I（`a 101{,}432-token KV pool`）与 §II 本段仍在。
- 数据/判据出处：`scripts/lab/run_matrix.py` 的 `TURNSTILE_EXPECT_POOL`（默认 101432、
  容差 ±20）；`docs/finding_concurrency_contamination_20260924.md`。
- 限定语 `rather than recorded` / `silently` / `incomparable`：随本段移出（`rather than`
  在衔接句里保留）。

---

### 块 II-2：工具等待里「为什么可以归因给控制器」

**原文位置**：原 `sec_background.tex` §*Workload* 第 2 段末（原第 23–24 行）。

**移出理由**：这是那句归因的**推导理由**（「harness 在控制器不在路径时是精确的」），
结论句（`§model attributes that 1.03\,s to the controller's admission delay rather than to
the harness`）留在正文。

**正文留下的衔接**：
```latex
The controller's own run
measures 16.85\,s, and \S\ref{sec:model} attributes that 1.03\,s to the
controller's admission delay rather than to the harness.
```

**原文（逐字）**：

```latex
because the harness is
exact where the controller is not in the path.
```

**值现在在哪**：
- `1.03` / `16.85` / `15.82`：**仍在正文**（衔接句与它前一句）。
- 同族的 `15.8--16.9`（§I 的区间）：§I 正文仍在，且有活守卫。
- 数据出处：`paper/data/toolwait.csv` 的 `pois200_foyer_hc` 行
  （`demand_mean_s = 15.82`、`measured_mean_s = 16.85`）。
- 限定语 `rather than to the harness`：**留在正文**。

---

### 块 II-3：锚点对照的百分比读数（81.9 / 230.3 / 81.1 / 236.4）

**原文位置**：原 `sec_background.tex` §*Baselines and the verdict criterion*（原第 86–91 行）。

**移出理由**：同一组读数（含四个数）在 §V 与表 I 各有一处**更完整**的陈述
（`sec_results.tex:70` 与表 I 的 `cap3+HC` 两行），§II 只需保留判据所需的差值。

**正文留下的衔接**（保留 `+5.8` / `+6.8` / `+6.6` / `+7.6` 四个差值与那句限定语，
只把锚点的百分比读数移走）：
```latex
Our best arm reads $-0.30$ and $+0.22$\,pp against the line, and $+5.8$ and
$+6.8$\,pp against the nearest static anchor below it in wall clock
(\texttt{cap3}+HiCache's repeat; $+6.6$ and $+7.6$ against that anchor's
\emph{first} run---so the sign of the comparison is not in question, but its
size moves with which run and which repeat you take).
```

**原文（逐字）**：

```latex
(\texttt{cap3}+HiCache's repeat, 81.9\% at 230.3 minutes; $+6.6$ and $+7.6$
would be the comparison against that anchor's \emph{first} run, 81.1\% at 236.4
minutes---so the sign of the comparison is not in question, but its size moves
with which run and which repeat you take).
```

**值现在在哪**：
- `81.9` / `230.3` / `81.1` / `236.4`：**仍在正文** —— `sec_results.tex:70`
  （「230.3 minutes, 81.9\% against 236.4 and 81.1\%」）与表 I
  （`sec_results.tex:126-128`）。
- `+5.8` / `+6.8` / `+6.6` / `+7.6`：**仍在正文**（衔接句，且 `5.8` / `6.6` 有活守卫
  `§II foyer_hz2_r2 对 cap3_hc{,_r2}`）。
- `$+5.8$` / `$+6.8$`：§VI 的 Limitations 另有同义句（「the closest controller's two runs
  sit $+5.8$ and $+6.8$\,pp \emph{above} the nearest static \emph{anchor below them in
  wall clock}」）。
- 数据出处：`paper/data/table1.csv`（`cap3_hc` / `cap3_hc_r2` / `foyer_hz2_r2` 三行）。
- ⚠ 限定语 `so the sign of the comparison is not in question, but its size moves with
  which run and which repeat you take`：**留在正文**（衔接句逐字保留）。

---

### 块 II-4：池容量的「容量受限」框架句

**原文位置**：原 `sec_background.tex` §*Engine and the binding constraint* 末（原第 38–40 行）。

**移出理由**：同一句在 §VI 的 Limitations 里**以更强的形式**出现（「the pool holds about
four median sessions, so concurrency is capacity-bound \emph{by construction}, and on a
device with a much larger pool the premise may not hold and the conclusion may invert」）。

**正文留下的衔接**：无（整句移出，前一段以池子守卫句收尾，仍完整）。

**原文（逐字）**：

```latex
The
pool holds about four median sessions, so concurrency here is capacity-bound
rather than scheduler-bound.
```

**值现在在哪**：
- `four median sessions`：**仍在正文** `sec_discussion.tex` 的 §*Limitations*。
- 数据出处：`paper/data/decomp.csv` 的 `running` 列 + 池子 101{,}432 / prompt 中位
  23{,}187（`make_tables.py` 可重算）。
- 限定语 `rather than scheduler-bound`：随本句移出，**但 §VI 的 `by construction` 是同一
  限定的更强形式**。

---

### 块 II-5：用 device-only 锚点复核那条臂的距离（46.0 vs 47.1）

**原文位置**：原 `sec_background.tex` §*Baselines and the verdict criterion* 末（原第 113–114 行）。

**移出理由**：这是「把包络换成 device-only 锚点」的**敏感性复核**，属稳健性细节；
论断句（`We report the conservative reading: below the front as we defined it, not below
every static configuration`）留在正文。

**正文留下的衔接**：
```latex
and one device-only point. We report the conservative
reading: \emph{below the front as we defined it}, not \emph{below every static
configuration}.
```

**原文（逐字）**：

```latex
Drawn from device-only anchors alone it is still
below the front, by 46.0 rather than 47.1\,pp.
```

**值现在在哪**：
- ⚠ `46.0`：**全稿仅此一处 → 现只在本文件**；数据出处 `paper/data/frontier_split.csv`
  的 `foyfix_hc` 行 `front=device`（`delta_pp = -45.98`）。
- `47.1`：**仍在正文** —— 表 I 的 `all throttles off` 行
  （`sec_results.tex:145`，`$-$47.10`，同源 `frontier_split.csv` 的 `front=mixed`）。
- 限定语 `as we defined it` / `not below every static configuration`：**留在正文**。

---

### 块 II-6：`policy, not the memory` 的机制展开

**原文位置**：原 `sec_background.tex` §*The controller under test* 第 1 段末（原第 48–52 行）。

**移出理由**：这是 §III 的机制段（radix 驱逐 → 重算）的预告；§II 保留那句**范围限定**
（`a statement about the \emph{policy}, not the memory`）本身。

**正文留下的衔接**：
```latex
This is what allows per-session actions at all, including the pause
primitive of \S\ref{sec:results:gate}: the controller never frees capacity by
discarding a session, only by admitting fewer, and that is a statement about the
\emph{policy}, not the memory (\S\ref{sec:model}).
```

**原文（逐字）**：

```latex
the engine's radix cache still evicts parked
prefixes under pressure, and we measure that it does and that they are
recomputed (\S\ref{sec:model})
```

**值现在在哪**：
- 无数字。
- §III 的机制段**仍在正文**：`sec_model.tex:108-115`（「tokens evicted from the radix
  cache … an evicted prefix is recomputed, close to one token for one … we call it
  consistent, not demonstrated」）与 `sec_model.tex:238`。
- 限定语 `a statement about the \emph{policy}, not the memory`：**留在正文**；
  `consistent, not demonstrated`：§III 与 §I 仍在。

---

## 三、`sec_criterion.tex`（§IV）移出 4 块，125 词

### 块 IV-1：±10% 扰动（判据的敏感性）

**原文位置**：原 `sec_criterion.tex` §*What this does and does not establish* 中段
（原第 81–84 行）。

**移出理由**：判据的敏感性分析；同一扰动在 §VII 有一处**跨两个负载**的更强陈述。

**正文留下的衔接**：
```latex
We report the third segment and read neither a value nor a location
off it. It is measured on different policies rather than by an
intervention---a cross-policy association, not a transportable causal
derivative.
```

**原文（逐字）**：

```latex
A $\pm10\%$
perturbation of $\tau$ puts the segment elasticities' bounds across one even on
the device-only curve, so the cliff is a description of the fitted points
rather than a threshold we have located precisely.
```

**值现在在哪**：
- `\pm10\%`：**仍在正文** —— `sec_xtrace.tex:81`（「the $\pm10\%$ perturbation puts every
  segment's bounds across zero on both traces」）。
- 限定语 `a description of the fitted points rather than a threshold we have located
  precisely`：随本段移出；**同义的限定语在 §IV 正文仍在** ——
  「but our six points cannot say where the regime ends」（`sec_criterion.tex`）与
  「no error bars, stopping at 1.87」。
- 数据出处：`paper/data/elasticity_hc.csv` / `slo_sensitivity.csv`。

---

### 块 IV-2：tier 配对的两卡/日期、同卡复测与池子对照

**原文位置**：原 `sec_criterion.tex` §*What this does and does not establish*（原第 86–91 行）。

**移出理由**：这是 §III 的 tier 配对细节（哪两条配置、隔多久、哪张卡、同卡复测如何），
属推导细节；§III 与 §VI 各有一处陈述。

**正文留下的衔接**：无（整句移出，前后两句各自完整）；指向 §III 的其余 `\S\ref{sec:model}`
仍在本节（§IV 第 1 段与 `eq:elasticity` 的拟合句）。

**原文（逐字）**：

```latex
The two configurations the tier comparison
rests on were run a day apart on different cards (\S\ref{sec:model}); the
same-card pairing \emph{of those two} has since run and moves realization by
10.1 points against the 12.2 the confounded pair shows, and \S\ref{sec:model}
quotes the smaller number (the pool-size control that has run varies capacity,
a different pairing).
```

**值现在在哪**：
- `10.1`：**仍在正文** —— `sec_model.tex:195`（「\emph{it lands at $10.1$ …」）。
- `12.2`：**仍在正文** —— `sec_model.tex:192`（「gap becomes 9.8 points rather than 12.2」）。
  ⚠ **只有 §III 那一处**；§VI 说的是同一件事但**不带这个数**
  （`sec_discussion.tex:249`「a same-card pairing returns the same verdict over a smaller
  gap」）。
- 限定语 `the smaller number` / `a different pairing`：随本段移出；§III 的同义限定语仍在。
- ⚠ 数据出处：`paper/data/tierpair.csv` / `paper/data/table1.csv`。
- ⚠ **两处 `\S\ref{sec:model}` 随本段移出**；`sec_model.tex` 本身仍被 §IV 第 1 段与
  拟合句引用，不产生悬空 `\ref`。

---

### 块 IV-3：cap6+HC 的兑现读数（85.4%）

**原文位置**：原 `sec_criterion.tex` §*The controllers run in a different region* 末
（原第 55–56 行）。

**移出理由**：与 cap8+HC 的 59.7% 构成对照；59.7% 那句有**活守卫**
（`host-tier 动态下界 sec_criterion.tex`，锚 `realizes`）必须留在正文，移出的是对照的另一半。

**正文留下的衔接**：
```latex
What the sweep does show is the weaker thing we can support: the flat
regime does not continue indefinitely---\texttt{cap8}+HC realizes 59.7\% of the
bound at the far end of the swept range---but our six points cannot say where
the regime ends.
```

**原文（逐字）**：

```latex
where \texttt{cap6}+HC realizes 85.4\% at almost the same running
count
```

**值现在在哪**：
- `59.7`（cap8+HC）：**仍在正文**（衔接句，且有活守卫）。
- ⚠ `85.4`（cap6+HC）：**全稿仅此一处 → 现只在本文件**；数据出处
  `paper/data/reuse.csv` 的 `cap6_hc` 行（`realized_frac = 0.8543`，`Rbar_busy = 1.865`）；
  同族区间（59.7--92.5\%）见 `sec_model.tex:171`。
- 限定语 `at almost the same running count`：随本块移出；同义的
  「almost the same running count」在 §VII 的 A100 段仍在。
- ⚠ 判据 `cannot say where the regime ends`：**留在正文**。

---

### 块 IV-4：第二负载迁移测试的读数展开

**原文位置**：原 `sec_criterion.tex` 末段（原第 90–93 行）。

**移出理由**：§VII 是这次迁移测试的正式所在，同一句话在 §VII 与摘要各有一处；
§IV 保留「做过这个测试」与「迁移是边界而非支撑」的收尾主张。

**正文留下的衔接**：
```latex
We tested whether the curve transfers to a second workload
(\S\ref{sec:xtrace}). We report this as a boundary: the criterion identifies a
branch, and where we could check it elsewhere the sign of the branch
transferred while its location did not; it never explained the failure.
```

**原文（逐字）**：

```latex
the direction transfers, the location does not, and on
that trace we can say no more than that added concurrency stopped paying.
```

**值现在在哪**：
- 无数字。
- `the direction transfers, the location does not`：**仍在正文** —— 摘要（「a second agent
  trace reproduces the direction but not the level」）、§VII（`sec_xtrace.tex` 的
  「the direction of …」）、以及**本段收尾句本身**（「the sign of the branch transferred
  while its location did not」）。
- 限定语 `can say no more than`：随本块移出；§VII 的「it costs us the ability to
  \emph{locate} the criterion's turn」与 `it never explained the failure` 仍在。

---

## 这次移出被守卫挡回来的三处（记录，避免重复尝试）

整块外移的**下界**由三个文件里的**活守卫**决定。以下三处按「整块」思路尝试后
**已被守卫挡回并恢复**，不要再试：

| 尝试 | 结果 | 挡它的守卫 |
|---|---|---|
| §II 整块移出锚点对照的括号（含 `81.9` / `81.1` / `230.3` / `236.4`） | 恢复：留着 `+5.8`/`+6.8`/`+6.6`/`+7.6` 与那句限定语 | `ck_near("§II foyer_hz2_r2 对 …", 5.8 / 6.6, "sec_background.tex")`（全局 `ck`，只要值在文件里） |
| §IV 移出 `cap8+HC realizes 59.7\%` 整句 | 恢复：59.7 留在正文 | `ck_near("host-tier 动态下界 sec_criterion.tex", 59.7, "sec_criterion.tex", "realizes", window=200)` |
| §II 移出 `+5.8 and +6.8` 子句 | 恢复 | 同上第一条 |

**机制**：这三条守卫的锚是**整句独有的短语**或**值本身**，值一离开文件就报 MISS。
`check_paper_numbers.py` 里 `where` 指向这三个文件的**活守卫调用点**分别有
**10 / 13 / 15 个**（不含退役条目；其中两条在循环里，展开后条数更多）——
这就是「整块外移」在这三节上的下界。

---

## 若要继续压缩：剩下三个文件里的候选（本次未动）

按「省下的词数 ÷ 代价」排序。代价一栏写的是**会失去什么**，供裁决。

| 候选 | 词数 | 代价 |
|---|---|---|
| §II 的池子守卫整句（`Every run is guarded … is in the supplement`） | ~34 | §II 不再声明 run 是**为什么**被验池的；§VI 的 Limitations 只提池子、不提 ±20 规则 |
| §II `It is the stricter of the two criteria we could have used … not harder.` | ~38 | §V 的「and `\S\ref{sec:bg}` states what that choice costs us」会失去落点（§VI 有同义句，需改 §V 的指向） |
| §IV 六位小数口径的括注（`Every elasticity here … 0.01--0.03.`） | ~40 | **会打断 2 条活守卫**（锚 `at six decimals the`），且论文不再声明自己用哪个精度口径 |
| §IV `It is measured on different policies rather than by an intervention …` | ~22 | ε 的因果限定语离开 §IV（§VI 只有 tier 那一处的同义句，不是 ε 的） |
| §IV 的 `What this does and does not establish:` 首句（六配置/五段/无误差棒） | ~65 | §IV 将**在正文里没有任何 limitations 声明** —— 与 RTAS 的「supplement 不得用来绕过页数」直接冲突，**不建议** |
| §I 的「Nine variants of our own controller span three mechanistically distinct ideas …」 | ~44 | §I 不再说清被测的是什么（§V 的表 I 仍在） |
| §II `because the spread across those runs ($4.4$\,pp of SLO) is wider than the margin that decides our headline` | ~25 | §II 里这句是**唯一的散文陈述**（§V 只在脚注里说过同一件事） |
| §IV `its running count moves only from 1.73 to 1.75 while the step cost moves by 1.0\,ms` | ~19 | 「分母近零」这个判断的证据离开 §IV（判断句留着） |

上表合计约 **287 词**。加上本次已移出的 **492 词**，三个文件可到的下界约
**3365 − 492 − 287 ≈ 2586 词**（排版口径）—— 但那需要接受上表右列的每一处代价。

---

## 附：本次改动的机械自查

- 三个文件**没有任何一行被删掉后不同时写进本文件**（见每块的「原文（逐字）」）。
- 三个文件里的**限定语**：本次移出的限定语共 21 处（见各块「值现在在哪」里标
  `随本段移出`/`随本句移出` 的条目），**逐字记在本文档**；正文里**没有删掉任何一个**
  —— 被移走的都是随其论断一起走的（对照：本项目 2026-09-27 那条「**删掉一个数，而它
  支撑的论断还在正文里**」的反面）。
- `\cite{}` / `\ref{}` / `\label{}`：本次**没有删除任何一条**；块 IV-2 里的两处
  `\S\ref{sec:model}` 随该块移入本文档（`sec_model.tex` 仍被 §IV 别处引用，无悬空）。
- 判据定义基座（`eq:elasticity` 及其 ε、`1.1^{1-\epsilon}` 的含义、拟合 vs 分段、R²、
  两组各四个段值、循环性披露）：**一字未动**。

---

# 第二轮外移（2026-09-27）：§I 与 §IV 的两段（净移出 ~155 词）

**背景**：正文压到 11 页；改后实测 **12 页、参考文献标题在第 11 页、正文结束于第 11 页**。

## 块 N1：§I「为什么 τ 会动」（87 词）

**原文位置**：`sec_intro.tex` 的 `\subsection{Why}` 第 2 段。

**移出理由**：与 §III（正文）与摘要（正文）重叠——摘要已写
「it tracks the memory tier, not the controller---an association across five policies,
consistent rather than demonstrated」，§III 的 tier 表与 87.9--92.4 / 92.5--36.4 仍在正文。

**原文（逐字）**：

```latex
Why $\tau$ moves is recomputation, and whether recomputation happens tracks the
memory tier rather than the policy---an association across five policies, which
\S\ref{sec:model} calls consistent rather than demonstrated. Prefix \emph{reuse}
is bounded by the workload---75.5\% of the prompt tokens here, a bound no
configuration we ran reaches---and realization is where the tier enters
(\S\ref{sec:model}: 87.9--92.4\% of the bound held at $\overline{R}_{\text{busy}}$ 1.25 to
1.75 with a host tier, 92.5\% to 36.4\% without one, as recomputation). So the
same admission action costs different step time in the two tiers.
```

**正文留下的衔接**：无（整段移出）。其上一段（$\tau$ 的分解与 `50 of 156 minutes`）
与下一节「Contributions」各自完整；贡献条第 1 条仍写
「We identify the memory tier as what determines …」。

**值现在在哪**：
- `75.5\%` / `87.9--92.4\%` / `92.5\%` / `36.4\%` / `1.25` / `1.75`：**仍在正文**
  （摘要；§III 的 tier 裸表与 `reuse.csv` 段落；§VII 的 `75.5\%` 与 `92.5\%` / `36.4\%` 对照句）。
- 限定语 `an association across five policies … consistent rather than demonstrated`：
  **仍在正文**（摘要；§III `\paragraph{What the engine is doing when it is not decoding.}`
  的「we call it consistent, not demonstrated」；§VI 结论的「an association across every
  configuration we ran rather than an intervention」）。

## 块 N2：§IV「device-only 的悬崖不解释失败」（68 词）

**原文位置**：`sec_criterion.tex`，`the regime ends.` 之后那一段的**前两句**。

**移出理由**：与 §III 的 `The mechanism stops`（host tier 吸收重算，**留在正文**）
和 §VII 的第二负载节重叠；「criterion 不解释失败」在摘要
（`it neither returns the verdict nor explains the failure`）与 §IV 本段**末句**（留在正文）都有。

**原文（逐字）**：

```latex
The device-only cliff is a recomputation effect: those runs recompute what they
evict, while under HiCache the host tier absorbs it, so it does not survive on
the configuration our controllers use. So the criterion does \emph{not}
explain why they lose---on their own configuration they were not in a region
where added concurrency was self-defeating.
```

**正文留下的衔接**：

```latex
What the measurement does is rule
one explanation out; it does not establish the opposite
(\S\ref{sec:results}), and the failure is not that this workload denies
admission control its lever, but that we could not build a rule that uses it
well.
```

**值现在在哪**：本块**不含读数**（纯机制解释）。限定语
`the criterion does not explain why they lose` 与
`the failure is not that this workload denies admission control its lever,
but that we could not build a rule that uses it well`：**留在正文**（见上）。

## 块 N3：§IV 结尾的迁移小结（45 词）

**原文位置**：`sec_criterion.tex` 末段（`\section` 的最后一段）。

**移出理由**：§VII 的同名 `\paragraph{The direction transfers; the level and the place
do not.}` 已把同一件事写全；本段是复述加指向。

**原文（逐字）**：

```latex
We tested whether the curve transfers to a second workload
(\S\ref{sec:xtrace}). We report this as a boundary: the criterion identifies a
branch, and where we could check it elsewhere the sign of the branch
transferred while its location did not; it never explained the failure.
```

**值现在在哪**：本块**不含读数**。第二负载的读数（`86.3\%` / `74.8--57.5\%` /
`92.5\%` / `1.7344` / `3.4077`）**都在正文 §VII**。
限定语 `it never explained the failure` 与 `the sign … transferred while its location
did not`：**仍在正文**（§VII 的 `What this section does and does not buy`，「It costs us
the ability to locate the criterion's turn」「the second workload … still did not win there」）。
