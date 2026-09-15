#!/bin/bash
# Poisson-arrival study — finish the static sweep (cap3, then cap4) in one lane.
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pois_cap34 --gpu 2 --port 30029 --runs 'pois200_cap3:static=3,pois200_cap4:static=4'
touch /data/xbw/turnstile/results/night/lane_pois_cap34_DONE
