# 文献研读：agentic serving 准入与预测的近邻（2026-09-11）

**Access note.** CONCUR/Continuum/TokenCake 读的是全文 HTML；Past-Future Scheduler、Autellix、InferCept 为摘要级（InferCept 的算法细节部分转引自 Continuum/TokenCake 的复现描述）；MAPS 全文被 OpenReview 屏蔽，仅获得 ICML 2026 站点的摘要。

**关于 µ-Serve 的更正.** 不存在做 conformal 输出长度预测的 µ-Serve。同名论文是 µ-Serve（USENIX ATC '24, Qiu et al.）——做 GPU 频率调度的功耗感知 serving，无长度预测、无 conformal。可能的记忆混淆来源：SSJF/代理模型序列长度预测（ASPLOS '24, arXiv:2404.08509，同一一作）和/或 MAPS（ICML '26，校准长度上界）。**不要引用 µ-Serve 作为 conformal 输出长度预测。**

## 对照表

| Paper (venue/year) | 预测信号 | 预测方法 | 保证/校准? | 准入/调度机制 | 硬件/场景 | Foyer 可借鉴 | 与我们贡献的重叠风险 |
|---|---|---|---|---|---|---|---|
| Past-Future Scheduler (ASPLOS 2025, [2507.10150](https://arxiv.org/abs/2507.10150)) | 运行 batch 在未来各解码时点的峰值 KV 内存 | 请求输出长度的经验历史分布，投影到未来时间步 | 无（经验分布，未校准） | 预测峰值内存装得下才准入 continuous batching；明确在排队延迟与有害驱逐间权衡 | LightLLM；通用 LLM serving；SLA 下 2-3× goodput | "把内存占用轨迹投影到未来时间、按峰值 fit 准入"的骨架——正是我们池子 fit 检查的公式；激进 vs 保守的驱逐-排队权衡框架（好引文） | **中**——同为 predict-memory-then-admit，但请求级、单轮、无每会话在线增长模型、无校准、无质量 shedding |
| Continuum (arXiv 2511.02230 v6 2026, Berkeley, [abs](https://arxiv.org/abs/2511.02230)) | 每工具类型的下次 tool-call 时长；卸载成本、逐轮排队延迟、workload 记忆性 η | 每工具历史经验 CDF S[f]；回退全局 CDF；再回退 Exp(1)（冷启动阶梯）；TTL = argmax P(τ,f)·Benefit − Cost | **无覆盖保证**；靠 TTL 过期（有界保留）而非校准界 | KV-cache TTL pinning：完结请求的缓存钉 τ 后自动驱逐；TTL 感知优先级；死锁牺牲者 = 最晚到达的被钉 program | vLLM+LMCache；Llama-3.1 8B/70B 等；SWE-Bench；最高 8× JCT | (1) Cost(τ,r)=MemUsage/M·τ vs Benefit 的代价模型可直接作为我们牺牲者选择的目标函数；(2) 每工具 CDF→全局→默认的阶梯与我们的 EMA+全局先验同形（引为先例，再加 conformal）；(3) TTL = "自动过期的安全阀"——我们的 conformal 上界可包装成 principled TTL | **中高**——已做每 program、预测驱动的保留/牺牲决策，带"下一轮多快来"的味道。必须声明差异：它预测*时间*而非*内存增长*；做保留而非准入；经验 CDF 无保证；且其自述分布漂移是未解开放问题 |
| TokenCake (arXiv 2510.18586 v3, [abs](https://arxiv.org/abs/2510.18586)) | 每工具类型的 function-call 时长（用于卸载/上传时机） | **EWMA 按工具类型混用户先验**：t̂=α·t_user+(1−α)·t_history——正是 EMA+全局先验 | 无；机会门 = 硬拒绝 + 软复合分 | 事件驱动的空闲 KV 主动卸载 + 预测上传；共享/保留双池内存分区 | vLLM；Qwen2.5-14B/A100 等；multi-agent 场景；延迟 −47% | (1) EMA+先验估计器形态（必须引：工具时长的先例，我们用于 KV 增长）；(2) 保留池分区 = named permit 的实现模板；(3) 其 first-fit/best-fit/priority-first 牺牲者消融设计 | **中高**——已做 agent 粒度、预测驱动的卸载牺牲者选择。但其需要用户标注 DAG + 每工具元数据（一种 trace/先验访问，我们刻意避免）、预测停顿时长而非 KV 增长、且无准入控制 |
| Autellix (arXiv 2502.13965, [abs](https://arxiv.org/abs/2502.13965)) | 无预测——调度状态 = 每 program 已完成调用数/已获服务 | 无（反应式 program 级记账） | 无 | Program 优先抢占调度；截获调用、按最少已获服务排序；end-of-turn 驱逐 | vLLM；agentic 负载 4-15× 吞吐 | 中间件"截获调用、给调度器注入 program 上下文"的架构定位；其 HOL-blocking 测量方法 | **低**——无准入、无预测、无内存管理（Continuum 指出其驱逐是弱点）；调度顺序类基线 |
| InferCept (ICML 2024, [PMLR](https://proceedings.mlr.press/v235/abhyankar24a.html)) | 每次 tool 截获时的重载/重算成本（仅下一轮） | Min-waste 启发式：比较重载成本与 GPU 占用来选 preserve/swap/evict（转引自 Continuum/TokenCake） | 无 | 截获式 serving：工具调用处暂停生成，preserve/swap/evict KV，腾出内存给更多请求；1.6-2× 吞吐 | 自研引擎 vs vLLM 时代系统 | "被暂停会话的内存是可回收容量"的框架——Foyer 的 pause-as-memory-reclamation 的雏形；preserve-vs-evict 成本核算 | **中**——逐截获、只看重载成本（Continuum 证明因忽略排队而次优）；无准入、无增长预测、无校准 |
| CONCUR (arXiv 2601.22705, 2026.1 — 直接基线, [abs](https://arxiv.org/abs/2601.22705)) | **无预测**——反应式聚合反馈：KV 使用率 U_t 与命中率 H_t | agent 并发窗口 W_t 的 AIMD：+α if U<U_low；×β if U>U_high∧H<H_thresh（α=2, β=0.5，阈值 0.2/0.5/0.2） | 无（固定阈值 + 敏感性分析） | 中间件 agent 级控制器；admit/pause/resume 原语在轮边界；约束聚合 KV 工作集 | SGLang on H100-80GB TP2-8；Qwen3-32B (4.09×)、DeepSeek-V3 (1.9×)；offline batch | (1) 三阶段 warmup/thrash/cooldown 表征——我们 motivation 的理想素材；(2) admit/pause/resume 原语词汇表（我们的 API 至少要这么有表达力）；(3) 其固定档 vs 自适应消融；(4) AIMD 作为前馈 permit 之下的安全网 | **高**——共享骨架（中间件、agent 级准入、暂停、连续性、KV 压力）。审稿人第一问必是"vs CONCUR"。回答要干脆：它是**反馈**控制、全局聚合信号、无每会话知识；Foyer 是**前馈**：每会话预测增长、每会话 fit 检查、named permit、SLO shedding、校准界 |
| TIE (ICML 2026, [2604.00499](https://arxiv.org/abs/2604.00499)) | 每请求的输出长度**分布** | 参数化重尾拟合：log-t 分布；尾部膨胀期望评分 | 分布式但参数化拟合——**无有限样本覆盖保证**（非 conformal） | 用尾部膨胀长度替代点估计做 SJF 排序 | 在线+离线；2.31× per-token 延迟 | 尾部膨胀评分直接迁移到我们的准入评分（按尾部风险准入，而非 EMA 均值）；log-t 作为每轮增量先验的候选参数族 | **中**——调度用的分布预测存在，但单轮输出长度、排序非准入、无保证 |
| Beyond Prediction (ICML 2026, [2606.18431](https://arxiv.org/abs/2606.18431)) | 明确**无预测**；轻量统计信号 | 软优先级提升（γ 参数化）；共优化的缓存感知抢占 | 无 | SRPT 替代；内存压力下的缓存感知抢占 | 生产+开源 trace；P99 TTLT −35-50% vs SRPT（带完美长度知识） | 其核心证据——点预测策略在分布漂移和内存压力下脆弱——正好是我们"要校准（鲁棒）界"的动机引文；其尾延迟评测协议 | **中低**——请求粒度的内存感知抢占存在，但哲学是反预测的；无准入、无会话 |
| MAPS (ICML 2026 poster, [OpenReview](https://openreview.net/forum?id=MsjYbZtVWU)) | 每请求输出长度 → 内存/解码负载**上界** | 设备侧投机长度预测与 prefill 重叠 + "不确定性感知校准得到目标覆盖率的输出长度上界"（摘要原话；"conformal"一词未出现） | **是——声称长度上界有目标覆盖**（机制未经我核实） | 分层全局-局部调度；按校准上界路由/排序请求 | 2 负载 2 模型；平均延迟 −42.6% | "校准上界 → 内存决策"模板——**我们升级方案的最近先例**；要差异化而非重新发明 | **中高（校准那一半）**——请求级、单轮、队列调度（非会话准入）。MAPS 之后，我们不能泛泛主张"LLM serving 的校准长度上界"，只能主张**跨轮会话级 KV 增长 + 准入**的具体化 |

邻接发现（不成表）：KV 约束调度理论证明任意到达下无常数竞争比（[2502.07115](https://arxiv.org/abs/2502.07115)，可用于"预测是必要的"论证）；PACO（serving 自动配置的 conformal 安全底座）；容量规划的 conformal GPU 需求包络；S3 响应长度感知（NeurIPS 2023）。均不碰会话级准入。

## 三个关键判断

### (a) conformal 校准的跨轮会话需求预测用于准入，有人做过吗？
**没有。** 最接近的（递减）：MAPS（ICML '26）做了校准的、目标覆盖的输出长度上界，但是**请求级**、用于**队列调度**、设备侧投机预测器——非会话级、非跨轮累计 KV 增长、非准入。TIE（ICML '26）分布化但参数化、无保证、请求级 SJF 排序。Continuum 用经验 CDF（无保证）预测工具时长（非内存需求）做保留 TTL。Past-Future 用未校准的历史输出长度分布。**空白确认：在线从会话自身逐轮增量学习的、分布无关/校准的、跨多轮 KV 增长上界 + 准入门控——这个组合是开放的。**
**措辞警告**：MAPS 之后，不能泛泛主张"LLM serving 的校准预测"，只能主张**会话/准入的具体化**。另外本集合中没有人干净满足 conformal 的可交换性假设（agent 会话时序相关且非平稳——Continuum 明说分布漂移未解），所以论文需要 adaptive/weighted conformal 变体——**这本身就是贡献机会**。

### (b) 会话粒度的预测式缓存牺牲者选择，有人做过吗？
**部分——原语存在，具体机制没有。** TokenCake 在 agent 粒度用预测的 function-call 停顿时长 + 关键度选卸载牺牲者（但依赖用户标注 DAG + 每工具 EWMA，面向已知停顿期的主动 CPU 卸载）。Continuum 的 TTL 由预测派生，但牺牲者按到达顺序选（非预测排序）。InferCept 只按重载成本逐截获决定。Beyond Prediction 刻意无预测。**没有人按"预测的下次轮次时间 × 预测 KV 增长、在校准界下"选牺牲者，也没有人把牺牲者选择与准入（permit）耦合。** Foyer 的牺牲者贡献是新的，但写作必须显式对标 TokenCake/Continuum——"暂停空闲最久的会话"与"按预测工具返回时间钉 TTL"肉眼可见地相邻。

### (c) 三个最值得借的具体技术
1. **Continuum 的成本-收益目标函数 + 冷启动阶梯**：Cost(τ,r)=MemUsage(r)/M·τ vs Benefit=CacheMissCost+OutOfOrderCost，在经验 CDF 上最大化；每工具 CDF→全局 CDF→解析默认的回退链。用作 Foyer 牺牲者选择与暂停时长选择的评分函数，把枚举 CDF 换成 conformal 上分位——并引 Continuum 阶梯为我们 EMA+全局先验的**未校准先例**（arXiv:2511.02230v6 §4）。
2. **CONCUR 的 AIMD 环路作为前馈 permit 之下的安全网**：保留一个由 U_t/H_t 驱动的乘性递减修正器，在预测错误时钳制 Foyer 的准入速率（其 Eq.1 与阈值敏感性分析，arXiv:2601.22705v1 §4.3/A.1）。这把我们的最大风险（预测错误）转化为**分层控制**的故事；其三阶段 thrashing 表征和命中率指标可直接复用进评测。
3. **TIE 的尾部膨胀评分 + 在线 conformal 化**：用 log-t（或 log-normal）作为每轮上下文增量的参数化先验，按尾部膨胀需求而非 EMA 均值评分准入，再对每会话残差做 split/adaptive conformal，用远少于纯经验分位所需的样本拿到有限样本覆盖（arXiv:2604.00499）。荣誉提名：Past-Future 的未来时点内存占用轨迹 = 我们池子 fit 公式的字面版；TokenCake 的共享/保留双池 = named permit 的实现参考。
