#!/bin/bash
# Poisson-arrival study — the fixed controller config (floor off, budget 0.95),
# unchanged from the flash-crowd study: we do NOT retune it for the new arrival shape.
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pois_foyer --gpu 3 --port 30028 --runs 'pois200_foyer:budget3:hw=0;target=0.95'
touch /data/xbw/turnstile/results/night/lane_pois_foyer_DONE
