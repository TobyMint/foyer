# 外移材料 —— `sec_model.tex`（§III Decomposing the Wall Clock）

本文档收集 2026-09-27 为适配 **RTAS 2027 技术正文 11 页硬限**而从 `paper/sec_model.tex`
**整块移出**的 6 段原文。移出经协调人 2026-09-27 裁决（方案 b）授权。

**移出纪律（本项目硬规矩）**：每一条都写明「**值现在在哪**」—— 标出该段承载的数字/限定语
是否在论文别处仍有出处。凡写不出「现在在哪」的，一律按「该恢复」处理。

**未移出（裁决明示保留）**：
- 能力控制段（tier 论证的收尾）；
- `consistent, not demonstrated`（§I 有 `\S\ref{sec:model}` 指向它）；
- 两张图的 `\caption`、图 2/图 7、全部公式、tier 表 —— 一个字未动。

**论文正文保留的指向**：移出后，`sec_model.tex` 在这些位置保留了指向本节其余部分的
最小衔接句（见每块的「正文留下的衔接」）。

---

## 块 1：round-1-and-later 命中率的另一种归一化

**原文位置**：原 `sec_model.tex` §*What tracks reuse is the tier, not the policy*，
`(75.5\% is the trace's bound …)` 那段之后、`Device occupancy does not explain the split`
之前（原第 186–191 行）。

**移出理由**：这是与主归一化并列的**第二种归一化**的稳健性检查，不是本节的
主证据链；其结论（同一种塌陷）已由 tier 表的 realization 列直接给出。

**正文留下的衔接**：无（整段移出，前后段仍各自完整）。

**原文（逐字）**：

```latex
The same collapse appears under a different normalization: the round-1-and-later
prefix hit rate falls from 80.8\% to 32.8\% across the device-only caps and holds
at 80.7\% to 78.7\% across the three host-tier caps of the controller's range. We
use the token-weighted all-steps convention because reuse and recomputation must
add to the prompt; neither convention is the trace's planned rate, which appears
here only as the bound.
```

**值现在在哪**：
- `80.8` / `78.7` / `77.3`(已先删) / `53.1`(已先删)：**全稿仅此一处** → 现只在本文件；
  数据出处为 `paper/data/hitrate.csv`。
- `32.8`：`sec_results.tex` 另有上下文含此值（非本节主张）。
- 限定语 `neither` / `only` / `bound`：随本段移出。

---

## 块 2：τ₁ 与重算的关联（r = +0.85）

**原文位置**：原 `sec_model.tex` §*What is left unexplained*，该 `\paragraph` 的第 1 段
后半（原第 250–257 行）。

**移出理由**：跨策略关联，非干预；本节标题主张（哪四条臂未被解释）由该段前半承载，
不依赖此关联。

**正文留下的衔接**：`\paragraph{What is left unexplained.}` 保留该段前半
（四条臂首测时被同机争用、已干净重测）与其括注，段落自足。

**原文（逐字）**：

```latex
Across the twenty-six we have step costs for, the $\tau_1$
spread does not look like a residual: it tracks their recomputation closely---a
straight line through them, $r = +0.85$ with a largest residual of
1.92\,ms. That is a cross-policy association like every other fit in this section,
not an intervention, and we report the association and not the line: the
coefficients are fitted to one configuration family, we have no derivation for them,
and the negative result does not rest on it either way, since the cancellation is
measured directly, not inferred from the mechanism.
```

**值现在在哪**：
- `+0.85`：`sec_background.tex` / `sec_results.tex` 另有 `0.85`（非同一量，需人工核）。
- `1.92`（最大残差）、`twenty-six`（集合规模）：**全稿仅此一处** → 现只在本文件；
  数据出处为 `paper/data/elasticity.csv` / `arm_running.csv`。
- 限定语 `does not look like a residual` / `not an intervention` / `not the line` /
  `no derivation` / `does not rest on it either way` / `measured directly, not inferred`：
  随本段移出。
- 同段的 `12--41\%`（争用抬高步成本）**仍在正文**，未移出。
- ⚠ `sec_discussion.tex:334` 有一句「prefix reuse is bounded by the workload, and whether
  that bound survives added concurrency is set by the memory tier---**an association across
  every configuration we ran rather than an intervention** `(\S\ref{sec:model})`」。
  这个 `\S\ref` 现在落在正文剩下的两处（引擎段的 `five points on five policies, not an
  intervention`；tier 段的 `a correlation we can name, on a pair confounded …`）——
  **落点仍然存在，但不再是这条 `r=+0.85` 的关联**。如果 §Discussion 那句指的是本条，
  要么回移本段，要么改 §Discussion 的指向。

---

## 块 3：计数器配对的告诫（definition, not finding）

**原文位置**：原 `sec_model.tex` §*What is left unexplained* 的第 2 段
（原第 259–268 行）。

**移出理由**：该段的告诫对象是 `reuse + recomputed = prompt` 这条**定义式**的用法，
属机制论证的元层面说明；机制段（*What the engine is doing* / *Where the mechanism stops*）
仍在正文。

**正文留下的衔接**：无（整段移出）。

**原文（逐字）**：

```latex
One caution: $\text{reuse} + \text{recomputed} = \text{prompt}$ is a definition,
not a finding, so ``the shortfall reappears as recomputation'' cannot by itself
establish the mechanism; independent of the partition, the evicted-token and
uncached-prefill counters are separate SGLang counters that track within
0.6--0.7\,M on all five device-only runs, and with a host tier the 1.3--15.2\,M gap
between them bounds what the host absorbed---tokens evicted and not
recomputed, equally consistent with the host having served them and with their
never having been asked for again. We can bound it, not identify it
(\texttt{eviction.csv}): those are tokens the \emph{device} had evicted and did not
recompute.
```

**值现在在哪**：
- `0.6--0.7\,M`、`1.3--15.2\,M`：**全稿仅此一处** → 现只在本文件；
  数据出处为 `paper/data/eviction.csv`。
- 限定语 `is a definition, not a finding` / `cannot by itself establish` / `bounds` /
  `equally consistent with` / `We can bound it, not identify it` / `did not recompute`：
  随本段移出。
- ⚠ `sec_discussion.tex` 的 §Discussion 引用了**同一条**告诫的另一半
  （`identities rather than measurements (\S\ref{sec:model})`）—— 若该处也需要
  「定义式不是发现」的展开，应把它一并指向本文件或回移本段。

---

## 块 4：配对实验的 margin / 机制 / 适用域（Scope）

**原文位置**：原 `sec_model.tex` §*What tracks reuse is the tier, not the policy*，
三处（原第 205–208、214–218、218–223 行）。

**移出理由**：裁决把「pair 的 confound/scope 细节」列为可移出块。
**注**：同属该行的 `The pair is not a paired experiment …` 一句**未移出** ——
收尾主张句 `… on a pair confounded in the two ways above` 的「two ways above」
指的就是那一句；移走它会让该指代悬空（本项目刚因悬空引用出过事故）。

**正文留下的衔接**：`…the criterion requires before it will read the comparison.`
之后直接接未移出的 confound 句，再直接接能力控制段；读起来仍完整。

**原文（逐字，三段）**：

```latex
The margin is small enough to matter: the two device-side runs differ by $2.4$ points,
an order of magnitude wider than the $0.14$ the verdict turns on, and less than
the 12.2 the confounded pair shows.
```

```latex
What differs is not how full the device pool is but what happens when it
overflows: without a host tier an evicted prefix is gone and must be recomputed,
with one it is demoted and read back. The pool is the binding resource and the tier
sets it---these two runs differ in the tier and in nothing we can see on the engine
side.
```

```latex
\emph{Scope}: both sit at the same running count (1.51 and 1.56), so this
identifies the \emph{level} of realization at one operating point, not how it moves
as concurrency rises; the slope is measured on the segment elasticities of
\S\ref{sec:criterion}, where the host tier keeps $\epsilon$ below one while the
device-only curve crosses it---that curve, not this pair, is what the title's claim
rests on.
```

**值现在在哪**：
- `2.4`（margin 句）：**仍在正文**（同段前文「its two runs differing by 2.4\,pp」）。
- `0.14`、`12.2`、`1.51`、`1.56`：**仍在正文**（前文预注册句与重复对句）。
- 机制句与 Scope 句**没有独有数字**。
- 限定语 `nothing we can see` / `not how it moves` / `not this pair`：随本块移出。
- `\S\ref{sec:criterion}` 这个指向随 Scope 句移出；`sec_criterion.tex` 本身仍以
  `eq:elasticity` 与 `Fig.~\ref{fig:cancel}` 被正文引用，不产生悬空引用。

---

## 块 5：`bres` 的证据（空转被追回但不改善判据）

**原文位置**：原 `sec_model.tex` §*Why idle time exists, and why recovering it does not pay*，
最后一 `\paragraph` 的前半（原第 305–310 行）。

**移出理由**：该臂的完整读数在 `sec_results.tex` 有出处；本节的论证只需
「remedy works and does not pay」与收尾的「Idle is recoverable in part」。

**正文留下的衔接**（保留的两句，**限定语 `does not pay` 与
`what it does not do is improve the criterion` 一并留在正文**）：

```latex
The obvious remedy---keep more sessions live so that someone is always ready---is
what \texttt{bres} does, and the clean measurement of it says the remedy works and
does not pay: what it does not do is improve the criterion (\S\ref{sec:results}).
```

**原文（逐字，被移出的部分）**：

```latex
it cuts idle by 9.5 minutes against its own baseline and its busy time
falls as well, by 15.5, so the arm finishes 25.4 minutes earlier, but its SLO falls
3.9\,pp and its distance below the static front is unchanged (\S\ref{sec:results}).
```

（为可读，上文把该句与保留的衔接句合起来读作：
「…the remedy works and does not pay: it cuts idle by 9.5 minutes … unchanged
(\S\ref{sec:results}).」）

**值现在在哪**：
- `9.5`：`sec_discussion.tex` / `sec_results.tex` / `sec_intro.tex` / `sec_a100.tex` 均有。
- `25.4`：`sec_results.tex` 有。`3.9`（pp）：`sec_results.tex` / `sec_intro.tex` 等有。
- `15.5`：`sec_xtrace.tex` 有（需人工核是否同一量）。
- 限定语 `does not pay` / `what it does not do`：**留在正文**；
  `its distance below the static front is unchanged` 随本块移出。

---

## 块 6：被撤回的主张（空转率不随并发单调下降）

**原文位置**：原 `sec_model.tex` §*Why idle time exists, and why recovering it does not pay*，
第 3 段（原第 297–303 行）。

**移出理由**：裁决列为可移出块。该撤回**另有记录**：`sec_discussion.tex` 的撤回清单
第 5 条（「空转率随并发单调下降」），且 `sec_criterion.tex` / `sec_results.tex` /
`sec_discussion.tex` 均含 `monoton` 上下文 —— 撤回事实在论文别处仍成立。

**正文留下的衔接**：无（整段移出）。其上一段（两个同 R̄ 配置的空转差）与
下一段（remdy 段）各自完整。

**原文（逐字）**：

```latex
We note one claim we had to drop here: an earlier draft reported that idle fraction
falls monotonically with mean concurrency, and with the full data it does not---on
the busy-conditional measure this section uses throughout, \texttt{no gate, no
resv.} at $\overline{R}_{\text{busy}}$ 1.68 idles 20.7\% while \texttt{cap4} at 1.65
idles 10.4\%, more concurrency and \emph{more} idle, the reverse of the reported
trend. The weaker statement that survives is the one we use---the stretches are
structural and long.
```

**值现在在哪**：
- `1.68` / `20.7\%` / `1.65` / `10.4\%`：**全稿仅此一处** → 现只在本文件；
  数据出处为 `paper/data/arm_running.csv`（`busy_conditional` 口径）。
- （同段早先已删的旁注 `1.33` / `1.48` 在 `sec_results.tex` 有同值上下文。）
- 限定语 `it does not` / `the weaker statement that survives`：随本段移出；
  撤回本身见 `sec_discussion.tex` 撤回清单第 5 条。

---

## 未移出但同属原候选清单的两块（裁决保留）

1. **能力控制段**（`A capacity-controlled version … capacity is not occupancy …`）：
   留在正文，作为 tier 论证收尾。
2. **`What the engine is doing when it is not decoding` + `Where the mechanism stops`**：
   留在正文 —— §I 明确 `\S\ref{sec:model} calls consistent rather than demonstrated`，
   移出会使该指向失去落点。

## 若要继续压缩：剩下两个候选（本次未动）

| 候选 | 词数 | 代价 |
|---|---|---|
| `The pair is not a paired experiment …`（confound 句） | ~55 | 收尾主张句的 `confounded in the two ways above` 失去指代，需改写该短语 |
| `Four of the arms above … values above are the clean ones.`（四条臂披露） | ~65 | 该 `\paragraph{What is left unexplained.}` 将只剩标题、无正文 |

---

# 第二轮外移（2026-09-27）：§III 的两段（净移出 ~290 词）

**背景**：正文压到 11 页；改后实测 **12 页、参考文献标题在第 11 页、正文结束于第 11 页**。

## 块 M1：`A refutation we had to withdraw.`（113 词，整段）

**原文位置**：`sec_model.tex` 的 `\subsection{What tracks reuse is the tier, not the policy}` 末段，在 `\paragraph{What is left unexplained.}` 之后。

**移出理由**：撤回记录的展开；§VI 的七条撤回清单已含「a refutation that was itself refuted」，
且清单句「Each is reported with its evidence in the audit file named in the supplement」仍在正文。

**原文（逐字）**：

```latex
\paragraph{A refutation we had to withdraw.} An earlier revision withdrew this
mechanism outright, on two checks that were both wrong: that total prefilled tokens
equalled the trace's planned prefill to a ratio of 1.00---but
\texttt{prompt\_tokens\_total} counts the full submitted prompt \emph{including}
its cached portion, so it equals the sum of prompt lengths by construction and
cannot detect recomputation, while the uncached count used above can---and that
SGLang reported no retractions, but radix-cache eviction is not a retraction: that
counter is for running requests preempted mid-flight. We record the episode because
it is the same failure mode as the segment argument of \S\ref{sec:bg}: a check that
looks like a measurement but is an identity.
```

**值现在在哪**：
- `1.00`（`prompt\_tokens\_total` 与计划 prefill 之比恒为 1 的**恒等式**）：现只在本文件；
  结论（恒等式不是测量）在 §VI 的撤回清单里；`\S\ref{sec:bg}` 的段论证仍在正文。
- 限定语 `on two checks that were both wrong` / `a check that looks like a measurement
  but is an identity`：**随本段移出**。

## 块 M2：`Why idle time exists, and why recovering it does not pay` 的前两段（152 词）

**移出理由**：第 1 段与 §I 的空转段同义（§I 仍在正文，含 `66.1--69.5\%` 与
`0.34\,s` / `15.8--16.9\,s` / `18\%`）；第 2 段的对照读数与 §V 的
「same median occupancy … 19 minutes faster」重叠；`bres` 的证据块早已外移（本文件块 5）。

**原文（逐字）**：

```latex
An individual idle stretch is a property of the workload, not of the controller: a
session in a tool wait holds its permit and its KV but issues no request, and with
only about two live sessions the probability that all of them wait at once is
substantial. The stretches are an order of magnitude longer than the 2\,s control
cycle, and no controller can shorten a gap that the tool set.

How much idle a \emph{run} accumulates is a different matter, and there the
controller is not off the hook: idle accumulates when every live session happens to
be parked at once, and an admission policy sets how many sessions are live.
\texttt{horizon}=1 (1.52) and \texttt{cap3}+HiCache (1.51) have the same mean
running count yet idle 36.7 and 24.1 minutes---a 52\% difference at matched
concurrency, and 12.6 of the 19.4-minute wall-clock gap between them is that idle
difference rather than step cost.
```

**正文留下的衔接**（小节标题保留，首段改写）：

```latex
Some idle is structural: a session in a tool wait issues no request, and an
admission policy sets how many sessions are live, so an individual stretch is the
workload's and how much a \emph{run} accumulates is not.
```

**值现在在哪**：
- `1.52` / `1.51` / `36.7` / `24.1` / `52\%` / `12.6` / `19.4`：**全稿仅此一处** → 现只在本文件；
  出处 `paper/data/decomp.csv`、`paper/data/arm_running.csv`、`paper/data/idle_pooled.csv`。
- 限定语 `a property of the workload, not of the controller`：**留在正文**（改写，见上）。

## 块 M3：结构性的补救（`Idle is recoverable in part` 前一句，57 词）

**移出理由**：读数展开（`66` / `47.4` / `37.9`）；末句 `Idle is recoverable in part;
recovering it is not what pays.` 与 `bres` 那句**留在正文**。

**原文（逐字）**：

```latex
The structural remedy would be to have the engine work during a wait: for the
waiting session there is none---its next round does not exist until its tool
returns---but for the \emph{pool} there is, since the admission queue holds a median
of 66 sessions, and \S\ref{sec:results} measures what happens when a policy runs
one: the charge-free base arm cuts total idle from 47.4 to 37.9 minutes, and it does
not move the verdict.
```

**正文留下的衔接**：

```latex
Idle is recoverable in part; recovering it is not what pays. The per-run idle
decomposition, and the structural remedy of giving the engine work during a wait,
are in the supplement.
```

**值现在在哪**：
- `66`（准入队列中位）：`paper/data/backlog.csv`；该读数此前在正文有守卫
  （`§VII pois200_foyer_push_25 队列中位`，已退役）。
- `47.4` / `37.9`（charge-free base arm 把总空转从 47.4 压到 37.9 分钟）：
  **全稿仅此一处** → 现只在本文件；出处 `paper/data/decomp.csv`（base 与 resident base 两条的 idle 分钟）。
- 限定语 `it does not move the verdict`：**留在正文**（`recovering it is not what pays`）。

---

## 本轮消费掉的候选（更新上面那张「若要继续压缩」表）

| 上表候选 | 本轮处置 |
|---|---|
| `The pair is not a paired experiment …`（confound 句） | **未动**：收尾主张句的 `confounded in the two ways above` 仍指向它 |
| `Four of the arms above … values above are the clean ones.` | **未动**：`What is left unexplained.` 段仍是正文里唯一的共租披露处（另有两条活守卫） |
| （上表未列）`A refutation we had to withdraw.` | **已外移**（块 M1，113 词） |
| （上表未列）`Why idle time exists …` 前两段 + 结构性补救句 | **已外移**（块 M2 / M3，209 词）；小节标题、`bres` 那句与「Idle is recoverable in part」留在正文 |
