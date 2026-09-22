#!/bin/bash
# 池容量杠杆（静态 cap 对照）：池应翻倍，对照 cap4_hc
# 引擎侧批次：改的是【上界本身】，不依赖政策维度。
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through --kv-cache-dtype fp8_e4m3"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane kv8cap --gpu 2 --port 30042 \
  --runs 'pois200_cap4_hc_kv8:static=4'
bash /data/xbw/turnstile/scripts/lane_done.sh kv8cap pois200_cap4_hc_kv8
