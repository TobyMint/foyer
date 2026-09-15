#!/bin/bash
# Throttle A/B wave 2 — high-water floor OFF (decay=0 -> floor follows the live
# reading). Hypothesis: the floor's phantom occupancy (~24k tok ~ 32% of budget)
# is what leaves only ~17k headroom, too little for a 30-50k session to be admitted.
export TURNSTILE_RUN_TIMEOUT_H=12
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane thr_nohw --gpu 2 --port 30022 --runs 'thr25_nohw:budget3:hw=0'
touch /data/xbw/turnstile/results/night/lane_thr_nohw_DONE
