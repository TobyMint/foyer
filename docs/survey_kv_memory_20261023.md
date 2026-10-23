# KV / 分层 / 前缀复用 24 篇：叙事结构横查（2026-10-23）

> 只拆故事怎么搭：痛点怎么演、gap 为何是结构性的、机制靠哪个可算量立住、实验怎么逼出机制。
> 源：arXiv PDF 全文（`pdftotext`）+ HiCache 官方博客；`†`=venue 取自公开出版信息，非 PDF 标注，引用前再核。
> **篇幅**：除 §一 的表外全文 ≈0.93k 字（表本身 1.8k），**删掉 §一 即在全篇 1200 字内**；表是逐篇查证用的附录。
> 检索备注见 §五。

---

## 一、逐篇速查（附录）

| 论文 | 开场 dramatize | 声称 gap（为何结构性） | insight + 机制 | 分析装置 | 实验 | 借 / 没讲清 |
|---|---|---|---|---|---|---|
| **vLLM** 2309 SOSP23 | 13B：权重 65%、KV>30%，且涨缩不定 | KV 存连续内存→"按需增长+共享"根本做不到，浪费 60–80% | OS 分页：PagedAttention / block table / 块级 COW / swap↔recompute | 碎片按内部·外部记账；仅一句"取决于带宽与算力"，无式 | FasterTransformer/Orca→同延迟 2–4×；消融：共享·调度·换出/重算 | 借 OS 隐喻+浪费%开场；漏 回收永远定性、无准入 |
| **SGLang** 2312 NeurIPS24† | 多调用程序，调用完 KV 即丢 | 通用引擎不懂 workload→跨调用复用结构上为 0 | 前缀是棵树：RadixAttention / radix tree+LRU / cache-aware(DFS) 调度 / frontend hint | **证** DFS 顺序=离线最优命中率（cache≥最长请求）；实测 52.4/74.1%，bench 50–99% | Guidance/LMQL/vLLM→6.4×；消融：命中率（调度顺序）+FSM | 借 命中率"可证+可测"双轨；漏 树只在 GPU，容量→命中率无模型 |
| **HiCache** blog25-09 | 上下文变长、客户端变多→命中率掉，历史 KV 必须驱逐 | GPU-only 树**容量封顶**："caching benefit is inevitably limited by a capacity bottleneck" | HiRadixTree 当跨层页表 / GPU-assisted I/O kernel / page-first+zero-copy / layer-wise overlap / 写策略 write-through·selective·write-back / 预取 best-effort·wait_complete | 无公式；容量→命中率经验曲线 + 生产数（40%→80%、TTFT −56%、6×） | 长上下文+多轮；后端 3FS/Mooncake/NIXL | 借 容量封顶→命中率跌 这条因果链；漏 无挂起语义 |
| **LMCache** 2510 2025 | 生产统计：用户存的 KV "远超 GPU 容量"，reuse/token 持续上升 | 缺引擎外的 KV 层；offload 引擎私有、不可跨引擎 | KV 该是独立层+buffer-pool 式 API / connector 解耦 / 控制 API(pin·lookup·move·compress) / chunk>page | 带宽-粒度论证；反直觉：context truncation 让前缀命中率**减半** | vLLM+LMCache→15× | 借 生产统计当开场证据；漏 不判"该不该挂起" |
| **CacheGen** 2310 SIGCOMM24 | 长上下文 prefill 定 TTFT，复用要过网络 | KV 太大→**网络是隐藏瓶颈** | KV 分布有局部性→tensor encoder（量化+算术编码）/ 压缩级随带宽自适应 / 低带宽回退"发文本重算" | 带宽–延迟曲线；"发文本 vs 发 KV"breakeven | 量化基线→延迟 3.2–3.7×、带宽 3.5–4.3× | 借 搬运 vs 重算变决策变量；漏 质量门限靠经验 |
| **CacheBlend** 2405 EuroSys25 | RAG 多 chunk 拼接，KV 只能前缀复用 | 非前缀复用丢 cross-attention（F1 0.35→0.15）→收益拿不到 | 只重算偏差最大的少数 token（HKVD），跨层可预测 / 重算与 KV 加载流水线重叠 / 允许 KV 放慢设备 | 重算比例 r 映射到偏差 Δattn；r=5–18% 时质量损失 ≤0.002（breakeven） | 全重算/全复用→TTFT 2.2–3.3×、吞吐 5× | 借"部分重算"第三档（挂起恢复同构）；漏 假设 KV 可得 |
| **FlexGen** 2303 ICML23 | 单卡 16GB 跑 175B | offload 继承训练策略→I/O 过量、"远低于硬件上限" | 形式化(schedule, placement, delegation) 搜索空间 / LP 求解 / Zig-Zag / groupwise 4-bit | **证** I/O 复杂度 ≤ 最优 2×；给 batch size 上界 | T4 上 OPT-175B 1 tok/s、batch 144；vs ZeRO-Infer 69×；消融：调度/放置/4-bit | 借 LP+上界句式；漏 延迟不敏感、无在线准入 |
| **ZeRO-Inference** blog22 | 模型比 GPU 大 | 缺"权重/状态放哪"的抽象 | 权重与 KV 常驻 CPU+NVMe，按层预取 | 无（工程 blog 体） | 被 FlexGen/H2O 当"朴素搬运派"baseline | 借 搬运派原型；漏 无模型，正好当我们的对照起点 |
| **InfiniGen** 2406 OSDI24 | KV 随长度涨；offload 后 PCIe 成新瓶颈 | 全量搬运=把带宽当免费，精度又不许乱丢 | 用本层输入+下层部分 Q/K 做"最小排练"**推测**关键 token，只预取这些 | 排练开销 vs 带宽节省 | 现代 offload 系统→3.00×（同精度） | 借 预测未来重要度；漏 单请求、静态 batch |
| **H2O** 2306 NeurIPS23 | KV 随长度涨，显存吃光 | 均匀保留浪费：attention 95% 稀疏 | heavy hitter+recent 固定预算 / 形式化为**动态 submodular** / greedy | near-optimal 保证；"20% 预算够"的容量论证 | DeepSpeed/FlexGen→29×/3×；消融：预算比例×任务 | 借 稀疏度→容量上界；漏 长链任务质量不稳 |
| **SnapKV** 2404 NeurIPS24 | 长输入 KV 线性涨 | 生成**之前**无法知道哪些位置重要 | 末窗 attention≈生成时→投票选 token | 自定义 **hit rate** + 鲁棒性（换 instruction 会掉） | 16K 输入 3.6× 速度、8.2× 内存；消融：pooling+窗口 | 借 用 hit rate 度量预测质量；漏 单轮 QA |
| **Quest** 2406 ICML24 | KV 读取占 >50% 延迟 | token 重要度**依赖 query**，静态选择必错 | page 内 K 的 min/max 给 attention **上界**→选 top-K page / 只后层启用 | 显式上界推导 + 选择开销 5–10 µs | 2.23× attention、7.03× 延迟 | 借 上界→剪枝；漏 单请求 |
| **PyramidKV** 2406 预印 | 各层呈"金字塔漏斗" | 各层同预算=结构性错配 | 层间预算金字塔（底多顶少）+ 分数选 token | 预算–质量曲线 | vs SnapKV/H2O 固定预算；消融：分配策略+超参 | 借 预算在层间再分配；漏 总量仍固定 |
| **Mooncake** 2407 FAST25† | Kimi：KV 是瓶颈，而集群 CPU/DRAM/SSD 闲置 | 请求级调度假设"所有请求都会被执行"→过载必崩 SLO | KVCache-centric Conductor / 分离式 KV 池 / CPP / layer-wise prefill / **prediction-based early rejection** / 热块复制 | **占用成本 S·T**；命中率-容量 34%→55%；早拒绝会震荡→须预测负载 | 模拟 525% 吞吐（守 SLO）；真实 +75% 请求 | 借 拒绝=准入、S·T 核算；漏 拒绝即丢状态，无"挂起"档 |
| **MemServe** 2406 2024 | 从 stateless 变 stateful，KV 生命周期+作用域同变长 | 请求内(PD 分离)与请求间(前缀缓存)各自为政 | MemPool 弹性池+API / 全局调度器 / prompt-tree 局部性路由 / huge page 共优化 | cost model：逐实例 argmin exec(x′,y′)+exec(x,y)；"缓存收益随轮数**线性**增" | vs vLLM→吞吐/延迟 | 借"收益随轮数线性增"；漏 集群级，单卡不适用 |
| **Pensieve** 2312 SIGMOD25† | 系统"stateless across requests"，每轮重算整段历史 | 无状态是结构性的：请求结束即丢 KV | 多级 GPU-CPU cache / ahead-of-time swap（与计算重叠）/ 只重算被驱逐 token / 非连续 KV 让 prefill+decode 同批 | 换出 vs 按 token 重算的二选一；保守双向带宽 | vLLM/TRT-LLM→1.14–3.0× | 借"stateful vs stateless"最锋利的 gap 句；漏 容量固定、无准入 |
| **CachedAttention** 2403 ATC24 | ShareGPT：73% 会话多轮、30%>4K token，每轮重算 | 引擎把 KV 当请求内临时态 | AttentionStore 分层(HBM/DRAM/SSD) / layer-wise 预载 / 异步保存 / scheduler-aware fetch·evict / PE 解耦+截断 | **带宽算术**：2K token KV 走 PCIe Gen4(26 GB/s)≈192 ms，盘<5 GB/s；缓冲式 S_buf=B(T_load·L_hist−T_pref·L_new)；上界"省 99% prefill" | TTFT −87%、prefill 7.8×、成本 −70% | 借 带宽算术+缓冲公式；漏 驱逐只给 hint |
| **KVFlow** 2507 2025 | 多 agent 工作流反复调用，LRU 在复用前驱逐 | LRU 对未来一无所知，而工作流**可预测** | Agent Step Graph→**steps-to-execution** / KV 节点级细粒度驱逐 / 树形前缀保留 / 全重叠预取 | 用"时间距离"替代 recency；预取把 miss 移出关键路径 | vs SGLang 分层 radix cache→1.83×/2.19× | 借 把未来变成可算的数；漏 假设图已知、无准入 |
| **kvlive** 2609 2026 | HBM 最贵，KV 是最大占用者；长会话必须跨层 | "机制是容易的一半，**放置策略**才是难的" | 三级模拟器(HBM/DRAM/SSD)+ 策略网格 + future-reading oracle | 容量结果与策略无关（会话 73.02×、成本 62.04×）；**负结果：连读未来的 oracle 预取都不赚** | 策略×容量网格（全模拟） | 借"机制 vs 策略"二分法；漏 纯模拟、无挂起/准入 |
| **MORI** 2606 2026 | tool-call 空窗里 KV 白占 HBM，LRU 抓不住快/闲两相 | busy/idle 二值化与容量比不匹配 | **idleness 连续且相对**：按 idleness 排序，最忙进 HBM、最闲进 DRAM，边界随容量比移动 / **每层做准入** / 亲和均衡 | "容量比 vs busy:idle 比"讲失配；低并发下所有 offload 命中率都 87–96%→机制被淹没 | Claude Code trace→20–71% 吞吐、18–43% TTFT | 借 把状态保留写成排序问题；漏 无硬核算、无 SLO |
| **EfficientAgent** 2609 2026 | agent 每轮重发全对话，host offload 成常态 | 现有系统 per-token 决策，**没有 working-set 概念** | OBR / 每 rank KV 字节 β / content-key 存活预测 / working-set-aware admission | OBR=1−T_load/T_rec，T_load=nβ/B+τ；H20 上 0.86 vs ≥5.6 µs/token→**OBR≥0.84**；判据=每字节 host 带宽的算力（H800 是 H20 的 6.7–7.0×） | 3 GPU×2 模型；命中率随算力/带宽比变 | 借 OBR（现成的搬运 vs 重算不等式）；漏 无会话级挂起准入 |
| **multitier** 2604 2026 | 单请求 40 GB KV，batch 掉到个位数 | 无跨 MHA/GQA/MQA/MLA 的 sizing，无跨 6 层管理 | 架构感知 sizing / 6 层(含 CXL) / Beta 先验复用预测 / EMA 头粒度驱逐 / RoPE 预取 | β/token/layer（MLA 1152 B vs MHA 65536 B）；命中 70–84%；集群投影 4150 tok/s/GPU | trace replay + **分析投影**（无真机） | 借 β 公式推并发上限；反面教材：投影当结果 |
| **persistmem** 2610 2026 ML4Sys | agent 分解让单次调用 KV 有界，很多系统加"持久记忆层"用 ablation 证收益 | 这类 ablation **结构上测不出东西**（每题自带证据） | 三层 agent 架构 / 四个测量修正 / CI 检测程序 | peak KV 14.3 vs 35.5/35.3 MiB；持久层 +0.368 MiB、准确率 +0.015(CI 含 0)→null | 8 组对照×n=100 | 借"null 是结构性的"反向叙事；警示 别把 ablation 当机制证明 |
| **ConServe** 2606 2026 | 会话总成本到达时未知，逐 turn 决策要预测不可观测量 | 脆弱性来自**调度单元**(turn)，不是预测器 | 以会话为单位：一次放置、一次 KV 传输、无学习成本模型 / 新指标 TTFET | 换单元而非加预测器（结构解） | p95 TTFET −51.08%、能耗 −7.51% | 借"换单元而非加预测器"的 gap 句式 |

---

## 二、三个值得逐字拆的动作

**vLLM**：不说"我们更快"，说"连续内存让共享不可能"，再给 pages/blocks/COW 三个可命名对象 ——gap 落在数据结构上。
**HiCache**：一句"收益被容量瓶颈限制"就把分层从优化变成唯一出路 ——先画 capacity→hit-rate，再让机制去移这条线。
**EfficientAgent**：OBR 用一个比值把搬运与重算放进同一量纲 ——我们的"挂起/重算"也需要一个比值+一个 breakeven，而不是策略对比表。

---

## 三、跨论文叙事规律（7 条）

1. **开场三段式**：必然增长的量（上下文/会话数/轮数）× 封顶资源（HBM）× 被浪费的百分比。数字越具体越好（65%/30%、95% 稀疏、40 GB/请求、73% 多轮）。
2. **gap 必须结构性**：不是"现有系统慢"，而是"现有系统的**数据结构/调度单元/serving 模型**使它不可能"——连续内存(vLLM)、请求级(Mooncake)、turn 级(ConServe)、stateless(Pensieve)、LRU(KVFlow)、GPU-only 树(HiCache)。这是机制合法性的唯一来源。
3. **机制名 = 隐喻名词 + 量化旋钮**：名字给想象（page/radix/HiRadix/HiRadixTree/pool/tier/idleness），旋钮给可调性（block size、cache size、steps-to-execution、recompute ratio、OBR）。名字最好复用 OS/存储既有词（page table、buffer pool、write-back）。
4. **"复用—搬运—重算"的演化史**：vLLM 只定性提 swap↔recompute → CacheGen/CacheBlend 把它变成显式决策变量（带宽、偏差）→ kvlive/EfficientAgent 给出 breakeven 与负结果。趋势是**从二选一走向可算的不等式，并明说"何时不值得"**。
5. **分析装置只有四模板**：①浪费分解（60–80%、95% 稀疏、99% 可省）②命中率-容量曲线（40→80%、34→55%）③带宽算术（192 ms、0.86 vs 5.6 µs）④上界/最优性（DFS 定理、2× optimal、min/max 上界、submodular）。我们在 ③+④，**最好能给一个上界**（给定 HBM 与带宽可维持多少会话 / 挂起阈值 breakeven）。
6. **实验骨架固定**：一个"朴素派"baseline（vLLM / LRU / SGLang+HiCache / 全量重算）+ 一档"消融即机制"，headline 是 2–3 位数乘法，且**必须有高压区**——压力不够时机制被淹没（MORI 自陈低并发下所有 offload 命中率都 87–96%）。
7. **分层记忆的天然三幕是"预测—失配—准入"，多数论文只演到第二幕**：容量封顶→跨层放置→靠预测（steps-to-execution / Beta 先验 / OBR）→预测必失配→需要**准入与边界**（MORI 每层准入、EfficientAgent working-set admission、Mooncake 早拒绝）。**第三幕就是我们的位置：不预测，而是核算+挂起。**

---

## 四、对我们这篇的直接含义

- **gap 句**：别人把"内存不够"当**放置/驱逐**问题，于是必须预测未来；而长会话 agent 的真实结构是**可挂起**的——承认"会话可暂停且保状态"，问题就从"预测谁被复用"变成"**核算还能容纳几个活跃会话**"，预测需求消失（同 ConServe"换单元"，但换的是**状态**）。
- **自造的分析装置**：①容量核算式（每会话 KV=f(轮数,上下文,模型)→可容纳会话上界）②挂起 breakeven（换出字节/带宽+恢复延迟 vs 重算 token 成本，比 OBR 多一维"会话时长"）③device/host 带宽算术（CachedAttention 式）。
- **要预埋的负结果**：不是所有长会话都值得挂起（kvlive 的 oracle 负结果），主动给"何时挂起不如重算"的边界，比多刷 1.2× 更立得住机制。
- **三个坑**：投影/模拟当结果（multitier）、ablation 当机制证明（persistmem 点名的结构性 null）、只讲机制不讲策略（kvlive：机制是容易的一半）。

---

## 五、检索备注

- **AgentMem-KV**：arXiv 全库（title/abs/all）无同名论文；最接近的是 2609.33762 EfficientAgent、2606.00866 MORI、2610.07782 persistent-memory。若该名出自某篇 2026 工作，需给 ID。
- **ZeRO-Inference** 无 arXiv，是 DeepSpeed/Microsoft 工程博客，被 FlexGen、H2O 当 baseline 引用。
- **HiCache** 无 arXiv 论文，只有 LMSYS 博客（2025-09-10）；KVFlow 称其为 "SGLang with hierarchical radix cache"。
- "消融"一栏只填有正式 ablation 节的论文（vLLM/SGLang/FlexGen/H2O/SnapKV/PyramidKV）；其余多为参数或组件扫描，未逐篇核。
- arXiv API 本日全程 429（限流），元数据改用 `arxiv.org/search` 与 `arxiv.org/abs` 页面核对；24 篇 PDF 均已落地 `pdftotext`。
