#!/bin/bash
# 短 trace 验证：同样的 controller，跑 2 轮的 trace（399 步，约 100 分钟）。
# 目的：确认"短 trace 复现全程结论"这个前提真的成立——不是靠 §三十八 的
# 离线截断分析，而是把它当成一条独立的 trace 文件真跑一遍。
set -e
export TURNSTILE_RUN_TIMEOUT_H=6
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04_r2.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane foy_r2 --gpu 2 --port 30042 \
  --runs 'pois200_foyer_r2:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh foy_r2 pois200_foyer_r2
