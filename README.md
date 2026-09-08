# Foyer

**在显存紧张的 GPU 上，给 agentic LLM serving 做准入控制（admission control）。**

一句话背景：真实 coding agent 的上下文又长又涨（中位峰值 69K token），而 24GB 的 3090 上 KV 池只有 ~11.5 万 token——**放几个会话进来、放谁进来**，直接决定系统是正常服务还是崩溃。Foyer 就是在这个场景下研究和对比各种准入策略的实验项目。

数据用的是真实的：UW TraceLab 的 4300+ 个脱敏 coding-agent 会话，重放到单卡 3090 的 SGLang 上。

## 目录里都有什么

| 路径 | 内容 |
|---|---|
| `runner/` | 改过的 [TraceLab](https://github.com/uw-syfi/TraceLab) `session_runner`（Apache-2.0）。加了两样东西：`--cap-file`（运行时轮询一个文件拿到动态并发上限，让外部控制器能随时改）和 `--admission-log`（每个会话的准入/释放事件 + 排队时长）。原版说明见 `UPSTREAM_README.md` |
| `scripts/controller_aimd.py` | Concur 式 AIMD 反馈控制器：显存使用率超目标 **且** 命中率崩了 → 窗口砍半；否则线性增长 |
| `scripts/controller_budget.py` | 我们的前馈控制器：新会话进门时就能看见它的体量（第一轮 prompt + 未来几轮增长 + trace 峰值封顶），装得下才放行；配 usage 硬闸和限频的饥饿保护 |
| `scripts/run_matrix.py` | 实验驱动器：每个策略跑之前重启一个干净的 SGLang（避免缓存互相污染），挂上监控器和控制器，跑完归档 |
| `scripts/monitor.py` / `agg.py` | 指标采样（usage/命中率/逐出数）和跨 run 聚合出表出图 |
| `scripts/launch_sglang.sh` | 3090 上能跑通的 SGLang 启动配置（YaRN 96K 上下文；gcc-12/NVCC 的 JIT 编译修复） |
| `results/night/` | 夜跑矩阵：每个策略一个目录（每步日志、引擎指标、准入事件、控制器决策、汇总） |
| `docs/NIGHT_REPORT.md` | 完整发现 + 注意事项 + 下一步 |

## 夜跑核心结果（200 个真实会话，Qwen2.5-Coder-7B，3090 24GB）

| 策略 | 失败步骤 | 前缀命中率 | TTFT 中位数 |
|---|---|---|---|
| default（不设限） | **121 / 980（12.3%）** | **0.0%** | **34.6 分钟** |
| 静态 cap = 8 | 1 | 2.0% | 80 秒 |
| token-budget（我们的） | 1 | 4.7% | 472 秒 |
| 静态 cap = 16 | 1 | 0.0% | 166 秒 |

一句话：**不放准入 = 灾难**（首 token 等半小时、12% 请求直接失败、缓存全灭每轮重算）；**准入控制把 TTFT 拉回 80 秒、失败率清零**，而且纯调度层改动、零 kernel 开发。

另外一个重要发现：**静态 cap 有"相位漂移失效"**——早期合适，但短会话跑完后活下来的都是大会话，8 个大会话照样撑爆池子，后期又开始 thrash。这正是需要动态控制的证据。

## 怎么复现

1. 机器：Ubuntu + RTX 3090/4090。装 Miniconda 环境：`sglang[all]==0.5.10.post1`、conda 的 gcc-12（`gxx_linux-64=12`，JIT 内核要 C++20）、rust
2. 模型：Qwen2.5-Coder-7B-Instruct，改 `config.json`（`max_position_embeddings=98304`、`rope_scaling=yarn/3.0`），见 `scripts/launch_sglang.sh`
3. 数据：TraceLab 公开数据集（GitHub releases 的 `syfi_coding_trace.duckdb`）+ 一个大 UTF-8 文本（enwik9，给合成 token 池用）。导出重放 CSV，列名必须是 `session_id,round_idx,prefix_len,input_len,output_len,tool_wait_after_ms`
4. rust 依赖在服务器上下不动：在联网机器上 `cd runner && cargo vendor vendor`，打包传过去离线编译
5. 跑：`python scripts/run_matrix.py --lane A --gpu 3 --port 30000 --runs default,cap8:static=8,aimd`

## 当前状态

进行中。部分 run 撞了 4 小时超时被截断（数据快照仍可用，注意看 `docs/NIGHT_REPORT.md` 的说明）。aimd/cap16/cap4 还在跑，全部落齐后重跑 `agg.py`。未投稿、未同行评审。

## 版权说明

`runner/` 修改自 [uw-syfi/TraceLab](https://github.com/uw-syfi/TraceLab)（Apache-2.0），原始 LICENSE 和 NOTICE 保留在目录内；实验用的 coding-agent 数据集也来自该项目。
