#!/bin/bash
# 低负载档：Foyer 会不会自动利用空出来的容量？（静态 cap 不会，它只会浪费。）
set -e
export TURNSTILE_RUN_TIMEOUT_H=14
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04_x05.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane foyer_x05 --gpu 3 --port 30043 \
  --runs 'pois200_foyer_x05:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh foyer_x05 pois200_foyer_x05
