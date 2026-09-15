#!/bin/bash
# Poisson-arrival study — static cap2 (the cap that was optimal under the flash crowd).
# Question: does the best fixed cap move when the arrival process changes?
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_pois200_l04.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane pois_cap2 --gpu 2 --port 30027 --runs 'pois200_cap2:static=2'
touch /data/xbw/turnstile/results/night/lane_pois_cap2_DONE
