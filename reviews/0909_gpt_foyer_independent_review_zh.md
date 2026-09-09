# Foyer 独立研究评审

审计对象：`TobyMint/foyer`，commit `fa0095a60f386d8a6105943568a924d82405c21c`（2026-09-09）。结论基于仓库原始日志、提交代码，以及截至 2026-09-09 可查的一手论文与官方文档。

## 按严重度排序的发现

### 1. 致命：核心“到达时可观测”在实现中是逐会话未来信息泄漏

**结论。** Foyer 不是只读首 prompt 和历史分布，而是在启动时预读每个会话的完整 trace，保存该会话未来每轮 `input_len`、`output_len` 和全程峰值；准入时再取未来 3 轮的真实增长。这是 clairvoyant oracle，不是可部署的 arrival-time predictor。它直接破坏“前馈方法优于反馈方法”的公平性与外部有效性。

**证据。** [`controller_budget2.py:103–130`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/scripts/controller_budget2.py#L103-L130) 预读 `appends/outs/peaks`，`horizon()` 按当前 session id 索引未来三轮；论文却把它表述为“trace 可观测”并等同于真实到达可观测（[`draft-v1.zh.md:86–90`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/paper/draft-v1.zh.md#L86-L90)）。此外，runner 把该轮真实 `output_len` 作为 `max_tokens`，并 `ignore_eos=true` 强制精确生成到该长度（[`backend.rs:69–83`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/runner/src/backend.rs#L69-L83)、[`backend.rs:173–190`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/runner/src/backend.rs#L173-L190)）。所有策略因此获得当前轮长度 oracle，Foyer 额外获得未来轮 oracle。

**修复建议。** 将“oracle-horizon”降为不可部署上界；正式方法只能使用请求到达前已经完成的其他会话、当前 prompt、应用/工具类型等特征，输出增长分布或高分位数而非点真值。按时间/应用/agent 类型划分训练、校准、测试集，报告预测误差、覆盖率、分布漂移和保守度—吞吐曲线。

### 2. 致命：控制器预测的会话与实际获准会话不是同一个

**结论。** 控制器只判断 `queued[0]` 是否 fit，却只向 runner 写一个标量 cap；runner 同时 spawn 全部 session，任意轮询 task 都可能抢到新增 slot。因此当前系统并没有实现“按会话 token 需求选择谁入场”，论文 §5.2 的机制解释不成立，收益很可能来自 cap≤4、单飞节流和 SLO 阀，而非 size-aware admission。

**证据。** 预测固定取队首见 [`controller_budget2.py:237–263`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/scripts/controller_budget2.py#L237-L263)；所有任务并发创建见 [`main.rs:125–131`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/runner/src/main.rs#L125-L131)；每个 task 独立轮询标量 cap 见 [`session.rs:98–121`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/runner/src/session.rs#L98-L121)。实际 Foyer 前 20 个 admission ordinal：25 档为 `0,4,3,12,5,...`，50 档为 `0,38,35,29,40,...`，200 档为 `0,34,177,22,139,...`，并非 trace FIFO。三档控制日志的最大 cap 都是 4。`active_sessions` 的 load/store 也不是原子 compare-and-swap，理论上可超额准入。

**修复建议。** 控制器必须发放绑定 session id 的 permit，runner 使用一个中心 FIFO/优先队列原子地完成选择与计数；日志逐次记录候选、预测需求、被选 session、实际增长和拒绝理由。增加 `first-prompt only`、历史分布、常数需求、随机选择、oracle future 五档消融。

### 3. 致命：“Concur 式 AIMD”并非忠实复现，不能支持“前馈胜反馈”

**结论。** 当前 AIMD 改了 Concur 的核心控制律、慢 15 倍采样，并且在窗口缩小时不能 pause/resume 已在场 agent。三轮手工调参不能弥补算法语义不一致；这是对主结论最直接的 baseline invalidity。

**证据。** [Concur](https://arxiv.org/abs/2601.22705) 的控制律仅在 `U < U_low` 时加性增长，并定义 agent-level `admit/pause/resume`。仓库注释也写成该公式（[`controller_aimd.py:2–9`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/scripts/controller_aimd.py#L2-L9)），但实现实际在任何 `usage < 0.90` 且未触发 congestion 时增长，`u_low` 完全未使用（[`controller_aimd.py:77–90`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/scripts/controller_aimd.py#L77-L90)）。运行器给 AIMD 30s 周期（[`run_matrix.py:176–184`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/scripts/run_matrix.py#L176-L184)），Foyer 默认 2s；而 session slot 整个生命周期持有，窗口下降只阻止新人，不能暂停活跃 agent（[`session.rs:87–90`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/runner/src/session.rs#L87-L90)）。

**修复建议。** 优先运行作者代码；否则逐条复现论文控制律和 pause/resume，并用一致的观测周期。报告原论文参数、跨硬件重调参数及完整网格，另加 `Concur + size hint` 混合基线。

### 4. 高：所谓 oracle cap 未被证明，且同档策略的 KV 容量不一致

**结论。** 仓库没有足以称为 oracle 的完整 cap sweep；尤其 Foyer 三档实际 cap 最大都为 4，却在 25/50 档只对比 cap6，没有最关键的 cap4/“cap4+单飞”对照。同一负载档的 KV pool 也不同，违反受控实验。

**证据。** 200 档仅留下 cap4/8/16，25/50 档仅有 cap6 的最终结果，未见 cap1–N 全扫或独立验证集选参。元数据中，25 档 default/cap6/AIMD 是 114,495 tokens，而 Foyer 是 101,432；50 档 default/cap6/AIMD/Foyer 分别为 76,018/101,432/114,495/101,432（各 run `metadata.json:9`），与论文“25/50 档均 101,432”不符（[`draft-v1.zh.md:121–124`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/paper/draft-v1.zh.md#L121-L124)）。策略还分布在 GPU 0/2/3 上，未随机交错顺序。

**修复建议。** 锁定相同 SGLang commit、GPU、时钟、KV pool token 数与所有 server flags；随机交错策略顺序。对每档完整扫描 cap，并把选 cap 的 trace 与评估 trace 分开；至少加入 static cap4、paced cap4、cap4+SLO valve，以隔离 token forecast 的真实贡献。

### 5. 高：新颖性层级只能判为“边际”，不是明确新颖

**结论。** “agent 作为准入单位、保护跨轮 KV、避免中期 thrashing”已由 Concur 直接覆盖；“按历史预测未来 KV/内存再决定是否接纳”已由请求级工作覆盖。Foyer 剩余的新意是把可靠的跨轮增长预测用于会话级准入，但当前实现是 oracle 且未定向执行，尚未形成可信的新技术贡献。

**证据。** [Concur (2026)](https://arxiv.org/abs/2601.22705) 已提出 proactive agent-level admission；[Past-Future Scheduler / ASPLOS 2025](https://arxiv.org/abs/2507.10150) 已用历史输出长度分布预测未来内存并执行 admission；[Continuum (2025/2026)](https://arxiv.org/abs/2511.02230) 已做 multi-turn program scheduling、工具时长预测和 KV retainment；[TokenCake (2026)](https://arxiv.org/abs/2510.18586) 已做 agent-aware admission/reserved capacity；[Autellix (2025)](https://arxiv.org/abs/2502.13965) 已把 program 作为调度一等公民；[InferCept (ICML 2024)](https://proceedings.mlr.press/v235/abhyankar24a.html) 与 [CachedAttention (USENIX ATC 2024)](https://www.usenix.org/conference/atc24/presentation/gao-bin) 已处理跨轮 KV 保留/复用。SGLang 自身也通过 `new_token_ratio` 与 `schedule-conservativeness` 做请求级未来 decode 预留；官方文档明确建议在 retraction 频繁时增大 conservativeness（[SGLang 文档](https://docs.sglang.io/docs/advanced_features/hyperparameter_tuning)）。

**修复建议。** 重写定位为“uncertainty-aware, cross-turn session demand admission”，不要把 agent-level admission 本身当贡献。核心应是可在线校准的需求分布、风险预算/机会约束控制及预测失败下的鲁棒性；与 Past-Future、Concur、Continuum/TokenCake 和 engine-native reserve 正面对比。

### 6. 高：执行相 TTFT 不是用户 TTFT，“无吞吐代价”也不完全成立

**结论。** 表 1 的 `<10s SLO` 从请求真正发给后端后计时，排除了数十分钟门外等待，不能称为用户侧 TTFT SLO。50 档 Foyer 的 session p50 反而劣于 cap6；25 档 wall 也慢 15%。不过 200 档 session completion 和 wall 的确优于 cap4，这部分结果值得保留。

**证据。** 论文承认 TTFT 不含准入等待（[`draft-v1.zh.md:121–125`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/paper/draft-v1.zh.md#L121-L125)）。从 `steps.jsonl + metadata.started` 重算：50 档 Foyer arrival→first-token p50=30.61min，cap6=29.73min；session completion p50=38.83min vs 34.17min。25 档 wall 为 1865.6s vs cap6 1622.2s，Foyer 慢 15.0%。200 档 Foyer completion p50=108.08min vs cap4 121.71min，wall=13627.7s vs 14026.9s。

**修复建议。** 将现指标改名 `backend execution TTFT`；主报 arrival-to-first-token、job/session completion CDF、goodput（在明确端到端 SLO 下）、吞吐和失败。离线 batch 场景应以 makespan/JCT 为主，交互式 serving 才以用户 TTFT 为主，不能混写。

### 7. 高：单次运行尚不足以证明 7.3pp，且“安全阀”不是边缘组件

**结论。** 200 档 56.9% vs 49.6% 的差值从会话采样角度看是有信号的，但单次系统 run 无法估计异步调度、GPU 状态和策略顺序带来的方差。SLO 阀在 15.8%–24.1% 的控制周期处于 breach，不能在消融前称为偶尔触发的安全阀；因此“前馈胜反馈”仍缺因果证据。

**证据。** 对两 run 的 199 个共同成功 session 做配对 session-cluster bootstrap（20,000 次、按 session 聚合 cached/prompt token ratio），差值为 7.26pp，95% CI=[4.03,10.46]pp；该区间不包含 run-to-run 变异，也不满足 session 间独立（共享同一缓存）。控制日志中，25/50/200 档 `slo_breach` 周期占 15.8%/24.1%/20.8%，排除 hard-stop 后仍占 13.2%/20.9%/15.2%。

**修复建议。** 同 GPU、相同 pool、随机交错策略做至少 5 次独立 run；主统计单位是 run，报告配对差值 CI，并在 run 内按 session/block bootstrap。完成三组件消融、参数敏感性和 `forecast-only vs valve-only` 2×2；不要只给逐请求 p 值。

### 8. 高：三档“负载”不是独立/真实到达分布，且固定五轮特别有利于 horizon=3

**结论。** 三个 CSV 是同一有序 trace 的嵌套前缀，所有 session 同时到达、每个恰好五轮。25/50 档全是 Claude，200 档混入 55 个 Codex；因此“负载变化”同时改变了工作负载组成，且没有验证持续到达、突发与长 horizon agent。

**证据。** 独立读取 `data/replay_night{25,50,200}.csv`：分别 25×5、50×5、200×5=1000 行；25 文件等于 50 文件前 125 行，50 文件等于 200 文件前 250 行。CSV 无 `arrival_time_ms` 列，runner 默认到达 0；agent 组成分别为 25 Claude、50 Claude、145 Claude+55 Codex。未来三轮 horizon 在五轮截断中覆盖了大部分剩余生命周期。

**修复建议。** 从全量 trace 分层随机抽样多个 seed；保留自然轮数，覆盖 1–100+ 轮；重放原始或合成的 Poisson、bursty、diurnal 到达；按 agent/app/tool 类别留出 OOD 测试。分别控制“并发量”和“组成”，不要用嵌套前缀代替重复。

### 9. 中：所选两 run 验数一致，但仓库统计链与若干论文数字不自洽

**结论。** 指定的独立验数通过，说明表 1 的两行不是抄错；但 200 档轮数、失败口径和聚合脚本 provenance 需要修正。

**证据。** 仅从 `steps.jsonl` 取 `status=SUCCESS` 且 `first_token_ms!=null`：

| run | 成功/记录 | TTFT p50 | `<10s` | SLO率 | 失败 | `comparison.csv`/表1 |
|---|---:|---:|---:|---:|---:|---|
| load25_budget2 | 125/125 | 4.30234s | 87 | 69.6% | 0 | 一致 |
| load50_budget2 | 250/250 | 4.248625s | 169 | 67.6% | 0 | 一致 |

但 `replay_night200.csv` 有 1000 数据行，不是论文所写 980；受控策略的共同 1 个失败来自同一条空 prompt/空 output 记录（CSV 第 832 行）导致 HTTP 400，应视为输入清洗错误。`comparison.csv` 有 `fails/oks/ttft_slo10` 三列，而提交的 [`agg.py:93–100`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/scripts/agg.py#L93-L100) 不会生成这些列，当前表不能由仓库脚本完整再生。

**修复建议。** 清洗空请求后全矩阵重跑；固定并文档化成功、失败、无首 token 与超时的分母；提交唯一版本的 aggregation/test 脚本与环境锁文件，CI 中从日志重生论文表并做 golden check。

### 10. 中：把 `schedule-conservativeness=2/4` 加进来是必要但不充分

**结论。** 该实验能界定 engine request-level reserve 的能力，但不能单独回答“引擎自己就行”。它只覆盖当前 request 的 decode 预留，Foyer 声称覆盖跨工具间隔的未来 turns；同时当前 runner 已把真实 output length 作为 `max_tokens`，会让 engine reserve 获得异常准确的信息。

**证据。** SGLang 官方文档说明 conservativeness 调节 retraction/利用率权衡，并建议在 retraction 频繁时增大（[官方调参文档](https://docs.sglang.io/docs/advanced_features/hyperparameter_tuning)）；仓库 launch 未记录该 flag，等价默认 1.0（[`run_matrix.py:72–76`](https://github.com/TobyMint/foyer/blob/fa0095a60f386d8a6105943568a924d82405c21c/scripts/run_matrix.py#L72-L76)）。

**修复建议。** 做 `conservativeness × Foyer on/off` 因子实验，并加入 engine-native `max-running-requests`、不同 `max_tokens` 真实性、retraction 与 prefix retention 指标；若两者收益可叠加，才可清楚证明层级正交。

## 投稿判断

当前证据强度不足以投 CCF-B 系统会议或 FGCS/JSA 档期刊：建议按 **reject / major redesign** 处理，而不是等误差棒和现有消融出来就投稿。硬门槛依次是：移除未来泄漏、实现定向会话准入、忠实复现 Concur、统一 KV 容量并补全 cap oracle、改用端到端指标；随后才是重复、消融、参数敏感性、第二/第三模型与硬件、真实到达和 OOD trace。若这些完成，并把贡献收敛为“不确定性可控的跨轮 KV 需求预测 + 会话级准入”，CCF-B/二区才有现实机会。

## 总体判断（200字以内）

新颖性：**边际**。最致命风险不是误差棒，而是 Foyer 读取逐会话未来三轮、实际又不能定向放行，同时 Concur 基线并不忠实，故“前馈胜反馈”的因果结论尚未成立。当前不够 CCF-B/二区；但问题重要，若重做在线预测、准入原语与公平基线，值得继续投入。
