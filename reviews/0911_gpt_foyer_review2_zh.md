# Foyer 二次独立审计

审计对象为 `TobyMint/foyer` 的 `a3e0c8a638146728cad810c83eb12dd681f887ed`，本次核对时也是公开 main 的 HEAD。核查日期为 2026-09-11。判断仅计入该提交实际包含的代码与日志，不计入“今晚运行”“明晨出”的数据；未重跑 GPU 实验。对原始 JSONL 独立计算指标，并对当前 Python 控制器做了无 GPU、固定输入的隔离测试。没有修改仓库源代码。

## 结论

工程修复值得肯定：F1 的逐会话未来泄漏已移除，F2 的点名准入已实现，F3 的错误增长控制律已改正。但“修复了原始缺陷”与“形成可信的性能因果证据”是两件事。当前复审包仍混入旧版消融、未锁齐的池容量和缺失原始日志的数字；主 run 又存在控制器断档与暂停状态修复痕迹。故评价可上调为“值得继续验证的在线原型”，尚不能上调为“已验证的投稿方案”。新颖性仍为边际。

最高优先级不是继续细扫参数，而是修复参数路由和恢复预算、冻结版本并让实验清单可自动核验。

## 上轮发现逐项判定

| 上轮发现 | 本轮判定 | 核验结果与未关闭部分 |
|---|---|---|
| F1：未来信息泄漏 | 原始问题关闭 | `budget3` 无 trace 输入，读取 queued 的首 prompt 和已完成轮次；但 EMA 点估计不是经过校准的预测分布，也未证明其独立价值。所有策略依然使用真实当轮 output_len 重放，这是共同外部有效性限制。 |
| F2：预测对象与准入对象不同 | 原始问题关闭；恢复协议仍需修 | 初次入场按 session ID 检查 permit，原来的竞争错配消失。当前 resume 仍按首 prompt 而非已知当前上下文算需求；`--disable-single-flight` 还有选择逻辑问题，详见下文。 |
| F3：Concur 基线失真 | 控制律问题关闭；整体公平性部分关闭 | grow/hold/cut 与轮边界 pause/resume 已实现。但参数不是论文配置，缺少按共同目标重调的曲线；改变周期时未归一化增长速率。 |
| F4：池容量错配、oracle 未证明 | 部分关闭 | 已提交的 200 档新主策略均为 101,432；25 档 cap2/7/8 仍为 97,367。cap3 的原始 run 在本提交缺失，200 档也没有 cap1/2。 |
| F5：新颖性边际 | 维持 | 收缩方向合理，新增 EMA 与点名 permit 主要是在把方法做成真实可部署原型，尚未形成有证据的新研究贡献。 |
| F6：TTFT 排除准入等待、无吞吐代价 | 叙事部分关闭；效用未证明 | REVIEW2 承认成本是进步。原始日志确认 JCT 有明显退步，且当前 669 分钟不是干净的算法成本样本。 |
| F7：重复和安全阀消融 | 未关闭 | 新版重复未提交；已提交的 nohw/nosf/nosv 是旧 budget2、旧 trace、旧 pool。不可把 92.2%→63.1% 写成新版 SLO 阀的消融结果。 |
| F8：负载组成与到达分布 | 未关闭 | 作者如实列为未开始。本次不重复扣“已承认”的分，但它依然限制泛化结论。 |
| 中项：清洗、统计管线、引擎基线 | 清洗关闭，其余未关闭 | 受控 200 档新 run 为 999/999 成功；`comparison.csv`、`agg.py`、论文旧稿均未随本轮更新，引擎因子实验未提交。 |

代码依据：[在线预测与数据来源](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/scripts/controller_budget3.py#L91-L183)、[named permit](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/runner/src/session.rs#L204-L235)、[轮边界暂停](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/runner/src/session.rs#L366-L391)、[AIMD2 控制律](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/scripts/controller_aimd2.py#L119-L156)。

## 本轮新增的高优先级发现

### 参数扫可能根本没启动 Foyer

**结论：当前 HEAD 的参数路由存在确定性错误；在确认生产命令与实际 argv 前，“调参悬崖”不能解释为机制现象。**

`run_matrix.py:241` 只有 `elif mode == "budget3"` 才启动在线控制器，但 `:247` 又在这个分支内部测试 `":" in mode`。因此 `budget3:target=0.80` 不会进入分支。未识别的 mode 没有报错，继续以空 `cap_args` 启动 runner，即可能成为无限流。另一方面，`:145` 使用逗号分隔 run，和参数列表的逗号冲突。对实际解析函数的隔离调用得到：

```text
输入：test:budget3:target=0.85,margin=1.0,sf=0
输出：
  ('test', 'budget3:target=0.85')
  ('margin=1.0', 'margin=1.0')
  ('sf=0', 'sf=0')
```

这是一个参数实验被解析成三个 run，而且均非有效的 budget3 mode。对应证据为 [run 解析](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/scripts/run_matrix.py#L143-L151)、[不可达参数分支](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/scripts/run_matrix.py#L241-L259)、[无策略兜底即启动 runner](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/scripts/run_matrix.py#L309-L321)。

仓库没有提交 0.0%/2.1% 调参 run 的原始日志，因此不能断言线上实验一定走了该错误路径——也可能用了仓库外的命令。但是，当前代码不能复现其声称的参数实验，且“无控制器”恰好是必须首先排除的归零解释。

**建议：** 用结构化 JSON/YAML 定义矩阵；未知策略直接失败；运行前打印并保存解析后的策略、完整 argv、PID 与文件哈希；有控制器的 run 必须验证启动、心跳及 permit 生效。先为解析器和命令构建加单元测试，再投入 GPU 时间。

### 主 run 不是可直接计入新版误差棒的冻结版本样本

**结论：67.3% 等聚合数字是真的，但这个 run 的连续性和版本一致性不够干净。**

`budget200c_budget3/controller.jsonl:8830–8831` 的时间从 `1789061853.216` 跳到 `1789064843.587`，断档 **49.84 分钟**。此前运行时间为 **299.97 分钟**，与旧版默认 `--max-minutes=300` 高度吻合；断档期间只有一条 step 完成记录。不能在没有进程记录时简单称其为随机系统方差或纯算法开销。[日志证据](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/results/night/budget200c_budget3/controller.jsonl#L8830-L8831)

实际 admission 日志只有 **4 次 pause、4 次 resume**，不是 REVIEW2 的 11 次。四次暂停持续 480.93、144.59、109.50、81.29 分钟，全部在尾部恢复。`controller.jsonl:17598` 认为 active=0、waiting=0，重启后的 `:17599` 却恢复 waiting=4。提交 `09cdc72` 恰好修复了 pause 被误判为 finished 的错误。这与该 run 经状态修复后恢复的解释相符；至少不能证明它全程执行同一个冻结版本。[暂停/恢复日志](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/results/night/budget200c_budget3/admissions.jsonl#L325)、[尾部状态跳变](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/results/night/budget200c_budget3/controller.jsonl#L17598-L17599)、[修复提交](https://github.com/TobyMint/foyer/commit/09cdc7289f9c1dd0c0c8ec8909175e791214556c)

此外，204 次产生候选的控制周期中，100 次由 starve guard 强制放行，占 **49.0%**；28.6% 的控制周期是 active=0 但 waiting>0。这是观察到的状态比例，不等同于 GPU 空闲时间比例；它提示系统大量依赖兜底计时器，尚未证明预测器负责主要的有效准入。

**建议：** 将该 run 保存为“开发/恢复诊断样本”，不要与两条修好后的 run 合成正式 ×3。修复后至少补足三条同版本、无人工干预的完整运行；异常恢复若是产品能力，应单独做故障注入实验。既不能把所有慢都算成算法必然代价，也不能事后随意减去空窗来美化结果。

### 消融与池容量声明仍不成立，部分关键 run 未提交

**结论：新版因果消融目前没有可审计证据。**

`budget2_nohw/nosf/nosv/metadata.json` 明确为旧策略、旧 trace MD5 `35cf3ca19e`、pool **114,495**；新版主 run 为 trace MD5 `4570fc5561`、pool **101,432**。因此 5.8%、58.5%、51.3% 只能作为旧版诊断。尤其 REVIEW2 所写“拆 SLO 阀，92→63”跨越了算法、trace、pool、准入原语和 shedding，不能作为单变量因果差异。[旧 nosv 元数据](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/results/night/budget2_nosv/metadata.json)、[新版元数据](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/results/night/budget200c_budget3/metadata.json)

25 档 cap2/7/8 的 pool 均为 **97,367**，比声明少约 4.0%，不是 101,432。小差异不能自动当成崩溃主因，但在宣称存在容量悬崖时不能忽略。[cap2 元数据](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/results/night/load25c_cap2/metadata.json#L9)

`git ls-tree` 检查不到 25 档 cap3/cap5、200 档 cap3 或 budget3 调参 run 的原始文件。cap 曲线脚本直接硬编码这些点；数字可能存在于作者机器，但本提交无法独立核验。[绘图硬编码](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/paper/fig_cap_cliff.py#L13-L19)

REVIEW2 把 budget2 的 52.4% 写为“200 档”也有错配：已提交且匹配这个数字的是 `load25c_budget2`，实测 52.426%。旧 budget2 同时使用不同准入/反馈能力，不能称为 budget3 的 oracle 上界。最多称为旧 clairvoyant 变体；真值预测上界必须在同一控制器骨架下比较，并且“多给信息的一个具体启发式”也不自动成为数学上界。

**建议：** 用 manifest 明确每一表格单元的 run ID、版本、pool、trace、参数及口径；由脚本从日志生成表格，缺文件或资源不一致时禁止汇总。

### 当前控制器还有两个可复现的边界错误

**恢复需求低估。** `budget3:240` 对所有 waiting session 使用 `(prompt0 + forecast) × margin`，包括已有较大上下文的暂停会话；runner 的 resume 事件还固定记录 `prompt_tokens=0`。隔离测试中，首 prompt=10,000，已知 ctx=60,000，预测增长=40,944，预算=76,074；当前代码按 need=58,586 放行，尽管已有上下文加预测增长本身就是 100,944。应至少以已知 ctx 而非 prompt0 计算 resume 需求，并处理其缓存是否仍驻留。[需求公式](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/scripts/controller_budget3.py#L234-L259)、[resume 记录](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/runner/src/session.rs#L381-L389)

**关闭 single-flight 时丢失候选。** 隔离测试给三个均能同时 fit 的候选 A/B/C，当前分支为每个候选累加 projection，却不断覆盖单个 `candidate`，最后只发 C 的 permit。它既不是正常 FIFO 的一次放行，也不是正确的批量放行。修复为显式候选集合，或明确只选择一个且不累计未获准候选的需求。[选择与 permit 写入](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/scripts/controller_budget3.py#L236-L259)

原始 F2 的“点名身份一致”仍然成立；这两个问题影响的是需求预算和消融语义，不应混为同一指控。另需补充异步协议测试：runner 只按 `paused` 集合在轮边界停下，不会仅因自己不在 `admit` 中而自动停止，因此撤销应有持续的期望状态与确认记录，不能把一次文件写入当成已完成回收。

## 独立验数与服务代价

下表仅使用本提交存在的原始日志。成功口径为 `status=SUCCESS`；TTFT 取非空首 token 时间；SLO 严格为 `<10s`。hit 为成功请求的 cached token 总数除以 server prompt token 总数，不是逐请求比率的简单平均。

| Run | 成功/记录 | 失败 | hit | 后端 TTFT p50 | 后端 SLO | wall |
|---|---:|---:|---:|---:|---:|---:|
| load25c_budget3 | 125/125 | 0 | 66.759% | 1.325s | 93.600% | 54.827min |
| load25c_aimd2 | 125/125 | 0 | 55.640% | 4.000s | 75.200% | 35.495min |
| budget200c_budget3 | 999/999 | 0 | 67.270% | 1.925s | 92.192% | 669.250min |
| budget200c_aimd2 | 999/999 | 0 | 48.443% | 5.558s | 65.866% | 291.370min |
| budget200c_cap4 | 999/999 | 0 | 45.136% | 8.401s | 52.753% | 265.645min |

以上与 REVIEW2 已给出的对应主数字一致。但如下用户侧时间和单位时间达标数，呈现另一面：

| 200 档指标 | budget3 | aimd2 | cap4 |
|---|---:|---:|---:|
| arrival→first-token p50 | 270.69min | 129.04min | 116.73min |
| session JCT p50 | 278.60min | 131.67min | 119.71min |
| session JCT p95 | 596.41min | 274.22min | 248.15min |
| 后端 `<10s` 成功请求/墙钟分钟 | 1.376 | 2.258 | 1.984 |

到达时刻优先取 queued 事件；cap4 没有 queued，使用 `admit.ts - waited_ms/1000`。JCT 终点取该会话最后一个 step 的 complete_timestamp，不计最后一步之后无后续请求的 tool wait。墙钟则沿用 metadata.wall_s，含 runner 初始化；因此不和 arrival 口径混同。以上只描述这次记录，不能推断修复后必然有同样代价。

“质量—吞吐帕累托”可以作为探索框架，但现在还不能作为成功结论。命中率是系统内部指标，不是任务正确率；后端 TTFT 也没有计入准入与 pause 等待。若仅在两个工作点上分别赢一个轴，不能证明改进了已有方法的前沿。尤其 25 档已有 cap1：hit 68.18%、SLO 95.2%；cap2：SLO 92.0%、wall 38.41min，提示更保守的静态策略可能取得相近后端质量。不过 cap2 的池子不齐，暂不能据此宣布严格支配。

200 档“2.5×”按 REVIEW2 给出的 cap3 数字实际约为 **2.68×**，但 cap3 原始日志缺失。只有预先定义清晰的双重约束（例如端到端会话 deadline + 单轮响应目标），再证明在相同约束下成本更低/可支持到达率更高，代价才具有充分可辩护性。对纯离线 coding-agent batch，JCT、完成吞吐和任务成功比首 token 更直接。

## Concur 与新颖性复核

Concur 原文 Eq.1 与 admit/pause/resume 已被当前代码基本落实，这是本轮真实进展。但论文 §5.1 给出的阈值为 `(U_low,U_high,H_thresh)=(0.2,0.5,0.2)`，仓库继续使用 `(0.35,0.75,0.03)`。3090 重调本身合理，却应称为“同控制律的重调实现”，并同时报告原文配置和公平重调结果，不能仅凭控制律一致就声称全部忠实。30s 改 2s、alpha 仍为 2，会将单位时间加性探测速率提高 15 倍；其退化不能证明反馈方法天然对频率敏感，更不能证明仅在 2s 测过的 Foyer 不敏感。[Concur 原文](https://arxiv.org/html/2601.22705v1#S5.SS1)、[仓库默认参数](https://github.com/TobyMint/foyer/blob/a3e0c8a638146728cad810c83eb12dd681f887ed/scripts/controller_aimd2.py#L74-L82)

新颖性仍是**边际**，但现在有了可被验证的具体落点。边界如下：

| 工作 | 已有覆盖 | Foyer 应证明的区别 |
|---|---|---|
| Concur，2026 | agent-level admission、缓存反馈、暂停/恢复 | 预测跨轮需求在共同目标下的增量价值，而非重复控制层抽象 |
| Past-Future Scheduler，ASPLOS 2025 | 历史分布预测未来批次内存，平衡排队与驱逐、提高 goodput | 从单请求输出长度预测扩展到长期会话增长的不确定性和停止时刻 |
| TokenCake | agent-aware admission、共享/预留容量、工具期间的 KV 调度 | 轻量会话外层控制的成本和预测价值，不应把容量感知本身当首次 |
| Continuum，v7 2026-09-08 | TTL KV retention、program FCFS，直接优化多轮 JCT | 能否在不修改引擎的约束下取得有竞争力的 JCT/服务前沿 |

来源：[Past-Future](https://arxiv.org/abs/2507.10150)、[TokenCake §3–5](https://arxiv.org/html/2510.18586v3)、[Continuum v7](https://arxiv.org/abs/2511.02230v7)。检索还发现 2026-09-09 的 [UNISON](https://arxiv.org/abs/2609.09643)：它用在线会话信息做 KV residency/分层决策，属于相邻方向，不足以单凭摘要判定与 Foyer 重复，但应纳入相关工作清单。

“在线可校准”目前更准确应写成“在线更新的 EMA 启发式”：代码没有预测区间、误差覆盖率或校准过程。Foyer 也已是预测、利用率反馈、TTFT 反馈和计时器共同作用的混合控制器，不能继续使用简单的“前馈战胜反馈”二分叙事。若能证明异质会话下的预测误差如何影响风险预算，并使控制器在分布漂移下稳定扩大可行服务区，才有上调新颖性的理由。

## 下一批最高杠杆的三个实验

执行前门槛：修正参数解析、resume 预算与消融语义；记录 git SHA/文件 hash/完整参数/精确 pool/trace hash，自动拒绝混配。下面三组按优先级排序。

**实验一：共同 SLO 下的静态/反馈/预测成本前沿。** 在相同 GPU/pool/trace 下比较 cap1–4、paced cap2/3、Concur 原文参数与公平重调配置、budget3；先 25 档快速定位，再做 200 档。按预先固定的后端 SLO 和会话 deadline 画出可行前沿，主报 JCT、完成率、单位时间达标数与墙钟。策略顺序随机交错，至少三条干净重复，资源允许用五条。通过标准是相同服务约束下有明确成本/容量收益，不是一个工作点更慢但命中率更高。

**实验二：预测与反馈/恢复能力的因果分解。** 固定同一个 named-permit 骨架、FIFO、high-water、SLO 阀、starve guard，只替换需求预测：零增长、全局历史均值、每会话 EMA、逐会话未来真值参考。再交叉测试 shedding 开/关，优先验证 EMA 相对简单预测是否改善上述前沿。记录预测误差、过/低估、正常与强制准入占比、暂停时长及每次错误准入后的 retraction。若 EMA 没有独立增益，应调整贡献定位，不再把预测器当核心。

**实验三：冻结参数后的异质/动态到达留出验证。** 用未参与调参的至少三个分层抽样 seed，保留自然轮数，分开改变到达强度与组成；测试短/长会话混合、Poisson/突发到达及 agent 类型留出。目标是找出固定 cap 会失配、而预测控制稳定获益的真实区间。首轮若成立，再扩到第二模型与不同 KV 容量；单纯换模型、继续调同一前缀 trace 的杠杆较低。

## 投稿现实性

当前仍不足以支撑 ICDCS/Middleware/IPDPS 或 FGCS/JSA 档的完整论文。这里不是把“未完成的路线图”当成不诚信，而是本提交里还有具体可复现的实验配置错误，且核心效用尚未成立。补两条重复并不自动跨过这些门槛。

若实验一证实服务前沿有稳定改进、实验二能归因到非平凡的需求建模、实验三能说明泛化范围，且补齐引擎基线与复现管线，可以重新讨论 CCF-B/该档期刊。若最终收益只能表达为“严格限流后 cache hit 更高，但任务完成显著更慢”，则不建议继续以当前核心主张扩写论文。

总体判断：原始 F1/F2 真正修复，值得继续；新颖性仍边际。最迫切风险是参数扫可能无控制器、主 run 带开发干预、旧消融被用于新主张。先建立冻结、可核验的服务前沿证据，再决定扩大投入。
