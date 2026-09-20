#!/bin/bash
# 25-tier fixed-config third repeat (n=3 for the error bars on the headline claim).
set -e
export TURNSTILE_RUN_TIMEOUT_H=6
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane rep25 --gpu 2 --port 30032 \
  --runs 'thr25_push_r3:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh rep25 thr25_push_r3
