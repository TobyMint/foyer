#!/bin/bash
# 未测过的轴：驱逐政策 lru->slru。对照 cap4_hc 213.0/3.93/63.4
# 单变量相对照组；引擎参数走 TURNSTILE_HICACHE_ARGS 通道（run_matrix.py:348 是通用附加参数）。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through --radix-eviction-policy slru"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane cap4slru --gpu 3 --port 30043 \
  --runs 'pois200_cap4_hc_slru:static=4'
bash /data/xbw/turnstile/scripts/lane_done.sh cap4slru pois200_cap4_hc_slru
