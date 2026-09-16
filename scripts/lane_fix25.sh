#!/bin/bash
# Align the remaining 25-tier cliff points: cap3 and cap5 were run on the 97,367 pool
# (startup race, same class as the 48,234 case). Short runs — do these first.
export TURNSTILE_RUN_TIMEOUT_H=6
export TURNSTILE_MEMFRAC=0.85
export TURNSTILE_TRACE=/data/xbw/turnstile/data/replay_night25.csv
S=/data/xbw/turnstile/TraceLab/replay/scripts/run_matrix.py
P=/data/xbw/turnstile/envs/main/bin/python
$P $S --lane fix25 --gpu 2 --port 30034 --runs 'load25c_cap3r:static=3,load25c_cap5r:static=5'
bash /data/xbw/turnstile/scripts/lane_done.sh fix25 load25c_cap3r load25c_cap5r
