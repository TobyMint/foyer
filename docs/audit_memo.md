# Turnstile Day-0.5 审计 Memo（2026-09-07）

## 结论：三条审计全部通过，Day 1 可以开工

### ① 覆盖率（数据：syfi_coding_trace.duckdb，665,453 rounds / 8,058 sessions）
- Session 峰值上下文：p25=39K, p50=69K, p75=126K, p90=228K
- 3090（memfrac 0.88，BF16，KV 池 102,917 tok）：并发 4 时仅约 6% 会话可完整容纳 → 压力是默认运行点
- 同 agent count 下 KV 工作集 p90/p10 = 5.1x（96K 子集内）
- tool wait：p50=218ms, p90=10s, p99=152s（重尾）
- 上下文上限定为 96K（YaRN 3x），过滤后保留 5,326 会话 / 80,035 rounds（66%）

### ② 重放器（session_runner，已从源码构建）
- 会话闭环内置（round i → 完整响应 → tool_wait → round i+1）
- 合成文本（enwik9 池，≥100M tok），直接提交 token id
- 内置 --max-active-sessions（static cap 基线可直接用）+ --summary-path（每 run JSON 汇总：TTFT/命中率/溢出/输出对账）

### ③ 冒烟测试（4 会话 / 20 步实弹）
- 20/20 成功，output_token_delta=0（逐 token 可复现）
- planned prefix hit 78.5% vs server 实测 68.3% → 差值即逐出证据，与 ① 的容量预测吻合
- TTFT p50=1.39s / p90=7.7s / max=22.6s

## 环境配置（可复现）
- 服务器 lab-3090（4x3090，驱动 570.133.07 / CUDA 12.8），实验从卡 3 开始用
- SGLang 0.5.10.post1 + torch 2.9.1 + sglang-kernel 0.4.1 + flashinfer 0.6.7（conda env: /data/xbw/turnstile/envs/main）
- 模型：/data/xbw/turnstile/models/qwen25-coder-7b-yarn96k（符号链接 + 补丁 config.json：max_pos=98304，yarn 3.0）
- 启动：scripts/launch_sglang.sh（gcc12 via conda + NVCC_CCBIN 修复 JIT；--enable-metrics --enable-cache-report；端口 30000）
- 关键坑位：JIT 需要 C++20（系统 gcc9 不行 → conda gxx12 + NVCC_CCBIN + PATH compiler-bin）；--rope-scaling 旗标不存在（用 config.json 补丁）；--enable-cache-report 必须开（runner 预检依赖 cached_tokens）；enwik9 在 data/ 下；CSV 列名必须是 round_idx 不是 round_index
- session_runner：TraceLab/replay/target/release/session_runner（laptop 上 cargo vendor 离线编译后 scp，reqwest 换 rustls）
- 数据：data/replay_sessions_96k.csv（全量 80,035 rounds / 5,326 sessions）、replay_starter200_96k.csv（200 会话）、replay_smoke4.csv（冒烟）
- 磁盘预算：/data 剩 1.7T，模型 15G，语料 1G，无压力

## Day 1 就绪清单
- 服务：GPU3 上 SGLang 已在跑（端口 30000），重启用 scripts/launch_sglang.sh
- 跑一个策略组合 = 选 CSV 切片 + session_runner 参数（--max-active-sessions 即 static cap）+ --summary-path 输出
- 待实现：Concur-style AIMD 复现（外部 proxy 控 max-active-sessions 动态值即可，无需改 runner）与 token-budget admission proxy
