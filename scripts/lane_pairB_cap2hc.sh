#!/bin/bash
# Matched pair, wave B, arm 2/2: static cap 2 + HiCache — the same arm as wave A's
# lane_pairA_cap2hc, moved to gpu3. Runs CONCURRENTLY with lane_pairB_foyerhc.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pairB_cap2hc --gpu 3 --port 30033 \
  --runs 'pois200_pairB_cap2hc:static=2'
bash /data/xbw/turnstile/scripts/lane_done.sh pairB_cap2hc pois200_pairB_cap2hc
