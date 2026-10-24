# 2026-10-24 第二轮调研：agentic serving 的拥挤程度与我们的位置

> 方法：arXiv API 关键词扫描（7 组查询，取最近 40 条/组，2026-10 为主），
> 逐篇抓 abs 页读摘要，再抓 HTML 全文对 15 篇做**措辞碰撞检查**。
> 本机 `curl` 可直连 arXiv（`web_search` 无 key，但 `web_fetch`/`curl` 可用）。

## 1. 扫描结果：三周内十几篇，方向已经很挤

按时间倒序，与"agent 会话 / KV / 准入"直接相关的（节选）：

| 日期 | arXiv | 标题 | 与我们关系 |
|---|---|---|---|
| 10-22 | 2610.31169 | SARIA: Persistence-Aware KV Caching with Coordinated DRAM–SSD Reload for LLM Agents | 持久化层，邻近 |
| 10-22 | 2610.30791 | Gandalf: Increasing Flash Storage Lifetime for KV Cache Offloading | HBF 寿命，远 |
| 10-20 | 2610.28577 | Cache Engineering for Agents | **agent 主动 drop KV**，新原语 |
| 10-16 | 2610.22863 | Understanding KV Residency in Production-Scale Agentic LLM Workloads | 测量，我们引作天花板 |
| 10-13 | 2610.17795 | Quota-Based Aging for Prediction-Guided Scheduling | 预测引导调度（模拟器） |
| 10-13 | 2610.17338 | Budgeted KV-Cache Repair for Evolving Contexts | 重算预算 |
| 10-12 | 2610.15579 | Approximation Algorithms for Dual-Memory Request Scheduling | 理论，双层调度 |
| 10-10 | 2610.14804 | AgentWeave: Distributed Agent Serving via Flow Decomposition | 分布式 |
| 10-06 | 2610.08378 | **Lachesis: Lifetime-Aware KV Cache Placement across HBM and HBF** | 放置，按生命周期 |
| 10-06 | 2610.07782 | Persistent Memory in Multi-Agent LLM Inference: What It Costs… | **负结果**（持久层无收益，带 CI） |
| 10-05 | 2610.06597 | **HEAR: Harness–Engine Pairing Protocol for Agentic Serving** | **接口协议**，撞我们的 permit |
| 10-02 | 2610.03088 | **Coda: Exploiting Admission Flexibility for Coding-Agent Serving** | **最近邻，撞得最狠** |
| 09-14 | 2609.16215 | Where Should the KV Cache Live?（kvlive） | 放置负结果 |
| 09-27 | 2609.33762 | EfficientAgent: What Makes KV Offloading Work | host tier 定容 + 工作集 |

## 2. 措辞碰撞检查（15 篇全文，词频）

| 措辞 | 命中 | 说明 |
|---|---|---|
| `feasible set` | **0** | 但 Coda 用了 `ℱ(t)` 符号 |
| `capacity accounting` / `ledger` | **0** | **完全没人用** |
| `working set` | EfficientAgent 48、persistent-memory 8、CONCUR 4、MORI 3 | EfficientAgent 占住"工作集" |
| `admission control` | **CONCUR 28**、MORI 7 | CONCUR 占住"准入控制" |
| `recompute` | EfficientAgent 19、2610.17338 18 | — |
| `oracle` | 2610.17338 17、kvlive 5 | 负结果常用 |

**结论**：我们那套词汇（capacity accounting / ledger / feasible set as a *test*）没人用；
但 **Coda 已经定义了 `ℱ(t)` = 满足 HBM 容量约束的 ready 请求集合**，且按"状态准备代价最小"在里面挑。
这和我们"可行集"是同一件事的两种说法，**必须引用并划清界限**。

## 3. 三篇必须正面处理的近邻

### Coda（2610.03088）
- 原话：`Let ℱ(t) denote the logically ready requests that satisfy the current HBM-capacity constraint; all other requests are temporarily infeasible.`
- 机制：Tiered-Aging 状态准入（在可行集内按"状态准备代价"排序）+ Compatibility-Aware 执行准入（按上下文长度分组解码）。
- 差异：**Coda 问"在可行集里下一个跑谁"，我们问"可行集本身有多大、越界要付什么"**。
  Coda 没有：可行集大小上界、复活/重算代价定价、单卡 regime、负结果。

### HEAR（2610.06597）
- 主张：harness 与 engine 之间缺一个**双向协议**（workflow intent ↔ runtime state）。
- 差异：HEAR 是**协议**（把语义标准化），我们是**策略**（账本 + 许可 + 定价）。
  我们可以引用它来说明"permit 这类接口已有共识"，但不能说"我们提出接口"。

### EfficientAgent（2609.33762）
- 主张：用 **stack-distance** 估 reuse working set，据此给 host tier 定容；tier 太小时过滤写入。
- 差异：它定的是 **host tier 容量**，我们定的是 **device 上谁驻留**。
  我们的"复用距离"（中位 3 轮）与它的 stack distance 同族，引用时要说明对象不同。

## 4. 还开着的口子（我们的位置）

1. **单卡内存墙**：Coda 多 worker、Lachesis 用 HBF、kvlive 是模拟器 + 1+8+64 三层。
   "一张 24GB 卡、池子装不下 1.5 个会话、真引擎"这个点上目前**没人**。
2. **把准入写成可强制执行的账本**：HEAR 给协议、Coda 给排序、CONCUR 给窗口，
   没人把"可行集"变成一个**字节账本 + 具名许可**。
3. **负结果**：kvlive 和 2610.07782 证明"负结果能发"，而我们手里有三条
   （预测器对照含神谕、挂起归因 54.7%、余量是二阶量）。
4. **regime 定律**：三个模型（7B/1.7B/0.6B）给 ρ_W = 12.9 / 8.1 / 7.3 三个坐标点，
   目前没人把"准入收益"画成超订比的函数。

## 5. 建议的故事（改口径，不换骨架）

> **在容量固定的单卡上，准入不是"放多少"，而是"哪个子集在字节上可行、越界要付多少重算"。**

三段论：
1. **可行集有界且很小**（中位 1，63% 的轮次只装得下 1 个）→ 阈值控制注定失效；
2. **离开可行集有代价**（复活 vs 重算；挂起 138 次、其中 54.7% 的重算是我们自己造成的）；
3. **代价可以定价，预测不必**（预测器对照含神谕；余量是二阶量；复用距离中位 3 轮）。

与 Coda 的一句话区别（写进 Related Work）：
> Coda asks which feasible request to run next; we ask how large the feasible set is,
> how to enforce it in bytes, and what it costs to leave it.
