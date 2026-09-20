#!/bin/bash
# Poisson main table: repeat of the Foyer row, for error bars on the headline number
# (the flash-crowd repeat was cancelled when the paper went Poisson-only).
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pois_rep --gpu 2 --port 30032 \
  --runs 'pois200_foyer_r2:budget3:hw=0;target=0.95'
bash /data/xbw/turnstile/scripts/lane_done.sh pois_rep pois200_foyer_r2
