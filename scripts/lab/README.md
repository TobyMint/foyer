# 实验机上的脚本（镜像）

这些脚本**实际运行在 lab-3090 的 `/data/xbw/turnstile/scripts/`**，
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
