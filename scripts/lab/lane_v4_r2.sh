#!/bin/bash
# v4：热会话按【引擎实测的边际代价】计费，而不是按整轮 ctx（v3 会重复计费）。
# 单变量：与 foy_r2 只差 charge=delta 这一个参数，其余逐字相同。
set -e
export TURNSTILE_RUN_TIMEOUT_H=6
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04_r2.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane v4_r2 --gpu 2 --port 30042 \
  --runs 'pois200_v4_r2:budget3:hw=0;target=0.95;charge=delta'
bash /data/xbw/turnstile/scripts/lane_done.sh v4_r2 pois200_v4_r2
