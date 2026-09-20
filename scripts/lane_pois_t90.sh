#!/bin/bash
# Poisson main table, budget rho = 0.90 (more conservative than the 0.95 headline).
# Goal: recover the ~2 pp hit-rate gap to the tuned static cap2 while keeping the
# wall-clock advantage. Same sessions, same pool, controller parameters unchanged
# except rho.
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pois_t90 --gpu 3 --port 30033 \
  --runs 'pois200_foyer_t90:budget3:hw=0;target=0.90'
bash /data/xbw/turnstile/scripts/lane_done.sh pois_t90 pois200_foyer_t90
