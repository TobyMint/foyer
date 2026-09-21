#!/bin/bash
# Matched pair, wave B, arm 1/2: Foyer + HiCache — the SAME arm as wave A's
# lane_pairA_foyerhc, moved to gpu2. Wave B exists to swap the GPUs, so a
# card-specific neighbour (or a card-specific clock/thermal state) cannot be
# mistaken for a treatment effect. The estimator is the paired difference.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pairB_foyerhc --gpu 2 --port 30032 \
  --runs 'pois200_pairB_foyerhc:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh pairB_foyerhc pois200_pairB_foyerhc
