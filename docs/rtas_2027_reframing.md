# RTAS 2027 定位重述（草案，待 codex 复核）

## 为什么必须做

RTAS 是**实时系统**会议。我们现在的稿子通篇是 **serving / 数据中心**语言：

| 现在用的词 | 读者是 serving 人时 | 读者是 real-time 人时 |
|---|---|---|
| SLO attainment % | 自然 | 需要翻译成「**deadline meet rate**」 |
| Pareto frontier (wall clock, SLO) | 自然 | 需要翻译成「**可达的（时延, 负载）区域**」 |
| busy-time throughput R̄/τ | 自然 | 需要翻译成「**服务率 / 每请求服务时间**」 |
| reuse bound / realization | 自然 | 与实时无关，是缓存指标 |
| 「准入控制」 | 自然 | **自然**（实时系统本来就有 admission control） |

**关键观察：我们的 10 s SLO 阈值本来就是一个 deadline。**
「SLO 达成率」= 「**deadline 满足率**」。「墙钟」= 「完工时间」。
所以这不是换结果，是**换词汇并突出时序面**。

## 我们的数据天然支持实时表述（这是最有说服力的一点）

ε = dlnτ/dlnR̄ **量的就是「并发上升时，每请求服务时间退化多快」** ——
这在实时系统里就是**服务时间的负载敏感性**，直接决定**能不能给时延界**。

| 实时系统的核心问题 | 我们的测量 |
|---|---|
| 加负载时，每请求时间**优雅退化**还是**崩溃**？ | 有 host tier：τ 从 27.0 涨到 29.8 ms（+10%）；无 host tier：27.4 → 36.7 ms（+34%） |
| 所以能承诺什么时延界？ | 有 host tier 时服务时间近乎不随负载变 ⇒ **可以给界**；没有时 ⇒ 给不出 |
| 为什么「内存没用满」不等于「可以加并发」？ | 因为**约束不是容量而是服务时间的负载敏感性** |

**这是论文最强的实时故事**：论文的机制主张（host tier 决定并发的代价）**就是**一个
实时主张（它决定时延界能不能成立）。

## 拟改的词汇表（正文全局）

| 现 | 改 |
|---|---|
| SLO attainment / SLO (\%) | **deadline meet rate**（首次出现时写「fraction of requests whose time-to-first-token meets a 10 s deadline」） |
| the 10 s threshold | **the 10 s deadline** |
| wall clock (minutes) | **makespan** 或保留 wall clock（首次定义） |
| the static envelope / frontier | the **latency–load frontier**（首次出现时定义） |
| $\overline{R}$, running count | 保留，但首次出现时点明它是**并发度** |
| busy-time throughput $\overline{R}/\tau$ | **service rate**（首次出现时给出等价式） |
| realized reuse / reuse bound | 保留（缓存指标），但在摘要里降权 |
| $\Delta$ (pp from the envelope) | **the margin by which an arm misses the achievable region** |

## 拟改的摘要（草稿）

> Agentic LLM sessions are long, multi-round jobs whose KV footprint grows every
> round. On a memory-constrained accelerator the pool binds, and admission
> control looks like the obvious way to keep per-request latency inside its
> **deadline**. We ask when it can be, and answer with a measurable property of
> the serving stack rather than a policy: busy-time **service rate** is
> $\overline{R}/\tau$, so raising concurrency by $f$ buys $f^{1-\epsilon}$, where
> $\epsilon$ is the elasticity of **per-step service time** to the concurrency
> $\overline{R}$. On a memory-bound agentic replay $\epsilon = 0.38$ to $0.61$,
> and it **tracks the memory tier, not the controller** — an association across
> five policies, consistent rather than demonstrated. That is a statement about
> **whether a latency bound can survive load**: with a host tier, per-step time
> rises only 27.0 to 29.8 ms as concurrency goes 1.25 to 1.75, so the bound can
> hold; without one it rises 27.4 to 36.7 ms and the **deadline meet rate**
> collapses from 92.5\% to 36.4\% as recomputation.
> The verdict is negative: nine controller variants spanning accounting, growth
> reserve and execution granularity, two more on the budget ceiling, and an
> independent congestion-based controller reimplemented — **none reaches the
> latency–load frontier** at a 10 s deadline; the best, measured twice, misses by
> $-0.30$ and $+0.22$\,pp, both inside the tie band. A tenth arm — the same
> controller revision, one expression changed — **does** cross, twice, by $1.3$
> and $2.2$\,pp: changing the *release* rule crosses the front there, changing
> the admission decision does not. Two more: on a second GPU with $9.7\times$ the
> pool the bound holds at twice the smaller card's concurrency; a second agent
> trace reproduces the direction but not the level, and having no host tier it
> tests the negative result, not the mechanism. Our criterion is a diagnostic: it
> neither returns the verdict nor explains the failure.

（±词数：原 264 词，本稿约 285 词 —— **摘要词数上限未在 RTAS 页面出现**，
IEEE 会议惯例 250，**定稿前要按目标 venue 的模板核**。）

## ⚠ 风险（必须与收益一起权衡）

1. **重述要动摘要 + 引言 + 术语，而篇幅已经紧到极限** ——
   换词本身不增词，但**首次出现处需要定义**（「deadline meet rate」要解释），
   估计 **+150~250 词**。在还差 1,510 词的情况下，这是**反向的**。
2. **重述可能引入新的不一致**：全文有 **834 项守卫**钉在现有措辞的锚上。
   改术语 = 大量锚失配 ⇒ 一批假 MISS + 一批静默失效的守卫。
   **本项目栽过最多次的就是这个**（「锚失配 = 那条检查不再检查任何东西」）。
3. **不做重述的风险**：RTAS 审稿人认为「这是 serving 论文」。

## 我的初步判断（待 codex 复核）

**做，但只做「低成本高信号」的部分**：

- **必做**：摘要 + 引言的**第一段与贡献条**改用实时词汇；**§II 首次定义处**加一句
  把 SLO 阈值点明为 deadline。**这是审稿人形成第一印象的地方。**
- **必做**：**Limitations 里加一条**「我们的时延界是 10 s 这个具体 deadline 下的，
  换 deadline 会改变判决」—— 这既是诚实的，也**直接回应实时审稿人最会问的问题**。
- **不做**：全文逐词替换（收益低、风险高、且 +词）。
- **理由**：审稿人读的是摘要、引言、图和结论。**在这四处说实时语言，
  比在正文 300 处改词有效得多，而且不破坏守卫锚点。**

⚠ 但我把这条判断交给 codex 复核 —— 特别是「只在四处改」够不够，
以及「+150~250 词」与「还差 1,510 词」的矛盾怎么解。
