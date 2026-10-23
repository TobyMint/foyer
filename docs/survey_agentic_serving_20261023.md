# Agentic Serving 叙事解剖（2026-10-23）

方法：arXiv API + 全文 PDF。只拆"怎么讲"，不比数据。

## 一、核心五篇

**CONCUR**（2601.22705, 2026-01；PDF 内改题 *Proactive Agent-Level Admission Control*）
开场：KV 在容量耗尽**之前**就崩——"中段抖动"。
gap：request 级 LRU 把暂停但语义关键的前缀当垃圾驱逐、逐轮重算；抖动期加 agent 反而更慢。
insight：KV≈带宽，准入须提前、以 agent 为单位。
机制/分析：admit/pause/resume 三原语 + cache-aware AIMD（用量、命中率双信号）+ 中间件；论证靠"重算 O(L²) 凸惩罚⇒乘性降速 O(log N) 步退出"，无排队论。
实验：SGLang／+request cap／+HiCache；端到端 batch 时延 4.09×；以"固定 cap 不行"反证机制。
可借：造病理名＋亮反直觉曲线；再立稻草人。回避：只离线 batch、挂起态不落地、阈值启发式、多卡非单卡。

**Continuum**（2511.02230, PVLDB 20(1) 2027）
开场：end-of-turn eviction 在工具间隙毁掉 KV。
gap：InferCept 只算 reload 成本，漏掉驱逐后重排队的 per-turn 队列延迟，且逐轮累积。
insight：给 KV 一个 TTL，长度由 reload 成本与队列延迟的 breakeven 定。
机制/分析：TTL 钉住 + program 级 FCFS + 工具时长历史估 P(τ,f)；成本式 CacheMissCost=Prefill-Reload+OutOfOrderCost，配大/小 TTL 两侧失效图。
实验：vLLM／InferCept／Autellix；平均 JCT >8×；机制验证=TTL 扫描。
可借：把"留不留"写成两项成本比较再给一个旋钮；用逐程序 bubble 图画出 gap。回避：TTL 是启发式非可行域，缺高负载前沿。

**ThunderAgent**（2602.13692, 2026-06）
开场：engine+K8s 拼装、按 request 调度，命中率随并发塌。
gap：三处结构性：KV 抖动、DP 副本内存不均、工具环境（磁盘/端口）失控。
insight：把 workflow 抽象成 LLM Program，统一调度异构资源。
机制/分析：LLM Program 抽象 + program-aware 队列（Restore/Pause）+ tool resource manager；Space-Time Product 五项成本分解，全局队列给 C_unused<c_min·Δt 上界，时间片 barrier。
实验：vLLM／Continuum／vLLM+SGLang Gateway；吞吐 1.5–3.6×；按成本项拆解。
可借：先给成本分解，每个机制对准一项浪费。回避：HBM 充裕；成本模型不含挂起态。

**Talaria**（2607.17181, 2026-07，非正式 venue）
开场：先甩测量——445 个 SWE session、中位 11 轮、25K token（96.8% 复用半前缀）、工具间隙 0.39s vs 重算 4.3s。
gap：request 是错的单元 ⇒ 空间错配（路由到无权重实例）+ 时间错配（轮转调度浪费 KV 局部性）。
insight：把 session 连续性做成 placement 与 admission 的联合决策。
机制/分析：session-aware router + soft reservation（为"可能回来"预留预算）+ session-prefill + memory substrate；论证=连续性窗口比较。
实验：baseline=同引擎关掉 SP/host-KV/D2D 的自身消融；p50 SCT 1000→189s。
可借：用测量数字造出物理窗口；拿自己的 ablated 版当 baseline。回避：测 SCT 不测容量上限、无拒绝语义、单服务器。

**MORI**（2606.00866, 2026-05）
开场：offload 后工具时长跨数量级，二分类 busy/idle 与硬件容量比不匹配。
gap：固定分类 + 缺 CPU 侧准入 ⇒ 两层各自抖动。
insight：idleness 是连续相对的谱，"比他人更闲"才决定去留。
机制/分析：idleness 评分 + 边界随容量比移动 + 双层准入 + 亲和性负载均衡；论证是容量比匹配（1:1.6 vs 1:3.1）+ 容量不变量。
实验：SMG／TA／TA+Offload；吞吐 +20–71%；用 1×/2× 容量比与 DP=3 当压力测试。
可借：一句话 insight 打掉二分法；把硬件容量比当自变量扫。回避：仍假设有 CPU 层；准入=填满，非预算。

## 二、次级（各一句叙事点）
- **Autellix**（2502.13965）：两级 HOL → "program 为一等公民"，preempt/prioritize。
- **Parrot**（2405.19888, OSDI'24）：semantic variable 暴露请求依赖，SLO 感知。
- **InferCept**（2402.01869）：interception 当一等操作，preserve/swap/evict 三选一。
- **KVFlow**（2507.07400）：Agent Step Graph → steps-to-execution，把"未来距离"变驱逐优先级。
- **Pensieve**（2312.05516, SIGMOD'25）：无状态是结构性病根，多级 KV 缓存往回补。
- **PBKV**（arXiv'26-05）：压力不够时策略全打平 → 直接把并发调到"有压力"的操作点。
- **PKAS**（HPDC'26）：点名"贪心填满 ⇒ 调度-抢占循环"，指标剔除重算 token。
- **Maestro**（arXiv'26-06）：唯一用 SLO 达标率，deadline 由隔离 profile 定、各 baseline 共用。

## 三、跨论文叙事规律
1. 标题造**病理名词**（thrashing / end-of-turn eviction / session continuity），不用形容词。
2. 摘要四拍：现象 → 为何结构性失败 → 命名 insight → 倍数。
3. 引言第二段必放**量化反直觉**（加 agent 更慢／0.39s vs 4.3s／37–40% 重算）。
4. gap 句式统一为"**粒度错了**"：request→agent→program→session，粒度递进就是本族叙事引擎。
5. 机制固定三件套：两个调度原语 + 一个成本/控制器，外加一个廉价旋钮（TTL、W_t、容量比）。
6. 分析层三选一：成本分解、breakeven、不变量/上界；几乎无人做真排队论。
7. 实验：baseline=引擎＋一个更聪明的同类＋自己的消融版；headline 单一倍数；机制靠"固定 cap 不行"或扫旋钮。
8. 集体回避：**准入的可行性判据**与**挂起态的存放/复活代价**无人建模（MORI 只到"填满"、Talaria 只到"预算"）——我们的位置在此。

→ 叙事空位：给准入一个**可核算的可行集**（谁能在卡上、住哪层、复活付多少搬运），并把边界写成可预测的，而不是阈值。

（AgentMem-KV 全库无同名；PBKV/PKAS/Maestro 的 ID 本轮未复验，叙事点取自 `survey_workload_design_6papers.md`。）
