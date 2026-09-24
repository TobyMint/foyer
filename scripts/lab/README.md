# scripts/lab —— 生成器与 lane 脚本

这个目录里有两类东西，**运行位置不一样**，别搞混（2026-09-24 因此栽过一次，
见 CLAUDE.md「本地镜像是部分快照」）：

## 一、必须在实验机（lab-3090）上跑的

判据：**输出会随「目录里有哪些 run」变化**（计数、排名、并发、集合中位数）。

- `gen_concurrency.py`（同时几条车道；本地跑会把 `var_cap3` 从 CONTESTED 判成 clean）
- `gen_gate_attrib.py`（全表统计；本地 34 行 vs 实验机 46 行）
- `gen_projection.py`（全表区间与中位数；本地 35 行 vs 实验机 47 行）
- `frontier.py --csv`（用 `TURNSTILE_RESULTS` 切目录；本地跑前先确认 `pois200_*` 目录数一致）

这三个生成器都带最小行数护栏（镜像不全直接报错）。跑完把 CSV scp 回 `paper/data/`。

## 二、可以在本地镜像上跑的

判据：run 列表是**显式写在脚本里**的（缺 run 会报错，不会静默少一行），
所以镜像不全会立刻暴露。本机 `results/night/` 里有 54 个 `pois200_*` 与
`realhr_*` 目录，够它们用：

- `gen_runs.py`（表 I 的行清单；`runs.csv`）
- `gen_table.py`（表 I 每一列含 Δ；`table1.csv`）
- `gen_reuse.py` / `gen_reuse_x.py` / `gen_slope.py`（复用兑现与斜率）
- `gen_decomp.py` / `gen_arm_running.py` / `gen_eviction.py`（时间与体积分解）
- `gen_occupancy.py` / `gen_hitrate.py` / `gen_tier25.py` / `gen_toolwait.py` /
  `gen_arrival_slo.py` / `gen_projection.py`（后者见上，须在实验机）
- 自检：`check_paper_numbers.py`（正文 ↔ CSV）、`audit_numbers.py`（正文 ↔ 任何文件）、
  `data_run_coverage.py`（镜像体检）、`compare_rerun.py`（重跑对照）

## 三、lane 脚本（跑实验用）

这些**实际运行在 lab-3090 的 `/data/xbw/turnstile/scripts/`**，
这里是从那边拉下来的镜像，用于留档与复现。

## 2026-09-22 新增

### 链条（整夜队列）
- `chain_gpu2.sh` / `chain_gpu3.sh`：顺序执行 lane 脚本，每条之间等上一条的 `summary.json`。
  **每张卡固定一个端口**（gpu2=30042、gpu3=30043）——因为 `run_matrix.start_server`
  的清理是 `pkill -f "launch_server.*--port {port}"`，**按端口做**；
  若每条 lane 用不同端口，前一条失败留下的 server 杀不掉，
  下一条会加载进已占用的显存 → 池子守卫拒绝 → **整条链静默级联失败**。
  链条里还有 **stale 守卫**：目标 run 目录已存在且无 `summary.json` 就先挪走
  （`run_matrix` 用 `makedirs(exist_ok=True)`，不清目录）。

### 三条新 trace（`/data/xbw/turnstile/data/`）
由 `replay_pois200_l04.csv`（999 行 / 200 会话 / 到达跨度 80 min）派生：

| 文件 | 改了什么 | 为什么 |
|---|---|---|
| `replay_pois200_l04_r2.csv` | 只保留 round 0,1（399 行） | 快速迭代：约 100 分钟 vs 全程 290 分钟。**到达窗口不变**，所以 200 个会话仍在同样的 80 分钟里到达，峰值拥塞不变，只是尾巴短了 |
| `replay_pois200_l04_x2.csv` | `arrival_time` 压缩 2× | 高负载档：静态 cap 要不要按负载重调？ |
| `replay_pois200_l04_x05.csv` | `arrival_time` 拉长 2× | 低负载档：Foyer 会不会自动吃掉多出来的容量？ |
| `replay_pois200_l04_c50.csv` | `prefix_len` / `input_len` 各 ×0.5 | 每请求显存减半：静态 cap 只会数数、看不见"请求变轻了"，Foyer 看的是池子利用率 |

**切法为什么按轮数而不是按会话数**：按会话切会把并发砍半，那是换了个实验。
按轮数切保住到达过程本身。依据：跑满的全程 run 里负载在时间上是均匀的
（每个十分位都是 r0..r4 各约 20 个，平均 prefix 19k→25k 平稳）。

### 工具
- `run_summary.py`：任意长度都能量的汇总（现有脚本写死了 999 步，短 trace 会被静默跳过）。
  并发用**时间加权**，不是按 admit 事件数加权——后者会被高并发时刻带偏。
- `fig_cliff.py`：并发 vs SLO / 段标准差，画出静态 cap 的悬崖和 Foyer 的位置。

### `quick.sh` —— 一条命令跑一次快速实验

```bash
quick.sh <短名> "<策略串>" [GPU]
quick.sh warm2 "budget3:hw=0;target=0.95"      # 自动挑空闲的卡
QUICK_TRACE=full quick.sh warm2 "..."          # 跑全程（默认跑短 trace）
```

默认用 `replay_pois200_l04_r2.csv`（约 100 分钟；全程 290 分钟），跑完自动出汇总。
**今天踩过的坑都封在里面**：端口按 GPU 固定、开跑前挪走同名旧目录、卡被占时拒绝而不是硬上。
