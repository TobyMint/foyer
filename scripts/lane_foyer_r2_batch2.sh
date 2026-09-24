#!/bin/bash
# 重跑因【主机争用】作废的四条控制器臂 —— 第二批（GPU 3）。
# 背景与判据见 lane_foyer_r2_batch1.sh 顶部注释。
#
# 与第一批逐字同配置，只换 GPU/端口与臂。两条车道合起来覆盖 bres/hz0/hz2/breshz1。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane foyer_r2_batch2 --gpu 3 --port 30053 \
  --runs "pois200_foyer_hz2_r2:budget3:hw=0;target=0.95;horizon=2,pois200_foyer_breshz1_r2:budget3:hw=0;target=0.95;horizon=1;base=resident"
bash /data/xbw/turnstile/scripts/lane_done.sh foyer_r2_batch2 pois200_foyer_breshz1_r2
