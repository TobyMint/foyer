#!/bin/bash
# Matched pair, wave A, arm 2/2: Foyer + HiCache, EXACTLY the config of the 297.6
# run (budget3:hw=0;target=0.95 plus the same HiCache flags).
#
# Runs CONCURRENTLY with lane_pairA_cap2hc on gpu2, so both arms see the same box
# conditions — that is the point of the pairing, not an accident of scheduling.
# See lane_pairA_cap2hc.sh for the full rationale.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_HICACHE_ARGS="--enable-hierarchical-cache --hicache-ratio 2 --hicache-write-policy write_through"
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pairA_foyerhc --gpu 3 --port 30033 \
  --runs 'pois200_pairA_foyerhc:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh pairA_foyerhc pois200_pairA_foyerhc
