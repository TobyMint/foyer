#!/bin/bash
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
P=/data/xbw/turnstile/envs/main/bin/python
$P /data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py --lane foyer_hc_r4 --gpu 2 --port 30042 \
  --runs 'pois200_foyer_hc_r4:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh foyer_hc_r4 pois200_foyer_hc_r4
