# Foyer

**在显存紧张的 GPU 上，给 agentic LLM serving 做准入控制（admission control）。**

一句话背景：真实 coding agent 的上下文又长又涨（首 prompt 中位 17K token，峰值中位 32K），而 24GB 的 3090 上 KV 池只有 ~10 万 token——**放几个会话进来、放谁进来**，直接决定系统是正常服务还是崩溃。Foyer 的核心主张：会话的 KV 需求在**到达时就可观测**，前馈式准入优于反应式（缓存反馈 AIMD）和需要逐档调参的静态并发上限。

数据用的是真实的：UW TraceLab 的 4300+ 个脱敏 coding-agent 会话，重放到单卡 3090 的 SGLang 上。

**想审这个项目？从 [REVIEW.md](REVIEW.md) 开始**（主张、证据位置、已知弱点、想被攻击的问题清单）。完整论文工作稿在 `paper/draft-v1.zh.md`。

## 目录里都有什么

| 路径 | 内容 |
|---|---|
| `REVIEW.md` | 评审简报（从这里开始读） |
| `paper/draft-v1.zh.md` | 论文工作稿（中文，结构同最终论文，数字全部可溯源） |
| `runner/` | 改过的 [TraceLab](https://github.com/uw-syfi/TraceLab) `session_runner`（Apache-2.0）。加了两样东西：`--cap-file`（运行时轮询动态并发上限）和 `--admission-log`（准入/释放事件 + 排队时长） |
| `scripts/controller_budget2.py` | **我们的前馈控制器 v0.5**：高水位空闲判据 + 单飞准入 + TTFT-SLO 熔断（含 `--disable-*` 消融开关） |
| `scripts/controller_budget.py` | 朴素前馈 v0.4（保留了做对照：它输给 aimd，失败分析是论文素材） |
| `scripts/controller_aimd.py` | Concur 式 AIMD 反馈控制器（3090 重调参，3 轮） |
| `scripts/run_matrix.py` | 实验驱动器：每策略重启干净 SGLang、挂监控与控制器、跑完归档 |
| `scripts/agg.py` / `monitor.py` | 指标采样与跨 run 聚合出表 |
| `results/night/` | 全部 run 的原始日志（逐轮 TTFT、准入事件、控制器决策、引擎指标）+ `comparison.csv` 聚合表 |

## 核心结果（三档负载 × 五策略，3090 单卡，Qwen2.5-Coder-7B）

Foyer（v0.5）三档全胜，包括打败需要逐档人工调参的 oracle 静态上限：

| 负载 | 最强对手 | 命中率 | TTFT p50 | SLO 达标 | Foyer 命中率 | Foyer TTFT p50 | Foyer SLO |
|---|---|---|---|---|---|---|---|
| 25 会话 | cap=6（oracle） | 33.9% | 14.8s | 40.0% | **51.5%** | **4.3s** | **69.6%** |
| 50 会话 | cap=6（oracle） | 17.7% | 34.8s | 17.2% | **58.1%** | **4.3s** | **67.6%** |
| 200 会话 | cap=4（oracle） | 49.6% | 5.6s | 62.3% | **56.9%** | **4.0s** | **71.9%** |

同时 wall 时间与最快基线持平或更短（200 档 227min，全场最短）——**质量收益零吞吐代价**。

反面对照同样保留：不限流 = 灾难（200 档命中率 0%、TTFT 中位 34.6 分钟、12.3% 请求失败）；我们的朴素前馈 v0.4 也翻过车（准入棘轮 + 假空闲泄漏，cap 涨到 64 收不回来），失败机理分析进了论文。

## 怎么复现

1. 机器：Ubuntu + RTX 3090/4090。装 Miniconda 环境：`sglang[all]==0.5.10.post1`、conda 的 gcc-12（`gxx_linux-64=12`，JIT 内核要 C++20）、rust
2. 模型：Qwen2.5-Coder-7B-Instruct，改 `config.json`（`max_position_embeddings=98304`、`rope_scaling=yarn/3.0`），见 `scripts/launch_sglang.sh`
3. 数据：TraceLab 公开数据集（GitHub releases 的 `syfi_coding_trace.duckdb`）+ 一个大 UTF-8 文本（enwik9，给合成 token 池用）。导出重放 CSV，列名必须是 `session_id,round_idx,prefix_len,input_len,output_len,tool_wait_after_ms`
4. rust 依赖在服务器上下不动：在联网机器上 `cd runner && cargo vendor vendor`，打包传过去离线编译
5. 跑：`python scripts/run_matrix.py --gpu 3 --port 30000 --runs default,cap4:static=4,aimd,budget2`

## 当前状态

进行中（2026-09-09）：三档主矩阵已完成；关键配置 ×3 重复（误差棒）与三组件消融在跑，预计 09-10 中午出齐；相关工作系统排查进行中。未投稿、未同行评审。

## 版权说明

`runner/` 修改自 [uw-syfi/TraceLab](https://github.com/uw-syfi/TraceLab)（Apache-2.0），原始 LICENSE 和 NOTICE 保留在目录内；实验用的 coding-agent 数据集也来自该项目。
