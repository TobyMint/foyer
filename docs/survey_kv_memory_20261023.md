# KV cache / 内存层级 / 前缀复用：21 篇的**叙事结构**横查（2026-10-23）

> 目的：不是比数据，是拆"故事怎么搭"。每篇只问四件事——**痛点怎么演、gap 为什么是结构性的、
> 机制靠哪个可算的量立住、实验怎么把机制逼出来**。
> 来源：arXiv PDF 全文（`pdftotext`）+ HiCache 官方博客；`†` = venue 取自公开出版信息而非 PDF 内标注，
> 引用前请再核。**AgentMem-KV 在 arXiv 检索不到同名论文**（见 §5），已用同期 3 篇 agent-memory KV 论文替代。

---

## 一、速查表（21 篇）

| 论文 | 开场 dramatize 的痛点 | 声称的 gap（为什么结构性） | insight + 机制组件 | 分析 / 理论装置 | 实验叙事 | 可借 / 没讲清 |
|---|---|---|---|---|---|---|
| **vLLM** `2309.06180` SOSP'23 | 13B on A100：权重 65%、KV >30%，且"涨缩不定" | KV 存**连续**内存——不是实现慢，是数据结构让"按需增长+共享"不可能，浪费 60–80% 显存 | OS 分页→PagedAttention；block table；COW 块级共享；swap / recompute 二选一；集中式 KV manager | 碎片按内部/外部显式记账；唯一一句机制比较："swap 还是 recompute 取决于 CPU–GPU 带宽与算力"，**无公式** | FasterTransformer/Orca → 同延迟 2–4×；消融=共享 vs 不共享 | 借 OS 隐喻 + "浪费百分比"开场；漏：回收决策永远定性、无准入 |
| **SGLang** `2312.07104` NeurIPS'24† | LM program 多次调用，调用完 KV 即丢 | 通用引擎对 workload 无感知 → 跨调用复用**结构上为 0** | 前缀是一棵树→RadixAttention；radix tree+LRU；cache-aware 调度；frontend hint | 定义命中率并**证明**：按 radix 树 DFS 顺序访问可达离线最优（cache≥最长请求）；实测 52.4%/74.1%，bench 50–99% | Guidance/LMQL/vLLM → 6.4×；消融分 RadixAttention / FSM | 借"命中率可证+可测"双轨；漏：树只在 GPU 内，容量→命中率无模型 |
| **HiCache**（LMSYS blog, 2025-09） | 上下文变长、客户端变多 → 命中率掉，因为历史 KV 必须被驱逐 | GPU-only radix tree **容量封顶**，"caching benefit is inevitably limited by a capacity bottleneck" | HiRadixTree 当跨层页表；GPU-assisted I/O kernel；page-first 布局+zero-copy；layer-wise overlap；写策略 write-through / write-through-selective / write-back；预取 best-effort vs wait_complete | 无公式；用"容量→命中率"经验曲线 + 生产数据（40%→80%、TTFT −56%、官方 6× / −80%） | 长上下文 + 多轮两套；后端 3FS/Mooncake/NIXL | 借"容量封顶→命中率下降"这条因果链；漏：无挂起语义、预取与调度只给定性策略 |
| **LMCache** `2510.09665` 2025 | 真实部署统计：用户存的 KV 总量"远超 GPU 容量"，reuse-per-token 持续上升 | 缺引擎外的 KV 层；现有 offload 是引擎私有、不可跨引擎 | KV 该是独立存储层+buffer-pool 式 API；connector 解耦；控制 API（pin/lookup/cleanup/move/compress）；chunk 粒度>page | 带宽-粒度论证（chunk 才能吃满带宽）；反直觉发现：**context truncation 让前缀命中率减半** | vLLM+LMCache → 15× 吞吐（多轮 QA/文档分析） | 借"生产统计当开场证据"；漏：不判断"该不该挂起" |
| **CacheGen** `2310.07240` SIGCOMM'24 | 长上下文 prefill 决定 TTFT；复用 KV 就得过网络 | KV 太大 → **网络是隐藏瓶颈**，不是算力 | KV 张量分布有局部性→自定义 tensor encoder（量化+算术编码）；压缩级别随带宽自适应；低带宽回退"发文本重算" | 带宽–延迟权衡曲线；"发文本 vs 发 KV"的 breakeven（质量约束下） | 量化基线 → 延迟 3.2–3.7×、带宽 3.5–4.3× | 借"搬运 vs 重算"变成显式决策变量；漏：质量门限靠经验 |
| **CacheBlend** `2405.16444` EuroSys'25 | RAG 多 chunk 拼接，KV 只能前缀复用 | 非前缀复用丢 cross-attention（F1 0.35→0.15）→**收益结构上拿不到** | 只重算 KV 偏差最大的少数 token（HKVD），且跨层可预测；选择性重算与 KV 加载流水线重叠；允许 KV 放慢设备 | 把"重算比例 r"映射到 attention 偏差 Δattn；r=5–18% 时质量损失 ≤0.002（可当 breakeven） | 全量重算/全量复用 → TTFT 2.2–3.3×、吞吐 5× | 借"部分重算"当第三档（挂起恢复同构）；漏：仍假设 KV 可得 |
| **FlexGen** `2303.06865` ICML'23 | 单卡 16GB 跑 175B，offloading 是唯一出路 | 现有 offload 继承训练策略 → I/O 过量、"远低于硬件上限" | 形式化 (compute schedule, tensor placement, delegation) 搜索空间；LP 求解；Zig-Zag 调度；groupwise 4-bit | **证**搜索空间内 I/O 复杂度 ≤ 最优 2×；给出 batch size 上界 | T4 上 OPT-175B 1 token/s、batch 144；vs ZeRO-Inference/Accelerate 69× | 借 LP+上界句式；漏："延迟不敏感"假设，无在线准入 |
| **ZeRO-Inference**（DeepSpeed 博客'22，非 arXiv） | 模型比 GPU 大 | 没有系统层面的"权重/状态放哪"抽象 | 权重与 KV 常驻 CPU+NVMe，按层预取 | 无正式分析（工程 blog 体） | 被 FlexGen/H2O 当作"朴素搬运派"baseline 引用 | 借：作"搬运派"原型；漏：无模型，正好当我们的对照起点 |
| **InfiniGen** `2406.19707` OSDI'24 | KV 随长度线性涨；offload 后 PCIe 成为新瓶颈 | 全量搬运=把带宽当免费；精度要求又不许乱丢 | 用当前层输入 + 下一层部分 Q/K 权重做"最小排练"，**推测**下一层关键 token，只预取这些 | 排练成本 vs 带宽节省的对比；正交旋转保数学等价 | 现代 offload 系统 → 3.00×（同精度） | 借"预测未来重要度"；漏：单请求、静态 batch |
| **H2O** `2306.14048` NeurIPS'23 | KV 随长度线性涨，显存被吃光 | 均匀保留 token 是浪费：attention 95% 稀疏 | Heavy Hitter + recent 固定预算；形式化为**动态 submodular**；greedy 近似 | 给出（温和假设下）near-optimal 保证；"20% 预算可撑"的上界论证 | DeepSpeed/FlexGen → 29×/3× | 借"稀疏度→容量上界"；漏：长链任务质量不稳 |
| **SnapKV** `2404.14469` NeurIPS'24 | 长输入下 KV 线性增长 | 生成**之前**无法知道哪些位置重要 | 最后 observation window 的 attention 与生成时高度一致→投票选 token | 自定义 **hit rate** 指标 + 鲁棒性分析（换 instruction 命中率会掉） | 16K 输入 3.6× 速度、8.2× 内存 | 借"用 hit rate 度量预测质量"；漏：单轮 QA |
| **Quest** `2406.10774` ICML'24 | KV 读取占 >50% 延迟 | token 重要度**依赖 query**，静态选择必然错 | page 内 K 的 min/max 给出 attention 权重的**上界**→选 top-K page；只在后层启用 | 显式上界推导 + 选择开销 5–10 µs | 2.23× attention、7.03× 延迟 | 借"上界→剪枝"论证；漏：单请求 |
| **PyramidKV** `2406.02069` 预印 | 各层信息聚合呈"金字塔漏斗" | 所有层同一预算 = 结构性错配 | 层间预算金字塔（底层多、顶层少）+ attention 分数选 token | 预算–质量曲线 | vs SnapKV/H2O 固定预算 | 借"预算在层间再分配"；漏：总量仍固定 |
| **Mooncake** `2407.00079` FAST'25 | Kimi 生产：KV 是瓶颈，而集群 CPU/DRAM/SSD 大量闲置 | 传统请求级调度假设"所有请求都会被执行"→过载时 SLO 必崩 | KVCache-centric Conductor；分离式 KV 池；chunked pipeline parallelism；layer-wise prefill；**prediction-based early rejection**；热块复制 | 用 **占用成本 S·T**（KV 大小×处理时间）当调度代价；命中率-容量曲线（1k→50k blocks：34%→55%）；早拒绝会震荡→需预测负载 | 模拟 525% 吞吐（守 SLO）；真实 Kimi +75% 请求 | 借"拒绝=准入"与 S·T 核算；漏：拒绝即丢状态，没有"挂起"这一档 |
| **MemServe** `2406.17565` 2024 | serving 从 stateless 变 stateful，KV 生命周期与作用域同时变长 | 请求内（PD 分离）与请求间（前缀缓存）优化各自为政，缺统一抽象 | MemPool 弹性内存池+API；全局调度器；prompt-tree 局部性感知路由；huge page 共优化布局与传输 | 显式 cost model：对每实例预测 exec(x′,y_p′)+exec(x,y_p) 取 argmin；结论句"context caching 收益随轮数**线性**增长" | vs vLLM → 吞吐/延迟 | 借"收益随轮数线性增"的必要性论证；漏：集群级，单卡不适用 |
| **Pensieve** `2312.05516` SIGMOD'25 | 现系统"stateless across requests"，每轮重算整段历史 | 无状态是结构性的：请求结束即丢 KV | 多级 GPU-CPU cache；ahead-of-time swapping（与计算重叠）；被驱逐 token 只重算该部分；非连续 KV 让 prefill/decode 同批 | 换出 vs 按 token 重算的二选一；保守双向带宽策略 | vLLM/TensorRT-LLM → 1.14–3.0× | 借"stateful vs stateless"最锋利的 gap 句；漏：容量上限固定、无准入 |
| **CachedAttention** `2403.19708` ATC'24 | ShareGPT：73% 会话多轮、30% 超 4K token，每轮重算 | 引擎把 KV 当请求内临时态 | AttentionStore 分层（HBM/DRAM/SSD）；layer-wise 预载；异步保存；scheduler-aware fetch/evict；位置编码解耦+截断保有效 | **带宽算术**：2K token KV 走 PCIe Gen4（26 GB/s）≈192 ms，磁盘 <5 GB/s；缓冲公式 S_buf = B(T_load·L_hist − T_pref·L_new)；上界"最多省 99% prefill" | TTFT −87%、prefill 吞吐 7.8×、成本 −70% | 借带宽算术+缓冲公式；漏：驱逐只给 hint，无准入语义 |
| **KVFlow** `2507.07400` 2025 | 多 agent 工作流反复调用同一批 agent，LRU 在复用前把 KV 驱逐 | LRU 对未来一无所知，而工作流是**可预测**的 | Agent Step Graph → 每 agent 一个 **steps-to-execution**；KV 节点级细粒度驱逐；树形前缀保留；全重叠后台预取 | 用"时间距离"替代 recency；预取把 miss 停顿移出关键路径 | vs SGLang 分层 radix cache → 1.83×/2.19× | 借"把未来变成可算的数"；漏：假设图已知、无容量准入 |
| **kvlive** `2609.16215` 2026 | HBM 最贵，KV 是最大占用者；长会话必须跨层 | "机制是容易的一半，**放置策略**才是难的" | 三级模拟器（HBM/DRAM/SSD）+ 策略网格 + future-reading oracle | 容量结果与策略无关（会话数 73.02×、成本 62.04×）；**负结果：连读未来的 oracle 预取都不赚带宽** | 策略×容量网格（全部为模拟） | 借"机制 vs 策略"二分法；漏：纯模拟、无挂起/准入 |
| **MORI** `2606.00866` 2026 | tool-call 空窗里 KV 白占 HBM，LRU 抓不住"快/闲"两相结构 | busy/idle 二值化与硬件容量比不匹配 | **idleness 是连续、相对的**：按 idleness 排序，最忙进 HBM、最闲进 DRAM，边界随容量比移动；**每层做准入**；亲和负载均衡 | 用"容量比 vs busy:idle 比"讲失配；低并发下所有 offload 系统命中率都 87–96%→机制被淹没 | Claude Code 真实 trace → 20–71% 吞吐、18–43% TTFT | 借"把状态保留写成排序问题"；漏：无硬核算、无 SLO 保证 |
| **EfficientAgent** `2609.33762` 2026 | agent 每轮重发全对话，host offload 是常态 | 现有系统 per-token 决策（load 便宜就 load），**没有 working-set 概念** | OBR（offload benefit ratio）；每 rank KV 字节 β_rank；content-key 存活预测；working-set-aware admission | OBR = 1 − T_load/T_rec，T_load = nβ/B + τ；H20 上 0.86 µs/token vs prefill ≥5.6 µs/token → **OBR ≥ 0.84**；硬件判据=每字节 host 带宽的算力（H800 是 H20 的 6.7–7.0×） | 3 GPU×2 模型；命中率随算力/带宽比变化 | 借 OBR（我们"搬运 vs 重算"的现成公式）；漏：无会话级挂起与准入的端到端 |
| **multitier** `2604.26968` 2026 | 单请求 40 GB KV，batch 掉到个位数 | 无跨 MHA/GQA/MQA/MLA 的统一 sizing，也无跨 6 层统一管理 | 架构感知 sizing；6 层（含 CXL）；Beta 先验复用预测；EMA 头粒度驱逐；RoPE 预取 | β/token/layer 公式（MLA 1152 B vs MHA 65536 B）；命中率 70–84%；集群投影 4150 tok/s/GPU | trace replay + **分析投影**（无真机） | 借"并发上限由 β 公式推出"的核算写法；反面教材：投影当结果 |
| **persistmem** `2610.07782` 2026 (ML4Sys) | agent 分解让单次调用 KV 有界；很多系统加"持久记忆层"并用 ablation 证收益 | 这类 ablation **结构上测不出东西**（单题 benchmark 每题自带证据） | 三层 agent 架构；四个测量修正；CI 检测程序 | peak KV 14.3 MiB vs 35.5/35.3；持久层 +0.368 MiB、准确率 +0.015（CI 含 0）→ null | 8 组对照 × n=100 | 借"null 是结构性的"反向叙事；警示：别把 ablation 当机制证明 |
| **ConServe** `2606.01839` 2026 | 会话总成本到达时未知，逐 turn 决策要预测不可观测量 | 脆弱性来自**调度单元**（turn），不是预测器 | 以会话为单元调度：一次放置、一次 KV 传输、无学习成本模型；新指标 TTFET | 用"换单元"消掉预测需求（结构解，不是模型解） | p95 TTFET −51.08%、能耗 −7.51% | 借"换单元而非加预测器"的 gap 句式 |

---

## 二、三个值得逐字拆的机制故事

**1）vLLM：把 OS 隐喻一次性兑现。** 它不写"我们更快"，它写"连续内存让共享不可能"，
然后给出 pages/blocks/COW 三个可直接命名的对象，最后用"浪费百分比"把因果闭环。
**动作**：*gap 必须落在数据结构上*，机制名直接借操作系统词汇，读者零成本理解。

**2）HiCache：把"容量"写成命中率的第一自变量。** 一句话完成必要性论证——
"收益被容量瓶颈限制（cache hit rate declines because most historical KV must be evicted）"。
于是分层不是优化而是**唯一出路**。**动作**：先画 capacity→hit-rate 曲线，再让机制去移动这条曲线。

**3）EfficientAgent：把"搬运 vs 重算"变成不等式。** OBR 用一个比值把两件事放进同一量纲，
并给出硬件判据（每字节带宽的算力）。**动作**：我们的"挂起 vs 重算 vs 驱逐"三选一，
也应当有一个 OBR 式的比值 + 一个 breakeven 点（挂起多久才划算），而不是策略对比表。

---

## 三、跨论文叙事规律（7 条）

1. **开场三段式**：一个必然增长的量（上下文/会话数/轮数）× 一个封顶的资源（HBM）× 一个被浪费的百分比。
   数字越具体越好（65%/30%、95% 稀疏、40 GB/请求、73% 多轮）。
2. **gap 必须"结构性"**：不是"现有系统慢"，而是"现有系统的**数据结构/调度单元/serving 模型**使它不可能"
   ——连续内存(vLLM)、请求级调度(Mooncake)、turn 级(ConServe)、stateless(Pensieve)、LRU(KVFlow)、GPU-only 树(HiCache)。
   这是机制合法性的唯一来源：**换机制才可能，调参不可能**。
3. **机制命名 = 隐喻名词 + 量化旋钮**。名字给想象（page/radix/HiRadix/pool/tier/idleness），
   旋钮给可调性（block size、cache size、steps-to-execution、recompute ratio、OBR）。
   名字最好复用 OS/存储的既有词（page table、buffer pool、write-back）。
4. **"复用—搬运—重算"三段论的演化史**：vLLM 只定性提 swap vs recompute → CacheGen/CacheBlend 把它变成显式决策变量
   （带宽、偏差）→ kvlive/EfficientAgent 给出 breakeven 与负结果。趋势是**从二选一走向可算的不等式，并明说"何时不值得"**。
5. **分析装置只有四种模板**：①浪费分解（60–80%、95% 稀疏、99% 可省）②命中率-容量曲线（40→80%、34→55%）
   ③带宽算术（192 ms、0.86 vs 5.6 µs）④上界/最优性（DFS 定理、2× optimal、min/max 上界、submodular）。
   我们的容量核算属于 ③+④——**最好能给出一个上界**（给定 HBM 与带宽可维持的会话数 / 挂起阈值 breakeven）。
6. **实验套路的固定骨架**：一个"朴素派"baseline（vLLM / LRU / SGLang+HiCache / 全量重算）+ 一档"消融即机制"，
   headline 是一个 2–3 位数的乘法，而且**必须有高压区**（过载、容量扫档、并发扫档）——压力不够时机制会被淹没
   （MORI 自陈：低并发下所有 offload 系统命中率都 87–96%）。
7. **分层记忆的天然三幕是"预测—失配—准入"，但多数论文只演到第二幕**：容量封顶 → 需要跨层放置 → 放置要靠预测
   （steps-to-execution / Beta 先验 / OBR）→ 预测必然失配，于是需要**准入与边界**（MORI 每层准入、EfficientAgent
   working-set admission、Mooncake 早拒绝）。**第三幕正是我们的位置：不预测，而是核算 + 挂起。**

---

## 四、对我们这篇论文的直接含义

- **gap 句可以这样立**：现有工作把"内存不够"当成**放置/驱逐**问题（往哪儿放、丢谁），
  于是必须预测未来（步骤、先验、存活）；而长会话 agent 的真实结构是**可挂起**的——
  一旦承认"会话可以暂停并保状态"，问题就从"预测谁会被复用"变成"**核算还能容纳几个活跃会话**"，
  预测需求消失（与 ConServe"换单元而非加预测器"同一手法，但换的是**状态**而非调度单元）。
- **需要自造的分析装置**：①容量核算式（每会话 KV = f(轮数, 上下文, 模型) → 可容纳会话上界）
  ②挂起 breakeven（挂起成本 = 换出字节/带宽 + 恢复延迟；对照重算 token 成本）——直接对标 OBR，
  但加"会话时长"这个维度；③device/host 分层的带宽算术（CachedAttention 式）。
- **要预埋的负结果**：不是所有长会话都值得挂起（kvlive 的 oracle 负结果、multitier 的投影教训），
  主动给出"何时挂起不如重算"的边界，比多刷 1.2× 更能立住机制。
- **必须避开的三坑**：①投影/模拟当结果（multitier）②ablation 当机制证明（persistmem 点名的结构性 null）
  ③只讲机制不讲策略（kvlive：机制是容易的一半）。

---

## 五、检索备注

- **AgentMem-KV**：arXiv 全库检索（title/abs/all）无同名论文；最接近的是 `2609.33762` EfficientAgent、
  `2606.00866` MORI、`2610.07782` persistent-memory。若该名来自某篇 2026 工作，需提供 ID。
- **ZeRO-Inference** 无 arXiv 版本，是 DeepSpeed/Microsoft 的工程博客，被 FlexGen、H2O 当 baseline 引用。
- **HiCache** 无 arXiv 论文，只有 LMSYS 官方博客（2025-09-10），其设计在 KVFlow 中被称作 "SGLang with hierarchical radix cache"。
- arXiv API 本次全程 429（限流），元数据改用 `arxiv.org/search` HTML 与 `arxiv.org/abs` 页面核对。
