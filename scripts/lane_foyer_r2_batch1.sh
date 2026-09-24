#!/bin/bash
# 重跑因【主机争用】作废的四条控制器臂 —— 第一批（GPU 2）。
#
# 为什么重跑（2026-09-24 发现）：
# 这四条臂（bres / hz0 / hz2 / breshz1）在 09-22 23:17–23:33 与另外三条一起启动，
# 四台 SGLang server + 四个 runner 同机重叠了约 300 分钟。它们的 τ₂（逐请求 decode
# 间隔中位，客户端实测、不经采样器）是 30.9~33.3 ms，而同一族的干净 run 是 23.8~25.7；
# 抬升在整个 run 内是【平的】，即持续的外部条件而非瞬态。
#
# 对照证据（scripts/lab/probe_concurrency.py）：cap1 单独/双车道跑时 τ₂ 恒在 20.4~20.7，
# 02:25 rl90+rl99 起来后跳到 22.4~27.5；t85 与 rl99 两条独立 run 在 07:09~07:23
# （rl90 结束前后）同时从 ~30 回落到 ~22~25。结论：总并发 <=2 时干净，>=3 时抬高 25~40%。
#
# 因此这四条的墙钟与 SLO 不与表 I 其余各行可比，必须重测。旧 run 目录原样保留，
# 不覆盖不删除（论文里要如实报告这次发现与重跑）。新 run 名一律加 _r2 后缀。
#
# 纪律：本车道全程只占 GPU 2 一条，与 GPU 3 的另一条凑成 2 条，绝不三条以上。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane foyer_r2_batch1 --gpu 2 --port 30052 \
  --runs "pois200_foyer_bres_r2:budget3:hw=0;target=0.95;base=resident,pois200_foyer_hz0_r2:budget3:hw=0;target=0.95;horizon=0"
bash /data/xbw/turnstile/scripts/lane_done.sh foyer_r2_batch1 pois200_foyer_hz0_r2
