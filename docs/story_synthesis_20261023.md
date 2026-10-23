# 论文故事合成（2026-10-23）

> 输入：四份调研（`survey_agentic_serving_*`、`survey_kv_memory_*`、
> `survey_scheduling_theory_*`、`survey_measurement_hooks_*`，共 ~50 篇）
> + 我们自己的 trace/run 证据 + 用户定调（轻数据、重故事、听起来有道理）。
> 本文件是"故事"的单一事实源；旧的 `story_arcs_20261023.md` 保留为演化记录。

---

## 0. 一句话论点

> **Admission should be a feasibility test, not a threshold.**
> 现有系统把"内存不够"当**放置/驱逐**问题（于是必须预测未来：steps-to-execution、
> 长度、Beta 先验、OBR）；长会话 agent 的真实结构是**可挂起**的。承认"会话可在轮边界
> 暂停且保状态"之后，准入就变成**容量核算**：谁能在卡上、住哪层、复活要付多少搬运——
> **预测需求消失，剩下的是可行性判定与代价核算。**

三个关键词：**capacity accounting**（可行性）、**reversible suspension**（状态）、
**revival breakeven**（代价）。

---

## 1. 四路调研合并出的 10 条叙事规律

1. **标题造“病理名词”**，不用形容词（thrashing / end-of-turn eviction /
   hold-all-live ceiling / re-read tax）。名字本身就是 claim 的载体。
2. **摘要四拍**：现象 → 为什么结构性失败 → 命名 insight → 单一倍数；
   **我们加第五拍：边界/反例**——调研里几乎没人写，这是我们能加分的地方。
3. **Intro 第二段必放一个量化反直觉**：加 agent 反而更慢（CONCUR）、
   0.39s vs 4.3s（Talaria）、88×（PerBank）。我们的是 **0.21s vs 18.6s** 与 **12.9× 超订**。
4. **gap 句式在本族是“粒度错了”**：request→agent→program→session。
   ⚠ 但 **agent 级准入已经被 CONCUR 占住**（PDF 内改题 *Proactive Agent-Level
   Admission Control*）；**per-tier admission 已经被 MORI 占住**。
   所以我们的 gap 不能再说“粒度/层级”，而要说：
   **“即使选对了单位，准入仍是个阈值控制器：没人写出可行集，也没人给挂起/复活定价。”**
5. **机制固定三件套**：两个调度原语 + 一个成本模型/控制器 + 一个廉价旋钮。
   我们：`admit / suspend / resume` 三个原语 + 容量账本 + 旋钮 `ρ`（容量预算）。
6. **分析层三选一**：成本分解、breakeven、不变量/上界；**几乎没人做真排队论**。
   我们做后两种：**容量可行集上界** + **OBR 的会话级 breakeven**。
   这是叙事上稀缺的（调研原话：“你们那条 A1/A3/A4 的路线在叙事上是稀缺的”）。
7. **实验骨架**：引擎 + 一个更聪明的同类 + 自己的消融版；单一 headline；高压区；
   机制靠“固定阈值不行”或扫旋钮。我们只有三条 run（request 级 / agent 级 / 我们），
   所以“自消融”要靠**日志反事实**（从 controller/steps 日志离线归因），不额外跑。
8. **先命名失效模式再修**（Mooncake 自承早拒导致 P/D 反相振荡）。
   我们主动写：准入会抬高引擎 idle；不是所有会话都值得挂起；缓存足够大时收益消失。
9. **不要宣称**：agent-level admission（CONCUR）、per-tier admission（MORI）、
   working-set admission（EfficientAgent）——这些都已存在。
10. **集体空白就是我们的位置**：准入的**可行性判据** + **挂起态的存放/复活代价**
    + **单卡内存墙下的 SLO**——四路调研都指向这里。

---

## 2. 定位表（related work 直接可用）

| 工作 | 他们占住的说法 | 他们没做的 | 我们的关系 |
|---|---|---|---|
| **CONCUR** 2601.22705 | agent 级准入、middle-phase thrashing、AIMD | 每会话容量核算、可行集、挂起态成本、单卡 | 我们不说"agent 级"，我们做**可行性 + 状态** |
| **Continuum** 2511.02230 | KV TTL、CacheMissCost、队列延迟 | 容量可行性、挂起/复活代价 | 我们是它的"容量版"：TTL 是启发式，我们是可行性界 |
| **ThunderAgent** 2602.13692 | LLM Program、Space-Time Product 五分解、上界 | 内存受限单卡、准入可行性 | 借它的成本分解句式，但对象换成 KV residency |
| **Talaria** 2607.17181 | session 连续性、soft reservation、测量开场 | 容量上限、拒绝语义、复活代价 | 我们补"可行性 + 代价" |
| **MORI** 2606.00866 | **per-tier admission**、idleness 谱 | 硬容量账本、SLO、挂起语义 | 我们的差异必须写"核算 + 可逆挂起"，不是 tier |
| **EfficientAgent** 2609.33762 | working-set admission、**OBR** | 会话级挂起、真引擎、SLO | 我们把 OBR 扩一维（会话还剩多少轮） |
| **kvlive** 2609.16215 | "机制容易、放置难"、oracle 负结果 | 真引擎、准入 | 我们用它的负结果支撑"挂起 breakeven" |
| **KV Residency** 2610.22863 | 生产级容量天花板（501.8 TB、p99>80GB、5.6%） | 单卡、SLO、准入、真引擎 | 我们回答"天花板下面单卡怎么办" |
| **ConServe** 2606.01839 | 换调度单元而非加预测器 | 换的是 unit；我们换的是 **state** | 同手法、不同对象 |
| **Mooncake** 2407.00079 | 过载早拒绝、SLO 当负载 | 拒绝即丢状态；我们是挂起 | 我们是"可逆的拒绝" |
| **KVFlow** 2507.07400 | steps-to-execution 预测 | 预测需求本身 | 我们不预测，核算 + 挂起 |
| **Pensieve** 2312.05516 | "无状态是结构性病根" | 单卡容量、准入、SLO | 我们的"状态保留"史前史引用 |
| **vLLM/SGLang/HiCache/LMCache** | 分页/前缀树/分层/外部 KV 层 | 都止步于"分配/放置" | 我们补"准入 + 复活定价" |

**一句话定位**：
> Prior work tells us where KV should live; we ask **who is allowed to hold it, and what it
> costs to bring it back** — a feasibility test with a price, under a single-card memory wall.

---

## 3. 最终故事

### 3.1 标题候选

1. *Admission Is a Feasibility Test, Not a Threshold: Capacity-Accounted, Reversible
   Session Admission for Agentic LLM Serving*
2. *Don't Predict, Account: Reversible Sessions for Agentic LLM Serving*
3. *The Feasible Set: Capacity Accounting and Revival Pricing for Agentic Serving*
4. *Suspend, Don't Discard: Capacity-Accounted Admission for Long-Horizon Agentic Serving*
5. （保守）*When a Session Does Not Fit: Capacity-Accounted Admission for Agentic LLM Serving*

### 3.2 摘要骨架（四拍 + 边界；数字落地前标 pending）

```
Agentic sessions are long-lived: each returns tens of times with a context that grows to
48–93K tokens. On a single 24GB GPU the working set of 19 such sessions is 12.9× the KV
pool — the pool holds 1.48 median sessions. Serving each return as an independent request
re-reads the prefix every round (12× re-read tax) and wastes up to 12.7× of the prefill work.
Existing fixes treat this as a placement problem and therefore predict the future; we make
sessions suspendable. At a round boundary a session's KV is demoted, and a later round is
restored by copy rather than recomputation. Admission then becomes a feasibility test over a
capacity ledger — who fits, on which tier, at what revival cost — and the threshold
disappears. We derive a capacity bound and a session-level revival-vs-recompute break-even,
and instantiate the design on SGLang. Against request-level serving and a Concur-style
agent-level controller, [pending: we measure X on the long-session replay], and we state
when suspension does not pay. [pending numbers]
```

### 3.3 Intro 五段弧

1. **P1 现象**：长会话、多轮、上下文增长；12.9× 超订；池子只装 1.48 个中位会话。
2. **P2 量化反直觉**：工具等待 0.21s（中位）vs 18.6s（均值），>10s 的间隔只占 15.6%
   却吃掉 95% 停放时长；每步 prefix 42K vs append 1.1K（38×）；naive 服务每轮重读。
3. **P3 为什么现有修法结构性不够**：
   分页/前缀树/分层（vLLM/SGLang/HiCache/LMCache）解决分配；
   TTL/放置（Continuum/KVFlow/MORI/EfficientAgent）必须预测未来；
   agent 级反馈（CONCUR）在抖动后才反应；过载拒绝（Mooncake）丢掉状态。
   **没人写可行集，也没人给复活定价。**
4. **P4 Insight**：把会话做成**可挂起**；准入 = 容量核算 + 可行性；增长用覆盖界
   而不是点预测；挂起/重算用 breakeven 而不是一律搬运。
5. **P5 Contributions**（三条）+ 结果 headline + 边界。

### 3.4 贡献（三条，避免与近邻撞）

1. **Formulation**：把"可挂起会话的准入"写成**容量核算可行性问题**：
   可行集 `F(t) = {s : Σ W_s(t) + ĝ_s ≤ C_eff}`，给出上界与准入规则；
   替代"阈值/反馈"式准入。
2. **Mechanism**：容量账本 + 命名许可 + 轮边界可逆挂起 + 覆盖有界的增长估计；
   在 SGLang/runner 上落地，计划即执行。
3. **Analysis & evidence**：容量可行集上界 + 会话级 revival/recompute breakeven
   （OBR 的会话维度扩展）；真引擎对比 request 级与 Concur 式 agent 级；
   主动给出"何时不赚"的负结果与边界。

### 3.5 11 页章节计划

```
1 Intro                 P1–P5；三条贡献；一张“超订/重读”图
2 Background            会话解剖；工作集/池子；工具等待重尾；12.7× 上界
3 Model                 会话、KV 增长、层级、复活成本；可行集定义；假设
4 Design                M1 账本+命名许可；M2 可逆挂起；M3 覆盖有界增长；M4 成本模型（含旋钮 ρ）
5 Analysis              Prop1 可行集上界；Prop2 会话级 breakeven；Prop3 覆盖保证下的准入安全
6 Implementation        SGLang/runner 改动；permit 协议；suspend/resume 语义
7 Evaluation            三臂；指标；逐会话；busy/idle 分解；日志反事实归因；负结果/边界
8 Related work          按 §2 定位表写，正面承认 CONCUR/MORI/EfficientAgent
9 Discussion            单卡/单 trace/单 SLO 的边界；“什么时候不赚”
10 Conclusion           一条可复用原则：feasibility, not threshold
```

### 3.6 分析（三条，正文一行、证明进附录）

- **Prop 1（可行性上界）**：给定 `C_dev`、`C_host`、每会话工作集 `W_s`，
  任意时刻可同时活跃的会话数 `|F(t)| ≤ C_eff / W̄`；我们的 19 会话、1.306M 工作集
  给出 `|F| ≈ 1.48`。⇒ 准入不是"调并发数"，是"选可行子集"。
- **Prop 2（会话级 breakeven）**：
  `T_revive = n·β/B + τ`，`T_recompute = P(ctx)`；
  只有当 `T_revive < p_return · T_recompute` 才值得挂起（`p_return` 由剩余轮数/工具等待
  分布给出）。⇒ 这是 OBR 加"会话还会不会回来"一维。
- **Prop 3（覆盖保证）**：若增长估计满足覆盖率 `1−δ`，按上界准入的容量违规概率 ≤ δ；
  ⇒ 把"安全垫"从拍常数变成可陈述的保证（假设写清楚，理论不外推）。

### 3.7 评估叙事（只有三条 run，靠日志补齐）

1. **主表**：A request 级 / B Concur 式 / C 我们；makespan、会话中位/p90、
   deadline miss、工作量、命中率。
2. **一张时间线图**：某个会话的 admit/pause/resume 与引擎忙闲，解释机制怎么工作。
3. **分解**：busy/idle + uncached prefill；回答"我们不是靠塞满引擎赢的"。
4. **日志反事实**（不占 GPU）：从 controller/steps 日志估计"如果只限制并发、不挂起"
   能拿到多少 → 把"状态保留"的贡献与"少并发"分开。
5. **负结果/边界**：短会话/高带宽/缓存足够大时，挂起不赚；`T_revive ≥ T_recompute`
   的判据 + 参数敏感性（解析，不跑新实验）。

### 3.8 不能说的话（纪律）

- ❌ "首次提出 agent-level admission"（CONCUR 已占）；
- ❌ "per-tier admission 是我们的创新"（MORI 已占）；
- ❌ "working-set admission 是新的"（EfficientAgent 已占）；
- ❌ 与静态并发上限对比（用户明确不要）；
- ❌ 宣称 3–4× 或统计显著性（n=1）；
- ❌ 把 10 月旧控制器数据当新结果（只能写"历史参考"）。

---

## 4. 现有证据 → 论文 claim（全部待新三臂确认）

| Claim | 证据来源 | 状态 |
|---|---|---|
| 长会话工作集 12.9× 超订、池子只装 1.48 个 | `long19_default/steps.jsonl` | ✅ 已复算 |
| 12× 重读税、38× prefix/append | 同上 | ✅ 已复算 |
| 12.7× 理论上界 | 建表 602 步 | ✅ 已复算 |
| 工具等待重尾（0.21s vs 18.6s；15.6% 吃掉 95%） | 同上 | ✅ 已复算 |
| A/B/C 三臂差异 | 新 run（C 在跑，A/B 等卡） | ⏳ |
| busy/idle 分解、device/host 命中 | 三条 run 的 metrics/日志 | ⏳ |
| 挂起 vs 重算 breakeven | 解析 + 机器参数 | ⏳ 分析 |
| 日志反事实归因 | controller/steps 日志 | ⏳ 分析 |

---

## 5. 下一步（按优先级）

1. 等 C 跑完、A/B 起跑；三条齐后按 §3.7 出表。
2. 写 `paper/main.tex` 新骨架（11 页，按 §3.5）；先用占位数字，拿到数据再填。
3. 用 `hypothesis-generation` 模板把 §4 升级成正式 claim/evidence ledger + prereg。
4. 写 §3 模型与 §5 分析的三条命题（正文一行、附录证明）。
5. 四份 survey 里的 citations 逐个回原文核（项目纪律：不许二手转述）。
