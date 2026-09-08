# Turnstile 夜跑验收报告（2026-09-08 晨）

## 一、完成情况

| Run | 状态 | 说明 |
|---|---|---|
| default | ✅ 完整（3.7h，rc=0） | 197/200 会话 |
| cap8 | ⚠️ 87%（4h 超时截断） | 873/1000 步快照可用 |
| budget (v0.4) | ⚠️ 96%（4h 超时截断） | 907/1000 步快照可用 |
| cap16 | 🔄 运行中（467/1000） | 预计 ~10:30 |
| aimd | 🔄 运行中（早期） | 预计 ~11:30 |
| cap4 | ⏳ 排队 | cap16 之后 |

注：4h 超时是旧 driver 常数，已改 6h；截断 run 的 steps.jsonl 数据完整可用于分析。

## 二、核心结果（200 真实 coding-agent 会话，96K 上下文，3090 24GB，KV 池 114K tok）

### 执行期质量（每步加权，来自 steps.jsonl）

| 策略 | 成功/失败 | 前缀命中率 | TTFT p50 | TTFT p90 |
|---|---|---|---|---|
| default（无准入） | 859/**121 败** | **0.0%** | **2,076s** | 3,100s |
| cap8（静态） | 873/1 | 2.0% | 80.3s | 166s |
| budget v0.4（前馈） | 907/1 | 4.7% | 471.7s | 952s |
| cap16（静态） | 467/1 | 0.0% | 165.9s | 278s |
| aimd（反馈） | 运行早期 | - | 81.0s | 163.0s |

### 三个论文级 observation

1. **无准入控制 = 灾难**：TTFT 中位数 34.6 分钟、12.3% 步骤直接失败、前缀命中率从计划的 75% 归零（逐出风暴摧毁缓存，每轮全量重算）。
2. **准入控制把 TTFT 从半小时拉回 80 秒（26×）、失败率从 12% 到 0.1%**——且不需要任何 kernel 开发，纯调度层。
3. **静态 cap 存在相位漂移失效**：cap8 早期命中率友好，但短会话完成后存活的全是大会话，8×大会话超出 KV 池，后期照样进 thrash（usage 92%、开始逐出）。动态控制（budget/aimd）的动机由此成立。

### 诚实的负面/复杂结果

- **本负载是极端过载**（200 会话 × 中位 56K 上下文 vs 114K 池），所有策略都要排队：gated 策略的准入等待 p50 达 1.6-1.8 小时，抵消了执行期收益，端到端会话完成时间各策略接近（p50 125-152 min）。**结论不是"gating 无用"，而是"该负载下系统根本性超订"**——今天应补一个梯度负载实验（50/100/200 会话），预期中等负载下 gating 大幅领先（无 thrash + 队列短）。
- budget v0.4 呈批式震荡（批完成→投影释放→大批准入→usage 顶格→硬停），振幅随队列缩短而增大（17→48）；vs cap8 更 Pack-more-sessions（199 vs 178 完成）但 TTFT p50 更差。v0.3→v0.4 的 starve-guard 自激→限频修复过程本身就是设计空间探索素材。
- **命中率全场地低（0-4.7%，计划 75%）**：24GB 卡上即使 gating 良好，并发工作集也无法保留前缀复用——**这个负载必须配层级缓存/KV 压缩才能工作**，正好衔接 KV 管理方向（C1 类）作为下一篇。

## 三、产物清单

- 数据：results/night/{default,cap8,budget,cap16,aimd,cap4}/{steps.jsonl, metrics.csv, admissions.jsonl, controller.jsonl, summary.json, metadata.json}
- 聚合：results/night/comparison.csv + first_figure.png（agg.py）
- 机制代码：TraceLab/replay/src（动态 cap-file 补丁）+ scripts/{controller_aimd, controller_budget, run_matrix, monitor, agg}.py
- 基建可复现：results/audit_memo.md

## 四、今天（白天）建议

1. 等 aimd/cap16/cap4 落地，重跑 agg.py 出完整六策略对比
2. **梯度负载实验**：50/100/200 会话 × {default, cap8, budget, aimd}——验证"中等负载下 gating 优势"假说（这是把故事从病理展示升级为机制论证的关键一步）
3. budget v0.5 设计讨论：批式准入 → 平滑准入（限频 admit）
4. 24h 内把夜跑数据整理成 paper-ready 图表（TTFT CDF、命中率时间线、retraction 风暴时间线）
