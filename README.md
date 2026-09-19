# Foyer

**在显存受限的单卡上，给 agentic LLM serving 做容量核算准入控制（capacity-accounted admission control）。**

真实 coding agent 的上下文又长又涨：首轮 prompt 中位 17K token，会话峰值中位 32K token，而 24GB 的 3090 上 7B 模型的 KV 池只有约 10 万 token——**一个会话就能占掉池子的 23–88%**。"同时放几个会话进来"直接决定系统是正常服务还是崩溃。Foyer 的主张：会话的 KV 需求在到达时刻就可观测（首轮 prompt + 会话增长轨迹），因此应当**按容量核算准入**，而不是数人头（静态 cap-N），也不是等缓存被打坏之后才反应（Concur 式 AIMD）。

数据用 UW TraceLab 的脱敏 coding-agent 会话（本次导出核对的库内含 8,058 会话 / 66.5 万轮），会话级闭环重放到单卡 3090 的 SGLang 0.5.10 + Qwen2.5-Coder-7B（YaRN ×3，96K 上下文）。

## 三个创新点（统一口径）

1. **容量核算准入（含命名许可）** —— 按 KV token 容量记账放行，控制器写下的不是并发数而是**确切的会话 ID 集合**，计划即执行（`scripts/controller_budget3.py`，论文 §3.1）
2. **状态保留式挂起** —— 被暂停会话的 KV 下沉主机内存，复活是搬运不是重算，使"暂停"可逆（SGLang HiCache，论文 §3.2）
3. **有界复活（设计，尚未验证）** —— 按"已等待时间 ÷ 复活代价"排序回归，代价按 KV 所在层级定价（论文 §3.3）

其余内容——动机实证（悬崖、n 不可先验）与测量性发现（驱逐 U 形曲线、保护层成本、数据有效性守卫）——是支撑材料，不单独计为创新点。

## 现在到哪了（2026-09-19）

- 系统完整可用：容量核算准入 + 命名许可 + 状态保留挂起 + 池子守卫。`results/night/` 下 80 个受管 run（75 个已完成），全部表格由 `scripts/make_tables.py` 一键重建（`docs/tables.md`）。
- 已确立的机制性发现：① 静态 cap 的甜点区极窄（25 档 cap3→cap5 命中率 64.9%→36.6%，cap7 归零）；② 压力驱逐–代价曲线是 **U 形**（零驱逐的 cap1 全表最慢，存在内部最优）；③ 我们**自己为安全加的**两个机制（高水位地板、单飞准入）曾吃掉 47% 的完成时间，回收即修复——"保护层会变成天花板"。
- **诚实站位**：200 齐射档，最好的静态 cap2（301.7min / 67.0% 命中）与我们（311.4min / 64.8%）接近打平；泊松到达（299.3 vs 310.5min）与真实高峰小时（79.3 vs 131.9min）我们更快。"不需要逐负载调参"这一立论**还缺池子/负载漂移实验的直接证据**（未跑）。
- 未完成：机制③"有界复活"只有设计；预测器的独立收益未证明（oracle 臂实现有缺陷、结论已撤回）；Concur 忠实复现 5 个 arm 完成 2 个；关键配置误差棒未做。

## 文档地图

| 文档 | 状态 | 用途 |
|---|---|---|
| `REVIEW.md` | ✅ 当前 | 给外部审计方的评审简报（主张 / 证据位置 / 已知弱点 / 想被攻击的问题） |
| `docs/STATE.md` | ✅ 当前 | 工程状态备忘：基础设施、已知缺陷、待办优先级、战略决策、协作约定 |
| `paper/draft-v1.zh.md` | ✅ 当前 | 论文中文工作稿，结构同最终论文，数字全部可溯源 |
| `docs/tables.md` | ✅ 当前 | 论文全部表格，由 `scripts/make_tables.py` 从 run 产物重建 |
| `docs/runs_registry.md` | ✅ 自动生成 | run 登记表（池子异常的历史 run 标 ⚠；未完成的标 running） |
| `docs/literature_survey_20260911.md` | 🕓 时点调研 | 2026-09-11 的相关工作调研快照 |
| `docs/NIGHT_REPORT.md`、`docs/audit_memo.md`、`docs/coverage_report.txt`、`docs/smoke_summary.json` | 🕓 历史 | 2026-09-07/08 项目启动期的验收与审计产物，已被后续实验取代 |
| `REVIEW2.md`、`reviews/` | 🕓 历史 | 09-09 / 09-11 与外部审计的交锋记录，描述的是当时 commit 的状态 |

## 目录里都有什么

| 路径 | 内容 |
|---|---|
| `runner/` | 修改自 [TraceLab](https://github.com/uw-syfi/TraceLab) 的 `session_runner`（Apache-2.0）：新增 `--permit-file` 命名许可（准入/暂停的确切会话集合）与 `--cap-file`（静态上限对照），以及准入事件日志（queued/admit/pause/resume/release + 排队时长） |
| `scripts/controller_budget3.py` | **论文里的 Foyer**：容量核算准入 + 命名许可 + SLO 熔断 + 饥饿保护（`budget3` 是它在代码中的名字） |
| `scripts/controller_budget2.py` | 开天眼预留版（不可部署的上界对照） |
| `scripts/controller_budget.py` | 朴素前馈 v0.4（保留作失败分析：准入棘轮、假空闲泄漏） |
| `scripts/controller_aimd2.py` | Concur 忠实复现（u_low/u_high/h_thresh + `--h-mode`） |
| `scripts/run_matrix.py` | 实验驱动器：池子守卫（不符则解算 memfrac 重试）+ 溯源 manifest |
| `scripts/make_tables.py` | 从 run 产物一键重建论文全部表格（含池子/步骤数校验） |
| `scripts/gen_registry.py` | 生成 `docs/runs_registry.md` |
| `results/night/` | run 产物镜像（完整数据在 lab-3090 上） |

## 怎么复现

1. 机器：Ubuntu + RTX 3090/4090。Miniconda 环境装 `sglang[all]==0.5.10.post1`、conda 的 gcc-12（`gxx_linux-64=12`，JIT 内核要 C++20）、rust
2. 模型：Qwen2.5-Coder-7B-Instruct，改 `config.json`（`max_position_embeddings=98304`、`rope_scaling=yarn/3.0`），见 `scripts/launch_sglang.sh`
3. 数据：TraceLab 公开数据集（GitHub releases 的 `syfi_coding_trace.duckdb`）+ 一个大 UTF-8 文本（enwik9，给合成 token 池用）。导出重放 CSV，列名必须是 `session_id,round_idx,prefix_len,input_len,output_len,tool_wait_after_ms`
4. rust 依赖在服务器上下不动：在联网机器上 `cd runner && cargo vendor vendor`，打包传过去离线编译
5. 跑：`python scripts/run_matrix.py --gpu 3 --port 30000 --runs default,cap4:static=4,aimd2,budget3`

## 版权说明

`runner/` 修改自 [uw-syfi/TraceLab](https://github.com/uw-syfi/TraceLab)（Apache-2.0），原始 LICENSE 和 NOTICE 保留在目录内；实验用的 coding-agent 数据集也来自该项目。
