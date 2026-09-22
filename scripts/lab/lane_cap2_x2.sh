#!/bin/bash
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04_x2.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane cap2_x2 --gpu 3 --port 30043 \
  --runs 'pois200_cap2_x2:static=2'
bash /data/xbw/turnstile/scripts/lane_done.sh cap2_x2 pois200_cap2_x2
