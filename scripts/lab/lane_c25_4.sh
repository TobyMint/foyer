#!/bin/bash
# 25 档静态 cap 前沿·cap4
# 25 档：125 步一条，约 30 分钟。目的是补【静态前沿对照】——原来那批七条全是 budget3 变体。
set -e
export TURNSTILE_RUN_TIMEOUT_H=3
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane c25_4 --gpu 2 --port 30042 \
  --runs 'pois200_cap4_25:static=4'
bash /data/xbw/turnstile/scripts/lane_done.sh c25_4 pois200_cap4_25
