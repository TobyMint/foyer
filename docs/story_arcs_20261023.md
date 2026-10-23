# 论文故事：候选叙事与选择（2026-10-23 起草）

> 用户 2026-10-23 定调：**轻数据、重故事；一定要“听起来很有道理”**。
> 本文件只做一件事：把“故事怎么讲”拆成可执行的叙事结构，等 4 路文献调研回来后细化。
> 注意：“轻数据”不是不要数据——每个数字仍然必须真实；“轻”指的是**数据服务于论证，而不是罗列测量**。

## 0. 我们能用的素材（只能用这些）

```
workload    19 会话 / 602 轮；终态工作集 1.306M token = 池（101,502）的 12.9 倍
            池只装得下 1.48 个中位会话；16/19 个会话终态 > 池一半，5 个 > 80%
            单轮上下文 中位 48.4K / p90 71.1K / max 92.8K
            每步 prefix p50 42K vs append p50 1.1K（38×）；prefix 重读 24.4M vs append 2.0M（12×）
            若每轮全量重算：12.7× 的理论浪费上界（必要 2.30M vs 最坏 29.2M；与 12.9× 不同量）
            工具等待 p50 0.21s / 均值 18.6s / p90 40s / max 300s；
            且 >10s 的间隔只占 15.6%，却吃掉 95% 的停放时长
机制        容量核算 + 命名许可；轮边界状态保留挂起（HiCache device/host）
            在线增长估计（EMA + 覆盖保证）；按 KV 层级定价（分析件）
旧实测     10 月旧控制器：request 级 vs 我们 1.43× / 3.39× / 1.30×（新三臂落地前只能当“历史参考”）
待补        新三臂 A/B/C 各一次（n=1）；device/host 命中分解；busy/idle 分解
不做        hc ratio 变化、noHC 消融、多 trace、重复实验
```

## 1. 什么叫“听起来有道理”（可操作清单）

1. **开场一个两难/反直觉**，不是“我们做了一个系统”。
2. 把问题压缩成**一个单位** + **一个代价模型**：单位 = 会话的 KV 工作集；
   代价 = KV 所在层级（device / host / 重算）。
3. 机制 = **3–4 条设计原则**，每条都能推出一个**可检验的预测**。
4. 分析 = **2–3 个简单、能对拍实测的公式**，不是复杂证明：
   复用上界、复活 vs 重算的 break-even、容量方程。
5. 实验 = **先讲一个会话/一小段时间线里机制怎么工作**，再给聚合表；
   baseline 用 request 级 / agent 级两级，且是“现有方法”，不是稻草人。
6. **诚实边界**：主动写“什么时候不成立”（缓存足够大、上下文太长、SLO 不同）——
   这反而让故事可信。
7. 结论 = 一个**可复用的设计原则**，不是“我们快 X 倍”。

## 2. 四条候选故事

### Arc A — “The Session Is the Unit”（单位优先；推荐主骨架）

- **Hook**：A coding-agent session is not a request. It returns 20–80 times, its
  context grows to 48–93K tokens, and on a 24GB GPU the working set of 19 sessions is
  **9× the KV pool**. Serving it as independent requests wastes up to **12.7×** of the
  prefill work.
- **Gap**：request 级调度看不见“会话”；agent 级反馈（Concur 式）看见了并发，
  但没有容量模型——它只能对“缓存快被打坏”做反应，不能预知每个会话还要多少 KV。
- **Insight**：准入的单位是**会话的 KV 工作集**；准入必须**可逆**（挂起/复活），
  否则“限制并发”就只是把会话赶到门外。
- **Mechanism**：容量账本 + 命名许可 → 计划即执行；轮边界挂起（KV 下沉）；
  增长估计 + 覆盖保证；按层级定价。
- **Analysis**：(i) 复用上界 `(D+P(ctx))/(D+P(inc))` → 1.4–2.4×，与实测 1.43× 对拍；
  (ii) 复活 vs 重算的 break-even；(iii) 容量方程。
- **Eval**：A/B/C 三条 run；makespan、会话端到端、deadline miss、工作量、命中率。
- **Pros**：直接对应证据；容易把“为什么现有不行”写成结构性论证。
- **Cons**：最“正常”的故事，需要在分析和实验上做出差异。

### Arc B — “Price the Tier”（成本模型优先；推荐作为 A 的核心分析章）

- **Hook**：Keeping a session alive costs different amounts depending on **where its KV
  lives**：device 命中免费、host 命中要搬运、被驱逐后整段重算最贵。现有系统把
  “命中/未命中”当二值，或只对缓存压力做反应——**没有给 residency 定价**。
- **Insight**：准入 = 在容量约束下“租”一段 KV residency；驱逐/复活是搬运成本与
  重算成本的比较。
- **Analysis**：有效容量 `C_eff = C_dev + C_host·(1 − β/P)`（β=搬运、P=重算）；
  break-even 条件；由成本模型直接推出“什时候该多放一个会话”。
- **Pros**：最有“理论感”；能用 device/host 命中数据支撑（不需要 hc 变化实验）；
  能把“HVAC 式”实现细节上升成 principle。
- **Cons**：需要从 metrics 拿到 device/host 分解；没有对照实验时，靠分析说服。

### Arc C — “Make Suspension Reversible”（系统原语优先）

- **Hook**：Serving systems pause at request granularity; when the agent comes back,
  its state is gone. But the agent's round boundary is a natural checkpoint.
- **Insight**：把“会话挂起”做成一等原语：suspend = KV demote to host；
  resume = page-in rather than recompute.
- **Pros**：画面感强、systems 味重；“像 OS 进程/页缓存”的类比容易讲。
- **Cons**：单独讲会被问“和 Concur 的 pause/resume 有什么不同”，需要 A/B 数据撑。

### Arc D — “The Missing 12.7×”（测量/谜题优先；只做 Intro 的 hook）

- **Hook**：The trace says 12.7× of the prefill work is avoidable; a real system wastes
  ~10× of it, and sometimes kills the session.
- **Pros**：开场极强，数据已有。
- **Cons**：容易滑回“实验报告”；适合做前两段，不做全文骨架。

## 3. 推荐组合与标题

**主骨架 = A（单位）+ B′（不预测，改挂起），C 作为机制章的核心；「价格」只作成本模型，
不再当主创新点**（MORI 已经占了“per-tier admission”这个说法，见 §9）。D 只做 Intro 的 hook。

标题候选（按 §9 的定位更新）：
1. *Don't Predict the Future: Reversible Sessions and Capacity-Accounted Admission for Agentic Serving*
2. *Suspend, Don't Predict: Session-Level Admission for Long-Horizon Agentic LLM Serving*
3. *The Session Stays: Capacity Accounting with Reversible Suspension for Agentic Serving*
4. （保守版）*When a Session Does Not Fit: Capacity-Accounted Admission for Agentic LLM Serving*

11 页章节计划：
```
1 Intro            hook（D）+ 为什么 request/agent 级都不够 + 3 条贡献
2 Background       会话解剖（轮数/增长/工具等待）+ 12.7× 上界 + 工作集/池子比
3 Model            容量、层级、复活成本、增长过程；假设与记号
4 Design           M1 账本+命名许可；M2 可逆挂起；M3 增长估计+覆盖；M4 层级定价；M5 公平
5 Analysis         三条可对拍的公式 + “什么时候控制才划算”
6 Implementation   SGLang/runner 上改了什么
7 Evaluation       A/B/C；指标；逐会话；busy/idle 分解；边界
8 Related work     与 Concur/Continuum/Maestro/... 的边界（不写静态对照那类）
9 Discussion       局限与适用边界
10 Conclusion      一条可复用的设计原则
```

## 4. Claims → Evidence（草稿）

| 主张 | 证据 | 状态 |
|---|---|---|
| 无控制会浪费 ~10× prefill、甚至打死会话 | A 臂（新跑）+ 10 月数据 | 待新数据 |
| 我们比 request 级更快/更省/更达标 | C vs A | 待新数据 |
| 我们比 agent 级（Concur 式）更快/更省 | C vs B | 待新数据 |
| 收益机制 = 容量核算 + 状态保留 | busy/idle 分解 + device/host 命中 | 分析现有日志 |
| 代价与 KV 所在层级有关 | device/host 命中 + 搬运/重算参数 | 分析现有日志 |
| 增长估计有覆盖保证 | 离线回放 steps 日志算覆盖率 | 待实现 |
| 边界：缓存足够大时收益消失 | 10 月 hc8 数据（仅作背景，不跑新实验） | 文章取舍待定 |

## 5. 等 4 路文献调研回来后要补的

- 4 份 `docs/survey_*_20261023.md`：agentic serving / KV memory / scheduling+theory /
  measurement+hooks。
- 从中提炼：标题公式、摘要模板、Intro 的 hook 写法、机制命名法、analysis 范式、
  evaluation 叙事顺序；再回来改本文件。
- 用 `hypothesis-generation` 的模板把上表升级成正式 claim/evidence ledger + prereg。

## 6. 不占 GPU 就能补的“故事证据”

1. 从 C 臂 metrics 解析 device/host 命中 → 支撑 Arc B；
2. busy/idle 分解（C 的 busy 时间 vs A）→ “我们不是靠塞满引擎赢的”；
3. 一个会话的 timeline（轮次 vs 准入/暂停）→ 机制图；
4. 从 trace 重算 12.7× 与工作集/池子比 → Intro 数字；
5. 从 metrics 估 prefill/decode 速率 → 成本模型参数。

## 7. 从调度/理论横查借来的具体动作（2026-10-23，见 `survey_scheduling_theory_20261023.md`）

1. **开场用 Little 律把内存翻成速率**：`KV 字节 = λ·W·b` ⇒ 「内存受限」就是「可持续速率受限」。
   一句等式就能把“池子装不下”从工程抱怨变成模型约束，比十页动机强。
2. **容量域 + 下界/可达夹逼**（RAD/SLAI 的做法）：先写每会话需求 `d̄`（含 KV 驻留与
   重算代价），证「任何调度都做不到比 X 更好」，再证我们的策略达到 X —— 两句建立“最优感”。
   我们的 `d̄` 要把**长会话 W（工作集）的方差**写进去，这正是与 request 级/agent 级的分界。
3. **定理取“够用的一行”**：正文只留一行条件（如 `Σ d̄_s ≤ C·ρ` 或 `max(prefill,decode) ≤ SLO`），
   证明进附录；RTAS 那批 real-time 论文全是这个模子。
4. **只给 break-even，不给“最优”**（Splitwise）：复活 vs 重算的交叉点 = 设计原则；
   承认交点依赖参数，比宣称全局最优更可信。
5. **把 SLO 反解成预算**（Sarathi/Mooncake）：deadline miss 预算 → 准入预算（token/会话数）；
   机制退化为“守门人”，故事更干净。
6. **主动命名失效模式再补**（Mooncake）：主动写「准入会抬高引擎 idle / 缓存足够大时收益消失」，
   再给分解与边界——比宣称零副作用可信得多。
7. **一个机制解释多个现象**（Llumnix）：容量核算同时解释 makespan、会话尾部、命中率、idle；
   把四个指标串成一条因果链，而不是四个独立结果。
8. **反直觉开场**（PerBank 的 88×）：12.7× 可避免的 prefill、均值 15.9s vs 中位 0.18s 的工具等待，
   都适合当“反常识数字”。
9. **用区间/界代替点估计**（FW-Agnostic）：增长估计给覆盖区间，准入用上界；比“预测一个数”更像理论。

## 8. 从测量型调研借来的钩子与差异化（2026-10-23，见 `survey_measurement_hooks_20261023.md`）

### 8.1 五个开场钩子（都用现有 trace 复算过）

1. **12.9×**：19 会话终态工作集 1.306M token = 单卡 KV 池的 12.9 倍；池子只装得下
   **1.48 个**中位会话。物理上装不下——这是全文第一句。
2. **12× 重读税**：同一批步里 prefix 重读 24.4M、append 仅 2.0M；每步 prefix p50 42K
   vs append p50 1.1K（38×）——agent 每一步都在重读整段历史。
3. **12.7×**：若每轮都被驱逐、全量重算，工作量上界 29.2M vs 必要 2.30M。
   （⚠ 与 12.9× 不是同一个量：一个是理论上界，一个是工作集/池子比。）
4. **0.21s vs 18.6s**：工具等待中位 0.21s、均值 18.6s、p90 40s；>10s 的间隔只占 15.6%，
   却吃掉 95% 的停放时长——**重尾定容量，不是平均**。
5. **1.48 会话的池子**：这个名字比“池子小”更具体，适合当一句话钩子。

### 8.2 新出现的最近邻（related work 必须正面处理）

- **2601.22705 CONCUR**（已在 6 篇里）：它的立论手法可整段借——给病态命名
  （middle-phase thrashing）+ 一条“占用 80–100% 而命中率崩塌”的反向曲线 + 三阶段因果链，
  然后才上控制律。我们可以给我们的病态起名：**“session overcommitment” / “re-read tax”**。
- **2610.22863 KV Residency in Production-Scale Agentic LLM Workloads**（Microsoft M365，
  121M 调用）：已经把“容量天花板”讲成故事——单 p99 会话 KV > H100 80GB、
  hold-all-live ceiling = 501.8 TB、推理只占驻留时长 5.6%；并给出预算压力下的重算率
  （LRU 63% / FNU 31% / MRR 13.6%）。**但它是 trace 估算、集群尺度、无 SLO、无准入决策。**
  ⇒ 我们的差异化必须钉死：**单卡内存墙 + 会话级准入决策 + SLO/尾延迟 + 真引擎端到端**。
- **2610.25231 AgentLens**：宿主侧资源表征/控制（10 框架/11 任务）；不同层，引一句即可。

### 8.3 摘要模板（18 篇抽样）

```
趋势 → “however 现有假设错” → “we observe X 是 Y%” → 机制 → 两个收益数
```
几乎都不写边界/反例——**这正是我们能加分的地方**：主动写“什么时候不成立”。

### 8.4 图序（论证序）

`单位（session→round→step）→ 形状（上下文/工具等待）→ 会计恒等式（总量=唯一+重复）
→ 时间线（一个会话的挂起/复活）→ 重尾 → 旋钮`。不要先放总览图。

### 8.5 一句话定位

> Existing work tells us the ceiling exists (2610.22863) or names the thrashing (CONCUR);
> we show, on a single memory-bound GPU, how a **session-level capacity ledger** keeps the
> server under that ceiling while meeting SLOs — and we name the price when it cannot.

## 9. 来自 KV/分层调研的关键修正（2026-10-23，见 `survey_kv_memory_20261023.md`，24 篇全文）

### 9.1 三个必须处理的事实

1. **MORI（2606.00866）已经占了“每层准入”**：它把 idleness 连续化排序，明确写
   “enforce admission control at each memory tier”。⇒ **“tier-aware admission”不能当我们的主创新**。
2. **kvlive（2609.16215）的二分法 + 强负结果**：“机制是容易的一半，放置策略才是难的”；
   连 future-reading oracle 预取都不赚带宽。⇒ 我们必须承认“**不是所有会话都值得挂起**”，
   并给一个 breakeven——这反而让机制可信。
3. **EfficientAgent（2609.33762）已有 OBR = 1 − T_load/T_rec**（搬运 vs 重算的不等式；
   H20 上 0.86 vs ≥5.6 µs/token ⇒ OBR≥0.84）。⇒ 我们**不要重新发明**，而是把它扩一维：
   **加“会话还剩多少轮/还要不要回来”这个时间维度**，得到“挂起 vs 重算”的会话级 breakeven。

### 9.2 新的主叙事（取代“价格”）

> **别人把“内存不够”当放置/驱逐问题，于是必须预测未来**（steps-to-execution / Beta 先验 /
> OBR / 长度预测）。**长会话 agent 的真实结构是“可挂起”的**：承认会话可在轮边界暂停且保状态，
> 问题就从“预测谁会被复用”变成“**核算还能容纳几个活跃会话**”——**预测需求消失**。
>
> 与 ConServe（2606.01839）“换调度单元而不是加预测器”是同一个动作，但我们换的是**状态**
> （可挂起会话），不是单元。

一句话 gap 句（可直接写进 Intro）：
> Existing systems treat a memory shortfall as a placement problem,
> which forces them to predict the future; we treat a session as suspendable,
> which turns admission into accounting — and prediction disappears.

### 9.3 分析装置（三种，全部可对拍）

1. **容量核算界**：给定 device/host 容量与每会话 KV 工作集，活跃会话数的上界
   `N_max = C / W̄`（配 12.9× 的实测超订）；准入就是守这个界。
2. **挂起 breakeven（OBR 的会话级扩展）**：
   `T_revive = n·β/B + τ`（n=KV 字节、β=每 token 每层字节、B=host 带宽、τ=固定开销），
   `T_recompute = P(ctx)`；只有 `T_revive < T_recompute` 才值得挂起。
   再加一维：**会话还会不会回来**（剩余轮数/工具等待分布）⇒ 期望收益 = p_return·(T_recompute − T_revive)。
3. **带宽算术**（CachedAttention 式）：2K token KV 过 PCIe Gen4 ≈ ? ms，与 prefill 时间对比；
   用我们机器上的实测参数（可测/可估）算，不引用别人的数当自己的。

### 9.4 要主动预埋的负结果（“听起来有道理”的关键）

- 不是所有长会话都值得挂起：当 `T_revive ≥ T_recompute`（上下文短/带宽低）时，重算更便宜；
- 缓存足够大 / 并发很低时，机制会被淹没（MORI 自陈低并发下所有 offload 命中率都 87–96%）；
- 主动写“我们什么时候不赚”——比多刷一个 1.2× 更能立住机制。

### 9.5 定位表（related work 用）

| 工作 | 他们的问题 | 我们的差异 |
|---|---|---|
| MORI 2606 | 每层准入 + idleness 排序 | 我们是**硬容量核算 + 命名许可 + 可逆挂起**；不做“按 idleness 排序”的软策略 |
| EfficientAgent 2609 | working-set admission + OBR | 它是 per-token 决策、无会话级挂起；我们把 OBR 扩到**会话时间维度**并落到真引擎 |
| kvlive 2609 | 模拟器里比较放置策略 | 我们承认它的负结果，给**挂起 breakeven**；真引擎端到端 |
| ConServe 2606 | 换调度单元（turn→session） | 我们换的是**状态**（可挂起），不是单元；且给容量界 |
| Mooncake 2407 | 过载早拒绝（拒绝即丢状态） | 我们是**挂起而非丢弃**，状态保留、可复活 |
| KVFlow 2507 | 预测 steps-to-execution | 我们不预测，核算 + 挂起；预测需求消失 |
| Mooncake/Continuum/Concur | 吞吐/延迟目标 | 我们单卡内存墙 + SLO/尾延迟 + 真引擎 |

### 9.6 对 §2 的影响

- **Arc B 的旧版本（Price the Tier 当主创新）作废**；tier 只作为 §9.2 成本模型里的一个量。
- **Arc C（可逆挂起）从“机制章”升级为“主叙事的一半”**：它不再是实现细节，
  而是让“预测消失”的那个结构性动作。
- 新的 §2 主骨架：**A（单位）+ C（可逆挂起/不预测）**，B 降为成本模型，D 做 hook。
