#!/bin/bash
# Poisson main table, budget rho = 0.85 (see lane_pois_t90.sh for the rationale).
set -e
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pois_t85 --gpu 2 --port 30032 \
  --runs 'pois200_foyer_t85:budget3:hw=0;target=0.85'
bash /data/xbw/turnstile/scripts/lane_done.sh pois_t85 pois200_foyer_t85
